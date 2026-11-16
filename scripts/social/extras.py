"""Story image and Reel video for a drafted post, made from its slides (no new numbers, no AI).

    story.jpg  1080x1920: the cover slide on the series colours, with room below for Instagram's link sticker.
    reel.mp4   1080x1920: every slide in order (about 3 s each, short crossfades), silent; add trending audio
               in the Instagram app when posting.

Instagram covers the top and bottom of Stories and Reels with its own buttons, so content stays inside a safe
area (roughly 250 px top, 340 px bottom).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from og import DEFAULT, THEMES, Fonts, logo, rgb  # noqa: E402

W, H = 1080, 1920


def backdrop(c1, c2):
    a, b = rgb(c1), rgb(c2)
    small = Image.new("RGB", (W // 8, H // 8))
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            t = min(1, (x / small.width * 0.4 + y / small.height * 0.6) * 1.05)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return small.resize((W, H), Image.BICUBIC)


def place(canvas, slide, box_w, top):
    """Paste a slide scaled to box_w wide with rounded corners and a soft shadow; returns its bottom edge."""
    s = slide.convert("RGB").resize((box_w, round(slide.height * box_w / slide.width)), Image.LANCZOS)
    x = (W - s.width) // 2
    r = 36
    mask = Image.new("L", s.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s.width - 1, s.height - 1], radius=r, fill=255)
    pad = 120   # room for the blur to fade out completely (no hard edge)
    shadow = Image.new("L", (s.width + 2 * pad, s.height + 2 * pad), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([pad, pad + 12, s.width + pad, s.height + pad + 12], radius=r, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    canvas.paste((0, 0, 0), (x - pad, top - pad), shadow)
    canvas.paste(s, (x, top), mask)
    return top + s.height


def story(folder, facts, root):
    """story.jpg from slides/01.jpg."""
    folder, root = Path(folder), Path(root)
    c1, c2, ink = THEMES.get(facts["promo"]["id"], DEFAULT)
    F = Fonts(root / "assets" / "fonts" / "BricolageGrotesque.ttf")
    img = backdrop(c1, c2)
    d = ImageDraw.Draw(img, "RGBA")
    logo(d, W // 2 - 150, 236, 1.1)
    d.text((W // 2 - 70, 271), "Toy Ticker", font=F(42, 700), fill=ink, anchor="lm")
    bottom = place(img, Image.open(folder / "slides" / "01.jpg"), 820, 360)
    y = bottom + 56
    d.text((W // 2, y), "Every price, updated daily", font=F(46, 700), fill=ink, anchor="mt")
    # A small chevron pointing at the space left for the link sticker.
    cy = y + 92
    d.line([(W // 2 - 26, cy), (W // 2, cy + 22), (W // 2 + 26, cy)], fill=ink, width=7, joint="curve")
    img.save(folder / "story.jpg", "JPEG", quality=90, optimize=True)
    return folder / "story.jpg"


MUSIC_EXTS = (".mp3", ".m4a", ".aac", ".wav")


def find_music(folder, root):
    """The track for a Reel: music.* in the post's folder, else the signature track in assets/music/, else None.
    Use only music licensed for Instagram (e.g. Meta Sound Collection); see SOCIAL.md."""
    for d, stem in ((Path(folder), "music"), (Path(root) / "assets" / "music", None)):
        if d.is_dir():
            for p in sorted(d.iterdir()):
                if p.suffix.lower() in MUSIC_EXTS and (stem is None or p.stem == stem):
                    return p
    return None


def reel(folder, facts, root, seconds=3.0, fade=0.35, fps=30, music=None):
    """reel.mp4 from every slide, with music if a track is found (find_music) or given; needs ffmpeg
    (Homebrew or imageio-ffmpeg). Returns the path, or None."""
    folder = Path(folder)
    music = Path(music) if music else find_music(folder, root)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return None
    c1, c2, _ = THEMES.get(facts["promo"]["id"], DEFAULT)
    slides = sorted((folder / "slides").glob("*.jpg"))
    if not slides:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for i, p in enumerate(slides):
            f = backdrop(c1, c2)
            place(f, Image.open(p), 960, 300)
            frames.append(Path(tmp) / f"{i:02d}.png")
            f.save(frames[-1])
        hold = [seconds + 0.5 if i == 0 else seconds for i in range(len(frames))]   # a beat longer on the cover
        cmd = [ffmpeg, "-y", "-loglevel", "error"]
        for p, t in zip(frames, hold):
            cmd += ["-loop", "1", "-t", f"{t + fade:.2f}", "-i", str(p)]
        chain, last, offset = [], "[0:v]", 0.0
        for i in range(1, len(frames)):
            offset += hold[i - 1]
            out = f"[v{i}]"
            chain.append(f"{last}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}{out}")
            last = out
        graph = ";".join(chain) + f";{last}format=yuv420p,fps={fps}[out]" if chain else f"[0:v]format=yuv420p,fps={fps}[out]"
        out = folder / "reel.mp4"
        total = sum(hold) + fade
        maps = ["-map", "[out]"]
        if music:
            # Loop the track if it's short, cut it to the video, fade in and out.
            cmd += ["-stream_loop", "-1", "-i", str(music)]
            a = len(frames)
            graph += (f";[{a}:a]atrim=0:{total:.2f},asetpts=PTS-STARTPTS,afade=t=in:d=0.6,"
                      f"afade=t=out:st={max(0, total - 1.8):.2f}:d=1.8,volume=0.9[aout]")
            maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-filter_complex", graph, *maps, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    return out
