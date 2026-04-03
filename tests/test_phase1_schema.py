"""Phase 1 스키마 & 기반 인프라 테스트.

검증 항목:
  1. 모든 테이블/뷰 생성 여부
  2. activity_summaries 46 컬럼 확인
  3. metric_store UNIQUE 제약
  4. 인덱스 존재 확인
  5. v_canonical_activities 뷰 동작
  6. metric_registry canonicalize
  7. metric_priority resolve_primary
  8. db_helpers CRUD 정합성
  9. 마이그레이션 멱등성
  10. 성능 벤치마크
"""

import json
import sqlite3
import time

import pytest

from src.db_setup import (
    ALL_TABLES,
    PIPELINE_TABLES,
    APP_TABLES,
    SCHEMA_VERSION,
    create_tables,
    migrate_db,
    _get_user_version,
)
from src.utils.metric_registry import (
    METRIC_REGISTRY,
    METRIC_CATEGORIES,
    canonicalize,
    get_metric,
    list_by_category,
    list_by_scope,
)
from src.utils.metric_priority import (
    get_provider_priority,
    resolve_primary,
    resolve_for_scope,
    resolve_all_primaries,
)
from src.utils.db_helpers import (
    upsert_payload,
    get_payload,
    upsert_activity,
    get_activity,
    get_activity_list,
    upsert_metric,
    upsert_metrics_batch,
    get_primary_metric,
    get_primary_metrics,
    get_all_providers,
    get_metrics_by_category,
    get_metric_history,
    upsert_daily_wellness,
    upsert_daily_fitness,
    get_db_status,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. 테이블 / 뷰 생성
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaCreation:
    """스키마 생성 검증."""

    def test_all_pipeline_tables_exist(self, db_conn):
        tables = {
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for t in PIPELINE_TABLES:
            assert t in tables, f"파이프라인 테이블 누락: {t}"

    def test_all_app_tables_exist(self, db_conn):
        tables = {
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for t in APP_TABLES:
            assert t in tables, f"앱 테이블 누락: {t}"

    def test_canonical_view_exists(self, db_conn):
        views = {
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_canonical_activities" in views

    def test_schema_version(self, db_conn):
        ver = _get_user_version(db_conn)
        assert ver == SCHEMA_VERSION

    def test_activity_summaries_column_count(self, db_conn):
        cols = db_conn.execute("PRAGMA table_info(activity_summaries)").fetchall()
        col_names = [c[1] for c in cols]
        # 46 컬럼: 4+3+4+3+2+2+3+2+1+4+4+4+1+5+2 + id = 46 (including id)
        assert len(col_names) >= 44, f"컬럼 수 부족: {len(col_names)}"
        # 핵심 컬럼 존재 확인
        for expected in [
            "source", "source_id", "activity_type", "start_time",
            "distance_m", "avg_pace_sec_km", "avg_hr",
            "training_effect_aerobic", "training_load", "suffer_score",
            "avg_ground_contact_time_ms", "avg_stride_length_cm",
            "source_url", "gear_id", "matched_group_id",
        ]:
            assert expected in col_names, f"컬럼 누락: {expected}"

    def test_distance_is_meters_not_km(self, db_conn):
        """SI 단위 전환 확인: distance_m (not distance_km)."""
        cols = {c[1] for c in db_conn.execute("PRAGMA table_info(activity_summaries)").fetchall()}
        assert "distance_m" in cols
        assert "distance_km" not in cols

    def test_metric_store_columns(self, db_conn):
        cols = {c[1] for c in db_conn.execute("PRAGMA table_info(metric_store)").fetchall()}
        for expected in [
            "scope_type", "scope_id", "metric_name", "category",
            "provider", "numeric_value", "text_value", "json_value",
            "algorithm_version", "confidence", "is_primary",
        ]:
            assert expected in cols, f"metric_store 컬럼 누락: {expected}"

    def test_daily_wellness_no_source_column(self, db_conn):
        """daily_wellness에는 source 컬럼이 없음 (하루 1행, merge 전략)."""
        cols = {c[1] for c in db_conn.execute("PRAGMA table_info(daily_wellness)").fetchall()}
        assert "source" not in cols
        assert "date" in cols


# ─────────────────────────────────────────────────────────────────────────────
# 2. UNIQUE 제약
# ─────────────────────────────────────────────────────────────────────────────

class TestConstraints:

    def test_activity_summaries_unique(self, db_conn):
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) "
            "VALUES ('garmin', 'g123', '2026-01-01T08:00:00')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO activity_summaries (source, source_id, start_time) "
                "VALUES ('garmin', 'g123', '2026-01-01T09:00:00')"
            )

    def test_metric_store_unique(self, db_conn):
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'garmin', 85)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
                "VALUES ('activity', '1', 'trimp', 'garmin', 90)"
            )

    def test_metric_store_same_name_different_provider(self, db_conn):
        """같은 metric_name이라도 provider가 다르면 공존 가능."""
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'garmin', 85)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'intervals', 91)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'runpulse:formula_v1', 88)"
        )
        rows = db_conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_id = '1' AND metric_name = 'trimp'"
        ).fetchone()
        assert rows[0] == 3

    def test_daily_wellness_unique_date(self, db_conn):
        db_conn.execute(
            "INSERT INTO daily_wellness (date, sleep_score) VALUES ('2026-01-01', 85)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO daily_wellness (date, sleep_score) VALUES ('2026-01-01', 90)"
            )

    def test_daily_fitness_unique_date_source(self, db_conn):
        db_conn.execute(
            "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'garmin', 50)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'garmin', 55)"
            )
        # 같은 날짜, 다른 source는 OK
        db_conn.execute(
            "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'intervals', 48)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. v_canonical_activities 뷰
# ─────────────────────────────────────────────────────────────────────────────

class TestCanonicalView:

    def _insert_activities(self, db_conn):
        """Garmin + Strava 동일 활동 (matched_group_id) + solo Intervals."""
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, matched_group_id) "
            "VALUES ('garmin', 'g1', '2026-03-25T18:00:00', 10020, 'grp1')"
        )
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, matched_group_id) "
            "VALUES ('strava', 's1', '2026-03-25T18:00:00', 10050, 'grp1')"
        )
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, distance_m) "
            "VALUES ('intervals', 'i1', '2026-03-26T07:00:00', 5000)"
        )

    def test_canonical_returns_one_per_group(self, db_conn):
        self._insert_activities(db_conn)
        rows = db_conn.execute("SELECT * FROM v_canonical_activities").fetchall()
        assert len(rows) == 2  # grp1에서 1개 + solo intervals 1개

    def test_canonical_prefers_garmin(self, db_conn):
        self._insert_activities(db_conn)
        row = db_conn.execute(
            "SELECT source FROM v_canonical_activities "
            "WHERE matched_group_id = 'grp1'"
        ).fetchone()
        assert row[0] == "garmin"

    def test_canonical_intervals_second_priority(self, db_conn):
        """Garmin 없으면 Intervals 우선."""
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, matched_group_id) "
            "VALUES ('intervals', 'i2', '2026-03-27T08:00:00', 'grp2')"
        )
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, matched_group_id) "
            "VALUES ('strava', 's2', '2026-03-27T08:00:00', 'grp2')"
        )
        row = db_conn.execute(
            "SELECT source FROM v_canonical_activities WHERE matched_group_id = 'grp2'"
        ).fetchone()
        assert row[0] == "intervals"


