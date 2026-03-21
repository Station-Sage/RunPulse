"""추천 칩 생성 — 규칙 기반 + AI 응답 파싱 하이브리드."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class RunnerState:
    """오늘 런너 상태 스냅샷."""
    date: str = ""
    has_today_run: bool = False
    acwr: float | None = None
    acwr_status: str = "unknown"    # low | safe | caution | danger
    tsb: float | None = None        # Training Stress Balance
    recovery_grade: str | None = None
    training_readiness: float | None = None
    race_days_left: int | None = None
    goal_name: str | None = None
    weekly_run_count: int = 0
    total_distance_this_week: float = 0.0


# 칩 레지스트리: id → {label, template}
# template은 briefing.py가 prompt_templates/<template>.txt를 로드하는 데 사용
CHIP_REGISTRY: dict[str, dict] = {
    "today_deep":      {"label": "오늘 훈련 상세 분석",          "template": "deep_analysis"},
    "weekly_review":   {"label": "이번 주 훈련 리뷰",            "template": "weekly_review"},
    "weekly_plan":     {"label": "다음 주 훈련 계획 만들어줘",   "template": "weekly_plan"},
    "recovery_advice": {"label": "컨디션/회복 조언",             "template": "recovery_advice"},
    "race_predict":    {"label": "레이스 준비도 / 예상 기록",    "template": "race_predict"},
    "injury_risk":     {"label": "부상 위험도 체크",             "template": "injury_risk"},
    "goal_setting":    {"label": "목표 설정 도움",               "template": "goal_setting"},
    "pace_zones":      {"label": "페이스/HR 존 분석",            "template": "pace_zones"},
    "season_review":   {"label": "시즌 전체 리뷰",              "template": "season_review"},
}

_RUN_TYPES = "('running','run','virtualrun','treadmill','highintensityintervaltraining')"


def get_runner_state(conn: sqlite3.Connection) -> RunnerState:
    """DB에서 현재 런너 상태를 수집하여 RunnerState 반환.

    Args:
        conn: SQLite 연결.
    """
    from src.analysis.recovery import get_recovery_status
    from src.analysis.trends import calculate_acwr
    from src.training.goals import get_active_goal

    today = date.today()
    state = RunnerState(date=today.isoformat())

    # 오늘 활동 유무
    row = conn.execute(
        f"SELECT COUNT(*) FROM activity_summaries"
        f" WHERE date(start_time) = ? AND activity_type IN {_RUN_TYPES}",
        (today.isoformat(),),
    ).fetchone()
    state.has_today_run = bool(row and row[0] > 0)

    # ACWR
    try:
        acwr_data = calculate_acwr(conn)
        av = (acwr_data or {}).get("average") or {}
        state.acwr = av.get("acwr")
        state.acwr_status = av.get("status") or "unknown"
    except Exception:
        pass

    # TSB
    try:
        row = conn.execute(
            "SELECT tsb FROM daily_fitness ORDER BY date DESC LIMIT 1"
        ).fetchone()
        state.tsb = row[0] if row else None
    except Exception:
        pass

    # 회복 상태
    try:
        rec = get_recovery_status(conn, today.isoformat())
        state.recovery_grade = rec.get("grade")
        detail = rec.get("detail") or {}
        state.training_readiness = detail.get("training_readiness_score")
    except Exception:
        pass

    # 활성 목표
    try:
        goal = get_active_goal(conn)
        if goal:
            state.goal_name = goal.get("name")
            race_date = goal.get("race_date")
            if race_date:
                try:
                    state.race_days_left = (date.fromisoformat(race_date) - today).days
                except ValueError:
                    pass
    except Exception:
        pass

    # 이번 주 기초 지표
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    week_end_dt = (today + timedelta(days=1)).isoformat()
    try:
        row = conn.execute(
            f"SELECT COUNT(DISTINCT COALESCE(matched_group_id, CAST(id AS TEXT))),"
            f"       COALESCE(SUM(distance_km), 0)"
            f" FROM activity_summaries"
            f" WHERE start_time >= ? AND start_time < ?"
            f"   AND activity_type IN {_RUN_TYPES}",
            (week_start, week_end_dt),
        ).fetchone()
        if row:
            state.weekly_run_count = row[0] or 0
            state.total_distance_this_week = round(float(row[1] or 0), 1)
    except Exception:
        pass

    return state


def rule_based_chips(state: RunnerState) -> list[dict]:
    """런너 상태 기반 규칙으로 추천 칩 최대 5개를 생성.

    우선순위:
    1. 오늘 훈련 완료 → today_deep 최상위
    2. ACWR 위험(caution/danger) → injury_risk 최상위
    3. 회복 부족(poor) 또는 훈련 준비도 < 30 → recovery_advice 우선
    4. D-30 이내 레이스 → race_predict 우선
    5. 나머지는 기본 풀에서 채움

    Returns:
        [{"id": "...", "label": "..."}] 최대 5개.
    """
    priority: list[str] = []

    if state.has_today_run:
        priority.append("today_deep")

    if state.acwr_status in ("caution", "danger"):
        priority.append("injury_risk")

    if state.recovery_grade == "poor" or (
        state.training_readiness is not None and state.training_readiness < 30
    ):
        priority.append("recovery_advice")

    if state.race_days_left is not None and 0 < state.race_days_left <= 30:
        priority.append("race_predict")

    # 기본 풀 (우선순위에 없는 것만)
    fallback_order = [
        "weekly_review", "weekly_plan", "recovery_advice",
        "race_predict", "pace_zones", "goal_setting", "injury_risk",
    ]
    seen = set(priority)
    pool = [cid for cid in fallback_order if cid not in seen]

    ordered = priority + pool
    result = []
    for cid in ordered:
        info = CHIP_REGISTRY.get(cid)
        if info:
            result.append({"id": cid, "label": info["label"]})
        if len(result) == 5:
            break

    return result
