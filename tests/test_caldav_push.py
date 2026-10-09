"""CalDAV 연동: UID 멱등 등록·사라진 일정 삭제·실패 사유·재계획 동기화 (mocked DAVClient)."""
import sys
import types
from datetime import date, timedelta

import pytest

from src.db_schema_v34 import ensure_v34
from src.training import caldav_push as C
from tests.helpers_pred import mem_conn

D = date.today() + timedelta(days=1)
CFG = {"caldav": {"url": "https://x/", "username": "u", "password": "p"}}


class FakeEvent:
    def __init__(self, store, uid):
        self.store, self.uid = store, uid

    def delete(self):
        self.store.pop(self.uid)


class FakeCal:
    name = "cal"

    def __init__(self):
        self.events = {}

    def save_event(self, vcal):
        uid = next(x[4:] for x in vcal.split("\r\n") if x.startswith("UID:"))
        self.events[uid] = vcal

    def event_by_uid(self, uid):
        return FakeEvent(self.events, uid)


@pytest.fixture
def cal(monkeypatch):
    fc = FakeCal()
    mod = types.SimpleNamespace(DAVClient=lambda **k: types.SimpleNamespace(
        principal=lambda: types.SimpleNamespace(calendars=lambda: [fc])))
    monkeypatch.setitem(sys.modules, "caldav", mod)
    return fc


@pytest.fixture
def c():
    conn = mem_conn()
    ensure_v34(conn)
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, source) VALUES (?, 'easy', 8, 'planner')",
                 (D.isoformat(),))
    conn.commit()
    return conn


def test_push_is_idempotent_and_dtend_next_day(c, cal):
    f, t = D.isoformat(), D.isoformat()
    assert C.push_range(CFG, c, f, t) == 1 and C.push_range(CFG, c, f, t) == 1
    assert len(cal.events) == 1
    v = next(iter(cal.events.values()))
    assert f"DTEND;VALUE=DATE:{(D + timedelta(days=1)).strftime('%Y%m%d')}" in v


def test_removed_workout_is_deleted_remotely(c, cal):
    f = D.isoformat()
    C.push_range(CFG, c, f, f)
    c.execute("DELETE FROM planned_workouts")
    C.push_range(CFG, c, f, f)
    assert cal.events == {} and c.execute("SELECT COUNT(*) FROM caldav_pushes").fetchone()[0] == 0


def test_not_installed_raises(c, monkeypatch):
    monkeypatch.setitem(sys.modules, "caldav", None)
    with pytest.raises(C.CalDavUnavailable):
        C.push_range(CFG, c, D.isoformat(), D.isoformat())
    assert C.test_connection(CFG) == (False, "캘린더 연동 모듈이 설치되지 않았어요.")


def test_connection_reasons(monkeypatch):
    def boom(**k):
        raise RuntimeError("401 Unauthorized")
    monkeypatch.setitem(sys.modules, "caldav", types.SimpleNamespace(DAVClient=boom))
    assert "비밀번호" in C.test_connection(CFG)[1]
    empty = types.SimpleNamespace(DAVClient=lambda **k: types.SimpleNamespace(principal=lambda: types.SimpleNamespace(calendars=lambda: [])))
    monkeypatch.setitem(sys.modules, "caldav", empty)
    assert "캘린더가 없어요" in C.test_connection(CFG)[1]
    assert C.test_connection({})[0] is False


def test_sync_after_replan_noop_without_pushes_and_swallows_errors(c, cal, monkeypatch):
    f = D.isoformat()
    assert C.sync_after_replan(CFG, c, f, f) is None
    C.push_range(CFG, c, f, f)
    monkeypatch.setattr(C, "push_range", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    assert C.sync_after_replan(CFG, c, f, f)["synced"] == 0
    assert C.sync_after_replan({}, c, f, f) is None
