"""시계열·인사이트·체크인·예측 조회 도구 (V2-AI-CLAUDE-QUEUE E4)."""
import json
import sqlite3

import pytest

from src.ai import tool_exec_series as T
from src.ai.tools import _DISPATCH
from src.db_schema_v20 import ensure_v20
from src.db_schema_v21 import ensure_v21
from src.db_schema_v25 import ensure_v25
from src.db_schema_v38 import ensure_v38
from src.db_schema_v46 import ensure_v46
from src.db_schema_v47 import ensure_v47
from src.db_setup import create_tables
from src.mcp_remote import policy


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    for f in (ensure_v20, ensure_v21, ensure_v25, ensure_v38, ensure_v46, ensure_v47):
        f(c)
    return c


def test_registered_and_classified():
    for n in ("get_wellness_series", "get_activity_stream", "get_insights", "get_checkins", "get_predictions"):
        assert n in _DISPATCH
    assert not policy.unclassified_tools()
    assert "get_activity_stream" in policy.LOCAL_ONLY_TOOLS


def test_wellness_series_kinds_and_values(conn):
    for i, v in enumerate([50, 60, 70]):
        conn.execute("INSERT INTO wellness_series(date,source,kind,ts,value) VALUES (?,?,?,?,?)",
                     (f"2026-11-1{i}", "garmin", "hrv", i, v))
    r = T._exec_get_wellness_series(conn, {"date_from": "2026-11-10", "date_to": "2026-11-18"})
    assert r["kinds"]["rows"][0][:2] == ["hrv", 3]
    r = T._exec_get_wellness_series(conn, {"kind": "hrv", "date_from": "2026-11-10", "date_to": "2026-11-18"})
    assert r["baseline"]["mean_7d"] == 60.0 and len(r["rows"]) == 3


def test_wellness_series_caps_range(conn):
    s, e = T._clamp_days({"date_from": "2020-01-01", "date_to": "2026-11-18"}, 14, 120)
    assert (T.date.fromisoformat(e) - T.date.fromisoformat(s)).days + 1 == 120


def _stream(conn, n=1000):
    for t in range(n):
        conn.execute("INSERT INTO activity_streams(activity_id,source,elapsed_sec,heart_rate) VALUES (1,'garmin',?,?)",
                     (t, 100 + t % 50))


def test_activity_stream_resample_and_cap(conn):
    _stream(conn, 20000)
    r = T._exec_get_activity_stream(conn, {"activity_id": 1, "channel": "heart_rate", "resample_sec": 1})
    assert len(r["rows"]) <= 300 and r["stats"]["n"] == 20000
    r = T._exec_get_activity_stream(conn, {"activity_id": 1, "from_sec": 0, "to_sec": 299})
    assert len(r["rows"]) == 10


def test_activity_stream_errors(conn):
    assert "error" in T._exec_get_activity_stream(conn, {})
    assert "error" in T._exec_get_activity_stream(conn, {"activity_id": 1, "channel": "latitude; DROP"})
    assert T._exec_get_activity_stream(conn, {"activity_id": 9})["error"] == "스트림 없음"


def test_insights_order_and_state(conn):
    ins = "INSERT INTO insight_events(kind,severity,as_of,dedupe_key,signals_json,text,state) VALUES (?,?,?,?,?,?,?)"
    conn.execute(ins, ("a", "info", "2026-11-18", "a:1", "[]", "정보", "open"))
    conn.execute(ins, ("b", "act", "2026-11-17", "b:1", json.dumps([{"signal": "acwr"}]), "행동", "seen"))
    conn.execute(ins, ("c", "act", "2026-11-18", "c:1", "bad json", "닫힘", "dismissed"))
    r = T._exec_get_insights(conn, {})
    assert [x[1] for x in r["rows"]] == ["b", "a"]
    assert [x[1] for x in T._exec_get_insights(conn, {"state": "dismissed"})["rows"]] == ["c"]


def test_checkins_redact_without_consent(conn):
    conn.execute("INSERT INTO user_inputs(input_date,input_type,fatigue,pain,mood,note) VALUES (date('now'),'checkin',6,'감기 기운',3,'열이 남')")
    r = T._exec_get_checkins(conn, {})
    row = r["checkins"]["rows"][0]
    assert "감기" not in json.dumps(row, ensure_ascii=False) and "열이" not in json.dumps(row, ensure_ascii=False)


def test_checkins_with_consent(conn):
    conn.execute("INSERT INTO illness_consent_events(action, via) VALUES ('grant','settings')")
    conn.execute("INSERT INTO user_inputs(input_date,input_type,fatigue,pain,mood,note) VALUES (date('now'),'checkin',6,'감기 기운',3,'메모')")
    row = T._exec_get_checkins(conn, {})["checkins"]["rows"][0]
    assert "감기 기운" in row and "메모" in row


def test_predictions_sections(conn):
    conn.execute("INSERT INTO prediction_snapshots(as_of,provider,distance_m,pred_s) VALUES ('2026-11-18','p',42195,12000)")
    conn.execute("INSERT INTO activity_best_efforts(activity_id,source,effort_name,elapsed_sec,distance_m) VALUES (1,'g','5K',1200,5000)")
    conn.execute("INSERT INTO race_results(activity_id,race_name,distance_m,official_time_sec,effort) VALUES (1,'r',10000,2500,'allout')")
    r = T._exec_get_predictions(conn, {})
    assert r["predictions"]["rows"][0][3] == 12000
    assert r["best_efforts"]["rows"][0][:2] == ["5K", 1200]
    assert r["races"]["rows"][0][0] == "r"
