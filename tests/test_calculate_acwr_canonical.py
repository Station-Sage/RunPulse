"""calculate_acwr 는 metric_store 의 정식 acwr(EWMA 7/42)를 읽는다 (D1f 통일)."""
import sqlite3
from datetime import date, timedelta

from src.analysis.trends import calculate_acwr


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE metric_store (scope_type TEXT, scope_id TEXT, metric_name TEXT,"
              " numeric_value REAL, is_primary INTEGER)")
    return c


def _put(c, day, val, primary=1):
    c.execute("INSERT INTO metric_store VALUES ('daily',?,'acwr',?,?)", (day, val, primary))


def test_none_when_no_metric():
    assert calculate_acwr(_conn()) is None


def test_latest_primary_value_and_status():
    c = _conn()
    t = date.today()
    _put(c, (t - timedelta(days=2)).isoformat(), 0.7)
    _put(c, (t - timedelta(days=1)).isoformat(), 1.4)
    _put(c, t.isoformat(), 9.9, primary=0)
    _put(c, (t + timedelta(days=1)).isoformat(), 2.0)
    av = calculate_acwr(c)["average"]
    assert av["acwr"] == 1.4 and av["status"] == "caution"
    assert av["date"] == (t - timedelta(days=1)).isoformat()
