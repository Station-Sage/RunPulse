"""Phase 7 Story 서비스 — 월/주/블록 단위 훈련 내러티브 조회.

설계 문서: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/40-v2-unimplemented/design.md §2.8
          v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D3 scope 일반화)

스코프별 데이터 조회 및 rule-based 여름 문단 생성. AI 생성은 기존 narrative 캐시/체인 재사용.
장애 시 규칙 fallback 필수.
"""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta
from typing import Any


def _parse_period(period: str) -> dict[str, Any]:
    """기간 문자열 파싱 — 2026-09 | 2026-W39 | b-<planId>-<phase>.

    Returns: {scope, year?, month?, week?, plan_id?, phase?}
    또는 ValueError 발생.
    """
    if period.startswith("b-"):
        parts = period[2:].split("-", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid block period: {period}")
        return {"scope": "block", "plan_id": parts[0], "phase": parts[1]}

    if "-W" in period:
        parts = period.split("-W")
        if len(parts) != 2:
            raise ValueError(f"Invalid week period: {period}")
        try:
            year = int(parts[0])
            week = int(parts[1])
            return {"scope": "week", "year": year, "week": week}
        except ValueError:
            raise ValueError(f"Invalid week period: {period}")

    if len(period) == 7 and period[4] == "-":
        try:
            year = int(period[:4])
            month = int(period[5:7])
            return {"scope": "month", "year": year, "month": month}
        except ValueError:
            raise ValueError(f"Invalid month period: {period}")

    raise ValueError(f"Invalid period format: {period}")


def _month_date_range(year: int, month: int) -> tuple[str, str]:
    """월 범위 계산 — 시작일, 종료일.

    현재 달이면 오늘까지, 과거 달이면 말일까지.
    """
    month_start = f"{year}-{month:02d}-01"
    today = date.today()
    if year == today.year and month == today.month:
        return month_start, today.isoformat()
    last_day = calendar.monthrange(year, month)[1]
    return month_start, f"{year}-{month:02d}-{last_day:02d}"


def _week_date_range(year: int, week: int) -> tuple[str, str]:
    """ISO주차 범위 계산 — 일요일 시작으로 조정.

    Returns: (일요일, 토요일)
    """
    from datetime import datetime, timedelta
    jan_4 = date(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.isoweekday() - 1)
    target_start = week_1_start + timedelta(weeks=week - 1)
    target_start_sunday = target_start - timedelta(days=(target_start.weekday() + 1) % 7)
    target_end_saturday = target_start_sunday + timedelta(days=6)
    return target_start_sunday.isoformat(), target_end_saturday.isoformat()


def _get_period_activity_stats(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """기간 내 러닝 활동 통계 — 거리, 횟수, 강도 분포, 대표 세션 등.

    v_canonical_activities만 집계(중복 제거됨).
    """
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_m), 0), COALESCE(MAX(distance_m), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?""",
        (start_date, end_date),
    ).fetchone()

    count = int(row[0]) if row else 0
    distance_m = float(row[1]) if row and row[1] else 0.0
    distance_km = round(distance_m / 1000.0, 1)
    longest_run_km = round(float(row[2]) / 1000.0, 1) if row and row[2] else 0.0

    return {
        "count": count,
        "distance_km": distance_km,
        "longest_run_km": longest_run_km,
    }


def _get_ctl_range(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """CTL 시작값, 종료값, 최댓값."""
    row_start = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? ORDER BY scope_id LIMIT 1",
        (start_date,),
    ).fetchone()

    row_end = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? AND scope_id <= ? ORDER BY scope_id DESC LIMIT 1",
        (start_date, end_date),
    ).fetchone()

    row_max = conn.execute(
        "SELECT MAX(numeric_value) FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? AND scope_id <= ?",
        (start_date, end_date),
    ).fetchone()

    ctl_start = float(row_start[0]) if row_start and row_start[0] is not None else None
    ctl_end = float(row_end[0]) if row_end and row_end[0] is not None else None
    ctl_peak = float(row_max[0]) if row_max and row_max[0] is not None else None

    return {
        "ctl_start": ctl_start,
        "ctl_end": ctl_end,
        "ctl_peak": ctl_peak,
    }


def _get_intensity_distribution(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """HR 존별 시간 분포 — Z1-2, Z3, Z4-5.

    존 데이터 커버리지 < 50%면 'insufficient'.
    """
    row = conn.execute(
        """SELECT
           COALESCE(SUM(CASE WHEN target_hr_zone IN (1, 2) THEN duration_sec ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN target_hr_zone = 3 THEN duration_sec ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN target_hr_zone IN (4, 5) THEN duration_sec ELSE 0 END), 0),
           COALESCE(SUM(duration_sec), 0)
           FROM (
               SELECT target_hr_zone, duration_sec
               FROM v_canonical_activities
               WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?
                 AND target_hr_zone IS NOT NULL AND target_hr_zone > 0
           )""",
        (start_date, end_date),
    ).fetchone()

    z12_sec = float(row[0]) if row else 0.0
    z3_sec = float(row[1]) if row else 0.0
    z45_sec = float(row[2]) if row else 0.0
    total_sec = float(row[3]) if row else 0.0

    if total_sec < 1:
        return {"status": "insufficient", "z12_pct": 0, "z3_pct": 0, "z45_pct": 0}

    coverage = (z12_sec + z3_sec + z45_sec) / total_sec
    if coverage < 0.5:
        return {"status": "insufficient", "z12_pct": 0, "z3_pct": 0, "z45_pct": 0}

    z12_pct = round(100 * z12_sec / total_sec)
    z3_pct = round(100 * z3_sec / total_sec)
    z45_pct = round(100 * z45_sec / total_sec)

    return {
        "status": "ok",
        "z12_pct": z12_pct,
        "z3_pct": z3_pct,
        "z45_pct": z45_pct,
        "coverage": round(100 * coverage),
    }


def _get_risk_peak(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any] | None:
    """위험도 최고 날 — ACWR 규칙 기반 (값만 아직 미구현, 설계에서 "규칙 최고 등급" 참고).

    Returns: {slug, value, date} 또는 None.
    """
    row = conn.execute(
        """SELECT numeric_value, scope_id FROM metric_store
           WHERE scope_type='daily' AND metric_name='acwr' AND is_primary=1
             AND scope_id >= ? AND scope_id <= ?
           ORDER BY numeric_value DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if not row or row[0] is None:
        return None

    acwr_value = float(row[0])
    acwr_date = row[1]

    return {
        "slug": "acwr",
        "value": round(acwr_value, 2),
        "date": acwr_date,
    }


def _get_key_sessions(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    limit: int = 3,
) -> list[dict]:
    """대표 세션 3: 최장, 품질 최고(workout_label), 레이스.

    각 항목은 {id, name, date, distance_km, type, workout_label}.
    """
    sessions = []

    # 최장 러닝
    row_long = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?
           ORDER BY distance_m DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_long:
        sessions.append({
            "id": row_long[0],
            "name": row_long[1] or "",
            "date": row_long[2],
            "distance_km": round(float(row_long[3]) / 1000.0, 1),
            "type": row_long[4],
            "workout_label": row_long[5],
        })

    # 품질 최고 (workout_label != None, 정렬은 distance 역순)
    row_quality = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ? AND workout_label IS NOT NULL
           ORDER BY distance_m DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_quality and (not row_long or row_quality[0] != row_long[0]):
        sessions.append({
            "id": row_quality[0],
            "name": row_quality[1] or "",
            "date": row_quality[2],
            "distance_km": round(float(row_quality[3]) / 1000.0, 1),
            "type": row_quality[4],
            "workout_label": row_quality[5],
        })

    # 레이스 (event_type='race')
    row_race = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM activity_summaries
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ? AND event_type='race'
           ORDER BY start_time DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_race and (not row_long or row_race[0] != row_long[0]):
        sessions.append({
            "id": row_race[0],
            "name": row_race[1] or "",
            "date": row_race[2],
            "distance_km": round(float(row_race[3]) / 1000.0, 1),
            "type": row_race[4],
            "workout_label": row_race[5],
        })

    return sessions[:limit]


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


def _get_block_dates(conn: sqlite3.Connection, plan_id: str, phase: str) -> tuple[str, str]:
    """활성 계획 phase 경계 조회 — 블록 단위 기간.

    현재 구현: plan_id는 미사용(향후 다중 계획 지원용). phase별로 활성 계획에서
    해당 phase의 시작/종료 주(월요일~토요일)를 찾는다.
    """
    from src.training.goals import get_active_goal
    from src.training.planner_schedule import schedule_for_goal
    from src.training.planner_rules import resolve_distance_label, plan_start_monday
    from src.training.planner_config import get_vdot_adj

    goal = get_active_goal(conn)
    if goal is None:
        raise ValueError(f"No active plan for block scope: {phase}")

    dlabel = resolve_distance_label(goal.get("distance_km", 10.0), goal.get("distance_label"))
    vdot = get_vdot_adj(conn)

    # schedule_for_goal는 전체 계획 주차 목록을 반환 (각 WeekTarget이 phase를 가짐)
    sched = schedule_for_goal(conn, goal, dlabel, vdot)
    plan_start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))

    if plan_start is None:
        raise ValueError("Cannot determine plan start date")

    # 요청한 phase의 첫 주(index)와 마지막 주(index)를 찾는다
    matching_indices = [i for i, w in enumerate(sched) if w.phase == phase]
    if not matching_indices:
        raise ValueError(f"Phase not found in active plan: {phase}")

    first_idx = matching_indices[0]
    last_idx = matching_indices[-1]

    # plan_start로부터 역산 (schedule은 race_date 역산이므로 시작이 index 0)
    start_week_date = plan_start + timedelta(weeks=first_idx)
    end_week_date = plan_start + timedelta(weeks=last_idx + 1) - timedelta(days=1)  # 토요일

    return start_week_date.isoformat(), end_week_date.isoformat()


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
    chips = [
        {
            "label": f"CTL {ctl_data.get('ctl_end', 0):.1f}",
            "value": ctl_data.get("ctl_end"),
            "drill": {"scope_type": "daily", "scope_id": end_date, "metric": "ctl"},
        },
        {
            "label": f"{period_label} {stats['distance_km']}km",
            "value": stats["distance_km"],
            "drill": None,  # 활동 목록 필터로 연결(별도 구현)
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
    else:  # week
        prev_date = date.fromisoformat(start_date) - timedelta(weeks=1)
        prev_start, prev_end = _week_date_range(prev_date.year, prev_date.isocalendar()[1])

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
        next_period = f"{next_year}-{next_month:02d}"
    else:  # week
        next_date = date.fromisoformat(end_date) + timedelta(days=1)
        prev_period = f"{prev_year}-W{prev_date.isocalendar()[1]:02d}"
        next_period = f"{next_date.year}-W{next_date.isocalendar()[1]:02d}"

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
        "compare": compare,
        "intensity": intensity,
        "key_sessions": key_sessions,
        "risk_peak": risk_peak,
        "milestones": milestones,
    }
