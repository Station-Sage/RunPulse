"""Phase 7b — 플랜 템플릿 조회 + 새 플랜 생성 서비스.

get_static_plan_templates() — 거리/목표 기반 3개 템플릿 비교 분석.
create_plan_from_template()  — 템플릿 선택 → goal + 전체 플랜 생성.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training.goals import add_goal
from src.training.planner import (
    generate_weekly_plan,
    save_weekly_plan,
    upsert_user_training_prefs,
)
from src.training.readiness import (
    analyze_readiness,
    get_recommended_weeks,
    recommend_weekly_km,
    vdot_to_time,
)


def _km_to_label(distance_km: float) -> str:
    """거리(km) → 가장 가까운 레이블."""
    if distance_km <= 2.0:
        return "1.5k"
    if distance_km <= 4.0:
        return "3k"
    if distance_km <= 7.5:
        return "5k"
    if distance_km <= 15.0:
        return "10k"
    if distance_km <= 30.0:
        return "half"
    if distance_km <= 50.0:
        return "full"
    return "custom"


def _get_current_vdot(conn: sqlite3.Connection) -> float | None:
    """metric_store에서 최근 30일 이내 가장 최근 VDOT 조회(race_pred_vdot — vdot_adj 폐기, P7-PRED-90)."""
    since = (date.today() - timedelta(days=30)).isoformat()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='race_pred_vdot' AND scope_type='daily' AND is_primary=1"
        "   AND scope_id<=? AND scope_id>=? AND numeric_value IS NOT NULL"
        " ORDER BY scope_id DESC LIMIT 1",
        (today, since),
    ).fetchone()
    return row[0] if row else None


def get_static_plan_templates(
    conn: sqlite3.Connection,
    distance_km: float,
    target_time_sec: int | None = None,
) -> list[dict]:
    """거리 + 목표 시간 기반 플랜 템플릿 3개 반환.

    Args:
        conn: SQLite 연결.
        distance_km: 목표 레이스 거리 (km).
        target_time_sec: 목표 완주 시간(초). None이면 "완주" 목표.

    Returns:
        [{"weeks","label","weekly_km_target","achievability_pct",
          "projected_time_end","risk_level","status_summary"}, ...]
    """
    rec = get_recommended_weeks(distance_km)
    week_presets = sorted(set([rec["min"], rec["optimal_min"], rec["optimal_max"]]))
    taper = rec["taper"]
    dist_label = _km_to_label(distance_km)

    # 완주 목표 → 현재 VDOT 기반 effective target 계산
    effective_target: int | None = target_time_sec
    if target_time_sec is None:
        vdot = _get_current_vdot(conn)
        if vdot:
            effective_target = vdot_to_time(vdot, distance_km * 1000)

    # 주차별 레이블 매핑
    week_labels: dict[int, str] = {
        rec["min"]: "빠른 완성",
        rec["optimal_max"]: "여유형",
    }

    templates = []
    for weeks in week_presets:
        week_label = week_labels.get(weeks, "권장")

        if effective_target is None:
            # VDOT 데이터 없음 — achievability 필드 전부 None
            templates.append({
                "weeks": weeks,
                "label": week_label,
                "weekly_km_target": None,
                "achievability_pct": None,
                "projected_time_end": None,
                "risk_level": None,
                "status_summary": "VDOT 데이터가 없습니다. 먼저 동기화하세요.",
            })
            continue

        analysis = analyze_readiness(conn, distance_km, effective_target, weeks)

        # 피크 주차 권장 주간 km
        vdot_for_km = analysis.get("current_vdot")
        if vdot_for_km is not None:
            peak_week = max(0, weeks - taper - 1)
            weekly_km_target: float | None = recommend_weekly_km(
                vdot_for_km, dist_label, "peak", peak_week, weeks
            )
        else:
            weekly_km_target = None

        ach = analysis.get("achievability_pct")
        if ach is None:
            risk_level: str | None = None
        elif ach >= 70:
            risk_level = "낮음"
        elif ach >= 40:
            risk_level = "중간"
        else:
            risk_level = "높음"

        templates.append({
            "weeks": weeks,
            "label": week_label,
            "weekly_km_target": weekly_km_target,
            "achievability_pct": ach,
            "projected_time_end": analysis.get("projected_time_end"),
            "risk_level": risk_level,
            "status_summary": analysis.get("status_summary", ""),
        })

    return templates


def create_plan_from_template(
    conn: sqlite3.Connection,
    distance_km: float,
    race_date: str | None,
    weeks: int,
    target_time_sec: int | None = None,
    name: str | None = None,
) -> int:
    """템플릿 선택으로 새 플랜 생성. goal_id 반환.

    Args:
        conn: SQLite 연결.
        distance_km: 목표 레이스 거리 (km).
        race_date: 레이스 날짜 (YYYY-MM-DD) 또는 None.
        weeks: 훈련 기간 (주).
        target_time_sec: 목표 완주 시간(초). None이면 "완주" 목표.
        name: 목표 이름. None이면 "{distance_km}km 목표" 자동 생성.

    Returns:
        새로 생성된 goal_id.
    """
    goal_name = name or f"{distance_km:.0f}km 목표"
    goal_id = add_goal(conn, goal_name, distance_km, race_date, target_time_sec)
    conn.execute("UPDATE goals SET plan_weeks=? WHERE id=?", (weeks, goal_id))
    upsert_user_training_prefs(conn)

    today = date.today()
    current_week = today - timedelta(days=today.weekday())

    ws = current_week
    for _ in range(weeks):
        plan = generate_weekly_plan(conn, goal_id=goal_id, week_start=ws)
        save_weekly_plan(conn, plan)
        ws += timedelta(weeks=1)

    conn.commit()
    return goal_id
