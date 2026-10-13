"""Compliance RAG agent. Run: python poc3_compliance/agent.py --mock"""
import argparse, json, os, pathlib, sys
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from llm import get_client
from tools import TOOL_SPEC, Toolbox
from validator import parse_json, validate

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
MAX_STEPS, MAX_REPAIRS = 10, 1


def run(bulletin_path, mock):
    bulletin = pathlib.Path(bulletin_path).read_text()
    client, box = get_client(mock), Toolbox(bulletin)
    system = (HERE / "prompts" / "system.md").read_text()
    messages = [{"role": "user", "content": [{"text": "Analyze this bulletin against our regulations and procedures.\n\n" + bulletin}]}]
    repairs = 0
    for step in range(MAX_STEPS):
        resp = client.converse(modelId=MODEL_ID, system=[{"text": system}], messages=messages,
                               toolConfig=TOOL_SPEC, inferenceConfig={"maxTokens": 3000, "temperature": 0})
        msg = resp["output"]["message"]; messages.append(msg)
        if resp["stopReason"] == "tool_use":
            results = []
            for b in msg["content"]:
                if "toolUse" in b:
                    tu = b["toolUse"]
                    print(f"  [step {step}] {tu['name']}({json.dumps(tu['input'])})")
                    results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                                   "content": [{"json": box.dispatch(tu["name"], tu["input"])}]}})
            messages.append({"role": "user", "content": results})
            continue
        text = "".join(b.get("text", "") for b in msg["content"])
        try:
            answer = parse_json(text); problems = validate(answer, box.seen)
        except Exception as e:
            answer, problems = None, [f"invalid JSON: {e}"]
        if not problems:
            return answer
        if repairs < MAX_REPAIRS:  # give the model one chance to fix itself
            repairs += 1
            print(f"  [validator] {problems}; asking model to repair")
            messages.append({"role": "user", "content": [{"text": "Validation failed: " + "; ".join(problems) +
                             ". Fix and return ONLY the corrected JSON. Cite only ids returned by tools."}]})
            continue
        return {"status": "DRAFT - VALIDATION FAILED", "problems": problems, "raw": answer}
    return {"status": "DRAFT - max steps reached"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bulletin", default=str(HERE / "data" / "new_bulletin.md"))
    p.add_argument("--mock", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.bulletin, a.mock), indent=2))
