# Daily Instagram draft (instructions for the local scheduled task)

Runs every evening at 7pm Pacific on the owner's Mac, from the Claude desktop app. You draft today's Toy Ticker Instagram carousel from this repo's price data and leave it for the owner to review. You do not post anything to Instagram, and you do not commit or push.

You are the writer. Code picks the facts, checks your work and draws the slides.

## Steps

1. **Get today's data.** From the repo root: `git pull --rebase --autostash -q origin main`. If that fails (offline, conflict), continue with the data already here and mention it in your report.

1b. **Check the queue first.** Read `social/queue.json` (a list; missing or empty means nothing is queued). If an entry has `"post_on"` equal to today's date, today's post is that queued post instead of the weekday series (when `"replaces_series"` is true): the owner already approved its idea and wording, so refresh it rather than writing something new:
   - Make today's folder by copying the queued folder's `post.json` (and any `music.*`) into `social/<today>-<same name after the date>/`, then build today's facts there: `.venv/bin/python -c "import sys,json; sys.path.insert(0,'scripts/social'); import facts; json.dump(facts.build('.'), open('<new folder>/facts.json','w'), ensure_ascii=False, indent=1)"`.
   - For each item in `"screenshots"`, retake the site screenshot: `.venv/bin/python scripts/social/screenshot.py <new folder> <item id>`.
   - Update every fact ID and every number in the slides, caption, alt text, Threads posts and hook to tonight's facts (look each one up again by item and fact kind; never reuse an old number). If a claim stopped being true (e.g. "priciest card", a break-even that no longer exists), rewrite that line in the same voice, keeping it short.
   - Run step 4 (check and draw) and step 5 (look at every slide and the Reel's frames) on the new folder, then skip to the report. In the report, say it's the queued post and what changed from the approved version.
   - If the entry has a `"refresh_note"`, follow it (e.g. re-sort a ranked list by tonight's prices).
   - Remove that entry from `social/queue.json` only after the check passes.

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
    "caption": "...", "hashtags": ["#HappyMeal"], "alt_text": ["one per slide"],
    "threads": ["1 or 2 short Threads posts, each ending with toy-ticker.github.io"], "threads_topic": "Pokemon Happy Meal"}
   ```
   `topic` must be today's series. Every slide has all eight fields; unused ones are `""` or `[]`. Every number must be copied exactly from a fact's `display` text.

4. **Check and draw.**
   ```bash
   .venv/bin/python scripts/social/draft.py --post <folder>/post.json
   ```
   If it prints problems, fix `post.json` and run it again, up to 3 attempts. If problems remain, leave them; the owner will see them in `post.json` under `problems`.
   The same command also writes `<folder>/story.jpg` (1080x1920 Story with room for the link sticker) and `<folder>/reel.mp4` (slideshow Reel with music from the library in `assets/music/`) and `<folder>/threads.txt` (the Threads posts and topic). Rerun it after any fix so they match the slides.

5. **Look at every slide** in `<folder>/slides/` and at `story.jpg`. Fix anything cut off, overlapping or hard to read by shortening text in post.json and rerunning step 4.

6. **Scout new music** for the Reel, **on Sundays only** (skip this step on other days: less automated browsing keeps the Meta accounts safe; see "Account safety" in SOCIAL.md). In Chrome, open https://www.facebook.com/sound (Meta Sound Collection: free and licensed for Instagram). Browse or search for tracks that suit today's post (start with keywords like chiptune, 8-bit, playful, upbeat pop, quirky, bouncy, happy ukulele, funky, retro arcade). Pick **2 or 3** that are instrumental, upbeat, start strong in the first second, and are at least 20 seconds long; skip anything already in `assets/music/` (compare names). Listen-check by reading the page's mood/genre/length details; don't download anything yet. Note each track's exact title, artist if shown, length, mood/genre and its page link.

7. **Only if the owner approves a track in this session** (e.g. "use track 2"): download it from its Meta Sound Collection page in Chrome (it lands in ~/Downloads, usually as an .mp4 containing only audio), then add it and rebuild the Reel:
   ```bash
   .venv/bin/python scripts/social/add_music.py ~/Downloads/"<file name>" --post <folder>
   .venv/bin/python scripts/social/draft.py --post <folder>/post.json
   ```
   That saves the track to the library for future Reels and makes this post's Reel use it.

8. **Threads, only if the owner asks in this session** (e.g. "post the threads"): follow `scripts/social/THREADS.md` exactly. It posts through Chrome, at most 1 Threads post a day, and stops before Post for the owner's yes.

## Don't

- Don't download music (or any file) before the owner approves that specific track in this session.
- Don't open Instagram, and don't browse Facebook beyond the Sunday music search. Open Threads only for step 8.
- Don't change any file outside `<folder>/` and `assets/music/` (the latter only via add_music.py after approval).
- Don't commit or push, and don't post anywhere except Threads via step 8 after the owner's yes.
- Don't invent, round or compute numbers, or add claims that aren't in facts.json.

## Report

End with: the series, the folder, the cover headline, the caption, whether the check passed, whether story.jpg and reel.mp4 were made (and which library track the Reel uses), the Threads post(s) from threads.txt with "Say 'post the threads' to post #1 to Threads", then the numbered new-music suggestions (title, length, mood, link) and ask whether to use one for this Reel. Keep it short so it reads well as a notification.
