"""P7-PRED-25: Garmin 참조값 파서."""
from src.sync.garmin_ref_parsers import parse_lactate_threshold, parse_race_predictions

LT = {"speed_and_heart_rate": {"calendarDate": "2026-05-01T17:56:58.483", "heartRate": 177, "speed": 0.38055449},
      "power": {"calendarDate": "2026-05-01T17:56:58.750", "functionalThresholdPower": 313}}
RP = {"calendarDate": "2026-05-11", "time5K": 1201, "time10K": 2585, "timeHalfMarathon": 5847, "timeMarathon": 12849}


def test_lt_latest_shape():
    assert parse_lactate_threshold(LT, "2026-05-11") == [
        {"date": "2026-05-01", "lthr_ref": 177.0, "lt_speed_ref": 3.8055, "ftp": 313.0}]


def test_lt_history_list_and_garbage():
    assert len(parse_lactate_threshold([LT, LT, "x"], "2026-05-11")) == 2
    assert parse_lactate_threshold({"foo": 1}, "2026-05-11") == []
    assert parse_lactate_threshold(None, "2026-05-11") == []


def test_race_predictions_latest_and_history():
    assert parse_race_predictions(RP, "2026-05-12") == [
        {"date": "2026-05-11", "race_pred_5k_sec": 1201.0, "race_pred_10k_sec": 2585.0,
         "race_pred_half_sec": 5847.0, "race_pred_marathon_sec": 12849.0}]
    h = parse_race_predictions([dict(RP, calendarDate="2026-05-10"), {"calendarDate": "2026-05-09"}], "x")
    assert [x["date"] for x in h] == ["2026-05-10"]
