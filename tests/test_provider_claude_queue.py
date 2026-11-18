"""claude_queue 어댑터·배치 다듬기·내러티브 큐 경로 (V2-AI-CLAUDE-QUEUE E2)."""
import sqlite3

import pytest

from src.ai import provider_claude_queue as pcq
from src.ai.provider_common import ProviderError
from src.db_schema_v47 import ensure_v47
from src.services import insight_polish as P
from src.services import narrative_queue as NQ


def _fake_run(result):
    return lambda *a, **k: result


def test_db_path_and_uid(tmp_path):
    p = tmp_path / "users" / "u@x.com" / "running.db"
    p.parent.mkdir(parents=True)
    c = sqlite3.connect(p)
    assert pcq.db_path_of(c) == str(p)
    assert pcq.uid_of(c) == "u@x.com"


def test_available_false_on_error(monkeypatch):
    monkeypatch.setattr(pcq.claude_queue, "status", lambda *a, **k: 1 / 0)
    assert pcq.available(sqlite3.connect(":memory:"), {}) is False


@pytest.mark.parametrize("res,reason", [
    ({"ok": False, "reason": "quota_sub"}, "quota_sub"),
    ({"ok": False, "reason": "cq_timeout"}, "cq_timeout"),
    ({"ok": False, "reason": "deadline"}, "cq_timeout"),
    ({"ok": False, "reason": "boom"}, "unexpected"),
])
def test_complete_maps_failures(monkeypatch, res, reason):
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    monkeypatch.setattr(pcq, "db_path_of", lambda c: "x")
    monkeypatch.setattr(pcq.claude_queue, "run_job", _fake_run(res))
    c = sqlite3.connect(":memory:")
    with pytest.raises(ProviderError) as e:
        pcq.complete(c, {}, kind="coach", prompt="p")
    assert e.value.reason == reason
    assert pcq.try_complete(c, {}, kind="coach", prompt="p") is None


def test_complete_ok_and_unavailable(monkeypatch):
    c = sqlite3.connect(":memory:")
    monkeypatch.setattr(pcq, "available", lambda *a: False)
    with pytest.raises(ProviderError) as e:
        pcq.complete(c, {}, kind="coach", prompt="p")
    assert e.value.reason == "no_key"
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    monkeypatch.setattr(pcq, "db_path_of", lambda c: "x")
    monkeypatch.setattr(pcq.claude_queue, "run_job", _fake_run({"ok": True, "text": "hi"}))
    assert pcq.complete(c, {}, kind="coach", prompt="p") == "hi"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    ensure_v47(c)
    for i, t in enumerate(["부하가 늘었어요 (ACWR 1.62).", "수면이 짧았어요 (5.2시간)."]):
        c.execute("INSERT INTO insight_events(kind,severity,as_of,dedupe_key,text) VALUES ('k','watch','2026-11-18',?,?)", (f"k:{i}", t))
    c.commit()
    return c


def test_parse_batch():
    assert P.parse_batch('```json\n[{"id":1,"text":"a"}]\n```') == [{"id": 1, "text": "a"}]
    assert P.parse_batch("nope") == [] and P.parse_batch("[1,2]") == []


def test_polish_batch_validates_each(conn, monkeypatch):
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    out = '[{"id":1,"text":"부하가 빠르게 올랐어요(ACWR 1.62)."},{"id":2,"text":"수면 9.9시간"}]'
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: out)
    assert P.polish_open_events(conn, {}) == 1
    rows = dict(conn.execute("SELECT id, text_ai FROM insight_events"))
    assert rows[1] and rows[2] is None


def test_polish_batch_falls_back_when_queue_fails(conn, monkeypatch):
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: None)
    assert P.polish_open_events(conn, {}) == 0  # 기존 체인도 provider 없음


def test_polish_skips_queue_when_unavailable(conn, monkeypatch):
    monkeypatch.setattr(pcq, "available", lambda *a: False)
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: pytest.fail("called"))
    assert P.polish_open_events(conn, {}) == 0


def test_polish_in_background(tmp_path):
    db = tmp_path / "r.db"
    c = sqlite3.connect(db)
    ensure_v47(c)
    c.commit()
    c.close()
    P.polish_in_background(str(db), {})  # 예외 없이 시작


@pytest.mark.parametrize("out,ok", [
    ("이번 달 120km를 달렸어요.", True),
    ("이번 달 999km를 달렸어요.", False),
    ("x" * 401, False), ("", False), ("# 제목", False),
])
def test_validate_narrative(out, ok):
    assert (NQ.validate_narrative("월간 120km 12회", out) is not None) is ok


def test_narrative_via_queue(monkeypatch):
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: "120km 달렸어요")
    assert NQ.narrative_via_queue(None, {}, "120km") == "120km 달렸어요"
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: None)
    assert NQ.narrative_via_queue(None, {}, "120km") is None
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    assert NQ.queue_ready(None, {}) is True


def test_warm_allows_queue_but_request_path_does_not():
    import inspect
    from src.services import narrative_warm, today_service
    assert inspect.signature(today_service.get_today_narrative).parameters["allow_queue"].default is False
    assert "allow_queue=True" in inspect.getsource(narrative_warm.warm_month_narrative)
    from src.api import routes_today
    assert "allow_queue" not in inspect.getsource(routes_today.get_today_narrative)
