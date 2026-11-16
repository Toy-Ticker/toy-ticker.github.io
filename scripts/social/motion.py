"""Animated Reel (reel.mp4, 1080x1920) for a drafted post: every slide becomes a full-screen scene with motion
(words popping in, toys sliding in, a VS badge that slams, prices counting up) and scenes push up into each other.

Same rule as the slides: every number shown is a fact's display text from facts.json (a count-up only animates
towards that exact value). Instagram covers the top ~250 px and bottom ~340 px of a Reel with its own buttons,
so content stays between those.
"""
import hashlib
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from og import DEFAULT, THEMES, Fonts, logo  # noqa: E402
from render import FACT_LABEL, TOPIC_DOT, TOPIC_LABEL, trim, wrap  # noqa: E402

W, H = 1080, 1920
FPS = 30
M = 72                       # side margin
TOP, BOTTOM = 290, 1560      # safe area for content
INK, GREY, WHITE = "#1d1d1b", "#6b6b66", (255, 255, 255, 245)
PUSH = 0.24                  # seconds for the transition between scenes

# Visual styles, rotated from post to post (like the music) so Reels don't all look alike. "clean" is the
# series colours below; the others bring their own type, colours and treatment. System fonts are only used to
# draw pixels on this Mac; they aren't shipped in the repo.
STYLES = {
    "clean": {},
    # Looks like a Reel made in the Instagram app: toy photo on a blurred wash, captions on white labels.
    "native": {"native": True, "font": "/System/Library/Fonts/SFNS.ttf", "bg": ("#2b2b2b", "#0f0f0f"),
               "ink": "#ffffff", "accent": "#facc15"},
    "sticker": {"font": "/System/Library/Fonts/SFNSRounded.ttf", "bg": ("#fff4e0", "#ffd6e8"), "dots": "#f3c6d9",
                "ink": "#1e1b4b", "accent": "#e11d74", "stroke": 9, "stroke_fill": "#ffffff", "shadow": "#1e1b4b",
                "panel": "#ffffff", "border": "#1e1b4b", "p_ink": "#1e1b4b", "p_grey": "#6b7280", "photo": "sticker",
                "rotate": False},
    "meme": {"font": "/System/Library/Fonts/Supplemental/Impact.ttf", "upper": True, "bg": ("#0a0a0a", "#2a2a2a"),
             "ink": "#ffffff", "accent": "#facc15", "stroke": 7, "stroke_fill": "#000000",
             "panel": "#141414", "border": "#ffffff", "p_ink": "#ffffff", "p_grey": "#d4d4d4", "rotate": False},
}

# Each series has its own Reel look (gradient start, end, text colour, number colour, transition), so followers
# can tell Monday from Thursday at a glance and back-to-back Reels don't look the same. Slides keep the
# promo's own colours.
LOOKS = {
    "card_spotlight": ("#1e3a8a", "#3b82f6", "#ffffff", "#1d4ed8", "left"),
    "doubles":        ("#0f766e", "#2dd4bf", "#ffffff", "#0f766e", "up"),
    "versus":         ("#c2410c", "#fbbf24", "#1d1d1b", "#c2410c", "zoom"),
    "scarce_finds":   ("#3b0764", "#8b5cf6", "#ffffff", "#6d28d9", "zoom"),
    "set_or_singles": ("#155e75", "#22d3ee", "#ffffff", "#0e7490", "left"),
    "guess_price":    ("#9d174d", "#f472b6", "#ffffff", "#be185d", "zoom"),
    "weekly_board":   ("#111827", "#4b5563", "#ffffff", "#d62300", "up"),
    "deal_check":     ("#064e3b", "#34d399", "#ffffff", "#047857", "left"),
    "toy_spotlight":  ("#b45309", "#facc15", "#1d1d1b", "#b45309", "up"),
    "group_chat":     ("#312e81", "#818cf8", "#ffffff", "#4f46e5", "up"),
    "checklist":      ("#164e63", "#22d3ee", "#ffffff", "#0e7490", "up"),
}


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def ease_out(p):
    return 1 - (1 - p) ** 3


def back_out(p, s=1.9):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


NUM = re.compile(r"(\$?)(\d[\d,]*)(\.\d+)?")


def count_up(display, p):
    """The display text with its first number animated from 0 to its value (p in 0..1); exact at p=1."""
    m = NUM.search(display)
    if not m or p >= 1:
        return display
    whole = m.group(2).replace(",", "")
    dec = len(m.group(3)) - 1 if m.group(3) else 0
    v = float(whole + (m.group(3) or "")) * ease_out(p)
    s = f"{v:,.{dec}f}" if "," in m.group(2) else f"{v:.{dec}f}"
    return display[:m.start()] + m.group(1) + s + display[m.end():]


