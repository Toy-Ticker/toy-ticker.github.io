"""Check a drafted post against the facts it was written from. Returns a list of problems (empty = OK).

The main job: every number in the caption, headlines, notes and alt text must appear in some fact's display text,
so the writer can't invent, round or compute a price.
"""
import re

LAYOUTS = {"cover", "ranked_list", "item", "highlight", "hero", "versus", "tier_list", "cta"}
TOPICS = ["weekly_board", "card_spotlight", "toy_spotlight", "fast_sellers", "scarce_finds", "set_or_singles",
          "guess_price", "after_promo", "doubles", "versus", "worth_it", "countdown"]
BANNED = [
    "will go up", "will rise", "will increase", "going to go up", "will be worth", "will drop", "will fall",
    "invest", "guaranteed", "sure thing", "before prices", "buy now", "act fast", "before it's too late",
    "price prediction", "predict", "skyrocket", "to the moon", "goldmine", "gold mine",
]
LIMITS = {"cover": (40, 70), "ranked_list": (36, 0), "item": (36, 0), "highlight": (40, 0), "hero": (40, 0), "versus": (40, 0), "tier_list": (40, 0), "cta": (40, 60)}
NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")


def numbers(text):
    """Numbers as written, normalised: '$1,234.50' -> '$1234.50', '12%' stays '12%'."""
    return {m.replace(",", "") for m in NUMBER.findall(text or "")}


def allowed_numbers(facts):
    ok = set()
    for f in facts["facts"]:
        ok |= numbers(f["display"])
    for s in facts["promo"].get("series", []):
        ok.add(str(s["size"]))
    ok |= {str(n) for n in range(1, 11)}   # rankings and slide counts ("top 5")
    ok.add(facts["date"][:4])              # the year
    return ok


