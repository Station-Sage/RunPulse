"""도구 응답 압축 헬퍼 — 호출당 토큰 사용량 절감.

- columnar(): 키를 행마다 반복하지 않는 {"fields", "rows"} 형태. 전부 NULL인 컬럼은 제거.
- num(): 정수값 float(84.0)은 int로, 나머지는 반올림 (불필요한 자릿수 제거).
- resolve_granularity(): 긴 기간은 일별 대신 주별 롤업으로 자동 전환.
- weekly_*(): 주별 롤업. 주 시작은 기본 일요일(마라톤 플랜 주차 기준).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable

from src.utils.pace import seconds_to_pace

AUTO_WEEKLY_OVER_DAYS = 62   # granularity=auto 일 때 이 일수를 넘으면 주별
MAX_DAILY_DAYS = 180         # granularity=day 를 명시해도 이 일수를 넘으면 주별
DEFAULT_WEEK_START = "sun"

WEEKLY_ACTIVITY_FIELDS = ["week", "runs", "km", "min", "pace", "hr", "long_km"]


def num(value, ndigits: int = 0):
    """반올림. 정수값이면 int로 내려 '84.0' 대신 '84'를 출력한다."""
    if value is None:
        return None
    rounded = round(float(value), ndigits)
    return int(rounded) if rounded == int(rounded) else rounded


def columnar(fields: list[str], rows: list[list]) -> dict:
    """{"fields": [...], "rows": [[...]]}. 모든 행에서 NULL인 컬럼은 헤더째 제거."""
    keep = [i for i in range(len(fields)) if any(r[i] is not None for r in rows)]
    return {
        "fields": [fields[i] for i in keep],
        "rows": [[r[i] for i in keep] for r in rows],
    }


def span_days(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days + 1


def resolve_granularity(requested: Any, span: int) -> tuple[str, str | None]:
    """(granularity, note). requested: 'auto'|'day'|'week' (그 외는 auto)."""
    if requested == "week":
        return "week", None
    if requested == "day":
        if span > MAX_DAILY_DAYS:
            return "week", f"{MAX_DAILY_DAYS}일 초과 구간은 주별로 제공"
        return "day", None
    return ("week" if span > AUTO_WEEKLY_OVER_DAYS else "day"), None


def week_start_of(day: str, first: str = DEFAULT_WEEK_START) -> str:
    d = date.fromisoformat(day[:10])
    offset = d.weekday() if first == "mon" else (d.weekday() + 1) % 7
    return (d - timedelta(days=offset)).isoformat()


def group_by_week(items: list, day_of: Callable[[Any], str], first: str) -> dict[str, list]:
    """주 시작일 → 항목 목록 (입력 순서 유지)."""
    groups: dict[str, list] = defaultdict(list)
    for item in items:
        groups[week_start_of(day_of(item), first)].append(item)
    return groups


def weekly_activity_rows(acts: list[tuple], first: str,
                         span: tuple[str, str] | None = None) -> list[list]:
    """acts: (date, km, sec, avg_hr) → 주별 [week, runs, km, min, pace, hr, long_km].

    pace는 총시간/총거리, hr은 시간 가중 평균 (단순 평균은 짧은 조깅에 왜곡됨).
    span=(start, end) 이면 러닝이 없던 주도 runs=0 행으로 채운다 — 공백 주(휴식·부상)가
    표에서 사라지면 훈련 단절을 읽을 수 없다.
    """
    groups = group_by_week(acts, lambda a: a[0], first)
    weeks = list(groups)
    if span:
        weeks, cur = [], date.fromisoformat(week_start_of(span[0], first))
        last = date.fromisoformat(week_start_of(span[1], first))
        while cur <= last:
            weeks.append(cur.isoformat())
            cur += timedelta(days=7)
    out = []
    for week in weeks:
        items = groups.get(week)
        if not items:
            out.append([week, 0, 0, 0, None, None, 0])
            continue
        km = sum(a[1] or 0 for a in items)
        sec = sum(a[2] or 0 for a in items)
        hr_pairs = [(a[3], a[2]) for a in items if a[3] and a[2]]
        hr_secs = sum(s for _, s in hr_pairs)
        hr = sum(h * s for h, s in hr_pairs) / hr_secs if hr_secs else None
        out.append([
            week, len(items), num(km, 1), round(sec / 60),
            seconds_to_pace(int(sec / km)) if km else None,
            num(hr), num(max((a[1] or 0) for a in items), 1),
        ])
    return out


def weekly_mean(rows: list[list], digits: list[int], first: str) -> list[list]:
    """rows: [date, v1, v2, ...] → 주별 [week, n, mean1, mean2, ...] (n=값이 있는 일수)."""
    out = []
    for week, items in group_by_week(rows, lambda r: r[0], first).items():
        means = []
        for i, nd in enumerate(digits, start=1):
            vals = [r[i] for r in items if r[i] is not None]
            means.append(num(sum(vals) / len(vals), nd) if vals else None)
        out.append([week, len(items), *means])
    return out


def weekly_last(rows: list[list], first: str) -> list[list]:
    """rows: [date, v1, ...] → 주별 [week, last1, ...] (주 마지막 유효값 — CTL 등 상태값용)."""
    out = []
    for week, items in group_by_week(rows, lambda r: r[0], first).items():
        last = []
        for i in range(1, len(items[0])):
            vals = [r[i] for r in items if r[i] is not None]
            last.append(vals[-1] if vals else None)
        out.append([week, *last])
    return out
