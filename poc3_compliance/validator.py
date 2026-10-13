"""Grounding check: every citation in the answer must be an id the agent actually retrieved."""
import json, re


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    return json.loads(text[start:])


def collect_citations(answer):
    cites = []
    for key in ("impacted_procedures", "gaps", "draft_actions"):
        for item in answer.get(key, []):
            cites += item.get("citations", [])
    cites += [d.get("source", "") for d in answer.get("deadlines", [])]
    return cites


def validate(answer, seen_ids):
    problems = []
    for key in ("bulletin_summary", "impacted_procedures", "gaps", "deadlines", "draft_actions", "status"):
        if key not in answer:
            problems.append(f"missing key: {key}")
    for c in collect_citations(answer):
        if not c:
            problems.append("empty citation")
        elif c not in seen_ids:
            problems.append(f"citation not retrieved (possible hallucination): {c}")
    for key in ("gaps", "draft_actions"):
        for item in answer.get(key, []):
            if not item.get("citations"):
                problems.append(f"{key} item without citations: {str(item)[:60]}")
    if "DRAFT" not in str(answer.get("status", "")).upper():
        problems.append("status must say DRAFT")
    return problems
