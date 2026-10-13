"""Streaming pipeline logic shared by the Lambda and local replay.
reading -> store -> trend model -> gate -> (only if needed) LLM agent.
  python poc1_field_ops/pipeline.py --scenario creep --mock --reset"""
import argparse, json, math, pathlib, re, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from analytics import analyze
from gate import screen
from store import get_store, LocalStore
import tools

FIELDS = ("pressure_psi", "flow_m3h", "temperature_c")


def parse_event(event):
    """Sensor messages are UNTRUSTED input. asset_id ends up in a prompt, so allow only a strict pattern."""
    asset = str(event.get("asset_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", asset):
        raise ValueError("bad asset_id")
    r = {"asset_id": asset, "ts": int(event.get("ts") or time.time())}
    for f in FIELDS:
        v = float(event[f])
        if not math.isfinite(v) or not -100 <= v <= 10000:
            raise ValueError(f"{f} outside sane range")
        r[f] = v
    return r


def process_reading(reading, mock=False, verbose=False):
    store = get_store(); asset = reading["asset_id"]
    store.put_reading(reading)
    trend = analyze(store.recent(asset, 6))
    state = store.get_state(asset)
    invoke, reasons, in_breach = screen(reading, trend, state)
    result = None
    if invoke:
        try:
            import agent
            result = agent.run(asset, mock, verbose=verbose)
        except Exception as e:   # safety floor: a model outage must never silence a real breach
            result = json.dumps({"error": str(e)})
            if in_breach:
                tools.send_alert("HIGH", f"Agent unavailable ({e}). Raw limit breach on {asset}: {reasons}")
        state = {"last_agent_run": reading["ts"], "in_breach": in_breach}
    else:
        state = {**state, "in_breach": in_breach}
    store.set_state(asset, state)
    return {"invoked": invoke, "reasons": reasons, "result": result}


def replay(asset, scenario, mock, reset):
    from simulator import gen
    s = get_store()
    if reset and isinstance(s, LocalStore): s.reset()
    pts = gen(asset, scenario)
    calls = 0
    for r in pts:
        out = process_reading(r, mock)
        if out["invoked"]:
            calls += 1
            print(f"[{time.strftime('%H:%M', time.gmtime(r['ts']))}] agent woken: {out['reasons']}")
    print(f"\n{len(pts)} readings processed, {calls} LLM call(s) (instead of {len(pts)})")
    return calls


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="VALVE-101")
    ap.add_argument("--scenario", default="creep", choices=["normal", "creep", "spike", "breach"])
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--reset", action="store_true", help="clear local out/ files first")
    a = ap.parse_args()
    replay(a.asset, a.scenario, a.mock, a.reset)