def check(post, facts):
    errs = []
    fx = {f["id"]: f for f in facts["facts"]}
    items = {i["id"]: i for i in facts["items"]}
    ok_nums = allowed_numbers(facts)
    slides = post.get("slides") or []

    if post.get("topic") not in TOPICS:
        errs.append(f"Unknown topic {post.get('topic')!r}; use one of {', '.join(TOPICS)}.")
    if not 3 <= len(slides) <= 7:
        errs.append(f"Use 3 to 7 slides (got {len(slides)}).")
    if slides and slides[0].get("layout") != "cover":
        errs.append("The first slide must be layout 'cover'.")
    if slides and slides[-1].get("layout") != "cta":
        errs.append("The last slide must be layout 'cta'.")

    def nums_ok(where, text):
        bad = sorted(numbers(text) - ok_nums)
        if bad:
            errs.append(f"{where}: number(s) {', '.join(bad)} don't appear in any fact's display text. "
                        "Copy numbers exactly from facts or use words.")

    def fact_ok(where, fid, item_id):
        if fid not in fx:
            errs.append(f"{where}: unknown fact {fid}.")
        elif fx[fid]["about"] != item_id:
            errs.append(f"{where}: fact {fid} is about {fx[fid]['about']}, not {item_id}.")

    for n, s in enumerate(slides, 1):
        where, lay = f"Slide {n}", s.get("layout")
        if lay not in LAYOUTS:
            errs.append(f"{where}: unknown layout {lay!r}.")
            continue
        head_max, sub_max = LIMITS[lay]
        if not s.get("headline"):
            errs.append(f"{where}: headline is empty.")
        elif len(s["headline"]) > head_max:
            errs.append(f"{where}: headline is {len(s['headline'])} characters; keep it to {head_max}.")
        if sub_max and len(s.get("subhead", "")) > sub_max:
            errs.append(f"{where}: subhead is over {sub_max} characters.")
        if len(s.get("note", "")) > 90:
            errs.append(f"{where}: note is over 90 characters.")
        for field in ("headline", "subhead", "note"):
            nums_ok(f"{where} {field}", s.get(field, ""))
        if lay in ("cover", "highlight"):
            for iid in s.get("item_ids", []):
                if iid not in items:
                    errs.append(f"{where}: unknown item {iid}.")
        if lay == "ranked_list":
            rows = s.get("rows") or []
            if not 3 <= len(rows) <= 5:
                errs.append(f"{where}: a ranked list needs 3 to 5 rows (got {len(rows)}).")
            for r, row in enumerate(rows, 1):
                iid = row.get("item_id")
                if iid not in items:
                    errs.append(f"{where} row {r}: unknown item {iid}.")
                    continue
                if not 1 <= len(row.get("fact_ids", [])) <= 2:
                    errs.append(f"{where} row {r}: give 1 or 2 fact_ids.")
                for fid in row.get("fact_ids", []):
                    fact_ok(f"{where} row {r}", fid, iid)
        if lay == "hero":
            if s.get("item_id") not in items:
                errs.append(f"{where}: a hero slide needs an item_id.")
            if len(s.get("fact_ids", [])) > 1:
                errs.append(f"{where}: a hero slide shows at most 1 fact.")
            for fid in s.get("fact_ids", []):
                fact_ok(where, fid, s.get("item_id"))
        if lay == "versus":
            ids, fids = s.get("item_ids", []), s.get("fact_ids", [])
            if len(ids) != 2 or len(fids) != 2:
                errs.append(f"{where}: a versus slide needs exactly 2 item_ids and 2 fact_ids (one per item, same order).")
            else:
                for iid, fid in zip(ids, fids):
                    if iid not in items:
                        errs.append(f"{where}: unknown item {iid}.")
                    else:
                        fact_ok(where, fid, iid)
        if lay == "tier_list":
            ids = s.get("item_ids", [])
            if not 4 <= len(ids) <= 16:
                errs.append(f"{where}: a tier list needs 4 to 16 item_ids.")
            for iid in ids:
                if iid not in items or "ask" not in items[iid]["facts"]:
                    errs.append(f"{where}: {iid} isn't an item with an asking price.")
        if lay == "highlight":
            if not 1 <= len(s.get("fact_ids", [])) <= 2:
                errs.append(f"{where}: a highlight needs 1 or 2 fact_ids.")
            for fid in s.get("fact_ids", []):
                if fid not in fx:
                    errs.append(f"{where}: unknown fact {fid}.")
        if lay == "item":
            iid = s.get("item_id")
            if iid not in items:
                errs.append(f"{where}: unknown item {iid}.")
            else:
                if not 1 <= len(s.get("fact_ids", [])) <= 3:
                    errs.append(f"{where}: give 1 to 3 fact_ids.")
                for fid in s.get("fact_ids", []):
                    fact_ok(where, fid, iid)

    if slides and slides[-1].get("layout") == "cta":
        sub = slides[-1].get("subhead", "")
        if not sub:
            errs.append("The cta slide needs a subhead saying what people will find on the site.")
    cap = post.get("caption", "")
    if cap.lower().count("link in bio") < 2:
        errs.append("The caption needs a call to action in the middle and at the end, each saying 'link in bio'.")
    if not 300 <= len(cap) <= 2200:
        errs.append(f"Caption is {len(cap)} characters; keep it between 300 and 900.")
    if "#" in cap:
        errs.append("Put hashtags in 'hashtags', not in the caption.")
    nums_ok("Caption", cap)
    tags = post.get("hashtags") or []
    if not 3 <= len(tags) <= 5 or not all(re.fullmatch(r"#\w+", t) for t in tags):
        errs.append("Give 3 to 5 hashtags, each like #HappyMeal (no spaces).")
    threads = post.get("threads")
    if not isinstance(threads, list) or not 1 <= len(threads) <= 2:
        errs.append("Give 1 or 2 Threads posts in 'threads' (a list of strings).")
        threads = []
    for n, t in enumerate(threads, 1):
        if not 60 <= len(t) <= 500:
            errs.append(f"Threads post {n} is {len(t)} characters; keep it between 60 and 500.")
        if "toy-ticker.github.io" not in t:
            errs.append(f"Threads post {n} must include the link toy-ticker.github.io (links are tappable on Threads).")
        if "link in bio" in t.lower():
            errs.append(f"Threads post {n}: don't say 'link in bio'; the link is in the post.")
        if "#" in t:
            errs.append(f"Threads post {n}: no hashtags; put one topic in 'threads_topic'.")
        nums_ok(f"Threads post {n}", t)
    poll = post.get("threads_poll") or []
    if poll and not (2 <= len(poll) <= 4 and all(1 <= len(o) <= 25 for o in poll)):
        errs.append("A Threads poll needs 2 to 4 options of up to 25 characters each.")
    for o in poll:
        nums_ok("Threads poll", o)
    topic_tag = post.get("threads_topic", "")
    if not (1 <= len(topic_tag) <= 50) or "#" in topic_tag:
        errs.append("Give one 'threads_topic' (1 to 50 characters, no #), e.g. 'Pokemon Happy Meal'.")
    alts = post.get("alt_text") or []
    if len(alts) != len(slides):
        errs.append(f"Give one alt text per slide ({len(slides)}), got {len(alts)}.")
    for n, a in enumerate(alts, 1):
        nums_ok(f"Alt text {n}", a)

    text = " ".join([cap, *alts, *threads, *(f"{s.get('headline', '')} {s.get('subhead', '')} {s.get('note', '')}" for s in slides)]).lower()
    for phrase in BANNED:
        if re.search(rf"\b{re.escape(phrase)}", text):
            errs.append(f"Remove the phrase {phrase!r}: no predictions, investment talk or urgency.")
    return errs
