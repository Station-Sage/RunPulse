"""V2-AUDIT 묶음 D(데이터·설정) — 가져오기 판별·크기 제한, 내보내기 기간·행 수·진행률, 토큰·AI 키·본문 검증."""
from __future__ import annotations

import io
import sqlite3
import zipfile

import pytest
from flask import Flask

from src.api import api_bp
from src.services import ai_settings_service as ais
from src.services import export_archive as ea
from src.services import export_service as es
from src.services import import_detect as idt
from src.services import import_service as ims

H = {"Origin": "http://localhost"}
STRAVA = "Activity ID,Activity Date,Activity Name,Activity Type,Distance\n1,\"Oct 1, 2026, 7:00:00 AM\",R,Run,1\n"
GARMIN = "활동 종류,날짜,거리\n러닝,2026-10-01 07:00:00,5\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_detect_unknown_csv_and_source_mismatch(tmp_path):
    assert idt.detect_kind([_write(tmp_path, "a.csv", "a,b\n1,2\n")])[1].startswith("알 수 없는 CSV")
    s = _write(tmp_path, "s.csv", STRAVA)
    g = _write(tmp_path, "g.csv", GARMIN)
    assert idt.detect_kind([s], "strava") == ("strava_csv", None)
    assert idt.detect_kind([g], "garmin") == ("garmin_csv", None)
    kind, err = idt.detect_kind([s], "garmin")
    assert kind is None and "Strava 파일로 보여요" in err
    assert "Garmin 파일로" in idt.detect_kind([g], "strava")[1]


def test_detect_broken_csv_field(tmp_path):
    p = _write(tmp_path, "big.csv", "Activity Date,x\n1,\"" + "y" * 200_000 + "\"\n")
    kind, err = idt.detect_kind([p])
    assert kind is None and "CSV를 읽지 못했어요" in err


