"""운영 반영 실패 보류 — 카드 생성·라운드 유지·선택 적용."""
import pytest

from scripts.audit import decisions, deploy_hold
from scripts.autopilot import notify, queue


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(notify, "send", lambda *a, **k: None)
    monkeypatch.setattr(deploy_hold.progress, "event", lambda *a, **k: None)


def _st(**kw):
    return {"phase": "develop", "round": 4, "units_done": 20, **kw}


def _fail(kind="tests"):
    return {"ran": True, "outcome": "failed", "kind": kind, "reason": "boom", "commits": 3}


def _choose(dp, action):
    recs = decisions.load(dp)
    c = recs[0]
    c.update(status="chosen", choice=next(o["key"] for o in c["options"] if o["action"] == action))
    decisions.save(recs, dp)


def test_hold_keeps_round_and_opens_card(tmp_path):
    dp, st = tmp_path / "d.json", _st()
    msg = deploy_hold.hold(st, _fail(), dp)
    assert (st["phase"], st["round"], st["units_done"]) == ("deploy_hold", 4, 20) and "DEPLOY-R4" in msg
    c = decisions.load(dp)[0]
    assert c["status"] == "open" and c["recommendation"] and c["review"]
    assert deploy_hold.release(st, tmp_path / "q.md", dp) is None and st["phase"] == "deploy_hold"


@pytest.mark.parametrize("action,phase,rnd", [("retry_now", "deploy_retry", 4), ("retry_later", "audit", 5), ("hold", "halted", 4)])
def test_release_actions(tmp_path, action, phase, rnd):
    dp, st = tmp_path / "d.json", _st()
    deploy_hold.hold(st, _fail("merge"), dp)
    _choose(dp, action)
    assert deploy_hold.release(st, tmp_path / "q.md", dp)
    assert (st["phase"], st["round"]) == (phase, rnd) and decisions.load(dp)[0]["status"] == "applied"


def test_release_fix_unit_queues_once(tmp_path):
    dp, q, st = tmp_path / "d.json", tmp_path / "q.md", _st()
    q.write_text("", encoding="utf-8")
    deploy_hold.hold(st, _fail("tests"), dp)
    _choose(dp, "fix_unit")
    deploy_hold.release(st, q, dp)
    assert st["phase"] == "develop" and [i.item_id for i in queue.parse(q)] == ["DEPLOY-FIX-R4"]
    assert deploy_hold._queue_fix(q, st, "tests", "x") == "DEPLOY-FIX-R4" and len(queue.parse(q)) == 1


def test_redo_status_keeps_waiting(tmp_path):
    dp, st = tmp_path / "d.json", _st()
    deploy_hold.hold(st, _fail(), dp)
    recs = decisions.load(dp)
    recs[0]["status"] = "redo"
    decisions.save(recs, dp)
    assert deploy_hold.release(st, None, dp) is None


def test_retry_success_advances_failure_reholds(tmp_path):
    dp = tmp_path / "d.json"
    st = _st(phase="deploy_retry")
    assert "완료" in deploy_hold.retry(st, lambda n: {"ran": True, "outcome": "done"}, dp)
    assert (st["phase"], st["round"], st["units_done"]) == ("audit", 5, 0)
    st = _st(phase="deploy_retry")
    deploy_hold.retry(st, lambda n: _fail("merge"), dp)
    assert (st["phase"], st["round"]) == ("deploy_hold", 4)


def test_step_waits_then_releases_and_run_until_stop_breaks(tmp_path, monkeypatch):
    from scripts.audit import loop
    dp = tmp_path / "d.json"
    monkeypatch.setattr(decisions, "DECISIONS_PATH", dp)
    monkeypatch.setattr(loop.notify, "send", lambda *a, **k: True)
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": True, "reason": ""})())
    q = tmp_path / "q.md"
    q.write_text("", encoding="utf-8")
    st = _st()
    deploy_hold.hold(st, _fail("merge"), dp)
    assert loop.step(st, path=q).startswith("결정 대기") and st["phase"] == "deploy_hold"
    out = loop.run_until_stop(st, path=q)
    assert out and out[-1].startswith("결정 대기") and st["phase"] == "deploy_hold"
    _choose(dp, "retry_later")
    loop.step(st, path=q)
    assert (st["phase"], st["round"]) == ("audit", 5)
