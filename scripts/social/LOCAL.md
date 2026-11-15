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

5. **Look at every slide** in `<folder>/slides/`. Fix anything cut off, overlapping or hard to read by shortening text in post.json and rerunning step 4.

## Don't

- Don't change any file outside `<folder>/`.
- Don't commit, push or post anywhere.
- Don't invent, round or compute numbers, or add claims that aren't in facts.json.

## Report

End with: the series, the folder, the cover headline, the caption, and whether the check passed. Keep it short so it reads well as a notification.
