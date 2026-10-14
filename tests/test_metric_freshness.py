"""metric_freshness 단위 테스트 (ADR-050 F1)."""
import json

import pytest

from src.services import metric_freshness as mf
from src.services.metric_freshness_spec import FRESHNESS_SPEC

DAY = "2026-10-10"


def _well(conn, date, **cols):
    keys = ["date", *cols]
    conn.execute(f"INSERT INTO daily_wellness ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})",
                 [date, *cols.values()])


def _metric(conn, name, value=50.0, date=DAY, conf=0.9, ver="1.1", js=None):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value,"
        " json_value, algorithm_version, confidence, is_primary) VALUES ('daily',?,?,?,?,?,?,?,1)",
        (date, name, "runpulse:formula_v1", value, json.dumps(js) if js is not None else None, ver, conf))


def _row(conn, name):
    conn.row_factory = None
    cur = conn.execute("SELECT * FROM metric_store WHERE metric_name=?", (name,))
    cols = [d[0] for d in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


def _setup(conn, wdate=DAY, tsb=True):
    _well(conn, wdate, body_battery_high=80, sleep_score=80, hrv_weekly_avg=60, avg_stress=30, resting_hr=50)
    if tsb:
        _metric(conn, "tsb", 5)


UTRS_ALL = {"components": {"body_battery": 1, "tsb": 1, "sleep": 1, "hrv": 1, "stress": 1}}


def test_missing_row(db_conn):
    fr = mf.assess(db_conn, "utrs", DAY, None)
    assert fr["level"] == "missing" and not fr["assertive"]


def test_fresh(db_conn):
    _setup(db_conn)
    _metric(db_conn, "utrs", js=UTRS_ALL)
    fr = mf.assess(db_conn, "utrs", DAY, _row(db_conn, "utrs"))
    assert fr["level"] == "fresh" and fr["assertive"] and fr["badge"] is None
    assert fr["inputs"]["wellness"]["days"] == 0


def test_stale_by_age(db_conn):
    _setup(db_conn, wdate="2026-10-07")
    _metric(db_conn, "utrs", js=UTRS_ALL)
    fr = mf.assess(db_conn, "utrs", DAY, _row(db_conn, "utrs"))
    assert fr["level"] == "stale" and fr["badge"]["text"] == "입력이 오래됐어요"
    assert any(r["code"] == "wellness_stale" and r["days"] == 3 for r in fr["reasons"])


def test_one_day_old_is_still_fresh(db_conn):
    _setup(db_conn, wdate="2026-10-09")
    _metric(db_conn, "utrs", js=UTRS_ALL)
    assert mf.assess(db_conn, "utrs", DAY, _row(db_conn, "utrs"))["level"] == "fresh"


def test_partial_low_confidence_and_missing_inputs(db_conn):
    _setup(db_conn)
    _metric(db_conn, "utrs", conf=0.25, js={"components": {"tsb": 1}})
    fr = mf.assess(db_conn, "utrs", DAY, _row(db_conn, "utrs"))
    assert fr["level"] == "partial" and not fr["assertive"]
    assert set(fr["missing_inputs"]) == {"body_battery_high", "sleep_score", "hrv_weekly_avg", "avg_stress"}
    assert fr["badge"]["text"] == "일부 데이터 없이 계산"


def test_metric_missing_makes_partial(db_conn):
    _setup(db_conn, tsb=False)
    _metric(db_conn, "utrs", js=UTRS_ALL)
    fr = mf.assess(db_conn, "utrs", DAY, _row(db_conn, "utrs"))
    assert fr["level"] == "partial" and any(r["code"] == "metric_missing" for r in fr["reasons"])


def test_rtti_modifier_never_stale_by_age(db_conn):
    _setup(db_conn, wdate="2026-10-01")
    _metric(db_conn, "atl", 40)
    _metric(db_conn, "ctl", 50)
    _metric(db_conn, "rtti", js={"wellness_used": ["body_battery_high", "sleep_score"]})
    fr = mf.assess(db_conn, "rtti", DAY, _row(db_conn, "rtti"))
    assert fr["level"] == "fresh"


def test_rtti_empty_wellness_used_is_partial(db_conn):
    _setup(db_conn)
    _metric(db_conn, "atl", 40)
    _metric(db_conn, "ctl", 50)
    _metric(db_conn, "rtti", js={"wellness_used": []})
    fr = mf.assess(db_conn, "rtti", DAY, _row(db_conn, "rtti"))
    assert fr["level"] == "partial" and any(r["code"] == "modifier_missing" for r in fr["reasons"])


def test_old_version_coverage_unknown(db_conn):
    _setup(db_conn)
    _metric(db_conn, "atl", 40)
    _metric(db_conn, "ctl", 50)
    _metric(db_conn, "rtti", ver="1.0", js={"wellness_used": ["sleep_score"]})
    fr = mf.assess(db_conn, "rtti", DAY, _row(db_conn, "rtti"))
    assert fr["coverage"] is None and any(r["code"] == "coverage_unknown" for r in fr["reasons"])


def _crs_setup(conn, signals, ver="1.1", utrs_conf=0.9, utrs_js=UTRS_ALL):
    _setup(conn)
    for n in ("acwr", "cirs"):
        _metric(conn, n, 1)
    _metric(conn, "utrs", conf=utrs_conf, js=utrs_js)
    _metric(conn, "crs", ver=ver, js={"signals": signals})


FULL_SIG = {"body_battery": 80, "hrv_today": 60, "hrv_rolling_days": 5}


def test_crs_fresh(db_conn):
    _crs_setup(db_conn, FULL_SIG)
    assert mf.assess(db_conn, "crs", DAY, _row(db_conn, "crs"))["level"] == "fresh"


def test_crs_gate_unknown_when_signal_null(db_conn):
    _crs_setup(db_conn, {**FULL_SIG, "hrv_today": None})
    fr = mf.assess(db_conn, "crs", DAY, _row(db_conn, "crs"))
    assert fr["level"] == "partial" and fr["unknown_gates"] == ["hrv_weekly_avg"]


def test_crs_upstream_worse_wins(db_conn):
    _crs_setup(db_conn, FULL_SIG, utrs_conf=0.25, utrs_js={"components": {"tsb": 1}})
    fr = mf.assess(db_conn, "crs", DAY, _row(db_conn, "crs"))
    assert fr["level"] == "partial" and any(r["code"] == "upstream" for r in fr["reasons"])


def test_assess_many_fixed_query_count(db_conn):
    _crs_setup(db_conn, FULL_SIG)
    rows = {n: _row(db_conn, n) for n in ("utrs", "crs")}
    stmts = []
    db_conn.set_trace_callback(stmts.append)
    out = mf.assess_many(db_conn, ["utrs", "crs"], DAY, rows)
    db_conn.set_trace_callback(None)
    assert len([s for s in stmts if s.lstrip().upper().startswith("SELECT")]) == 2
    assert out["crs"]["level"] == "fresh"


def test_boost_hold_fresh_releases(db_conn):
    _crs_setup(db_conn, FULL_SIG)
    assert mf.crs_boost_hold(db_conn, DAY) == {"hold": False, "reasons": []}


def test_boost_hold_missing_crs(db_conn):
    _setup(db_conn)
    h = mf.crs_boost_hold(db_conn, DAY)
    assert h["hold"] and h["reasons"][0]["code"] == "crs_missing"


def test_boost_hold_stale(db_conn):
    _crs_setup(db_conn, FULL_SIG)
    db_conn.execute("UPDATE daily_wellness SET date='2026-10-05'")
    h = mf.crs_boost_hold(db_conn, DAY)
    assert h["hold"] and h["reasons"][0]["code"] == "crs_stale"


def test_boost_hold_short_hrv_history(db_conn):
    _crs_setup(db_conn, {**FULL_SIG, "hrv_rolling_days": 2})
    h = mf.crs_boost_hold(db_conn, DAY)
    assert h["hold"] and h["reasons"][0]["code"] == "gate_unknown"


def test_boost_hold_old_row_without_key_is_hold(db_conn):
    _crs_setup(db_conn, {"body_battery": 80, "hrv_today": 60}, ver="1.0")
    assert mf.crs_boost_hold(db_conn, DAY)["hold"]


def test_boost_hold_text():
    assert "보류" in mf.boost_hold_text("crs_stale")


def test_spec_shape():
    for name, s in FRESHNESS_SPEC.items():
        assert s["wellness_role"] in ("component", "modifier", "gate"), name
        assert s["wellness"] and s["metrics"], name
