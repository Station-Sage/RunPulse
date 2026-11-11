"""V2-AUDIT 묶음 D(데이터·설정) — 오류 문구 정리·연결 실패 구분·동기화 상태·소스 토글·기준값 검사."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest
from flask import Flask

from src.api import api_bp
from src.services import data_connect_service as dcs
from src.services import data_service, profile_service as ps, sync_state_service as sss
from src.services.sync_trigger_service import connection_skip
from src.sync.sync_errors import check_failure_reason, classify_text, public_message
from src.utils import sync_jobs

RAW = ("GET https://intervals.icu/api/v1/athlete/i123 연결 실패: HTTPSConnectionPool(host='intervals.icu', "
       "port=443): Max retries exceeded (NameResolutionError)")


def test_classify_text_and_public_message():
    assert classify_text(RAW) == "network"
    assert classify_text("Read timed out") == "timeout"
    assert classify_text("GET x failed: 503") == "upstream_5xx"
    assert classify_text(None) == "unknown"
    msg = public_message(None, RAW)
    assert "intervals.icu" not in msg and "네트워크" in msg
    assert public_message("auth_expired", RAW).startswith("인증이 만료")


def test_check_failure_reason():
    assert check_failure_reason({"ok": False, "status": "서버 연결 실패", "reason": "network"}) == "network"
    assert check_failure_reason({"ok": False, "status": "연결 실패", "detail": RAW}) == "network"
    assert check_failure_reason({"ok": False, "status": "잘못된 API 키", "detail": "인증 실패 (401)"}) == "credentials"
    assert check_failure_reason({"ok": False, "status": "설정 누락", "detail": "api_key 미설정"}) == "credentials"


def _job(i, service, status, error=None, code=None, hours_ago=1.0):
    t = (datetime.now() - timedelta(hours=hours_ago + i / 100)).isoformat(timespec="seconds")
    return sync_jobs.SyncJob(f"j{i}", service, "2026-10-01", "2026-10-07", 7, None, status, 7, 7, 3, 0, t, t,
                             None, error, error_code=code, finished_at=t)


def test_sync_state_error_has_no_raw_detail(monkeypatch):
    conn = sqlite3.connect(":memory:")
    from src.db_setup import create_tables, migrate_db
    create_tables(conn)
    migrate_db(conn)
    cfg = {"intervals": {"api_key": "k"}, "sync_sources": ["intervals"]}
    monkeypatch.setattr(sss, "list_recent_jobs", lambda p, limit=20, **kw: [_job(1, p, "failed", RAW)]
                        if p == "intervals" else [])
    s = sss.get_sync_state(conn, cfg)
    err = next(x for x in s["sources"] if x["provider"] == "intervals")["last_error"]
    assert err["code"] == "network" and "detail" not in err and "intervals.icu" not in str(err)
    assert s["overall"]["label_ko"] == "성공한 동기화 없음"  # D-06: 시도는 있었으나 성공 없음


def test_sync_state_finds_success_beyond_recent_window(monkeypatch):
    conn = sqlite3.connect(":memory:")
    from src.db_setup import create_tables, migrate_db
    create_tables(conn)
    migrate_db(conn)
    cfg = {"garmin": {"email": "x"}, "sync_sources": ["garmin"]}
    fails = [_job(i, "garmin", "failed", code="network") for i in range(20)]
    ok = _job(99, "garmin", "completed", hours_ago=30)

    def fake(p, limit=20, *, status=None, **_kw):
        if p != "garmin":
            return []
        return [ok] if status == "completed" else fails[:limit]

    monkeypatch.setattr(sss, "list_recent_jobs", fake)
    g = next(x for x in sss.get_sync_state(conn, cfg)["sources"] if x["provider"] == "garmin")
    assert g["last_success_at"] is not None


def test_list_recent_jobs_filters_services_and_status():
    a = sync_jobs.create_job("garmin", "2026-10-01", "2026-10-02")
    sync_jobs.create_job("export", "2026-10-01", "2026-10-02")
    sync_jobs.update_job(a.id, status="completed")
    assert {j.service for j in sync_jobs.list_recent_jobs(None, 10, services=("garmin",))} == {"garmin"}
    assert [j.id for j in sync_jobs.list_recent_jobs("garmin", 10, status="completed")] == [a.id]


def test_runs_hide_raw_error_and_non_sync_jobs():
    j = sync_jobs.create_job("intervals", "2026-10-01", "2026-10-02")
    sync_jobs.update_job(j.id, status="failed", last_error=RAW)
    e = sync_jobs.create_job("export", "2026-10-01", "2026-10-02")
    sync_jobs.update_job(e.id, status="completed")
    runs = data_service.runs()
    assert [r["provider"] for r in runs] == ["intervals"]
    assert "intervals.icu" not in runs[0]["last_error"] and "네트워크" in runs[0]["last_error"]


def test_connect_failure_message_distinguishes_network():
    reason, msg = dcs.failure_message("intervals", {"ok": False, "status": "연결 실패", "detail": RAW})
    assert reason == "network" and "Intervals.icu 서버에 연결하지 못했어요" in msg
    reason, msg = dcs.failure_message("intervals", {"ok": False, "status": "잘못된 API 키"})
    assert reason == "credentials" and msg == "연결하지 못했어요 · 잘못된 API 키"


def test_connection_skip_codes():
    assert connection_skip("intervals", {"ok": False, "reason": "network", "status": "서버 연결 실패"}).code == "unreachable"
    assert connection_skip("runalyze", {"ok": False, "status": "토큰 없음"}).code == "not_connected"


def test_strava_app_ready():
    assert dcs.strava_app_ready({"client_id": "12345", "client_secret": "abcdef"})
    assert not dcs.strava_app_ready({"client_id": " ", "client_secret": "abc"})
    assert not dcs.strava_app_ready({"client_id": "app", "client_secret": "abc"})
    assert not dcs.strava_app_ready({"client_id": "1", "client_secret": "a b"})


@pytest.fixture
def rd_client(monkeypatch):
    import src.api.routes_data as rd

    cfg = {"intervals": {"athlete_id": "i1", "api_key": "k"}, "sync_sources": ["intervals"]}
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: cfg)
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, cfg, rd


def test_trigger_unreachable_is_503(rd_client, monkeypatch, tmp_path):
    from src.services import sync_trigger_service as sts

    c, _cfg, rd = rd_client
    monkeypatch.setattr(rd, "db_path", lambda: tmp_path / "x.db")
    (tmp_path / "x.db").write_bytes(b"")
    monkeypatch.setattr(sts, "_checkers", lambda: {p: (lambda cfg: {"ok": False, "status": "서버 연결 실패",
                                                                     "reason": "network"}) for p in sts.ALL_SOURCES})
    r = c.post("/api/v1/data/sync", json={"sources": ["intervals"]}, headers={"Origin": "http://localhost"})
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "SOURCE_UNREACHABLE"


def test_patch_unconnected_source_is_409(rd_client):
    c = rd_client[0]
    r = c.patch("/api/v1/data/sources/runalyze", json={"sync_enabled": False}, headers={"Origin": "http://localhost"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "NOT_CONNECTED"


def test_is_connected():
    assert sss.is_connected({"runalyze": {"token": "t"}}, "runalyze")
    assert not sss.is_connected({}, "runalyze") and not sss.is_connected({}, "coros")


@pytest.fixture
def pconn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE metric_store (metric_name TEXT, scope_type TEXT, scope_id TEXT, "
              "numeric_value REAL, provider TEXT, is_primary INTEGER)")
    c.execute("CREATE TABLE daily_wellness (date TEXT, resting_hr INTEGER)")
    c.executemany("INSERT INTO metric_store VALUES (?,?,?,?,?,?)", [
        ("hrmax_self", "daily", "2026-10-01", 192, "runpulse:formula_v1", 1),
        ("lthr_self", "daily", "2026-10-01", 178, "runpulse:formula_v1", 1)])
    yield c
    c.close()


def test_check_changes_lthr_must_be_below_hrmax(pconn):
    ch, _ = ps.validate_changes({"overrides": {"hrmax": 125}, "source_choice": {"hrmax": "manual"}})
    code, msg = ps.check_changes(pconn, {}, ch)
    assert code == "INVALID_PARAM" and "178" in msg and "125" in msg
    ok, _ = ps.validate_changes({"overrides": {"hrmax": 195}, "source_choice": {"hrmax": "manual"}})
    assert ps.check_changes(pconn, {}, ok) is None
    weekly, _ = ps.validate_changes({"overrides": {"weekly_km": 40}})  # 심박을 안 건드리면 기존 상태로 막지 않음
    assert ps.check_changes(pconn, {"profile": {"overrides": {"hrmax": 125}}}, weekly) is None


def test_check_changes_source_without_value(pconn):
    ch, _ = ps.validate_changes({"source_choice": {"threshold_pace": "device"}})
    code, msg = ps.check_changes(pconn, {}, ch)
    assert code == "SOURCE_UNAVAILABLE" and "기기 값" in msg


def test_profile_patch_status_codes(monkeypatch, tmp_path, pconn):
    import src.api.routes_data_profile as rp

    monkeypatch.setattr(rp, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rp, "load_config", lambda user_id=None: {})
    monkeypatch.setattr(ps, "save_config", lambda c, user_id=None: None)
    monkeypatch.setattr(rp, "db_path", lambda: tmp_path / "x.db")
    f = sqlite3.connect(tmp_path / "x.db")
    f.executescript("\n".join(pconn.iterdump()))
    f.close()
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    h = {"Origin": "http://localhost"}
    with app.test_client() as c:
        assert c.patch("/api/v1/data/profile", json={"overrides": {"hrmax": 125}}, headers=h).status_code == 400
        assert c.patch("/api/v1/data/profile", json={"source_choice": {"lthr": "device"}}, headers=h).status_code == 422
        assert c.patch("/api/v1/data/profile", json={"overrides": {"hrmax": 196}}, headers=h).status_code == 200
