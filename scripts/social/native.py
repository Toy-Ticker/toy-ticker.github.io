"""The "native" Reel style: looks like a Reel made in the Instagram app, not a designed graphic.

Each scene is the toy's photo big on a soft, blurred wash of its own colours, with captions in Instagram's own
text look (black text on white rounded labels, one label per line, popping in line by line). Numbers are still
facts' display text only. Used by motion.Reel when the post's reel_style is "native".
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageStat

W, H = 1080, 1920
TOP, BOTTOM = 290, 1560
SF = "/System/Library/Fonts/SFNS.ttf"


def ease_out(p):
    return 1 - (1 - p) ** 3


def back_out(p, s=1.7):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def prog(t, start, dur):
    return max(0.0, min(1.0, (t - start) / dur)) if dur > 0 else float(t >= start)


class Native:
    def __init__(self, R):
        from og import Fonts
        from pathlib import Path
        self.R = R
        self.F = Fonts(Path(SF)) if Path(SF).exists() else R.F0
        self._bg, self._labels = {}, {}

    # --- pieces ----------------------------------------------------------------------------------
    def backdrop(self, ids):
        """A blurred wash of the item photos' colours, like a photo shot close up: cached per item set."""
        key = tuple(ids)
        if key not in self._bg:
            photos = [self.R.photo(i, 400) for i in ids if self.R.photo(i, 400) is not None]
            if photos:
                cols = [tuple(int(c) for c in ImageStat.Stat(p.convert("RGB"), p.getchannel("A")).mean) for p in photos]
            else:
                cols = [(240, 160, 60)]
            c1 = cols[0]
            c2 = cols[-1] if len(cols) > 1 else tuple(int(v * 0.55) for v in c1)
            small = Image.new("RGB", (54, 96))
            px = small.load()
            for y in range(96):
                for x in range(54):
                    t = min(1, (x / 54 * 0.35 + y / 96 * 0.65))
                    px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            bg = small.resize((W, H), Image.BICUBIC)
            for p in photos[:2]:                # out-of-focus copies of the toy, like a real photo's background
                big = p.resize((int(p.width * 2.6), int(p.height * 2.6)), Image.BILINEAR)
                bg.paste(big, (W // 2 - big.width // 2 + (0 if len(photos) == 1 else (-300 if p is photos[0] else 300)),
                               H // 2 - big.height // 2), big)
            bg = bg.filter(ImageFilter.GaussianBlur(60))
            shade = Image.new("RGB", (W, H), (0, 0, 0))
            self._bg[key] = Image.blend(bg, shade, 0.18)
        return self._bg[key].copy()

    def label(self, text, size, dark=False):
        """One Instagram-style caption line: text on a rounded label (white with black text, or the reverse)."""
        key = (text, size, dark)
        if key not in self._labels:
            f = self.F(size, 700)
            d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
            l, t, r, b = d0.textbbox((0, 0), text, font=f)
            asc, desc = f.getmetrics()
            px, py = int(size * 0.42), int(size * 0.22)
            w, h = r - l + 2 * px, asc + desc + 2 * py
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(size * 0.32), fill="#000000" if dark else "#ffffff")
            d.text((px - l, py), text, font=f, fill="#ffffff" if dark else "#000000")
            self._labels[key] = im
        return self._labels[key]

    def caption(self, frame, text, cy, t, start, size=64, dark=False, max_w=W - 150, stagger=0.12, center=True):
        """Wrapped caption, one label per line, overlapping slightly like Instagram's text background; lines
        pop in one after another. Returns the y below the block."""
        f = self.F(size, 700)
        lines = self.wrap(text, f, max_w - int(size * 0.84))
        h = self.label("Ag", size).height
        step = int(h * 0.86)
        y = cy - (step * (len(lines) - 1) + h) // 2 if center else cy
        for k, ln in enumerate(lines):
            p = prog(t, start + k * stagger, 0.22)
            if p > 0:
                self.R.paste(frame, self.label(ln, size, dark), W // 2, y + k * step + h // 2,
                             0.7 + 0.3 * back_out(p), min(1, p * 2))
        return y + step * (len(lines) - 1) + h

    def wrap(self, text, f, max_w):
        """Greedy wrap, then narrowed as far as it goes without adding a line, so lines come out even
        (no lone last word), the way people break captions by hand."""
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))

        def greedy(limit):
            words, lines, cur = text.split(), [], ""
            for w_ in words:
                test = (cur + " " + w_).strip()
                if d.textlength(test, font=f) <= limit or not cur:
                    cur = test
                else:
                    lines.append(cur)
                    cur = w_
            return lines + ([cur] if cur else [])

        best = greedy(max_w)
        lo, hi = max_w * 0.4, max_w
        while hi - lo > 4:
            mid = (lo + hi) / 2
            if len(greedy(mid)) == len(best):
                hi = mid
            else:
                lo = mid
        return greedy(hi)

    def toy(self, frame, iid, cx, cy, size, t, start=0.0):
        p = ease_out(prog(t, start, 0.35))
        self.R.paste(frame, self.R.photo(iid, size), cx, cy + (1 - p) * 80, (0.92 + 0.08 * p) * (1 + 0.04 * t), p)

    def number(self, frame, fid, cy, t, start):
        """A big number as a black label, counting up to the fact's exact display text."""
        from motion import count_up
        p = prog(t, start, 0.6)
        if p <= 0:
            return
        txt = count_up(self.R.fx[fid]["display"], p)
        bump = 1 + 0.1 * math.sin(math.pi * prog(t, start + 0.6, 0.2))
        self.R.paste(frame, self.label(txt, 120, dark=True), W // 2, cy, bump, min(1, p * 3))
        lp = prog(t, start + 0.5, 0.25)
        if lp > 0:
            self.R.paste(frame, self.label(self.R.label(fid), 40), W // 2, cy + 120, 1, lp)

    # --- scenes ------------------------------------------------------------------------------------
    def scene_hook(self, hook):
        ids = (hook.get("item_ids") or [])[:2]

        def draw(t):
            f = self.backdrop(ids)
            if len(ids) == 1:
                self.toy(f, ids[0], W // 2, 1150, 640, t)
            else:
                for iid, cx in zip(ids, (W // 2 - 240, W // 2 + 240)):
                    self.toy(f, iid, cx, 1150, 440, t)
            # The caption is on screen from the first frame (it's the thumbnail people scroll past).
            self.caption(f, hook["text"], 520, 1.0, 0, size=78)
            return f
        return 1.6, draw

    def scene_cover(self, s):
        ids = s.get("item_ids", [])[:3]

        def draw(t):
            f = self.backdrop(ids[:2])
            n = len(ids)
            for k, iid in enumerate(ids):
                cx = W // 2 + (k - (n - 1) / 2) * 330
                self.toy(f, iid, cx, 1200, 520 if n == 1 else 330, t, 0.15 * k)
            end = self.caption(f, s["headline"], 520, t, 0.1, size=72)
            if s.get("subhead"):
                self.caption(f, s["subhead"], end + 50, t, 0.6, size=44, dark=True, center=False)
            return f
        return 2.6, draw

    def scene_hero(self, s):
        iid, fids = s.get("item_id"), s.get("fact_ids", [])[:1]

        def draw(t):
            f = self.backdrop([iid])
            self.toy(f, iid, W // 2, 760, 620, t)
            self.caption(f, s["headline"], 360, t, 0.15, size=62)
            if fids:
                self.number(f, fids[0], 1200, t, 0.5)
            if s.get("note"):
                self.caption(f, s["note"], 1450, t, 1.4, size=48, dark=True)
            return f
        return 3.0, draw

    def scene_versus(self, s):
        ids, fids = s.get("item_ids", [])[:2], s.get("fact_ids", [])[:2]

        def draw(t):
            f = self.backdrop(ids)
            self.caption(f, s["headline"], 380, t, 0, size=62)
            for i, (iid, cx) in enumerate(zip(ids, (W // 2 - 245, W // 2 + 245))):
                p = ease_out(prog(t, 0.2 + 0.08 * i, 0.35))
                self.R.paste(f, self.R.photo(iid, 420), cx + (1 - p) * (-400 if i == 0 else 400), 860, 1, p)
                if i < len(fids):
                    q = prog(t, 0.8 + 0.12 * i, 0.5)
                    if q > 0:
                        from motion import count_up
                        txt = count_up(self.R.fx[fids[i]]["display"], q)
                        self.R.paste(f, self.label(txt, 76, dark=True), cx, 1150, 1, min(1, q * 3))
                        self.R.paste(f, self.label(self.R.label(fids[i]), 30), cx, 1240, 1, min(1, q * 3))
            self.R.vs(f, W // 2, 860, back_out(prog(t, 0.55, 0.28)))
            if s.get("note"):
                self.caption(f, s["note"], 1430, t, 1.6, size=50, dark=True)
            return f, (0.58, 0.18)
        return 3.2, draw

    def scene_highlight(self, s):
        fids, ids = s.get("fact_ids", [])[:2], s.get("item_ids", [])[:3]

        def draw(t):
            f = self.backdrop(ids[:2])
            n = len(ids)
            for k, iid in enumerate(ids):
                self.toy(f, iid, W // 2 + (k - (n - 1) / 2) * 300, 760, 280, t, 0.1 * k)
            self.caption(f, s["headline"], 380, t, 0, size=62)
            if fids:
                self.number(f, fids[0], 1080, t, 0.5)
            if len(fids) > 1:
                p = prog(t, 1.2, 0.3)
                if p > 0:
                    self.R.paste(f, self.label("vs " + self.R.fx[fids[1]]["display"], 70), W // 2, 1300, 1, p)
                    self.R.paste(f, self.label(self.R.label(fids[1]), 34, dark=True), W // 2, 1385, 1, p)
            if s.get("note"):
                self.caption(f, s["note"], 1500, t, 1.8, size=48, dark=True)
            return f
        return 3.2, draw

    def scene_screenshot(self, s):
        """The site itself, as if screen-recorded: the focus region in a rounded frame, scrolling if it's tall,
        under a caption label, on the item's blurred wash."""
        from pathlib import Path
        iid = s["image"][len("site-"):-len(".png")]
        shot = Image.open(Path(self.R.folder) / s["image"]).convert("RGB")
        fw = 920
        sc = shot.resize((fw, int(shot.height * fw / shot.width)), Image.LANCZOS)
        f0, f1 = (int(v * sc.height) for v in s["focus"])
        dur = 3.4
        top, bottom = 560, 1380
        fh = bottom - top
        mask_cache = {}

        def draw(t):
            f = self.backdrop([iid] if iid in self.R.items else [])
            self.caption(f, s["headline"], 400, t, 0, size=62)
            span = f1 - f0
            if span > fh:
                p = prog(t, 0.5, dur - 1.2)
                y0, view = f0 + p * p * (3 - 2 * p) * (span - fh), fh
            else:
                y0, view = f0, span
            crop = sc.crop((0, int(y0), fw, int(y0 + view)))
            if crop.size not in mask_cache:
                m = Image.new("L", crop.size, 0)
                ImageDraw.Draw(m).rounded_rectangle([0, 0, crop.width - 1, crop.height - 1], radius=34, fill=255)
                mask_cache[crop.size] = m
            rise = ease_out(prog(t, 0.1, 0.4))
            if rise > 0.05:
                yy = int(top + (fh - crop.height) / 2 + (1 - rise) * 120)
                f.paste(crop, ((W - fw) // 2, yy), mask_cache[crop.size])
            if s.get("note"):
                self.caption(f, s["note"], 1470, t, dur - 1.1, size=48, dark=True)
            return f
        return dur, draw

    def scene_cta(self, s):
        ids = [i for sl in self.R.post["slides"] for i in (sl.get("item_ids") or [sl.get("item_id")]) if i][:1]

        def draw(t):
            f = self.backdrop(ids)
            end = self.caption(f, s["headline"], 640, t, 0.1, size=72)
            if s.get("subhead"):
                end = self.caption(f, s["subhead"], end + 40, t, 0.5, size=44, dark=True, center=False)
            q = ease_out(prog(t, 0.9, 0.3)) * (1 + 0.04 * math.sin(max(0, t - 1.2) * 7))
            self.R.paste(f, self.label("link in bio  ·  toy-ticker.github.io", 46, dark=True), W // 2, end + 140, q)
            return f
        return 2.6, draw
