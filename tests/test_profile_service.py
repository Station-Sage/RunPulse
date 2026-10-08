"""profile_service — 자체 추정/기기/직접 입력 병합과 사용값 결정, PATCH 검증."""
from __future__ import annotations

import sqlite3

import pytest

from src.services import profile_service as ps


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE metric_store (metric_name TEXT, scope_type TEXT, scope_id TEXT, "
              "numeric_value REAL, provider TEXT, is_primary INTEGER)")
    c.execute("CREATE TABLE daily_wellness (date TEXT, resting_hr INTEGER)")
    c.executemany("INSERT INTO metric_store VALUES (?,?,?,?,?,?)", [
        ("hrmax_self", "daily", "2026-10-01", 188.4, "runpulse:formula_v1", 1),
        ("lthr_self", "daily", "2026-10-01", 168.0, "runpulse:formula_v1", 1),
        ("hrmax_ref", "daily", "2026-10-02", 190, "garmin", 0),
    ])
    c.executemany("INSERT INTO daily_wellness VALUES (?,?)", [(f"2026-10-0{i}", 50 + i) for i in range(1, 6)])
    yield c
    c.close()


def _row(rows, key):
    return next(r for r in rows if r["key"] == key)


def test_rows_merge_self_and_device(conn):
    rows = ps.profile_rows(conn, {})
    hr = _row(rows, "hrmax")
    assert hr["self"]["value"] == 188 and hr["device"] == {"value": 190, "provider": "garmin", "at": "2026-10-02"}
    assert hr["using"] == "self"
    assert _row(rows, "resting_hr")["self"]["value"] == 53
    assert _row(rows, "lthr")["device"] is None
    assert _row(rows, "weekly_km")["using"] == "none"


def test_manual_override_wins_and_choice_respected(conn):
    cfg = {"profile": {"overrides": {"hrmax": 192}, "source_choice": {}}}
    assert _row(ps.profile_rows(conn, cfg), "hrmax")["using"] == "manual"
    cfg["profile"]["source_choice"] = {"hrmax": "device"}
    assert _row(ps.profile_rows(conn, cfg), "hrmax")["using"] == "device"
    cfg["profile"]["source_choice"] = {"hrmax": "self"}
    assert ps.effective_value(cfg, "hrmax", conn) == 188


def test_choice_without_value_falls_back(conn):
    cfg = {"profile": {"source_choice": {"lthr": "device"}}}
    assert _row(ps.profile_rows(conn, cfg), "lthr")["using"] == "self"


def test_legacy_keys_read_as_manual(conn):
    cfg = {"user": {"max_hr": 185, "threshold_pace": 300, "weekly_distance_target": 45.0}}
    assert ps.effective_value(cfg, "hrmax") == 185
    assert ps.effective_value(cfg, "threshold_pace") == 300
    assert _row(ps.profile_rows(conn, cfg), "weekly_km")["manual"] == {"value": 45.0}


def test_validate_changes():
    ok, err = ps.validate_changes({"overrides": {"hrmax": 191.6, "lthr": None}, "source_choice": {"hrmax": "manual"}})
    assert err is None and ok["overrides"] == {"hrmax": 192, "lthr": None}
    for bad in ({"overrides": {"hrmax": 999}}, {"overrides": {"x": 1}}, {"overrides": {"hrmax": True}},
                {"source_choice": {"hrmax": "nope"}}, {}):
        assert ps.validate_changes(bad)[1]


def test_apply_changes_sets_and_clears(monkeypatch):
    saved = []
    monkeypatch.setattr(ps, "save_config", lambda c, user_id=None: saved.append(c))
    cfg = {"profile": {"overrides": {"lthr": 160}}}
    ps.apply_changes(cfg, "u", {"overrides": {"hrmax": 190, "lthr": None}, "source_choice": {"hrmax": "manual"}})
    assert cfg["profile"] == {"overrides": {"hrmax": 190}, "source_choice": {"hrmax": "manual"}} and saved


