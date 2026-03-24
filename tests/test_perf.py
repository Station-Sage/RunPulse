"""성능 개선 관련 테스트 (PERF-1~4).

- PERF-1: db_setup — 인덱스 존재 + v_canonical_activities LEFT JOIN 패턴
- PERF-2: unified_activities — DB 레벨 페이지네이션
- PERF-3: app — TTL 캐시 (_get_home_data)
- PERF-4: sync — 병렬 동기화 (_sync_source 독립 실행)
"""
from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest


# ── 공통 픽스처 ────────────────────────────────────────────────────────────
@pytest.fixture
def mem_conn():
    """인메모리 SQLite 커넥션 (테이블 포함)."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT,
            activity_type TEXT DEFAULT 'running',
            start_time TEXT NOT NULL,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            calories INTEGER,
            description TEXT,
            matched_group_id TEXT,
            workout_label TEXT,
            avg_power REAL,
            event_type TEXT,
            workout_type TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_activity_detail_metrics_activity_source
            ON activity_summaries(id, source);
        CREATE INDEX IF NOT EXISTS idx_activity_summaries_group_time
            ON activity_summaries(matched_group_id, start_time DESC);

        CREATE VIEW IF NOT EXISTS v_canonical_activities AS
        SELECT a.*
        FROM activity_summaries a
        LEFT JOIN activity_summaries b
            ON  b.matched_group_id = a.matched_group_id
            AND b.matched_group_id IS NOT NULL
            AND (
                CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                              WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                < CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                OR (
                    CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                  WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    = CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                    WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    AND b.id < a.id
                )
            )
        WHERE b.id IS NULL;
    """)
    yield conn
    conn.close()


# ── PERF-1: db_setup 인덱스 + 뷰 ──────────────────────────────────────────

