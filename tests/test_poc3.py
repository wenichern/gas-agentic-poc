import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "poc3_compliance"))
import agent
from retriever import LocalRetriever
from validator import validate


def test_retrieval_finds_right_sop():
    top = LocalRetriever().search("Records retention", "procedures")[0]
    assert top["id"] == "SOP-REC-02 §2.1"


def test_agent_finds_two_gaps_and_one_compliant():
    out = agent.run(str(pathlib.Path(agent.HERE, "data", "new_bulletin.md")), mock=True)
    assert len(out["gaps"]) == 2
    assert any(p["procedure"] == "SOP-OD-03 §5.1" for p in out["impacted_procedures"])
    assert "DRAFT" in out["status"]


def test_validator_catches_hallucinated_citation():
    bad = {"bulletin_summary": "x", "impacted_procedures": [], "deadlines": [], "status": "DRAFT",
           "draft_actions": [], "gaps": [{"description": "d", "severity": "HIGH", "citations": ["SOP-FAKE §9"]}]}
    assert any("SOP-FAKE" in p for p in validate(bad, {"SOP-LS-01 §3.1"}))