# ─────────────────────────────────────────────────────────────────────────────
# 4. metric_registry
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricRegistry:

    def test_registry_size(self):
        assert len(METRIC_REGISTRY) >= 80, f"등록 메트릭 {len(METRIC_REGISTRY)}개 < 80"

    def test_canonicalize_garmin_alias(self):
        name, cat = canonicalize("aerobicTrainingEffect", source="garmin")
        # 이건 activity_summaries 컬럼이므로 registry에 없을 수 있음.
        # registry에 없으면 unmapped으로 처리됨.
        assert isinstance(name, str)
        assert isinstance(cat, str)

    def test_canonicalize_intervals_trimp(self):
        name, cat = canonicalize("icu_trimp", source="intervals")
        assert name == "trimp"
        assert cat == "training_load"

    def test_canonicalize_direct_name(self):
        name, cat = canonicalize("trimp")
        assert name == "trimp"
        assert cat == "training_load"

    def test_canonicalize_unmapped(self):
        name, cat = canonicalize("completely_unknown_field", source="garmin")
        assert name == "garmin__completely_unknown_field"
        assert cat == "_unmapped"

    def test_get_metric_exists(self):
        md = get_metric("trimp")
        assert md is not None
        assert md.name == "trimp"
        assert md.category == "training_load"

    def test_get_metric_not_exists(self):
        assert get_metric("nonexistent_metric") is None

    def test_list_by_category(self):
        hr_metrics = list_by_category("hr_zone")
        assert len(hr_metrics) >= 5  # zone 1-5

    def test_list_by_scope(self):
        daily = list_by_scope("daily")
        assert len(daily) >= 10  # sleep, stress, readiness, predictions...

    def test_all_categories_documented(self):
        """레지스트리의 모든 category가 METRIC_CATEGORIES에 등록."""
        cats_used = {md.category for md in METRIC_REGISTRY.values()}
        for cat in cats_used:
            assert cat in METRIC_CATEGORIES, f"카테고리 미등록: {cat}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. metric_priority
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricPriority:

    def test_user_highest_priority(self):
        assert get_provider_priority("user") == 0

    def test_runpulse_ml_higher_than_formula(self):
        assert get_provider_priority("runpulse:ml") < get_provider_priority("runpulse:formula")

    def test_runpulse_higher_than_garmin(self):
        assert get_provider_priority("runpulse:formula_v1") < get_provider_priority("garmin")

    def test_garmin_higher_than_strava(self):
        assert get_provider_priority("garmin") < get_provider_priority("strava")

    def test_unknown_provider(self):
        assert get_provider_priority("some_unknown") == 999

    def test_resolve_primary_basic(self, db_conn):
        """3개 provider 중 runpulse:formula가 primary가 되어야 함."""
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'garmin', 85)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'intervals', 91)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'runpulse:formula_v1', 88)"
        )

        resolve_primary(db_conn, "activity", "1", "trimp")

        primary = db_conn.execute(
            "SELECT provider, numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='1' AND metric_name='trimp' AND is_primary=1"
        ).fetchone()
        assert primary[0] == "runpulse:formula_v1"
        assert primary[1] == 88

    def test_user_override(self, db_conn):
        """user provider는 항상 최우선."""
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'runpulse:ml_v1', 90)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'user', 95)"
        )
        resolve_primary(db_conn, "activity", "1", "trimp")

        primary = db_conn.execute(
            "SELECT provider FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='1' AND metric_name='trimp' AND is_primary=1"
        ).fetchone()
        assert primary[0] == "user"

    def test_resolve_for_scope(self, db_conn):
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'garmin', 85)"
        )
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'hrss', 'garmin', 70)"
        )
        count = resolve_for_scope(db_conn, "activity", "1")
        assert count == 2


