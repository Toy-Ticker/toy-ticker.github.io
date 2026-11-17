"""Weekly market report: one static page a week summing up Happy Meal toy prices.

Numbers only, straight from data/ (no AI): biggest movers, hardest to find (same rarity score as the site),
most sold, best deals today, and how long the current promo has left.

  python3 scripts/weekly_report.py --publish            # reports/<date>/index.html + reports/index.html + data/reports.json
  python3 scripts/weekly_report.py --publish --if-sunday  # what the daily price job runs: only acts on Sundays (UTC)
  python3 scripts/weekly_report.py --out FILE           # a one-off preview at the repo root (paths relative to it)

<date> is the day of the price data. Publishing the same date again replaces that week's page.
"""
import argparse
import html
import json
import math
import re
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://toy-ticker.github.io/"
LOG = ROOT / "data" / "reports.json"   # [{date, lede}], newest first: the archive page and sitemap read it
PREFIX = ""   # path from the page being written back to the site root ("../../" for reports/<date>/)
EPN = {"mkcid": "1", "mkrid": "711-53200-19255-0", "siteid": "0", "campid": "5339247181", "toolid": "10001", "mkevt": "1"}
MIN_LISTINGS = 5   # movers need at least this many listings on both days, so one odd listing can't top the board


# Series tag colours, the same pill colours as the series tabs on the main page (THEMES in index.html).
STYLE = {
    "pokemon-2026": ("Pokémon cards", "#fff3c4", "#6b4300", "#4a3a00", "#ffe27a"),
    "pokemon-toys-2026": ("Pokémon toys", "#fde3dc", "#7a1f07", "#4a1a10", "#ffd0c2"),
    "boo-buckets-2026": ("Boo Buckets", "#eeedfe", "#3c3489", "#3b2a5c", "#ddd0ff"),
    "spongebob-onepiece-2026": ("SpongeBob × One Piece", "#e0f2fb", "#0b4f8a", "#123a52", "#bfe9fb"),
    "hello-kitty-godzilla-2026": ("Hello Kitty × Godzilla", "#fde4ef", "#7d1145", "#4a1a30", "#ffc9df"),
    "world-cup-squishmallows-2026": ("World Cup Squishmallows", "#e2f4ea", "#135c35", "#173d2a", "#c4f0d6"),
    "bt21-2026": ("BT21", "#eeedfe", "#3c3489", "#2e2a5c", "#dcd8ff"),
}


def tag(idx, iid, link=True):
    """Coloured series pill linking to that series on Toy Ticker; a green dot when it's in Happy Meals now."""
    sid = idx["items"][iid]["set"]; s = idx["sets"][sid]
    name, bg, ink, bgd, inkd = STYLE.get(sid, (s.get("tab") or s["name"], "#f1f0ea", "#444", "#33332f", "#ddd"))
    when = "in Happy Meals now" if s.get("current") else f"ended {date.fromisoformat(s['end']).strftime('%b %Y')}" if s.get("end") else ""
    el = f'a href="./?s={esc(sid)}"' if link else "span"   # no link inside a deal card, which is itself a link
    el = el.replace('href="./', f'href="{PREFIX or "./"}')
    return (f'<{el} class="tag" style="--tb:{bg};--ti:{ink};--tbd:{bgd};--tid:{inkd}" title="{esc(s["name"])}{(" · " + when) if when else ""}">'
            f'{"<i></i>" if s.get("current") else ""}{esc(name)}</{el.split()[0]}>')


def esc(s):
    return html.escape(str(s if s is not None else ""))


def usd(v):
    return "—" if v is None else f"${v:,.2f}"


def aff(url, label):
    u = urlparse(url)
    if not u.netloc.endswith("ebay.com"):
        return url
    q = dict(parse_qsl(u.query)); q.update(EPN); q["customid"] = label
    return urlunparse(u._replace(query=urlencode(q)))


def load():
    idx = json.loads((ROOT / "data/index.json").read_text())
    hist, sold = {}, {}
    for f in (ROOT / "data/series").glob("*.json"):
        d = json.loads(f.read_text())
        hist.update(d.get("history", {})); sold.update(d.get("sold", {}))
    return idx, hist, sold


