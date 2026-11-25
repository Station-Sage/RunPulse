import json

from scripts.audit import decisions, docs_ctx, steward

BODY = "새 비전 본문 " * 20
YES = json.dumps({"change": True, "reason": "근거 있음", "new_vision": BODY})


def _env(tmp_path):
    (tmp_path / "VISION.md").write_text("# t\n\n> n\n\n옛 본문", encoding="utf-8")
    return tmp_path, tmp_path / "d.json", tmp_path / "plan.json"


def test_parse():
    assert steward.parse(YES)["reason"] == "근거 있음"
    assert steward.parse('{"change":false}') is None
    assert steward.parse(json.dumps({"change": True, "reason": "x", "new_vision": "짧"})) is None


def test_step_creates_proposal_and_decision_once(tmp_path):
    root, d, pl = _env(tmp_path)
    r = steward.step(ask=lambda *a, **k: YES, root=root, dpath=d, plan_path=pl)
    assert "결정 대기" in r
    assert (root / "vision-proposals" / "v2.md").exists()
    rec = decisions.load(d)[0]
    assert rec["id"] == "VIS-v2" and rec["kind"] == "vision" and rec["status"] == "open"
    assert "이미" in steward.step(ask=lambda *a, **k: 1 / 0, root=root, dpath=d, plan_path=pl)


def test_step_no_change_writes_nothing(tmp_path):
    root, d, pl = _env(tmp_path)
    assert "변경 없음" in steward.step(ask=lambda *a, **k: '{"change":false}', root=root, dpath=d, plan_path=pl)
    assert not (root / "vision-proposals").exists() and decisions.load(d) == []


def test_apply_choice_A_replaces_vision_with_backup(tmp_path):
    root, d, pl = _env(tmp_path)
    steward.step(ask=lambda *a, **k: YES, root=root, dpath=d, plan_path=pl)
    decisions.choose("VIS-v2", "A", d)
    note = steward.apply_choice(decisions.load(d)[0], dpath=d, root=root)
    assert "반영" in note
    v = (root / "VISION.md").read_text(encoding="utf-8")
    assert "새 비전 본문" in v and v.startswith("# t") and "옛 본문" not in v
    assert "옛 본문" in (root / "vision-proposals" / "v2.prev.md").read_text(encoding="utf-8")
    assert decisions.load(d)[0]["status"] == "applied"


def test_apply_choice_B_rejects(tmp_path):
    root, d, pl = _env(tmp_path)
    steward.step(ask=lambda *a, **k: YES, root=root, dpath=d, plan_path=pl)
    decisions.choose("VIS-v2", "B", d)
    assert "기각" in steward.apply_choice(decisions.load(d)[0], dpath=d, root=root)
    assert "옛 본문" in (root / "VISION.md").read_text(encoding="utf-8")
