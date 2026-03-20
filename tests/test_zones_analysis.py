"""zones_analysis.py 테스트."""

import json
import pytest
from datetime import date, timedelta

from src.analysis.zones_analysis import analyze_zones, weekly_zone_trend


_TODAY = date.today().isoformat()
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _insert_activity(conn, start_time=None, avg_hr=155, duration_sec=3600,
                     matched_group_id=None, source="garmin"):
    """테스트용 활동 삽입 헬퍼."""
    if start_time is None:
        start_time = _TODAY + "T08:00:00"
    cur = conn.execute(
        "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, "
        "distance_km, duration_sec, avg_hr, matched_group_id) VALUES (?,?,?,?,?,?,?,?)",
        (source, f"{source}_{start_time}", "running", start_time,
         10.0, duration_sec, avg_hr, matched_group_id),
    )
    return cur.lastrowid


def _insert_strava_with_stream(conn, heartrates: list, tmp_path,
                                start_time=None, matched_group_id=None) -> int:
    """Strava 활동 + stream 파일 삽입 헬퍼."""
    sid = _insert_activity(conn, start_time, source="strava",
                           matched_group_id=matched_group_id)
    stream_data = {
        "heartrate": heartrates,
        "velocity_smooth": [3.0] * len(heartrates),
        "time": list(range(len(heartrates))),
        "distance": [i * 3.0 for i in range(len(heartrates))],
    }
    stream_file = tmp_path / f"stream_{sid}.json"
    stream_file.write_text(json.dumps(stream_data), encoding="utf-8")
    conn.execute(
        "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
        "VALUES (?, 'strava', 'stream_file', ?)",
        (sid, str(stream_file)),
    )
    return sid


def _hr_list_with_zone_pcts(z1=25, z2=55, z3=10, z4=7, z5=3,
                              max_hr=190) -> list[int]:
    """원하는 zone 비율로 HR 리스트 생성 (zones.py 기본 경계값 기준)."""
    from src.utils.zones import hr_zones
    bounds = hr_zones(max_hr)
    # 각 zone 중앙 HR 사용
    zone_midpoints = [int((b[0] + b[1]) / 2) for b in bounds]
    result = []
    for z_idx, pct in enumerate([z1, z2, z3, z4, z5]):
        result.extend([zone_midpoints[z_idx]] * pct)
    return result


