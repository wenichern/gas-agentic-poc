"""AWS Lambda entry point. Triggered by an IoT Core rule on gas/sensors/<asset_id>."""
import json, os
os.environ.setdefault("OUT_DIR", "/tmp/out")   # Lambda's filesystem is read-only except /tmp
from pipeline import parse_event, process_reading


def handler(event, context):
    try:
        reading = parse_event(event)
    except (KeyError, ValueError, TypeError) as e:
        print(json.dumps({"rejected": str(e)}))
        return {"invoked": False, "rejected": str(e)}
    out = process_reading(reading, mock=False, verbose=True)
    print(json.dumps({"asset": reading["asset_id"], "invoked": out["invoked"], "reasons": out["reasons"]}))
    return {"invoked": out["invoked"]}
