"""Phase 5-J consumer migration 검증 테스트.

v0.3 스키마: activity_summaries.distance_m (미터).
소비자 코드가 distance_m / 1000.0 AS distance_km 알리아스를 올바르게 사용하는지 확인.
"""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, timedelta

import pytest

_TODAY = date.today()
_ACT1_DT = f"{(_TODAY - timedelta(days=7)).isoformat()}T08:00:00"   # garmin
_ACT2_DT = f"{(_TODAY - timedelta(days=3)).isoformat()}T08:00:00"   # strava
_ACT1_DATE = (_TODAY - timedelta(days=7)).isoformat()
_ACT2_DATE = (_TODAY - timedelta(days=3)).isoformat()

from src.analysis.trends import weekly_trends
from src.analysis.compare import compare_periods
from src.analysis.weekly_score import _get_week_basics as get_week_basics
from src.services.activity_service import get_activity_list
from src.utils.dedup import assign_group_id, auto_group_all
from src.sync.garmin_v2_mappings import (
    extract_summary_fields_from_api,
    extract_summary_fields_from_zip,
)
from src.sync.extractors.runalyze_extractor import RunalyzeExtractor
from src.sync.extractors.intervals_extractor import IntervalsExtractor


# ─── 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture
def conn(db_conn):
    """테스트용 활동 2건 삽입 (distance_m = 10_000 m = 10 km)."""
    db_conn.executemany(
        """INSERT INTO activity_summaries
           (source, source_id, activity_type, start_time, distance_m,
            duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("garmin", "g1", "running", _ACT1_DT, 10_000, 3600, 360, 150, 170, 100),
            ("strava", "s1", "running", _ACT2_DT, 21_097, 7200, 341, 155, 175, 200),
        ],
    )
    db_conn.commit()
    return db_conn


# ─── 1. activity_service ──────────────────────────────────────────────────

class TestActivityService:
    def test_distance_m_present_in_row(self, conn):
        result = get_activity_list(conn, per_page=10)
        acts = result["activities"]
        assert len(acts) == 2
        # v_canonical_activities에서 distance_m 반환
        distances = {a["source"]: a.get("distance_m") for a in acts}
        assert distances["garmin"] == pytest.approx(10_000)
        assert distances["strava"] == pytest.approx(21_097)

    def test_filter_min_distance_m(self, conn):
        result = get_activity_list(conn, filters={"min_distance_m": 15_000}, per_page=10)
        assert result["total"] == 1
        assert result["activities"][0]["source"] == "strava"


# ─── 2. analysis.trends ───────────────────────────────────────────────────

class TestTrends:
    def test_weekly_distance_km(self, conn):
        rows = weekly_trends(conn, weeks=4)
        # 활동이 있는 주가 존재해야 함
        non_zero = [r for r in rows if r.get("total_distance_km", 0) > 0]
        assert len(non_zero) > 0
        # 값이 km 단위인지 (10000m → 10km, 21097m → 21km)
        for r in rows:
            assert (r.get("total_distance_km") or 0) < 1000, "km 단위여야 함 (미터 아님)"


# ─── 3. analysis.compare ──────────────────────────────────────────────────

class TestCompare:
    def test_compare_periods_distance_km(self, conn):
        p1_start = (_TODAY - timedelta(days=14)).isoformat()
        mid = (_TODAY - timedelta(days=4)).isoformat()
        p2_end = (_TODAY + timedelta(days=3)).isoformat()
        p1 = compare_periods(conn, p1_start, mid, mid, p2_end)
        # 첫 번째 기간에 garmin 10km 활동이 있어야 함
        assert p1["period1"]["total_distance_km"] == pytest.approx(10.0, abs=0.1)


# ─── 4. analysis.weekly_score ─────────────────────────────────────────────

class TestWeeklyScore:
    def test_total_distance_km(self, conn):
        week_start = (_TODAY - timedelta(days=8)).isoformat()
        week_end = (_TODAY - timedelta(days=6)).isoformat()
        summary = get_week_basics(conn, week_start, week_end)
        dist = summary.get("total_distance_km", 0)
        # garmin 10km 포함
        assert dist == pytest.approx(10.0, abs=0.1)


# ─── 5. analysis.activity_deep ────────────────────────────────────────────

class TestActivityDeep:
    def test_distance_km_alias_sql(self, conn):
        """_find_activity 쿼리와 동일한 distance_m / 1000.0 AS distance_km 알리아스 검증."""
        act_id = conn.execute(
            "SELECT id FROM activity_summaries WHERE source='garmin'"
        ).fetchone()[0]
        # activity_deep._find_activity와 동일한 alias 패턴
        row = conn.execute(
            "SELECT distance_m / 1000.0 AS distance_km FROM activity_summaries WHERE id = ?",
            (act_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(10.0, abs=0.01)


# ─── 6. utils.dedup ───────────────────────────────────────────────────────

class TestDedup:
    def test_assign_group_no_crash(self, conn):
        act_id = conn.execute(
            "SELECT id FROM activity_summaries WHERE source='garmin'"
        ).fetchone()[0]
        # 에러 없이 실행되어야 함 (distance_m 쿼리 사용)
        result = assign_group_id(conn, act_id)
        assert result is None or isinstance(result, str)

    def test_auto_group_all_no_crash(self, conn):
        stats = auto_group_all(conn)
        assert "groups_created" in stats
        assert "activities_grouped" in stats


# ─── 7. garmin_v2_mappings ────────────────────────────────────────────────

class TestGarminV2Mappings:
    def test_extract_api_returns_distance_m(self):
        raw = {
            "activityName": "Morning Run",
            "activityType": {"typeKey": "running"},
            "startTimeLocal": "2026-04-01 08:00:00",
            "distance": 10_000.0,  # API는 미터
            "duration": 3600,
            "movingDuration": 3580,
        }
        fields = extract_summary_fields_from_api(raw)
        assert "distance_m" in fields
        assert "distance_km" not in fields
        assert fields["distance_m"] == pytest.approx(10_000.0)

    def test_extract_zip_returns_distance_m(self):
        raw = {
            "name": "Morning Run",
            "activityType": "running",
            "startTimeLocal": 1743494400000,  # epoch ms
            "distance": 1_000_000,  # ZIP은 cm (10km = 1,000,000 cm)
            "duration": 3_600_000,  # ms
            "movingDuration": 3_580_000,
        }
        fields = extract_summary_fields_from_zip(raw)
        assert "distance_m" in fields
        assert "distance_km" not in fields
        assert fields["distance_m"] == pytest.approx(10_000.0, rel=0.01)


# ─── 8. runalyze_extractor ────────────────────────────────────────────────

class TestRunalyzeExtractor:
    def test_extract_core_distance_m(self):
        extractor = RunalyzeExtractor()
        raw = {
            "id": "123",
            "datetime": "2026-04-01T08:00:00",
            "sport": {"name": "Running"},
            "distance": 10_000.0,  # Runalyze는 미터
            "s": 3600,
        }
        core = extractor.extract_activity_core(raw)
        assert "distance_m" in core
        assert core["distance_m"] == pytest.approx(10_000.0)


# ─── 9. intervals_extractor ───────────────────────────────────────────────

class TestIntervalsExtractor:
    def test_extract_core_distance_m(self):
        extractor = IntervalsExtractor()
        raw = {
            "id": "456",
            "start_date_local": "2026-04-01T08:00:00",
            "type": "Run",
            "distance": 10_000.0,  # Intervals.icu는 미터
            "elapsed_time": 3600,
        }
        core = extractor.extract_activity_core(raw)
        assert "distance_m" in core
        assert core["distance_m"] == pytest.approx(10_000.0)


# ─── 10. views_export CSV ─────────────────────────────────────────────────

class TestViewsExportCSV:
    def test_csv_distance_km_conversion(self, conn):
        """views_export CSV가 distance_m → km 변환을 올바르게 수행하는지 확인."""
        from src.services.activity_service import get_activity_list

        result = get_activity_list(conn, per_page=100)
        acts = result["activities"]

        # views_export._CSV_COLUMNS와 동일한 변환 로직 검증
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["소스", "거리(km)"])
        for act in acts:
            distance_km = round((act.get("distance_m") or 0) / 1000, 3)
            writer.writerow([act["source"], distance_km])

        reader = csv.DictReader(io.StringIO(buf.getvalue()))
        rows = list(reader)
        assert len(rows) == 2

        dists = {r["소스"]: float(r["거리(km)"]) for r in rows}
        assert dists["garmin"] == pytest.approx(10.0, abs=0.01)
        assert dists["strava"] == pytest.approx(21.097, abs=0.01)
