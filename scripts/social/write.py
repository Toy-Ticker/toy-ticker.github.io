"""Ask Claude to write one Instagram carousel post from facts.json. Returns the post as a dict.

One request (plus one retry if check.py finds problems). Needs ANTHROPIC_API_KEY.
"""
import json
from pathlib import Path

import anthropic

from check import TOPICS, check

MODEL = "claude-opus-5-5"
PROMPT = (Path(__file__).with_name("prompt.md")).read_text()

SLIDE = {
    "type": "object",
    "properties": {
        "layout": {"type": "string", "enum": ["cover", "ranked_list", "item", "highlight", "cta"]},
        "headline": {"type": "string"},
        "subhead": {"type": "string"},
        "item_ids": {"type": "array", "items": {"type": "string"}},
        "rows": {"type": "array", "items": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}, "fact_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["item_id", "fact_ids"], "additionalProperties": False}},
        "item_id": {"type": "string"},
        "fact_ids": {"type": "array", "items": {"type": "string"}},
        "note": {"type": "string"},
    },
    "required": ["layout", "headline", "subhead", "item_ids", "rows", "item_id", "fact_ids", "note"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "enum": TOPICS},
        "slides": {"type": "array", "items": SLIDE},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "alt_text": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["topic", "slides", "caption", "hashtags", "alt_text"],
    "additionalProperties": False,
}


def ask(client, messages):
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",   # a declined request is re-run on Anthropic's recommended fallback model
        system=PROMPT,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=messages,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined to write the post: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude's reply was cut off (max_tokens).")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text), response


def write(facts, topic="weekly_board", client=None):
    """Returns (post, problems). problems is empty when the post passed check.py."""
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content":
                 f"Requested topic: {topic}\n\nFacts file:\n```json\n{json.dumps(facts, ensure_ascii=False)}\n```"}]
    post, response = ask(client, messages)
    problems = check(post, facts)
    if problems:
        messages += [{"role": "assistant", "content": response.content},
                     {"role": "user", "content": "check.py found these problems. Fix every one and return the whole post:\n- "
                                                 + "\n- ".join(problems)}]
        post, _ = ask(client, messages)
        problems = check(post, facts)
    return post, problems
