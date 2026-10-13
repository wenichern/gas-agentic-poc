"""Readings, per-asset state and logs. LocalStore (files in OUT_DIR) or DynamoStore (when READINGS_TABLE is set)."""
import json, os, pathlib, time
from decimal import Decimal

RETENTION_S = 7 * 86400
LOG_FILES = ("readings.jsonl", "state.json", "alerts.jsonl", "work_orders.jsonl", "assessments.jsonl")


def out_dir():
    p = pathlib.Path(os.getenv("OUT_DIR", "out")); p.mkdir(parents=True, exist_ok=True); return p


class LocalStore:
    def _f(self, name): return out_dir() / name

    def _read(self, name):
        f = self._f(name)
        return [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []

    def reset(self):
        for n in LOG_FILES:
            if self._f(n).exists(): self._f(n).unlink()

    def put_reading(self, r):
        with open(self._f("readings.jsonl"), "a") as f: f.write(json.dumps(r) + "\n")

    def recent(self, asset, hours=6):
        by_ts = {r["ts"]: r for r in self._read("readings.jsonl") if r["asset_id"] == asset}
        rows = [by_ts[k] for k in sorted(by_ts)]
        if not rows: return []
        cutoff = rows[-1]["ts"] - hours * 3600   # window is relative to the newest reading, not wall clock
        return [r for r in rows if r["ts"] >= cutoff]

    def get_state(self, asset):
        f = self._f("state.json")
        return json.loads(f.read_text()).get(asset, {}) if f.exists() else {}

    def set_state(self, asset, state):
        f = self._f("state.json"); allst = json.loads(f.read_text()) if f.exists() else {}
        allst[asset] = state; f.write_text(json.dumps(allst))

    def log(self, kind, payload):
        with open(self._f(f"{kind}s.jsonl"), "a") as f: f.write(json.dumps(payload) + "\n")

    def logs(self, kind, since_ts=0):
        return [p for p in self._read(f"{kind}s.jsonl") if p.get("ts", 0) >= since_ts]


class DynamoStore:
    """Table: pk (S) + ts (N). Readings pk=asset, logs pk='LOG#<kind>', state pk='STATE#<asset>'. TTL attr: expires_at."""

    def __init__(self, table):
        import boto3
        self.t = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1")).Table(table)

    @staticmethod
    def _dec(o): return json.loads(json.dumps(o), parse_float=Decimal)  # DynamoDB rejects Python floats

    @staticmethod
    def _undec(o):
        if isinstance(o, list): return [DynamoStore._undec(x) for x in o]
        if isinstance(o, dict): return {k: DynamoStore._undec(v) for k, v in o.items()}
        if isinstance(o, Decimal): return int(o) if o == o.to_integral_value() else float(o)
        return o

    def put_reading(self, r):
        self.t.put_item(Item=self._dec({**r, "pk": r["asset_id"], "expires_at": int(r["ts"]) + RETENTION_S}))

    def recent(self, asset, hours=6):
        from boto3.dynamodb.conditions import Key
        newest = self.t.query(KeyConditionExpression=Key("pk").eq(asset), ScanIndexForward=False, Limit=1)["Items"]
        if not newest: return []
        cutoff = newest[0]["ts"] - Decimal(int(hours * 3600))
        items = self.t.query(KeyConditionExpression=Key("pk").eq(asset) & Key("ts").gte(cutoff))["Items"]
        return [self._undec(i) for i in items]  # ascending by ts; one page is plenty for a few hundred points

    def get_state(self, asset):
        it = self.t.get_item(Key={"pk": f"STATE#{asset}", "ts": 0}).get("Item")
        return self._undec(it.get("state", {})) if it else {}

    def set_state(self, asset, state):
        self.t.put_item(Item=self._dec({"pk": f"STATE#{asset}", "ts": 0, "state": state}))

    def log(self, kind, payload):
        self.t.put_item(Item=self._dec({"pk": f"LOG#{kind}", "ts": int(time.time() * 1e6), "payload": payload,
                                        "expires_at": int(time.time()) + RETENTION_S}))

    def logs(self, kind, since_ts=0):
        from boto3.dynamodb.conditions import Key
        items = self.t.query(KeyConditionExpression=Key("pk").eq(f"LOG#{kind}") & Key("ts").gte(Decimal(int(since_ts * 1e6))))["Items"]
        return [self._undec(i["payload"]) for i in items]


def get_store():
    table = os.getenv("READINGS_TABLE")
    return DynamoStore(table) if table else LocalStore()
