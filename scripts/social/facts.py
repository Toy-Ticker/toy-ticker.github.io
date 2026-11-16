"""Pick this week's postable facts from Toy Ticker's data. No AI here: every number a post may use comes from this file.

Reads data/index.json, data/series/<id>.json and data/config.json for the series in restaurants now and returns
facts.json: a flat list of numbered facts ("f12": Pikachu card's typical asking price is $12.99), the items they
belong to, ready-made rankings, and the topics of recent posts so the writer doesn't repeat itself.
"""
import json
from datetime import date, timedelta
from pathlib import Path

# Days the price rules changed (e.g. Nov 14: unreported shipping counts as paid). Price changes are never
# measured across one of these, so a rule change can't show up as a market move.
RULE_CHANGES = ["2026-11-14"]
MIN_LISTINGS = 5        # thinner markets than this don't make rankings
MIN_CHANGE_DAYS = 3     # a "change" needs at least this many days between the two prices
MIN_CHANGE = 0.10       # risers/fallers move at least 10%
SPOTLIGHTS = {"card_spotlight", "toy_spotlight", "guess_price"}   # topics that feature one item


def money(v):
    return f"${v:,.2f}"


def pct(v):
    return f"{'+' if v >= 0 else '-'}{abs(v) * 100:.0f}%"


def days(n):
    return f"{n} day{'s' if n != 1 else ''}"


def short_date(iso):
    return date.fromisoformat(iso).strftime("%b %-d")


def load(root, rel):
    return json.loads((Path(root) / rel).read_text())


def current_series(config, today):
    """Series in restaurants on `today`, plus the group that shows them as one (if any)."""
    live = [s for s in config["series"] if s.get("current") or (s.get("end") and s["start"] <= today <= s["end"])]
    ids = {s["id"] for s in live}
    group = next((g for g in config.get("groups", []) if ids & set(g["members"])), None)
    return live, group


def change(history, today):
    """Price change over the last week (or as far back as allowed), never across a rule change.
    Returns (fraction, base_date) or None."""
    pts = [p for p in history if p.get("median") is not None and p.get("count", 0) >= MIN_LISTINGS]
    if len(pts) < 2:
        return None
    last = pts[-1]
    floor = max([d for d in RULE_CHANGES if d <= last["date"]], default="0000")
    week_ago = (date.fromisoformat(last["date"]) - timedelta(days=7)).isoformat()
    base = next((p for p in pts if p["date"] >= max(floor, week_ago)), None)
    if not base or (date.fromisoformat(last["date"]) - date.fromisoformat(base["date"])).days < MIN_CHANGE_DAYS:
        return None
    return last["median"] / base["median"] - 1, base["date"]


class Facts:
    def __init__(self):
        self.list = []

    def add(self, about, what, value, display):
        fid = f"f{len(self.list) + 1}"
        self.list.append({"id": fid, "about": about, "what": what, "value": value, "display": display})
        return fid


