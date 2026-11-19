"""get_metrics / get_metrics_trend 메트릭 이름 대소문자 무시 + 빈 결과 안내."""
import sqlite3
from datetime import date

import pytest

from src.ai.tool_exec_context import _exec_get_metrics, _exec_get_metrics_trend
from src.db_setup import create_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, is_primary, provider)"
              " VALUES ('daily', ?, 'cirs', 25.4, 1, 'runpulse')", (date.today().isoformat(),))
    return c


def test_get_metrics_uppercase_names(conn):
    out = _exec_get_metrics(conn, {"date": date.today().isoformat(), "metric_names": ["CIRS", "ACWR"]})
    assert out["metrics"] == {"cirs": 25.4}


def test_get_metrics_empty_has_note(conn):
    out = _exec_get_metrics(conn, {"date": "2000-01-01", "metric_names": ["cirs"]})
    assert out["metrics"] == {} and "소문자" in out["note"]


def test_trend_uppercase_name(conn):
    out = _exec_get_metrics_trend(conn, {"metric_name": "CIRS", "days": 5})
    assert out["rows"] and "note" not in out


def test_trend_empty_has_note(conn):
    out = _exec_get_metrics_trend(conn, {"metric_name": "nope", "days": 5})
    assert "값이 없다" in out["note"]


def test_llm_followups_excludes_current_chip(conn):
    from src.ai.chat_engine import llm_followups
    chips = llm_followups(conn, "오늘 뭐 할까", "today_advice")
    assert chips and "today_advice" not in chips and len(chips) <= 3
