"""Tiny trend/anomaly model in pure Python (linear fit). Swap for a SageMaker endpoint later; keep the same output shape."""
from config import THRESHOLDS, MIN_POINTS


def _fit(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0: return 0.0, my, 0.0, 0.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    ss_res = sum((y - (icpt + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return slope, icpt, (1 - ss_res / ss_tot) if ss_tot > 0 else 0.0, (ss_res / max(n - 2, 1)) ** 0.5


def analyze(readings):
    rs = sorted(readings, key=lambda r: r["ts"])
    out = {"n_points": len(rs), "window_hours": 0.0, "metrics": {}}
    if len(rs) < 3:
        out["note"] = "insufficient data"; return out
    t_last = rs[-1]["ts"]
    xs = [(r["ts"] - t_last) / 3600 for r in rs]   # hours, 0 = newest
    out["window_hours"] = round(-xs[0], 2)
    for m, (kind, thr) in THRESHOLDS.items():
        ys = [r[m] for r in rs]
        s0, i0, _, std0 = _fit(xs[:-1], ys[:-1])    # baseline WITHOUT newest point -> anomaly score
        z = (ys[-1] - i0) / max(std0, 1e-3 * abs(sum(ys) / len(ys)) + 1e-6)
        slope, level, r2, _ = _fit(xs, ys)           # all points -> slope and current level
        if kind == "max":
            h = 0.0 if ys[-1] >= thr else ((thr - level) / slope if slope > 0 else None)
        else:
            h = 0.0 if ys[-1] <= thr else ((level - thr) / -slope if slope < 0 else None)
        if h is not None: h = max(0.0, h)
        if h is not None and h > 72: h = None        # beyond 3 days = not a useful prediction
        conf = "low" if len(rs) < MIN_POINTS or r2 < 0.3 else ("high" if len(rs) >= 36 and r2 >= 0.7 else "medium")
        out["metrics"][m] = {"latest": ys[-1], "slope_per_hour": round(slope, 2), "r2": round(r2, 2),
                             "anomaly_z": round(z, 1), "hours_to_threshold": None if h is None else round(h, 1),
                             "confidence": conf}
    return out
