"""tests/test_milestone_service.py — milestone_service 단위 테스트.

임시 DB(conftest db_conn 픽스처) 기반. 실 사용자 DB 접근 없음.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services.milestone_service import detect_and_store_milestones, get_recent_milestones
from src.utils.db_helpers import upsert_metric


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _make_conn(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    migrate_db(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _insert_activity(conn, *, source="garmin", source_id, start_time, distance_m,
                     avg_pace_sec_km=300, elapsed_time_sec=None, name="run"):
    cur = conn.execute(
        """
        INSERT INTO activity_summaries
            (source, source_id, name, start_time, distance_m,
             avg_pace_sec_km, elapsed_time_sec, activity_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'running')
        """,
        (source, source_id, name, start_time, distance_m, avg_pace_sec_km, elapsed_time_sec),
    )
    return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# distance_threshold 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestDistanceThreshold:
    def test_100km_created_on_crossing(self, tmp_path):
        """100km 문턱을 넘는 활동 날짜로 마일스톤 생성."""
        conn = _make_conn(tmp_path)
        # 90km 먼저 쌓기
        _insert_activity(conn, source_id="a1", start_time="2026-01-01 08:00:00",
                         distance_m=90000)
        conn.commit()

        # 15km 추가 → 총 105km → 100km 돌파
        _insert_activity(conn, source_id="a2", start_time="2026-01-10 08:00:00",
                         distance_m=15000)
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-01-10", "2026-01-10")
        conn.commit()

        assert len(result) == 1
        m = result[0]
        assert m["type"] == "distance_threshold"
        assert m["title"] == "누적 100km 돌파"
        assert m["date"] == "2026-01-10"

    def test_multiple_thresholds_crossed(self, tmp_path):
        """한 활동에서 200km·300km 두 배수를 동시에 넘으면 2개 생성."""
        conn = _make_conn(tmp_path)
        _insert_activity(conn, source_id="a1", start_time="2026-01-01 08:00:00",
                         distance_m=190000)
        conn.commit()

        _insert_activity(conn, source_id="a2", start_time="2026-01-10 08:00:00",
                         distance_m=120000)  # 190+120 = 310km → 200·300 돌파
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-01-10", "2026-01-10")
        conn.commit()

        titles = {m["title"] for m in result}
        assert "누적 200km 돌파" in titles
        assert "누적 300km 돌파" in titles

    def test_no_duplicate_on_second_call(self, tmp_path):
        """같은 범위로 두 번 호출해도 중복 삽입 안 됨 (INSERT OR IGNORE)."""
        conn = _make_conn(tmp_path)
        _insert_activity(conn, source_id="a1", start_time="2026-01-01 08:00:00",
                         distance_m=90000)
        _insert_activity(conn, source_id="a2", start_time="2026-01-10 08:00:00",
                         distance_m=15000)
        conn.commit()

        detect_and_store_milestones(conn, "2026-01-10", "2026-01-10")
        conn.commit()
        second = detect_and_store_milestones(conn, "2026-01-10", "2026-01-10")
        conn.commit()

        assert second == []  # 두 번째엔 신규 삽입 없음
        rows = conn.execute("SELECT COUNT(*) FROM milestones").fetchone()[0]
        assert rows == 1  # 딱 1개만


# ─────────────────────────────────────────────────────────────────────────────
# PB 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestPB:
    def _make_race(self, conn, source_id, start_time, distance_m, pace, elapsed=None, name="Race"):
        return _insert_activity(conn, source_id=source_id, start_time=start_time,
                                distance_m=distance_m, avg_pace_sec_km=pace,
                                elapsed_time_sec=elapsed, name=name)

    def test_pb_created_when_faster(self, tmp_path):
        """이전 기록보다 빠른 레이스 → PB 생성."""
        conn = _make_conn(tmp_path)
        # 과거 10K: 6분/km (360 s/km)
        self._make_race(conn, "old", "2026-01-01 08:00:00", 10000, 360)
        conn.commit()

        # 오늘 10K: 5분30초/km (330 s/km) — 더 빠름
        self._make_race(conn, "new", "2026-06-01 08:00:00", 10000, 330,
                        elapsed=3300, name="10K Race")
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()

        assert any(m["title"] == "10K PB" for m in result)

    def test_no_pb_when_slower(self, tmp_path):
        """이전 기록보다 느리면 PB 미생성."""
        conn = _make_conn(tmp_path)
        self._make_race(conn, "old", "2026-01-01 08:00:00", 10000, 300)
        conn.commit()

        self._make_race(conn, "new", "2026-06-01 08:00:00", 10000, 350,
                        name="10K Race slow")
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()

        assert not any(m["title"] == "10K PB" for m in result)

    def test_no_pb_for_first_race(self, tmp_path):
        """이전 기록이 없으면(첫 완주) PB로 치지 않음."""
        conn = _make_conn(tmp_path)
        self._make_race(conn, "first", "2026-06-01 08:00:00", 10000, 330,
                        name="First 10K Race")
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()

        assert result == []

    def test_pb_no_duplicate(self, tmp_path):
        """같은 범위로 두 번 호출해도 PB 중복 삽입 안 됨."""
        conn = _make_conn(tmp_path)
        self._make_race(conn, "old", "2026-01-01 08:00:00", 10000, 360)
        self._make_race(conn, "new", "2026-06-01 08:00:00", 10000, 330, name="10K Race")
        conn.commit()

        detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()
        second = detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()

        assert second == []

    def test_pb_race_keyword_detection(self, tmp_path):
        """'대회' 키워드 이름 활동도 레이스로 인식."""
        conn = _make_conn(tmp_path)
        self._make_race(conn, "old", "2026-01-01 08:00:00", 10000, 360, name="대회")
        self._make_race(conn, "new", "2026-06-01 08:00:00", 10000, 300, name="여름 대회")
        conn.commit()

        result = detect_and_store_milestones(conn, "2026-06-01", "2026-06-01")
        conn.commit()
        assert any(m["title"] == "10K PB" for m in result)


# ─────────────────────────────────────────────────────────────────────────────
# metric_recompute 테스트 (upsert_metric 연동)
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricRecompute:
    def test_recompute_milestone_created_on_version_change(self, tmp_path):
        """allow-list 메트릭의 algorithm_version이 바뀌면 metric_recompute 마일스톤 생성."""
        conn = _make_conn(tmp_path)
        upsert_metric(conn, "daily", "2026-01-01", "ctl", "runpulse:formula_v1",
                      numeric_value=70.0, algorithm_version="1.0")
        conn.commit()

        upsert_metric(conn, "daily", "2026-01-01", "ctl", "runpulse:formula_v1",
                      numeric_value=72.0, algorithm_version="2.0")
        conn.commit()

        row = conn.execute(
            "SELECT * FROM milestones WHERE type='metric_recompute' AND metric_name='ctl'"
        ).fetchone()
        assert row is not None
        assert dict(row)["old_value"] == pytest.approx(70.0)
        assert dict(row)["new_value"] == pytest.approx(72.0)

    def test_no_recompute_same_version(self, tmp_path):
        """같은 algorithm_version이면 마일스톤 안 생성."""
        conn = _make_conn(tmp_path)
        upsert_metric(conn, "daily", "2026-01-01", "ctl", "runpulse:formula_v1",
                      numeric_value=70.0, algorithm_version="1.0")
        upsert_metric(conn, "daily", "2026-01-01", "ctl", "runpulse:formula_v1",
                      numeric_value=70.5, algorithm_version="1.0")
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM milestones WHERE type='metric_recompute'").fetchone()[0]
        assert count == 0

    def test_no_recompute_for_non_allowlist_metric(self, tmp_path):
        """allow-list 밖 메트릭은 version이 바뀌어도 마일스톤 안 생성."""
        conn = _make_conn(tmp_path)
        upsert_metric(conn, "daily", "2026-01-01", "atl", "runpulse:formula_v1",
                      numeric_value=80.0, algorithm_version="1.0")
        upsert_metric(conn, "daily", "2026-01-01", "atl", "runpulse:formula_v1",
                      numeric_value=85.0, algorithm_version="2.0")
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM milestones WHERE type='metric_recompute'").fetchone()[0]
        assert count == 0


# ─────────────────────────────────────────────────────────────────────────────
# get_recent_milestones 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestGetRecentMilestones:
    def test_returns_empty_when_no_milestones(self, tmp_path):
        conn = _make_conn(tmp_path)
        result = get_recent_milestones(conn)
        assert result == []

    def test_returns_ordered_by_date_desc(self, tmp_path):
        conn = _make_conn(tmp_path)
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-01-01', 'A')"
        )
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-06-01', 'B')"
        )
        conn.commit()

        result = get_recent_milestones(conn)
        assert result[0]["date"] == "2026-06-01"
        assert result[1]["date"] == "2026-01-01"

    def test_limit_respected(self, tmp_path):
        conn = _make_conn(tmp_path)
        for i in range(5):
            conn.execute(
                "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-01-01', ?)",
                (f"M{i}",),
            )
        conn.commit()

        result = get_recent_milestones(conn, limit=3)
        assert len(result) == 3

    def test_date_range_filters(self, tmp_path):
        conn = _make_conn(tmp_path)
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-01-01', 'Jan')"
        )
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-06-01', 'Jun')"
        )
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-12-01', 'Dec')"
        )
        conn.commit()

        result = get_recent_milestones(conn, date_from="2026-02-01", date_to="2026-11-01")
        titles = [r["title"] for r in result]
        assert titles == ["Jun"]

    def test_no_date_range_returns_all(self, tmp_path):
        """date_from/date_to 둘 다 없으면 기존과 동일하게 전체 기간."""
        conn = _make_conn(tmp_path)
        conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('pb', '2026-01-01', 'Jan')"
        )
        conn.commit()

        result = get_recent_milestones(conn)
        assert len(result) == 1
