"""PMC 오늘 부분일 처리 + 오늘 메트릭 지연 갱신 테스트."""
import sqlite3
from datetime import date, datetime, timedelta

from src.db_setup import create_tables
from src.metrics import pmc
from src.metrics.base import CalcContext
from src.metrics.pmc import PMCCalculator, elapsed_day_fraction
from src.metrics.today_refresh import refresh_today_if_stale
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _seed_run(conn, day: date, trimp: float, sid: str):
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, moving_time_sec, avg_hr, max_hr) VALUES (?,?,?,?,?,?,?,?,?)",
        ["garmin", sid, "Run", "running", f"{day.isoformat()} 08:00:00", 10000, 3000, 155, 185],
    )
    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    upsert_metric(conn, "activity", str(aid), "trimp", "runpulse:formula_v1",
                  numeric_value=trimp, category="rp_load")


def _seed_history(conn, today: date, days: int = 50):
    for i in range(1, days):
        _seed_run(conn, today - timedelta(days=i), 100.0, f"h{i}")
    conn.commit()


def _val(results, name):
    return next(r.numeric_value for r in results if r.metric_name == name)


def test_elapsed_day_fraction():
    noon = datetime(2026, 9, 25, 12, 0, 0)
    assert elapsed_day_fraction("2026-09-25", noon) == 0.5
    assert elapsed_day_fraction("2026-09-24", noon) == 1.0  # 과거 날짜는 하루 전체
    assert elapsed_day_fraction("2026-09-25", datetime(2026, 9, 25, 0, 0, 0)) == 0.0


def test_today_rest_decay_is_prorated(monkeypatch):
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today.isoformat())

    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 1.0)
    full_day = PMCCalculator().compute(ctx)
    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 0.02)
    just_after_midnight = PMCCalculator().compute(ctx)

    # 하루를 통째로 휴식 가정하면 ATL이 더 많이 감쇠 → TSB 상승. 자정 직후엔 어제 값에 가깝다.
    assert _val(just_after_midnight, "atl") > _val(full_day, "atl")
    assert _val(just_after_midnight, "tsb") < _val(full_day, "tsb")


def test_today_actual_load_counts_fully(monkeypatch):
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today.isoformat())
    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 0.3)
    rest = _val(PMCCalculator().compute(ctx), "atl")
    _seed_run(conn, today, 150.0, "today")
    conn.commit()
    ran = _val(PMCCalculator().compute(ctx), "atl")
    assert ran > rest  # 오늘 이미 한 운동은 시각과 무관하게 전부 반영


def test_refresh_today_if_stale():
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    assert refresh_today_if_stale(conn) is True  # 오늘 행 없음 → 계산
    row = conn.execute(
        "SELECT 1 FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name='tsb'",
        (today.isoformat(),),
    ).fetchone()
    assert row is not None
    assert refresh_today_if_stale(conn) is False  # 방금 계산 → 신선
    conn.execute("UPDATE metric_store SET updated_at = datetime('now', '-2 hours')"
                 " WHERE scope_type='daily' AND scope_id=?", (today.isoformat(),))
    conn.commit()
    assert refresh_today_if_stale(conn) is True  # 오래됨 → 재계산
