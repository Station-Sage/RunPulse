"""ai_parser 모듈 테스트."""
import json
import pytest

from src.ai.ai_parser import (
    extract_json_block,
    parse_ai_chips,
    parse_suggestions,
    parse_weekly_plan,
)


# ── extract_json_block ────────────────────────────────────────────────────────

def test_extract_json_block_from_code_block():
    text = 'some text\n```json\n{"key": "value"}\n```\nmore text'
    result = extract_json_block(text)
    assert result == {"key": "value"}


def test_extract_json_block_bare_code_block():
    text = "```\n{\"a\": 1}\n```"
    result = extract_json_block(text)
    assert result == {"a": 1}


def test_extract_json_block_no_code_block():
    text = 'Here is the data: {"x": 99}'
    result = extract_json_block(text)
    assert result == {"x": 99}


def test_extract_json_block_list():
    text = '```json\n[1, 2, 3]\n```'
    result = extract_json_block(text)
    assert result == [1, 2, 3]


def test_extract_json_block_none_when_invalid():
    text = "no json here"
    result = extract_json_block(text)
    assert result is None


def test_extract_json_block_broken_json():
    text = "```json\n{broken\n```"
    result = extract_json_block(text)
    assert result is None


# ── parse_weekly_plan ─────────────────────────────────────────────────────────

def _make_plan_text(workouts: list[dict], week_start: str = "2026-03-23") -> str:
    data = {"week_start": week_start, "workouts": workouts}
    return f"```json\n{json.dumps(data, ensure_ascii=False)}\n```"


def test_parse_weekly_plan_valid():
    workouts = [
        {"date": "2026-03-23", "type": "easy", "distance_km": 8.0,
         "description": "이지런", "rationale": "회복"},
    ]
    text = _make_plan_text(workouts)
    plan, errors = parse_weekly_plan(text)
    assert errors == []
    assert plan is not None
    assert plan["week_start"] == "2026-03-23"
    assert len(plan["workouts"]) == 1


def test_parse_weekly_plan_no_json():
    plan, errors = parse_weekly_plan("plain text no json")
    assert plan is None
    assert len(errors) > 0


def test_parse_weekly_plan_invalid_type():
    workouts = [{"date": "2026-03-23", "type": "sprint", "distance_km": 5.0}]
    text = _make_plan_text(workouts)
    plan, errors = parse_weekly_plan(text)
    assert plan is None
    assert any("sprint" in e for e in errors)


def test_parse_weekly_plan_missing_date():
    workouts = [{"type": "easy", "distance_km": 5.0}]
    text = _make_plan_text(workouts)
    plan, errors = parse_weekly_plan(text)
    assert plan is None
    assert any("date" in e for e in errors)


def test_parse_weekly_plan_rest_no_distance_ok():
    workouts = [{"date": "2026-03-24", "type": "rest"}]
    text = _make_plan_text(workouts)
    plan, errors = parse_weekly_plan(text)
    assert errors == []


def test_parse_weekly_plan_empty_workouts():
    text = '```json\n{"week_start": "2026-03-23", "workouts": []}\n```'
    plan, errors = parse_weekly_plan(text)
    assert plan is None
    assert any("비어있" in e or "없" in e for e in errors)


# ── parse_suggestions ─────────────────────────────────────────────────────────

def test_parse_suggestions_string_list():
    text = '```json\n{"suggestions": ["칩1", "칩2", "칩3"]}\n```'
    result = parse_suggestions(text)
    assert result == ["칩1", "칩2", "칩3"]


def test_parse_suggestions_dict_list():
    data = {"suggestions": [{"label": "A"}, {"label": "B"}]}
    text = f'```json\n{json.dumps(data)}\n```'
    result = parse_suggestions(text)
    assert result == ["A", "B"]


def test_parse_suggestions_max_5():
    data = {"suggestions": [f"칩{i}" for i in range(10)]}
    text = f'```json\n{json.dumps(data)}\n```'
    result = parse_suggestions(text)
    assert len(result) == 5


def test_parse_suggestions_no_json():
    result = parse_suggestions("AI 응답 텍스트만 있고 JSON 없음")
    assert result == []


# ── parse_ai_chips ────────────────────────────────────────────────────────────

def test_parse_ai_chips_basic():
    data = {"suggestions": ["오늘 훈련 분석", "이번 주 리뷰"]}
    text = f'```json\n{json.dumps(data)}\n```'
    chips = parse_ai_chips(text)
    assert len(chips) == 2
    assert chips[0]["label"] == "오늘 훈련 분석"
    assert "id" in chips[0]


def test_parse_ai_chips_with_id():
    data = {"chips": [{"id": "today_deep", "label": "심층 분석"}]}
    text = f'```json\n{json.dumps(data)}\n```'
    chips = parse_ai_chips(text)
    assert chips[0]["id"] == "today_deep"


def test_parse_ai_chips_empty_on_failure():
    chips = parse_ai_chips("no json")
    assert chips == []
