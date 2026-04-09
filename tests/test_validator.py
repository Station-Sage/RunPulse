"""DataValidator 테스트.

각 체크가 PASS/WARN/FAIL을 올바르게 판정하는지 검증합니다.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables
from src.validation.validator import DataValidator, CheckResult


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def empty_conn():
    """빈 인메모리 DB (테이블 있음)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn


@pytest.fixture
def populated_conn(empty_conn):
    """기본 데이터가 채워진 DB."""
    conn = empty_conn
    _populate_base(conn)
    return conn


def _populate_base(conn: sqlite3.Connection):
    """모든 체크가 PASS되는 최소 데이터 세트."""
    today = date.today()

    # source_payloads
    for i, src in enumerate(["garmin", "strava", "intervals", "runalyze"], start=1):
        conn.execute(
            "INSERT INTO source_payloads (source, entity_type, entity_id, payload, payload_hash) "
            "VALUES (?, 'activity', ?, '{}', ?)",
            (src, f"ext_{i}", f"hash_{i}"),
        )

    # activity_summaries
    for i, src in enumerate(["garmin", "strava", "intervals", "runalyze"], start=1):
        conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, start_time, distance_m, duration_sec, activity_type)
               VALUES (?, ?, ?, ?, ?, 'running')""",
            (src, f"ext_{i}", f"{today.isoformat()}T08:00:00", 10000, 3000),
        )

    # metric_store (activity scope, runpulse provider, category 있음)
    activity_ids = [r[0] for r in conn.execute("SELECT id FROM activity_summaries").fetchall()]
    for act_id in activity_ids:
        for metric in ["trimp", "hrss", "vo2max", "efficiency_factor", "fearp", "vdot"]:
            conn.execute(
                """INSERT INTO metric_store
                   (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)
                   VALUES ('activity', ?, ?, 'fitness', 'runpulse:formula', 10.0, 1)""",
                (str(act_id), metric),
            )

    # daily_wellness — 최근 30일 중 25일
    for i in range(25):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO daily_wellness (date, resting_hr) VALUES (?, 55)",
            (d,),
        )

    # metric_store (daily scope) — ctl/atl/tsb 30일치 (연속)
    for i in range(30):
        d = (today - timedelta(days=i)).isoformat()
        for metric in ["ctl", "atl", "tsb"]:
            conn.execute(
                """INSERT INTO metric_store
                   (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)
                   VALUES ('daily', ?, ?, 'fitness', 'runpulse:formula', 50.0, 1)""",
                (d, metric),
            )

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 1. row_counts
# ─────────────────────────────────────────────────────────────────────────────

class TestRowCounts:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        check = _find(r, "row_counts")
        assert check.status == "PASS"

    def test_fail_empty_db(self, empty_conn):
        r = DataValidator(empty_conn).run_all()
        check = _find(r, "row_counts")
        assert check.status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 2. source_distribution
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceDistribution:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "source_distribution").status == "PASS"

    def test_fail_missing_source(self, populated_conn):
        # runalyze 제거
        populated_conn.execute("DELETE FROM activity_summaries WHERE source = 'runalyze'")
        populated_conn.commit()
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "source_distribution").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 3. unmapped_metric_ratio
# ─────────────────────────────────────────────────────────────────────────────

class TestUnmappedMetricRatio:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "unmapped_metric_ratio").status == "PASS"

    def test_fail_all_null(self, empty_conn):
        empty_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'runpulse:formula', 10.0)"
        )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        # category=NULL이 100%이므로 FAIL
        assert _find(r, "unmapped_metric_ratio").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 4. metric_density
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricDensity:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "metric_density").status == "PASS"

    def test_fail_sparse(self, empty_conn):
        # 활동 10개, 메트릭 2개
        for i in range(10):
            empty_conn.execute(
                "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, "
                "duration_sec, activity_type) VALUES ('garmin', ?, '2025-01-01T08:00:00', 5000, 1800, 'running')",
                (f"id_{i}",),
            )
        for i in range(1, 11):
            empty_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
                "VALUES ('activity', ?, 'trimp', 'fitness', 'runpulse:formula', 5.0)",
                (str(i),),
            )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "metric_density").status in ("WARN", "FAIL")


# ─────────────────────────────────────────────────────────────────────────────
# 5. primary_uniqueness
# ─────────────────────────────────────────────────────────────────────────────

class TestPrimaryUniqueness:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "primary_uniqueness").status == "PASS"

    def test_fail_duplicate_primary(self, empty_conn):
        for provider in ("garmin", "runpulse:formula"):
            empty_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary) "
                "VALUES ('activity', '1', 'trimp', 'fitness', ?, 10.0, 1)",
                (provider,),
            )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "primary_uniqueness").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 6. provider_distribution
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderDistribution:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "provider_distribution").status == "PASS"

    def test_fail_no_runpulse(self, empty_conn):
        empty_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
            "VALUES ('activity', '1', 'trimp', 'fitness', 'garmin', 10.0)"
        )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "provider_distribution").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 7. dedup_consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestDedupConsistency:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "dedup_consistency").status == "PASS"

    def test_fail_same_source_in_group(self, empty_conn):
        group_id = "group-abc"
        for i in range(2):
            empty_conn.execute(
                "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, "
                "duration_sec, activity_type, matched_group_id) "
                "VALUES ('garmin', ?, '2025-01-01T08:00:00', 10000, 3000, 'running', ?)",
                (f"g_{i}", group_id),
            )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "dedup_consistency").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 8. data_quality
# ─────────────────────────────────────────────────────────────────────────────

class TestDataQuality:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "data_quality").status == "PASS"

    def test_fail_negative_distance(self, empty_conn):
        empty_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, "
            "duration_sec, activity_type) VALUES ('garmin', 'x', '2025-01-01T08:00:00', -100, 1800, 'running')"
        )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "data_quality").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 9. wellness_coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestWellnessCoverage:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "wellness_coverage").status == "PASS"

    def test_fail_no_wellness(self, empty_conn):
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "wellness_coverage").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 10. fitness_continuity
# ─────────────────────────────────────────────────────────────────────────────

class TestFitnessContinuity:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "fitness_continuity").status == "PASS"

    def test_fail_large_gap(self, empty_conn):
        today = date.today()
        # 10일치 → 10일 gap → 다시 5일치
        for i in range(5):
            d = (today - timedelta(days=i)).isoformat()
            empty_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
                "VALUES ('daily', ?, 'ctl', 'fitness', 'runpulse:formula', 50.0)",
                (d,),
            )
        for i in range(25, 35):
            d = (today - timedelta(days=i)).isoformat()
            empty_conn.execute(
                "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
                "VALUES ('daily', ?, 'ctl', 'fitness', 'runpulse:formula', 50.0)",
                (d,),
            )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "fitness_continuity").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 11. referential_integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestReferentialIntegrity:
    def test_pass(self, populated_conn):
        r = DataValidator(populated_conn).run_all()
        assert _find(r, "referential_integrity").status == "PASS"

    def test_fail_orphan_lap(self, empty_conn):
        empty_conn.execute(
            "INSERT INTO activity_laps (activity_id, source, lap_index, start_time, duration_sec) "
            "VALUES (9999, 'garmin', 1, '2025-01-01T08:00:00', 300)"
        )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "referential_integrity").status == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 12. engine_coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestEngineCoverage:
    def test_fail_empty_metric_store(self, empty_conn):
        r = DataValidator(empty_conn).run_all()
        check = _find(r, "engine_coverage")
        # 메트릭 없으면 WARN(produces 로드 실패 시) 또는 FAIL
        assert check.status in ("WARN", "FAIL")

    def test_pass_all_produces_present(self, empty_conn):
        """모든 produces 메트릭이 metric_store에 존재하면 PASS."""
        from src.metrics.engine import ALL_CALCULATORS
        for calc in ALL_CALCULATORS:
            for metric in calc.produces:
                empty_conn.execute(
                    "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
                    "VALUES ('daily', '2025-01-01', ?, 'fitness', 'runpulse:formula', 1.0)",
                    (metric,),
                )
        empty_conn.commit()
        r = DataValidator(empty_conn).run_all()
        assert _find(r, "engine_coverage").status == "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# run_all — 전체 구조
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAll:
    def test_returns_12_results(self, populated_conn):
        results = DataValidator(populated_conn).run_all()
        assert len(results) == 12

    def test_all_have_valid_status(self, populated_conn):
        results = DataValidator(populated_conn).run_all()
        for r in results:
            assert r.status in ("PASS", "WARN", "FAIL"), f"{r.name}: unexpected status {r.status!r}"

    def test_check_result_fields(self, populated_conn):
        results = DataValidator(populated_conn).run_all()
        for r in results:
            assert isinstance(r, CheckResult)
            assert r.name
            assert r.expected
            assert r.actual


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _find(results: list[CheckResult], name: str) -> CheckResult:
    for r in results:
        if r.name == name:
            return r
    raise AssertionError(f"Check '{name}' not found in results")
