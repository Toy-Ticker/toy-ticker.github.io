# Reply drafts for popular posts (instructions for the scheduled task)

Runs every 3 hours, 9am–9pm Pacific, on the owner's Mac. You find popular Instagram posts about the Pokémon Happy Meal (or whatever Happy Meal promo is current), draft a few short replies to commenters using Toy Ticker's price data, and **ask the owner to approve them**. You post only what the owner approves, in this session, as @toy_ticker.

Goal: people reading a popular post see a genuinely useful price fact from @toy_ticker, tap the profile, and follow the bio link to https://toy-ticker.github.io/.

## Steps

1. **Today's numbers.** From the repo root `/Users/lungfaing/toy-ticker`:
   ```bash
   git pull --rebase --autostash -q origin main
   mkdir -p social/replies
   .venv/bin/python scripts/social/facts.py > social/replies/facts-$(date +%F).json
   ```
   Every number in a reply must be copied from a fact's `display` in that file (rounding "$64.09" to "like $64" is fine in casual speech; nothing else may be computed or invented).

2. **Check today's limits.** Read `social/replies/log.jsonl` (one JSON line per posted reply: `date`, `post_url`, `comment_user`, `text`). If 10 or more replies were posted today, stop and report "daily limit reached". Never draft for a post that already has a @toy_ticker comment or appears in the log.

3. **Find posts** in Chrome (read only: do not like, follow, comment or DM while browsing):
   - Look at https://www.instagram.com/explore/tags/pokemonhappymeal/ and https://www.instagram.com/explore/tags/mcdonaldspokemon/ (and the current promo's tags if it isn't Pokémon).
   - Pick up to **3 posts** that are under 48 hours old (prefer under 24) and have at least 20 comments or 1,000 likes. Skip giveaways, ads, accounts selling toys, and posts not about the Happy Meal toys/cards.
   - Also check the newest posts on https://www.instagram.com/officialhappymeal/ and https://www.instagram.com/mcdonalds/ that are about Happy Meal toys. If one is under 24 hours old, include it (it counts toward the 3 posts) but draft **at most 1 reply** on it: official brand posts filter spam heavily. A new Happy Meal launch post is the best case: be early, with a useful price fact about the series it announces or the one it replaces.
   - Open each and read its top comments.

4. **Draft replies:** up to **3 per post**, only to comments the data genuinely answers (what something sells for, extras/duplicates, complete sets, which ones are scarce or sell fast, "is it worth it"). The style the owner approved:
   - lowercase, short (one sentence or two), casual ("rn", "lol", "like"), at most one emoji
   - react to the person first, then **one** fact
   - say "ebay" (US prices); no links, no "Toy Ticker", no "check out", no hashtags
   - never pretend to be a collector or claim experiences ("i got two weedles too"); sympathy like "same 😭" is fine
   - no predictions or investment talk ("will go up", "invest", "grab them before…")
   - never reuse a reply's wording; vary openings
   - a question back ("which ones are you still missing?") is fine instead of a fact
   Approved examples: "same 😭 there's like 97 weedles on ebay rn so they're basically trade bait lol" · "all 15 cards is impressive 👀 full sets go for like $64 on ebay rn" · "good pick 🖤 umbreon's been flying off ebay"

5. **Save and ask.** Write the drafts to `social/replies/<date>-<HHMM>.md`: for each post its URL, author, age, likes/comments; for each draft the comment you're replying to (user + text), your reply, and the fact ID(s) it uses. Then **end your turn with the numbered list of drafts and ask the owner which to post** (e.g. "post 1, 3, 4", "post all", "skip"). If you found nothing worth replying to, say so briefly and stop.

6. **Only after the owner's explicit approval in this session**, post exactly the approved drafts (or the owner's edited wording) in Chrome as @toy_ticker:
   - open the post, click **Reply** under the comment, and confirm the box starts with `@<their username>` before typing; if it doesn't, click Reply again
   - type the reply, click **Post**, wait a few seconds, and confirm it appears (the comment count goes up)
   - space replies out by at least 20 seconds
   - append each posted reply to `social/replies/log.jsonl`
   - if Instagram shows any warning ("action blocked", "try again later", unusual activity), stop immediately and tell the owner

## Don't

- Don't post, like, follow or DM anything without the owner's explicit approval in this session.
- Don't post more than 10 replies a day in total, or more than 3 on one post.
- Don't change files outside `social/replies/`; don't commit or push.

## Report

Keep it short so it reads well as a notification: how many posts and drafts, then the numbered drafts, then the question.
