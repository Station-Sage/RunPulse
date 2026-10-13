"""tests/test_api_input_contracts.py — SRV 1차 적용 4개 라우트 입력 계약 (T-15·P-04·P-05·C-02, ADR-048).

재현 값은 설계서 §4 2단계 목록. 잘못된 값은 조용히 보정하지 않고 400 INVALID_PARAM + details.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


@pytest.fixture(autouse=True)
def _fake_ai_chat(monkeypatch):
    from src.ai.chat_engine_result import ChatResult, EngineInfo

    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None, consent=None,
              require_consent=False, on_event=None, cancelled=None):
        return ChatResult("[fake]", EngineInfo("ok", "fake", "fake-model"), as_of="2026-09-30")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)
    from src.services import coach_async
    monkeypatch.setattr(coach_async, "INLINE", True)
    coach_async._RUNS.clear()


@pytest.fixture
def ctx(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    import src.api.routes_coach as rc
    import src.api.routes_plan as rp
    import src.api.routes_today as rt
    origs = [(m, m.db_path) for m in (rc, rp, rt)]
    for m, _ in origs:
        m.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as client:
        yield client, db_file
    for m, orig in origs:
        m.db_path = orig


def _details(res, status=400):
    assert res.status_code == status, res.get_data(as_text=True)
    err = res.get_json()["error"]
    assert err["code"] == "INVALID_PARAM"
    return err["details"]


def _rows(db_file, sql):
    conn = sqlite3.connect(str(db_file))
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# ── T-15 체크인 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fatigue", [0, 11, 5.5, "x", -1, True, [], {}])
def test_checkin_rejects_bad_fatigue(ctx, fatigue):
    client, db = ctx
    res = client.post("/api/v1/today/checkin", json={"fatigue": fatigue})
    assert "fatigue" in _details(res)
    assert _rows(db, "SELECT COUNT(*) FROM user_inputs") == [(0,)]


def test_checkin_rejects_bad_pain_and_long_note(ctx):
    client, _ = ctx
    assert "pain" in _details(client.post("/api/v1/today/checkin", json={"pain": "bogus"}))
    assert "note" in _details(client.post("/api/v1/today/checkin", json={"note": "가" * 501}))
    assert "note" in _details(client.post("/api/v1/today/checkin", json={"note": 123}))


def test_checkin_boundaries_accepted(ctx):
    client, _ = ctx
    for fatigue in (1, 10):
        assert client.post("/api/v1/today/checkin", json={"fatigue": fatigue}).status_code == 200
    res = client.post("/api/v1/today/checkin", json={"fatigue": "5", "pain": "severe", "note": "가" * 500})
    assert res.status_code == 200 and res.get_json()["data"]["fatigue"] == 5


def test_checkin_non_json_is_415_and_broken_json_400(ctx):
    client, db = ctx
    res = client.post("/api/v1/today/checkin", data="fatigue=5", content_type="text/plain")
    assert res.status_code == 415 and res.get_json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    res = client.post("/api/v1/today/checkin", data="{oops", content_type="application/json")
    assert "body" in _details(res)
    assert _rows(db, "SELECT COUNT(*) FROM user_inputs") == [(0,)]


def test_save_checkin_service_keeps_minimal_invariant():
    from src.services.today_service import save_checkin
    conn = sqlite3.connect(":memory:")
    with pytest.raises(ValueError):
        save_checkin(conn, fatigue=11)
    with pytest.raises(ValueError):
        save_checkin(conn, pain="bogus")


# ── P-04 templates ───────────────────────────────────────────────────────────

def _race(days):
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.mark.parametrize("qs,field", [
    ("distance_km=0", "distance_km"),
    ("distance_km=251", "distance_km"),
    ("distance_km=abc", "distance_km"),
    ("distance_km=10&target_time_sec=0", "target_time_sec"),
    ("distance_km=10&target_time_sec=172801", "target_time_sec"),
    ("distance_km=10&target_time_sec=99:99:99", "target_time_sec"),
    ("distance_km=10&race_date=garbage", "race_date"),
    ("distance_km=10&race_date=2020-01-01", "race_date"),
])
def test_templates_rejects(ctx, qs, field):
    client, _ = ctx
    assert field in _details(client.get(f"/api/v1/coach/plan/templates?{qs}"))


def test_templates_rejects_race_date_past_5_years(ctx):
    client, _ = ctx
    far = date.today().replace(year=date.today().year + 6).isoformat() if not (
        date.today().month == 2 and date.today().day == 29) else "2099-01-01"
    assert "race_date" in _details(client.get(f"/api/v1/coach/plan/templates?distance_km=10&race_date={far}"))


def test_templates_today_race_date_and_optional_fields_ok(ctx):
    client, _ = ctx
    assert client.get(f"/api/v1/coach/plan/templates?distance_km=10&race_date={_race(0)}").status_code == 200
    assert client.get("/api/v1/coach/plan/templates?distance_km=42.195&target_time_sec=14400").status_code == 200
    assert client.get("/api/v1/coach/plan/templates?distance_km=10&race_date=&target_time_sec=").status_code == 200


# ── P-05 plan create ─────────────────────────────────────────────────────────

def _plan(client, **over):
    body = {"distance_km": 10.0, "weeks": 8, **over}
    return client.post("/api/v1/coach/plan", json=body)


@pytest.mark.parametrize("over,field", [
    ({"weeks": 0}, "weeks"), ({"weeks": -3}, "weeks"), ({"weeks": 500}, "weeks"), ({"weeks": "x"}, "weeks"),
    ({"weeks": 5.5}, "weeks"),
    ({"distance_km": "abc"}, "distance_km"), ({"distance_km": 0}, "distance_km"),
    ({"distance_km": 251}, "distance_km"),
    ({"race_date": "garbage"}, "race_date"), ({"race_date": "2020-01-01"}, "race_date"),
    ({"target_time_sec": 0}, "target_time_sec"), ({"target_time_sec": "99:99:99"}, "target_time_sec"),
    ({"target_time_sec": 172801}, "target_time_sec"),
    ({"name": "n" * 101}, "name"),
    ({"recent_weekly_km": "abc"}, "recent_weekly_km"), ({"recent_weekly_km": -1}, "recent_weekly_km"),
    ({"recent_long_km": 99}, "recent_long_km"),
])
def test_plan_create_rejects(ctx, over, field):
    client, db = ctx
    assert field in _details(_plan(client, **over))
    assert _rows(db, "SELECT COUNT(*) FROM goals") == [(0,)]


def test_plan_create_missing_required_fields(ctx):
    client, _ = ctx
    res = client.post("/api/v1/coach/plan", json={})
    assert set(_details(res)) == {"distance_km", "weeks"}


def test_plan_create_non_json_415(ctx):
    client, _ = ctx
    res = client.post("/api/v1/coach/plan", data="x", content_type="text/plain")
    assert res.status_code == 415


def test_plan_create_string_numbers_accepted(ctx):
    client, _ = ctx
    res = _plan(client, distance_km="10", weeks="8", target_time_sec="2700")
    assert res.status_code == 200 and res.get_json()["data"]["plan_weeks"] == 8
    assert "meta" not in res.get_json()


def test_plan_create_weeks_adjusted_returns_meta_warning(ctx):
    """가능 주수(avail)보다 긴 weeks 는 보정하되 meta.warnings 로 알린다(SRV-7·SRV-11)."""
    client, _ = ctx
    res = _plan(client, weeks=30, race_date=_race(21))
    assert res.status_code == 200
    body = res.get_json()
    applied = body["data"]["plan_weeks"]
    assert applied < 30
    assert body["meta"]["warnings"] == [{"code": "WEEKS_ADJUSTED", "requested": 30, "applied": applied}]


def test_plan_create_race_date_today_ok(ctx):
    client, _ = ctx
    assert _plan(client, weeks=1, race_date=_race(0)).status_code == 200


def test_plan_service_keeps_minimal_invariant(ctx):
    from src.services import plan_template_service as svc
    conn = sqlite3.connect(":memory:")
    with pytest.raises(ValueError):
        svc.create_plan_from_template(conn, 10.0, None, 0)
    with pytest.raises(ValueError):
        svc.create_plan_from_template(conn, 0, None, 8)
    with pytest.raises(ValueError):
        svc.get_static_plan_templates(conn, -5)


# ── C-02 coach ───────────────────────────────────────────────────────────────

def test_coach_create_thread_rejects_non_string_message(ctx):
    """C-02 재현: initial_message=123 은 예전엔 AttributeError → HTML 500."""
    client, db = ctx
    assert "initial_message" in _details(client.post("/api/v1/coach/threads", json={"initial_message": 123}))
    assert _rows(db, "SELECT COUNT(*) FROM chat_threads") == [(0,)]


def test_coach_rejects_long_message_and_bad_ids(ctx):
    client, _ = ctx
    assert "initial_message" in _details(
        client.post("/api/v1/coach/threads", json={"initial_message": "가" * 4001}))
    assert "client_msg_id" in _details(
        client.post("/api/v1/coach/threads", json={"initial_message": "hi", "client_msg_id": "x" * 101}))
    assert "client_msg_id" in _details(
        client.post("/api/v1/coach/threads", json={"initial_message": "hi", "client_msg_id": 5}))
    assert "chip_id" in _details(client.post("/api/v1/coach/threads", json={"chip_id": "nope"}))
    assert "chip_id" in _details(client.post("/api/v1/coach/threads", json={"chip_id": ["a"]}))
    assert "context" in _details(
        client.post("/api/v1/coach/threads", json={"initial_message": "hi", "context": "activity"}))
    assert "context" in _details(
        client.post("/api/v1/coach/threads", json={"initial_message": "hi", "context": {"kind": "k" * 33}}))


def test_coach_message_boundaries_and_whitespace(ctx):
    client, _ = ctx
    res = client.post("/api/v1/coach/threads", json={"initial_message": "가" * 4000})
    assert res.status_code == 201
    tid = res.get_json()["data"]["thread"]["id"]
    # 공백뿐인 본문 + chip 없음 → 400, chip 만 있으면 통과
    assert "content" in _details(client.post(f"/api/v1/coach/threads/{tid}/messages", json={"content": "   "}))
    assert client.post(f"/api/v1/coach/threads/{tid}/messages", json={"chip_id": "week_plan"}).status_code == 201
    assert "content" in _details(client.post(f"/api/v1/coach/threads/{tid}/messages", json={"content": 123}))
    assert "content" in _details(
        client.post(f"/api/v1/coach/threads/{tid}/messages", json={"content": "가" * 4001}))


def test_coach_context_and_client_msg_id_pass_through(ctx):
    client, _ = ctx
    res = client.post("/api/v1/coach/threads", json={
        "initial_message": " 후반 심박 ", "client_msg_id": "abc-1", "context": {"kind": "activity", "ref": "7"}})
    assert res.status_code == 201
    assert res.get_json()["data"]["thread"]["context"] == {"kind": "activity", "ref": "7"}
    again = client.post("/api/v1/coach/threads", json={
        "initial_message": " 후반 심박 ", "client_msg_id": "abc-1", "context": {"kind": "activity", "ref": "7"}})
    assert again.status_code == 200  # 같은 client_msg_id 재전송은 멱등


def test_coach_non_json_415(ctx):
    client, _ = ctx
    res = client.post("/api/v1/coach/threads", data="hi", content_type="text/plain")
    assert res.status_code == 415


# ── 안전망: 검증 밖 예외도 JSON ──────────────────────────────────────────────

def test_unvalidated_route_exception_is_json_500(ctx, monkeypatch):
    client, _ = ctx
    import src.api.routes_today as rt

    def boom(*a, **k):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(rt.today_service, "save_checkin", boom)
    res = client.post("/api/v1/today/checkin", json={"fatigue": 5})
    assert res.status_code == 500
    assert res.get_json()["error"]["code"] == "INTERNAL"
    assert "db exploded" not in res.get_data(as_text=True)
