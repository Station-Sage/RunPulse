"""activity_deep.py 테스트."""

import json
import pytest
from datetime import date, timedelta

from src.analysis.activity_deep import deep_analyze


_TODAY = date.today().isoformat()
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _insert_activity(conn, source="garmin", start_time=None, distance_km=10.0,
                     duration_sec=3600, avg_hr=150, max_hr=175,
                     avg_cadence=180, elevation_gain=50.0, calories=500,
                     matched_group_id=None):
    """테스트용 활동 삽입."""
    if start_time is None:
        start_time = _TODAY + "T08:00:00"
    cur = conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, activity_type, start_time, distance_km, duration_sec, "
        "avg_pace_sec_km, avg_hr, max_hr, avg_cadence, elevation_gain, calories, "
        "matched_group_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, f"{source}_{start_time}", "running", start_time,
         distance_km, duration_sec, round(duration_sec / distance_km),
         avg_hr, max_hr, avg_cadence, elevation_gain, calories, matched_group_id),
    )
    return cur.lastrowid


def _add_garmin_metrics(conn, act_id, te_aerobic=3.2, te_anaerobic=1.5,
                         training_load=120.0, vo2max=48.5):
    """Garmin source_metrics 삽입."""
    for name, val in [
        ("training_effect_aerobic", te_aerobic),
        ("training_effect_anaerobic", te_anaerobic),
        ("training_load", training_load),
        ("vo2max", vo2max),
    ]:
        if val is not None:
            conn.execute(
                "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) "
                "VALUES (?, 'garmin', ?, ?)", (act_id, name, val)
            )


def _add_intervals_metrics(conn, act_id, tl=95.0, hrss=80.0, intensity=0.75):
    """Intervals source_metrics 삽입."""
    for name, val in [
        ("icu_training_load", tl),
        ("icu_hrss", hrss),
        ("icu_intensity", intensity),
    ]:
        conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) "
            "VALUES (?, 'intervals', ?, ?)", (act_id, name, val)
        )


def _add_runalyze_metrics(conn, act_id, evo2max=49.0, vdot=45.0, trimp=80.0,
                           marathon_shape=85.0, race_pred=None):
    """Runalyze source_metrics 삽입."""
    for name, val in [
        ("effective_vo2max", evo2max),
        ("vdot", vdot),
        ("trimp", trimp),
        ("marathon_shape", marathon_shape),
    ]:
        if val is not None:
            conn.execute(
                "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) "
                "VALUES (?, 'runalyze', ?, ?)", (act_id, name, val)
            )
    if race_pred:
        conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
            "VALUES (?, 'runalyze', 'race_prediction', ?)",
            (act_id, json.dumps(race_pred)),
        )


def _add_strava_metrics(conn, act_id, suffer_score=120.0, stream_path=None,
                         best_efforts=None):
    """Strava source_metrics 삽입."""
    if suffer_score is not None:
        conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) "
            "VALUES (?, 'strava', 'relative_effort', ?)", (act_id, suffer_score)
        )
    if stream_path:
        conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
            "VALUES (?, 'strava', 'stream_file', ?)", (act_id, stream_path)
        )
    if best_efforts:
        conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_json) "
            "VALUES (?, 'strava', 'best_efforts', ?)",
            (act_id, json.dumps(best_efforts)),
        )


def _make_stream_file(tmp_path, n=120, v=3.0, hr=150, suffix="") -> str:
    """간단한 stream JSON 파일 생성."""
    data = {
        "time": list(range(n)),
        "distance": [i * v for i in range(n)],
        "heartrate": [hr] * n,
        "velocity_smooth": [v] * n,
    }
    p = tmp_path / f"stream{suffix}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


