"""P7-PRED-25: Garmin 참조값 동기화(가짜 클라이언트)."""
from src.sync.garmin_ref_sync import backfill_history, sync_lactate_threshold, sync_race_predictions
from tests.helpers_pred import mem_conn
from tests.test_garmin_ref_parsers import LT, RP


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail

    def get_lactate_threshold(self, latest=True, start_date=None, end_date=None, aggregation="daily"):
        if self.fail:
            raise RuntimeError("401")
        return LT if latest else [LT]

    def get_race_predictions(self, startdate=None, enddate=None, _type=None):
        if self.fail:
            raise RuntimeError("401")
        return RP if startdate is None else [dict(RP, calendarDate="2026-05-10"), RP]


def _val(c, name, day):
    r = c.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name=? "
                  "AND provider='garmin'", (day, name)).fetchone()
    return r and r[0]


def test_snapshots():
    c = mem_conn()
    assert sync_lactate_threshold(c, FakeClient(), "2026-05-11") == 3
    assert _val(c, "lthr_ref", "2026-05-01") == 177.0 and _val(c, "lt_speed_ref", "2026-05-01") == 3.8055
    assert sync_race_predictions(c, FakeClient(), "2026-05-11") == 4
    assert _val(c, "race_pred_5k_sec", "2026-05-11") == 1201.0


def test_history_and_failure():
    c = mem_conn()
    assert backfill_history(c, FakeClient(), "2026-05-01", "2026-05-11") == {"race_parsed": 8, "lt_parsed": 3}
    assert _val(c, "race_pred_10k_sec", "2026-05-10") == 2585.0
    assert sync_race_predictions(c, FakeClient(fail=True), "2026-05-11") == 0
    assert backfill_history(c, FakeClient(fail=True), "2026-05-01", "2026-05-11") == {"race_parsed": 0, "lt_parsed": 0}