def build(root, today=None, social_dir="social", series=None):
    root = Path(root)
    index = load(root, "data/index.json")
    config = load(root, "data/config.json")
    today = today or index["updated"][:10]
    if series:   # a past (or any) series by id, e.g. for an "After the promo" post
        live = [s for s in config["series"] if s["id"] == series]
        group = next((g for g in config.get("groups", []) if series in g["members"] and len(g["members"]) == 1), None)
        if not live:
            raise SystemExit(f"Unknown series {series!r}")
    else:
        live, group = current_series(config, today)
    if not live:
        raise SystemExit("No series in restaurants today; nothing to post about.")
    F = Facts()
    items, kinds = [], {}

    end = max(s["end"] for s in live)
    days_left = (date.fromisoformat(end) - date.fromisoformat(today)).days
    ended = days_left < 0
    promo = {
        "id": group["id"] if group else live[0]["id"],
        "name": group["name"] if group else live[0]["name"],
        "description": group["description"] if group else live[0]["description"],
        "start": min(s["start"] for s in live), "end": end,
        "ended": ended,
        "facts": [F.add(None, "last day in restaurants", end, short_date(end)),
                  F.add(None, "days since the promo ended", -days_left, f"{-days_left} days") if ended else
                  F.add(None, "days left in restaurants", days_left, f"{days_left} days")],
    }

    for s in live:
        sid, kind = s["id"], s.get("kind", "toys")
        kinds[sid] = kind
        word = "card" if kind == "cards" else "toy"
        series_data = load(root, f"data/series/{sid}.json")
        sets = index["sets"][sid]
        ins = sets.get("insights") or {}
        sales = (ins.get("sales") or {}).get("items", {})
        # Days of sales behind the sold counts: the sales window, but no longer than tracking has run
        # (same as the site's supplyDays()).
        span = None
        if ins.get("since"):
            span = min((ins.get("sales") or {}).get("window", 30),
                       (date.fromisoformat(sets.get("lastUpdate") or ins["since"]) - date.fromisoformat(ins["since"])).days)
        singles = 0.0
        for c in s["items"]:
            iid = f"{sid}-{c['number']}"
            ix = index["items"].get(iid, {})
            latest = ix.get("latest") or {}
            if latest.get("median") is None:
                continue
            name = f"{c['name']} {word}" if group else c["name"]
            fid = {"ask": F.add(iid, "typical eBay asking price today, shipping included", latest["median"], money(latest["median"])),
                   "listings": F.add(iid, "listings priced today", latest["count"],
                                         f"{latest['count']} listing{'s' if latest['count'] != 1 else ''}")}
            singles += latest["median"]
            ch = change(series_data["history"].get(iid, []), today)
            if ch:
                fid["change"] = F.add(iid, f"change in asking price since {short_date(ch[1])}", round(ch[0], 4),
                                      f"{pct(ch[0])} since {short_date(ch[1])}")
            markup = None
            sold = [p for p in series_data.get("sold", {}).get(iid, []) if p.get("count", 0) >= MIN_LISTINGS]
            if sold:
                p = sold[-1]
                fid["sold"] = F.add(iid, f"typical sold price, {short_date(p['date'])} to {short_date(p['end'])}",
                                    p["median"], money(p["median"]))
                # Deal check: how far today's typical asking price sits above (or below) what buyers paid.
                gap = round(latest["median"] - p["median"], 2)
                markup = gap
                if gap > 0:
                    fid["markup"] = F.add(iid, "typical asking price minus typical sold price (how much more sellers ask than buyers pay)",
                                          gap, money(gap))
                elif gap < 0:
                    fid["below"] = F.add(iid, "typical sold price minus typical asking price (buyers paid more than today's asks)",
                                          -gap, money(-gap))
            sl = sales.get(iid)
            sells = None
            if sl and sl.get("sold", 0) >= MIN_LISTINGS and span and span >= MIN_CHANGE_DAYS:
                fid["sold_count"] = F.add(iid, f"in the last {days(span)}", sl["sold"], f"{sl['sold']} sold")
                fid["sold_window"] = F.add(iid, "days of sales those counts cover", span, days(span))
                fid["days_to_sell"] = F.add(iid, "typical days to sell", sl["days"], days(sl["days"]))
                # "Sells out in": today's listings / sales per day, as the site's market read. Not rated when the
                # search only follows a small sample of the item's listings (supply estimate 5x+ the count).
                supply = latest.get("supply") or 0
                if latest["count"] >= MIN_LISTINGS and not (supply and latest["count"] / supply < 0.2):
                    d = sells = latest["count"] / (sl["sold"] / span)
                    fid["sells_out"] = F.add(iid, "days today's listings would last at the recent sales pace", round(d, 1),
                                             "60+ days" if d > 60 else f"about {days(max(1, round(d)))}")
            # A local photo only (official toy photo or official card scan), never a seller's eBay photo.
            local = next((p for p in (ix.get("image", ""), f"assets/cards/{iid}.png")
                          if p and not p.startswith("http") and (root / p).exists()), None)
            items.append({
                "id": iid, "name": name, "series": sid, "kind": kind, "number": c["number"],
                "rarity": ix.get("rarity") or ("Holo" if c.get("holo") else None),
                "image": local,
                "listings": latest["count"], "ask": latest["median"],
                "change": ch[0] if ch else None, "sold_count": (sl or {}).get("sold"), "sells_out": sells,
                "markup": markup,
                "facts": fid,
            })
        # Complete set vs singles.
        full = [p for p in (sets.get("fullSet") or {}).get("history", []) if p.get("median") is not None]
        set_facts = {"singles": F.add(sid, f"all {len(s['items'])} {word}s bought as singles (sum of typical asking prices)",
                                      round(singles, 2), money(singles))}
        if full and full[-1].get("count", 0) >= 3:
            set_facts["complete_set"] = F.add(sid, "typical asking price for a complete set listing",
                                              full[-1]["median"], money(full[-1]["median"]))
            saved = round(singles - full[-1]["median"], 2)
            if saved > 0:
                set_facts["set_saves"] = F.add(sid, "saved by buying a complete set instead of all singles (singles sum minus set price)",
                                               saved, money(saved))
        promo.setdefault("series", []).append({"id": sid, "name": s["name"], "kind": kind, "size": len(s["items"]),
                                               "facts": set_facts})

    def top(rows, key, n=5, reverse=True):
        return [r["id"] for r in sorted(rows, key=key, reverse=reverse)[:n]]

    ok = [r for r in items if r["listings"] >= MIN_LISTINGS]
    rankings = {}
    for sid, kind in kinds.items():
        rankings[f"most_valuable_{kind}"] = top([r for r in ok if r["series"] == sid], lambda r: r["ask"])
    moved = [r for r in ok if r["change"] is not None]
    rankings["risers"] = top([r for r in moved if r["change"] >= MIN_CHANGE], lambda r: r["change"])
    rankings["fallers"] = top([r for r in moved if r["change"] <= -MIN_CHANGE], lambda r: r["change"], reverse=False)
    rankings["most_sold"] = top([r for r in ok if r["sold_count"]], lambda r: r["sold_count"])
    # Daily series: fastest to sell out, fewest listed, and spotlight picks not featured in recent posts.
    # Playful angles: the toys everyone has (most listed = most duplicates), card vs toy of the same Pokémon,
    # and every item by asking price (for tier lists and versus pairs).
    rankings["most_listed"] = top([r for r in ok if r["kind"] != "cards"], lambda r: r["listings"])
    base = lambda r: r["name"].rsplit(" ", 1)[0] if r["name"].endswith((" card", " toy")) else r["name"]  # noqa: E731
    cards_by = {base(r): r["id"] for r in ok if r["kind"] == "cards"}
    rankings["card_toy_pairs"] = [[cards_by[base(r)], r["id"]] for r in ok if r["kind"] != "cards" and base(r) in cards_by]
    rankings["by_price"] = top(ok, lambda r: r["ask"], n=len(ok))
    rankings["fast_sellers"] = top([r for r in items if r["sells_out"]], lambda r: r["sells_out"], reverse=False)
    # Deal check: biggest gap between asking and sold (sellers ask most over what buyers pay), and the smallest.
    priced = [r for r in ok if r["markup"] is not None]
    rankings["biggest_markup"] = top(priced, lambda r: r["markup"])
    rankings["smallest_markup"] = top(priced, lambda r: r["markup"], reverse=False)
    rankings["fewest_listings"] = top([r for r in items if r["listings"] >= 1], lambda r: r["listings"], reverse=False)
    recent = recent_posts(root / social_dir)
    featured = {i for p in recent if p.get("topic") in SPOTLIGHTS for i in p.get("items", [])}
    for kind in ("cards", "toys"):
        pool = [r for r in ok if r["kind"] == kind and r["image"] and r["id"] not in featured]
        rankings[f"spotlight_{kind}"] = top(pool, lambda r: (r["sold_count"] or 0, r["ask"]), n=8)

    return {
        "date": today,
        "source": "eBay US Buy It Now asking prices, shipping included; sold prices from listings that ended",
        "promo": promo,
        "facts": F.list,
        "items": [{k: v for k, v in r.items() if k not in ("ask", "change", "sold_count", "listings", "sells_out")}
                  for r in items],
        "rankings": rankings,
        "recent_posts": recent,
    }


def recent_posts(folder, n=8):
    """Topic and headlines of the last n drafted posts, newest first."""
    out = []
    for p in sorted(Path(folder).glob("*/post.json"), reverse=True)[:n]:
        try:
            post = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        slides = post.get("slides", [])
        items = {i for s in slides for i in [s.get("item_id"), *s.get("item_ids", []),
                                             *(r.get("item_id") for r in s.get("rows", []))] if i}
        out.append({"date": p.parent.name[:10], "topic": post.get("topic"),
                    "headlines": [s.get("headline") for s in slides], "items": sorted(items)})
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(build(Path(__file__).resolve().parents[2], *(sys.argv[1:2])), indent=1, ensure_ascii=False))
