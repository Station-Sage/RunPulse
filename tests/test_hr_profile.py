"""P7-PRED-24: HR 프로필 자체 추정 + 참조값."""
import json

from src.metrics.base import CalcContext
from src.metrics.hr_profile import HRProfileCalculator, race_second_part_hr
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def _race(c, sid, date, hr_series, dist=10000.0, avg_hr=175, max_hr=192):
    aid = seed_run(c, sid=sid, date=date, name="양천 마라톤 10k", dist=dist, moving=2676, avg_hr=avg_hr, max_hr=max_hr, event_type="race")
    seed_laps(c, aid, [(1000, 268, h, None, None, h + 3) for h in hr_series])
    return aid


def test_second_part_hr():
    laps = [{"dur_s": 100, "hr": h} for h in (140, 150, 170, 180, 180, 180)]
    assert race_second_part_hr(laps) == 177.5


def test_self_profile_from_race():
    c = mem_conn()
    _race(c, "r1", "2026-04-11", [158, 163, 167, 177, 180, 179, 186, 188, 192, 191])
    seed_run(c, sid="x", date="2026-04-20", max_hr=190, avg_hr=150)
    for d in ("2026-04-01", "2026-04-02", "2026-04-03"):
        c.execute("INSERT INTO daily_wellness (date, resting_hr) VALUES (?, 43)", (d,))
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-04-25")
    res = {r.metric_name: r for r in HRProfileCalculator().compute(ctx)}
    data = json.loads(res["hr_profile"].json_value)
    assert data["self"]["hrmax"] == 190.0            # 192(대회), 190 → 두 번째
    assert data["self"]["lthr_source"] == "races"
    assert res["lthr_self"].numeric_value == round(0.98 * (180 + 179 + 186 + 188 + 192 + 191 + 177) / 7, 1)
    assert data["ref"] is None


def test_fallback_and_ref():
    c = mem_conn()
    seed_run(c, sid="a", date="2026-09-01", max_hr=192)
    seed_run(c, sid="b", date="2026-09-02", max_hr=190)
    upsert_metric(c, "daily", "2026-05-01", "lthr_ref", "garmin", numeric_value=177.0)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")
    data = json.loads({r.metric_name: r for r in HRProfileCalculator().compute(ctx)}["hr_profile"].json_value)
    assert data["self"]["lthr"] == 174.2 and data["self"]["lthr_source"] == "hrmax_ratio"
    assert data["ref"] == {"source": "garmin", "lthr": 177.0, "hrmax": None} and data["lthr_gap"] == -2.8
    assert data["zones"]["ref"]["lthr"][3] == [168.2, 177.0] or tuple(data["zones"]["ref"]["lthr"][3]) == (168.2, 177.0)
