"""efficiency.py 테스트."""

import json
import pytest
from datetime import date, timedelta

from src.analysis.efficiency import calculate_efficiency, efficiency_trend


def _insert_activity(conn, source="garmin", start_time=None, matched_group_id=None):
    """테스트용 활동 삽입 헬퍼."""
    if start_time is None:
        start_time = date.today().isoformat() + "T08:00:00"
    cur = conn.execute(
        "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, "
        "distance_km, duration_sec, matched_group_id) VALUES (?,?,?,?,?,?,?)",
        (source, f"{source}_{start_time}", "running", start_time, 10.0, 3600,
         matched_group_id),
    )
    return cur.lastrowid


def _insert_strava_with_stream(conn, stream_data: dict, tmp_path,
                                start_time=None, matched_group_id=None) -> int:
    """Strava 활동 + stream 파일 삽입 헬퍼."""
    sid = _insert_activity(conn, "strava", start_time, matched_group_id)
    stream_file = tmp_path / f"stream_{sid}.json"
    stream_file.write_text(json.dumps(stream_data), encoding="utf-8")
    conn.execute(
        "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
        "VALUES (?, 'strava', 'stream_file', ?)",
        (sid, str(stream_file)),
    )
    return sid


def _make_stream(n: int, v1: float, v2: float, hr: float = 150.0) -> dict:
    """전반 속도 v1, 후반 속도 v2, HR 일정인 stream dict 생성."""
    mid = n // 2
    velocities = [v1] * mid + [v2] * (n - mid)
    heartrates = [hr] * n
    return {"heartrate": heartrates, "velocity_smooth": velocities}


