"""unified_activities 서비스 테스트."""
from __future__ import annotations

import sqlite3
import pytest

from src.services.unified_activities import (
    UnifiedField,
    UnifiedActivity,
    _pick_value,
    build_unified_activity,
    build_source_comparison,
    fetch_unified_activities,
    assign_group_to_activities,
    remove_from_group,
    SERVICE_PRIORITY,
)


# ── 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture
def mem_db():
    """인메모리 SQLite DB (activity_summaries 스키마)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT,
            activity_type TEXT,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr REAL,
            max_hr REAL,
            avg_cadence REAL,
            elevation_gain REAL,
            calories REAL,
            description TEXT,
            matched_group_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    return conn


def _insert(conn, source, distance_km=10.0, matched_group_id=None, **kwargs):
    vals = {
        "source": source,
        "source_id": f"{source}-1",
        "activity_type": "run",
        "start_time": "2026-01-15T08:00:00",
        "distance_km": distance_km,
        "duration_sec": 3600,
        "avg_pace_sec_km": 360,
        "avg_hr": 150.0,
        "max_hr": 175.0,
        "avg_cadence": 170.0,
        "elevation_gain": 50.0,
        "calories": 600.0,
        "description": "test",
        "matched_group_id": matched_group_id,
        **kwargs,
    }
    cursor = conn.execute(
        """INSERT INTO activity_summaries
           (source, source_id, activity_type, start_time, distance_km, duration_sec,
            avg_pace_sec_km, avg_hr, max_hr, avg_cadence, elevation_gain, calories,
            description, matched_group_id)
           VALUES (:source, :source_id, :activity_type, :start_time, :distance_km,
                   :duration_sec, :avg_pace_sec_km, :avg_hr, :max_hr, :avg_cadence,
                   :elevation_gain, :calories, :description, :matched_group_id)""",
        vals,
    )
    return cursor.lastrowid


# ── _pick_value ───────────────────────────────────────────────────────────

class TestPickValue:
    def test_garmin_first(self):
        source_rows = {
            "strava": {"distance_km": 10.0},
            "garmin": {"distance_km": 10.5},
        }
        result = _pick_value(source_rows, "distance_km")
        assert result.value == 10.5
        assert result.source == "garmin"

    def test_fallback_when_garmin_missing(self):
        source_rows = {
            "strava": {"distance_km": 10.1},
            "intervals": {"distance_km": 10.2},
        }
        result = _pick_value(source_rows, "distance_km")
        assert result.source == "strava"
        assert result.value == 10.1

    def test_none_when_all_missing(self):
        source_rows = {"garmin": {"distance_km": None}, "strava": {}}
        result = _pick_value(source_rows, "distance_km")
        assert result.value is None
        assert result.source is None

    def test_all_values_populated(self):
        source_rows = {
            "garmin": {"distance_km": 10.0},
            "strava": {"distance_km": 9.9},
        }
        result = _pick_value(source_rows, "distance_km")
        assert result.all_values == {"garmin": 10.0, "strava": 9.9}

    def test_service_priority_order(self):
        # 모든 4소스가 있을 때 garmin 우선
        source_rows = {s: {"distance_km": float(i)} for i, s in enumerate(SERVICE_PRIORITY)}
        result = _pick_value(source_rows, "distance_km")
        assert result.source == "garmin"


# ── build_unified_activity ────────────────────────────────────────────────

class TestBuildUnifiedActivity:
    def _make_row(self, source, rid=1, gid=None):
        return {
            "id": rid, "source": source, "source_id": f"{source}-1",
            "activity_type": "run", "start_time": "2026-01-15T08:00:00",
            "distance_km": 10.0, "duration_sec": 3600, "avg_pace_sec_km": 360,
            "avg_hr": 150.0, "max_hr": 175.0, "avg_cadence": 170.0,
            "elevation_gain": 50.0, "calories": 600.0, "description": "test",
            "matched_group_id": gid,
        }

    def test_single_source(self):
        row = self._make_row("garmin", rid=1)
        ua = build_unified_activity(None, [row])
        assert ua.is_real_group is False
        assert ua.available_sources == ["garmin"]
        assert ua.can_expand is False

    def test_multi_source_group(self):
        rows = [
            self._make_row("garmin", rid=1, gid="uuid-1"),
            self._make_row("strava", rid=2, gid="uuid-1"),
        ]
        ua = build_unified_activity("uuid-1", rows)
        assert ua.is_real_group is True
        assert ua.can_expand is True
        assert ua.representative_id == 1  # garmin is representative

    def test_representative_id_garmin_first(self):
        rows = [
            self._make_row("strava", rid=2, gid="uuid-1"),
            self._make_row("garmin", rid=5, gid="uuid-1"),
        ]
        ua = build_unified_activity("uuid-1", rows)
        assert ua.representative_id == 5

    def test_date_property(self):
        row = self._make_row("garmin", rid=1)
        ua = build_unified_activity(None, [row])
        assert ua.date == "2026-01-15"

    def test_effective_group_id_solo(self):
        row = self._make_row("garmin", rid=7)
        ua = build_unified_activity(None, [row])
        assert ua.effective_group_id == "7"

    def test_effective_group_id_real_group(self):
        rows = [
            self._make_row("garmin", rid=1, gid="my-group"),
            self._make_row("strava", rid=2, gid="my-group"),
        ]
        ua = build_unified_activity("my-group", rows)
        assert ua.effective_group_id == "my-group"


# ── build_source_comparison ───────────────────────────────────────────────

class TestBuildSourceComparison:
    def test_returns_list_of_dicts(self):
        source_rows = {
            "garmin": {"distance_km": 10.0, "avg_hr": 150.0, "duration_sec": 3600,
                       "avg_pace_sec_km": 360, "max_hr": 175.0, "avg_cadence": 170.0,
                       "elevation_gain": 50.0, "avg_power": None, "calories": 600.0},
            "strava": {"distance_km": 9.9, "avg_hr": 148.0, "duration_sec": 3580,
                       "avg_pace_sec_km": 362, "max_hr": 172.0, "avg_cadence": None,
                       "elevation_gain": 48.0, "avg_power": None, "calories": None},
        }
        rows = build_source_comparison(source_rows)
        assert isinstance(rows, list)
        assert len(rows) == 9  # 파워 포함 9 fields

    def test_field_names_present(self):
        source_rows = {"garmin": {}, "strava": {}}
        rows = build_source_comparison(source_rows)
        fields = [r["field"] for r in rows]
        assert "거리(km)" in fields
        assert "평균 심박(bpm)" in fields
        assert "파워(W)" in fields  # 신규

    def test_values_per_source(self):
        source_rows = {
            "garmin": {"distance_km": 10.5},
            "strava": {"distance_km": 10.1},
        }
        rows = build_source_comparison(source_rows)
        dist_row = next(r for r in rows if r["field"] == "거리(km)")
        assert dist_row["garmin"] == 10.5
        assert dist_row["strava"] == 10.1

    def test_missing_source_not_in_row(self):
        source_rows = {"garmin": {"distance_km": 10.0}}
        rows = build_source_comparison(source_rows)
        dist_row = next(r for r in rows if r["field"] == "거리(km)")
        assert "strava" not in dist_row

    def test_unified_value_and_source_present(self):
        source_rows = {
            "garmin": {"distance_km": 10.5},
            "strava": {"distance_km": 10.1},
        }
        rows = build_source_comparison(source_rows)
        dist_row = next(r for r in rows if r["field"] == "거리(km)")
        assert dist_row["unified_value"] == 10.5       # garmin 우선
        assert dist_row["unified_source"] == "garmin"

    def test_unified_source_fallback(self):
        """garmin 없으면 strava → intervals → runalyze 순서."""
        source_rows = {
            "strava": {"distance_km": 10.1},
            "intervals": {"distance_km": 10.2},
        }
        rows = build_source_comparison(source_rows)
        dist_row = next(r for r in rows if r["field"] == "거리(km)")
        assert dist_row["unified_source"] == "strava"

    def test_unified_value_none_when_all_missing(self):
        source_rows = {"garmin": {}, "strava": {}}
        rows = build_source_comparison(source_rows)
        dist_row = next(r for r in rows if r["field"] == "거리(km)")
        assert dist_row["unified_value"] is None
        assert dist_row["unified_source"] is None


# ── fetch_unified_activities ──────────────────────────────────────────────

class TestFetchUnifiedActivities:
    def test_returns_solo_activities(self, mem_db):
        _insert(mem_db, "garmin")
        _insert(mem_db, "strava")
        activities, total, stats = fetch_unified_activities(mem_db)
        assert total == 2
        assert len(activities) == 2

    def test_groups_by_matched_group_id(self, mem_db):
        gid = "test-group-uuid"
        _insert(mem_db, "garmin", matched_group_id=gid)
        _insert(mem_db, "strava", matched_group_id=gid)
        _insert(mem_db, "intervals")
        activities, total, stats = fetch_unified_activities(mem_db)
        assert total == 2  # 1 group + 1 solo

    def test_grouped_activity_has_both_sources(self, mem_db):
        gid = "test-group-uuid"
        _insert(mem_db, "garmin", matched_group_id=gid)
        _insert(mem_db, "strava", matched_group_id=gid)
        activities, total, stats = fetch_unified_activities(mem_db)
        ua = activities[0]
        assert set(ua.available_sources) == {"garmin", "strava"}

    def test_pagination(self, mem_db):
        for i in range(5):
            _insert(mem_db, "garmin", start_time=f"2026-01-{i+1:02d}T08:00:00")
        activities, total, stats = fetch_unified_activities(mem_db, page=1, page_size=3)
        assert total == 5
        assert len(activities) == 3

    def test_stats_total_dist(self, mem_db):
        _insert(mem_db, "garmin", distance_km=10.0)
        _insert(mem_db, "strava", distance_km=8.0)
        _, _, stats = fetch_unified_activities(mem_db)
        assert stats["total_dist_km"] == pytest.approx(18.0)

    def test_date_filter(self, mem_db):
        _insert(mem_db, "garmin", start_time="2026-01-10T08:00:00")
        _insert(mem_db, "garmin", start_time="2026-02-10T08:00:00")
        activities, total, _ = fetch_unified_activities(
            mem_db, date_from="2026-02-01", date_to="2026-02-28"
        )
        assert total == 1

    def test_source_filter(self, mem_db):
        _insert(mem_db, "garmin")
        _insert(mem_db, "strava")
        activities, total, _ = fetch_unified_activities(mem_db, source_filter="garmin")
        assert total == 1
        assert activities[0].available_sources == ["garmin"]


# ── assign_group / remove_from_group ─────────────────────────────────────

class TestGroupOperations:
    def test_assign_creates_group(self, mem_db):
        id1 = _insert(mem_db, "garmin")
        id2 = _insert(mem_db, "strava")
        gid = assign_group_to_activities(mem_db, [id1, id2])
        assert gid  # UUID 문자열
        rows = mem_db.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id IN (?, ?)", (id1, id2)
        ).fetchall()
        assert all(r[0] == gid for r in rows)

    def test_assign_requires_two(self, mem_db):
        id1 = _insert(mem_db, "garmin")
        with pytest.raises(ValueError):
            assign_group_to_activities(mem_db, [id1])

    def test_remove_from_group(self, mem_db):
        gid = "my-group"
        id1 = _insert(mem_db, "garmin", matched_group_id=gid)
        id2 = _insert(mem_db, "strava", matched_group_id=gid)
        remove_from_group(mem_db, id1)
        row = mem_db.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id = ?", (id1,)
        ).fetchone()
        assert row[0] is None
        # id2 는 그대로
        row2 = mem_db.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id = ?", (id2,)
        ).fetchone()
        assert row2[0] == gid
