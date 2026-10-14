"""RMR Calculator 단위 테스트 — 신뢰도(ADR-050 F2)."""
import sqlite3

import pytest

from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.rmr import RMRCalculator
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn


def _run(conn, d="2026-04-01"):
    return RMRCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id=d))


def _wellness(conn, **cols):
    cols = {"date": "2026-04-01", **cols}
    conn.execute(f"INSERT INTO daily_wellness ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                 list(cols.values()))


def test_all_inputs_confidence_one():
    conn = _conn()
    _wellness(conn, resting_hr=55, body_battery_high=80, sleep_score=85)
    upsert_metric(conn, "daily", "2026-04-01", "tsb", "runpulse:formula_v1", numeric_value=5.0)
    r = _run(conn)[0]
    assert r.confidence == pytest.approx(1.0)
    assert RMRCalculator.version == "1.1"


def test_tsb_only_confidence_quarter():
    conn = _conn()
    _wellness(conn)
    upsert_metric(conn, "daily", "2026-04-01", "tsb", "runpulse:formula_v1", numeric_value=5.0)
    assert _run(conn)[0].confidence == pytest.approx(0.25)


def test_no_inputs_no_row():
    conn = _conn()
    _wellness(conn)
    assert _run(conn) == []
