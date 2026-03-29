"""tests/test_condition_ai_card.py — render_condition_ai_card 단위 테스트."""
import pytest

from src.web.views_training_condition import render_condition_ai_card


def _call(**kwargs) -> str:
    defaults = dict(
        adj=None, utrs_val=None, cirs_val=None,
        cirs_json={}, workouts=[],
    )
    defaults.update(kwargs)
    return render_condition_ai_card(**defaults)


def test_returns_empty_when_no_data():
    html = _call()
    assert html == ""


def test_shows_utrs_badge():
    html = _call(utrs_val=75.0)
    assert "UTRS 75" in html


def test_utrs_green_when_high():
    html = _call(utrs_val=80.0)
    assert "#00ff88" in html


def test_utrs_red_when_low():
    html = _call(utrs_val=30.0)
    assert "#ff4444" in html


def test_cirs_badge_shown():
    html = _call(cirs_val=25.0)
    assert "CIRS 25" in html


def test_cirs_red_border_when_danger():
    html = _call(cirs_val=75.0, utrs_val=60.0)
    assert "border-left:4px solid #ff4444" in html
    assert "⚠️" in html


def test_wellness_badges_from_adj():
    adj = {"wellness": {"body_battery": 60, "sleep_score": 70, "hrv_value": 45}, "tsb": 5.0}
    html = _call(adj=adj, utrs_val=65.0)
    assert "BB 60" in html
    assert "수면 70" in html
    assert "HRV 45" in html
    assert "TSB +5.0" in html


def test_adjustment_section_when_adjusted():
    adj = {
        "adjusted": True,
        "original_type": "interval",
        "adjusted_type": "easy",
        "adjustment_reason": "피로 과부하",
        "wellness": {},
    }
    html = _call(adj=adj)
    assert "인터벌" in html
    assert "이지런" in html
    assert "피로 과부하" in html


def test_no_adjustment_section_when_not_adjusted():
    adj = {"adjusted": False, "fatigue_level": "low", "wellness": {}}
    html = _call(adj=adj, utrs_val=65.0)
    assert "피로도" in html
    assert "낮음" in html


def test_ai_section_shown_with_utrs():
    html = _call(utrs_val=75.0, cirs_val=20.0, cirs_json={})
    assert "AI 훈련 추천" in html
    assert "UTRS 75" in html


def test_ai_override_shown():
    html = _call(utrs_val=60.0, cirs_json={}, ai_override="오늘은 템포런을 권장합니다.")
    assert "오늘은 템포런을 권장합니다." in html
    assert "AI" in html


def test_ai_badge_only_when_override():
    html_no_override = _call(utrs_val=60.0, cirs_json={})
    html_with_override = _call(utrs_val=60.0, cirs_json={}, ai_override="추천")
    # AI 뱃지(테두리 스타일)는 override 시에만
    assert "border:1px solid var(--cyan)" not in html_no_override
    assert "border:1px solid var(--cyan)" in html_with_override


def test_volume_boost_shown_when_applicable():
    adj = {"adjusted": False, "fatigue_level": "low", "volume_boost": True, "wellness": {}}
    html = _call(adj=adj, utrs_val=80.0, cirs_val=20.0, cirs_json={})
    assert "볼륨 부스트" in html


def test_volume_boost_hidden_when_cirs_high():
    adj = {"adjusted": False, "fatigue_level": "low", "volume_boost": True, "wellness": {}}
    html = _call(adj=adj, utrs_val=80.0, cirs_val=55.0, cirs_json={})
    assert "볼륨 부스트" not in html


def test_card_title_present():
    html = _call(utrs_val=60.0)
    assert "오늘 컨디션" in html
    assert "AI 추천" in html