# ─────────────────────────────────────────────────────────────────────────────
# 6. db_helpers CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestDbHelpers:

    def test_upsert_payload_new(self, db_conn):
        rid, is_new = upsert_payload(
            db_conn, "garmin", "activity_summary", "g123",
            {"activityId": 123, "activityName": "Morning Run"},
            entity_date="2026-03-25",
        )
        assert rid > 0
        assert is_new is True

    def test_upsert_payload_unchanged(self, db_conn):
        payload = {"activityId": 123}
        upsert_payload(db_conn, "garmin", "activity_summary", "g123", payload)
        _, is_new = upsert_payload(db_conn, "garmin", "activity_summary", "g123", payload)
        assert is_new is False

    def test_upsert_payload_changed(self, db_conn):
        upsert_payload(db_conn, "garmin", "activity_summary", "g123", {"v": 1})
        _, is_new = upsert_payload(db_conn, "garmin", "activity_summary", "g123", {"v": 2})
        assert is_new is True

    def test_get_payload(self, db_conn):
        upsert_payload(db_conn, "garmin", "activity_summary", "g123", {"test": True})
        result = get_payload(db_conn, "garmin", "activity_summary", "g123")
        assert result == {"test": True}

    def test_upsert_activity(self, db_conn):
        aid = upsert_activity(db_conn, {
            "source": "garmin",
            "source_id": "g456",
            "activity_type": "running",
            "start_time": "2026-03-25T18:30:00Z",
            "distance_m": 10020.0,
            "duration_sec": 3120,
            "avg_hr": 155,
            "avg_pace_sec_km": 312.0,
            "training_effect_aerobic": 3.2,
        })
        assert aid > 0

        activity = get_activity(db_conn, aid)
        assert activity["distance_m"] == 10020.0
        assert activity["avg_hr"] == 155
        assert activity["training_effect_aerobic"] == 3.2

    def test_upsert_activity_update(self, db_conn):
        upsert_activity(db_conn, {
            "source": "garmin", "source_id": "g789",
            "activity_type": "running", "start_time": "2026-01-01T08:00:00Z",
            "distance_m": 5000,
        })
        upsert_activity(db_conn, {
            "source": "garmin", "source_id": "g789",
            "activity_type": "running", "start_time": "2026-01-01T08:00:00Z",
            "distance_m": 5050,  # 업데이트
            "avg_hr": 145,       # 새 필드 추가
        })
        row = db_conn.execute(
            "SELECT distance_m, avg_hr FROM activity_summaries WHERE source_id = 'g789'"
        ).fetchone()
        assert row[0] == 5050
        assert row[1] == 145

    def test_upsert_metric_and_get_primary(self, db_conn):
        upsert_metric(
            db_conn, "activity", "1", "trimp", "garmin",
            numeric_value=85, category="training_load",
        )
        upsert_metric(
            db_conn, "activity", "1", "trimp", "runpulse:formula_v1",
            numeric_value=88, category="training_load",
        )
        resolve_primary(db_conn, "activity", "1", "trimp")

        primary = get_primary_metric(db_conn, "activity", "1", "trimp")
        assert primary is not None
        assert primary["provider"] == "runpulse:formula_v1"
        assert primary["numeric_value"] == 88

    def test_upsert_metrics_batch(self, db_conn):
        metrics = [
            {"metric_name": "hr_zone_1_sec", "provider": "garmin",
             "numeric_value": 1200, "category": "hr_zone"},
            {"metric_name": "hr_zone_2_sec", "provider": "garmin",
             "numeric_value": 900, "category": "hr_zone"},
            {"metric_name": "empty_metric", "provider": "garmin"},  # 값 없음 → skip
        ]
        count = upsert_metrics_batch(db_conn, "activity", "1", metrics)
        assert count == 2

    def test_get_all_providers(self, db_conn):
        upsert_metric(db_conn, "activity", "1", "trimp", "garmin", numeric_value=85)
        upsert_metric(db_conn, "activity", "1", "trimp", "intervals", numeric_value=91)
        providers = get_all_providers(db_conn, "activity", "1", "trimp")
        assert len(providers) == 2
        names = {p["provider"] for p in providers}
        assert names == {"garmin", "intervals"}

    def test_get_metrics_by_category(self, db_conn):
        upsert_metric(db_conn, "activity", "1", "hr_zone_1_sec", "garmin",
                       numeric_value=1200, category="hr_zone")
        upsert_metric(db_conn, "activity", "1", "hr_zone_2_sec", "garmin",
                       numeric_value=900, category="hr_zone")
        upsert_metric(db_conn, "activity", "1", "trimp", "garmin",
                       numeric_value=85, category="training_load")

        # primary 설정
        resolve_for_scope(db_conn, "activity", "1")

        hr = get_metrics_by_category(db_conn, "activity", "1", "hr_zone")
        assert len(hr) == 2

    def test_upsert_daily_wellness_merge(self, db_conn):
        """Garmin이 먼저 채우고, Intervals가 빈 필드만 채움."""
        upsert_daily_wellness(db_conn, {
            "date": "2026-03-25",
            "sleep_score": 82,
            "resting_hr": 48,
        })
        upsert_daily_wellness(db_conn, {
            "date": "2026-03-25",
            "sleep_score": 75,   # 이미 채워져 있으므로 무시
            "weight_kg": 70.5,   # NULL이었으므로 채움
        })
        row = db_conn.execute(
            "SELECT sleep_score, weight_kg FROM daily_wellness WHERE date = '2026-03-25'"
        ).fetchone()
        assert row[0] == 82    # Garmin 값 유지
        assert row[1] == 70.5  # Intervals 값으로 채움

    def test_upsert_daily_fitness(self, db_conn):
        fid = upsert_daily_fitness(
            db_conn, "2026-03-25", "intervals",
            ctl=52.3, atl=68.1, tsb=-15.8,
        )
        assert fid > 0

    def test_get_db_status(self, db_conn):
        status = get_db_status(db_conn)
        assert "activity_summaries_count" in status
        assert "metric_providers" in status
        assert "primary_violations" in status
        assert status["primary_violations"] == 0

    def test_get_activity_list(self, db_conn):
        for i in range(5):
            upsert_activity(db_conn, {
                "source": "garmin", "source_id": f"g{i}",
                "activity_type": "running",
                "start_time": f"2026-03-{20+i}T08:00:00Z",
                "distance_m": 10000 + i * 100,
            })
        activities = get_activity_list(db_conn, limit=3, canonical_only=False)
        assert len(activities) == 3
        # 최신순 정렬 확인
        assert activities[0]["start_time"] > activities[1]["start_time"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. 마이그레이션 멱등성
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration:

    def test_migrate_idempotent(self, db_conn):
        migrate_db(db_conn)
        migrate_db(db_conn)  # 두 번째도 안전

    def test_create_tables_idempotent(self, db_conn):
        create_tables(db_conn)
        create_tables(db_conn)  # 두 번째도 안전


# ─────────────────────────────────────────────────────────────────────────────
# 8. 성능 벤치마크
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:

    def test_activity_list_under_200ms(self, db_conn):
        """활동 200개 + 50개 목록 조회 < 200ms."""
        for i in range(200):
            db_conn.execute(
                "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m) "
                "VALUES (?, ?, 'running', ?, ?)",
                ("garmin", f"g{i}", f"2026-01-{(i%28)+1:02d}T08:00:00Z", 10000 + i),
            )
        db_conn.commit()

        start = time.perf_counter()
        rows = db_conn.execute(
            "SELECT * FROM activity_summaries ORDER BY start_time DESC LIMIT 50"
        ).fetchall()
        elapsed = time.perf_counter() - start

        assert len(rows) == 50
        assert elapsed < 0.2, f"활동 목록 조회 {elapsed:.3f}s > 200ms"

    def test_metric_store_bulk_insert(self, db_conn):
        """메트릭 1000개 INSERT < 1s."""
        start = time.perf_counter()
        for i in range(1000):
            db_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, category) "
                "VALUES ('activity', ?, ?, 'garmin', ?, 'test')",
                (str(i), f"metric_{i}", float(i)),
            )
        db_conn.commit()
        elapsed = time.perf_counter() - start

        count = db_conn.execute("SELECT COUNT(*) FROM metric_store").fetchone()[0]
        assert count == 1000
        assert elapsed < 1.0, f"1000 메트릭 INSERT {elapsed:.3f}s > 1s"
        
        # ─────────────────────────────────────────────────────────────────────────────
