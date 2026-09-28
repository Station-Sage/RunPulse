"""tests/test_sync_state_service.py — SyncState 계약(작업 원장 기준 동기화 상태)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import sync_state_service as svc
from src.utils.sync_jobs import SyncJob

NOW = datetime(2026, 9, 28, 13, 0, 0).astimezone()


def _job(service: str, status: str, hours_ago: float, last_error: str | None = None) -> SyncJob:
    t = (NOW - timedelta(hours=hours_ago)).replace(tzinfo=None).isoformat(timespec="seconds")
    return SyncJob(f"{service}-{status}-{hours_ago}", service, "2026-09-14", "2026-09-28", 14, None,
                   status, 14, 14, 0, 0, t, t, None, last_error)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


CONFIG = {"garmin": {"email": "x"}, "intervals": {"api_key": "k"}, "strava": {"refresh_token": "t"},
          "sync_sources": ["garmin", "intervals"]}


def _state(conn, monkeypatch, jobs: dict[str, list[SyncJob]]):
    monkeypatch.setattr(svc, "list_recent_jobs", lambda p, limit=20: jobs.get(p, []))
    return svc.get_sync_state(conn, CONFIG, now=NOW)


def test_ok_when_recent_success(conn, monkeypatch):
    s = _state(conn, monkeypatch, {"garmin": [_job("garmin", "completed", 0.5)],
                                   "intervals": [_job("intervals", "completed", 1)]})
    assert s["overall"]["level"] == "ok"
    assert s["overall"]["label_ko"] == "30분 전 동기화"
    by = {x["provider"]: x for x in s["sources"]}
    assert by["garmin"]["state"] == "idle-ok"
    assert by["strava"]["state"] == "disabled"
    assert by["runalyze"]["state"] == "not_connected"


def test_restart_stopped_job_is_not_an_error(conn, monkeypatch):
    s = _state(conn, monkeypatch, {"garmin": [_job("garmin", "stopped", 0.2, "프로세스 재시작으로 중단됨"),
                                              _job("garmin", "completed", 1)],
                                   "intervals": [_job("intervals", "completed", 1)]})
    assert s["open_errors"] == 0


def test_auth_error_and_caveat(conn, monkeypatch):
    s = _state(conn, monkeypatch, {"garmin": [_job("garmin", "auth_required", 1, "토큰 만료"),
                                              _job("garmin", "completed", 50)],
                                   "intervals": [_job("intervals", "completed", 1)]})
    g = next(x for x in s["sources"] if x["provider"] == "garmin")
    assert g["state"] == "error-auth_expired" and g["last_error"]["action"] == "reconnect"
    assert s["overall"]["level"] == "error"
    assert {"code": "source_missing", "provider": "garmin", "days": 2} in s["caveats"]


def test_stale_when_success_older_than_12h(conn, monkeypatch):
    s = _state(conn, monkeypatch, {"garmin": [_job("garmin", "completed", 13)],
                                   "intervals": [_job("intervals", "completed", 1)]})
    assert s["overall"]["level"] == "stale"


def test_payload_time_converted_from_utc(conn, monkeypatch):
    conn.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload, fetched_at)"
                 " VALUES ('garmin', 'activity', '1', '{}', '2026-09-28 02:56:47')")
    s = _state(conn, monkeypatch, {})
    g = next(x for x in s["sources"] if x["provider"] == "garmin")
    assert datetime.fromisoformat(g["last_new_data_at"]) == datetime(2026, 9, 28, 2, 56, 47).replace(
        tzinfo=__import__("datetime").timezone.utc)
