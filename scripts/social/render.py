"""Draw a post's slides as 1080x1350 JPEGs (Instagram's 4:5 portrait), in the site's colours and fonts.

Every number on a slide is a fact's display text from facts.json, looked up by ID; nothing here makes up values.
"""
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from og import DEFAULT, THEMES, Fonts, logo, rgb  # noqa: E402

W, H = 1080, 1350
M = 64                      # side margin
INK, GREY, PANEL = "#1d1d1b", "#6b6b66", (255, 255, 255, 240)
# One series per weekday (see scripts/social/draft.py SCHEDULE): its label on the cover, and a dot colour so
# followers can tell the series apart at a glance.
TOPIC_LABEL = {"weekly_board": "WEEKLY SUMMARY", "card_spotlight": "CARD SPOTLIGHT", "toy_spotlight": "TOY SPOTLIGHT",
               "fast_sellers": "FAST SELLERS", "scarce_finds": "THE RAREST BOX", "set_or_singles": "SET OR SINGLES",
               "guess_price": "GUESS THE PRICE", "after_promo": "AFTER THE PROMO", "doubles": "GOT IT TWICE?", "versus": "VERSUS", "worth_it": "WORTH IT?",
               "countdown": "COUNTDOWN", "deal_check": "DEAL CHECK", "group_chat": "GROUP CHAT", "checklist": "CHECKLIST"}
TOPIC_DOT = {"weekly_board": "#1d1d1b", "card_spotlight": "#2563eb", "toy_spotlight": "#16a34a", "fast_sellers": "#dc2626",
             "scarce_finds": "#7c3aed", "set_or_singles": "#0891b2", "guess_price": "#db2777", "after_promo": "#ca8a04", "doubles": "#0d9488", "versus": "#ea580c", "deal_check": "#059669", "group_chat": "#4f46e5", "checklist": "#0891b2"}
FACT_LABEL = {"ask": "typical asking price", "listings": "listed today", "change": "price change",
              "sold": "typical sold price", "days_to_sell": "typical time to sell",
              "sells_out": "to sell out at this pace", "sold_window": "of sales tracked",
              "singles": "all bought as singles", "complete_set": "for a complete set",
              "end": "last day in restaurants", "days_left": "left in restaurants",
              "ended_on": "promo ended", "days_since": "since the promo ended",
              "markup": "more than buyers pay", "below": "less than buyers paid", "set_saves": "saved with a complete set",
              "breakeven": "break-even buy price after fees and postage"}


