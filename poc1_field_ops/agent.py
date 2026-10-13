"""Minimal agent loop on the Bedrock Converse API.  Run: python poc1_field_ops/agent.py --mock"""
import argparse, json, os, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from llm import get_client
from tools import TOOL_SPEC, dispatch
from store import get_store

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
MAX_STEPS = 8  # hard stop so an agent can never loop forever


def run(asset_id, mock, verbose=True):
    client = get_client(mock)
    system = (pathlib.Path(__file__).parent / "prompts" / "system.md").read_text()
    messages = [{"role": "user", "content": [{"text": f"Assess asset {asset_id} now."}]}]
    for step in range(MAX_STEPS):
        resp = client.converse(modelId=MODEL_ID, system=[{"text": system}], messages=messages,
                               toolConfig=TOOL_SPEC, inferenceConfig={"maxTokens": 1000, "temperature": 0})
        msg = resp["output"]["message"]
        messages.append(msg)
        if resp["stopReason"] != "tool_use":
            text = "".join(b.get("text", "") for b in msg["content"])
            try: parsed = json.loads(text)
            except ValueError: parsed = {"raw": text}
            get_store().log("assessment", {"ts": time.time(), "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                           "asset_id": asset_id, "result": parsed})
            return text
        results = []
        for b in msg["content"]:
            if "toolUse" in b:
                tu = b["toolUse"]
                if verbose: print(f"  [step {step}] tool -> {tu['name']}({json.dumps(tu['input'])})")
                results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                               "content": [{"json": dispatch(tu["name"], tu["input"])}]}})
        messages.append({"role": "user", "content": results})
    return json.dumps({"error": "max steps reached"})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--asset", default="VALVE-101")
    p.add_argument("--mock", action="store_true", help="offline, no AWS calls")
    a = p.parse_args()
    print(run(a.asset, a.mock))
