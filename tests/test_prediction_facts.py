"""레이스 예측 설명 근거(prediction_facts, ADR-059 D18) — 지표 해석 표면 facts 보강·검증·익명화."""
from __future__ import annotations

import json
import sqlite3

from src.db_setup import create_tables
from src.services import ai_wording as aw
from src.services import metric_interpretation as mi
from src.services.metrics_explain import get_metric_explain
from src.services.prediction_facts import confidence_label

DAY = "2026-10-01"
JS = {"contributions": {"race": 0.62, "work": 0.38}, "signals_s": {"race": 6330, "work": 6420},
      "low_s": 6240, "high_s": 6540, "confidence": 0.52, "reasons": ["기준 대회가 30주 전", "근거 신호 2개"]}


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, json_value, is_primary)"
              " VALUES ('daily', ?, 'race_pred_half_sec', 'runpulse:formula_v1', 6365, ?, 1)", (DAY, json.dumps(JS)))
    c.execute("INSERT INTO goals(name, race_date, distance_km, target_time_sec, status) VALUES"
              " ('무릎 조심 하프', '2026-11-15', 21.0975, 6300, 'active')")
    c.commit()
    return c


def _explain(c):
    return get_metric_explain(c, "daily", DAY, "race_pred_half_sec")


def test_prediction_facts_range_confidence_limiting_gap():
    c = _conn()
    f = mi.build_facts(c, _explain(c))
    assert f["range_fast"] == "1:44:00" and f["range_slow"] == "1:49:00"
    assert f["confidence"] == "보통" and f["limiting"] == "기준 대회가 30주 전, 근거 신호 2개"
    assert f["main_signal"] == "대회 기록" and f["main_signal_weight_pct"] == 60 and f["signal_count"] == 2
    assert f["target_time"] == "1:45:00" and f["gap_to_target"] == "+1:05" and f["gap_direction"] == "목표보다 느림"
    assert "무릎" not in json.dumps(f, ensure_ascii=False)     # 목표 이름은 보내지 않는다


def test_prediction_wording_validates_against_evidence():
    c = _conn()
    it = mi.build_item(c, _explain(c))
    assert it is not None
    basis = json.dumps({k: v for k, v in aw._payload(mi.SURFACE, it).items() if k != "id"}, ensure_ascii=False)
    ok = "목표보다 1:05 느린 예측이에요. 기준 대회가 30주 전이라 범위가 1:44:00~1:49:00 로 넓어요."
    assert aw.validate(mi.SURFACE, basis, ok) == ok
    assert aw.validate(mi.SURFACE, basis, "다음 달엔 1:40:00 까지 줄어요.") is None


def test_non_prediction_slug_has_no_prediction_facts():
    c = _conn()
    c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
              " VALUES ('daily', ?, 'tsb', 'runpulse:formula_v1', -5, 1)", (DAY,))
    assert "range_fast" not in mi.build_facts(c, get_metric_explain(c, "daily", DAY, "tsb"))


def test_confidence_label_matches_frontend():
    assert [confidence_label(v) for v in (None, 0.3, 0.45, 0.7)] == [None, "낮음", "보통", "높음"]


def test_prediction_rule_fallback_when_no_other_rule():
    c = _conn()
    ex = _explain(c)
    assert mi.rule_text(ex) == "모델 범위는 1:44:00~1:49:00, 신뢰도 보통이에요. 제한 요인: 기준 대회가 30주 전."
    assert ex["meaning"]["interpretation"]["source"] == "rule"
