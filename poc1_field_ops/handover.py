"""Shift handover report from the last N hours of alerts, work orders and agent assessments.
  python poc1_field_ops/handover.py --mock --shift Night --hours 12
Works against DynamoDB too: set READINGS_TABLE (records are stored there by the Lambda)."""
import argparse, json, os, pathlib, sys, time
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from llm import get_client
from store import get_store

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")


def collect(hours):
    s = get_store(); since = time.time() - hours * 3600
    return {"alerts": s.logs("alert", since), "work_orders": s.logs("work_order", since), "assessments": s.logs("assessment", since)}


def render_mock(d, shift, hours):
    hhmm = lambda x: x.get("time", "")[11:16]
    L = [f"# Shift Handover: {shift} ({hours}h window)", "", "## Summary",
         f"{len(d['alerts'])} alert(s), {len(d['work_orders'])} work order(s), {len(d['assessments'])} agent assessment(s).", "", "## Alerts"]
    L += [f"- {hhmm(a)} UTC [{a['severity']}] {a['message']}" for a in d["alerts"]] or ["No alerts in this period."]
    L += ["", "## Work orders awaiting approval (approval status is not tracked in this POC)"]
    L += [f"- {hhmm(w)} UTC {w['asset_id']} {w['priority']}: {w['description']}" for w in d["work_orders"]] or ["None."]
    L += ["", "## Assets to watch next shift"]
    latest = {}
    for a in d["assessments"]: latest[a["asset_id"]] = a
    L += [f"- {k} ({hhmm(v)} UTC): {v['result'].get('trend_forecast', 'n/a')}" for k, v in latest.items()] or ["None."]
    L += ["", "## Data gaps", "- Mock report (template, no language model). Forecast confidence is not shown here."]
    return "\n".join(L)


def render_llm(d, shift, hours):
    system = (HERE / "prompts" / "handover.md").read_text()
    r = get_client(False).converse(modelId=MODEL_ID, system=[{"text": system}], inferenceConfig={"maxTokens": 1500, "temperature": 0.2},
        messages=[{"role": "user", "content": [{"text": f"Shift: {shift}. Window: {hours}h.\n\n" + json.dumps(d, default=str)}]}])
    return "".join(b.get("text", "") for b in r["output"]["message"]["content"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12)
    ap.add_argument("--shift", default="Night")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    d = collect(a.hours)
    print(render_mock(d, a.shift, a.hours) if a.mock else render_llm(d, a.shift, a.hours))
