"""규칙 기반 주간 훈련 계획 생성 (v2 — 논문 기반 재설계).

설계 원칙:
  1. 사용자 가용일 우선 (휴식 요일/날짜 먼저 차단)
  2. Seiler 2010 80/20 원칙 + Daniels Q-day 규칙 (주 2~3회)
  3. Hard-Easy 원칙: Q-day 후 반드시 1일 이상 Z1/rest
  4. CRS 게이트(crs.py): 훈련 강도 상한 실시간 조정
  5. Daniels Running Formula 3rd Ed: VDOT_ADJ → 페이스 처방
  6. Buchheit & Laursen 2013: 인터벌 처방 (interval_calc.py)
  7. Mujika & Padilla 2003 / Bosquet 2007: 테이퍼 (볼륨 -40~50%, 강도 유지)
  8. 3:1 사이클: 3주 부하 후 1주 회복 (Foster 1998 Monotony 근거)

모듈 분리:
  - planner_config.py: 상수, 설정/메트릭 조회 헬퍼
  - planner_rules.py:  훈련 단계·볼륨·Q-day·페이스·배분·설명 규칙
  - planner.py (이 파일): 메인 생성/저장/조회 함수 + 하위 호환 re-export
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
from datetime import date, timedelta

from .planner_config import (
    DISTANCE_LABEL_KM,  # noqa: F401 (re-export)
    HR_ZONE,
    LONG_RUN_BASE,
    LONG_RUN_PHASE_FACTOR,
    MAX_Q_DAYS_BY_LABEL,
    get_available_days,
    get_eftp,
    get_latest_fitness,
    get_marathon_shape_pct,
    get_vdot_adj,
    get_week_index,
    load_prefs,
)
from .planner_rules import (
    RATIONALE,
    assign_long_run_slot,
    assign_qday_slots,
    description,
    distribute_volume,
    get_paces_from_vdot,
    pace_range,
    resolve_distance_label,
    training_phase,
    weekly_volume_km,
    weeks_to_race,
)

log = logging.getLogger(__name__)

# ── 하위 호환 private alias (test_planner.py 등) ────────────────────────
_training_phase = training_phase
_weekly_volume_km = weekly_volume_km


# ── 메인 계획 생성 함수 ───────────────────────────────────────────────────

def generate_weekly_plan(
    conn: sqlite3.Connection,
    goal_id: int | None = None,
    config: dict | None = None,
    week_start: date | None = None,
) -> list[dict]:
    """규칙 기반 주간 훈련 계획 생성 (v2).

    Args:
        conn: SQLite 연결.
        goal_id: 목표 id. None이면 active 목표 자동 선택.
        config: 설정 딕셔너리.
        week_start: 주 시작일 (월요일). None이면 이번 주 월요일.

    Returns:
        7개 planned_workout dict 리스트 (월~일).
    """
    from src.training.goals import get_active_goal, get_goal

    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    # 목표 로드
    goal = get_goal(conn, goal_id) if goal_id is not None else None
    if goal is None:
        goal = get_active_goal(conn)

    goal_distance = goal["distance_km"] if goal else 10.0
    race_date = goal["race_date"] if goal else None
    distance_label = goal.get("distance_label") if goal else None
    dlabel = resolve_distance_label(goal_distance, distance_label)

    # 피트니스 데이터
    fitness = get_latest_fitness(conn)
    ctl, tsb = fitness["ctl"], fitness["tsb"]
    vdot = get_vdot_adj(conn)
    eftp = get_eftp(conn)
    shape_pct = get_marathon_shape_pct(conn)

    # 훈련 단계
    weeks_left = weeks_to_race(race_date)
    week_idx = get_week_index(week_start, conn)
    phase = training_phase(weeks_left, week_idx)

    # 주간 볼륨
    total_km = weekly_volume_km(ctl, phase, tsb, shape_pct)
    long_km = LONG_RUN_BASE.get(dlabel, 14.0) * LONG_RUN_PHASE_FACTOR.get(
        phase if phase != "recovery_week" else "base", 1.0
    )
    long_km = min(long_km, total_km * 0.35)

    # 사용자 설정 (휴식 요일/날짜)
    prefs = load_prefs(conn)
    available = get_available_days(week_start, prefs)
    if not available:
        available = list(range(7))

    # Q-day 수 결정
    # Seiler 2010 80/20: 가용일의 20% → ceil로 올림 (round는 7일→1개로 과소)
    max_q = prefs.get("max_q_days") or MAX_Q_DAYS_BY_LABEL.get(dlabel, 2)
    if phase in ("taper", "base", "recovery_week"):
        max_q = min(max_q, 1)
    n_avail = len(available)
    n_q = min(max_q, max(1, math.ceil(n_avail * 0.20)))
    if n_avail <= 3:
        n_q = min(1, n_q)

    # Q-day 슬롯 배치 (Hard-Easy 원칙)
    q_slots = assign_qday_slots(available, n_q, dlabel, phase)

    # Long run 슬롯
    has_long = dlabel not in ("1.5k", "3k") and phase != "taper"
    long_slot = assign_long_run_slot(available, q_slots) if has_long else None

    # Q-day 타입: phase 기반 순수 결정 (CRS 게이트 없음 — 일일 추천카드에서 적용)
    # build/peak → interval, base/taper/recovery_week → tempo
    q_type_for_slot = "interval" if phase not in ("taper", "base", "recovery_week") else "tempo"

    # Q-day 다음날 → recovery (Daniels Hard-Easy 원칙: Lydiard/Bowerman)
    # 플랜 생성 시 구조적으로 항상 적용
    recovery_slots: set[int] = set()
    for qs in q_slots:
        nxt = qs + 1
        if (nxt < 7 and nxt in available
                and nxt not in q_slots and nxt != long_slot):
            recovery_slots.add(nxt)

    # 7일 템플릿 구성
    template: list[str] = []
    for i in range(7):
        if i not in available:
            template.append("rest")
        elif i == long_slot and has_long:
            template.append("long")
        elif i in q_slots:
            template.append(q_type_for_slot)
        elif i in recovery_slots:
            # Q-day 다음날: 회복 조깅 (Daniels: E+50~+90 영역)
            template.append("recovery")
        else:
            template.append("easy")

    # 거리 배분
    paces = get_paces_from_vdot(vdot, config)
    dists = distribute_volume(template, total_km, long_km)

    # 인터벌 처방 JSON 생성
    interval_rep_m = prefs.get("interval_rep_m", 1000)

    plan: list[dict] = []
    for i, (wtype, dist) in enumerate(zip(template, dists)):
        day = week_start + timedelta(days=i)
        pace_min, pace_max = pace_range(wtype, paces)

        interval_json: str | None = None
        if wtype == "interval" and vdot:
            try:
                from src.training.interval_calc import prescribe_from_vdot
                rx = prescribe_from_vdot(interval_rep_m, vdot, eftp)
                interval_json = json.dumps(rx, ensure_ascii=False)
            except Exception as e:
                log.warning("인터벌 처방 오류: %s", e)

        plan.append({
            "date": day.isoformat(),
            "workout_type": wtype,
            "distance_km": dist,
            "target_pace_min": pace_min,
            "target_pace_max": pace_max,
            "target_hr_zone": HR_ZONE.get(wtype),
            "description": description(wtype, dist, day),
            "rationale": RATIONALE.get(wtype, ""),
            "source": "planner",
            "interval_prescription": interval_json,
            "_phase": phase,
            "_vdot": vdot,
        })

    return plan


# ── 저장/조회/설정 ─────────────────────────────────────────────────────────

def save_weekly_plan(conn: sqlite3.Connection, plan: list[dict]) -> int:
    """주간 계획을 planned_workouts 테이블에 저장.

    같은 날짜의 source='planner' 기존 레코드를 삭제 후 재삽입.

    Returns:
        저장된 레코드 수.
    """
    if not plan:
        return 0

    for w in plan:
        conn.execute(
            "DELETE FROM planned_workouts WHERE date = ? AND source = 'planner'",
            (w["date"],),
        )

    count = 0
    for w in plan:
        conn.execute(
            """INSERT INTO planned_workouts
               (date, workout_type, distance_km, target_pace_min, target_pace_max,
                target_hr_zone, description, rationale, source, interval_prescription)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                w["date"], w["workout_type"], w.get("distance_km"),
                w.get("target_pace_min"), w.get("target_pace_max"),
                w.get("target_hr_zone"), w.get("description"),
                w.get("rationale"), w.get("source", "planner"),
                w.get("interval_prescription"),
            ),
        )
        count += 1

    conn.commit()
    return count


