"""지표 행동 힌트(규칙) + ACWR 저부하·휴식기 밴드. 정적 힌트의 AI 다듬기(metric_note)는 폐지(ADR-059 2단계)."""
import inspect

from src.services import metric_display
from src.services.metric_display import action_hint, band_key


def test_band_key_acwr_low_and_layoff():
    assert band_key("acwr", "caution", 0.6) == "low"
    assert band_key("acwr", "caution", 0.1) == "layoff"
    assert band_key("acwr", "caution", 1.4) == "caution"
    assert band_key("cirs", "good", 0.1) == "good"


def test_action_hint_layoff_text_differs_from_overload():
    assert "휴식기" in action_hint("acwr", "caution", value=0.05)
    assert "줄이세요" in action_hint("acwr", "caution", value=1.4)


def test_action_hint_is_rule_only():
    """metric_note 캐시 경로 제거 — 힌트는 항상 규칙 문구(conn 인자 없음)."""
    assert "conn" not in inspect.signature(action_hint).parameters
    assert "metric_notes" not in inspect.getsource(metric_display)
