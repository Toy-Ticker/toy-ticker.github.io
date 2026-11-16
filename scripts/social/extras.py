"""Story image and Reel video for a drafted post, made from its slides (no new numbers, no AI).

    story.jpg  1080x1920: the cover slide on the series colours, with room below for Instagram's link sticker.
    reel.mp4   1080x1920: every slide in order (about 3 s each, short crossfades), silent; add trending audio
               in the Instagram app when posting.

Instagram covers the top and bottom of Stories and Reels with its own buttons, so content stays inside a safe
area (roughly 250 px top, 340 px bottom).
"""
import hashlib
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
    """The track for a Reel: music.* in the post's folder if there is one; else the library track this post used
    before (reel_music.txt, so redrawing keeps it); else the library track used least recently by other posts'
    Reels, so back-to-back Reels don't share music. assets/music/ is kept out of git (the repo is public; the
    tracks are licensed for Instagram use, not to share). Use only music licensed for Instagram (e.g. Meta Sound
    Collection); see SOCIAL.md."""
    folder = Path(folder)
    own = [p for p in sorted(folder.glob("music.*")) if p.suffix.lower() in MUSIC_EXTS]
    if own:
        return own[0]
    lib = Path(root) / "assets" / "music"
    tracks = sorted(p for p in lib.iterdir() if p.suffix.lower() in MUSIC_EXTS) if lib.is_dir() else []
    if not tracks:
        return None
    by_name = {t.name: t for t in tracks}
    mine = folder / "reel_music.txt"
    if mine.exists() and mine.read_text().strip() in by_name:
        return by_name[mine.read_text().strip()]
    # When each other post last used each track (newest folder first: date in the name, then file time).
    last_used = {}
    for rec in folder.parent.glob("*/reel_music.txt"):
        if rec.parent == folder:
            continue
        name = rec.read_text().strip()
        key = (rec.parent.name[:10], rec.stat().st_mtime)
        if name in by_name and key > last_used.get(name, ("", 0)):
            last_used[name] = key
    seed = int(hashlib.md5(folder.name.encode()).hexdigest(), 16)
    pick = min(tracks, key=lambda t: (last_used.get(t.name, ("", 0)), (seed + tracks.index(t)) % len(tracks)))
    mine.write_text(pick.name + "\n")
    return pick


def hook_frames(hook, facts, root, out_dir, fps=30, seconds=1.6):
    """The Reel's opener: a full-screen card with the hook text big at the top and the toy's photo below it,
    slowly zooming in. Text is there from the very first frame (that frame is what people see before it
    plays, and what decides whether they keep scrolling). Returns the PNG paths, one per video frame."""
    from render import text_block, trim
    root = Path(root)
    c1, c2, ink = THEMES.get(facts["promo"]["id"], DEFAULT)
    F = Fonts(root / "assets" / "fonts" / "BricolageGrotesque.ttf")
    base = backdrop(c1, c2)
    d = ImageDraw.Draw(base)
    text_end = text_block(d, (72, 290), hook["text"], F, W - 144, 170, 800, ink, 3, 84, 1.0)
    items = {i["id"]: i for i in facts["items"]}
    ids = hook.get("item_ids") or ([hook["item_id"]] if hook.get("item_id") else [])
    photos = [trim(Image.open(root / items[i]["image"]).convert("RGBA")) for i in ids[:2] if items.get(i, {}).get("image")]
    paths, n = [], round(fps * seconds)
    for k in range(n):
        f = base.copy()
        t = k / max(1, n - 1)
        pop = 1 - (1 - min(1, t / 0.25)) ** 3            # quick ease-out pop over the first quarter
        scale = (0.80 + 0.20 * pop) * (1 + 0.10 * t)       # then a push in
        size = 620 if len(photos) == 1 else 470
        box = size * scale
        # Below the text (sized at full zoom so it never grows into it), above Instagram's bottom buttons (~340 px).
        cy = int(min(H - 360 - size * 1.1 / 2, max(1180, text_end + 50 + size * 1.1 / 2)))
        centers = [W // 2] if len(photos) == 1 else [W // 2 - 255, W // 2 + 255]
        for ph0, cx in zip(photos, centers):
            r = box / max(ph0.size)
            ph = ph0.resize((max(1, int(ph0.width * r)), max(1, int(ph0.height * r))), Image.LANCZOS)
            f.paste(ph, (cx - ph.width // 2, cy - ph.height // 2), ph)
        if len(photos) == 2:   # a VS badge between them
            dd = ImageDraw.Draw(f)
            rr = int(70 * scale)
            dd.ellipse([W // 2 - rr, cy - rr, W // 2 + rr, cy + rr], fill="#dc2626", outline="white", width=8)
            dd.text((W // 2, cy), "VS", font=F(int(64 * scale), 800), fill="white", anchor="mm")
        paths.append(Path(out_dir) / f"hook_{k:03d}.png")
        f.save(paths[-1])
    return paths


def reel(folder, facts, root, seconds=3.0, fade=0.35, fps=30, music=None, hook=None):
    """reel.mp4 from every slide, with music if a track is found (find_music) or given; needs ffmpeg
    (Homebrew or imageio-ffmpeg). With a hook ({"text", "item_ids"} (1 or 2 items) from post.json's reel_hook) it opens on a
    1.6 s full-screen hook card and the slides move faster (2.5 s each). Returns the path, or None."""
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
        cmd = [ffmpeg, "-y", "-loglevel", "error"]
        if hook and hook.get("text"):
            seconds, hook_s = 2.5, 1.6
            hook_frames(hook, facts, root, tmp, fps, hook_s)
            hold = [hook_s] + [seconds] * len(frames)
            cmd += ["-framerate", str(fps), "-i", str(Path(tmp) / "hook_%03d.png")]
            frames = [None] + frames
        else:
            hold = [seconds + 0.5 if i == 0 else seconds for i in range(len(frames))]   # a beat longer on the cover
        for p, t in zip(frames, hold):
            if p is not None:
                cmd += ["-loop", "1", "-t", f"{t + fade:.2f}", "-i", str(p)]
        chain, last, offset = [], "[0:v]", 0.0
        src = [f"[{i}:v]" for i in range(len(frames))]
        if frames and frames[0] is None:
            # The hook clip and the still slides must share frame rate and timebase for xfade.
            chain.append(f"[0:v]fps={fps},settb=AVTB,tpad=stop_mode=clone:stop_duration={fade:.2f}[h0]")
            last = "[h0]"
            for i in range(1, len(frames)):
                chain.append(f"[{i}:v]fps={fps},settb=AVTB[s{i}]")
                src[i] = f"[s{i}]"
        for i in range(1, len(frames)):
            offset += hold[i - 1]
            out = f"[v{i}]"
            chain.append(f"{last}{src[i]}xfade=transition=fade:duration={fade}:offset={offset:.2f}{out}")
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
            maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
        cmd += ["-filter_complex", graph, *maps, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    return out
