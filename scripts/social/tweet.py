"""A tweet-style text card from Toy Ticker's own account (@toy_ticker): avatar, name, handle, the text and an
optional toy photo. No likes, reposts or view counts (they'd be made-up numbers) and no X/Twitter logo."""
from pathlib import Path

from PIL import Image, ImageDraw

INK, GREY, LINE = "#0f1419", "#536471", "#eff3f4"


class Tweet:
    def __init__(self, root, items, F):
        from render import trim, wrap
        self.root, self.items, self.F, self.trim, self.wrap = Path(root), items, F, trim, wrap

    def card(self, s, width):
        from og import logo
        k = width / 940                      # sizes are designed for a 940 px wide card
        pad, av = int(44 * k), int(96 * k)
        f_name, f_handle, f_text = self.F(int(40 * k), 700), self.F(int(36 * k), 500), self.F(int(50 * k), 500)
        d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        lines = []
        for para in s["headline"].split("\n"):
            lines += self.wrap(d0, para, f_text, width - 2 * pad) if para.strip() else [""]
        lh = int(66 * k)
        ids = [i for i in (s.get("item_ids") or [])[:2] if (self.items.get(i) or {}).get("image")]
        ph_h = int(360 * k) if ids else 0
        h = pad + av + int(30 * k) + len(lines) * lh + (int(30 * k) + ph_h if ids else 0) + pad
        im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, width - 1, h - 1], radius=int(36 * k), fill="#ffffff", outline=LINE, width=2)
        tile = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        logo(ImageDraw.Draw(tile), 0, 0, 1.0)
        tile = tile.resize((av, av), Image.LANCZOS)
        mask = Image.new("L", (av, av), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, av - 1, av - 1], fill=255)
        im.paste(tile, (pad, pad), mask)
        d.ellipse([pad, pad, pad + av - 1, pad + av - 1], outline=LINE, width=2)
        tx = pad + av + int(22 * k)
        d.text((tx, pad + int(10 * k)), "Toy Ticker", font=f_name, fill=INK)
        d.text((tx, pad + int(54 * k)), "@toy_ticker", font=f_handle, fill=GREY)
        y = pad + av + int(30 * k)
        for ln in lines:
            d.text((pad, y), ln, font=f_text, fill=INK)
            y += lh
        if ids:
            y += int(30 * k)
            box_w = width - 2 * pad
            d.rounded_rectangle([pad, y, pad + box_w, y + ph_h], radius=int(28 * k), fill="#f7f9f9", outline=LINE, width=2)
            col = box_w / len(ids)
            for j, iid in enumerate(ids):
                ph = self.trim(Image.open(self.root / self.items[iid]["image"]).convert("RGBA"))
                ph.thumbnail((int(col * 0.8), int(ph_h * 0.84)), Image.LANCZOS)
                im.paste(ph, (int(pad + col * (j + 0.5) - ph.width / 2), int(y + (ph_h - ph.height) / 2)), ph)
        return im
