"""Draft one Instagram carousel post: facts -> Claude -> check -> slides, into social/<date>-<topic>/.

    python scripts/social/draft.py                       # weekly board for today's data (needs ANTHROPIC_API_KEY)
    python scripts/social/draft.py --topic worth_it
    python scripts/social/draft.py --sample              # no API call: a fixed sample post, to test the slides

Written by a Claude Code routine instead of the API (see scripts/social/ROUTINE.md):
    python scripts/social/draft.py --facts-only          # writes social/<date>-<topic>/facts.json, prints the folder
    python scripts/social/draft.py --post social/<folder>/post.json --branch <branch>   # check + slides + pr.md

Writes facts.json, post.json (with any check problems), caption.txt, slides/NN.jpg and pr.md (the PR description).
Exit code 0 even when the check finds problems: the PR is then opened marked "Needs edit" instead of dropping the post.
"""
import argparse
import json
import os
from pathlib import Path

import facts as facts_mod
from check import TOPICS, check
from render import render

ROOT = Path(__file__).resolve().parents[2]
# One series per weekday (Monday = 0), local time. "--topic today" picks from this.
SCHEDULE = ["deal_check", "doubles", "card_spotlight", "scarce_finds", "set_or_singles", "guess_price", "weekly_board"]


def sample_post(f):
    """A post built from the rankings without Claude, for testing the renderer and the PR."""
    items = {i["id"]: i for i in f["items"]}
    r = f["rankings"]
    cards, toys = r.get("most_valuable_cards", []), r.get("most_valuable_toys", [])
    rows = lambda ids, extra: [{"item_id": i, "fact_ids": [items[i]["facts"]["ask"]] +  # noqa: E731
                                ([items[i]["facts"][extra]] if extra in items[i]["facts"] else [])} for i in ids]
    star = (cards or toys)[0]
    slides = [
        {"layout": "cover", "headline": "What your Pokémon Happy Meal is worth", "subhead": "This week's eBay prices for every card and toy",
         "item_ids": [t for t in toys if items[t]["image"]][:3]},
        {"layout": "ranked_list", "headline": "Most valuable cards", "rows": rows(cards, "listings")},
        {"layout": "ranked_list", "headline": "Most valuable toys", "rows": rows(toys, "listings")},
        {"layout": "item", "headline": "The one everyone wants", "item_id": star,
         "fact_ids": [items[star]["facts"][k] for k in ("ask", "sold_count", "days_to_sell") if k in items[star]["facts"]],
         "note": "Sample note: code draws the numbers, Claude writes the words."},
        {"layout": "cta", "headline": "Every toy and card, priced daily"},
    ]
    for s in slides:
        for k, v in {"subhead": "", "item_ids": [], "rows": [], "item_id": "", "fact_ids": [], "note": ""}.items():
            s.setdefault(k, v)
    return {"topic": "weekly_board", "slides": slides,
            "caption": "SAMPLE POST (no AI). " + "This is a fixed test post used to check the slide renderer and the pull request. " * 4,
            "hashtags": ["#HappyMeal", "#PokemonTCG", "#McDonaldsToys"],
            "alt_text": [f"Slide {n}" for n in range(1, len(slides) + 1)],
            "threads": ["SAMPLE POST (no AI). A fixed test Threads post. See every toy's price: toy-ticker.github.io"],
            "threads_topic": "Pokemon Happy Meal",
            "reel_hook": {"text": "SAMPLE hook", "item_ids": slides[0]["item_ids"][:1]}}


def pr_body(post, f, problems, folder, branch):
    repo = os.environ.get("GITHUB_REPOSITORY", "Toy-Ticker/toy-ticker.github.io")
    raw = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/{folder.relative_to(ROOT).as_posix()}"
    fx = {x["id"]: x for x in f["facts"]}
    names = {i["id"]: i["name"] for i in f["items"]}
    used = []
    for s in post["slides"]:
        for fid in s.get("fact_ids", []) + [x for row in s.get("rows", []) for x in row.get("fact_ids", [])]:
            if fid in fx and fid not in used:
                used.append(fid)
    lines = [f"Instagram post drafted from Toy Ticker data for {f['date']}. Topic: **{post['topic']}**.", ""]
    if problems:
        lines += ["## ⚠️ Needs edit", "", "check.py still found problems after one retry. Fix them in `post.json` "
                  "and the caption, or close this PR:", ""] + [f"- {p}" for p in problems] + [""]
    lines += ["## Caption", "", "Copy this into Instagram:", "", "```", caption_text(post), "```", "",
              "## Slides", ""]
    lines += [f"![slide {n}]({raw}/slides/{n:02d}.jpg)" for n in range(1, len(post["slides"]) + 1)]
    lines += ["", "<details><summary>Alt text (Instagram: Advanced settings → Accessibility)</summary>", ""]
    lines += [f"{n}. {a}" for n, a in enumerate(post.get("alt_text", []), 1)] + ["", "</details>", ""]
    lines += ["<details><summary>Facts used</summary>", "", "| Fact | Item | What | Value |", "| --- | --- | --- | --- |"]
    lines += [f"| {fid} | {names.get(fx[fid]['about'], fx[fid]['about'] or '')} | {fx[fid]['what']} | {fx[fid]['display']} |"
              for fid in used] + ["", "</details>", "",
              "**To post (Phase 1):** save the slides from the Files tab, upload them as one carousel in Instagram, "
              "paste the caption, then merge this PR so the agent remembers the post."]
    return "\n".join(lines)


