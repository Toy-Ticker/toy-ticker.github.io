"""A group chat between toys, drawn like a phone messaging app: used by the 'chat' slide (render.py) and the
animated chat scene (motion.py).

The first toy to speak is "me" (right side, blue bubbles); everyone else is on the left (grey bubbles) with a
round avatar of their official photo and their name above the first message of each run.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

BLUE, GREY_BUBBLE, NAME_GREY, INK = "#0a84ff", "#e9e9eb", "#8e8e93", "#1d1d1b"


def short_name(item):
    n = item["name"]
    return n.rsplit(" ", 1)[0] if n.endswith((" toy", " card")) else n


class Chat:
    def __init__(self, root, items, F, width, size=44):
        from render import trim, wrap
        self.root, self.items, self.F, self.width, self.size = Path(root), items, F, width, size
        self._trim, self._wrap = trim, wrap
        self.scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        self.av = int(size * 1.55)                  # avatar diameter
        self._tiles, self._avatars = {}, {}

    def avatar(self, iid):
        if iid not in self._avatars:
            d = self.av
            im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
            mask = Image.new("L", (d, d), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
            tile = Image.new("RGBA", (d, d), "#ffffff")
            it = self.items.get(iid) or {}
            if it.get("image"):
                ph = self._trim(Image.open(self.root / it["image"]).convert("RGBA"))
                if ph.height > ph.width * 1.2:      # cards: use the artwork near the top
                    ph = ph.crop((0, int(ph.height * 0.08), ph.width, int(ph.height * 0.08) + ph.width))
                ph.thumbnail((int(d * 0.86), int(d * 0.86)), Image.LANCZOS)
                tile.paste(ph, ((d - ph.width) // 2, (d - ph.height) // 2), ph)
            im.paste(tile, (0, 0), mask)
            ImageDraw.Draw(im).ellipse([0, 0, d - 1, d - 1], outline="#d1d1d6", width=2)
            self._avatars[iid] = im
        return self._avatars[iid]

    def layout(self, messages):
        """Positions of every name label and bubble, top to bottom, in a column `width` wide starting at y=0."""
        f = self.F(self.size, 500)
        me = messages[0]["from"] if messages else None
        pad_x, pad_y, lh = int(self.size * 0.62), int(self.size * 0.42), int(self.size * 1.22)
        max_w = int(self.width * 0.70)
        left_x = 12 + self.av + 14
        els, y, prev = [], 0, None
        for k, m in enumerate(messages):
            side = "right" if m["from"] == me else "left"
            new_run = m["from"] != prev
            if new_run and k:
                y += int(self.size * 0.55)
            if new_run:   # every run is labelled, "me" included: the speakers are characters
                els.append({"kind": "name", "y": y, "x": left_x + 8 if side == "left" else self.width - 20,
                            "align": side, "text": short_name(self.items[m["from"]]), "msg": k})
                y += int(self.size * 0.78)
            lines = self._wrap(self.scratch, m["text"], f, max_w - 2 * pad_x)
            tw = max(self.scratch.textlength(ln, font=f) for ln in lines)
            w, h = int(tw + 2 * pad_x), int(len(lines) * lh + 2 * pad_y - (lh - self.size) * 0.3)
            x = self.width - 12 - w if side == "right" else left_x
            last_of_run = k + 1 == len(messages) or messages[k + 1]["from"] != m["from"]
            els.append({"kind": "bubble", "y": y, "x": x, "w": w, "h": h, "side": side, "lines": lines,
                        "from": m["from"], "msg": k, "avatar": side == "left" and last_of_run})
            y += h + int(self.size * 0.22)
            prev = m["from"]
        return els, y

    def bubble_tile(self, el):
        key = (el["msg"], el["w"], el["h"])
        if key not in self._tiles:
            f = self.F(self.size, 500)
            im = Image.new("RGBA", (el["w"], el["h"]), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            right = el["side"] == "right"
            d.rounded_rectangle([0, 0, el["w"] - 1, el["h"] - 1], radius=int(self.size * 0.85),
                                fill=BLUE if right else GREY_BUBBLE)
            ty = int(self.size * 0.42)
            for ln in el["lines"]:
                d.text((int(self.size * 0.62), ty), ln, font=f, fill="#ffffff" if right else INK)
                ty += int(self.size * 1.22)
            self._tiles[key] = im
        return self._tiles[key]

    def typing_tile(self, t):
        """A grey bubble with three bouncing dots (t in seconds)."""
        w, h = int(self.size * 2.6), int(self.size * 1.5)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=GREY_BUBBLE)
        r = int(self.size * 0.16)
        for i in range(3):
            dy = int(-r * 0.9 * max(0, math.sin(t * 9 - i * 0.9)))
            cx = int(w / 2 + (i - 1) * r * 3)
            d.ellipse([cx - r, h // 2 - r + dy, cx + r, h // 2 + r + dy], fill="#8e8e93")
        return im

    def draw(self, canvas, els, shown, offset=0.0, scales=None, typing=None, t=0.0):
        """Draw onto `canvas` (RGBA, `width` wide) the first `shown` messages, scrolled up by `offset` px.
        scales: {msg index: pop scale}; typing: (from item id, y, side) to show a typing bubble at that y."""
        d = ImageDraw.Draw(canvas)
        nf = self.F(int(self.size * 0.62), 500)
        for el in els:
            if el["msg"] >= shown:
                break
            y = el["y"] - offset
            if y > canvas.height or y + el.get("h", 40) < -40:
                continue
            if el["kind"] == "name":
                d.text((el["x"], y), el["text"], font=nf, fill=NAME_GREY, anchor="ra" if el.get("align") == "right" else "la")
                continue
            tile = self.bubble_tile(el)
            s = (scales or {}).get(el["msg"], 1.0)
            if s < 0.999:
                tile = tile.resize((max(1, int(tile.width * s)), max(1, int(tile.height * s))), Image.BILINEAR)
            ax = el["x"] + el["w"] - tile.width if el["side"] == "right" else el["x"]
            canvas.paste(tile, (int(ax), int(y + el["h"] - tile.height)), tile)
            if el["avatar"]:
                av = self.avatar(el["from"])
                canvas.paste(av, (12, int(y + el["h"] - av.height)), av)
        if typing:
            who, y, side = typing
            tile = self.typing_tile(t)
            left = side == "left"
            x = 12 + self.av + 14 if left else self.width - 12 - tile.width
            canvas.paste(tile, (int(x), int(y - offset)), tile)
            if left:
                av = self.avatar(who)
                canvas.paste(av, (12, int(y - offset + tile.height - av.height)), av)