def test_detect_zip_traversal(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../activities.csv", STRAVA)
    assert "허용되지 않는 경로" in idt.detect_kind([z])[1]
    assert idt.unsafe_member("/etc/x") and idt.unsafe_member("a/../../b") and not idt.unsafe_member("export/a.csv")


def test_extension_hint_follows_source(tmp_path):
    assert idt.extension_hint("garmin").startswith("Garmin")
    assert idt.extension_hint("strava").startswith("Strava")
    assert "Garmin" in idt.detect_kind([tmp_path / "x.txt"], "garmin")[1]


@pytest.fixture
def import_client(monkeypatch, tmp_path):
    from src import db_setup
    import src.api.routes_data_import as ri

    p = tmp_path / "running.db"
    monkeypatch.setattr(db_setup, "get_db_path", lambda uid=None: p)
    monkeypatch.setattr(ims, "get_db_path", lambda uid=None: p)
    db_setup.init_db()
    monkeypatch.setattr(ri, "db_path", lambda: p)
    monkeypatch.setattr(ri, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(ims, "imports_dir", lambda uid: tmp_path / "imports")
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, tmp_path / "imports"


def _upload(c, name, data, source="strava", **kw):
    return c.post("/api/v1/data/import/preview", data={"files": (io.BytesIO(data), name), "source": source},
                  content_type="multipart/form-data", headers=H, **kw)


def test_import_rejections_leave_no_upload_dir(import_client):
    c, root = import_client
    r = _upload(c, "a.csv", b"a,b\n1,2\n")
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_UPLOAD"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../activities.csv", STRAVA)
    assert _upload(c, "e.zip", buf.getvalue()).status_code == 400
    big = ("Activity Date,x\n1,\"" + "y" * 200_000 + "\"\n").encode()
    assert _upload(c, "big.csv", big).status_code == 400
    assert not root.exists() or not any(root.iterdir())


def test_import_too_large_before_write(import_client, monkeypatch):
    c, root = import_client
    monkeypatch.setattr(ims, "MAX_BYTES", 10)
    import src.api.routes_data_import as ri
    monkeypatch.setattr(ri, "_FORM_SLACK", 10)
    r = _upload(c, "s.csv", STRAVA.encode())
    assert r.status_code == 413 and r.get_json()["error"]["code"] == "TOO_LARGE"
    assert not root.exists()


@pytest.fixture
def econn():
    c = sqlite3.connect(":memory:")
    c.executescript("""
    CREATE TABLE daily_wellness (date TEXT, sleep_score INT, sleep_duration_sec INT, hrv_weekly_avg REAL,
      hrv_last_night REAL, resting_hr INT, body_battery_high INT, body_battery_low INT, avg_stress INT,
      steps INT, active_calories INT, weight_kg REAL);
    INSERT INTO daily_wellness (date, resting_hr) VALUES ('2026-10-01', 50);
    INSERT INTO daily_wellness (date) VALUES ('2026-10-02');
    """)
    yield c
    c.close()


def test_export_params_messages_and_future():
    assert es.parse_params({"kind": "quick_load", "from": "2026-09-30", "to": "2026-01-01"})[1] == "시작일이 종료일보다 늦어요"
    assert es.parse_params({"kind": "quick_load", "from": "bad"})[1] == "시작일은 YYYY-MM-DD 형식이에요"
    assert "오늘 이후" in es.parse_params({"kind": "quick_load", "from": "2999-01-01"})[1]


def test_quick_filename_includes_period():
    assert es.quick_filename("quick_load", "2026-01-01", "2026-03-31") == "runpulse_load_2026-01-01_2026-03-31.csv"
    assert es.quick_filename("quick_load").startswith("runpulse_load_20")


def test_wellness_csv_skips_empty_rows(econn):
    rows = list(es.wellness_csv(econn))
    assert [r[0] for r in rows[1:]] == ["2026-10-01"]
    text, n = es.quick_export(econn, "quick_wellness")
    assert n == 1 and text.startswith("﻿")


def test_export_route_content_type_and_rows(monkeypatch, tmp_path, econn):
    import src.api.routes_data_export as rx

    dbp = tmp_path / "x.db"
    f = sqlite3.connect(dbp)
    f.executescript("\n".join(econn.iterdump()))
    f.close()
    monkeypatch.setattr(rx, "db_path", lambda: dbp)
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        r = c.post("/api/v1/data/export", json={"kind": "quick_wellness", "from": "2026-10-02"}, headers=H)
        assert r.status_code == 200 and r.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert r.headers["X-Export-Rows"] == "0" and "2026-10-02" in r.headers["Content-Disposition"]


def test_build_archive_reports_progress(tmp_path):
    from src.db_setup import create_tables, migrate_db

    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    migrate_db(conn)
    calls = []
    ea.build_archive(conn, tmp_path / "a.zip", ("metrics",), progress=lambda d, t: calls.append((d, t)))
    assert calls[0][0] == 0 and calls[-1][0] == calls[-1][1] and len(calls) >= 3


@pytest.fixture
def token_client(monkeypatch, tmp_path):
    from src.api import routes_mcp_tokens as r
    from src.db_setup import create_tables
    from src.mcp_remote import token_index as ti

    monkeypatch.setattr(ti, "index_path", lambda: tmp_path / "mcp_tokens.db")
    users = tmp_path / "users"
    monkeypatch.setattr(ti, "get_db_path", lambda uid=None, create=True: users / (uid or "default") / "running.db")
    (users / "u1").mkdir(parents=True)
    c = sqlite3.connect(users / "u1" / "running.db")
    create_tables(c)
    c.close()
    monkeypatch.setattr(r, "get_current_user_id", lambda: "u1")
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app.test_client()


@pytest.mark.parametrize("body,code", [
    ({"label": "x", "days": 0}, "BAD_DAYS"), ({"label": "x", "days": -5}, "BAD_DAYS"),
    ({"label": "x", "days": 99999999}, "BAD_DAYS"), ({"label": "x", "days": 1.9}, "BAD_DAYS"),
    ({"label": ["x"]}, "LABEL_INVALID"), ({"label": "y" * 41}, "LABEL_TOO_LONG"), ([1], "INVALID_PARAM"),
])
def test_mcp_token_body_validation(token_client, body, code):
    r = token_client.post("/api/v1/settings/mcp-tokens", json=body, headers=H)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == code


def test_mcp_token_days_integer_ok(token_client):
    r = token_client.post("/api/v1/settings/mcp-tokens", json={"label": "x", "days": 30}, headers=H)
    assert r.status_code == 201


def test_json_object_rejects_array_on_calendar_feed(monkeypatch):
    import src.api.routes_data_calendar as rc

    monkeypatch.setattr(rc, "get_current_user_id", lambda: "u")
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    r = app.test_client().post("/api/v1/data/calendar-feed", json=[1], headers=H)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_PARAM"


@pytest.mark.parametrize("key", ["ab cd", "abc\ndef", "<b>key</b>", "k" * 300, "키값"])
def test_ai_key_format_rejected(key):
    assert ais.key_format_error(key)
    assert ais.validate_patch({"keys": {"gemini": key}})[1]


def test_ai_key_ok_and_blank_feedback():
    assert ais.key_format_error("AIzaSy-abc_123") is None
    assert ais.validate_patch({"keys": {"gemini": "   "}}) == ({}, "API 키를 입력해 주세요")
    out, err = ais.validate_patch({"keys": {"gemini": ""}, "exclude_notes": True})
    assert err is None and out == {"exclude_notes": True}
