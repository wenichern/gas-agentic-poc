"""Sensor simulator. Scenarios: normal | creep (slow pressure rise, ~4h to limit) | spike | breach.
  python poc1_field_ops/simulator.py --scenario creep --backfill               # local store
  READINGS_TABLE=... python poc1_field_ops/simulator.py --scenario creep --publish   # history to DynamoDB, last point via IoT Core"""
import argparse, json, pathlib, random, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))


def gen(asset, scenario="creep", minutes=360, step=5, now=None, seed=7):
    rnd = random.Random(seed); now = int(now or time.time()); n = minutes // step + 1
    pts = []
    for i in range(n):
        mins = i * step
        p, f, t = 700.0, 90.0, 60.0
        if scenario == "creep":
            p += (10 / 60) * mins; t += 0.02 * mins
        k = min(6, max(0, i - (n - 7)))               # last 6 points
        if scenario == "breach":
            p += 142 * k / 6; f -= 43 * k / 6; t += 28 * k / 6
        p += rnd.gauss(0, 1.5); f += rnd.gauss(0, 2); t += rnd.gauss(0, 0.3)
        if scenario == "spike" and i == n - 1: p = 835.0
        pts.append({"asset_id": asset, "ts": now - (n - 1 - i) * step * 60,
                    "pressure_psi": round(p, 1), "flow_m3h": round(f, 1), "temperature_c": round(t, 1)})
    return pts


def publish(topic, payload):
    import boto3
    ep = boto3.client("iot").describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
    boto3.client("iot-data", endpoint_url=f"https://{ep}").publish(topic=topic, qos=1, payload=json.dumps(payload))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="VALVE-101")
    ap.add_argument("--scenario", default="creep", choices=["normal", "creep", "spike", "breach"])
    ap.add_argument("--backfill", action="store_true", help="write history to the store")
    ap.add_argument("--publish", action="store_true", help="backfill all but the newest point, publish the newest to IoT Core")
    ap.add_argument("--topic-prefix", default="gas/sensors")
    a = ap.parse_args()
    pts = gen(a.asset, a.scenario)
    if a.backfill or a.publish:
        from store import get_store
        s = get_store()
        for r in (pts[:-1] if a.publish else pts): s.put_reading(r)
        print(f"stored {len(pts) - 1 if a.publish else len(pts)} readings")
    if a.publish:
        publish(f"{a.topic_prefix}/{a.asset}", pts[-1]); print("published", pts[-1])
    if not (a.backfill or a.publish):
        print(json.dumps(pts[-3:], indent=1))