class TestDbSetupPerf:
    def test_create_tables_includes_composite_indexes(self, tmp_path):
        """create_tables()가 복합 인덱스 2개를 생성한다."""
        from src.db_setup import create_tables
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        create_tables(conn)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_activity_detail_metrics_activity_source" in indexes
        assert "idx_activity_summaries_group_time" in indexes
        conn.close()

    def test_v_canonical_activities_deduplicates_by_priority(self, mem_conn):
        """v_canonical_activities: 같은 그룹에서 Garmin 우선 1행만 반환."""
        gid = "grp-001"
        mem_conn.executemany(
            "INSERT INTO activity_summaries(source, source_id, start_time, matched_group_id)"
            " VALUES (?,?,?,?)",
            [
                ("garmin", "g1", "2026-01-01T07:00:00", gid),
                ("strava", "s1", "2026-01-01T07:01:00", gid),
                ("intervals", "i1", "2026-01-01T07:02:00", gid),
            ],
        )
        rows = mem_conn.execute(
            "SELECT source FROM v_canonical_activities WHERE matched_group_id = ?", (gid,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "garmin"

    def test_v_canonical_activities_solo_activity_included(self, mem_conn):
        """v_canonical_activities: 그룹 없는 단독 활동도 포함."""
        mem_conn.execute(
            "INSERT INTO activity_summaries(source, source_id, start_time)"
            " VALUES ('strava', 'solo1', '2026-01-02T08:00:00')"
        )
        rows = mem_conn.execute(
            "SELECT id FROM v_canonical_activities WHERE matched_group_id IS NULL"
        ).fetchall()
        assert len(rows) == 1

    def test_migrate_db_adds_indexes_to_existing_db(self, tmp_path):
        """migrate_db()가 기존 DB에 복합 인덱스를 추가한다."""
        from src.db_setup import create_tables, migrate_db
        db_file = tmp_path / "old.db"
        conn = sqlite3.connect(str(db_file))
        create_tables(conn)
        # 인덱스 드롭 후 migrate로 복원 확인
        conn.execute("DROP INDEX IF EXISTS idx_activity_detail_metrics_activity_source")
        conn.commit()
        migrate_db(conn)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_activity_detail_metrics_activity_source" in indexes
        conn.close()


# ── PERF-2: unified_activities DB 페이지네이션 ────────────────────────────

class TestUnifiedActivitiesPagination:
    def _populate(self, conn, n: int = 25, group: bool = True):
        """n개 단독 활동 + 옵션으로 3소스 그룹 1개 삽입."""
        rows = [
            ("garmin", f"g{i}", f"2026-01-{i+1:02d}T07:00:00", None, float(i + 1), 3600)
            for i in range(n)
        ]
        conn.executemany(
            "INSERT INTO activity_summaries(source, source_id, start_time, matched_group_id, distance_km, duration_sec)"
            " VALUES (?,?,?,?,?,?)",
            rows,
        )
        if group:
            gid = "test-group-uuid"
            conn.executemany(
                "INSERT INTO activity_summaries(source, source_id, start_time, matched_group_id, distance_km)"
                " VALUES (?,?,?,?,?)",
                [
                    ("garmin", "gg1", "2025-12-01T07:00:00", gid, 10.0),
                    ("strava", "ss1", "2025-12-01T07:01:00", gid, 10.1),
                    ("intervals", "ii1", "2025-12-01T07:02:00", gid, 9.9),
                ],
            )

    def test_total_count_correct(self, mem_conn):
        """총 그룹 수 = 단독 25 + 그룹 1 = 26."""
        from src.services.unified_activities import fetch_unified_activities
        self._populate(mem_conn)
        _, total, _ = fetch_unified_activities(mem_conn, page=1, page_size=20)
        assert total == 26

    def test_pagination_page1_and_page2(self, mem_conn):
        """페이지1 = 20개, 페이지2 = 6개."""
        from src.services.unified_activities import fetch_unified_activities
        self._populate(mem_conn)
        acts1, _, _ = fetch_unified_activities(mem_conn, page=1, page_size=20)
        acts2, _, _ = fetch_unified_activities(mem_conn, page=2, page_size=20)
        assert len(acts1) == 20
        assert len(acts2) == 6

    def test_group_merges_into_one_activity(self, mem_conn):
        """3소스 그룹 → 1개 UnifiedActivity, available_sources 3개."""
        from src.services.unified_activities import fetch_unified_activities
        self._populate(mem_conn)
        # 최근 활동 기준 마지막 페이지에 그룹이 있음 (오래된 날짜)
        acts, total, _ = fetch_unified_activities(mem_conn, page=2, page_size=20)
        group_acts = [a for a in acts if a.is_real_group]
        assert len(group_acts) == 1
        assert len(group_acts[0].available_sources) == 3

    def test_stats_returns_total_dist(self, mem_conn):
        """stats에 total_dist_km이 포함된다."""
        from src.services.unified_activities import fetch_unified_activities
        self._populate(mem_conn, n=5, group=False)
        _, _, stats = fetch_unified_activities(mem_conn, page=1, page_size=10)
        assert stats["total_dist_km"] > 0
        assert stats["total_count"] == 5

    def test_sort_asc(self, mem_conn):
        """오름차순 정렬 시 첫 활동이 가장 오래됨."""
        from src.services.unified_activities import fetch_unified_activities
        self._populate(mem_conn, n=5, group=False)
        acts, _, _ = fetch_unified_activities(
            mem_conn, page=1, page_size=5, sort_by="date", sort_dir="asc"
        )
        dates = [a.start_time.value for a in acts]
        assert dates == sorted(dates)

    def test_empty_page_returns_empty_list(self, mem_conn):
        """데이터 없으면 빈 리스트 반환."""
        from src.services.unified_activities import fetch_unified_activities
        acts, total, _ = fetch_unified_activities(mem_conn, page=1, page_size=20)
        assert acts == []
        assert total == 0


# ── PERF-3: TTL 캐시 ──────────────────────────────────────────────────────

class TestHomeDataCache:
    def test_cache_returns_same_object_within_ttl(self, tmp_path):
        """TTL 내 두 번 호출 시 동일 객체 반환 (재계산 없음)."""
        import src.web.app as app_module

        db_file = tmp_path / "running.db"
        fake_data = {"recovery": {}, "weekly": None, "recent_rows": []}
        cache_key = str(db_file)

        # 캐시 초기화 후 TTL 이내 항목 주입
        app_module._home_cache.clear()
        app_module._home_cache[cache_key] = {
            "ts": time.monotonic(),
            "data": fake_data,
        }

        result = app_module._get_home_data(db_file)
        assert result is fake_data  # 동일 객체 (재계산 안 함)

    def test_cache_recomputes_after_ttl(self, tmp_path, monkeypatch):
        """TTL 경과 후 재계산한다."""
        import src.web.app as app_module

        app_module._home_cache.clear()

        db_file = tmp_path / "running.db"
        conn = sqlite3.connect(str(db_file))
        from src.db_setup import create_tables
        create_tables(conn)
        conn.close()

        call_count = {"n": 0}

        def fake_recovery(conn, today):
            call_count["n"] += 1
            return {"available": False}

        monkeypatch.setattr("src.analysis.recovery.get_recovery_status", fake_recovery)
        monkeypatch.setattr(
            "src.analysis.weekly_score.calculate_weekly_score", lambda conn: None
        )
        monkeypatch.setattr(
            "src.services.unified_activities.fetch_unified_activities",
            lambda *a, **kw: ([], 0, {}),
        )

        # 만료된 캐시 주입
        cache_key = str(db_file)
        app_module._home_cache[cache_key] = {
            "ts": time.monotonic() - app_module._HOME_CACHE_TTL - 1,
            "data": {"recovery": {}, "weekly": None, "recent_rows": []},
        }

        app_module._get_home_data(db_file)
        assert call_count["n"] == 1  # 재계산 발생


# ── PERF-4: 병렬 sync ─────────────────────────────────────────────────────

class TestParallelSync:
    def test_sync_source_returns_counts(self, tmp_path):
        """_sync_source가 activities/wellness 카운트를 반환한다."""
        from src.sync import _sync_source

        db_file = tmp_path / "running.db"
        conn = sqlite3.connect(str(db_file))
        from src.db_setup import create_tables
        create_tables(conn)
        conn.close()

        config = {}
        fake_act = MagicMock(return_value=3)
        fake_well = MagicMock(return_value=1)

        with patch.dict("src.sync.SOURCES", {"garmin": (fake_act, fake_well)}):
            result = _sync_source("garmin", config, db_file, 7)

        assert result["activities"] == 3
        assert result["wellness"] == 1
        assert result["errors"] == []

    def test_sync_source_captures_errors(self, tmp_path):
        """동기화 함수 예외 발생 시 errors 리스트에 기록, 프로세스 계속."""
        from src.sync import _sync_source

        db_file = tmp_path / "running.db"
        conn = sqlite3.connect(str(db_file))
        from src.db_setup import create_tables
        create_tables(conn)
        conn.close()

        fake_act = MagicMock(side_effect=RuntimeError("연결 실패"))

        with patch.dict("src.sync.SOURCES", {"strava": (fake_act, None)}):
            result = _sync_source("strava", {}, db_file, 7)

        assert result["activities"] == 0
        assert len(result["errors"]) == 1
        assert "연결 실패" in result["errors"][0]

    def test_multiple_sources_run_independently(self, tmp_path):
        """복수 소스가 독립적으로 실행된다 (각각 자신의 카운트 반환)."""
        from src.sync import _sync_source

        db_file = tmp_path / "running.db"
        conn = sqlite3.connect(str(db_file))
        from src.db_setup import create_tables
        create_tables(conn)
        conn.close()

        results = {}
        for source, ret in [("garmin", 5), ("strava", 2), ("intervals", 3), ("runalyze", 1)]:
            fake_act = MagicMock(return_value=ret)
            with patch.dict("src.sync.SOURCES", {source: (fake_act, None)}):
                results[source] = _sync_source(source, {}, db_file, 7)

        assert results["garmin"]["activities"] == 5
        assert results["strava"]["activities"] == 2
        assert results["intervals"]["activities"] == 3
        assert results["runalyze"]["activities"] == 1
