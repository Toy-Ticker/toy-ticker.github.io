# Instagram Post Agent Plan

As of 2026-11-15 · companion to [SOCIAL.md](SOCIAL.md)

An agent that turns Toy Ticker's daily prices into Instagram carousel posts on a schedule. You approve each post with one click.

## The short version

```
GitHub Action (cron, Sun + Wed)
  │
  ├─ 1. Pick facts       scripts/social/facts.py   prices.json → facts.json (numbers only, no AI)
  ├─ 2. Write the post   scripts/social/write.py   Claude → post.json (slides text, caption, alt text)
  ├─ 3. Check the post   scripts/social/check.py   rules + every number matches facts.json
  ├─ 4. Draw slides      scripts/social/render.py  Pillow → 1080×1350 JPEGs (same fonts/themes as og.py)
  └─ 5. Open a PR        "Instagram: weekly board, Nov 23"  ← you review images + caption
                                   │ merge = approve
                                   ▼
GitHub Action (on merge to main, after Pages deploys)
  └─ 6. Publish          scripts/social/publish.py  Instagram API → carousel live
```

**Why it's built this way:**
- **No AI for the numbers.** Prices come only from `prices.json`. Claude writes the words and chooses the angle, and a check makes sure it didn't invent or change any number. A wrong price is the biggest risk listed in the roadmap.
- **No AI images.** Slides are drawn by code from real data and official photos, the same way the link-preview images in `og/` already are.
- **Merging a PR is the approval.** No new tools or dashboards. You can approve from the GitHub app on your phone, and every post that has ever gone out is kept in git.
- **GitHub Pages hosts the images.** Instagram's API only accepts images at a public URL. When you merge, the slides go live on the site, so they get a public address with no extra hosting.
- **A fixed pipeline with one Claude step, not an open-ended agent.** It's cheaper, predictable and easy to debug. It can grow into a fuller agent later if needed (see Phase 4).

## What you set up by hand (once, ~1 hour)

1. **Instagram account** `@toyticker` (email toyticker@gmail.com, 2FA on), then switch it to a **professional account** (Creator or Business, both free) in Instagram settings.
2. **Meta developer app** at developers.facebook.com, using the **"Instagram API with Instagram Login"** product. It doesn't need a Facebook Page. Add `@toyticker` as a tester and grant `instagram_business_basic` and `instagram_business_content_publish`.
   While the app only posts to your own account, it should be able to stay in development mode without App Review. Check this during setup; Meta changes these rules often.