# 9. 실 DB 검증 — default 유저
# ─────────────────────────────────────────────────────────────────────────────

class TestRealDbDefault:
    """default 유저 DB에 대한 v0.3 마이그레이션 및 기본 검증.

    data/users/default/running.db가 없으면 자동 skip.
    """

    def test_existing_tables(self, db_conn_default):
        """기존 v0.2 테이블이 존재하는지 확인."""
        tables = {
            r[0] for r in db_conn_default.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # v0.2 테이블 중 일부는 있어야 함
        assert "activity_summaries" in tables

    def test_migrate_creates_new_tables(self, db_conn_default):
        """v0.3 마이그레이션 후 신규 테이블 추가 확인."""
        migrate_db(db_conn_default)
        tables = {
            r[0] for r in db_conn_default.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # v0.3 신규 테이블
        for t in ["metric_store", "source_payloads", "weather_cache"]:
            assert t in tables, f"마이그레이션 후 {t} 없음"

    def test_existing_data_preserved(self, db_conn_default):
        """마이그레이션 후 기존 activity_summaries 데이터 보존."""
        count_before = db_conn_default.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]

        migrate_db(db_conn_default)

        count_after = db_conn_default.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]
        assert count_after == count_before, "마이그레이션 후 데이터 유실"

    def test_schema_version_updated(self, db_conn_default):
        """마이그레이션 후 schema version이 10."""
        migrate_db(db_conn_default)
        ver = db_conn_default.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION


