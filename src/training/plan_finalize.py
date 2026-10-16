"""주간 계획 최종 정합화(PLN-4) — 변형이 모두 끝난 뒤 행 불변식을 검사하고 자동 보정한다.

불변식: 휴식 행은 거리 0, 설명의 km 가 거리 컬럼과 같음, 달리는 요일은 지정한 운동 요일의 부분집합.
위반은 보정 후 로그만 남기고 생성·저장은 막지 않는다. 보정은 요일·휴식 거리에 한정한다(설명 km 불일치·롱런 비중은 week_violations 로 보고만).
"""
from __future__ import annotations

import logging
import re
from datetime import date

from .planner_rules import description

log = logging.getLogger(__name__)

LONG_SHARE_MAX = 0.5
_KM_RE = re.compile(r"(\d+(?:\.\d+)?)km")
_FREE = ("rest", "race")


def _km(r: dict) -> float:
    return float(r.get("distance_km") or 0.0)


def week_violations(rows: list[dict], run_weekdays) -> list[str]:
    """불변식 위반 목록(빈 리스트면 정상). 행은 수정하지 않는다."""
    days = set(run_weekdays)
    out: list[str] = []
    total = sum(_km(r) for r in rows if r["workout_type"] != "race")
    for r in rows:
        t, d = r["workout_type"], r["date"]
        if t == "rest" and _km(r) > 0:
            out.append(f"{d}: 휴식인데 거리 {_km(r)}km")
        if t not in _FREE and date.fromisoformat(d).weekday() not in days:
            out.append(f"{d}: 지정하지 않은 요일에 {t}")
        m = _KM_RE.search(r.get("description") or "")
        if t != "race" and m and abs(float(m.group(1)) - _km(r)) > 0.1:
            out.append(f"{d}: 설명 {m.group(1)}km ≠ 거리 {_km(r)}km")
        if t == "long" and total > 0 and _km(r) > total * LONG_SHARE_MAX + 1e-9:
            out.append(f"{d}: 롱런이 주간의 {LONG_SHARE_MAX:.0%} 초과")
    return out


def finalize_week(rows: list[dict], *, run_weekdays) -> list[dict]:
    """요일·휴식 거리 위반 행만 보정해 반환(제자리 수정). 그 외 행의 설명·구조는 건드리지 않는다. race 행은 그대로."""
    days = set(run_weekdays)
    fixed: list[str] = []
    for r in rows:
        t = r["workout_type"]
        if t == "race":
            continue
        day = date.fromisoformat(r["date"])
        changed = False
        if t != "rest" and day.weekday() not in days:
            r.update(workout_type="rest", target_pace_min=None, target_pace_max=None,
                     target_hr_zone=None, interval_prescription=None, rationale="")
            t, changed = "rest", True
            fixed.append(f"{r['date']}: 지정하지 않은 요일의 운동을 휴식으로")
        if t == "rest" and (changed or _km(r) > 0):
            if not changed:
                fixed.append(f"{r['date']}: 휴식 거리 {_km(r)}km 를 0 으로")
            r["distance_km"] = 0.0
            r["structure"] = None
            r["description"] = description("rest", None, day)
    if fixed:
        log.warning("주간 계획 불변식 위반 %d건 자동 보정: %s", len(fixed), "; ".join(fixed))
    return rows