class Reel:
    def __init__(self, post, facts, root):
        from extras import backdrop
        self.post, self.facts, self.root = post, facts, Path(root)
        self.F = Fonts(self.root / "assets" / "fonts" / "BricolageGrotesque.ttf")
        c1, c2, ink = THEMES.get(facts["promo"]["id"], DEFAULT)
        accent, self.transition = ("#d62300" if c1 in ("#ffcb05", "#ffb703") else c1), "up"
        if post.get("topic") in LOOKS:
            c1, c2, ink, accent, self.transition = LOOKS[post["topic"]]
        self.style_name = post.get("reel_style") if post.get("reel_style") in STYLES else "clean"
        st = self.st = STYLES[self.style_name]
        self.F0 = self.F                       # the site's font, kept for the chat UI
        if st.get("font") and Path(st["font"]).exists():
            self.F = Fonts(Path(st["font"]))
        if st.get("bg"):
            c1, c2 = st["bg"]
            ink, accent = st["ink"], st["accent"]
        self.ink, self.accent = ink, accent
        self.p_fill, self.p_ink, self.p_grey = st.get("panel", WHITE), st.get("p_ink", INK), st.get("p_grey", GREY)
        self.bg = backdrop(c1, c2)
        if st.get("dots"):                     # scrapbook paper: a soft dot grid
            dd = ImageDraw.Draw(self.bg)
            for yy in range(20, H, 46):
                for xx in range(20 + (yy // 46 % 2) * 23, W, 46):
                    dd.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=st["dots"])
        self.fx = {f["id"]: f for f in facts["facts"]}
        self.items = {i["id"]: i for i in facts["items"]}
        self.kind_of = {fid: k for i in facts["items"] for k, fid in i["facts"].items()}
        for s in facts["promo"].get("series", []):
            self.kind_of.update({fid: k for k, fid in s["facts"].items()})
        self._photo, self._txt = {}, {}
        self.scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    # --- cached pieces -------------------------------------------------------------------------
    def photo(self, iid, size):
        size = max(8, int(size) // 4 * 4)
        key = (iid, size)
        if key not in self._photo:
            it = self.items.get(iid) or {}
            if not it.get("image"):
                self._photo[key] = None
            else:
                base = self._photo.get((iid, "raw"))
                if base is None:
                    base = self._photo[(iid, "raw")] = trim(Image.open(self.root / it["image"]).convert("RGBA"))
                r = size / max(base.size)
                im = base.resize((max(1, int(base.width * r)), max(1, int(base.height * r))), Image.LANCZOS)
                if self.st.get("photo") == "sticker":
                    im = self.stickerize(im, iid)
                self._photo[key] = im
        return self._photo[key]

    def stickerize(self, im, iid):
        """Die-cut sticker: thick white outline, hard drop shadow, a small tilt that's the same for each item."""
        from PIL import ImageFilter
        o = max(4, im.width // 22)
        pad = o * 3
        a = Image.new("L", (im.width + 2 * pad, im.height + 2 * pad), 0)
        a.paste(im.getchannel("A"), (pad, pad))
        edge = a.filter(ImageFilter.MaxFilter(2 * (o // 2) + 1)).filter(ImageFilter.MaxFilter(2 * (o // 2) + 1))
        out = Image.new("RGBA", a.size, (0, 0, 0, 0))
        out.paste(self.st.get("shadow", "#000000"), (o // 2 + 4, o // 2 + 6), edge)
        out.paste("#ffffff", (0, 0), edge)
        out.paste(im, (pad, pad), im)
        tilt = (int(hashlib.md5(iid.encode()).hexdigest(), 16) % 13) - 6
        return out.rotate(tilt, resample=Image.BICUBIC, expand=True)

    def text_img(self, text, size, weight, fill):
        if self.st.get("upper"):
            text = text.upper()
        key = (text, size, weight, fill)
        if key not in self._txt:
            f = self.F(size, weight)
            # Same box height for every word at a size (ascender to descender), so words share a baseline.
            ascent, descent = f.getmetrics()
            # Text on the background gets the style's outline (and sticker shadow); text on panels doesn't.
            sw = int(self.st.get("stroke", 0) * size / 100) if fill == self.ink and self.st.get("stroke") and size >= 64 else 0
            sh = max(3, size // 16) if sw and self.st.get("shadow") else 0
            l, _, r, _ = self.scratch.textbbox((0, 0), text, font=f, stroke_width=sw)
            im = Image.new("RGBA", (r - l + 8 + sh, ascent + descent + 8 + 2 * sw + sh), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            if sh:
                dr.text((4 - l + sh, 4 + sw + sh), text, font=f, fill=self.st["shadow"], stroke_width=sw,
                        stroke_fill=self.st["shadow"])
            dr.text((4 - l, 4 + sw), text, font=f, fill=fill, stroke_width=sw, stroke_fill=self.st.get("stroke_fill"))
            self._txt[key] = im
        return self._txt[key]

    def label(self, fid):
        return FACT_LABEL.get(self.kind_of.get(fid), self.fx[fid]["what"])

    # --- drawing helpers -------------------------------------------------------------------------
    @staticmethod
    def paste(frame, im, cx, cy, scale=1.0, alpha=1.0):
        """Paste im centred at (cx, cy), scaled and faded."""
        if im is None or scale <= 0.01 or alpha <= 0.01:
            return
        if abs(scale - 1) > 0.01:
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
        if alpha < 0.99:
            a = im.getchannel("A").point(lambda v: int(v * alpha))
            im = im.copy()
            im.putalpha(a)
        frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

    def layout_words(self, text, x, y, max_w, size, weight, max_lines, min_size=48, leading=1.04, center=False):
        """Wrap text (shrinking to fit max_lines); returns [(word, cx, cy, size)] and the y below the block."""
        if self.st.get("upper"):
            text = text.upper()
        while True:
            f = self.F(size, weight)
            lines = wrap(self.scratch, text, f, max_w)
            if len(lines) <= max_lines or size <= min_size:
                break
            size -= 6
        out, sp = [], self.scratch.textlength(" ", font=f)
        for ln in lines[:max_lines]:
            words = ln.split(" ")
            lw = self.scratch.textlength(ln, font=f)
            xx = x + (max_w - lw) / 2 if center else x
            for w_ in words:
                ww = self.scratch.textlength(w_, font=f)
                out.append((w_, xx + ww / 2, y + size * 0.55, size))
                xx += ww + sp
            y += int(size * leading)
        return out, y

    def pop_words(self, frame, words, t, start, weight=800, fill=None, stagger=0.07, dur=0.28):
        for k, (w_, cx, cy, size) in enumerate(words):
            p = prog(t, start + k * stagger, dur)
            if p <= 0:
                continue
            self.paste(frame, self.text_img(w_, size, weight, fill or self.ink), cx, cy, 0.55 + 0.45 * back_out(p), min(1, p * 2))

    def fade_text(self, frame, text, x, y, max_w, size, weight, fill, t, start, center=False, max_lines=2):
        p = ease_out(prog(t, start, 0.3))
        if p <= 0:
            return
        words, _ = self.layout_words(text, x, y + (1 - p) * 30, max_w, size, weight, max_lines, 28, 1.12, center)
        for w_, cx, cy, sz in words:
            self.paste(frame, self.text_img(w_, sz, weight, fill), cx, cy, 1.0, p)

    def panel(self, d, box, radius=34):
        """A card: plain white for clean; outlined with a hard offset shadow for sticker and meme."""
        if self.st.get("border"):
            x0, y0, x1, y1 = box
            if self.st.get("shadow"):
                d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=radius, fill=self.st["shadow"])
            d.rounded_rectangle(box, radius=radius, fill=self.p_fill, outline=self.st["border"], width=6)
        else:
            d.rounded_rectangle(box, radius=radius, fill=WHITE)

    def big_number(self, frame, fid, cx, y, size, t, start, fill=None, max_w=None, prefix=""):
        p = prog(t, start, 0.7)
        if p <= 0:
            return
        txt = prefix + count_up(self.fx[fid]["display"], p)
        final = prefix + self.fx[fid]["display"]
        f = self.F(size, 800)
        while max_w and size > 40 and self.scratch.textlength(final, font=f) > max_w:
            size -= 4
            f = self.F(size, 800)
        pop = 1 + 0.12 * math.sin(math.pi * prog(t, start + 0.7, 0.22))   # a little bump when it lands
        self.paste(frame, self.text_img(txt, size, 800, fill or self.accent), cx, y + size * 0.55, pop, min(1, p * 3))

    # --- scenes: each returns (seconds, draw(t) -> RGB image) ---------------------------------------
    def scene_hook(self, hook):
        ids = (hook.get("item_ids") or [])[:2]

        def draw(t):
            f = self.bg.copy()
            words, end = self.layout_words(hook["text"], M, TOP, W - 2 * M, 170, 800, 3, 84, 1.0)
            for w_, cx, cy, sz in words:      # text is there from the very first frame
                self.paste(f, self.text_img(w_, sz, 800, self.ink), cx, cy)
            pop = back_out(prog(t, 0.05, 0.35))
            size = (600 if len(ids) == 1 else 450) * (0.75 + 0.25 * pop) * (1 + 0.08 * t / 1.6)
            cy = min(BOTTOM - 330, max(1180, end + 50 + 330))
            xs = [W // 2] if len(ids) == 1 else [W // 2 - 255, W // 2 + 255]
            for iid, cx in zip(ids, xs):
                self.paste(f, self.photo(iid, size), cx, cy)
            if len(ids) == 2:
                self.vs(f, W // 2, cy, back_out(prog(t, 0.3, 0.3)))
            return f
        return 1.6, draw

    def vs(self, f, cx, cy, p):
        if p <= 0:
            return
        r = int(64 * max(0.01, p))
        d = ImageDraw.Draw(f)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#dc2626", outline="white", width=8)
        d.text((cx, cy), "VS", font=self.F(max(10, int(58 * p)), 800), fill="white", anchor="mm")

    def scene_cover(self, s):
        ids = s.get("item_ids", [])[:3]
        label = TOPIC_LABEL.get(self.post.get("topic"), "PRICES")
        dot = TOPIC_DOT.get(self.post.get("topic"))

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            pf = self.F(32, 700)
            tw = d.textlength(label, font=pf)
            a = int(255 * ease_out(prog(t, 0, 0.25)))
            d.rounded_rectangle([M, TOP, M + tw + 96, TOP + 60], radius=30, fill=(0, 0, 0, int(a * 0.12)))
            if dot:
                d.ellipse([M + 20, TOP + 16, M + 48, TOP + 44], fill=dot, outline="#ffffff", width=3)
            d.text((M + 66, TOP + 30), label, font=pf, fill=self.ink, anchor="lm")
            words, end = self.layout_words(s["headline"], M, TOP + 110, W - 2 * M, 128, 800, 4, 72)
            self.pop_words(f, words, t, 0.1)
            if s.get("subhead"):
                self.fade_text(f, s["subhead"], M, end + 20, W - 2 * M, 50, 500, self.ink, t, 0.1 + 0.07 * len(words))
            if ids:
                n = len(ids)
                col = (W - 2 * M) / n
                for k, iid in enumerate(ids):
                    p = back_out(prog(t, 0.5 + 0.12 * k, 0.35))
                    self.paste(f, self.photo(iid, min(330, col - 30)), M + col * (k + 0.5), 1310, p)
            return f
        return 2.6, draw

    def scene_hero(self, s):
        iid, fids = s.get("item_id"), s.get("fact_ids", [])[:1]

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            p = ease_out(prog(t, 0, 0.3))
            self.paste(f, self.photo(iid, 560), W // 2, 600, (1.35 - 0.35 * p) * (1 + 0.04 * t), p)
            words, end = self.layout_words(s["headline"], M, 960, W - 2 * M, 88, 800, 2, 56)
            self.pop_words(f, words, t, 0.25, stagger=0.05)
            if fids:
                top = end + 30
                self.panel(d, [M, top, W - M, top + 250])
                self.big_number(f, fids[0], W // 2, top + 20, 140, t, 0.6, max_w=W - 2 * M - 60)
                lp = ease_out(prog(t, 1.0, 0.3))
                self.paste(f, self.text_img(self.label(fids[0]), 38, 500, self.p_grey), W // 2, top + 205, 1, lp)
                end = top + 250
            if s.get("note"):
                self.fade_text(f, s["note"], M, end + 34, W - 2 * M, 50, 700, self.ink, t, 1.5)
            return f
        return 3.0, draw

    def scene_versus(self, s):
        ids, fids = s.get("item_ids", [])[:2], s.get("fact_ids", [])[:2]

        def draw(t):
            f = self.bg.copy()
            words, end = self.layout_words(s["headline"], M, TOP, W - 2 * M, 92, 800, 2, 56)
            self.pop_words(f, words, t, 0, stagger=0.05)
            top = max(end + 40, 560)
            gap, cw = 34, (W - 2 * 56 - 34) / 2
            ph = 1040 - top + 300
            bot = top + 760
            # panels slide in from the sides
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dl = ImageDraw.Draw(layer)
            for i, iid in enumerate(ids[:2]):
                p = ease_out(prog(t, 0.25 + 0.08 * i, 0.4))
                off = (1 - p) * (W * 0.7) * (-1 if i == 0 else 1)
                x0 = 56 + i * (cw + gap) + off
                x1 = x0 + cw
                self.panel(dl, [x0, top, x1, bot], radius=32)
                it = self.items[iid]
                self.paste(layer, self.photo(iid, cw - 80), (x0 + x1) / 2, top + 40 + (cw - 80) / 2)
                name = self.text_img(it["name"], 40, 700, self.p_ink)
                self.paste(layer, name, (x0 + x1) / 2, bot - 230, min(1, (cw - 30) / name.width))
                if i < len(fids):
                    self.big_number(layer, fids[i], (x0 + x1) / 2, bot - 190, 84, t, 0.85 + 0.1 * i, max_w=cw - 40)
                    lab = self.text_img(self.label(fids[i]), 28, 500, self.p_grey)
                    self.paste(layer, lab, (x0 + x1) / 2, bot - 50, min(1, (cw - 30) / lab.width),
                               ease_out(prog(t, 1.2, 0.3)))
            f.paste(layer, (0, 0), layer)
            self.vs(f, W // 2, top + 40 + (cw - 80) / 2, back_out(prog(t, 0.6, 0.28)))
            if s.get("note"):
                self.fade_text(f, s["note"], M, bot + 36, W - 2 * M, 52, 700, self.ink, t, 1.7)
            return f, (0.62, 0.2)   # shake when the VS lands
        return 3.2, draw

    def scene_highlight(self, s):
        fids, ids = s.get("fact_ids", [])[:2], s.get("item_ids", [])[:3]

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            words, end = self.layout_words(s["headline"], M, TOP, W - 2 * M, 96, 800, 3, 56)
            self.pop_words(f, words, t, 0, stagger=0.05)
            top = end + 40
            self.panel(d, [M, top, W - M, top + 760])
            if fids:
                self.big_number(f, fids[0], W // 2, top + 50, 190, t, 0.4, max_w=W - 2 * M - 60)
                self.paste(f, self.text_img(self.label(fids[0]), 40, 500, self.p_grey), W // 2, top + 290, 1,
                           ease_out(prog(t, 0.9, 0.3)))
            if len(fids) > 1:
                p = ease_out(prog(t, 1.1, 0.35))
                txt = "vs " + self.fx[fids[1]]["display"]
                self.paste(f, self.text_img(txt, 92, 800, self.p_ink), W // 2 + (1 - p) * 500, top + 400, 1, p)
                self.paste(f, self.text_img(self.label(fids[1]), 36, 500, self.p_grey), W // 2 + (1 - p) * 500, top + 480, 1, p)
            for k, iid in enumerate(ids):
                col = (W - 2 * M - 120) / max(1, len(ids))
                self.paste(f, self.photo(iid, min(180, col - 20)), M + 60 + col * (k + 0.5), top + 640,
                           back_out(prog(t, 1.4 + 0.1 * k, 0.3)))
            if s.get("note"):
                self.fade_text(f, s["note"], M, top + 800, W - 2 * M, 52, 700, self.ink, t, 1.9)
            return f
        return 3.2, draw

    def scene_tier_list(self, s):
        its = [i for i in s.get("item_ids", []) if i in self.items and "ask" in self.items[i]["facts"]]
        its.sort(key=lambda i: -self.fx[self.items[i]["facts"]["ask"]]["value"])
        tiers = [("S", "#e11d48"), ("A", "#f97316"), ("B", "#eab308"), ("C", "#22c55e")]
        size = -(-len(its) // 4) if its else 1
        groups = [its[i * size:(i + 1) * size] for i in range(4)]
        dur = 1.0 + 0.09 * len(its) + 0.9

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            words, end = self.layout_words(s["headline"], M, TOP, W - 2 * M, 88, 800, 2, 56)
            self.pop_words(f, words, t, 0, stagger=0.05)
            top = end + 40
            rh = (BOTTOM - top - 3 * 16) / 4
            k = 0
            for r, ((name, col), grp) in enumerate(zip(tiers, groups)):
                p = ease_out(prog(t, 0.3 + 0.08 * r, 0.3))
                off = (1 - p) * -W
                ry = top + r * (rh + 16)
                self.panel(d, [M + off, ry, W - M + off, ry + rh], radius=24)
                d.rounded_rectangle([M + off, ry, M + 130 + off, ry + rh], radius=24, fill=col)
                d.rectangle([M + 110 + off, ry, M + 130 + off, ry + rh], fill=col)
                d.text((M + 65 + off, ry + rh / 2), name, font=self.F(80, 800), fill="#ffffff", anchor="mm")
                if grp:
                    avail = W - M - 24 - (M + 150)
                    cell = min(rh - 20, avail / len(grp))
                    for j, iid in enumerate(grp):
                        q = back_out(prog(t, 0.8 + 0.09 * (k + j), 0.28))
                        self.paste(f, self.photo(iid, cell - 12), M + 150 + cell * (j + 0.5), ry + rh / 2, q)
                k += len(grp)
            return f
        return dur, draw

    def scene_cta(self, s):
        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            p = back_out(prog(t, 0, 0.4))
            tile = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
            logo(ImageDraw.Draw(tile), 4, 4, 3.0)
            self.paste(f, tile, W // 2, 470, p)
            words, end = self.layout_words(s["headline"], M, 640, W - 2 * M, 104, 800, 3, 60, 1.04, center=True)
            self.pop_words(f, words, t, 0.25, stagger=0.06)
            if s.get("subhead"):
                self.fade_text(f, s["subhead"], M, end + 16, W - 2 * M, 44, 500, self.ink, t, 0.8, center=True)
            by = end + 170
            q = ease_out(prog(t, 1.0, 0.3)) * (1 + 0.04 * math.sin(max(0, t - 1.3) * 7))
            btn = Image.new("RGBA", (700, 120), (0, 0, 0, 0))
            bd = ImageDraw.Draw(btn)
            bd.rounded_rectangle([0, 0, 699, 119], radius=60, fill="#ffffff")
            bd.text((350, 60), "Tap the link in bio", font=self.F(52, 800), fill=INK, anchor="mm")
            self.paste(f, btn, W // 2, by, q)
            self.fade_text(f, "toy-ticker.github.io", M, by + 90, W - 2 * M, 48, 800, self.ink, t, 1.2, center=True)
            d.text((W // 2, BOTTOM - 20), "Not affiliated with McDonald's or The Pokémon Company. Prices: eBay US; not advice.",
                   font=self.F(24, 500), fill=self.ink, anchor="mm")
            return f
        return 2.6, draw

    def scene_chat(self, s):
        """The toys' group chat: typing dots, then each bubble pops in; scrolls up like a phone."""
        from chatui import Chat
        msgs = s.get("messages") or []
        members = list(dict.fromkeys(m["from"] for m in msgs))
        x0, x1, y0, y1 = M - 24, W - M + 24, TOP - 30, BOTTOM + 20
        cw = x1 - x0 - 40
        c = Chat(self.root, self.items, self.F0, cw, 52)
        els, total_h = c.layout(msgs)
        head_h = 150
        area_h = y1 - y0 - head_h - 24
        me = msgs[0]["from"] if msgs else None
        # When each message starts typing and when its bubble lands.
        times, t = [], 0.55
        for m in msgs:
            typing = 0.4 if m["from"] != me else 0.25
            times.append((t, t + typing))
            t += typing + min(1.3, 0.5 + 0.026 * len(m["text"]))
        dur = t + 0.8
        tops = {el["msg"]: el["y"] for el in els if el["kind"] == "name"}
        bubbles = {el["msg"]: el for el in els if el["kind"] == "bubble"}
        mask = Image.new("L", (cw, area_h), 0)
        ImageDraw.Draw(mask).rectangle([0, 0, cw, area_h], fill=255)

        def need(bottom):
            return max(0, bottom - area_h)

        def draw(tt):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            rise = ease_out(prog(tt, 0, 0.35))
            oy = int((1 - rise) * 160)
            d.rounded_rectangle([x0, y0 + oy, x1, y1 + oy], radius=44, fill=(255, 255, 255, int(250 * rise)))
            ax = x0 + 30
            for k, iid in enumerate(members[:5]):
                f.paste(c.avatar(iid), (ax + k * 48, y0 + 28 + oy), c.avatar(iid))
            tx = ax + 48 * min(5, len(members)) + 34
            title = self.text_img(s["headline"], 48, 800, "#1d1d1a")
            if title.width > x1 - tx - 30:
                title = title.resize((x1 - tx - 30, int(title.height * (x1 - tx - 30) / title.width)), Image.LANCZOS)
            f.paste(title, (tx, y0 + 26 + oy), title)
            d.text((tx, y0 + 92 + oy), f"{len(members)} members", font=self.F0(30, 500), fill="#8e8e93")
            d.line([x0 + 24, y0 + head_h - 8 + oy, x1 - 24, y0 + head_h - 8 + oy], fill="#e5e5ea", width=2)
            shown, scales, typing, offset = 0, {}, None, 0.0
            for k, (ts, tl) in enumerate(times):
                el = bubbles[k]
                if tt >= tl:
                    shown = k + 1
                    scales[k] = 0.6 + 0.4 * back_out(prog(tt, tl, 0.25))
                    offset = max(offset, need(el["y"] + el["h"]) * ease_out(prog(tt, tl, 0.25)))
                elif tt >= ts:
                    ty = tops.get(k, el["y"])
                    if k in tops:      # the name label comes with the typing bubble
                        shown = max(shown, k)
                    typing = (msgs[k]["from"], el["y"], el["side"])
                    offset = max(offset, need(el["y"] + int(52 * 1.5)) * ease_out(prog(tt, ts, 0.25)))
                    break
            area = Image.new("RGBA", (cw, area_h), (0, 0, 0, 0))
            # show the name label of the message being typed
            show_names = shown + (1 if typing and any(e["kind"] == "name" and e["msg"] == shown for e in els) else 0)
            c.draw(area, [e for e in els if e["kind"] == "bubble" and e["msg"] < shown or
                          e["kind"] == "name" and e["msg"] < show_names], max(shown, show_names), offset, scales, typing, tt)
            if rise > 0.05:
                f.paste(area, (x0 + 20, y0 + head_h + 12 + oy), area)
            return f
        return dur, draw

    def scene_rapid(self, s):
        """Rapid fire: one item per second, cheapest to priciest. Full-screen photo on its own colour wash,
        name and price as Instagram-style labels, a counter, and a hard cut with a white flash on each beat."""
        from native import Native
        nat = getattr(self, "_nat", None) or Native(self)
        self._nat = nat
        rows = s.get("rows") or []
        beat = 1.0
        n = len(rows)
        intro = 0.0 if (self.post.get("reel_hook") or {}).get("text") else 1.2   # the hook already says it

        def draw(t):
            if t < intro:     # the headline, then go
                f = nat.backdrop([rows[0]["item_id"]])
                nat.caption(f, s["headline"], 820, t, 0, size=80)
                if s.get("subhead"):
                    nat.caption(f, s["subhead"], 1060, t, 0.35, size=46, dark=True)
                return f
            k = min(n - 1, int((t - intro) / beat))
            lt = t - intro - k * beat
            r = rows[k]
            iid, fid = r["item_id"], r["fact_ids"][0]
            f = nat.backdrop([iid])
            pop = back_out(prog(lt, 0, 0.18))
            last = k == n - 1
            size = 720 if last else 640
            self.paste(f, self.photo(iid, size), W // 2, 900, (0.75 + 0.25 * pop) * (1 + 0.05 * lt), 1)
            it = self.items[iid]
            name = it["name"].rsplit(" ", 1)[0] if it["name"].endswith((" toy", " card")) else it["name"]
            self.paste(f, nat.label(f"{k + 1}/{n}", 40, dark=True), W // 2, TOP + 20, 1)
            self.paste(f, nat.label(name, 72), W // 2, 1340, 0.85 + 0.15 * pop)
            self.paste(f, nat.label(self.fx[fid]["display"], 110, dark=True), W // 2, 1480, 0.8 + 0.2 * pop)
            if last:
                self.paste(f, nat.label("the priciest", 48), W // 2, TOP + 110, back_out(prog(lt, 0.15, 0.25)))
            if lt < 0.06:     # flash on the cut
                f = Image.blend(f, Image.new("RGB", (W, H), "#ffffff"), 0.55 * (1 - lt / 0.06))
            return f
        return intro + n * beat + 0.8, draw

    def scene_checklist(self, s):
        """The checklist: rows drop in one by one with an empty checkbox, then it holds so people can screenshot."""
        rows = s.get("rows") or []
        n = len(rows)
        dur = 1.0 + 0.11 * n + 2.8

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            words, end = self.layout_words(s["headline"], M, TOP - 20, W - 2 * M, 80, 800, 2, 50)
            self.pop_words(f, words, t, 0, stagger=0.05)
            if s.get("subhead"):
                self.fade_text(f, s["subhead"], M, end + 4, W - 2 * M, 38, 500, self.ink, t, 0.3, max_lines=1)
                end += 56
            top, bot, gap = end + 30, BOTTOM + 40, 12
            per_col = -(-n // 2)
            rh = (bot - top - (per_col - 1) * gap) / max(1, per_col)
            cw = (W - 2 * (M - 30) - 18) / 2
            sold_col = "#15803d" if self.p_fill in (WHITE, "#ffffff") else "#4ade80"
            for k, r in enumerate(rows):
                p = ease_out(prog(t, 0.5 + 0.11 * k, 0.3))
                if p <= 0:
                    continue
                col, row = divmod(k, per_col)
                x0 = M - 30 + col * (cw + 18) + (1 - p) * (200 if col else -200)
                y0 = top + row * (rh + gap)
                x1 = x0 + cw
                self.panel(d, [x0, y0, x1, y0 + rh], radius=18)
                b = rh * 0.3
                d.rounded_rectangle([x0 + 14, y0 + (rh - b) / 2, x0 + 14 + b, y0 + (rh + b) / 2], radius=6,
                                    outline="#9ca3af", width=3)
                iid, fid = r["item_id"], r["fact_ids"][0]
                ph = self.photo(iid, rh - 16)
                if ph is not None:
                    self.paste(f, ph, x0 + 24 + b + (rh - 16) / 2, y0 + rh / 2, 1, p)
                it = self.items[iid]
                name = it["name"].rsplit(" ", 1)[0] if it["name"].endswith((" toy", " card")) else it["name"]
                sold = self.kind_of.get(fid) == "sold"
                price = self.fx[fid]["display"]
                pf = self.F(int(rh * 0.36), 800)
                pw = d.textlength(price, font=pf)
                d.text((x1 - 16, y0 + rh * 0.42), price, font=pf, fill=sold_col if sold else self.p_ink, anchor="rm")
                d.text((x1 - 16, y0 + rh * 0.76), "sold" if sold else "asking", font=self.F(int(rh * 0.17), 500),
                       fill=self.p_grey, anchor="rm")
                nx = x0 + 34 + b + rh - 16
                size = int(rh * 0.3)
                while size > 16 and d.textlength(name, font=self.F(size, 700)) > x1 - 26 - pw - nx:
                    size -= 2
                d.text((nx, y0 + rh / 2), name, font=self.F(size, 700), fill=self.p_ink, anchor="lm")
            return f
        return dur, draw

    def scene_tweet(self, s):
        """A tweet-style text card from @toy_ticker (no likes or reposts: those would be made-up numbers)."""
        from tweet import Tweet
        tw = Tweet(self.root, self.items, self.F0)
        card = tw.card(s, 940)

        def draw(t):
            f = self.bg.copy()
            p = ease_out(prog(t, 0.0, 0.35))
            self.paste(f, card, W // 2, (TOP + BOTTOM) / 2 + (1 - p) * 140, 0.94 + 0.06 * p, p)
            return f
        return max(3.0, 1.6 + 0.035 * len(s["headline"])), draw

    def scene_screenshot(self, s):
        """The site itself: a phone-style frame scrolling through the focus region of the screenshot."""
        shot = Image.open(Path(self.folder) / s["image"]).convert("RGB")
        fw = W - 2 * M
        sc = shot.resize((fw, int(shot.height * fw / shot.width)), Image.LANCZOS)
        f0, f1 = (int(v * sc.height) for v in s["focus"])
        mask_cache = {}
        dur = 3.4

        def draw(t):
            f = self.bg.copy()
            d = ImageDraw.Draw(f, "RGBA")
            words, end = self.layout_words(s["headline"], M, TOP, W - 2 * M, 92, 800, 2, 56)
            self.pop_words(f, words, t, 0, stagger=0.05)
            top = end + 36
            fh = BOTTOM - (150 if s.get("note") else 40) - top
            span = f1 - f0
            if span > fh:      # scroll down through the region
                p = prog(t, 0.5, dur - 1.2)
                p = p * p * (3 - 2 * p)
                y0, view = f0 + p * (span - fh), fh
            else:              # region fits: show it, gently zooming in
                y0, view = f0, span
            crop = sc.crop((0, int(y0), fw, int(y0 + view)))
            z = 1 + 0.05 * t / dur
            if span <= fh:
                crop = crop.resize((int(crop.width * z), int(crop.height * z)), Image.BILINEAR)
                cx0 = (crop.width - fw) // 2
                crop = crop.crop((cx0, 0, cx0 + fw, min(crop.height, fh)))
            rise = ease_out(prog(t, 0.1, 0.4))
            yy = int(top + (1 - rise) * 120)
            key = crop.size
            if key not in mask_cache:
                m = Image.new("L", key, 0)
                ImageDraw.Draw(m).rounded_rectangle([0, 0, key[0] - 1, key[1] - 1], radius=30, fill=255)
                mask_cache[key] = m
            d.rounded_rectangle([M - 8, yy - 8, M + fw + 8, yy + crop.height + 8], radius=36,
                                fill=(255, 255, 255, int(255 * rise)))
            if rise > 0.05:
                f.paste(crop, (M, yy), mask_cache[key])
            if s.get("note"):
                self.fade_text(f, s["note"], M, yy + crop.height + 34, W - 2 * M, 50, 700, self.ink, t, dur - 1.1)
            return f
        return dur, draw

    def scene_still(self, slide_path):
        """Fallback for other layouts: the drawn slide, slowly zooming."""
        from extras import place
        im = Image.open(slide_path)

        def draw(t):
            f = self.bg.copy()
            sc = 1 + 0.05 * t / 2.6
            w = int(960 * sc)
            place(f, im, w, int(300 - (w - 960) * 0.6))
            return f
        return 2.6, draw

    def scenes(self, folder):
        self.folder = Path(folder)
        out = []
        nat = None
        if self.st.get("native"):
            from native import Native
            nat = Native(self)
        pick = lambda name: getattr(nat, name, None) or getattr(self, name, None)  # noqa: E731
        hook = self.post.get("reel_hook") or {}
        if hook.get("text"):
            out.append(pick("scene_hook")(hook))
        slides = sorted((Path(folder) / "slides").glob("*.jpg"))
        rapid = any(sl["layout"] == "rapid" for sl in self.post["slides"])
        for k, s in enumerate(self.post["slides"]):
            if rapid and s["layout"] == "cover":     # a rapid Reel goes straight from the hook into the list
                continue
            fn = pick(f"scene_{s['layout']}")
            if fn:
                out.append(fn(s))
            elif k < len(slides):
                out.append(self.scene_still(slides[k]))
        return out


def frames(scenes, style="up"):
    """Every video frame in order, with a transition into each new scene (push up, push left, or zoom-through)
    and the VS shake."""
    prev = None
    for i, (dur, draw) in enumerate(scenes):
        n = round(dur * FPS)
        last = None
        for k in range(n):
            t = k / FPS
            res = draw(t)
            f, shake = (res if isinstance(res, tuple) else (res, None))
            if shake and shake[0] <= t <= shake[0] + shake[1]:
                amp = 14 * (1 - (t - shake[0]) / shake[1])
                g = f.copy()
                g.paste(f, (int(amp * math.sin(t * 90)), int(amp * math.cos(t * 70))))
                f = g
            last = f
            if prev is not None and t < PUSH:
                e = ease_out(t / PUSH)
                g = Image.new("RGB", (W, H))
                if style == "left":
                    off = int(e * W)
                    g.paste(prev, (-off, 0))
                    g.paste(f, (W - off, 0))
                elif style == "zoom":       # old scene zooms past the camera while the new one fades in
                    z = 1 + 0.35 * e
                    big = prev.resize((int(W * z), int(H * z)), Image.BILINEAR)
                    g.paste(big, (-(big.width - W) // 2, -(big.height - H) // 2))
                    g = Image.blend(g, f, e)
                else:
                    off = int(e * H)
                    g.paste(prev, (0, -off))
                    g.paste(f, (0, H - off))
                f = g
            yield f
        prev = last


def pick_style(folder, post):
    """The post's reel_style if it names one; else the style it used before (reel_style.txt, so redrawing keeps
    it); else the style other posts used least recently, so back-to-back Reels look different."""
    folder = Path(folder)
    if post.get("reel_style") in STYLES:
        return post["reel_style"]
    mine = folder / "reel_style.txt"
    if mine.exists() and mine.read_text().strip() in STYLES:
        return mine.read_text().strip()
    last = {}
    for rec in folder.parent.glob("*/reel_style.txt"):
        name = rec.read_text().strip()
        if rec.parent != folder and name in STYLES:
            key = (rec.parent.name[:10], rec.stat().st_mtime)
            last[name] = max(last.get(name, ("", 0)), key)
    names = [n for n in STYLES if STYLES[n].get("rotate", True)]   # sticker and meme only when asked for
    seed = int(hashlib.md5(folder.name.encode()).hexdigest(), 16)
    pick = min(names, key=lambda n: (last.get(n, ("", 0)), (seed + names.index(n)) % len(names)))
    mine.write_text(pick + "\n")
    return pick


def build(folder, facts, root, post, music=None):
    """Write <folder>/reel.mp4. Returns the path, or None without ffmpeg."""
    from extras import find_music
    folder = Path(folder)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return None
    post = dict(post, reel_style=pick_style(folder, post))
    R = Reel(post, facts, root)
    sc = R.scenes(folder)
    total = sum(round(d * FPS) for d, _ in sc) / FPS
    music = Path(music) if music else find_music(folder, root)
    out = folder / "reel.mp4"
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-"]
    maps = ["-map", "0:v"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        cmd += ["-filter_complex", f"[1:a]atrim=0:{total:.2f},asetpts=PTS-STARTPTS,afade=t=in:d=0.4,"
                f"afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5,volume=0.9[aout]"]
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
    cmd += [*maps, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20", "-t", f"{total:.2f}",
            "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in frames(sc, R.transition):
            p.stdin.write(f.convert("RGB").tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg exited with {p.returncode}")
    return out
