"""Phase 7 Story 서비스 — 월/주/블록 단위 훈련 내러티브 조회.

설계 문서: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/40-v2-unimplemented/design.md §2.8
          v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D3 scope 일반화)

스코프별 데이터 조회 및 규칙 기반 문단 생성. AI 생성은 기존 narrative 캐시/체인 재사용.
장애 시 규칙 fallback 필수.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from src.services.story_period import (
    _get_block_dates, _month_date_range, _parse_period, _week_date_range, week_neighbors,
)
from src.services.story_compare import compare_basis
from src.services.story_stats import (
    _get_ctl_range, _get_intensity_distribution, _get_key_sessions,
    _get_period_activity_stats, _get_risk_peak,
)


def _rule_narrative_month(
    distance_km: float,
    count: int,
    ctl_start: float | None,
    ctl_end: float | None,
) -> str:
    """월별 규칙 기반 한 문단 내러티브."""
    parts: list[str] = []

    if count > 0:
        parts.append(f"{distance_km}km를 {count}회 훈련했습니다.")
    else:
        return "이 기간 훈련 기록이 아직 없습니다."

    if ctl_start is not None and ctl_end is not None:
        diff = ctl_end - ctl_start
        if diff > 2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_end:.0f}로 꾸준히 높아졌습니다.")
        elif diff < -2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_end:.0f}로 줄었습니다.")
        else:
            parts.append(f"훈련 부하(CTL)가 {ctl_end:.0f}으로 안정적으로 유지됐습니다.")

    return " ".join(parts)


def _rule_narrative_week(
    distance_km: float,
    count: int,
    ctl_start: float | None,
    ctl_end: float | None,
) -> str:
    """주별 규칙 기반 한 문단 내러티브."""
    parts: list[str] = []

    if count > 0:
        parts.append(f"이번 주 {distance_km}km, {count}회를 훈련했습니다.")
    else:
        return "이 기간 훈련 기록이 아직 없습니다."

    if ctl_start is not None and ctl_end is not None:
        diff = ctl_end - ctl_start
        if diff > 1:
            parts.append(f"체력(CTL)이 {ctl_start:.1f}→{ctl_end:.1f}로 증가했습니다.")
        elif diff < -1:
            parts.append(f"체력(CTL)이 {ctl_start:.1f}→{ctl_end:.1f}로 감소했습니다.")

    return " ".join(parts)


def get_story(
    conn: sqlite3.Connection,
    period: str,
    config: dict | None = None,
) -> dict[str, Any]:
    """훈련 이야기 조회 — 월/주/블록 일반화.

    Args:
        conn: SQLite 연결
        period: '2026-09' | '2026-W39' | 'b-<planId>-<phase>'
        config: AI 설정(선택)

    Returns: {period, paragraph, chips, compare, intensity, key_sessions, risk_peak, milestones}
    또는 ValueError 발생(잘못된 period).
    """
    parsed = _parse_period(period)
    scope = parsed["scope"]

    if scope == "month":
        year, month = parsed["year"], parsed["month"]
        start_date, end_date = _month_date_range(year, month)
        period_label = f"{year}년 {month}월"

    elif scope == "week":
        year, week = parsed["year"], parsed["week"]
        start_date, end_date = _week_date_range(year, week)
        period_label = f"{year}년 {week}주"

    else:  # block
        plan_id, phase_name = parsed["plan_id"], parsed["phase"]
        try:
            start_date, end_date = _get_block_dates(conn, plan_id, phase_name)
            period_label = f"{phase_name} 블록"
        except NotImplementedError:
            raise ValueError(f"Block scope not yet implemented: {period}")

    # ── 기본 통계 ────────────────────────────────────────────────────────
    stats = _get_period_activity_stats(conn, start_date, end_date)
    ctl_data = _get_ctl_range(conn, start_date, end_date)
    intensity = _get_intensity_distribution(conn, start_date, end_date)
    key_sessions = _get_key_sessions(conn, start_date, end_date)
    risk_peak = _get_risk_peak(conn, start_date, end_date)

    # ── 한 문단 내러티브 (규칙 기반, AI fallback은 나중) ────────────────
    if scope == "month":
        paragraph = _rule_narrative_month(
            stats["distance_km"],
            stats["count"],
            ctl_data["ctl_start"],
            ctl_data["ctl_end"],
        )
    else:  # week
        paragraph = _rule_narrative_week(
            stats["distance_km"],
            stats["count"],
            ctl_data["ctl_start"],
            ctl_data["ctl_end"],
        )

    # ── 칩 데이터 (드릴 참조 포함) ──────────────────────────────────────
    chips = []
    if ctl_data.get("ctl_end") is not None:
        chips.append({
            "label": f"CTL {ctl_data['ctl_end']:.1f}",
            "value": ctl_data["ctl_end"],
            "drill": {"scope_type": "daily", "scope_id": end_date, "metric": "ctl"},
        })
    chips += [
        {
            "label": f"{period_label} {stats['distance_km']}km",
            "value": stats["distance_km"],
            "drill": None,
        },
        {
            "label": f"최장 {stats['longest_run_km']}km",
            "value": stats["longest_run_km"],
            "drill": None,
        },
    ]

    # ── 이전 동일 단위 비교 ──────────────────────────────────────────────
    if scope == "month":
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_start, prev_end = _month_date_range(prev_year, prev_month)
    else:  # week — 달력 연도와 ISO 주차를 섞지 않는다(M-01: 연말 경계)
        if scope == "week":
            wy, ww = year, week
        else:  # block — 시작일이 속한 주(일요일 시작이면 다음 날 월요일) 기준
            iso = (date.fromisoformat(start_date) + timedelta(days=1)).isocalendar()
            wy, ww = iso[0], iso[1]
        prev_week_id, next_week_id = week_neighbors(wy, ww)
        prev_y, prev_w = (int(x) for x in prev_week_id.split("-W"))
        prev_start, prev_end = _week_date_range(prev_y, prev_w)

    # 진행 중인 기간은 이전 기간도 같은 일수까지만 비교한다(M-14: 10월 1~11일 vs 9월 전체 방지).
    today = date.today().isoformat()
    is_future = start_date > today
    basis = compare_basis(scope, start_date, end_date, prev_start, prev_end, today)
    prev_end = basis["prev_end"]
    prev_stats = _get_period_activity_stats(conn, prev_start, prev_end)
    compare = [
        {
            "key": "distance",
            "label": "거리",
            "value": stats["distance_km"],
            "prev": prev_stats["distance_km"],
            "delta_pct": round(
                100 * (stats["distance_km"] - prev_stats["distance_km"]) / max(prev_stats["distance_km"], 0.1)
            ) if prev_stats["distance_km"] > 0 else 0,
        },
        {
            "key": "count",
            "label": "횟수",
            "value": stats["count"],
            "prev": prev_stats["count"],
            "delta_pct": round(
                100 * (stats["count"] - prev_stats["count"]) / max(prev_stats["count"], 1)
            ) if prev_stats["count"] > 0 else 0,
        },
    ]

    # ── 이전/다음 기간 네비게이션 ──────────────────────────────────────────
    if scope == "month":
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        prev_period = f"{prev_year}-{prev_month:02d}"
        next_period = f"{next_year}-{next_month:02d}" if f"{next_year}-{next_month:02d}-01" <= today else None
    else:  # week — 아직 시작하지 않은 다음 주는 링크하지 않는다(월 모드와 같은 규칙)
        next_y, next_w = (int(x) for x in next_week_id.split("-W"))
        prev_period = prev_week_id
        next_period = next_week_id if _week_date_range(next_y, next_w)[0] <= today else None

    # ── 마일스톤 (조회 중인 기간 내) ─────────────────────────────────────
    from src.services import milestone_service
    milestones = milestone_service.get_recent_milestones(
        conn, limit=5, date_from=start_date, date_to=end_date
    )

    return {
        "period": {
            "id": period,
            "label": period_label,
            "start": start_date,
            "end": end_date,
            "prev": prev_period,
            "next": next_period,
        },
        "paragraph": paragraph,
        "chips": chips,
        "compare": [] if is_future else compare,
        "compare_basis": basis["label"],
        "is_future": is_future,
        "intensity": intensity,
        "key_sessions": key_sessions,
        "risk_peak": risk_peak,
        "milestones": milestones,
    }