class TestDeepAnalyze:
    def test_deep_full_4sources(self, db_conn, tmp_path):
        """4소스 모두 있는 경우 전체 필드 반환."""
        group_id = "grp_full_test"
        gid = _insert_activity(db_conn, "garmin", matched_group_id=group_id)
        sid = _insert_activity(db_conn, "strava", matched_group_id=group_id)
        iid = _insert_activity(db_conn, "intervals", matched_group_id=group_id)
        rid = _insert_activity(db_conn, "runalyze", matched_group_id=group_id)

        _add_garmin_metrics(db_conn, gid)
        _add_strava_metrics(db_conn, sid, stream_path=_make_stream_file(tmp_path, suffix="_full"))
        _add_intervals_metrics(db_conn, iid)
        _add_runalyze_metrics(db_conn, rid, race_pred={"5k": 1200, "10k": 2520})
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        assert result["garmin"]["training_effect_aerobic"] == pytest.approx(3.2)
        assert result["strava"]["suffer_score"] == pytest.approx(120.0)
        assert result["intervals"]["icu_training_load"] == pytest.approx(95.0)
        assert result["runalyze"]["effective_vo2max"] == pytest.approx(49.0)
        assert result["runalyze"]["race_predictions"] == {"5k": 1200, "10k": 2520}

    def test_deep_garmin_only(self, db_conn):
        """Garmin 데이터만 있어도 정상 동작, 나머지 None."""
        gid = _insert_activity(db_conn, "garmin")
        _add_garmin_metrics(db_conn, gid)
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        assert result["garmin"]["training_effect_aerobic"] is not None
        assert result["strava"]["suffer_score"] is None
        assert result["intervals"]["icu_training_load"] is None
        assert result["runalyze"]["effective_vo2max"] is None

    def test_deep_partial_2sources(self, db_conn):
        """2소스만 있으면 나머지 소스 필드 None."""
        group_id = "grp_partial"
        gid = _insert_activity(db_conn, "garmin", matched_group_id=group_id)
        iid = _insert_activity(db_conn, "intervals", matched_group_id=group_id)
        _add_garmin_metrics(db_conn, gid)
        _add_intervals_metrics(db_conn, iid)
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        assert result["garmin"]["training_load"] is not None
        assert result["intervals"]["icu_hrss"] is not None
        assert result["strava"]["suffer_score"] is None
        assert result["runalyze"]["vdot"] is None

    def test_deep_by_activity_id(self, db_conn):
        """activity_id로 조회."""
        gid = _insert_activity(db_conn, "garmin")
        db_conn.commit()
        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        assert result["activity"]["distance_km"] == pytest.approx(10.0)

    def test_deep_by_date(self, db_conn):
        """date로 조회 — 해당 날짜의 가장 최근 활동."""
        _insert_activity(db_conn, "garmin")
        db_conn.commit()
        result = deep_analyze(db_conn, date=_TODAY)
        assert result is not None
        assert result["activity"]["date"] == _TODAY

    def test_deep_today_default(self, db_conn):
        """파라미터 없으면 오늘 날짜 활동 반환."""
        _insert_activity(db_conn, "garmin")
        db_conn.commit()
        result = deep_analyze(db_conn)
        assert result is not None
        assert result["activity"]["date"] == _TODAY

    def test_deep_no_activity(self, db_conn):
        """활동 없으면 None 반환."""
        result = deep_analyze(db_conn)
        assert result is None

    def test_pace_splits_calculation(self, db_conn, tmp_path):
        """1km 단위 pace splits 정확도 검증."""
        sid = _insert_activity(db_conn, "strava")
        # 3km 스트림: 매 1km 마다 정확히 300초 (5:00/km)
        n = 301
        data = {
            "time": list(range(n)),         # 0~300초
            "distance": [i * 10.0 for i in range(n)],  # 0~3000m
            "heartrate": [148] * n,
            "velocity_smooth": [10.0] * n,
        }
        stream_file = tmp_path / "stream_splits.json"
        stream_file.write_text(json.dumps(data), encoding="utf-8")
        _add_strava_metrics(db_conn, sid, stream_path=str(stream_file))
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=sid)
        assert result is not None
        splits = result["strava"]["pace_splits"]
        assert splits is not None
        assert len(splits) == 3
        for split in splits:
            assert split["pace_sec"] == pytest.approx(100, abs=2)  # 10m/s = 100s/km

    def test_pace_splits_no_stream(self, db_conn):
        """stream 없으면 pace_splits None."""
        sid = _insert_activity(db_conn, "strava")
        db_conn.commit()
        result = deep_analyze(db_conn, activity_id=sid)
        assert result is not None
        assert result["strava"]["pace_splits"] is None

    def test_fitness_context_from_daily_fitness(self, db_conn):
        """daily_fitness 데이터가 fitness_context에 반영됨."""
        gid = _insert_activity(db_conn, "garmin")
        db_conn.execute(
            "INSERT INTO daily_fitness (date, source, ctl, atl, tsb, garmin_vo2max) "
            "VALUES (?, 'intervals', ?, ?, ?, ?)",
            (_TODAY, 55.0, 62.0, -7.0, 48.5),
        )
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        fc = result["fitness_context"]
        assert fc["ctl"] == pytest.approx(55.0)
        assert fc["atl"] == pytest.approx(62.0)
        assert fc["tsb"] == pytest.approx(-7.0)

    def test_recovery_context_from_wellness(self, db_conn):
        """daily_wellness 데이터가 recovery_context에 반영됨."""
        gid = _insert_activity(db_conn, "garmin")
        db_conn.execute(
            "INSERT INTO daily_wellness "
            "(date, source, sleep_score, sleep_hours, hrv_value, resting_hr, "
            "body_battery, stress_avg) VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)",
            (_TODAY, 85.0, 7.5, 45.0, 52, 80, 35),
        )
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=gid)
        assert result is not None
        rc = result["recovery_context"]
        assert rc["sleep_score"] == pytest.approx(85.0)
        assert rc["sleep_hours"] == pytest.approx(7.5)
        assert rc["hrv_value"] == pytest.approx(45.0)
        assert rc["body_battery"] == 80
        assert rc["stress_level"] == 35
        assert rc["resting_hr"] == 52

    def test_calculated_efficiency_included(self, db_conn, tmp_path):
        """calculate_efficiency 결과가 calculated.efficiency에 포함."""
        sid = _insert_activity(db_conn, "strava")
        stream_path = _make_stream_file(tmp_path, n=120, v=3.0, hr=150, suffix="_eff")
        _add_strava_metrics(db_conn, sid, stream_path=stream_path)
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=sid)
        assert result is not None
        eff = result["calculated"]["efficiency"]
        assert eff is not None
        assert "decoupling_pct" in eff
        assert "status" in eff

    def test_calculated_zones_included(self, db_conn, tmp_path):
        """analyze_zones 결과가 calculated.zones에 포함."""
        sid = _insert_activity(db_conn, "strava")
        hr_data = [140] * 80 + [160] * 20
        stream_file = tmp_path / "stream_zones.json"
        stream_file.write_text(json.dumps({
            "heartrate": hr_data,
            "velocity_smooth": [3.0] * len(hr_data),
            "time": list(range(len(hr_data))),
            "distance": [i * 3.0 for i in range(len(hr_data))],
        }), encoding="utf-8")
        _add_strava_metrics(db_conn, sid, stream_path=str(stream_file))
        db_conn.commit()

        result = deep_analyze(db_conn, activity_id=sid)
        assert result is not None
        zones = result["calculated"]["zones"]
        assert zones is not None
        assert "zone_distribution" in zones
        assert "polarization_status" in zones
