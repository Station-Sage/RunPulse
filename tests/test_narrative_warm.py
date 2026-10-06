"""tests/test_narrative_warm.py — 내러티브 워밍 가드·반환값 검증."""
from __future__ import annotations

from unittest.mock import patch

from src.services import narrative_warm as nw

TODAY = "2026-09-22"


def _run(conn, ai=True, **kw):
    out = {"source": "ai" if ai else "rule"}
    with patch("src.services.today_service.get_today_narrative", return_value=out) as m:
        return nw.warm_month_narrative(conn, TODAY, consent_ok=kw.get("consent", True)), m


def test_no_consent_skips_llm(db_conn):
    r, m = _run(db_conn, consent=False)
    assert r == "no_consent" and not m.called


def test_warmed_and_counts_call(db_conn):
    r, _ = _run(db_conn)
    assert r == "warmed" and nw._calls_today(db_conn, TODAY) == 1


def test_rule_fallback_is_failed(db_conn):
    r, _ = _run(db_conn, ai=False)
    assert r == "failed"


def test_exception_is_failed_and_no_cache_row(db_conn):
    with patch("src.services.today_service.get_today_narrative", side_effect=RuntimeError("x")):
        assert nw.warm_month_narrative(db_conn, TODAY, consent_ok=True) == "failed"
    assert db_conn.execute("SELECT COUNT(*) FROM ai_cache WHERE tab='today_narrative'").fetchone()[0] == 0


def test_capped_after_daily_limit(db_conn):
    nw._bump_calls(db_conn, TODAY, nw.WARM_DAILY_CAP)
    r, m = _run(db_conn)
    assert r == "capped" and not m.called


def test_fresh_cache_skips(db_conn):
    with patch("src.services.narrative_warm.get_narrative_cache", return_value={"text": "x"}):
        r, m = _run(db_conn)
    assert r == "fresh" and not m.called
