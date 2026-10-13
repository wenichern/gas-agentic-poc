"""Tools the agent may call. Sensors come from the store (or a fallback simulation); alerts/work orders go to AWS if configured."""
import datetime, json, os, random, time
from decimal import Decimal
from analytics import analyze
from store import get_store

_asset = {"asset_id": {"type": "string"}}
TOOL_SPEC = {"tools": [
    {"toolSpec": {"name": "get_sensor_readings", "description": "Latest pressure (psi), flow (m3/h), temperature (C) for an asset.",
      "inputSchema": {"json": {"type": "object", "properties": _asset, "required": ["asset_id"]}}}},
    {"toolSpec": {"name": "get_trend_analysis", "description": "Trend model over recent history: slope per hour, anomaly z-score, estimated hours until each limit is crossed, and confidence.",
      "inputSchema": {"json": {"type": "object", "properties": {**_asset, "window_hours": {"type": "number"}}, "required": ["asset_id"]}}}},
    {"toolSpec": {"name": "get_maintenance_history", "description": "Past maintenance events and last maintenance date for an asset.",
      "inputSchema": {"json": {"type": "object", "properties": _asset, "required": ["asset_id"]}}}},
    {"toolSpec": {"name": "send_alert", "description": "Notify the on-duty supervisor. Use only for actual threshold breaches.",
      "inputSchema": {"json": {"type": "object", "properties": {"severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "message": {"type": "string"}}, "required": ["severity", "message"]}}}},
    {"toolSpec": {"name": "create_work_order", "description": "Open a maintenance work order (P1 breach, P2 preventive). A human approves it. Duplicates within 24h are skipped.",
      "inputSchema": {"json": {"type": "object", "properties": {"asset_id": {"type": "string"}, "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
        "description": {"type": "string"}}, "required": ["asset_id", "priority", "description"]}}}},
]}


def get_sensor_readings(asset_id):
    rows = get_store().recent(asset_id, 1)
    if rows:
        r = rows[-1]
        return {"asset_id": asset_id, "pressure_psi": r["pressure_psi"], "flow_m3h": r["flow_m3h"],
                "temperature_c": r["temperature_c"], "ts": r["ts"], "source": "store"}
    if os.getenv("SCENARIO", "breach") == "breach":   # fallback so the very first demo works with no data
        return {"asset_id": asset_id, "pressure_psi": 842.5, "flow_m3h": 47.0, "temperature_c": 88.0, "source": "simulated"}
    return {"asset_id": asset_id, "pressure_psi": round(random.uniform(600, 780), 1),
            "flow_m3h": round(random.uniform(60, 120), 1), "temperature_c": round(random.uniform(40, 80), 1), "source": "simulated"}


def get_trend_analysis(asset_id, window_hours=6):
    rows = get_store().recent(asset_id, window_hours)
    if len(rows) < 3:
        return {"note": "insufficient history; no trend available", "n_points": len(rows)}
    return analyze(rows)


def get_maintenance_history(asset_id):
    return {"asset_id": asset_id, "last_maintenance": "2025-11-02",
            "events": [{"date": "2024-05-10", "type": "seal replacement"}, {"date": "2025-11-02", "type": "actuator calibration"}],
            "design_life_cycles": 100000, "cycles_since_overhaul": 71000}


def _write(kind, payload):
    payload["ts"] = time.time(); payload["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if kind == "alert" and os.getenv("ALERT_TOPIC_ARN"):
        import boto3
        boto3.client("sns").publish(TopicArn=os.environ["ALERT_TOPIC_ARN"], Message=json.dumps(payload))
    elif kind == "work_order" and os.getenv("WORK_ORDER_TABLE"):
        import boto3, uuid
        item = json.loads(json.dumps({**payload, "id": str(uuid.uuid4())}), parse_float=Decimal)
        boto3.resource("dynamodb").Table(os.environ["WORK_ORDER_TABLE"]).put_item(Item=item)
    get_store().log(kind, payload)
    return {"status": "recorded", "kind": kind}


def send_alert(severity, message):
    return _write("alert", {"severity": severity, "message": message})


def create_work_order(asset_id, priority, description):
    dup = [w for w in get_store().logs("work_order", time.time() - 86400)
           if w.get("asset_id") == asset_id and w.get("priority") == priority]
    if dup:
        return {"status": "duplicate_skipped", "existing_ts": dup[-1]["ts"]}
    return _write("work_order", {"asset_id": asset_id, "priority": priority, "description": description, "status": "PENDING_APPROVAL"})


REGISTRY = {f.__name__: f for f in (get_sensor_readings, get_trend_analysis, get_maintenance_history, send_alert, create_work_order)}


def dispatch(name, args):
    if name not in REGISTRY:
        return {"error": f"unknown tool {name}"}
    try:
        return REGISTRY[name](**args)
    except Exception as e:  # return errors to the model instead of crashing the loop
        return {"error": str(e)}
