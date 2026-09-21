"""랩(세트) 조회 도구 — get_activity_laps, compare_workout_sets."""
import json
import sqlite3

from src.ai.tools import TOOL_DECLARATIONS, execute_tool
from src.db_setup import create_tables


def _conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _add_activity(conn, aid, name, start, km=10.0):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, "
        "start_time, distance_m, duration_sec, avg_pace_sec_km, avg_hr) "
        "VALUES (?,?,?,?,'running',?,?,?,?,?)",
        (aid, "garmin", f"g{aid}", name, start, km * 1000, 3000, 300, 150),
    )


def _add_lap(conn, aid, idx, trigger, pace, hr=None, cad=None, power=None, dist=1000.0):
    conn.execute(
        "INSERT INTO activity_laps (activity_id, source, lap_index, distance_m, "
        "duration_sec, avg_pace_sec_km, avg_hr, avg_cadence, avg_power, lap_trigger) "
        "VALUES (?,'garmin',?,?,?,?,?,?,?,?)",
        (aid, idx, dist, int(pace * dist / 1000), pace, hr, cad, power, trigger),
    )


def _seed_tempo(conn, aid=1, day="2026-02-18"):
    _add_activity(conn, aid, "2. 템포런", f"{day} 15:40:41")
    _add_lap(conn, aid, 0, "WARMUP", 344, hr=106, cad=156, power=225, dist=130)
    for i, (pace, hr) in enumerate([(277, 155), (274, 169), (280, 173)], start=1):
        _add_lap(conn, aid, i, "ACTIVE", pace, hr=hr, cad=180, power=289)
    _add_lap(conn, aid, 4, "COOLDOWN", 827, hr=158, cad=96, power=87, dist=80)
    conn.commit()


def _call(conn, name, args):
    return json.loads(execute_tool(conn, name, args))


class TestToolDeclarations:
    def test_new_tools_declared(self):
        names = {t["name"] for t in TOOL_DECLARATIONS}
        assert {"get_activity_laps", "compare_workout_sets"} <= names

    def test_declarations_have_schema(self):
        for t in TOOL_DECLARATIONS:
            if t["name"] in ("get_activity_laps", "compare_workout_sets"):
                assert t["parameters"]["type"] == "object"
                assert t["description"]


class TestGetActivityLaps:
    def test_returns_compact_rows(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activity_laps", {"activity_id": 1})
        assert out["lap_count"] == 5
        assert out["name"] == "2. 템포런"
        assert len(out["laps"]) == 5
        # 키 반복 없는 배열 형태 — 행 길이가 fields 길이와 같아야 한다
        assert all(len(row) == len(out["fields"]) for row in out["laps"])

    def test_pace_formatted(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activity_laps", {"activity_id": 1})
        pace_i = out["fields"].index("pace")
        assert out["laps"][1][pace_i] == "4:37"

    def test_lap_types_counted(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activity_laps", {"activity_id": 1})
        assert out["lap_types"] == {"WARMUP": 1, "ACTIVE": 3, "COOLDOWN": 1}

    def test_filter_active_only(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activity_laps", {"activity_id": 1, "lap_type": "active"})
        assert out["lap_count"] == 3
        assert out["lap_types"] == {"ACTIVE": 3}

    def test_all_null_column_dropped(self):
        """전부 NULL인 컬럼은 토큰 절약을 위해 헤더에서 제외한다."""
        conn = _conn()
        _add_activity(conn, 2, "이지런", "2026-02-19 06:00:00")
        _add_lap(conn, 2, 0, "INTERVAL", 360, hr=140)
        conn.commit()
        out = _call(conn, "get_activity_laps", {"activity_id": 2})
        assert "hr" in out["fields"]
        assert "pwr" not in out["fields"]
        assert "cad" not in out["fields"]

    def test_no_laps_returns_message(self):
        conn = _conn()
        _add_activity(conn, 3, "랩없음", "2026-02-20 06:00:00")
        conn.commit()
        out = _call(conn, "get_activity_laps", {"activity_id": 3})
        assert out["laps"] == []
        assert "message" in out


class TestCompareWorkoutSets:
    def _seed_two(self, conn):
        _seed_tempo(conn, aid=1, day="2026-02-18")
        _add_activity(conn, 2, "1. 1000m 인터벌", "2026-04-18 06:00:00")
        for i, pace in enumerate([247, 249, 269], start=1):
            _add_lap(conn, 2, i, "ACTIVE", pace, hr=172)
        conn.commit()

    def test_sessions_sorted_recent_first(self):
        conn = _conn()
        self._seed_two(conn)
        out = _call(conn, "compare_workout_sets", {})
        assert out["count"] == 2
        assert out["sessions"][0]["date"] == "2026-04-18"

    def test_set_aggregates(self):
        conn = _conn()
        self._seed_two(conn)
        s = _call(conn, "compare_workout_sets", {"name_contains": "인터벌"})["sessions"][0]
        assert s["sets"] == 3
        assert s["set_paces"] == ["4:07", "4:09", "4:29"]
        assert s["best_pace"] == "4:07"
        assert s["worst_pace"] == "4:29"
        assert s["avg_hr"] == 172

    def test_positive_drift_means_slowdown(self):
        conn = _conn()
        self._seed_two(conn)
        s = _call(conn, "compare_workout_sets", {"name_contains": "인터벌"})["sessions"][0]
        assert s["drift_sec"] == 22

    def test_excludes_non_active_laps(self):
        """워밍업·쿨다운은 작업 구간 집계에서 제외된다."""
        conn = _conn()
        _seed_tempo(conn)
        s = _call(conn, "compare_workout_sets", {})["sessions"][0]
        assert s["sets"] == 3
        assert s["work_km"] == 3.0

    def test_name_filter(self):
        conn = _conn()
        self._seed_two(conn)
        out = _call(conn, "compare_workout_sets", {"name_contains": "템포"})
        assert out["count"] == 1

    def test_date_range_filter(self):
        conn = _conn()
        self._seed_two(conn)
        out = _call(conn, "compare_workout_sets",
                    {"start_date": "2026-03-01", "end_date": "2026-05-01"})
        assert out["count"] == 1
        assert out["sessions"][0]["date"] == "2026-04-18"

    def test_limit(self):
        conn = _conn()
        self._seed_two(conn)
        assert _call(conn, "compare_workout_sets", {"limit": 1})["count"] == 1

    def test_auto_lap_run_is_not_a_workout(self):
        """자동 1km랩(INTERVAL)만 있는 러닝은 구조화 워크아웃이 아니다."""
        conn = _conn()
        _add_activity(conn, 5, "장거리 달리기", "2026-01-03 10:30:13")
        for i in range(5):
            _add_lap(conn, 5, i, "INTERVAL", 360, hr=150)
        conn.commit()
        out = _call(conn, "compare_workout_sets", {})
        assert out["sessions"] == []
        assert "message" in out


class TestActivityIdExposed:
    """activity_id가 없으면 랩 도구를 호출할 수 없다."""

    def test_get_activity_includes_id(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activity", {"date": "2026-02-18"})
        assert out["activities"][0]["activity_id"] == 1

    def test_get_activities_range_includes_id(self):
        conn = _conn()
        _seed_tempo(conn)
        out = _call(conn, "get_activities_range",
                    {"start_date": "2026-02-01", "end_date": "2026-02-28"})
        assert out["activities"][0]["activity_id"] == 1