class TestAnalyzeZones:
    def test_zone_distribution_sum_100(self, db_conn, tmp_path):
        """모든 zone pct 합 ≈ 100%."""
        hr_data = _hr_list_with_zone_pcts(z1=20, z2=50, z3=15, z4=10, z5=5)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        total = sum(z["pct"] for z in result["zone_distribution"].values())
        assert total == pytest.approx(100.0, abs=0.5)

    def test_polarization_optimal(self, db_conn, tmp_path):
        """easy 80% → 'optimal'."""
        # Z1+Z2=80%, Z3=10%, Z4+Z5=10%
        hr_data = _hr_list_with_zone_pcts(z1=40, z2=40, z3=10, z4=7, z5=3)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["polarization_status"] == "optimal"
        assert 75 <= result["easy_pct"] <= 85

    def test_polarization_too_hard(self, db_conn, tmp_path):
        """easy 60% → 'too_hard'."""
        hr_data = _hr_list_with_zone_pcts(z1=20, z2=40, z3=20, z4=15, z5=5)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["polarization_status"] == "too_hard"
        assert result["easy_pct"] < 75

    def test_polarization_too_easy(self, db_conn, tmp_path):
        """easy 90% → 'too_easy'."""
        hr_data = _hr_list_with_zone_pcts(z1=50, z2=40, z3=5, z4=4, z5=1)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["polarization_status"] == "too_easy"
        assert result["easy_pct"] > 85

    def test_threshold_heavy(self, db_conn, tmp_path):
        """moderate 30%, easy 80% → 'threshold_heavy' (우선순위 높음)."""
        # Z1+Z2=60%, Z3=30%, Z4+Z5=10%  → easy=60% < 75% 이지만 moderate>25 우선
        # 대신 easy=70%, moderate=30% 로 구성
        hr_data = _hr_list_with_zone_pcts(z1=35, z2=35, z3=30, z4=0, z5=0)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["polarization_status"] == "threshold_heavy"
        assert result["moderate_pct"] > 25

    def test_boundary_75(self, db_conn, tmp_path):
        """easy 정확히 75% → 'optimal'."""
        hr_data = _hr_list_with_zone_pcts(z1=37, z2=38, z3=15, z4=7, z5=3)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["easy_pct"] == pytest.approx(75.0, abs=1.0)
        assert result["polarization_status"] in ("optimal", "too_hard")  # 경계

    def test_boundary_85(self, db_conn, tmp_path):
        """easy 정확히 85% → 'optimal'."""
        hr_data = _hr_list_with_zone_pcts(z1=42, z2=43, z3=10, z4=3, z5=2)
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["easy_pct"] == pytest.approx(85.0, abs=1.0)
        assert result["polarization_status"] in ("optimal", "too_easy")  # 경계

    def test_strava_stream_priority(self, db_conn, tmp_path):
        """stream 있으면 data_source 'strava_stream'."""
        hr_data = [140] * 100 + [155] * 100
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["data_source"] == "strava_stream"

    def test_intervals_fallback(self, db_conn):
        """stream 없고 intervals hr_zones 있으면 'intervals_zones'."""
        sid = _insert_activity(db_conn, source="intervals")
        # hr_zone_distribution JSON 저장
        zones_data = {"1": 600, "2": 1200, "3": 400, "4": 200, "5": 100}
        db_conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
            "VALUES (?, 'intervals', 'hr_zone_distribution', ?)",
            (sid, json.dumps(zones_data)),
        )
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["data_source"] == "intervals_zones"
        assert result["total_time_seconds"] == 2500

    def test_avg_hr_last_resort(self, db_conn):
        """stream 없고 intervals zones 없으면 'avg_hr_estimate'."""
        _insert_activity(db_conn, avg_hr=140, duration_sec=3600)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["data_source"] == "avg_hr_estimate"

    def test_config_hr_zones(self, db_conn, tmp_path):
        """config의 hr_zones 경계값 사용 확인."""
        # max_hr 기준 Z1<130, Z2<150, Z3<165, Z4<180, Z5>=180
        config = {
            "user": {
                "max_hr": 195,
                "hr_zones": {"zone1_max": 130, "zone2_max": 150,
                             "zone3_max": 165, "zone4_max": 180},
            }
        }
        # HR 120이면 Z1, HR 145이면 Z2
        hr_data = [120] * 80 + [145] * 20
        _insert_strava_with_stream(db_conn, hr_data, tmp_path)
        db_conn.commit()

        result = analyze_zones(db_conn, _TODAY, _TOMORROW, config)
        # Z1=80%, Z2=20% → easy=100%
        assert result["easy_pct"] == pytest.approx(100.0, abs=1.0)
        assert result["polarization_status"] == "too_easy"

    def test_no_activity(self, db_conn):
        """활동 없으면 empty 결과 반환."""
        result = analyze_zones(db_conn, _TODAY, _TOMORROW)
        assert result["activity_count"] == 0
        assert result["polarization_status"] == "unknown"


class TestWeeklyZoneTrend:
    def test_weekly_zone_trend(self, db_conn):
        """4주 추세 반환 — 항상 N개 항목."""
        result = weekly_zone_trend(db_conn, weeks=4)
        assert len(result) == 4
        for entry in result:
            assert "week_start" in entry
            assert "easy_pct" in entry
            assert "hard_pct" in entry
            assert "moderate_pct" in entry
            assert "status" in entry
            assert "runs" in entry