def caption_text(post):
    return f"{post['caption'].rstrip()}\n\n{' '.join(post.get('hashtags', []))}"


def threads_text(post):
    """Threads posts for copy-paste or Chrome posting (see scripts/social/THREADS.md)."""
    parts = [f"Topic: {post.get('threads_topic', '')}"]
    for n, t in enumerate(post.get("threads", []), 1):
        parts.append(f"--- Threads post {n} ---\n{t.strip()}")
        if n == 1 and post.get("threads_poll"):
            parts[-1] += "\n\nPoll options: " + " / ".join(post["threads_poll"])
    return "\n\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="weekly_board", choices=TOPICS + ["today"],
                    help="series to draft; 'today' picks the weekday's series from SCHEDULE")
    ap.add_argument("--date", help="data date (default: the latest update)")
    ap.add_argument("--sample", action="store_true", help="skip Claude and use a fixed sample post")
    ap.add_argument("--branch", default="main", help="branch the PR images will live on")
    ap.add_argument("--series", help="a series id to post about instead of the one in restaurants (e.g. a past series)")
    ap.add_argument("--facts-only", action="store_true", help="only write facts.json (for a writer outside this script)")
    ap.add_argument("--post", help="a post.json someone else wrote, next to its facts.json: check it and draw it")
    args = ap.parse_args()
    if args.topic == "today":
        from datetime import datetime
        args.topic = SCHEDULE[datetime.now().weekday()]

    if args.post:
        folder = Path(args.post).resolve().parent
        f = json.loads((folder / "facts.json").read_text())
    else:
        f = facts_mod.build(ROOT, args.date, series=args.series)
        folder = ROOT / "social" / (f"{f['date']}-{args.topic.replace('_', '-')}"
                                    f"{'-' + args.series if args.series else ''}{'-sample' if args.sample else ''}")
        n = 2
        base = folder
        while (folder / "post.json").exists() and not args.sample:   # never overwrite a drafted post
            folder, n = base.with_name(f"{base.name}-{n}"), n + 1
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "facts.json").write_text(json.dumps(f, indent=1, ensure_ascii=False))
        if args.facts_only:
            print(folder.relative_to(ROOT))
            return

    if args.post:
        post = json.loads(Path(args.post).read_text())
        post.pop("problems", None)
        problems = check(post, f)
    elif args.sample:
        post = sample_post(f)
        problems = check(post, f)
    else:
        from write import write
        post, problems = write(f, args.topic)
    try:
        render(post, f, folder, ROOT)
    except Exception as e:  # noqa: BLE001 - a broken post still gets a PR, marked for editing
        problems.append(f"Slides could not be drawn: {e!r}")
    else:
        # Story image and Reel video from the same slides (Reel only where ffmpeg is available).
        import extras
        try:
            extras.story(folder, f, ROOT)
            import motion   # animated Reel; the plain slideshow (extras.reel) is the fallback
            try:
                made = motion.build(folder, f, ROOT, post)
            except Exception as e:  # noqa: BLE001
                print(f"! animated reel failed ({e!r}); using the slideshow")
                made = extras.reel(folder, f, ROOT, hook=post.get("reel_hook"))
            if not made:
                print("(no ffmpeg: skipped reel.mp4)")
        except Exception as e:  # noqa: BLE001 - extras never block the post
            print(f"! story/reel: {e!r}")
    (folder / "post.json").write_text(json.dumps({**post, "problems": problems}, indent=1, ensure_ascii=False))
    (folder / "caption.txt").write_text(caption_text(post))
    if post.get("threads"):
        (folder / "threads.txt").write_text(threads_text(post))
    (folder / "pr.md").write_text(pr_body(post, f, problems, folder, args.branch))
    print(folder.relative_to(ROOT))
    print("problems:" if problems else "check: OK", *problems, sep="\n- " if problems else "")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"folder={folder.relative_to(ROOT).as_posix()}\nneeds_edit={'true' if problems else 'false'}\n")


if __name__ == "__main__":
    main()
