"""TRIMP 추정 Calculator 테스트 — 심박 결측 러닝의 페이스 기반 부하 추정."""
import sqlite3

from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.trimp import TRIMPCalculator
from src.metrics.trimp_est import TRIMPEstCalculator, fit_hr_from_speed
from src.utils.metric_priority import get_provider_priority


def _conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _add(conn, n, speed, hr, day):
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_speed_ms, avg_hr) VALUES ('garmin', ?, 'r', 'running', ?, ?, 3000, ?, ?)",
        (str(n), f"2026-03-{day:02d} 08:00:00", speed * 3000, speed, hr),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed(conn, n=10):
    for i in range(n):
        s = 2.5 + 0.1 * i
        _add(conn, i, s, 120 + 20 * (s - 2.5) / 0.1 * 0.5, i + 1)


def _ctx(conn, aid):
    return CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))


def test_fit_recovers_line():
    fit = fit_hr_from_speed([(2.0, 120.0), (3.0, 150.0), (4.0, 180.0)])
    assert fit and abs(fit[1] - 30) < 1e-6 and abs(fit[0] - 60) < 1e-6


def test_fit_rejects_flat_or_negative():
    assert fit_hr_from_speed([(3.0, 140.0), (3.0, 150.0)]) is None
    assert fit_hr_from_speed([(2.0, 160.0), (3.0, 140.0)]) is None


def test_estimates_missing_hr_with_low_confidence():
    conn = _conn()
    _seed(conn)
    aid = _add(conn, 99, 3.2, None, 20)
    res = TRIMPEstCalculator().compute(_ctx(conn, aid))
    assert len(res) == 1 and res[0].metric_name == "trimp"
    assert res[0].numeric_value > 0 and res[0].confidence <= 0.5


def test_faster_pace_gives_higher_estimate():
    conn = _conn()
    _seed(conn)
    slow, fast = _add(conn, 98, 2.6, None, 20), _add(conn, 99, 3.3, None, 21)
    a = TRIMPEstCalculator().compute(_ctx(conn, slow))[0].numeric_value
    b = TRIMPEstCalculator().compute(_ctx(conn, fast))[0].numeric_value
    assert b > a


def test_skips_when_hr_measured():
    conn = _conn()
    _seed(conn)
    aid = _add(conn, 99, 3.0, 150, 20)
    assert TRIMPEstCalculator().compute(_ctx(conn, aid)) == []


def test_empty_when_not_enough_history():
    conn = _conn()
    _seed(conn, n=3)
    aid = _add(conn, 99, 3.0, None, 20)
    assert TRIMPEstCalculator().compute(_ctx(conn, aid)) == []


def test_measured_provider_outranks_estimate():
    assert get_provider_priority(TRIMPCalculator.provider) < get_provider_priority(TRIMPEstCalculator.provider)
    assert TRIMPEstCalculator.produces == ["trimp"] and TRIMPEstCalculator.name != TRIMPCalculator.name


def test_store_primary_prefers_measured():
    from src.metrics.engine import _save_results
    conn = _conn()
    _seed(conn)
    aid = _add(conn, 99, 3.0, None, 20)
    est, meas = TRIMPEstCalculator(), TRIMPCalculator()
    _save_results(conn, est, est.compute(_ctx(conn, aid)), str(aid))
    prim = lambda: conn.execute("SELECT provider FROM metric_store WHERE metric_name='trimp'"
                                " AND scope_id=? AND is_primary=1", (str(aid),)).fetchall()
    assert prim() == [(est.provider,)]
    conn.execute("UPDATE activity_summaries SET avg_hr=150 WHERE id=?", (aid,))
    conn.commit()
    _save_results(conn, meas, meas.compute(_ctx(conn, aid)), str(aid))
    assert prim() == [(meas.provider,)]
