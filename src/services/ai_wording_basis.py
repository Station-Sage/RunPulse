"""AI 다듬기 재생성 기준(src_hash 근거) — 항목이 선언한 사실만, 반올림해서 해시한다 (ADR-059 D15~D17).

- 현재형 표면(오늘 이유·이야기·지표 해석): 기본 근거 = 반올림한 facts + 규칙 문구(facts 로 설명되는 숫자는 가림) + 항목이
  덧붙인 의존(deps, 예: 그 기간 활동 서명). 미세한 수치 변화(거리 0.1km·페이스 5초·비율 0.05 미만)로는 재생성하지 않는다.
- 스냅샷형 표면(이 러닝의 의미): 항목이 basis 를 직접 선언 — 그 활동 자신의 데이터만(`wording_deps.activity_signature`).
  이후 CTL/TSB 변동처럼 활동 밖의 변화는 해시에 들어가지 않는다.
facts 는 AI 로 보내는 근거이고 basis 는 해시 전용이다(AI 로 보내지 않음 — 메모 해시 같은 값도 들어갈 수 있다).
"""
from __future__ import annotations

import re

_NUM = re.compile(r"\d+(?:\.\d+)?")
_PACE = re.compile(r"(\d+):(\d\d)(?::(\d\d))?")
RATIO_KEYS = ("acwr", "ratio", "monotony")
STEP_PACE_SEC = 5
STEP_RATIO = 0.05
STEP_PCT = 5           # 퍼센트 값은 5%p(= 비율 0.05)


def _bucket(v: float, step: float) -> float:
    return round(round(v / step) * step, 2)


def _q_time_str(s: str) -> str:
    """'5:31/km'·'1:45:32' 같은 시간 문자열을 5초 단위로."""
    def sub(m: re.Match) -> str:
        if m.group(3) is not None:
            sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            sec = int(_bucket(sec, STEP_PACE_SEC))
            return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
        sec = int(_bucket(int(m.group(1)) * 60 + int(m.group(2)), STEP_PACE_SEC))
        return f"{sec // 60}:{sec % 60:02d}"
    return _PACE.sub(sub, s)


def quantize_value(key: str, v):
    """한 값의 해시용 반올림. 정수·불리언은 그대로(횟수·일수·등급)."""
    k = key.lower()
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, str):
        return _q_time_str(v)
    if isinstance(v, int):
        return v
    if not isinstance(v, float):
        return v
    if "km" in k or "distance" in k:
        return round(v, 1)
    if "pace" in k or k.endswith("_sec"):
        return _bucket(v, STEP_PACE_SEC)
    if any(r in k for r in RATIO_KEYS):
        return _bucket(v, STEP_RATIO)
    if k.endswith("_pct") or k.startswith("pct"):
        return _bucket(v, STEP_PCT)
    return int(round(v)) if abs(v) >= 10 else round(v, 1)


def quantize(facts: dict) -> dict:
    return {k: quantize_value(k, v) for k, v in (facts or {}).items()}


def _covered(facts: dict) -> set[str]:
    """facts 가 설명하는 숫자(원값과 그 반올림 0·1자리)."""
    from src.services.ai_wording import _norm
    out: set[str] = set()
    for v in facts.values():
        for n in _NUM.findall(str(v)):
            out.add(_norm(n))
            if "." in n:
                f = float(n)
                out |= {_norm(f"{f:.1f}"), str(int(round(f)))}
    return out


def default_basis(rule_text: str, facts: dict | None, deps: dict | None = None) -> dict:
    """현재형 표면의 해시 근거 — 규칙 문구의 숫자 중 facts 가 설명하는 것은 가리고(반올림된 facts 로 대신 추적),
    설명되지 않는 숫자는 그대로 둔다(그 숫자가 바뀌면 재생성)."""
    from src.services.ai_wording import _norm
    cov = _covered(facts or {})
    masked = _NUM.sub(lambda m: "#" if _norm(m.group(0)) in cov else m.group(0), rule_text or "")
    out = {"rule": masked, "facts": quantize(facts or {})}
    if deps:
        out["deps"] = deps
    return out
