"""LLM client factory: real Amazon Bedrock (Converse API) or an offline mock."""
import json, os, re


def get_client(mock: bool):
    if mock:
        return MockBedrock()
    import boto3
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))


class MockBedrock:
    """Deterministic stand-in mimicking Converse tool use. Real tool calls, rule-based 'reasoning' (not a language model)."""

    def converse(self, **kw):
        msgs = kw["messages"]
        first = msgs[0]["content"][0]["text"]
        m = re.search(r"asset (\S+) now", first); asset = m.group(1) if m else "UNKNOWN"
        names, results = {}, []
        for msg in msgs:
            if isinstance(msg["content"], list):
                for b in msg["content"]:
                    if "toolUse" in b: names[b["toolUse"]["toolUseId"]] = b["toolUse"]["name"]
                    if "toolResult" in b: results.append(b["toolResult"])
        done = {names.get(r["toolUseId"]) for r in results}
        if not results:
            return self._tools([("get_sensor_readings", {"asset_id": asset}), ("get_trend_analysis", {"asset_id": asset}),
                                ("get_maintenance_history", {"asset_id": asset})])
        data = {names[r["toolUseId"]]: r["content"][0]["json"] for r in results}
        r, trend, hist = data["get_sensor_readings"], data.get("get_trend_analysis", {}), data["get_maintenance_history"]
        alerts = []
        if r["pressure_psi"] > 800: alerts.append("Pressure above 800 psi")
        if r["flow_m3h"] < 50: alerts.append("Flow below 50 m3/h")
        if r["temperature_c"] > 90: alerts.append("Temperature above 90 C")
        proj = [(k, t["hours_to_threshold"]) for k, t in trend.get("metrics", {}).items()
                if t["hours_to_threshold"] is not None and 0 < t["hours_to_threshold"] <= 6 and t["confidence"] != "low"]
        if alerts and "send_alert" not in done:
            return self._tools([("send_alert", {"severity": "HIGH", "message": "; ".join(alerts)}),
                                ("create_work_order", {"asset_id": asset, "priority": "P1", "description": "Inspect: " + "; ".join(alerts)})])
        if proj and not alerts and "create_work_order" not in done:
            txt = ", ".join(f"{k} in ~{h}h" for k, h in proj)
            return self._tools([("create_work_order", {"asset_id": asset, "priority": "P2", "description": f"Preventive inspection, projected limit crossing: {txt}"})])
        forecast = ("trend unavailable (insufficient history)" if "note" in trend else
                    "; ".join(f"{k} projected to reach its limit in ~{h}h" for k, h in proj) or "no limit crossing projected within 6h")
        rem = hist["design_life_cycles"] - hist["cycles_since_overhaul"]
        final = {"alerts": alerts, "predicted_rul": f"{rem} cycles to overhaul limit (ESTIMATE, no wear model)",
                 "trend_forecast": forecast,
                 "summary": (("ACTION TAKEN: " + "; ".join(alerts) + ". ") if alerts else "No limit breached. ") + forecast + "."}
        return {"stopReason": "end_turn", "output": {"message": {"role": "assistant", "content": [{"text": json.dumps(final)}]}}}

    @staticmethod
    def _tools(calls):
        return {"stopReason": "tool_use", "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": f"mock-{i}-{n}", "name": n, "input": a}} for i, (n, a) in enumerate(calls)]}}}
