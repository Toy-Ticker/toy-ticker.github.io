# Toy Ticker Social Media Plan

As of 2026-11-15 · account email: toyticker@gmail.com

Social is how Toy Ticker gets found **before Google catches up** and how people **come back without accounts**.
It serves the roadmap's Now goal: win the Pokémon window that closes Dec 14.

Budget: about **2 hours a week** on top of the 6–8 for building. Everything below is sized to fit that.

## What social has to do

| Job | Why | Measure |
| --- | --- | --- |
| Get the site found | Search clicks are still small five days after launch; collectors trade tips in feeds and groups, not search | Link clicks reported by each platform; Search Console clicks for "toy ticker" |
| Bring people back | The site has no alerts yet (RSS feeds are in Now #2) | Followers; repeat link clicks on weekly posts |
| Build trust in the numbers | "Wrong price goes viral" is a listed risk; showing method and corrections in public defuses it | Replies asking "where's this from?" answered within a day |
| Pay its way | EPN and Ko-fi | EPN clicks and Ko-fi tips in weeks with posts vs without |

The site has no analytics, so every number comes from the platforms' own stats, Search Console, EPN and Ko-fi. Record them once a week (see Weekly review).

## Accounts

Claim **@toyticker** everywhere now, even on platforms that won't be used yet, so nobody else takes it.
Fallbacks if taken, in order: `@toytickerhq`, `@toyticker.prices`, `@toytickerapp`.

**Decision (Nov 15): Instagram first, image carousels, no video.** Posts are drafted on a schedule by the agent in [SOCIAL_AGENT.md](SOCIAL_AGENT.md). The other platforms come later, reusing the same images.

| Platform | Role | Priority |
| --- | --- | --- |
| **Instagram** (carousels) | First and only platform to start. Weekly price board and "Worth it?" carousels, made by the agent. Turn on Threads cross-posting | Now |
| **Facebook groups** | Where Happy Meal collectors and resellers actually trade. Answer price questions with item links; no content needed | Next (manual) |
| **TikTok** (photo mode) | The same carousel images as photo posts | Later |
| **X / Bluesky** | The same images; Bluesky's free API is easy to add to the agent | Later |
| **Video** (Reels, TikTok, Shorts) | Only if image posts show traction; a slideshow made from the same slides first | Maybe |
| Reddit | Ruled out as a data source; as distribution only for one-off data posts where a sub allows them (e.g. the "After the promo" chart) | Occasional |
| Pinterest, LinkedIn | Skip | — |

Setup checklist (one sitting, ~1 hour):

- [ ] Sign up with toyticker@gmail.com; turn on 2FA with an authenticator app on every account; keep recovery codes out of the repo.
- [ ] Avatar: the price-tag-with-sparkline logo (`assets/logo.svg`) on a solid background. No McDonald's, Pokémon or Happy Meal logos in the avatar, banner or name.
- [ ] Name: **Toy Ticker** · Bio: `Daily eBay prices for McDonald's Happy Meal toys & cards. Not affiliated with McDonald's. No ads, no accounts.`
- [x] Link: `https://toy-ticker.github.io/` (repo moved to the Toy-Ticker organization on Nov 15 so the address has no personal name; a short domain can be added later).
- [ ] Banner: `og/site.png`.
- [ ] Pinned post: "What Toy Ticker is" (template A below).
- [ ] Add the social links to the site footer and About page.

## Daily lineup (from Nov 16)

One Instagram carousel a day, drafted at 7pm Pacific by the local scheduled task (see SOCIAL_AGENT.md). Each weekday is its own series, labelled on the cover with its own colour dot. Every slide is a quick highlight: one point, one big number.

| Day | Series | What it shows |
| --- | --- | --- |
| Sun | WEEKLY SUMMARY | The week's 3–4 takeaways |
| Mon | CARD SPOTLIGHT | One card not featured lately: sold vs asking, how fast it sells, what to do |
| Tue | TOY SPOTLIGHT | The same for one toy; a thin market is the story when listings are few |
| Wed | FAST SELLERS | Top 5 by how fast today's listings would sell out |
| Thu | SCARCE FINDS | Fewest listings, and why that makes prices jumpy |
| Fri | SET OR SINGLES | Complete set vs singles, per series |
| Sat | GUESS THE PRICE | Quiz: cover hides the price, slide 2 reveals what buyers paid |

Each draft also comes with `story.jpg` (the cover on a 9:16 Story, with space for a link sticker to toy-ticker.github.io) and `reel.mp4` (a ~19 s slideshow of the slides). Reels get music from `music.mp3` (or .m4a/.wav) in the post's folder, or else one of the tracks in `assets/music/`, rotating day by day so consecutive days differ; with neither they're silent. Tracks there are kept out of git: the repo is public and the music is licensed for posts, not for sharing the files. The 7pm draft also suggests 2–3 new Meta Sound Collection tracks (facebook.com/sound) for its Reel; on approval it downloads the track and adds it with `scripts/social/add_music.py` (audio only, volume-matched, 44.1 kHz, silence trimmed). Use only music licensed for Instagram, such as Meta Sound Collection: baked-in popular songs can get a Reel muted or removed. Post the carousel, share it or story.jpg to your Story with a link sticker, and post the Reel for reach beyond followers.

After Dec 14: Thursday becomes AFTER THE PROMO and Friday THEN VS NOW (needs facts for finished series; not built yet). The schedule lives in `SCHEDULE` in `scripts/social/draft.py`; series rules are in `scripts/social/prompt.md`.

## Pinned intro post

`scripts/social/intro.py --screenshot <png>` draws the 3-slide "What is Toy Ticker?" carousel into `social/intro/` (no prices on the slides, since it stays pinned). The phone screenshot is captured with headless Chrome at 500 px wide (Chrome's minimum) with reduced motion, so the site's count-up numbers are final:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --force-prefers-reduced-motion --window-size=500,2100 --force-device-scale-factor=2 --virtual-time-budget=10000 --screenshot=site.png "https://toy-ticker.github.io/?s=pokemon-happy-meal-2026"
```

## Replies on popular posts (from Nov 15)

A scheduled task, "Toy Ticker reply drafts", runs at 9am, noon, 3pm, 6pm and 9pm Pacific. It finds popular #pokemonhappymeal / #mcdonaldspokemon posts from the last 48 hours, drafts casual one-fact replies to commenters from that day's prices, and asks for approval; nothing is posted without it. Limits: 3 replies per post, 10 a day. Steps and style rules: [scripts/social/REPLIES.md](scripts/social/REPLIES.md). Drafts and the posted log live in `social/replies/` (not committed).

## Content pillars

Every post is one of these. Each one comes straight from data the site already has, so there's nothing to research.

1. **The weekly board.** Top 5 most valuable items this week, biggest movers, cheapest way to a complete set. Image carousel or a 20-second video scrolling the site.
2. **"Worth it?"** One item or one chase card per post: what it costs on eBay vs what a Happy Meal costs, how many are listed, how fast they sell (Most sold, days to sell).
3. **After the promo.** History from the five finished series: what happened to prices once the promo ended. Strongest piece for the Dec 14 window; ties to Now #3. History only, never a forecast.
4. **Deals spotted.** A listing below the 30-day median, linked through the site. Always marked as an affiliate link.
5. **Calendar.** What's on now, what ends when, what's next ("4 days left at the counter").
6. **How the numbers work.** Short explainers: asking vs sold, why lots and graded cards are filtered, why shipping counts. Corrections go here too, in public.

Mix per week: 2 × board/worth-it, 1 × calendar or after-the-promo, 1 × deal, plus replies. Method posts when a question or a fix comes up.

## Post templates

Placeholders in `{braces}` come from `data/prices.json` on the day.

**A. Pinned: what Toy Ticker is**
> Toy Ticker tracks eBay prices for every McDonald's Happy Meal toy and card, updated daily. Check what yours are worth before you buy or list. Free, no ads, no accounts. 🔗 {link}

**B. Weekly board**
> Pokémon Happy Meal prices this week 📈
> 1. {item} — {median} ({change} vs last week)
> 2. …
> Full set as singles: {set_singles} · as a set: {set_price}
> Every item: {link}

**C. Worth it?**
> {item}: a Happy Meal costs ~$5. On eBay it's going for {median} ({count} listed, usually sells in {days} days). {link}

**D. Calendar / countdown**
> {days} days left on the Pokémon Happy Meal. After Dec 14 the only place to get them is resale. Here's what happened to the last five series after they ended: {link}

**E. Deal**
> {item} listed at {price}, below its 30-day median of {median}. {link} #ad (affiliate link, Toy Ticker may earn a commission)

**F. Correction**
> Fix: {what} was off from {date} to {date} because {reason}. Charts now mark the change. Thanks {@person} for flagging it.

Hashtags (3–5, no more): `#HappyMeal #McDonaldsToys #PokemonTCG #HappyMealToys #Reseller`, plus the series tag (`#BooBuckets`, `#Squishmallows`…).

## Video format (TikTok / Reels / Shorts) — on hold

Not part of the current plan (see the decision under Accounts). Kept for later. Faceless works and saves time: screen recording of the site + on-screen text + trending audio at low volume.

- **0–2 s:** the hook on screen. "This Happy Meal card is selling for {price}" / "Don't open this toy".
- **2–15 s:** scroll the item page, chart visible; one number per beat.
- **Last 2 s:** "Every toy's price: link in bio".
- Record 3–4 at once on Sunday, schedule through the week with each platform's built-in scheduler.

If showing physical toys, use your own; credit official photos as the site does.

## Four-week calendar: Pokémon window

| Week | Focus | Posts |
| --- | --- | --- |
| **Nov 16–22** | Launch | Set up accounts; pinned post; first weekly board; 2 "worth it?" videos (top card, top toy); join 5–10 Facebook collector groups and read their rules before posting anything |
| **Nov 23–29** | Thanksgiving / Black Friday traffic | Weekly board; "cheapest way to a complete set" carousel; one deal post; first method post (asking vs sold) |
| **Nov 30–Dec 6** | Build toward the end | Weekly board; "After the promo" chart once it ships (Reddit-worthy); countdown starts ("14 days left") |
| **Dec 7–14** | Last chance | Daily countdown story/post; "which ones to grab before they're gone" (from listing counts, not predictions); refreshed share images; Dec 14 recap |
| **Dec 15+** | After the promo | Weekly "Pokémon one week after" board; teaser for the next series as soon as it's announced |

After Dec 14, settle into the steady rhythm: one weekly board, one video, one calendar post, and a launch-day push for every new series (the series launch kit in Next makes day-one posts possible).

## Automate later, not now

Post by hand for the first four weeks to learn what lands. Then:

1. Have the daily job write a **ready-to-post weekly board** (image + caption text) next to the `og/` images, using `scripts/og.py`.
2. Auto-post that to **Bluesky** (free API) from the GitHub Action.
3. X's API is paid; keep X manual unless it turns out to matter.
4. When RSS feeds ship (Now #2), mention them in bios and pinned posts as the "price alert" option.

## Rules

- **No predictions or investment talk.** No "this will go up", "buy now before it moons". History and current listings only, same as the About page.
- **Disclose affiliate links** every time (`#ad` or "affiliate link"), per FTC and eBay Partner Network rules.
- **No seller usernames** in screenshots or captions; crop listing screenshots. Matches the site's choice not to store them.
- **Not affiliated with McDonald's** in every bio; no brand logos as Toy Ticker's own identity.
- **Group rules first.** In Facebook groups, help in comments before ever posting a link; one link post per group per week at most, only where self-promotion is allowed.
- **Answer price questions with the data**, not opinions; if a number looks wrong, check it and post a correction if it is.

## Weekly review (10 minutes, Sundays)

Write a line per week at the bottom of this file:

| Week | Followers (TT / IG / X / BS) | Link clicks | Search clicks "toy ticker" | EPN clicks | Ko-fi | Best post | Change next week |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nov 16–22 | | | | | | | |

Drop a platform after four weeks if it brings fewer than ~5% of link clicks and takes more than 20 minutes a week.

## Open questions

- [ ] Faceless videos only, or your own hands/voice with real toys? (Real toys usually reach further; faceless is faster.)
- [ ] Buy a short domain (e.g. toyticker.com or similar) before printing links everywhere? Changing links later breaks old posts.
- [ ] Is @toyticker free on TikTok, Instagram, X and Bluesky? Decide the fallback before claiming any, so the handle matches everywhere.
