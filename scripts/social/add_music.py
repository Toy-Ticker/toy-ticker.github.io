"""Add a downloaded track (e.g. from Meta Sound Collection) to the Reel music library.

    .venv/bin/python scripts/social/add_music.py ~/Downloads/"Some Track.mp4" [--post social/<folder>]

Keeps only the audio, evens out the loudness (-16 LUFS, like the other tracks), converts to 44.1 kHz stereo AAC
(Instagram's web upload stalls on 48 kHz), and trims silence at the start and end so short tracks loop cleanly.
Saves assets/music/<slug>.m4a. With --post, also copies it to <folder>/music.m4a so that post's Reel uses it.
assets/music/ is gitignored: the tracks are licensed for posting on Instagram, not for sharing the files.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "assets" / "music"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "track"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--post", help="a post folder whose Reel should use this track")
    args = ap.parse_args()
    src = Path(args.src).expanduser()
    if not src.is_file():
        sys.exit(f"Not found: {src}")
    ffmpeg = shutil.which("ffmpeg") or sys.exit("ffmpeg not found")
    LIB.mkdir(parents=True, exist_ok=True)
    out = LIB / f"{slug(src.stem)}.m4a"
    # Trim leading/trailing silence (reverse trick for the tail), then normalise loudness.
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse")
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(src), "-vn",
                    "-af", f"{trim},loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "2",
                    "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                         capture_output=True, text=True).stdout.strip()
    print(f"{out.relative_to(ROOT)}  ({float(dur):.1f} s)")
    if args.post:
        post = Path(args.post)
        if not post.is_absolute():
            post = ROOT / post
        shutil.copy(out, post / "music.m4a")
        print(f"{(post / 'music.m4a').relative_to(ROOT)}  (this post's Reel)")


if __name__ == "__main__":
    main()
