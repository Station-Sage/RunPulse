"""OpsStore(T1) — 멱등 DDL, UPSERT, 14/90일 보존 경계, 사용자 삭제."""
from datetime import datetime, timedelta

import pytest

from src.ops.store import OpsStore, default_store, ops_db_path

NOW = datetime(2026, 11, 6, 12, 0, 0)


@pytest.fixture
def store(tmp_path):
    return OpsStore(tmp_path / "ops.db", clock=lambda: NOW)


def test_ddl_idempotent(tmp_path):
    a = OpsStore(tmp_path / "x.db")
    a.touch_activity("u", NOW)
    b = OpsStore(tmp_path / "x.db")  # 같은 파일에 DDL 재실행
    assert b.last_active("u") == NOW


def test_ops_db_path_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "e.db"))
    assert ops_db_path() == tmp_path / "e.db"
    assert default_store().path == tmp_path / "e.db"


def test_touch_activity_returns_previous(store):
    assert store.touch_activity("u", NOW - timedelta(days=3)) is None
    assert store.touch_activity("u", NOW) == NOW - timedelta(days=3)
    assert store.all_activity() == {"u": NOW}


def test_state_upsert_roundtrip(store):
    store.put_state("u", next_due_at=NOW, fail_streak=2, auth_streak={"garmin": 1}, last_result="fail")
    store.put_state("u", next_due_at=NOW + timedelta(hours=1), state="dormant", fail_streak=3)
    st = store.get_state("u")
    assert st["next_due_at"] == NOW + timedelta(hours=1)
    assert (st["state"], st["fail_streak"], st["auth_streak"]) == ("dormant", 3, {})
    assert set(store.all_states()) == {"u"}
    assert store.get_state("nobody") is None


def test_add_run_and_runs_since(store):
    store.add_run("u", started_at=NOW, finished_at=NOW + timedelta(seconds=90), result="ok",
                  sources=["garmin", "strava"], job_ids=["j1"])
    runs = store.runs_since(NOW - timedelta(hours=1))
    assert runs[0]["duration_s"] == 90 and runs[0]["sources"] == "garmin,strava"


def test_usage_accumulates_user_and_global(store):
    store.add_usage("2026-11-06", "a", "coach", calls=1, tokens_in=10, tokens_out=5)
    store.add_usage("2026-11-06", "a", "coach", calls=1, tokens_in=1, tokens_out=1)
    store.add_usage("2026-11-06", "b", "warm", calls=1, refused=1)
    assert store.usage("2026-11-06", "a") == {"calls": 2, "tokens": 17, "refused": 0}
    assert store.usage("2026-11-06") == {"calls": 3, "tokens": 17, "refused": 1}
    assert store.top_usage("2026-11-06")[0]["uid"] == "a"


def test_purge_boundaries(store):
    store.add_run("u", started_at=NOW - timedelta(days=14, seconds=1), result="ok")
    store.add_run("u", started_at=NOW - timedelta(days=14), result="ok")
    store.add_usage((NOW - timedelta(days=91)).date().isoformat(), "u", "coach", calls=1)
    store.add_usage((NOW - timedelta(days=90)).date().isoformat(), "u", "coach", calls=1)
    assert store.purge() == {"sched_runs": 1, "llm_usage_daily": 1}
    assert len(store.runs_since(NOW - timedelta(days=30))) == 1


def test_delete_user_removes_all_rows(store):
    store.touch_activity("u")
    store.put_state("u", next_due_at=NOW)
    store.add_run("u", started_at=NOW, result="ok")
    store.add_usage("d", "u", "coach", calls=1)
    store.add_usage("d", "v", "coach", calls=1)
    store.delete_user("u")
    assert store.last_active("u") is None and store.get_state("u") is None
    assert store.usage("d") ["calls"] == 1
