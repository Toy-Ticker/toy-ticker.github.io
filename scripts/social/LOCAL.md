# Daily Instagram draft (instructions for the local scheduled task)

Runs every evening at 7pm Pacific on the owner's Mac, from the Claude desktop app. You draft today's Toy Ticker Instagram carousel from this repo's price data and leave it for the owner to review. You do not post anything to Instagram, and you do not commit or push.

You are the writer. Code picks the facts, checks your work and draws the slides.

## Steps

1. **Get today's data.** From the repo root: `git pull --rebase --autostash -q origin main`. If that fails (offline, conflict), continue with the data already here and mention it in your report.

2. **Get the facts for today's series.**
   ```bash
   .venv/bin/python scripts/social/draft.py --facts-only --topic today
   ```
   It prints a folder such as `social/2026-11-17-card-spotlight`; the part after the date is today's series. Read `<folder>/facts.json`. If it says no series is in restaurants, stop and report that.
   If `.venv` is missing, create it once: `/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/pip install -q pillow`.

3. **Write the post.** Read `scripts/social/prompt.md` and follow it exactly (the series descriptions, slide layouts, caption rules, the number rule, no predictions). Write `<folder>/post.json` in this shape:
   ```json
   {"topic": "...", "slides": [{"layout": "cover|ranked_list|item|highlight|cta", "headline": "", "subhead": "", "item_ids": [],
     "rows": [{"item_id": "", "fact_ids": []}], "item_id": "", "fact_ids": [], "note": ""}],
    "caption": "...", "hashtags": ["#HappyMeal"], "alt_text": ["one per slide"]}
   ```
   `topic` must be today's series. Every slide has all eight fields; unused ones are `""` or `[]`. Every number must be copied exactly from a fact's `display` text.

4. **Check and draw.**
   ```bash
   .venv/bin/python scripts/social/draft.py --post <folder>/post.json
   ```
   If it prints problems, fix `post.json` and run it again, up to 3 attempts. If problems remain, leave them; the owner will see them in `post.json` under `problems`.
   The same command also writes `<folder>/story.jpg` (1080x1920 Story with room for the link sticker) and `<folder>/reel.mp4` (slideshow Reel with music from the library in `assets/music/`). Rerun it after any fix so they match the slides.

5. **Look at every slide** in `<folder>/slides/` and at `story.jpg`. Fix anything cut off, overlapping or hard to read by shortening text in post.json and rerunning step 4.

6. **Scout new music** for the Reel. In Chrome, open https://www.facebook.com/sound (Meta Sound Collection: free and licensed for Instagram). Browse or search for tracks that suit today's post (start with keywords like chiptune, 8-bit, playful, upbeat pop, quirky, bouncy, happy ukulele, funky, retro arcade). Pick **2 or 3** that are instrumental, upbeat, start strong in the first second, and are at least 20 seconds long; skip anything already in `assets/music/` (compare names). Listen-check by reading the page's mood/genre/length details; don't download anything yet. Note each track's exact title, artist if shown, length, mood/genre and its page link.

7. **Only if the owner approves a track in this session** (e.g. "use track 2"): download it from its Meta Sound Collection page in Chrome (it lands in ~/Downloads, usually as an .mp4 containing only audio), then add it and rebuild the Reel:
   ```bash
   .venv/bin/python scripts/social/add_music.py ~/Downloads/"<file name>" --post <folder>
   .venv/bin/python scripts/social/draft.py --post <folder>/post.json
   ```
   That saves the track to the library for future Reels and makes this post's Reel use it.

## Don't

- Don't download music (or any file) before the owner approves that specific track in this session.
- Don't change any file outside `<folder>/` and `assets/music/` (the latter only via add_music.py after approval).
- Don't commit, push or post anywhere.
- Don't invent, round or compute numbers, or add claims that aren't in facts.json.

## Report

End with: the series, the folder, the cover headline, the caption, whether the check passed, whether story.jpg and reel.mp4 were made (and which library track the Reel uses), then the numbered new-music suggestions (title, length, mood, link) and ask whether to use one for this Reel. Keep it short so it reads well as a notification.
