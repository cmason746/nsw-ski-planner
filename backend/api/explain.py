"""
Recommendation "why" prose — grounded LLM generation via Amazon Bedrock.

The scorer has already selected and described the facts (8 factors + a runner-up
contrast, in the overview's band words). This module only *rephrases those exact
facts into flowing prose* — Claude Haiku 4.5 on Bedrock, strictly prompted to add,
change, or invent nothing. The deterministic facts are the anti-hallucination
guardrail: every claim in the prose traces back to a computed fact.

We call Bedrock through **boto3's `bedrock-runtime`**, which the Lambda runtime
already provides — so the API function needs no extra dependencies and no container
build. One call covers all cards. If Bedrock is unavailable or the response won't
parse, we fall back to a plain templated join of the same facts, so POST /recommend
never fails.
"""

import json
import os
from datetime import date

from scorer import WEATHER_KEYS

# Bedrock model id + region come from the environment (set in template.yaml) so the
# exact id / inference profile can be confirmed at deploy without a code change.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")
REGION = os.environ.get("BEDROCK_REGION")  # None → boto3 uses the Lambda's own region

_client = None

SYSTEM_PROMPT = """You write the short "why" blurb for a NSW ski-resort recommendation app.

For each resort-day given, write a small paragraph, in the third person, explaining why it's a good pick that day and why it was chosen over the runner-up resort.

STRICT RULES — the app's trust depends on these:
- Use ONLY the facts listed for that resort-day. Never add, infer, or invent a condition, number, comparison, or claim that isn't in the facts.
- Don't mention any factor that isn't listed, and don't guess weather you weren't given.
- Natural, flowing prose — no bullet points, no markdown, no headings.
- Lead with what makes the day good, then weave the runner-up comparison in naturally.
- Refer to the day by name (e.g. "Saturday").

Return ONLY a JSON object mapping each date (exactly as given, e.g. "2026-08-15") to its paragraph. No other text."""


def generate_why(cards: list, preferences: dict) -> list:
    """
    Add a `why` prose string to each card. Returns the same list.
    Falls back to a templated join per card if Bedrock is unavailable / unparseable.
    """
    if not cards:
        return cards

    whys = {}
    try:
        prompt = _build_prompt(cards, preferences)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "temperature": 0.4,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = _bedrock().invoke_model(modelId=MODEL_ID, body=body)
        payload = json.loads(response["body"].read())
        text = "".join(b["text"] for b in payload["content"] if b.get("type") == "text")
        whys = _parse_json(text)
    except Exception as e:  # network, auth, boto3 missing, or parse — degrade gracefully
        print(f"generate_why: falling back to templated prose ({type(e).__name__}: {e})")

    for card in cards:
        card["why"] = whys.get(card["date"]) or _fallback_why(card)
    return cards


def _bedrock():
    """Lazy boto3 client — keeps the module importable without boto3/creds locally."""
    global _client
    if _client is None:
        import boto3
        _client = boto3.client("bedrock-runtime", region_name=REGION or None)
    return _client


# --- Prompt building (deterministic; this is what the model rephrases) ---

def _build_prompt(cards: list, preferences: dict) -> str:
    blocks = [_render_card(card) for card in cards]
    prefs = _prefs_summary(preferences)
    header = f"The skier: {prefs}.\n\n" if prefs else ""
    return header + "\n\n".join(blocks)


def _render_card(card: dict) -> str:
    lines = [f"{card['resort']} — {_format_date(card['date'])}  (date key: {card['date']})",
             "Facts (use only these):"]
    lines += [f"- {_fact_line(f)}" for f in card["facts"]]

    contrast = card.get("contrast")
    if contrast:
        lines.append(f"Chosen over {contrast['runner_up']}:")
        for fc in contrast["factors"]:
            lines.append(
                f"- {_fact_line(fc['chosen'])}  —  {contrast['runner_up']} only: {_fact_line(fc['runner_up'])}"
            )
    return "\n".join(lines)


def _fact_line(fact: dict) -> str:
    factor = fact["factor"]
    if factor in WEATHER_KEYS:
        return _weather_line(fact)
    if factor == "recent_snow":
        return f"{fact['label']} ({_num(fact['cm'])} cm in the last couple of days)"
    if factor == "lifts":
        return f"{fact['label']} ({fact['pct']}% of lifts running)"
    if factor == "base_depth":
        return f"{fact['label']} ({_num(fact['cm'])} cm base)"
    return fact["label"]  # ability / size / run_length / price


def _weather_line(fact: dict) -> str:
    am, pm = _phrase(fact.get("am")), _phrase(fact.get("pm"))
    if am and pm:
        return f"{am} (all day)" if am == pm else f"{am} in the morning, {pm} in the afternoon"
    return am or pm or ""


def _phrase(value) -> str:
    """One weather reading → 'label (number unit)'. value is a string, a dict, or None."""
    if value is None:
        return None
    if isinstance(value, str):  # rain/snow classification is already a phrase
        return value
    label = value.get("label")
    if "kmh" in value:
        num = f"{_num(value['kmh'])} km/h"
    elif "cm" in value:
        num = f"{_num(value['cm'])} cm"
    elif "sunniness_pct" in value:
        num = f"{_num(value['sunniness_pct'])}% sun"
    elif "temp_c" in value:
        num = f"{_num(value['temp_c'])}°C"
    else:
        num = None
    phrase = f"{label} ({num})" if num else label
    if value.get("note"):
        phrase += f", {value['note']}"
    return phrase


# --- Fallback prose (no LLM) ---

def _fallback_why(card: dict) -> str:
    """Plain templated join of the top facts + contrast — used only if Bedrock fails."""
    facts = ", ".join(_fact_line(f) for f in card["facts"][:4])
    why = f"{card['resort']} on {_format_date(card['date'])}: {facts}."
    contrast = card.get("contrast")
    if contrast:
        why += f" Chosen over {contrast['runner_up']}."
    return why


# --- helpers ---

def _prefs_summary(preferences: dict) -> str:
    parts = [f"a {preferences.get('ability', 'beginner')} skier"]
    if preferences.get("cost_matters"):
        parts.append("keeping costs down")
    if preferences.get("bigger_resort"):
        parts.append("wanting a bigger resort")
    if preferences.get("longer_runs"):
        parts.append("wanting longer runs")
    snow_pref = preferences.get("snow_pref")
    if snow_pref == "snowy":
        parts.append("chasing fresh snow")
    elif snow_pref == "bluebird":
        parts.append("after sunny days")
    return ", ".join(parts)


def _format_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%A %-d %B %Y")  # e.g. "Saturday 15 August 2026"


def _parse_json(text: str) -> dict:
    """Parse the model's JSON, tolerating stray prose or code fences around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


def _num(x) -> str:
    """Trim a float for display: 8.0 → '8', 8.5 → '8.5'."""
    return f"{x:g}"
