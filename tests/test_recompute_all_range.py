"""P7-PRED-87: recompute_all 이 재계산 범위 밖 이력을 지우지 않는다."""
from datetime import date, timedelta

from src.metrics.engine import clear_runpulse_metrics, recompute_all
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_run


def test_clear_range_keeps_history():
    c = mem_conn()
    old = seed_run(c, sid="old", date="2025-01-10")
    new = seed_run(c, sid="new", date="2026-09-20")
    for aid in (old, new):
        upsert_metric(c, "activity", str(aid), "trimp", "runpulse:formula_v1", numeric_value=50.0)
    upsert_metric(c, "daily", "2025-01-10", "ctl", "runpulse:formula_v1", numeric_value=30.0)
    upsert_metric(c, "daily", "2026-09-20", "ctl", "runpulse:formula_v1", numeric_value=40.0)
    upsert_metric(c, "daily", "2026-09-20", "garmin_x", "garmin", numeric_value=1.0)
    assert clear_runpulse_metrics(c, "2026-09-01", "2026-09-30") == 2
    left = {(r[0], r[1]) for r in c.execute("SELECT scope_id, metric_name FROM metric_store")}
    assert left == {(str(old), "trimp"), ("2025-01-10", "ctl"), ("2026-09-20", "garmin_x")}


def test_recompute_all_default_spans_all_history():
    c = mem_conn()
    first = (date.today() - timedelta(days=40)).isoformat()
    seed_run(c, sid="a", date=first)
    upsert_metric(c, "daily", "2000-01-01", "ctl", "runpulse:formula_v1", numeric_value=1.0)   # 활동 이전 행은 범위 밖
    res = recompute_all(c)
    assert len(res) == 41
    assert c.execute("SELECT count(*) FROM metric_store WHERE scope_id='2000-01-01'").fetchone()[0] == 1
    assert len(recompute_all(c, days=5)) == 5
