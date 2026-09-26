"""P7-PRED-12: Garmin 랩 확장 필드·스트림 키 선택."""
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.garmin_lap_fields import lap_extras, pick
from src.utils.db_helpers import upsert_laps_batch, upsert_streams_batch
from tests.helpers_pred import mem_conn as _conn


def test_lap_extras_drops_none():
    assert lap_extras({"avgGradeAdjustedSpeed": 3.4, "elevationLoss": None, "wktStepIndex": 2}) == \
        {"gap_speed_ms": 3.4, "wkt_step_index": 2}


def test_pick_prefers_first_key_list_and_dict():
    idx = {"sumElapsedDuration": 0, "directElapsedDuration": 1}
    assert pick([12.0, 3.0], idx, ("sumElapsedDuration", "directElapsedDuration")) == 12.0
    assert pick([None, 3.0], idx, ("sumElapsedDuration", "directElapsedDuration")) == 3.0
    assert pick({"directElapsedDuration": 7}, {}, ("sumElapsedDuration", "directElapsedDuration")) == 7


def test_extractor_uses_real_time_axis():
    raw = {"metricDescriptors": [{"key": "sumElapsedDuration", "metricsIndex": 0},
                                 {"key": "directElapsedDuration", "metricsIndex": 1},
                                 {"key": "sumDistance", "metricsIndex": 2},
                                 {"key": "directHeartRate", "metricsIndex": 3}],
           "activityDetailMetrics": [{"metrics": [0.0, 0, 0.0, 120]}, {"metrics": [4.6, 1, 13.0, 121]},
                                     {"metrics": [9.4, 2, 27.1, 122]}]}
    rows = GarminExtractor().extract_activity_streams(raw)
    assert [r["elapsed_sec"] for r in rows] == [0, 5, 9]            # 샘플 인덱스(0,1,2)가 아니라 실제 초
    assert rows[2]["distance_m"] == 27.1


def test_laps_keep_gap_and_step():
    laps = GarminExtractor().extract_activity_laps({"lapDTOs": [
        {"duration": 240.0, "distance": 1000.0, "averageSpeed": 4.17, "intensityType": "INTERVAL",
         "avgGradeAdjustedSpeed": 4.2, "wktStepIndex": 1, "directWorkoutComplianceScore": 88}]})
    assert (laps[0]["gap_speed_ms"], laps[0]["wkt_step_index"], laps[0]["compliance_score"], laps[0]["lap_trigger"]) == \
        (4.2, 1, 88, "INTERVAL")


def test_activity_gap_metric_sec_per_km():
    ms = GarminExtractor().extract_activity_metrics({"avgGradeAdjustedSpeed": 3.137, "calories": 500})
    gap = [m for m in ms if m.metric_name == "gap"]
    assert len(gap) == 1 and gap[0].numeric_value == 318.8
    assert not [m for m in GarminExtractor().extract_activity_metrics({"avgGradeAdjustedSpeed": 0}) if m.metric_name == "gap"]


def test_garmin_lap_extras_preserved():
    splits = {"lapDTOs": [{"distance": 1000.0, "duration": 250.0, "averageSpeed": 4.0, "averageHR": 165,
                           "avgGradeAdjustedSpeed": 4.05, "elevationLoss": 3.0, "averageTemperature": 21.0,
                           "elapsedDuration": 252.0, "movingDuration": 250.0, "directWorkoutComplianceScore": 88.0,
                           "intensityType": "ACTIVE"}]}
    laps = GarminExtractor().extract_activity_laps(splits)
    assert laps[0]["gap_speed_ms"] == 4.05 and laps[0]["compliance_score"] == 88.0
    assert laps[0]["lap_trigger"] == "ACTIVE" and laps[0]["elapsed_duration_sec"] == 252.0
    c = _conn()
    upsert_laps_batch(c, 1, laps)
    row = c.execute("SELECT gap_speed_ms, elevation_loss, avg_temperature_c, compliance_score FROM activity_laps").fetchone()
    assert row == (4.05, 3.0, 21.0, 88.0)


def test_garmin_stream_uses_sum_elapsed_and_distance():
    raw = {"metricDescriptors": [{"key": "sumDistance", "metricsIndex": 0}, {"key": "sumElapsedDuration", "metricsIndex": 1},
                                 {"key": "directHeartRate", "metricsIndex": 2}, {"key": "directGradeAdjustedSpeed", "metricsIndex": 3},
                                 {"key": "directSpeed", "metricsIndex": 4}],
           "activityDetailMetrics": [{"metrics": [0.0, 0.0, 120, 3.0, 3.0]}, {"metrics": [6.1, 2.0, 125, 3.1, 3.05]},
                                     {"metrics": [12.4, 4.0, 130, 3.2, 3.1]}]}
    rows = GarminExtractor().extract_activity_streams(raw)
    assert [r["elapsed_sec"] for r in rows] == [0, 2, 4]
    assert rows[2]["distance_m"] == 12.4 and rows[2]["gap_speed_ms"] == 3.2
    c = _conn()
    upsert_streams_batch(c, 7, rows)
    assert c.execute("SELECT max(elapsed_sec), max(gap_speed_ms) FROM activity_streams").fetchone() == (4, 3.2)
