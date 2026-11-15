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
TOPIC_LABEL = {"weekly_board": "THIS WEEK'S PRICES", "worth_it": "WORTH IT?", "countdown": "COUNTDOWN"}
FACT_LABEL = {"ask": "typical asking price", "listings": "listed today", "change": "price change",
              "sold": "typical sold price", "sold_count": "sold in 30 days", "days_to_sell": "typical time to sell"}


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

    def footer(self, d, text=None):
        d.text((W // 2, H - 48), text or f"eBay US asking prices, shipping included · {self.day}",
               font=self.F(24, 500), fill=self.ink, anchor="mm")

    def pill(self, d, x, y, text):
        f = self.F(26, 700)
        tw = d.textlength(text, font=f)
        light = self.ink == "#ffffff"
        d.rounded_rectangle([x, y, x + tw + 40, y + 50], radius=25, fill=(255, 255, 255, 70) if light else (0, 0, 0, 30))
        d.text((x + 20, y + 25), text, font=f, fill=self.ink, anchor="lm")

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
        self.pill(d, M, 168, f"{TOPIC_LABEL.get(topic, 'PRICES')} · {self.day.rsplit(',', 1)[0].upper()}")
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
                d.text((x0 + col / 2, bot - 44), self.display(it["facts"]["ask"]), font=self.F(38, 700),
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
        self.footer(d)
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
        self.footer(d)
        return img

    def cta(self, s, n, total, topic):
        img, d = self.canvas()
        d.text((W - M, 81), f"{n} / {total}", font=self.F(28, 600), fill=self.ink, anchor="rm")
        logo(d, W // 2 - 110, 300, 3.4)
        y = text_block(d, (M, 600), s["headline"], self.F, W - 2 * M, 92, 700, self.ink, 3, 52, 1.04)
        d.rounded_rectangle([M + 140, y + 50, W - M - 140, y + 150], radius=50, fill="#ffffff")
        d.text((W // 2, y + 100), "Link in bio", font=self.F(48, 700), fill=INK, anchor="mm")
        d.text((W // 2, y + 210), "toy-ticker.github.io", font=self.F(34, 600), fill=self.ink, anchor="mm")
        d.text((W // 2, y + 260), "Free · no ads · no accounts", font=self.F(30, 500), fill=self.ink, anchor="mm")
        self.footer(d, "Not affiliated with McDonald's. Prices from eBay US listings; not advice.")
        return img


def render(post, facts, out_dir, root):
    """Write slides/01.jpg ... to out_dir. Returns the file paths."""
    out = Path(out_dir) / "slides"
    out.mkdir(parents=True, exist_ok=True)
    S = Slides(facts, root)
    slides = post["slides"]
    paths = []
    for n, s in enumerate(slides, 1):
        img = getattr(S, s["layout"])(s, n, len(slides), post.get("topic"))
        p = out / f"{n:02d}.jpg"
        img.convert("RGB").save(p, "JPEG", quality=90, optimize=True, progressive=True)
        paths.append(p)
    return paths