3. **Long-lived access token** (valid 60 days, refreshable), plus the Instagram user ID.
4. **Anthropic API key** from console.anthropic.com, with a monthly spend limit set (e.g. $5).
5. **GitHub repo secrets:** `IG_USER_ID`, `IG_ACCESS_TOKEN`, `ANTHROPIC_API_KEY`, and `GH_SECRETS_TOKEN` (a fine-grained token that can only write this repo's secrets, used to refresh the Instagram token).

Secrets live only in GitHub secrets, never in the repo or in a post file.

## Phase 1: drafts only, no posting (week of Nov 16) — built Nov 15

Goal: every Sunday a PR shows up with a finished post that you then upload by hand. This tests the content before anything is automated.

**How it runs (updated Nov 15): a daily local scheduled task**, "Toy Ticker daily Instagram draft", in the Claude desktop app at **7pm Pacific every day** (on your Claude plan, no API key, no GitHub connection). It follows [scripts/social/LOCAL.md](scripts/social/LOCAL.md): pull the latest prices, `draft.py --facts-only --topic today` picks the weekday's series (see the daily lineup in SOCIAL.md) and writes the facts, the session writes `post.json` following `prompt.md`, `draft.py --post` checks it and draws the slides into `social/<date>-<series>/`. It never posts, commits or overwrites an existing draft (a second draft on the same day goes to `<folder>-2`). Your Mac must be awake with the app open; a missed run happens the next time the app opens. Manage it in the app's Scheduled section. You review the draft, then posting goes through Chrome with your OK before Share.

Alternatives kept for later: [scripts/social/ROUTINE.md](scripts/social/ROUTINE.md) (a cloud Claude Code routine that opens a PR; needs GitHub connected on the Claude account the app uses) and the manual GitHub Action `social-draft.yml` (Claude API; needs the `ANTHROPIC_API_KEY` secret).

**Each week:** open the PR, check the slides and caption, save the slides from the Files tab, post them to Instagram as one carousel, paste the caption, then merge the PR (merged posts are how the agent avoids repeating itself).

Test the slides locally without an API call: `python scripts/social/draft.py --sample` (writes to `social/<date>-weekly-board-sample/`, which git ignores).

**Rule-change dates:** `RULE_CHANGES` in `scripts/social/facts.py` lists days the price rules changed (Nov 14: shipping fix). Price changes are never measured across one, so add a date there whenever the matching or shipping rules change. Because of the Nov 14 change, "risers" and "fallers" stay empty until Nov 17 (at least 3 clean days).

**`facts.py`: what's worth posting this week.** Pure Python, reading `data/prices.json` and the listing ledger:
- Top 5 items by median price in the current series, with week-over-week change
- Biggest risers and fallers (only items with at least 5 listings, so thin markets don't make the list)
- Complete set as singles vs as a set
- Days left in the promo (from `data/config.json`)
- Most sold this week and typical days to sell
- Last 8 posts' topics (from `social/` history), so the agent doesn't repeat itself

The output is a small `facts.json`, and every number in it has an ID (`f1`, `f2`…).

**`write.py`: one Claude call.**
- Model: `claude-opus-5-5`. One request a week costs well under $0.20; at two posts a week that's about a dollar a month.
- Fallback: on by default (`fallbacks: "default"`), so a declined request retries on another model instead of failing the run.
- Structured output (`output_config.format` with a JSON schema) returns:
  ```json
  {
    "topic": "weekly_board | worth_it | countdown",
    "slides": [{"layout": "cover|ranked_list|item|cta", "headline": "...", "items": [{"item_id": "...", "fact_ids": ["f3"]}]}],
    "caption": "...",
    "hashtags": ["#HappyMeal", "..."],
    "alt_text": ["one per slide"]
  }
  ```
- The prompt holds the voice guide and the Rules section of SOCIAL.md, as fixed text so it can be cached. Slides refer to numbers by fact ID; the renderer fills in the real values. The caption may quote numbers, and the check verifies them.

**`check.py`: fail the run rather than post something wrong.**
- Every number in the caption and headlines appears in `facts.json` (after rounding).
- Banned phrases: "will go up", "invest", "guaranteed", "buy now before", "price prediction"…
- Caption under 2,200 characters, at most 5 hashtags, 3–10 slides, alt text for every slide.
- "Not affiliated with McDonald's" appears on the last slide (drawn by the renderer, not written by the AI).
- If the check fails, it retries Claude once with the errors listed. If that also fails, it opens the PR marked **Needs edit** instead of dropping the post.

**`render.py`: the slides.** 1080×1350 JPEGs (4:5, the tallest shape the feed allows), reusing `og.py`'s theme colours and Bricolage/Inter fonts. Four layouts: cover, ranked list, single item (photo + price + mini chart), and call to action ("Every toy's price: link in bio"). Output goes to `social/2026-11-23-weekly-board/`.

**The pull request** (opened by the routine, or by the manual `social-draft.yml` workflow):
- Runs Sundays after the daily price job.
- Opens a PR on branch `claude/social-<date>-<topic>` (the workflow uses `social/…`). The PR body shows the caption ready to copy, the slide images and a "facts used" table.

**Done when:** three Sunday drafts in a row needed little or no editing before you posted them by hand.

## Phase 2: publish on merge (from about Dec 1)

**`publish.py`:** uses Instagram's three-step publishing:
1. Create one media container per slide (`image_url` = the slide's Pages URL, `is_carousel_item=true`).
2. Create the carousel container with the slide container IDs and the caption.
3. Publish it, then write the Instagram post ID and permalink back into `social/<date>/post.json`.

**Workflow `.github/workflows/social-publish.yml`:**
- Runs when a PR from a `social/*` branch is merged.
- Waits until every slide URL on Pages returns 200 (Pages takes a minute or two to deploy), then publishes.
- Optional `publish_at` in `post.json`: the job waits for that time on a schedule instead of posting the moment you merge. That lets you approve on Saturday and post at the best time.
- If anything fails, it comments on the PR with the error. It never retries the publish step on its own, so a post can't go out twice.

**Token refresh:** a monthly job refreshes the 60-day Instagram token and saves it back with `gh secret set` using `GH_SECRETS_TOKEN`. If the refresh fails, it opens an issue, so you hear about it weeks before the token expires.

## Phase 3: learn from results (after ~4 weeks of posts)

- **`insights.py`** pulls each post's reach, saves, shares and profile visits from the Instagram API 7 days after it goes up and saves them to `social/insights.json`. This fills in the Instagram part of the weekly review table in SOCIAL.md.
- `facts.py` passes the last 8 posts' results to Claude, so it can favour the topics and hooks that worked.
- Add **Wednesday** posts ("Worth it?" for one item, or a countdown) once Sundays run smoothly.
- **Dec 7–14 countdown:** a daily post from the same pipeline (`topic: countdown`), all drafted in one PR on Dec 6 with `publish_at` times, so you approve one week of posts in one go.

## Phase 4: optional, only if it earns it

- **Skip review for the routine weekly board.** Once ~6 posts in a row merged without edits, the board can publish automatically. Anything else still waits for you.
- **New-series launch post.** When the series launch kit (roadmap Next #1) adds a series, it also drafts a launch post.
- **Reels from the same slides** (simple slideshow video), if you want video reach later without filming anything.
- **Fuller agent:** if the pipeline ever needs to look things up on its own (e.g. check what the next promo is), move step 2 to a Claude agent with tools. Until then, one call is enough.

## Files this adds

```
scripts/social/ROUTINE.md         instructions the weekly Claude Code routine follows
scripts/social/draft.py           runs the steps below and writes the PR description (Phase 1)
scripts/social/facts.py  write.py  check.py  render.py   (Phase 1, built)
scripts/social/publish.py  insights.py                   (Phases 2–3)
scripts/social/prompt.md          voice guide + rules (cached system prompt)
.github/workflows/social-draft.yml  social-publish.yml  social-token.yml
social/<date>-<topic>/            slides/*.jpg, post.json, facts.json
```

## Costs

| Item | Cost |
| --- | --- |
| Claude API, ~10 posts/month | about $1–2 a month |
| GitHub Actions | free on a public repo |
| Instagram API, Meta app | free |
| Your time | ~5 min per post to review the PR |

## Risks

| Risk | Mitigation |
| --- | --- |
| Wrong number gets posted | Numbers come from code; check.py rejects any number not in facts.json; you review every PR |
| Meta changes API or app rules | Phase 1 works without the API; fall back to manual upload from the PR |
| Token expires quietly | Monthly refresh job; opens an issue if it fails |
| Posts start to feel samey | Topic history in the prompt; results feed back into the prompt in Phase 3 |
| Account flagged as a bot | Low volume (2–7 posts/week), official API only, no auto-likes, auto-follows or auto-DMs |

## Decisions for you

- [ ] Days and times: Sunday + Wednesday to start? (Instagram's own Insights will show when followers are online after a few weeks.)
- [ ] Should the slides use the official toy photos (as the site does), or only charts and text?
- [ ] Phase 1 as the first build, starting this week?
