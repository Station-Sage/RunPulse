"""요일 슬롯 기반 방식 공용 헬퍼 — 엔진이 정한 러닝 요일·주간 총량은 유지하고 요일별 역할만 재배정한다."""
from __future__ import annotations

import json
from datetime import date

from src.training.plan_structure import structure_for_plan

_DN = ["월", "화", "수", "목", "금", "토", "일"]


def run_rows(plan: list[dict]) -> list[dict]:
    return [r for r in plan if r.get("workout_type") not in ("rest", "race") and (r.get("distance_km") or 0) > 0]


def week_total(plan: list[dict]) -> float:
    return round(sum(r["distance_km"] for r in run_rows(plan)), 1)


def iso_parity(week_start) -> int:
    d = date.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    return d.isocalendar()[1] % 2


def share_out(total: float, weights: dict[int, float], caps: dict[int, float], floor: float = 3.0) -> dict[int, float]:
    """total 을 가중치 비율로 나누되 상한(caps)을 넘는 몫은 나머지에 재분배. 합은 (상한 허용 범위에서) total 유지."""
    out = {k: 0.0 for k in weights}
    free = set(weights)
    left = total
    for _ in range(len(weights)):
        w = sum(weights[k] for k in free)
        if not free or w <= 0:
            break
        capped = False
        for k in sorted(free):
            v = left * weights[k] / w
            if v > caps.get(k, 1e9):
                out[k] = caps[k]
                free.discard(k)
                left -= caps[k]
                capped = True
                break
        if not capped:
            for k in free:
                out[k] = left * weights[k] / w
            break
    return {k: max(round(v * 2) / 2, floor) for k, v in out.items()}


def set_row(row: dict, wtype: str, dist: float, desc_tail: str, pace: tuple[int, int] | None, zone: int | None,
            rationale: str, rx: dict | None = None) -> None:
    """한 행을 새 역할로 덮어쓴다. 설명의 km 는 distance_km 와 반드시 같다(finalize 불변식)."""
    day = date.fromisoformat(row["date"]) if isinstance(row["date"], str) else row["date"]
    row["workout_type"] = wtype
    row["distance_km"] = round(dist, 1)
    row["description"] = f"{_DN[day.weekday()]}요일 {dist:.1f}km {desc_tail}"
    row["target_pace_min"], row["target_pace_max"] = pace if pace else (None, None)
    row["target_hr_zone"] = zone
    row["rationale"] = rationale
    row["interval_prescription"] = json.dumps(rx, ensure_ascii=False) if rx else None
    row["structure"] = structure_for_plan(wtype, row["distance_km"], row["target_pace_min"], row["target_pace_max"],
                                          row["interval_prescription"])


def parse_day(v) -> date:
    return date.fromisoformat(v[:10]) if isinstance(v, str) else v


def pick_days(days: list[int], long_wd: int, n: int) -> list[int]:
    """롱런 요일을 뺀 후보에서 n 개를 서로·롱런과 이틀 이상 떨어지게 고른다(불가능하면 가능한 만큼 채움)."""
    mid = [d for d in days if d != long_wd]
    picks: list[int] = []
    for strict in (True, False):
        for d in mid:
            if len(picks) >= n:
                break
            if d in picks:
                continue
            near = [p for p in picks + [long_wd] if abs(p - d) == 1 or {p, d} == {0, 6}]
            if strict and near:
                continue
            picks.append(d)
    return sorted(picks[:n])


def build_week(plan: list[dict], quality: list, long_fn, easy_fn, *, long_weight: float, long_cap: float,
               min_rows: int = 3, rest_after_long=None) -> list[dict] | None:
    """quality=[(km, fn)] 는 고정 거리 품질 세션, 나머지 총량을 롱런·이지가 long_weight 비율로 나눈다.

    fn(row, km) / long_fn(row, km) / easy_fn(row, km) 가 set_row 를 호출한다. 러닝 행이 min_rows 미만이면 None(무변경)."""
    rows = run_rows(plan)
    if len(rows) < min_rows:
        return None
    wd = {parse_day(r["date"]).weekday(): r for r in rows}
    days = sorted(wd)
    long_wd = 6 if 6 in wd else days[-1]
    picks = pick_days(days, long_wd, len(quality))
    total = sum(r["distance_km"] for r in rows)
    fixed = 0.0
    for d, (km, fn) in zip(picks, quality):
        km = max(round(km * 2) / 2, 3.0)
        fn(wd[d], km)
        fixed += km
    rest = [d for d in days if d not in picks]
    weights = {d: (long_weight if d == long_wd else (0.6 if rest_after_long and d == (long_wd + 1) % 7 else 1.0))
               for d in rest}
    km_map = share_out(max(total - fixed, 3.0 * len(rest)), weights, {long_wd: long_cap})
    for d in rest:
        (long_fn if d == long_wd else easy_fn)(wd[d], km_map[d])
    return plan
