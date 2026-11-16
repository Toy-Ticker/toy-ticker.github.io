"""The pinned "What is Toy Ticker?" carousel: 3 slides (what it is, how to use it, link in bio).

    .venv/bin/python scripts/social/intro.py [--screenshot site.png]

A pinned post stays up for weeks, so the slides carry no prices. --screenshot is a phone-width capture of the site
(see SOCIAL.md for the headless-Chrome command; capture with reduced motion so numbers aren't mid-animation).
Writes social/intro/slides/01-03.jpg.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from og import Fonts, logo  # noqa: E402
from render import H, M, W, gradient, text_block, trim  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
C1, C2, INK = "#d62300", "#ffb703", "#ffffff"
DARK, GREY, PANEL = "#1d1d1b", "#6b6b66", (255, 255, 255, 245)
ITEMS = ["assets/toys/pokemon-toys-2026-11.png", "assets/cards/pokemon-2026-004.png", "assets/toys/pokemon-toys-2026-04.png"]


def base(F, n):
    img = gradient(C1, C2)
    d = ImageDraw.Draw(img, "RGBA")
    logo(d, M, 52, 0.9)
    d.text((M + 72, 81), "Toy Ticker", font=F(34, 700), fill=INK, anchor="lm")
    d.text((W - M, 81), f"{n} / 3", font=F(28, 600), fill=INK, anchor="rm")
    return img, d


def footer(d, F, text="toy-ticker.github.io  ·  Not affiliated with McDonald's"):
    d.text((W // 2, H - 48), text, font=F(24, 500), fill=INK, anchor="mm")


def photo(img, path, box):
    ph = trim(Image.open(ROOT / path).convert("RGBA"))
    x0, y0, x1, y1 = box
    ph.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
    img.paste(ph, (x0 + (x1 - x0 - ph.width) // 2, y0 + (y1 - y0 - ph.height) // 2), ph)


def slide1(F):
    img, d = base(F, 1)
    d.rounded_rectangle([M, 168, M + 250, 218], radius=25, fill=(255, 255, 255, 60))
    d.text((M + 125, 193), "START HERE", font=F(26, 700), fill=INK, anchor="mm")
    y = text_block(d, (M, 250), "What is Toy Ticker?", F, W - 2 * M, 118, 700, INK, 2, 70, 1.0)
    y = text_block(d, (M, y + 20), "Daily eBay prices for every McDonald's Happy Meal toy and card", F,
                   W - 2 * M, 50, 500, INK, 3, 32, 1.15)
    top, bot = max(y + 60, 760), H - 120
    d.rounded_rectangle([M, top, W - M, bot], radius=32, fill=PANEL)
    col = (W - 2 * M) / 3
    for i, p in enumerate(ITEMS):
        x0 = int(M + i * col)
        photo(img, p, (x0 + 30, top + 40, int(x0 + col - 30), bot - 110))
    d.text((W // 2, bot - 58), "Free  ·  no ads  ·  no accounts", font=F(36, 700), fill=DARK, anchor="mm")
    footer(d, F)
    return img


def slide2(F, shot):
    img, d = base(F, 2)
    text_block(d, (M, 160), "How to use it", F, W - 2 * M, 96, 700, INK, 1, 60)
    # Phone on the left: a capture of the site's top half in a dark rounded frame.
    pw, ph = 430, 860
    px, py = M, 320
    d.rounded_rectangle([px - 14, py - 14, px + pw + 14, py + ph + 14], radius=58, fill=DARK)
    if shot:
        s = Image.open(shot).convert("RGB")
        s = s.resize((pw, round(s.height * pw / s.width)), Image.LANCZOS).crop((0, 0, pw, ph))
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=46, fill=255)
        img.paste(s, (px, py), mask)
    else:
        d.rounded_rectangle([px, py, px + pw, py + ph], radius=46, fill="#ffffff")
    # Steps on the right.
    steps = [("1", "Find your toy or card", "Search, or tap the Happy Meal it came in"),
             ("2", "See what it sells for", "Asking and sold prices on eBay, with a daily chart"),
             ("3", "Track your collection", "Mark yours in My Happy Meals and spot deals")]
    sx, sw = px + pw + 56, W - M - (px + pw + 56)
    y = py + 10
    for num, head, sub in steps:
        d.ellipse([sx, y, sx + 64, y + 64], fill="#ffffff")
        d.text((sx + 32, y + 32), num, font=F(38, 700), fill=C1, anchor="mm")
        yy = text_block(d, (sx, y + 84), head, F, sw, 44, 700, INK, 2, 30, 1.08)
        yy = text_block(d, (sx, yy + 6), sub, F, sw, 30, 500, INK, 3, 22, 1.2)
        y = yy + 46
    footer(d, F)
    return img


def slide3(F):
    img = gradient(C1, C2)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((W - M, 81), "3 / 3", font=F(28, 600), fill=INK, anchor="rm")
    logo(d, W // 2 - 110, 210, 3.4)
    y = text_block(d, (M, 480), "What's yours worth?", F, W - 2 * M, 104, 700, INK, 2, 60, 1.02)
    lines = ["Every Pokémon toy and card, priced daily", "Past Happy Meals too, back to June",
             "Sold prices, charts and deals"]
    y += 24
    for ln in lines:
        d.ellipse([M + 4, y + 14, M + 22, y + 32], fill="#ffffff")
        y = text_block(d, (M + 44, y), ln, F, W - 2 * M - 44, 40, 600, INK, 2, 28, 1.15) + 14
    d.rounded_rectangle([M + 140, y + 30, W - M - 140, y + 130], radius=50, fill="#ffffff")
    d.text((W // 2, y + 80), "Tap the link in bio", font=F(46, 700), fill=DARK, anchor="mm")
    d.text((W // 2, y + 190), "toy-ticker.github.io", font=F(40, 700), fill=INK, anchor="mm")
    for dy, line in ((132, "Not affiliated with McDonald's or The Pokémon Company."),
                     (90, "Images: happymeal.com, pokemon.com")):
        d.text((W // 2, H - dy), line, font=F(24, 500), fill=INK, anchor="mm")
    footer(d, F, "Prices from eBay US listings; not advice.")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot")
    args = ap.parse_args()
    F = Fonts(ROOT / "assets" / "fonts" / "BricolageGrotesque.ttf")
    out = ROOT / "social" / "intro" / "slides"
    out.mkdir(parents=True, exist_ok=True)
    for n, img in enumerate([slide1(F), slide2(F, args.screenshot), slide3(F)], 1):
        img.convert("RGB").save(out / f"{n:02d}.jpg", "JPEG", quality=90, optimize=True, progressive=True)
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