class TestCalculateEfficiency:
    def test_calculate_efficiency_good(self, db_conn, tmp_path):
        """decoupling < 5% → status 'good'."""
        # ef1 = 3.0/150 = 0.02, ef2 = 2.9/150 = 0.01933 → decoupling ≈ 3.3%
        stream = _make_stream(100, v1=3.0, v2=2.9)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["status"] == "good"
        assert result["decoupling_pct"] < 5.0

    def test_calculate_efficiency_fair(self, db_conn, tmp_path):
        """decoupling 5~10% → status 'fair'."""
        # ef1=0.02, ef2=2.7/150=0.018 → decoupling=10% (경계 테스트는 별도)
        # 여기서는 7% 근처: v2=2.79 → ef2=0.0186 → decouple=(0.02-0.0186)/0.02*100=7%
        stream = _make_stream(100, v1=3.0, v2=2.79)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["status"] == "fair"
        assert 5.0 <= result["decoupling_pct"] < 10.0

    def test_calculate_efficiency_poor(self, db_conn, tmp_path):
        """decoupling > 10% → status 'poor'."""
        # v2=2.6 → ef2=2.6/150=0.01733 → decouple=(0.02-0.01733)/0.02*100=13.3%
        stream = _make_stream(100, v1=3.0, v2=2.6)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["status"] == "poor"
        assert result["decoupling_pct"] > 10.0

    def test_calculate_efficiency_boundary_5(self, db_conn, tmp_path):
        """decoupling 정확히 5% → status 'fair'."""
        # ef1=3.0/150=0.02, ef2=2.85/150=0.019 → decouple=(0.02-0.019)/0.02*100=5.0%
        stream = _make_stream(100, v1=3.0, v2=2.85)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["decoupling_pct"] == pytest.approx(5.0, abs=0.01)
        assert result["status"] == "fair"

    def test_calculate_efficiency_boundary_10(self, db_conn, tmp_path):
        """decoupling 정확히 10% → status 'poor'."""
        # ef1=3.0/150=0.02, ef2=2.7/150=0.018 → decouple=(0.02-0.018)/0.02*100=10.0%
        stream = _make_stream(100, v1=3.0, v2=2.7)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["decoupling_pct"] == pytest.approx(10.0, abs=0.01)
        assert result["status"] == "poor"

    def test_no_stream_file(self, db_conn):
        """stream 파일 없는 activity → None."""
        sid = _insert_activity(db_conn, "garmin")
        assert calculate_efficiency(db_conn, sid) is None

    def test_no_heartrate_in_stream(self, db_conn, tmp_path):
        """heartrate 키 없는 stream → None."""
        stream = {"velocity_smooth": [3.0] * 100}
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        assert calculate_efficiency(db_conn, sid) is None

    def test_no_velocity_in_stream(self, db_conn, tmp_path):
        """velocity_smooth 키 없는 stream → None."""
        stream = {"heartrate": [150] * 100}
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        assert calculate_efficiency(db_conn, sid) is None

    def test_insufficient_data_points(self, db_conn, tmp_path):
        """60포인트 미만 → None."""
        stream = _make_stream(59, v1=3.0, v2=2.9)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        assert calculate_efficiency(db_conn, sid) is None

    def test_ef_calculation_accuracy(self, db_conn, tmp_path):
        """알려진 입력값으로 EF 및 decoupling 정확도 검증."""
        # 전반 100개: v=3.0, hr=150 → ef1=0.02
        # 후반 100개: v=2.85, hr=150 → ef2=0.019 → decoupling=5.0%
        stream = _make_stream(200, v1=3.0, v2=2.85)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path)
        result = calculate_efficiency(db_conn, sid)
        assert result is not None
        assert result["ef_first_half"] == pytest.approx(3.0 / 150, rel=1e-3)
        assert result["ef_second_half"] == pytest.approx(2.85 / 150, rel=1e-3)
        assert result["decoupling_pct"] == pytest.approx(5.0, abs=0.01)
        assert result["avg_hr_first"] == pytest.approx(150.0)
        assert result["data_points"] == 200

    def test_activity_with_group_lookup(self, db_conn, tmp_path):
        """garmin 활동 → 같은 그룹의 strava stream 탐색."""
        gid = _insert_activity(db_conn, "garmin", matched_group_id="grp_1")
        db_conn.execute(
            "UPDATE activity_summaries SET matched_group_id = 'grp_1' WHERE id = ?", (gid,)
        )
        stream = _make_stream(100, v1=3.0, v2=2.9)
        sid = _insert_strava_with_stream(db_conn, stream, tmp_path,
                                          matched_group_id="grp_1")
        db_conn.execute(
            "UPDATE activity_summaries SET matched_group_id = 'grp_1' WHERE id = ?", (sid,)
        )
        db_conn.commit()
        # garmin 활동 id로 efficiency 계산 시 strava stream 탐색
        result = calculate_efficiency(db_conn, gid)
        assert result is not None
        assert result["status"] == "good"


class TestEfficiencyTrend:
    def test_efficiency_trend_multiple_weeks(self, db_conn, tmp_path):
        """여러 주 데이터 → 주별 집계."""
        today = date.today()
        # 2주 전 월요일에 활동 삽입
        two_weeks_ago = today - timedelta(days=today.weekday() + 14)
        start_time = two_weeks_ago.isoformat() + "T08:00:00"
        stream = _make_stream(100, v1=3.0, v2=2.9)
        _insert_strava_with_stream(db_conn, stream, tmp_path, start_time=start_time)
        db_conn.commit()

        results = efficiency_trend(db_conn, weeks=4)
        assert isinstance(results, list)
        # 데이터 있는 주만 포함
        assert len(results) >= 1
        for entry in results:
            assert "week_start" in entry
            assert "avg_ef" in entry
            assert "avg_decoupling" in entry
            assert "activity_count" in entry
            assert "status" in entry

    def test_efficiency_trend_skips_no_stream(self, db_conn):
        """stream 없는 activity는 집계에서 제외 → 결과 없음."""
        _insert_activity(db_conn, "garmin")
        db_conn.commit()
        results = efficiency_trend(db_conn, weeks=2)
        assert results == []
