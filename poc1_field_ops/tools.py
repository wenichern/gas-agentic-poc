"""Tools the agent may call. Sensors are simulated; alerts/work orders go to AWS if configured, else local files."""
import json, os, random, pathlib, datetime

SCENARIO = os.getenv("SCENARIO", "breach")  # "normal" | "breach"
OUT = pathlib.Path("out"); OUT.mkdir(exist_ok=True)

TOOL_SPEC = {"tools": [
    {"toolSpec": {"name": "get_sensor_readings", "description": "Latest pressure (psi), flow (m3/h), temperature (C) for an asset.",
      "inputSchema": {"json": {"type": "object", "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}}}},
    {"toolSpec": {"name": "get_maintenance_history", "description": "Past maintenance events and last maintenance date for an asset.",
      "inputSchema": {"json": {"type": "object", "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}}}},
    {"toolSpec": {"name": "send_alert", "description": "Notify the on-duty supervisor. Use only for threshold breaches.",
      "inputSchema": {"json": {"type": "object", "properties": {"severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "message": {"type": "string"}}, "required": ["severity", "message"]}}}},
    {"toolSpec": {"name": "create_work_order", "description": "Open a maintenance work order. Requires human approval before execution in production.",
      "inputSchema": {"json": {"type": "object", "properties": {"asset_id": {"type": "string"}, "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
        "description": {"type": "string"}}, "required": ["asset_id", "priority", "description"]}}}},
]}


def get_sensor_readings(asset_id):
    if SCENARIO == "breach":
        return {"asset_id": asset_id, "pressure_psi": 842.5, "flow_m3h": 47.0, "temperature_c": 88.0}
    return {"asset_id": asset_id, "pressure_psi": round(random.uniform(600, 780), 1),
            "flow_m3h": round(random.uniform(60, 120), 1), "temperature_c": round(random.uniform(40, 80), 1)}


def get_maintenance_history(asset_id):
    return {"asset_id": asset_id, "last_maintenance": "2025-11-02",
            "events": [{"date": "2024-05-10", "type": "seal replacement"}, {"date": "2025-11-02", "type": "actuator calibration"}],
            "design_life_cycles": 100000, "cycles_since_overhaul": 71000}


def _write(kind, payload):
    payload["ts"] = datetime.datetime.utcnow().isoformat()
    if kind == "alert" and os.getenv("ALERT_TOPIC_ARN"):
        import boto3
        boto3.client("sns").publish(TopicArn=os.environ["ALERT_TOPIC_ARN"], Message=json.dumps(payload))
    elif kind == "work_order" and os.getenv("WORK_ORDER_TABLE"):
        import boto3, uuid
        payload["id"] = str(uuid.uuid4())
        boto3.resource("dynamodb").Table(os.environ["WORK_ORDER_TABLE"]).put_item(Item=payload)
    with open(OUT / f"{kind}s.jsonl", "a") as f:
        f.write(json.dumps(payload) + "\n")
    return {"status": "recorded", "kind": kind}


def send_alert(severity, message):
    return _write("alert", {"severity": severity, "message": message})


def create_work_order(asset_id, priority, description):
    return _write("work_order", {"asset_id": asset_id, "priority": priority, "description": description, "status": "PENDING_APPROVAL"})


REGISTRY = {f.__name__: f for f in (get_sensor_readings, get_maintenance_history, send_alert, create_work_order)}


def dispatch(name, args):
    if name not in REGISTRY:
        return {"error": f"unknown tool {name}"}
    try:
        return REGISTRY[name](**args)
    except Exception as e:  # return errors to the model instead of crashing the loop
        return {"error": str(e)}
