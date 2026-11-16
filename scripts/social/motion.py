"""Animated Reel (reel.mp4, 1080x1920) for a drafted post: every slide becomes a full-screen scene with motion
(words popping in, toys sliding in, a VS badge that slams, prices counting up) and scenes push up into each other.

Same rule as the slides: every number shown is a fact's display text from facts.json (a count-up only animates
towards that exact value). Instagram covers the top ~250 px and bottom ~340 px of a Reel with its own buttons,
so content stays between those.
"""
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
PUSH = 0.24                  # seconds for the push-up transition between scenes


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
        self.ink = ink
        self.accent = "#d62300" if c1 in ("#ffcb05", "#ffb703") else c1
        self.bg = backdrop(c1, c2)
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
                self._photo[key] = base.resize((max(1, int(base.width * r)), max(1, int(base.height * r))), Image.LANCZOS)
        return self._photo[key]

    def text_img(self, text, size, weight, fill):
        key = (text, size, weight, fill)
        if key not in self._txt:
            f = self.F(size, weight)
            # Same box height for every word at a size (ascender to descender), so words share a baseline.
            ascent, descent = f.getmetrics()
            l, _, r, _ = self.scratch.textbbox((0, 0), text, font=f)
            im = Image.new("RGBA", (r - l + 8, ascent + descent + 8), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((4 - l, 4), text, font=f, fill=fill)
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
                self.paste(f, self.text_img(self.label(fids[0]), 38, 500, GREY), W // 2, top + 205, 1, lp)
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
                dl.rounded_rectangle([x0, top, x1, bot], radius=32, fill=WHITE)
                it = self.items[iid]
                self.paste(layer, self.photo(iid, cw - 80), (x0 + x1) / 2, top + 40 + (cw - 80) / 2)
                name = self.text_img(it["name"], 40, 700, INK)
                self.paste(layer, name, (x0 + x1) / 2, bot - 230, min(1, (cw - 30) / name.width))
                if i < len(fids):
                    self.big_number(layer, fids[i], (x0 + x1) / 2, bot - 190, 84, t, 0.85 + 0.1 * i, max_w=cw - 40)
                    lab = self.text_img(self.label(fids[i]), 28, 500, GREY)
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
                self.paste(f, self.text_img(self.label(fids[0]), 40, 500, GREY), W // 2, top + 290, 1,
                           ease_out(prog(t, 0.9, 0.3)))
            if len(fids) > 1:
                p = ease_out(prog(t, 1.1, 0.35))
                txt = "vs " + self.fx[fids[1]]["display"]
                self.paste(f, self.text_img(txt, 92, 800, INK), W // 2 + (1 - p) * 500, top + 400, 1, p)
                self.paste(f, self.text_img(self.label(fids[1]), 36, 500, GREY), W // 2 + (1 - p) * 500, top + 480, 1, p)
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
                d.rounded_rectangle([M + off, ry, W - M + off, ry + rh], radius=24, fill=WHITE)
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
        out = []
        hook = self.post.get("reel_hook") or {}
        if hook.get("text"):
            out.append(self.scene_hook(hook))
        slides = sorted((Path(folder) / "slides").glob("*.jpg"))
        for k, s in enumerate(self.post["slides"]):
            fn = getattr(self, f"scene_{s['layout']}", None)
            if fn:
                out.append(fn(s))
            elif k < len(slides):
                out.append(self.scene_still(slides[k]))
        return out


def frames(scenes):
    """Every video frame in order, with a push-up transition into each new scene and the VS shake."""
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
                off = int(ease_out(t / PUSH) * H)
                g = Image.new("RGB", (W, H))
                g.paste(prev, (0, -off))
                g.paste(f, (0, H - off))
                f = g
            yield f
        prev = last


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
        for f in frames(sc):
            p.stdin.write(f.convert("RGB").tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg exited with {p.returncode}")
    return out
