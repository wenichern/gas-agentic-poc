"""LLM client factory: real Amazon Bedrock (Converse API) or an offline mock."""
import json, os


def get_client(mock: bool):
    if mock:
        return MockBedrock()
    import boto3
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))


class MockBedrock:
    """Deterministic stand-in that mimics Converse tool-use so you can learn the loop with no AWS cost."""

    def converse(self, **kw):
        msgs = kw["messages"]
        results = [b["toolResult"] for m in msgs if m["role"] == "user" and isinstance(m["content"], list)
                   for b in m["content"] if "toolResult" in b]
        names = {}
        for m in msgs:
            if m["role"] == "assistant":
                for b in m["content"]:
                    if "toolUse" in b:
                        names[b["toolUse"]["toolUseId"]] = b["toolUse"]["name"]
        done = {names.get(r["toolUseId"]) for r in results}

        if not results:
            return self._tools([("get_sensor_readings", {"asset_id": "VALVE-101"}),
                                ("get_maintenance_history", {"asset_id": "VALVE-101"})])
        data = {names[r["toolUseId"]]: r["content"][0]["json"] for r in results}
        r = data["get_sensor_readings"]
        alerts = []
        if r["pressure_psi"] > 800: alerts.append("Pressure above 800 psi")
        if r["flow_m3h"] < 50: alerts.append("Flow below 50 m3/h")
        if r["temperature_c"] > 90: alerts.append("Temperature above 90 C")
        if alerts and "send_alert" not in done:
            return self._tools([("send_alert", {"severity": "HIGH", "message": "; ".join(alerts)}),
                                ("create_work_order", {"asset_id": "VALVE-101", "priority": "P1",
                                                       "description": "Inspect valve: " + "; ".join(alerts)})])
        final = {"alerts": alerts, "predicted_rul": "approx. 40 days (mock estimate)",
                 "summary": ("ACTION TAKEN: " if alerts else "All readings normal. ") + "; ".join(alerts)}
        return {"stopReason": "end_turn",
                "output": {"message": {"role": "assistant", "content": [{"text": json.dumps(final)}]}}}

    @staticmethod
    def _tools(calls):
        return {"stopReason": "tool_use", "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": f"mock-{i}-{n}", "name": n, "input": a}} for i, (n, a) in enumerate(calls)]}}}
