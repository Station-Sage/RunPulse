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


# 실측 이력 응답 형태(2026-09-26): 리스트가 아니라 시리즈별 dict
LT_HIST = {
    "speed": [{"from": "2026-01-04", "until": "2026-01-04", "series": "running", "value": 0.37222, "updatedDate": "2026-01-04"},
              {"from": "2026-01-24", "until": "2026-01-24", "series": "running", "value": 0.36111, "updatedDate": "2026-01-24"}],
    "heart_rate": [{"from": "2026-01-04", "until": "2026-01-04", "series": "running", "value": 171.0, "updatedDate": "2026-01-04"},
                   {"from": "2026-01-24", "until": "2026-01-24", "series": "running", "value": 169.0, "updatedDate": "2026-01-24"}],
    "power": [{"from": "2026-01-24", "until": "2026-01-24", "series": "running", "value": 281.0, "updatedDate": "2026-01-24"},
              {"from": "2026-01-25", "until": "2026-01-25", "series": "cycling", "value": 999.0, "updatedDate": "2026-01-25"}],
}


def test_lt_history_dict_shape():
    got = parse_lactate_threshold(LT_HIST, "2026-09-26")
    assert got == [
        {"date": "2026-01-04", "lthr_ref": 171.0, "lt_speed_ref": 3.7222, "ftp": None},
        {"date": "2026-01-24", "lthr_ref": 169.0, "lt_speed_ref": 3.6111, "ftp": 281.0}]  # cycling 시리즈는 제외
