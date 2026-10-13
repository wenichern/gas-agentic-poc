import json, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "poc1_field_ops"))
os.environ["SCENARIO"] = "breach"
import agent


def test_breach_triggers_alert_and_work_order():
    out = json.loads(agent.run("VALVE-101", mock=True))
    assert any("Pressure" in a for a in out["alerts"])
    assert set(out) == {"alerts", "predicted_rul", "summary"}
