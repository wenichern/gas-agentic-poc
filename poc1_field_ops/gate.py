"""Cheap deterministic screen that decides whether the (slow, costly) LLM agent should run."""
from config import breaches, COOLDOWN_MIN, LOOKAHEAD_H, MIN_POINTS, Z_LIMIT


def screen(reading, trend, state):
    """Returns (invoke_agent, reasons, in_breach)."""
    reasons = []
    b = breaches(reading)
    reasons += [f"BREACH: {x}" for x in b]
    for m, t in trend.get("metrics", {}).items():
        h = t["hours_to_threshold"]
        if h is not None and 0 < h <= LOOKAHEAD_H and t["confidence"] != "low":
            reasons.append(f"{m} projected to cross its limit in ~{h}h")
        if trend.get("n_points", 0) >= MIN_POINTS and abs(t["anomaly_z"]) >= Z_LIMIT:
            reasons.append(f"{m} anomalous (z={t['anomaly_z']})")
    in_breach = bool(b)
    if not reasons:
        return False, ["normal"], in_breach
    new_episode = in_breach and not state.get("in_breach", False)   # first reading of a breach always wakes the agent
    cooled = reading["ts"] - state.get("last_agent_run", 0) >= COOLDOWN_MIN * 60
    if new_episode or cooled:
        return True, reasons, in_breach
    return False, ["cooldown"] + reasons, in_breach
