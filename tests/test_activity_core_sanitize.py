"""센서 미측정/GPS 글리치 값 정리 — sanitize_activity_core, ACWR 캡."""
import sqlite3

from src.db_setup import create_tables
from src.metrics.acwr import ACWRCalculator
from src.metrics.base import CalcContext
from src.sync._helpers import sanitize_activity_core, save_activity_core
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn


class TestSanitizeActivityCore:
    def test_zero_hr_becomes_none(self):
        clean = sanitize_activity_core({"avg_hr": 0, "max_hr": 0, "distance_m": 5000})
        assert clean["avg_hr"] is None
        assert clean["max_hr"] is None
        assert clean["distance_m"] == 5000

    def test_valid_hr_is_kept(self):
        clean = sanitize_activity_core({"avg_hr": 150, "max_hr": 180})
        assert (clean["avg_hr"], clean["max_hr"]) == (150, 180)

    def test_impossible_max_speed_becomes_none(self):
        assert sanitize_activity_core({"max_speed_ms": 103.2})["max_speed_ms"] is None

    def test_plausible_max_speed_is_kept(self):
        assert sanitize_activity_core({"max_speed_ms": 6.5})["max_speed_ms"] == 6.5

    def test_input_is_not_mutated(self):
        core = {"avg_hr": 0}
        sanitize_activity_core(core)
        assert core["avg_hr"] == 0

    def test_save_activity_core_stores_null(self):
        conn = _conn()
        aid = save_activity_core(conn, {
            "source": "garmin", "source_id": "g-zero", "start_time": "2024-07-06 11:12:26",
            "activity_type": "running", "distance_m": 5000, "duration_sec": 1800,
            "avg_hr": 0, "max_hr": 0, "max_speed_ms": 103.2,
        })
        row = conn.execute(
            "SELECT avg_hr, max_hr, max_speed_ms FROM activity_summaries WHERE id=?", (aid,)
        ).fetchone()
        assert (row["avg_hr"], row["max_hr"], row["max_speed_ms"]) == (None, None, None)


class TestStreamHeartRate:
    def test_zero_heart_rate_becomes_null(self):
        """심박 0은 센서 미측정이므로 스트림에서도 NULL 처리한다."""
        from src.sync.extractors.garmin_extractor import GarminExtractor

        rows = GarminExtractor().extract_activity_streams({
            "metricDescriptors": [
                {"key": "directElapsedDuration", "metricsIndex": 0},
                {"key": "directHeartRate", "metricsIndex": 1},
            ],
            "activityDetailMetrics": [
                {"metrics": [0.0, 0.0]},
                {"metrics": [1.0, 120.0]},
            ],
        })
        assert "heart_rate" not in rows[0]
        assert rows[1]["heart_rate"] == 120


class TestACWRCap:
    """ACWR은 일별 부하에서 자체 EWMA(α = 2/(N+1))로 계산한다(PMC α 변경과 분리, DECISIONS D1f)."""

    def _compute(self, load, history=True):
        from datetime import date, timedelta
        conn = _conn()
        if history:
            upsert_metric(conn, "daily", "2026-03-04", "ctl", "runpulse:formula_v1", numeric_value=40.0, category="rp_load")  # 28일 전 CTL(P7-PRED-89)
            conn.commit()
        loads = {(date(2026, 4, 1) - timedelta(days=i)).isoformat(): load for i in range(60)} if load else {}
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01", _prefetched_daily_loads=loads)
        return ACWRCalculator().compute(ctx)

    def test_steady_load_ratio(self):
        # 49일 창 일정 부하: ATL ≈ 부하, CTL ≈ 부하 × (1 − (41/43)^50) → 약 1.10
        r = self._compute(load=80.0)
        assert len(r) == 1 and 1.05 < r[0].numeric_value < 1.15

    def test_low_chronic_load_returns_empty(self):
        assert self._compute(load=2.0) == []          # P7-PRED-89: 5.0 절단 대신 "데이터 수집 중"

    def test_no_history_returns_empty(self):
        assert self._compute(load=80.0, history=False) == []

    def test_zero_ctl_returns_empty(self):
        assert self._compute(load=0) == []