def gradient(c1, c2):
    a, b = rgb(c1), rgb(c2)
    small = Image.new("RGB", (W // 4, H // 4))
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            t = min(1, (x / small.width * 0.5 + y / small.height * 0.5) * 1.05)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return small.resize((W, H), Image.BICUBIC)


def trim(ph):
    """Crop a product photo to the product: drop transparent/white margins and the white name label some
    official photos carry (it would be invisible on a white panel anyway)."""
    flat = Image.new("RGB", ph.size, "white")
    flat.paste(ph, mask=ph)
    ink = ImageChops.difference(flat, Image.new("RGB", ph.size, "white")).convert("L").point(lambda v: 255 if v > 40 else 0)
    box = ink.getbbox()
    return ph.crop(box) if box else ph


def wrap(d, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def text_block(d, xy, text, F, max_w, size, weight, fill, max_lines, min_size=28, leading=1.08):
    """Wrap text into at most max_lines, shrinking the font until it fits. Returns the y below the block."""
    x, y = xy
    while True:
        font = F(size, weight)
        lines = wrap(d, text, font, max_w)
        if len(lines) <= max_lines and all(d.textlength(ln, font=font) <= max_w for ln in lines) or size <= min_size:
            break
        size -= 4
    for ln in lines[:max_lines]:
        d.text((x, y), ln, font=font, fill=fill)
        y += int(size * leading)
    return y


def fit_font(d, text, F, max_w, size, weight, min_size=22):
    while size > min_size and d.textlength(text, font=F(size, weight)) > max_w:
        size -= 2
    return F(size, weight)


class Slides:
    def __init__(self, facts, root):
        self.facts = facts
        self.root = Path(root)
        self.F = Fonts(self.root / "assets" / "fonts" / "BricolageGrotesque.ttf")
        self.fx = {f["id"]: f for f in facts["facts"]}
        self.items = {i["id"]: i for i in facts["items"]}
        self.kind_of = {fid: k for i in facts["items"] for k, fid in i["facts"].items()}
        for s in facts["promo"].get("series", []):           # set-level facts (complete set, singles)
            self.kind_of.update({fid: k for k, fid in s["facts"].items()})
        self.kind_of.update(dict(zip(facts["promo"].get("facts", []),
                                     ("ended_on", "days_since") if facts["promo"].get("ended") else ("end", "days_left"))))
        c1, c2, ink = THEMES.get(facts["promo"]["id"], DEFAULT)
        self.c1, self.c2, self.ink = c1, c2, ink
        self.accent = "#d62300" if c1 in ("#ffcb05", "#ffb703") else c1
        self.day = date.fromisoformat(facts["date"]).strftime("%b %-d, %Y")

    # --- shared pieces -------------------------------------------------------------------------
    def canvas(self):
        img = gradient(self.c1, self.c2)
        return img, ImageDraw.Draw(img, "RGBA")

    def header(self, d, n, total):
        logo(d, M, 52, 0.9)
        d.text((M + 72, 81), "Toy Ticker", font=self.F(34, 700), fill=self.ink, anchor="lm")
        d.text((W - M, 81), f"{n} / {total}", font=self.F(28, 600), fill=self.ink, anchor="rm")

    def footer(self, d, text=None, fids=()):
        """Source line; says "asking and sold prices" when the slide shows a sold price."""
        kind = "asking + sold prices" if any(self.kind_of.get(f) == "sold" for f in fids) else "asking prices"
        line = text or f"toy-ticker.github.io  ·  eBay US {kind}, shipping incl.  ·  {self.day.rsplit(',', 1)[0]}"
        d.text((W // 2, H - 48), line, font=fit_font(d, line, self.F, W - 2 * M, 24, 500, 18),
               fill=self.ink, anchor="mm")

    def pill(self, d, x, y, text, dot=None):
        f = self.F(26, 700)
        tw = d.textlength(text, font=f)
        pad = 44 if dot else 0
        light = self.ink == "#ffffff"
        d.rounded_rectangle([x, y, x + tw + 40 + pad, y + 50], radius=25,
                            fill=(255, 255, 255, 70) if light else (0, 0, 0, 30))
        if dot:
            d.ellipse([x + 18, y + 13, x + 42, y + 37], fill=dot, outline="#ffffff", width=3)
        d.text((x + 20 + pad, y + 25), text, font=f, fill=self.ink, anchor="lm")

    def thumb(self, img, d, item, box):
        """Item photo (official toy photo) fitted into box, or a card tile when there's no local photo."""
        x0, y0, x1, y1 = box
        if item.get("image"):
            ph = trim(Image.open(self.root / item["image"]).convert("RGBA"))
            ph.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
            img.paste(ph, (x0 + (x1 - x0 - ph.width) // 2, y0 + (y1 - y0 - ph.height) // 2), ph)
            return
        w = x1 - x0
        cw = int(min(w, (y1 - y0) * 0.72))
        cx0 = x0 + (w - cw) // 2
        d.rounded_rectangle([cx0, y0, cx0 + cw, y1], radius=max(6, cw // 12), fill=self.c1, outline=self.accent,
                            width=max(2, cw // 40))
        size = max(14, cw // 4)
        d.text((cx0 + cw // 2, (y0 + y1) // 2), item["number"], font=self.F(size, 700), fill=INK, anchor="mm")
        if item.get("rarity"):
            d.text((cx0 + cw // 2, y1 - max(10, cw // 8)), item["rarity"].upper(), font=self.F(max(10, cw // 9), 700),
                   fill=INK, anchor="mm")

    def display(self, fid):
        return self.fx[fid]["display"]

    def label(self, fid):
        return FACT_LABEL.get(self.kind_of.get(fid), self.fx[fid]["what"])

    # --- layouts -------------------------------------------------------------------------------
    def cover(self, s, n, total, topic):
        img, d = self.canvas()
        self.header(d, n, total)
        self.pill(d, M, 168, f"{TOPIC_LABEL.get(topic, 'PRICES')} · {self.day.rsplit(',', 1)[0].upper()}",
                  TOPIC_DOT.get(topic))
        y = text_block(d, (M, 250), s["headline"], self.F, W - 2 * M, 112, 700, self.ink, 3, 60, 1.02)
        if s.get("subhead"):
            text_block(d, (M, y + 24), s["subhead"], self.F, W - 2 * M, 44, 500, self.ink, 2, 30)
        picks = [self.items[i] for i in s.get("item_ids", []) if i in self.items][:3]
        if picks:
            top, bot = 830, H - 110
            d.rounded_rectangle([M, top, W - M, bot], radius=32, fill=PANEL)
            col = (W - 2 * M) / len(picks)
            for i, it in enumerate(picks):
                x0 = int(M + i * col)
                self.thumb(img, d, it, (x0 + 30, top + 30, int(x0 + col - 30), bot - 120))
                d.text((x0 + col / 2, bot - 88), it["name"], font=fit_font(d, it["name"], self.F, col - 30, 32, 600),
                       fill=INK, anchor="mm")
                price = "$ ?" if topic == "guess_price" else self.display(it["facts"]["ask"])  # quiz: no spoiler
                d.text((x0 + col / 2, bot - 44), price, font=self.F(38, 700),
                       fill=self.accent, anchor="mm")
        self.footer(d)
        return img

    def ranked_list(self, s, n, total, topic):
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 170), s["headline"], self.F, W - 2 * M, 80, 700, self.ink, 2, 48, 1.04)
        rows = s.get("rows", [])
        top, bot = max(y + 30, 360), H - 110
        d.rounded_rectangle([M, top, W - M, bot], radius=32, fill=PANEL)
        rh = (bot - top - 40) / max(1, len(rows))
        for i, row in enumerate(rows):
            it = self.items[row["item_id"]]
            fids = row.get("fact_ids", [])
            ry = top + 20 + i * rh
            mid = ry + rh / 2
            if i:
                d.line([M + 36, ry, W - M - 36, ry], fill="#e6e5df", width=2)
            d.text((M + 44, mid), f"{i + 1}", font=self.F(52, 700), fill=self.accent, anchor="lm")
            ts = int(min(rh - 28, 130))
            self.thumb(img, d, it, (M + 100, int(mid - ts / 2), M + 100 + ts, int(mid + ts / 2)))
            nx = M + 130 + ts
            big = self.display(fids[0]) if fids else ""
            bf = self.F(56, 700)
            bw = d.textlength(big, font=bf)
            d.text((W - M - 40, mid), big, font=bf, fill=INK, anchor="rm")
            name_w = W - M - 40 - bw - 30 - nx
            d.text((nx, mid - (20 if len(fids) > 1 else 0)), it["name"], font=fit_font(d, it["name"], self.F, name_w, 40, 600),
                   fill=INK, anchor="lm")
            if len(fids) > 1:
                small = f"{self.display(fids[1])}"
                d.text((nx, mid + 26), small, font=fit_font(d, small, self.F, name_w, 28, 500), fill=GREY, anchor="lm")
        self.footer(d, fids=[f for row in rows for f in row.get("fact_ids", [])])
        return img

    def item(self, s, n, total, topic):
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 170), s["headline"], self.F, W - 2 * M, 80, 700, self.ink, 2, 48, 1.04)
        it = self.items[s["item_id"]]
        fids = s.get("fact_ids", [])
        top, bot = max(y + 30, 360), H - 110
        d.rounded_rectangle([M, top, W - M, bot], radius=32, fill=PANEL)
        self.thumb(img, d, it, (M + 60, top + 40, M + 380, top + 400))
        x = M + 420
        d.text((x, top + 70), it["name"], font=fit_font(d, it["name"], self.F, W - M - 40 - x, 48, 700), fill=INK)
        if fids:
            d.text((x, top + 150), self.display(fids[0]), font=fit_font(d, self.display(fids[0]), self.F, W - M - 40 - x, 120, 700),
                   fill=self.accent)
            d.text((x, top + 290), self.label(fids[0]), font=self.F(30, 500), fill=GREY)
        rest = fids[1:3]
        if rest:
            ty = top + 450
            tw = (W - 2 * M - 120 - 30 * (len(rest) - 1)) / len(rest)
            for i, fid in enumerate(rest):
                tx = M + 60 + i * (tw + 30)
                d.rounded_rectangle([tx, ty, tx + tw, ty + 170], radius=22, fill="#f4f3ee")
                d.text((tx + 30, ty + 30), self.display(fid), font=fit_font(d, self.display(fid), self.F, tw - 60, 56, 700), fill=INK)
                d.text((tx + 30, ty + 115), self.label(fid), font=fit_font(d, self.label(fid), self.F, tw - 60, 28, 500), fill=GREY)
        if s.get("note"):
            text_block(d, (M + 60, bot - 190), s["note"], self.F, W - 2 * M - 120, 38, 500, INK, 3, 26)
        self.footer(d, fids=fids)
        return img

    def highlight(self, s, n, total, topic):
        """One takeaway: a headline, one big number (optionally a second), photos, a short note, centred in the panel."""
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 170), s["headline"], self.F, W - 2 * M, 84, 700, self.ink, 2, 52, 1.04)
        fids = s.get("fact_ids", [])[:2]
        picks = [self.items[i] for i in s.get("item_ids", []) if i in self.items][:3]
        top, bot = max(y + 34, 380), H - 110
        d.rounded_rectangle([M, top, W - M, bot], radius=32, fill=PANEL)
        cx, inner = W // 2, W - 2 * M - 120
        note_h = 150 if s.get("note") else 0
        facts_h = (260 if fids else 0) + (172 if len(fids) > 1 else 0)
        ph = max(0, min(240, bot - note_h - top - 80 - facts_h - 30)) if picks else 0
        if ph < 120:                       # not enough room for photos to read: leave them out
            picks, ph = [], 0
        content = facts_h + (ph + 30 if picks else 0)
        yy = top + max(40, (bot - note_h - top - content) / 2)
        if fids:
            big = self.display(fids[0])
            d.text((cx, yy), big, font=fit_font(d, big, self.F, inner, 168, 700), fill=self.accent, anchor="ma")
            d.text((cx, yy + 190), self.label(fids[0]), font=fit_font(d, self.label(fids[0]), self.F, inner, 36, 500),
                   fill=GREY, anchor="ma")
            yy += 260
        if len(fids) > 1:
            d.line([M + 200, yy, W - M - 200, yy], fill="#e6e5df", width=2)
            prices = {"ask", "sold", "complete_set", "singles"}
            both_prices = {self.kind_of.get(f) for f in fids} <= prices
            second = f"{'vs ' if both_prices else ''}{self.display(fids[1])}"
            d.text((cx, yy + 30), second, font=fit_font(d, second, self.F, inner, 64, 700), fill=INK, anchor="ma")
            d.text((cx, yy + 112), self.label(fids[1]), font=fit_font(d, self.label(fids[1]), self.F, inner, 30, 500),
                   fill=GREY, anchor="ma")
            yy += 172
        if picks:
            col = inner / len(picks)
            for i, it in enumerate(picks):
                x0 = int(M + 60 + i * col)
                self.thumb(img, d, it, (x0 + 20, int(yy + 20), int(x0 + col - 20), int(yy + 20 + ph)))
        if s.get("note"):
            text_block(d, (M + 60, bot - 130), s["note"], self.F, inner, 38, 600, INK, 2, 26)
        self.footer(d, fids=fids)
        return img

    # --- playful layouts --------------------------------------------------------------------
    def hero(self, s, n, total, topic):
        """One big photo, one line, at most one number: built to stop the scroll."""
        img, d = self.canvas()
        self.header(d, n, total)
        it = self.items.get(s.get("item_id"))
        fids = s.get("fact_ids", [])[:1]
        # Space below the photo: headline (up to 2 lines), the number and its label, the note.
        below = 170 + (175 if fids else 0) + (100 if s.get("note") else 0)
        top, bot = 160, H - 110 - below
        d.rounded_rectangle([M, top, W - M, bot], radius=36, fill=PANEL)
        if it:
            self.thumb(img, d, it, (M + 60, top + 36, W - M - 60, bot - 36))
        y = text_block(d, (M, bot + 36), s["headline"], self.F, W - 2 * M, 72, 700, self.ink, 2, 48, 1.04)
        if fids:
            big = self.display(fids[0])
            d.text((M, y + 8), big, font=fit_font(d, big, self.F, W - 2 * M, 100, 700), fill=self.ink)
            d.text((M, y + 122), self.label(fids[0]), font=self.F(30, 500), fill=self.ink)
            y += 175
        if s.get("note"):
            text_block(d, (M, y + 6), s["note"], self.F, W - 2 * M, 34, 500, self.ink, 2, 24)
        self.footer(d, fids=fids)
        return img

    def versus(self, s, n, total, topic):
        """Two items side by side, each with its photo and one number, and a VS badge between them."""
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 165), s["headline"], self.F, W - 2 * M, 78, 700, self.ink, 2, 48, 1.04)
        ids, fids = s.get("item_ids", [])[:2], s.get("fact_ids", [])[:2]
        top = max(y + 30, 360)
        bot = H - (250 if s.get("note") else 130)
        gap = 36
        cw = (W - 2 * M - gap) / 2
        for i, iid in enumerate(ids):
            it = self.items[iid]
            x0 = int(M + i * (cw + gap))
            x1 = int(x0 + cw)
            d.rounded_rectangle([x0, top, x1, bot], radius=30, fill=PANEL)
            self.thumb(img, d, it, (x0 + 30, top + 30, x1 - 30, bot - 230))
            d.text(((x0 + x1) // 2, bot - 200), it["name"], font=fit_font(d, it["name"], self.F, cw - 40, 38, 700),
                   fill=INK, anchor="ma")
            if i < len(fids):
                big = self.display(fids[i])
                d.text(((x0 + x1) // 2, bot - 148), big, font=fit_font(d, big, self.F, cw - 40, 76, 700),
                       fill=self.accent, anchor="ma")
                d.text(((x0 + x1) // 2, bot - 58), self.label(fids[i]),
                       font=fit_font(d, self.label(fids[i]), self.F, cw - 40, 26, 500), fill=GREY, anchor="ma")
        cy = (top + bot) // 2 - 100
        d.ellipse([W // 2 - 56, cy - 56, W // 2 + 56, cy + 56], fill=self.accent, outline="#ffffff", width=8)
        d.text((W // 2, cy), "VS", font=self.F(44, 700), fill="#ffffff", anchor="mm")
        if s.get("note"):
            text_block(d, (M, bot + 30), s["note"], self.F, W - 2 * M, 38, 600, self.ink, 2, 26)
        self.footer(d, fids=fids)
        return img

    def tier_list(self, s, n, total, topic):
        """Items sorted into S/A/B/C rows by asking price; photos only, no numbers."""
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 165), s["headline"], self.F, W - 2 * M, 78, 700, self.ink, 2, 48, 1.04)
        d.text((M, y + 6), "Ranked by typical eBay asking price", font=self.F(28, 500), fill=self.ink)
        its = [self.items[i] for i in s.get("item_ids", []) if i in self.items and "ask" in self.items[i]["facts"]]
        its.sort(key=lambda it: -self.fx[it["facts"]["ask"]]["value"])
        tiers = [("S", "#e11d48"), ("A", "#f97316"), ("B", "#eab308"), ("C", "#22c55e")]
        size = -(-len(its) // len(tiers)) if its else 1
        groups = [its[i * size:(i + 1) * size] for i in range(len(tiers))]
        top, bot = y + 60, H - 110
        rh = (bot - top - 3 * 14) / 4
        for r, ((name, col), grp) in enumerate(zip(tiers, groups)):
            ry = int(top + r * (rh + 14))
            d.rounded_rectangle([M, ry, W - M, ry + rh], radius=22, fill=PANEL)
            d.rounded_rectangle([M, ry, M + 120, ry + rh], radius=22, fill=col)
            d.rectangle([M + 100, ry, M + 120, ry + rh], fill=col)
            d.text((M + 60, ry + rh / 2), name, font=self.F(72, 700), fill="#ffffff", anchor="mm")
            if grp:
                avail = W - M - 24 - (M + 140)
                cell = min(rh - 24, avail / len(grp))
                for k, it in enumerate(grp):
                    x0 = int(M + 140 + k * cell)
                    self.thumb(img, d, it, (x0 + 4, int(ry + (rh - cell) / 2 + 4), int(x0 + cell - 4), int(ry + (rh + cell) / 2 - 4)))
        self.footer(d)
        return img

    def chat(self, s, n, total, topic):
        """The toys' group chat (headline = chat name), all messages, scrolled to the latest if it's long."""
        from chatui import Chat
        img, d = self.canvas()
        self.header(d, n, total)
        x0, y0, x1, y1 = M, 140, W - M, H - 100
        d.rounded_rectangle([x0, y0, x1, y1], radius=36, fill=(255, 255, 255, 250))
        msgs = s.get("messages") or []
        members = list(dict.fromkeys(m["from"] for m in msgs))
        area_h = y1 - (y0 + 130) - 24
        for size in range(34, 21, -2):    # shrink the text until the whole chat fits
            c = Chat(self.root, self.items, self.F, x1 - x0 - 40, size)
            if c.layout(msgs)[1] <= area_h:
                break
        ax = x0 + 30
        head = Chat(self.root, self.items, self.F, x1 - x0 - 40, 34)
        for k, iid in enumerate(members[:5]):
            img.paste(head.avatar(iid), (ax + k * 40, y0 + 26), head.avatar(iid))
        tx = ax + 40 * min(5, len(members)) + 30
        d.text((tx, y0 + 22), s["headline"], font=fit_font(d, s["headline"], self.F, x1 - tx - 30, 38, 800), fill=INK)
        d.text((tx, y0 + 70), f"{len(members)} members", font=self.F(24, 500), fill=GREY)
        top = y0 + 130
        d.line([x0 + 20, top - 16, x1 - 20, top - 16], fill="#e5e5ea", width=2)
        els, total_h = c.layout(msgs)
        area = Image.new("RGBA", (x1 - x0 - 40, y1 - top - 24), (0, 0, 0, 0))
        c.draw(area, els, len(msgs), offset=max(0, total_h - area.height))
        img.paste(area, (x0 + 20, top), area)
        return img

    def checklist(self, s, n, total, topic):
        """Every item in two columns with an empty checkbox, its photo, name and price (sold, else asking)."""
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 160), s["headline"], self.F, W - 2 * M, 70, 700, self.ink, 1, 44)
        if s.get("subhead"):
            y = text_block(d, (M, y + 4), s["subhead"], self.F, W - 2 * M, 32, 500, self.ink, 1, 24)
        rows = s.get("rows") or []
        per_col = -(-len(rows) // 2)
        top, bot, gap = y + 24, H - 110, 12
        rh = (bot - top - (per_col - 1) * gap) / per_col
        cw = (W - 2 * M - 20) / 2
        for k, r in enumerate(rows):
            col, row = divmod(k, per_col)
            x0, y0 = M + col * (cw + 20), top + row * (rh + gap)
            d.rounded_rectangle([x0, y0, x0 + cw, y0 + rh], radius=18, fill=PANEL)
            b = min(34, rh * 0.42)
            d.rounded_rectangle([x0 + 16, y0 + (rh - b) / 2, x0 + 16 + b, y0 + (rh + b) / 2], radius=7,
                                outline="#9ca3af", width=3)
            it = self.items[r["item_id"]]
            tsz = rh - 14
            self.thumb(img, d, it, (int(x0 + 28 + b), int(y0 + 7), int(x0 + 28 + b + tsz), int(y0 + 7 + tsz)))
            name = it["name"].rsplit(" ", 1)[0] if it["name"].endswith((" toy", " card")) else it["name"]
            tx = x0 + 40 + b + tsz
            fid = r["fact_ids"][0]
            price, kind = self.display(fid), self.kind_of.get(fid)
            pf = fit_font(d, price, self.F, 150, 38, 700)
            pw = d.textlength(price, font=pf)
            d.text((x0 + cw - 16, y0 + rh / 2 - 8), price, font=pf, fill=self.accent if kind == "sold" else INK, anchor="rm")
            d.text((x0 + cw - 16, y0 + rh / 2 + 22), "sold" if kind == "sold" else "asking", font=self.F(20, 500),
                   fill=GREY, anchor="rm")
            d.text((tx, y0 + rh / 2), name, font=fit_font(d, name, self.F, cw - (tx - x0) - pw - 30, 32, 600),
                   fill=INK, anchor="lm")
        self.footer(d, fids=[r["fact_ids"][0] for r in rows])
        return img

    def tweet(self, s, n, total, topic):
        """A tweet-style text card from @toy_ticker on a plain light background, like a screenshot people share."""
        from tweet import Tweet
        img = Image.new("RGB", (W, H), "#f2f2f2")
        card = Tweet(self.root, self.items, self.F).card(s, W - 2 * M)
        img.paste(card, ((W - card.width) // 2, (H - card.height) // 2), card)
        return img

    def screenshot(self, s, n, total, topic):
        """A crop of the site's own item page (focus = [top, bottom] fractions of the image) in a rounded frame."""
        img, d = self.canvas()
        self.header(d, n, total)
        y = text_block(d, (M, 165), s["headline"], self.F, W - 2 * M, 78, 700, self.ink, 2, 48, 1.04)
        shot = Image.open(Path(self.folder) / s["image"]).convert("RGB")
        f0, f1 = s["focus"]
        crop = shot.crop((0, int(f0 * shot.height), shot.width, int(f1 * shot.height)))
        top, bot = y + 30, H - (200 if s.get("note") else 110)
        fw, fh = W - 2 * M, bot - top
        r = min(fw / crop.width, fh / crop.height)
        crop = crop.resize((int(crop.width * r), int(crop.height * r)), Image.LANCZOS)
        x = (W - crop.width) // 2
        mask = Image.new("L", crop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, crop.width - 1, crop.height - 1], radius=28, fill=255)
        d.rounded_rectangle([x - 6, top - 6, x + crop.width + 6, top + crop.height + 6], radius=32, fill=(255, 255, 255, 255))
        img.paste(crop, (x, top), mask)
        if s.get("note"):
            text_block(d, (M, top + crop.height + 30), s["note"], self.F, W - 2 * M, 38, 600, self.ink, 2, 26)
        self.footer(d, text="toy-ticker.github.io  ·  screenshot of the site")
        return img

    def cta(self, s, n, total, topic):
        img, d = self.canvas()
        d.text((W - M, 81), f"{n} / {total}", font=self.F(28, 600), fill=self.ink, anchor="rm")
        logo(d, W // 2 - 110, 300, 3.4)
        y = text_block(d, (M, 580), s["headline"], self.F, W - 2 * M, 92, 700, self.ink, 3, 52, 1.04)
        if s.get("subhead"):   # what they'll find on the site: the reason to tap
            y = text_block(d, (M, y + 12), s["subhead"], self.F, W - 2 * M, 36, 500, self.ink, 2, 26)
        d.rounded_rectangle([M + 140, y + 40, W - M - 140, y + 140], radius=50, fill="#ffffff")
        d.text((W // 2, y + 90), "Tap the link in bio", font=self.F(46, 700), fill=INK, anchor="mm")
        d.text((W // 2, y + 196), "toy-ticker.github.io", font=self.F(38, 700), fill=self.ink, anchor="mm")
        d.text((W // 2, y + 246), "Free · no ads · no accounts", font=self.F(28, 500), fill=self.ink, anchor="mm")
        # Credits follow the post: Pokémon promos name The Pokémon Company; card scans come from pokemon.com.
        pokemon = "pokemon" in self.facts["promo"]["id"]
        cards = any((i.get("image") or "").startswith("assets/cards/") for i in self.facts["items"])
        for dy, line in ((132, "Not affiliated with McDonald's or The Pokémon Company." if pokemon
                          else "Not affiliated with McDonald's or the brands shown."),
                         (90, "Images: happymeal.com" + (", pokemon.com" if cards else ""))):
            d.text((W // 2, H - dy), line, font=self.F(24, 500), fill=self.ink, anchor="mm")
        self.footer(d, "Prices from eBay US listings; not advice.")
        return img


def render(post, facts, out_dir, root):
    """Write slides/01.jpg ... to out_dir. Returns the file paths."""
    out = Path(out_dir) / "slides"
    out.mkdir(parents=True, exist_ok=True)
    S = Slides(facts, root)
    S.folder = Path(out_dir)
    slides = post["slides"]
    paths = []
    for n, s in enumerate(slides, 1):
        img = getattr(S, s["layout"])(s, n, len(slides), post.get("topic"))
        p = out / f"{n:02d}.jpg"
        img.convert("RGB").save(p, "JPEG", quality=90, optimize=True, progressive=True)
        paths.append(p)
    return paths
