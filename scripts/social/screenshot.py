"""Screenshot one item's card on the live site (phone width, 3x) for a post: <folder>/site-<item id>.png.

Uses the site's screenshot mode (index.html ?only=1#i=<id>), which shows just that item's details, prices,
Market read and chart, and hides specific sellers' listings. Needs Google Chrome; serves nothing itself, so
defaults to the live site; --base http://localhost:8765/ uses the local dev server.

    .venv/bin/python scripts/social/screenshot.py social/<folder> pokemon-2026-004
"""
import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def shoot(folder, item_id, base="https://toy-ticker.github.io/", width=500, scale=3):
    out = Path(folder) / f"site-{item_id}.png"
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", f"--user-data-dir={prof}",
                        f"--screenshot={out}", f"--window-size={width},2200", f"--force-device-scale-factor={scale}",
                        "--timeout=7000", f"{base}?only=1&v={int(time.time())}#i={item_id}"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Trim the empty page background below the card.
    im = Image.open(out).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, im.height - 2)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        im.crop((0, 0, im.width, min(im.height, box[3] + 12 * scale))).save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("item_id")
    ap.add_argument("--base", default="https://toy-ticker.github.io/")
    a = ap.parse_args()
    print(shoot(a.folder, a.item_id, a.base))
    sys.exit(0)