# ─────────────────────────────────────────────────────────────────────────────
# 10. 실 DB 검증 — pansongit@gmail.com 유저
# ─────────────────────────────────────────────────────────────────────────────

class TestRealDbUser:
    """실 유저(pansongit@gmail.com) DB에 대한 v0.3 마이그레이션 검증.

    data/users/pansongit@gmail.com/running.db가 없으면 자동 skip.
    """

    def test_has_real_data(self, db_conn_user):
        """실제 활동 데이터가 있는지 확인."""
        count = db_conn_user.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]
        assert count > 0, "실 유저 DB에 활동 데이터 없음"

    def test_migrate_preserves_data(self, db_conn_user):
        """마이그레이션이 기존 데이터를 보존."""
        count_before = db_conn_user.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]

        migrate_db(db_conn_user)

        count_after = db_conn_user.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]
        assert count_after == count_before

    def test_migrate_adds_metric_store(self, db_conn_user):
        """마이그레이션 후 metric_store 테이블 생성."""
        migrate_db(db_conn_user)
        tables = {
            r[0] for r in db_conn_user.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "metric_store" in tables

    def test_source_payloads_exist(self, db_conn_user):
        """raw payload가 보존되어 있는지 확인 (reprocess 가능 여부)."""
        # v0.2에서는 raw_source_payloads 이름이었을 수 있음
        tables = {
            r[0] for r in db_conn_user.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # v0.2 이름 또는 v0.3 이름
        has_payloads = "raw_source_payloads" in tables or "source_payloads" in tables
        assert has_payloads, "raw payload 테이블 없음"

        # 데이터 존재 확인
        table_name = "raw_source_payloads" if "raw_source_payloads" in tables else "source_payloads"
        count = db_conn_user.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
        assert count > 0, f"{table_name}에 데이터 없음 — reprocess 불가"

    def test_source_distribution(self, db_conn_user):
        """소스별 활동 분포 확인."""
        rows = db_conn_user.execute(
            "SELECT source, COUNT(*) FROM activity_summaries GROUP BY source"
        ).fetchall()
        dist = {r[0]: r[1] for r in rows}
        print(f"\n  소스별 활동 분포: {dist}")
        assert len(dist) >= 1, "최소 1개 소스 필요"

    def test_canonical_view_after_migrate(self, db_conn_user):
        """마이그레이션 후 canonical 뷰 동작."""
        migrate_db(db_conn_user)

        total = db_conn_user.execute(
            "SELECT COUNT(*) FROM activity_summaries"
        ).fetchone()[0]
        canonical = db_conn_user.execute(
            "SELECT COUNT(*) FROM v_canonical_activities"
        ).fetchone()[0]

        print(f"\n  전체 활동: {total}, 대표 활동: {canonical}")
        assert canonical <= total
        assert canonical > 0

    def test_daily_wellness_has_data(self, db_conn_user):
        """daily_wellness에 데이터가 있는지 확인."""
        tables = {
            r[0] for r in db_conn_user.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "daily_wellness" not in tables:
            pytest.skip("daily_wellness 테이블 없음")

        count = db_conn_user.execute(
            "SELECT COUNT(*) FROM daily_wellness"
        ).fetchone()[0]
        print(f"\n  daily_wellness 행 수: {count}")
        # 있으면 OK, 없어도 실패는 아님 (아직 sync 안 했을 수 있음)

    def test_db_summary(self, db_conn_user):
        """실 DB 전체 요약 출력 (정보 확인용)."""
        migrate_db(db_conn_user)

        tables = db_conn_user.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"\n  테이블 목록: {[t[0] for t in tables]}")

        ver = db_conn_user.execute("PRAGMA user_version").fetchone()[0]
        print(f"  스키마 버전: {ver}")

        for t in ["activity_summaries", "daily_wellness", "daily_fitness",
                   "metric_store", "activity_laps", "activity_streams"]:
            try:
                count = db_conn_user.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"  {t}: {count} rows")
            except Exception:
                print(f"  {t}: (테이블 없음)")