def get_planned_workouts(
    conn: sqlite3.Connection,
    week_start: date | None = None,
) -> list[dict]:
    """이번 주 (또는 지정 주) planned_workouts 조회."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)

    rows = conn.execute(
        """SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max,
                  target_hr_zone, description, rationale, completed, source, ai_model,
                  interval_prescription
           FROM planned_workouts
           WHERE date >= ? AND date < ?
           ORDER BY date""",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale",
            "completed", "source", "ai_model", "interval_prescription"]
    return [dict(zip(keys, r)) for r in rows]


def upsert_user_training_prefs(
    conn: sqlite3.Connection,
    rest_weekdays_mask: int = 0,
    blocked_dates: list[str] | None = None,
    interval_rep_m: int = 1000,
    max_q_days: int = 0,
    long_run_weekday_mask: int = 0,
) -> None:
    """user_training_prefs 저장 (id=1 고정 upsert).

    Args:
        long_run_weekday_mask: 롱런 요일 비트마스크 (0=자동 선택).
    """
    conn.execute(
        """INSERT INTO user_training_prefs
           (id, rest_weekdays_mask, blocked_dates, interval_rep_m, max_q_days,
            long_run_weekday_mask, updated_at)
           VALUES (1, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(id) DO UPDATE SET
               rest_weekdays_mask=excluded.rest_weekdays_mask,
               blocked_dates=excluded.blocked_dates,
               interval_rep_m=excluded.interval_rep_m,
               max_q_days=excluded.max_q_days,
               long_run_weekday_mask=excluded.long_run_weekday_mask,
               updated_at=excluded.updated_at""",
        (
            rest_weekdays_mask,
            json.dumps(blocked_dates or [], ensure_ascii=False),
            interval_rep_m,
            max_q_days,
            long_run_weekday_mask,
        ),
    )
    conn.commit()