def test_profile_api_roundtrip(monkeypatch, tmp_path, conn):
    from flask import Flask

    import src.api.routes_data as rd
    from src.api import api_bp

    cfg: dict = {}
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: cfg)
    monkeypatch.setattr(ps, "save_config", lambda c, user_id=None: None)
    monkeypatch.setattr(rd, "db_path", lambda: tmp_path / "x.db")
    f = sqlite3.connect(tmp_path / "x.db")
    f.executescript("\n".join(conn.iterdump()))
    f.close()
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        assert len(c.get("/api/v1/data/profile").get_json()["data"]["rows"]) == 5
        r = c.patch("/api/v1/data/profile", json={"overrides": {"hrmax": 191}, "source_choice": {"hrmax": "manual"}})
        assert r.status_code == 200
        row = next(x for x in r.get_json()["data"]["rows"] if x["key"] == "hrmax")
        assert row["using"] == "manual" and row["manual"]["value"] == 191
        assert c.patch("/api/v1/data/profile", json={"overrides": {"hrmax": 5}}).status_code == 400


def test_preview_zones_and_affected(conn):
    from src.services import recompute_service as rs

    conn.execute("CREATE TABLE activity_summaries (start_time TEXT, avg_hr INTEGER)")
    from datetime import date
    conn.execute("INSERT INTO activity_summaries VALUES (?,150)", (date.today().isoformat(),))
    ch, _ = ps.validate_changes({"overrides": {"hrmax": 200}, "source_choice": {"hrmax": "manual"}})
    out = rs.preview_profile(conn, {}, ch)
    assert out["changed_keys"] == ["hrmax"] and out["zones_before"] != out["zones_after"]
    assert out["affected_days"] == 1 and "TRIMP" in out["affected_metrics"]
    ch, _ = ps.validate_changes({"overrides": {"weekly_km": 40}})
    assert rs.preview_profile(conn, {}, ch)["affected_days"] == 0


def test_before_after_status():
    from src.services import recompute_service as rs

    rows = rs.before_after({"ctl": {"value": 40.0}, "tsb": None}, {"ctl": {"value": 42.5}, "tsb": {"value": 1.0}})
    d = {r["slug"]: r for r in rows}
    assert d["ctl"]["delta"] == 2.5 and d["ctl"]["status"] == "changed"
    assert d["tsb"]["status"] == "new" and d["vdot"]["status"] == "unavailable"


def test_job_routes(monkeypatch, tmp_path):
    from flask import Flask

    import src.api.routes_data as rd
    import src.services.recompute_service as rs
    from src.api import api_bp
    from src.utils import sync_jobs

    monkeypatch.setattr(sync_jobs, "_jobs_db_path", lambda uid=None: str(tmp_path / "jobs.db"))
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "db_path", lambda: tmp_path / "x.db")
    (tmp_path / "x.db").write_bytes(b"")
    started = []
    monkeypatch.setattr(rs.threading, "Thread", lambda **kw: type("T", (), {"start": lambda self: started.append(kw)})())
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        assert c.post("/api/v1/data/recompute", json={"scope": "x"}).status_code == 400
        assert c.post("/api/v1/data/recompute", json={"scope": "from", "from": "bad"}).status_code == 400
        r = c.post("/api/v1/data/recompute", json={"scope": "90d", "reason": "t"})
        assert r.status_code == 202 and started
        jid = r.get_json()["data"]["job_id"]
        assert c.post("/api/v1/data/recompute", json={"scope": "all"}).status_code == 409
        j = c.get(f"/api/v1/data/jobs/{jid}").get_json()["data"]
        assert j["state"] == "queued" and j["result"] is None
        sync_jobs.update_job(jid, status="completed", result_json='{"before_after": []}')
        assert c.get(f"/api/v1/data/jobs/{jid}").get_json()["data"]["state"] == "done"
        assert c.get("/api/v1/data/jobs/nope").status_code == 404