def label(idx, iid):
    it = idx["items"][iid]; s = idx["sets"][it["set"]]
    kind = " card" if s.get("kind") == "cards" else " toy" if it["set"].startswith("pokemon") else ""
    return f"{it['name']}{kind}", s.get("tab") or s["name"]


def movers(idx, hist, today):
    """Change in median asking price over the last 7 days (or since tracking began, if that's shorter)."""
    start = (date.fromisoformat(today) - timedelta(days=7)).isoformat()
    out = []
    for iid, h in hist.items():
        if iid not in idx["items"] or not h:
            continue
        now = h[-1]
        then = next((p for p in h if p["date"] >= start), None)
        if not then or then is now or not now.get("median") or not then.get("median"):
            continue
        if min(now.get("count") or 0, then.get("count") or 0) < MIN_LISTINGS:
            continue
        out.append({"id": iid, "ch": now["median"] / then["median"] - 1, "from": then["median"], "to": now["median"], "since": then["date"]})
    return sorted(out, key=lambda x: -x["ch"])


def rarity(idx):
    """Same score as the site: geometric mean of price vs typical and typical supply vs supply, per set and kind."""
    out = []
    for sid, s in idx["sets"].items():
        if not s.get("current"):
            continue
        rows = [(iid, it["latest"]) for iid, it in idx["items"].items() if it["set"] == sid and (it.get("latest") or {}).get("median")]
        rows = [(i, L, L.get("supply") or L.get("count")) for i, L in rows if (L.get("supply") or L.get("count"))]
        if len(rows) < 4:
            continue
        mp = sorted(L["median"] for _, L, _ in rows)[len(rows) // 2]
        ms = sorted(sup for *_, sup in rows)[len(rows) // 2]
        for iid, L, sup in rows:
            out.append({"id": iid, "score": math.sqrt(L["median"] / mp * ms / sup), "price": L["median"], "sup": sup, "fewer": sup < ms})
    return sorted(out, key=lambda x: -x["score"])


def tier(s):
    return ("Very hard to find", "#b42318") if s >= 2 else ("Hard to find", "#d97706") if s >= 1.3 else ("Typical", "#8a8a84") if s >= .75 else ("Easy to find", "#1a7f37")


def deals(idx):
    out = [{"id": iid, **d} for iid, it in idx["items"].items() if idx["sets"][it["set"]].get("current") for d in it.get("deals") or []]
    best = {}
    for d in sorted(out, key=lambda d: -d["below"]):
        best.setdefault(d["id"], d)   # one deal per item
    return sorted(best.values(), key=lambda d: -d["below"])


def most_sold(idx, sold, today):
    start = (date.fromisoformat(today) - timedelta(days=7)).isoformat()
    out = []
    for iid, weeks in sold.items():
        if iid not in idx["items"]:
            continue
        n = sum(w.get("count") or 0 for w in weeks if (w.get("end") or w["date"]) >= start)
        if n:
            out.append({"id": iid, "n": n, "price": weeks[-1].get("median")})
    return sorted(out, key=lambda x: -x["n"])


def thumb(idx, iid):
    img = idx["items"][iid].get("image")
    return f'<img src="{esc(PREFIX + img)}" alt="" loading="lazy">' if img else '<span class="ph"></span>'


def row(idx, iid, right, sub=""):
    name, _ = label(idx, iid)
    return (f'<li>{thumb(idx, iid)}<span class="nm"><b>{esc(name)}</b><span class="tl">{tag(idx, iid)}</span>{f"<small>{sub}</small>" if sub else ""}</span>'
            f'<span class="rt">{right}</span></li>')


def build(idx, hist, sold, prev=None):
    """(html, today, lede as plain text). prev: the previous report's date, for a link back."""
    today = idx.get("updated") or max(h[-1]["date"] for h in hist.values() if h)
    today = today[:10]
    mv = movers(idx, hist, today)
    up, down = [m for m in mv if m["ch"] > 0.02][:5], [m for m in reversed(mv) if m["ch"] < -0.02][:3]
    hard = [r for r in rarity(idx) if r["fewer"] and r["score"] >= 1.3]
    rar = hard[:5]
    dl = deals(idx)[:4]
    ms = most_sold(idx, sold, today)[:5]
    live = [(sid, s) for sid, s in idx["sets"].items() if s.get("current") and s.get("end") and not s.get("group")]
    end = min((s["end"] for _, s in live), default=None)
    left = (date.fromisoformat(end) - date.fromisoformat(today)).days if end else None
    listings = sum((it.get("latest") or {}).get("count") or 0 for it in idx["items"].values())
    sales = sum(x["n"] for x in most_sold(idx, sold, today))
    since = min((m["since"] for m in mv), default=today)
    nice = lambda d: date.fromisoformat(d).strftime("%b %-d")
    week = date.fromisoformat(today).strftime("%B %-d, %Y")

    def pct(v):
        return f'<b class="{"up" if v > 0 else "down"}">{"▲" if v > 0 else "▼"} {abs(v) * 100:.0f}%</b>'

    hero = up[0] if up else None
    hero_line = (f"<b>{esc(label(idx, hero['id'])[0])}</b> led the week, up {hero['ch'] * 100:.0f}% to {usd(hero['to'])}."
                 if hero else "A quiet week: no item moved more than 2%.")
    if rar:
        hero_line += f" <b>{esc(label(idx, rar[0]['id'])[0])}</b> is the hardest to find, with just {rar[0]['sup']} listed."
    if left is not None:
        hero_line += f" {left} days left to get Pokémon in a Happy Meal."

    def mrow(m):
        return row(idx, m["id"], pct(m["ch"]), f"asking {usd(m['from'])} → {usd(m['to'])}")
    falling = f'<p class="sub">Falling</p><ol class="list">{"".join(mrow(m) for m in down)}</ol>' if down else ""
    sections = []
    sections.append(f"""<section class="card"><h2>Biggest movers</h2><p class="q">Change in median asking price, {nice(since)} → {nice(today)}, items with {MIN_LISTINGS}+ listings</p>
      <ol class="list">{"".join(mrow(m) for m in up) or "<li class='none'>Nothing rose more than 2%.</li>"}</ol>
      {falling}</section>""")
    sections.append(f"""<section class="card"><h2>Hardest to find</h2><p class="q">Pricier and fewer listed than the rest of their set. 1.0 is typical.</p>
      <ol class="list">{"".join(row(idx, r["id"], f'<b style="color:{tier(r["score"])[1]}">{r["score"]:.1f}</b><small>{tier(r["score"])[0]}</small>', f"asking {usd(r['price'])} · {r['sup']} listed") for r in rar) or "<li class='none'>Nothing stands out this week.</li>"}</ol></section>""")
    if ms:
        sections.append(f"""<section class="card"><h2>Most sold</h2><p class="q">eBay sales Toy Ticker detected in the last 7 days, and what they sold for</p>
      <ol class="list">{"".join(row(idx, s["id"], f'<b>{s["n"]}</b><small>sold</small>', f"sold for about {usd(s['price'])}" if s.get("price") else "") for s in ms)}</ol></section>""")
    if dl:
        cards = "".join(f"""<a class="deal" href="{esc(aff(d['url'], 'weekly-report'))}" target="_blank" rel="sponsored noopener">
          {f'<img src="{esc(d["image"])}" alt="" referrerpolicy="no-referrer" loading="lazy">' if d.get("image") else ""}
          <b>{esc(label(idx, d['id'])[0])}</b><span>{tag(idx, d['id'], link=False)}</span><span class="dp"><small class="lb">listed at</small> {usd(d['price'])} <em>{round(d['below'] * 100)}% under usual asking</em></span>
          <small>{"free shipping" if not d.get("ship") else f"incl. {usd(d['ship'])} shipping"} · eBay ↗</small></a>""" for d in dl)
        sections.append(f"""<section class="card wide"><h2>Best deals today</h2><p class="q">Listings furthest under the usual asking price, one per item</p>
      <div class="deals">{cards}</div></section>""")

    lede = re.sub(r"<[^>]+>", "", hero_line)
    root = PREFIX or "./"
    back = f'<a href="../{prev}/">← Week of {esc(nice(prev))}</a> · ' if prev else ""
    nav = f'<p class="weeks">{back}<a href="../">All weekly reports</a></p>' if PREFIX else ""
    url = f"{SITE}reports/{today}/"
    page = head(f"Happy Meal toy market report · {week} · Toy Ticker", f"Week of {week}: {lede}", url) + f"""
<body><main>
  <div class="top"><a href="{root}">← Toy Ticker</a><span class="pill">WEEKLY REPORT</span></div>
  <h1>Happy Meal toy market<br>week of {esc(week)}</h1>
  <p class="lede">{hero_line}</p>
  <div class="stats">
    <div><b>{listings:,}</b><small>eBay listings tracked today</small></div>
    <div><b>{sales:,}</b><small>sales detected this week</small></div>
    <div><b>{len(hard)}</b><small>items hard to find right now</small></div>
    {f'<div><b>{left}</b><small>days left of Pokémon in Happy Meals</small></div>' if left is not None else ""}
  </div>
  <p class="legend"><i></i>in Happy Meals now · tap a series tag to see all its prices</p>
  <div class="grid">{"".join(sections)}</div>
  {nav}
  <p class="cta"><a href="{root}">See every price on Toy Ticker</a></p>
  <footer><b>Asking</b> is the median price sellers list at today; <b>sold</b> is what buyers actually paid in sales Toy Ticker detected. Asking usually runs above sold. eBay US, shipping included, updated daily. Deals and links may earn Toy Ticker a commission. Not affiliated with McDonald's.</footer>
</main></body></html>
"""
    return page, today, lede


def head(title, desc, url):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}"><meta property="og:image" content="{SITE}og/site.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{PREFIX}assets/logo.svg" type="image/svg+xml">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>"""


CSS = """
  :root {{ --bg:#fafaf7; --panel:#fff; --text:#1d1d1b; --muted:#6b6b66; --line:#e6e5df; --accent:#d62300; --up:#1a7f37; --down:#b42318;
          --display:"Bricolage Grotesque",-apple-system,sans-serif; --body:Inter,-apple-system,sans-serif; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141413; --panel:#1e1e1c; --text:#f2f1ec; --muted:#a3a29c; --line:#33332f; --up:#4ac26b; --down:#ff7b72; }} }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:var(--body); line-height:1.45; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 20px 16px 48px; }}
  .top {{ display:flex; justify-content:space-between; align-items:center; font-size:14px; }}
  .top a {{ color:var(--accent); font-weight:600; text-decoration:none; }}
  .pill {{ display:inline-block; font-size:12px; font-weight:700; letter-spacing:.06em; color:var(--accent); background:color-mix(in srgb,var(--accent) 10%,transparent); border-radius:999px; padding:3px 10px; }}
  h1 {{ font-family:var(--display); font-size:clamp(28px,5vw,42px); line-height:1.1; margin:14px 0 8px; }}
  .lede {{ font-size:17px; max-width:62ch; margin:0 0 16px; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin:0 0 18px; }}
  .stats div {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:12px 14px; }}
  .stats b {{ display:block; font-family:var(--display); font-size:26px; font-variant-numeric:tabular-nums; }}
  .stats small {{ color:var(--muted); font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px 18px; min-width:0; }}
  .card.wide {{ grid-column:1/-1; }}
  h2 {{ font-family:var(--display); font-size:19px; margin:0 0 2px; }}
  .q {{ color:var(--muted); font-size:13px; margin:0 0 10px; }}
  .sub {{ font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:14px 0 4px; }}
  .list {{ list-style:none; margin:0; padding:0; display:grid; gap:8px; }}
  .list li {{ display:grid; grid-template-columns:40px minmax(0,1fr) auto; gap:10px; align-items:center; }}
  .list li.none {{ display:block; color:var(--muted); font-size:14px; }}
  .list img, .ph {{ width:40px; height:40px; object-fit:contain; border-radius:8px; background:var(--bg); display:block; }}
  .nm b {{ display:block; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .nm small {{ display:block; color:var(--muted); font-size:12px; }}
  .nm .tl {{ display:block; margin:2px 0; }}
  .tag {{ display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:700; line-height:1; padding:3px 7px; margin-right:6px;
          border-radius:999px; background:var(--tb); color:var(--ti); text-decoration:none; white-space:nowrap; vertical-align:1px; }}
  .tag i {{ width:6px; height:6px; border-radius:50%; background:#2fbf71; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) .tag {{ background:var(--tbd); color:var(--tid); }} }}
  .legend {{ font-size:12px; color:var(--muted); margin:-6px 0 14px; }}
  .legend i {{ display:inline-block; width:6px; height:6px; border-radius:50%; background:#2fbf71; margin-right:4px; vertical-align:1px; }}
  .rt {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .rt small {{ display:block; color:var(--muted); font-size:11px; }}
  .up {{ color:var(--up); }} .down {{ color:var(--down); }}
  .deals {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; }}
  .deal {{ display:grid; gap:2px; text-decoration:none; color:inherit; border:1px solid var(--line); border-radius:12px; padding:10px; background:var(--bg); }}
  .deal:hover {{ border-color:var(--accent); }}
  .deal img {{ width:100%; height:120px; object-fit:contain; border-radius:8px; background:#fff; }}
  .dp {{ font-family:var(--display); font-size:20px; font-weight:600; }}
  .dp em {{ font-style:normal; font-size:12px; font-weight:700; color:var(--up); margin-left:6px; }}
  .dp .lb {{ display:inline; font-family:var(--body); font-size:12px; font-weight:500; color:var(--muted); }}
  .deal small {{ color:var(--muted); font-size:12px; }}
  .cta {{ margin:18px 0 0; text-align:center; }}
  .cta a {{ display:inline-block; background:var(--accent); color:#fff; font-weight:600; border-radius:999px; padding:10px 20px; text-decoration:none; }}
  footer {{ margin-top:20px; color:var(--muted); font-size:12px; text-align:center; }}
  .weeks {{ text-align:center; font-size:14px; margin:18px 0 0; }}
  .weeks a, .arch a {{ color:var(--accent); font-weight:600; text-decoration:none; }}
  .arch {{ list-style:none; padding:0; margin:0; display:grid; gap:10px; }}
  .arch li {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }}
  .arch li.new {{ border-color:var(--accent); }}
  .arch a {{ font-family:var(--display); font-size:19px; }}
  .arch p {{ margin:4px 0 0; font-size:14px; }}
""".replace("{{", "{").replace("}}", "}")


def archive(log):
    rows = "".join(f"""<li class="{"new" if i == 0 else ""}"><a href="{e['date']}/">Week of {esc(date.fromisoformat(e['date']).strftime("%B %-d, %Y"))}</a>
      {"<span class='pill'>LATEST</span>" if i == 0 else ""}<p>{esc(e['lede'])}</p></li>""" for i, e in enumerate(log))
    return head("Weekly Happy Meal toy market reports · Toy Ticker",
                "Every week's Happy Meal toy prices on eBay: biggest movers, hardest to find, most sold and best deals.", f"{SITE}reports/") + f"""
<body><main>
  <div class="top"><a href="../">← Toy Ticker</a><span class="pill">WEEKLY REPORTS</span></div>
  <h1>Happy Meal toy market reports</h1>
  <p class="lede">Every Sunday: which toys rose and fell, which are hardest to find, what sold and the best deals, from Toy Ticker's daily eBay prices.</p>
  <ol class="arch">{rows}</ol>
  <footer>eBay US prices, shipping included. Not affiliated with McDonald's.</footer>
</main></body></html>
"""


def main():
    global PREFIX
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "report-preview.html"))
    ap.add_argument("--publish", action="store_true", help="write reports/<date>/ and the archive")
    ap.add_argument("--if-sunday", action="store_true", help="do nothing unless today (UTC) is Sunday")
    a = ap.parse_args()
    if a.if_sunday and datetime.now(timezone.utc).weekday() != 6:
        print("Weekly report: not Sunday, skipped"); return
    idx, hist, sold = load()
    if not a.publish:
        Path(a.out).write_text(build(idx, hist, sold)[0])
        print("wrote", a.out); return
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    PREFIX = "../../"
    day = (idx.get("updated") or "")[:10]
    prev = next((e["date"] for e in log if e["date"] < day), None)
    page, today, lede = build(idx, hist, sold, prev)
    out = ROOT / "reports" / today / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    log = sorted([e for e in log if e["date"] != today] + [{"date": today, "lede": lede}], key=lambda e: e["date"], reverse=True)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n")
    PREFIX = "../"
    (ROOT / "reports" / "index.html").write_text(archive(log))
    print(f"Weekly report: reports/{today}/ ({len(log)} in the archive)")


if __name__ == "__main__":
    main()
