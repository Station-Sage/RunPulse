"""호출 가이드 — 도구 목록과 어긋나지 않는지, 세션 고정 비용이 상한을 넘지 않는지."""
import json
import re
from pathlib import Path

from src.ai.tool_guide import MAX_GUIDE_CHARS, USAGE_GUIDE
from src.ai.tools import TOOL_DECLARATIONS

_SKILL = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "runpulse-data" / "SKILL.md"
_TOOL_NAMES = {t["name"] for t in TOOL_DECLARATIONS}
_TOOL_LIKE = re.compile(r"\b(?:get|compare)_[a-z_]+\b")

# 세션마다 1회 전달되는 고정 비용 상한 (문자 수, 문자수/3 ≈ 토큰). 도구를 늘릴 때 의식적으로 올린다.
_MAX_DECLARATION_CHARS = 5000


def test_guide_within_length_budget():
    assert len(USAGE_GUIDE) <= MAX_GUIDE_CHARS


def test_guide_mentions_every_tool():
    assert [n for n in sorted(_TOOL_NAMES) if n not in USAGE_GUIDE] == []


def test_guide_and_skill_reference_only_real_tools():
    stale = set(_TOOL_LIKE.findall(USAGE_GUIDE)) - _TOOL_NAMES
    stale |= set(_TOOL_LIKE.findall(_SKILL.read_text(encoding="utf-8"))) - _TOOL_NAMES
    assert stale == set()


def test_skill_mentions_every_tool():
    text = _SKILL.read_text(encoding="utf-8")
    assert [n for n in sorted(_TOOL_NAMES) if n not in text] == []


def test_declaration_fixed_cost_budget():
    size = len(json.dumps(TOOL_DECLARATIONS, ensure_ascii=False, separators=(",", ":")))
    assert size <= _MAX_DECLARATION_CHARS, f"{size} chars"
