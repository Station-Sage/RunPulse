"""웰니스 원값 근거(wellness_facts, ADR-059 D18) — 지표 해석·회복 인사이트 facts 포함, 건강 일반화 유지."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.db_setup import create_tables
from src.services import ai_wording as aw
from src.services import insight_evidence as ev
from src.services import metric_interpretation as mi
from src.services.metrics_explain import get_metric_explain
from src.services.wellness_facts import wellness_facts

DAY = "2026-04-01"


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    d0 = date.fromisoformat(DAY)
    for i in range(1, 31):   # 지난 30일: 수면 7시간·스트레스 30·안정시 심박 50·HRV 60
        c.execute("INSERT INTO daily_wellness(date, sleep_duration_sec, sleep_score, avg_stress, resting_hr,"
                  " hrv_last_night, body_battery_high) VALUES (?, 25200, 80, 30, 50, 60, 90)",
                  ((d0 - timedelta(days=i)).isoformat(),))
    c.execute("INSERT INTO daily_wellness(date, sleep_duration_sec, sleep_score, avg_stress, resting_hr,"
              " hrv_last_night, body_battery_high) VALUES (?, 18360, 55, 48, 57, 41, 62)", (DAY,))
    for name, v in (("tsb", -13.5), ("ctl", 42.3), ("utrs", 40.0)):
        c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                  " VALUES ('daily', ?, ?, 'runpulse:formula_v1', ?, 1)", (DAY, name, v))
    c.commit()
    return c


def test_day_values_and_own_averages():
    f = wellness_facts(_conn(), DAY)
    assert f["sleep_hours"] == 5.1 and f["sleep_hours_avg_7d"] == 7.0 and f["sleep_hours_avg_90d"] == 7.0
    assert f["stress"] == 48 and f["stress_avg_7d"] == 30
    assert f["resting_hr"] == 57 and f["hrv"] == 41 and f["hrv_avg_90d"] == 60
    assert f["sleep_score"] == 55 and f["body_battery_max"] == 62


def test_missing_day_or_short_history():
    c = _conn()
    assert wellness_facts(c, "2026-05-01") == {}
    c.execute("DELETE FROM daily_wellness WHERE date < '2026-03-30'")   # 표본 2일 → 평균 생략
    f = wellness_facts(c, DAY)
    assert "sleep_hours_avg_7d" not in f and f["sleep_hours"] == 5.1


def test_metric_interp_recovery_slugs_include_wellness():
    c = _conn()
    tsb = mi.build_item(c, get_metric_explain(c, "daily", DAY, "tsb")).facts
    assert tsb["sleep_hours"] == 5.1 and tsb["hrv_avg_7d"] == 60
    ctl = mi.build_facts(c, get_metric_explain(c, "daily", DAY, "ctl"))
    assert "sleep_hours" not in ctl   # 부하 누적 지표에는 웰니스를 붙이지 않는다


def test_wellness_numbers_pass_validation_and_health_terms_still_rejected():
    c = _conn()
    it = mi.build_item(c, get_metric_explain(c, "daily", DAY, "tsb"))
    basis = json.dumps(aw._payload(mi.SURFACE, it), ensure_ascii=False)
    ok = "수면이 5.1시간으로 평소 7시간보다 짧고 HRV 도 41로 평소 60보다 낮아요. 오늘은 회복을 먼저 챙겨요."
    assert aw.validate(mi.SURFACE, basis, ok) == ok
    assert aw.validate(mi.SURFACE, basis, "수면 5.1시간, 감기 기운일 수 있어요.") is None


def test_recovery_insight_facts_include_wellness_but_pain_flag_none():
    c = _conn()
    f = ev.evidence_facts(c, "recovery_low", [], DAY)
    assert f["sleep_hours"] == 5.1 and f["stress"] == 48 and f["tsb"] == -13.5
    assert ev.evidence_facts(c, "load_spike", [], DAY).get("sleep_hours") is None
    assert ev.evidence_facts(c, "pain_flag", [{"signal": "injury", "value": 2}], DAY) == {}
