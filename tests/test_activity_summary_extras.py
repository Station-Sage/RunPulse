"""activity_summary_extras 단위 테스트."""
import sqlite3

from src.services import activity_summary_extras as ex


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE metric_store (scope_type TEXT, scope_id TEXT, metric_name TEXT, provider TEXT,"
              " numeric_value REAL, text_value TEXT, json_value TEXT)")
    return c


def _splits(paces):
    return [{"pace_sec_km": p, "partial": False} for p in paces]


def test_pace_cv_needs_three_splits():
    assert ex.pace_cv(_splits([300, 300])) is None
    assert ex.pace_cv(_splits([300, 300, 300])) == 0.0
    assert ex.pace_cv(_splits([270, 330, 270, 330])) > 0.05


def test_workout_class_and_environment():
    c = _conn()
    c.execute("INSERT INTO metric_store VALUES ('activity','1','workout_type_classified','runpulse:auto',NULL,'easy',NULL)")
    c.execute("INSERT INTO metric_store VALUES ('activity','1','weather_temp_c','open_meteo',24,NULL,NULL)")
    c.execute("INSERT INTO metric_store VALUES ('activity','1','fearp','runpulse:auto',320,NULL,NULL)")
    core = {"avg_hr": 140, "max_hr": 190, "avg_pace_sec_km": 335}
    wc = ex.build_workout_class(c, [1], core, _splits([335, 335, 335]))
    assert wc["workout_class"] == "easy" and wc["label"] == "이지런"
    assert wc["workout_class_basis"]["hr_pct_max"] == 73.7
    env = ex.build_environment(c, [1], core)
    assert env["temp_c"] == 24 and env["pace_effect_sec_km"] == 15
    assert ex.build_environment(_conn(), [1], core) is None


def test_hr_zones_from_detail_and_device():
    c = _conn()
    assert ex.build_hr_zones(c, [1]) is None
    c.execute("INSERT INTO metric_store VALUES ('activity','1','hr_zones_detail','intervals',NULL,NULL,'[10,20,30,40,50]')")
    assert ex.build_hr_zones(c, [1])["sec"] == [10, 20, 30, 40, 50]
    c2 = _conn()
    for z in range(1, 6):
        c2.execute("INSERT INTO metric_store VALUES ('activity','1',?, 'garmin',?,NULL,NULL)", (f"hr_zone_time_{z}", z * 60))
    assert ex.build_hr_zones(c2, [1])["basis"] == "device_zones"


def test_source_diffs_threshold():
    sc = {"garmin": {"distance_m": 10000, "elevation_gain": 120, "avg_hr": 150},
          "strava": {"distance_m": 10050, "elevation_gain": 95, "avg_hr": 150}}
    rows = {r["row"]: r for r in ex.build_source_diffs(sc)}
    assert rows["distance"]["significant"] is False and rows["distance"]["reason"] is None
    assert rows["elevation"]["significant"] is True and rows["elevation"]["abs"] == 25
    assert ex.build_source_diffs({"garmin": sc["garmin"]}) == []


def test_verdict_text_and_none():
    core = {"avg_pace_sec_km": 335, "avg_hr": 140}
    wc = {"label": "이지런", "workout_class_basis": {"hr_pct_max": 73.7, "pace_cv": 0.02}}
    v = ex.build_verdict(core, wc, [], {"pace_effect_sec_km": 15})
    assert v["text"].startswith("이지런 5:35/km") and "페이스 일정" in v["text"]
    assert len(v["evidence"]) == 3
    assert ex.build_verdict({}, wc, [], None) is None
