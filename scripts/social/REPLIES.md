# Reply drafts for popular posts

The owner finds popular Instagram posts about the current Happy Meal promo and shares their links. You draft a few short replies to commenters using Toy Ticker's price data. **The owner posts them from the Instagram app.** You never post, like, follow or DM, and you don't browse Instagram looking for posts (see "Account safety" in SOCIAL.md: on Nov 15 automated browsing and posting got @toy_ticker sent to a "Confirm you're human" check).

Goal: people reading a popular post see a genuinely useful price fact from @toy_ticker, tap the profile, and follow the bio link to https://toy-ticker.github.io/.

## Steps

1. **Today's numbers.** From the repo root `/Users/lungfaing/toy-ticker`:
   ```bash
   git pull --rebase --autostash -q origin main
   mkdir -p social/replies
   .venv/bin/python scripts/social/facts.py > social/replies/facts-$(date +%F).json
   ```
   For a past series, add its id: `.venv/bin/python -c "import sys; sys.path.insert(0,'scripts/social'); import facts, json; print(json.dumps(facts.build('.', series='<id>'), ensure_ascii=False))"`.
   Every number in a reply must be copied from a fact's `display` (rounding "$64.09" to "like $64" is fine in casual speech; nothing else may be computed or invented).

2. **The links.** Use the post links the owner pasted in chat, or the lines in `social/replies/links.txt`. Skip any link already in `social/replies/log.jsonl`. Check today's count in the log: while the account is warming up (see SOCIAL.md), drafts stop at **3 replies a day** in total.

3. **Read each post once.** Open the link (one page load per post, no scrolling through other pages, no hashtag or profile browsing) and read the post and its top comments. If the page asks to log in or shows any check, stop and tell the owner; don't try to get around it.

4. **Draft replies:** at most 3 per post (1 on official @mcdonalds / @officialhappymeal posts), only to comments the data genuinely answers (what something sells for, extras/duplicates, complete sets, which ones are scarce or sell fast, "is it worth it"). The style the owner approved:
   - lowercase, short (one sentence or two), casual ("rn", "lol", "like"), at most one emoji
   - react to the person first, then **one** fact
   - say "ebay" (US prices); no links, no "check out", no hashtags
   - **soft site mention, at most 1 in 3 replies** (owner's choice, Nov 15): when the comment asks what something is worth, or a running joke fits (the daily Weedle count), you may end with a short, honest pointer like "we track all of them daily, it's in our bio" or "we post the weedle count every day". Say "we" (the account), never pretend to be a random collector. Never the same pointer wording twice; no "Toy Ticker" brand name or URL in comments on other people's posts
   - never pretend to be a collector or claim experiences ("i got two weedles too"); sympathy like "same 😭" is fine
   - no predictions or investment talk ("will go up", "invest", "grab them before…")
   - never reuse a reply's wording; vary openings
   - a question back ("which ones are you still missing?") is fine instead of a fact
   Approved examples (with a soft mention: "97 weedles on ebay rn 💀 we post the weedle count every day if you wanna follow the chaos"): "same 😭 there's like 97 weedles on ebay rn so they're basically trade bait lol" · "all 15 cards is impressive 👀 full sets go for like $64 on ebay rn" · "good pick 🖤 umbreon's been flying off ebay"

5. **Save and hand over.** Write the drafts to `social/replies/<date>-<HHMM>.md`: for each, the post link, the commenter's username and comment, your reply, and the fact ID it uses. Show the owner a short numbered list. When they say which ones they posted, append those to `social/replies/log.jsonl` (`date`, `post_url`, `comment_user`, `text`).

## Don't

- Don't post, like, follow, DM, or browse Instagram beyond reading the shared links once.
- Don't change files outside `social/replies/`; don't commit or push.
