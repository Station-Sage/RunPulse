"""Garmin training_status 중첩 payload 파서 테스트."""
from src.sync.garmin_daily_extensions import _primary_training_status, sync_daily_training_status


def _rec(primary, acute, chronic, status=7):
    return {
        "primaryTrainingDevice": primary, "trainingStatus": status, "fitnessTrend": 2,
        "acuteTrainingLoadDTO": {
            "dailyTrainingLoadAcute": acute, "dailyTrainingLoadChronic": chronic,
            "dailyAcuteChronicWorkloadRatio": 1.1,
        },
    }


def _payload(recs):
    return {"mostRecentTrainingStatus": {"latestTrainingStatusData": recs}}


class FakeClient:
    def __init__(self, data):
        self.data = data

    def get_training_status(self, d):
        return self.data


def _val(conn, name):
    r = conn.execute(
        "SELECT numeric_value FROM metric_store WHERE scope_type='daily' "
        "AND scope_id='2026-10-09' AND metric_name=?", (name,)).fetchone()
    return r[0] if r else None


def test_primary_device_selected():
    data = _payload({"1": _rec(False, 10, 20), "2": _rec(True, 300, 400)})
    assert _primary_training_status(data)["acuteTrainingLoadDTO"]["dailyTrainingLoadAcute"] == 300


def test_falls_back_to_first_and_empty():
    assert _primary_training_status(_payload({"1": _rec(False, 10, 20)}))["trainingStatus"] == 7
    assert _primary_training_status({}) == {}


def test_saves_garmin_loads_not_pmc(db_conn):
    sync_daily_training_status(db_conn, FakeClient(_payload({"2": _rec(True, 300, 400)})), "2026-10-09")
    assert _val(db_conn, "garmin_acute_load") == 300
    assert _val(db_conn, "garmin_chronic_load") == 400
    assert _val(db_conn, "atl") is None and _val(db_conn, "ctl") is None


def test_no_data_is_noop(db_conn):
    sync_daily_training_status(db_conn, FakeClient({}), "2026-10-09")
    assert _val(db_conn, "garmin_acute_load") is None
