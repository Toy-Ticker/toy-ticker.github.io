# Posting to Threads with Chrome

The owner chose (Nov 15) to post Toy Ticker's Threads posts through Claude in Chrome rather than from their phone. Instagram stays phone-only (see "Account safety" in SOCIAL.md). Threads and Instagram can share one Meta login, so a flag on one can affect the other: keep Threads automation small, slow and visibly human-approved.

## When

Only when the owner asks in the session ("post the threads", "post threads post 1"), usually after the 7pm draft. Never on a schedule by itself, never unattended.

## Limits

- **1 Threads post a day** (check `social/threads/log.jsonl`). The second draft in `threads.txt` is for another day, or for the owner to post themselves.
- Only post. No likes, follows, replies, reposts, DMs, feed scrolling or profile browsing.
- One page load to open the composer; no retries in a loop. If anything fails twice, stop and tell the owner.
- If Threads shows a login page, a "confirm you're human" check, a CAPTCHA, a warning, or anything unusual: stop and tell the owner. Never solve or get around it, and never type a password.

## Steps

1. Read `<folder>/threads.txt` and the log. Pick the post the owner named (default: post 1). Show the owner the exact text and topic once more.
2. In Chrome (Claude in Chrome extension), open https://www.threads.com/ in a new tab. Confirm the signed-in profile is **toy_ticker** (profile icon or the composer's name). If it's anyone else, stop.
3. Open the composer ("What's new?" / the + button). Type the post text exactly as in threads.txt. Add the topic with the composer's topic option ("Add a topic") using `Topic:` from threads.txt; if there's no such option, skip it (don't type a #). If threads.txt lists "Poll options" under this post, add a poll with the composer's poll button and enter the options in order.
4. Check the link preview appeared for toy-ticker.github.io. Take a screenshot and **stop before Post**. Ask the owner: "Post this to Threads?" Click **Post** only after a clear yes for this post.
5. After it's live, open nothing else. Append a line to `social/threads/log.jsonl`: `{"date": "YYYY-MM-DD", "folder": "...", "post": 1, "text": "..."}`. Close the tab and report "Posted to Threads".

## Don't

- Don't open Instagram from this flow.
- Don't edit or delete posts unless the owner asks for that specific post.
- Don't commit or push.
