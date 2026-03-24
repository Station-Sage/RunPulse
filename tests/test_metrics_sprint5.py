"""Sprint 5 신규 메트릭 단위 테스트: RTTI, WLEI, TPDI."""
from __future__ import annotations

import sqlite3

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """인메모리 SQLite DB + 필요한 최소 스키마."""
    c = sqlite3.connect(":memory:")
    c.execute(
        """CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT DEFAULT 'garmin',
            source_id TEXT,
            start_time TEXT,
            activity_type TEXT DEFAULT 'run',
            distance_km REAL,
            duration_sec INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_pace_sec_km REAL,
            elevation_gain REAL,
            start_lat REAL,
            start_lon REAL,
            trainer INTEGER DEFAULT 0
        )"""
    )
    c.execute(
        """CREATE TABLE computed_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            activity_id INTEGER,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            computed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, activity_id, metric_name)
        )"""
    )
    c.execute(
        """CREATE TABLE activity_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE daily_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT
        )"""
    )
    c.commit()
    return c


# ---------------------------------------------------------------------------
# RTTI
# ---------------------------------------------------------------------------

class TestRTTI:
    def test_pure_function(self):
        from src.metrics.rtti import calc_rtti
        assert abs(calc_rtti(80.0, 100.0) - 80.0) < 0.1
        assert abs(calc_rtti(120.0, 100.0) - 120.0) < 0.1  # 과부하

    def test_zero_optimal_max(self):
        from src.metrics.rtti import calc_rtti
        assert calc_rtti(50.0, 0.0) == 0.0

    def test_saves_to_db(self, conn):
        from src.metrics.rtti import calc_and_save_rtti
        conn.execute(
            """INSERT INTO daily_detail_metrics (date, metric_name, metric_value)
               VALUES (?, ?, ?), (?, ?, ?), (?, ?, ?)""",
            (
                "2026-03-20", "running_tolerance_load", 90.0,
                "2026-03-20", "running_tolerance_optimal_max", 120.0,
                "2026-03-20", "running_tolerance_score", 75.0,
            ),
        )
        conn.commit()
        rtti = calc_and_save_rtti(conn, "2026-03-20")
        assert rtti is not None
        assert abs(rtti - 75.0) < 0.1  # 90/120*100 = 75

        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name='RTTI'"
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 75.0) < 0.1

    def test_no_data_returns_none(self, conn):
        from src.metrics.rtti import calc_and_save_rtti
        result = calc_and_save_rtti(conn, "2026-03-25")
        assert result is None

    def test_uses_recent_7day_fallback(self, conn):
        """당일 데이터 없어도 최근 7일 이내 데이터 사용."""
        from src.metrics.rtti import calc_and_save_rtti
        conn.execute(
            """INSERT INTO daily_detail_metrics (date, metric_name, metric_value)
               VALUES (?, ?, ?), (?, ?, ?)""",
            (
                "2026-03-18", "running_tolerance_load", 60.0,
                "2026-03-18", "running_tolerance_optimal_max", 100.0,
            ),
        )
        conn.commit()
        rtti = calc_and_save_rtti(conn, "2026-03-20")
        assert rtti is not None
        assert abs(rtti - 60.0) < 0.1  # 60/100*100


# ---------------------------------------------------------------------------
# WLEI
# ---------------------------------------------------------------------------

