"""Single source of truth for limits and gating rules. prompts/system.md must agree with THRESHOLDS (a test checks)."""
THRESHOLDS = {"pressure_psi": ("max", 800.0), "flow_m3h": ("min", 50.0), "temperature_c": ("max", 90.0)}
COOLDOWN_MIN = 60     # min minutes between LLM runs per asset (a NEW breach episode bypasses this)
LOOKAHEAD_H = 6       # wake the agent if a limit is projected within this many hours
MIN_POINTS = 12      # below this, trend and anomaly scores are too noisy to act on
Z_LIMIT = 4.0         # wake the agent if the latest reading is this many std-devs off the trend


def breaches(r):
    out = []
    for m, (kind, thr) in THRESHOLDS.items():
        v = r[m]
        if kind == "max" and v > thr: out.append(f"{m} {v} above {thr}")
        if kind == "min" and v < thr: out.append(f"{m} {v} below {thr}")
    return out
