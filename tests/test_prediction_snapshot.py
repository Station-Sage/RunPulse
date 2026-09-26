"""P7-PRED-63: 예측 스냅샷 기록·중복 억제·대회 전향 평가·요약."""
import json

from src.services import prediction_snapshot_service as ps
from src.services.race_result_service import confirm
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_run


def _pred(c, day, provider, sec, variant=None):
    js = {"low_s": sec - 60, "high_s": sec + 60, "confidence": 0.8, "contributions": {"race": 1.0}}
    if variant:
        js["variant"] = variant
    upsert_metric(c, "daily", day, "race_pred_10k_sec", provider, numeric_value=sec, json_value=js)


def test_record_only_today_and_dedupe():
    c = mem_conn()
    _pred(c, "2026-09-20", "runpulse:formula_v1", 2700)
    assert ps.record_snapshots(c, "2026-09-21") == 0          # 그날 값 없음(과거 값 재사용 안 함)
    _pred(c, "2026-09-21", "runpulse:formula_v1", 2700)
    _pred(c, "2026-09-21", "runpulse:shadow_r4", 2760, "base")
    assert ps.record_snapshots(c, "2026-09-21") == 2
    _pred(c, "2026-09-22", "runpulse:formula_v1", 2700)
    assert ps.record_snapshots(c, "2026-09-22") == 0          # 값 같고 7일 안 → 생략
    _pred(c, "2026-09-23", "runpulse:formula_v1", 2690)
    assert ps.record_snapshots(c, "2026-09-23") == 1
    row = c.execute("SELECT variant, low_s, inputs_json FROM prediction_snapshots WHERE provider='runpulse:shadow_r4'").fetchone()
    assert row[0] == "base" and row[1] == 2700 and json.loads(row[2])["contributions"] == {"race": 1.0}


def test_garmin_uses_recent_value_only():
    c = mem_conn()
    _pred(c, "2026-09-01", "garmin", 2600)
    assert ps.record_snapshots(c, "2026-09-10") == 1
    c2 = mem_conn()
    _pred(c2, "2026-08-01", "garmin", 2600)
    assert ps.record_snapshots(c2, "2026-09-10") == 0          # 14일 넘은 Garmin 값은 스냅샷하지 않음


def test_evaluate_on_confirm():
    c = mem_conn()
    for d, sec in (("2026-08-29", 2760), ("2026-09-20", 2730), ("2026-09-27", 2720)):
        _pred(c, d, "runpulse:formula_v1", sec)
        ps.record_snapshots(c, d)
    c.execute("INSERT INTO daily_wellness (date, sleep_score, hrv_last_night) VALUES ('2026-09-27', 70, 60)")
    rid = seed_run(c, sid="r", date="2026-09-27", name="가을 10K 대회", dist=10000.0, moving=2700, elapsed=2705)
    confirm(c, rid, "allout", official_time_sec=2700)
    rows = c.execute("SELECT horizon_days, pred_s, actual_s, residual_pct, covariates_json FROM prediction_snapshots "
                     "WHERE race_activity_id=? ORDER BY horizon_days", (rid,)).fetchall()
    assert [r[0] for r in rows] == [0, 7, 28] and [r[1] for r in rows] == [2720, 2730, 2760]
    assert rows[0][2] == 2700 and abs(rows[0][3] - (2720 / 2700 - 1) * 100) < 0.01
    assert json.loads(rows[0][4])["sleep_score"] == 70
    s = ps.summary(c)
    assert [x["horizon_days"] for x in s] == [0, 7, 28] and s[0]["hit80"] == 1 and s[0]["n"] == 1


def test_not_allout_not_evaluated():
    c = mem_conn()
    _pred(c, "2026-09-27", "runpulse:formula_v1", 2720)
    ps.record_snapshots(c, "2026-09-27")
    rid = seed_run(c, sid="r", date="2026-09-27", name="펀런 10K 대회", dist=10000.0, moving=3000)
    confirm(c, rid, "fun")
    assert c.execute("SELECT count(*) FROM prediction_snapshots WHERE actual_s IS NOT NULL").fetchone()[0] == 0
