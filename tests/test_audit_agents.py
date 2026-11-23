from scripts.audit import agents
from scripts.audit.perspectives import AUDIT_MODELS, build_prompt


def test_group_issues_and_prompt():
    ledger = {"a|small|390": {"status": "이슈", "note": "tap-target <24px x3"},
              "b|error|390": {"status": "이슈", "note": "error-state missing"},
              "c|small|390": {"status": "확인", "note": ""}}
    g = agents.group_issues(ledger)
    assert set(g) == {"tap-target", "error-state-missing"}
    p = build_prompt("ui", g)
    assert "tap-target: 1건" in p and "JSON" in p


def test_parse_findings_graceful():
    assert agents.parse_findings("not json") == []
    txt = '결과:\n[{"kind":"x","verdict":"real","impact":"i","fix":"f"},{"kind":"y","verdict":"bad"}]'
    assert [f["kind"] for f in agents.parse_findings(txt)] == ["x"]


def test_backlog_lines_dedup_and_models():
    fs = [{"kind": "x", "verdict": "real", "perspective": "ui", "impact": "i", "fix": "f"},
          {"kind": "x", "verdict": "real", "perspective": "ux"}, {"kind": "z", "verdict": "noise", "perspective": "ui"}]
    assert len(agents.backlog_lines(fs)) == 1 and "(판단 필요)" in agents.backlog_lines(fs)[0]
    assert "opus" not in AUDIT_MODELS.values()
