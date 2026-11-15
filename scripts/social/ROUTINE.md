# Weekly Instagram draft (instructions for the Claude Code routine)

You are drafting one Instagram carousel post for Toy Ticker from this repo's price data, then opening a pull request so the owner can review it and post it by hand. You do not post anything to Instagram.

You are the writer. Code picks the facts, checks your work and draws the slides.

## Steps

1. **Set up.** From the repo root: `pip install pillow` (skip if already installed).

2. **Pick the topic.** Use `weekly_board`, unless the promo in restaurants has 7 or fewer days left, then use `countdown`. If unsure, run step 3 with `weekly_board` and read `promo.facts` in facts.json for days left.

3. **Get the facts.**
   ```bash
   python scripts/social/draft.py --facts-only --topic <topic>
   ```
   It prints a folder such as `social/2026-11-22-weekly-board`. Read `<folder>/facts.json`.
   If it says no series is in restaurants, stop and report that; there is nothing to post.

4. **Write the post.** Read `scripts/social/prompt.md` and follow it exactly: it is your brief (topics, slide layouts, caption rules, the number rule, the rules on predictions). Write the post as JSON to `<folder>/post.json` in this shape:
   ```json
   {"topic": "...", "slides": [{"layout": "cover|ranked_list|item|highlight|cta", "headline": "", "subhead": "", "item_ids": [],
     "rows": [{"item_id": "", "fact_ids": []}], "item_id": "", "fact_ids": [], "note": ""}],
    "caption": "...", "hashtags": ["#HappyMeal"], "alt_text": ["one per slide"]}
   ```
   Every slide has all eight fields; unused ones are `""` or `[]`. Every number you write must be copied exactly from a fact's `display` text.

5. **Check and draw.** Pick the branch name `claude/social-<folder name without social/>`, then:
   ```bash
   python scripts/social/draft.py --post <folder>/post.json --branch <branch>
   ```
   If it prints problems, fix `post.json` and run it again. Up to 3 attempts in all. If problems remain after that, continue anyway; the PR will be marked as needing edits.

6. **Look at the slides.** Open each `<folder>/slides/NN.jpg` and check nothing is cut off, overlapping or unreadable. If a headline is too long for its slide, shorten it in post.json and rerun step 5.

7. **Open the pull request.**
   - Create the branch, commit only `<folder>/` (nothing else in the repo), push it.
   - Open a PR against `main`. Title: `Instagram: <folder name>`, prefixed with `[Needs edit] ` if step 5 still had problems. Body: the contents of `<folder>/pr.md`.
   - If you can't open a PR from this session, push the branch anyway and end your report with the branch name, the title and the body so the owner can open it.

## Don't

- Don't change any file outside `<folder>/`, including the scripts, prompt.md or the data.
- Don't commit to `main` or merge anything.
- Don't invent, round or compute numbers; don't add claims that aren't in facts.json.
- Don't post to Instagram or any other site.

## Report

End with: the PR link (or branch), the topic, the cover headline, and whether the check passed.