class TestWLEI:
    def test_pure_function_neutral(self):
        from src.metrics.wlei import calc_wlei
        # 20°C, 60% — 스트레스 없음 → WLEI = TRIMP
        result = calc_wlei(100.0, 20.0, 60.0)
        assert abs(result - 100.0) < 0.1

    def test_pure_function_hot_humid(self):
        from src.metrics.wlei import calc_wlei
        # 30°C, 80% → temp_stress=1.25, humidity_stress=1.16
        result = calc_wlei(100.0, 30.0, 80.0)
        assert result > 100.0

    def test_pure_function_cold(self):
        from src.metrics.wlei import calc_wlei
        # 0°C → temp_stress=1.075
        result = calc_wlei(100.0, 0.0, 60.0)
        assert result > 100.0

    def test_saves_to_db(self, conn):
        from src.metrics.wlei import calc_and_save_wlei
        conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, activity_type)
               VALUES ('garmin', 'w1', '2026-03-20T08:00:00', 'run')"""
        )
        conn.commit()
        act_id = conn.execute("SELECT id FROM activity_summaries WHERE source_id='w1'").fetchone()[0]

        # TRIMP 삽입
        conn.execute(
            """INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value)
               VALUES ('2026-03-20', ?, 'TRIMP', 80.0)""",
            (act_id,),
        )
        # 날씨 삽입
        conn.execute(
            """INSERT INTO activity_detail_metrics (activity_id, metric_name, metric_value)
               VALUES (?, 'weather_temp_c', 25.0), (?, 'weather_humidity_pct', 70.0)""",
            (act_id, act_id),
        )
        conn.commit()

        wlei = calc_and_save_wlei(conn, act_id)
        assert wlei is not None
        assert wlei > 80.0  # 더운 날씨로 증폭

        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name='WLEI'"
        ).fetchone()
        assert row is not None

    def test_no_trimp_returns_none(self, conn):
        from src.metrics.wlei import calc_and_save_wlei
        conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time)
               VALUES ('garmin', 'w2', '2026-03-20T08:00:00')"""
        )
        conn.commit()
        act_id = conn.execute("SELECT id FROM activity_summaries WHERE source_id='w2'").fetchone()[0]
        result = calc_and_save_wlei(conn, act_id)
        assert result is None


# ---------------------------------------------------------------------------
# TPDI
# ---------------------------------------------------------------------------

class TestTPDI:
    def test_pure_function(self):
        from src.metrics.tpdi import calc_tpdi
        # 실외 300초/km, 실내 270초/km → 실내가 더 빠름 → 음수
        result = calc_tpdi(300.0, 270.0)
        assert result > 0  # 300-270=30, 30/300*100=10%

    def test_zero_outdoor_returns_zero(self):
        from src.metrics.tpdi import calc_tpdi
        assert calc_tpdi(0.0, 270.0) == 0.0

    def test_saves_to_db(self, conn):
        from src.metrics.tpdi import calc_and_save_tpdi
        from datetime import datetime

        # 실외 활동 2개
        for i, (src_id, start) in enumerate([
            ("o1", "2026-02-01T08:00:00"),
            ("o2", "2026-02-15T08:00:00"),
        ]):
            conn.execute(
                """INSERT INTO activity_summaries
                   (source, source_id, start_time, activity_type, trainer)
                   VALUES ('garmin', ?, ?, 'run', 0)""",
                (src_id, start),
            )
        # 실내 활동 2개
        for src_id, start in [("i1", "2026-02-05T08:00:00"), ("i2", "2026-02-20T08:00:00")]:
            conn.execute(
                """INSERT INTO activity_summaries
                   (source, source_id, start_time, activity_type, trainer)
                   VALUES ('garmin', ?, ?, 'treadmill', 1)""",
                (src_id, start),
            )
        conn.commit()

        # FEARP 삽입 (실외: 300, 실내: 330)
        for src_id, fearp_val in [("o1", 300.0), ("o2", 310.0), ("i1", 330.0), ("i2", 340.0)]:
            act_id = conn.execute(
                "SELECT id FROM activity_summaries WHERE source_id=?", (src_id,)
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value)
                   VALUES ('2026-02-01', ?, 'FEARP', ?)""",
                (act_id, fearp_val),
            )
        conn.commit()

        tpdi = calc_and_save_tpdi(conn, "2026-03-20", weeks=8)
        assert tpdi is not None
        # 실외 avg=305, 실내 avg=335 → (305-335)/305*100 < 0 (실내가 더 느림)
        assert tpdi < 0

    def test_insufficient_data_returns_none(self, conn):
        from src.metrics.tpdi import calc_and_save_tpdi
        result = calc_and_save_tpdi(conn, "2026-03-20")
        assert result is None
