"""AI 채팅 전용 컨텍스트 빌더 — 의도 감지 → DB 자동 수집.

사용자 질문의 의도를 감지하여 관련 데이터를 DB에서 수집하고
AI 프롬프트용 컨텍스트 텍스트를 생성한다.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.pace import seconds_to_pace

log = logging.getLogger(__name__)

# ── 의도 감지 ──────────────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "today": ["오늘", "훈련 어떻", "방금", "아까", "분석해", "평가해", "어땠"],
    "race": ["대회", "마라톤", "레이스", "하프", "10k", "5k", "풀코스", "준비도", "예측"],
    "compare": ["비교", "작년", "지난번", "이전", "나아졌", "성장", "변화", "개선", "퇴보"],
    "plan": ["내일", "계획", "조정", "다음", "스케줄", "훈련량", "몇 키로"],
    "recovery": ["회복", "피로", "쉬어", "컨디션", "휴식", "오버", "과훈련", "부상"],
}

# 날짜 패턴: "3월 15일", "3/15", "2025-03-15", "지난주 월요일", "어제" 등
import re as _re

_DATE_PATTERNS = [
    # 2025-03-15, 2025.03.15
    _re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})"),
    # 3월 15일, 3월15일
    _re.compile(r"(\d{1,2})월\s*(\d{1,2})일"),
    # 3/15
    _re.compile(r"(\d{1,2})/(\d{1,2})"),
]

_RELATIVE_DATE_KW: dict[str, int] = {
    "어제": -1, "그제": -2, "그저께": -2, "엊그제": -2,
    "그끄저께": -3, "3일전": -3, "3일 전": -3,
}


def _extract_date(message: str) -> str | None:
    """메시지에서 날짜 추출. 없으면 None."""
    today = date.today()

    # 상대 날짜
    for kw, delta in _RELATIVE_DATE_KW.items():
        if kw in message:
            return (today + timedelta(days=delta)).isoformat()

    # 지난주 + 요일
    _WEEKDAY_KO = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    m = _re.search(r"지난\s*주?\s*(월|화|수|목|금|토|일)", message)
    if m:
        wd = _WEEKDAY_KO[m.group(1)]
        last_monday = today - timedelta(days=today.weekday() + 7)
        return (last_monday + timedelta(days=wd)).isoformat()

    # 절대 날짜
    for pat in _DATE_PATTERNS:
        m = pat.search(message)
        if m:
            groups = m.groups()
            try:
                if len(groups) == 3:  # YYYY-MM-DD
                    return date(int(groups[0]), int(groups[1]), int(groups[2])).isoformat()
                elif len(groups) == 2:  # M월D일 or M/D
                    y = today.year
                    d = date(y, int(groups[0]), int(groups[1]))
                    # 미래면 작년으로
                    if d > today:
                        d = date(y - 1, int(groups[0]), int(groups[1]))
                    return d.isoformat()
            except ValueError:
                continue

    return None


def detect_intent(message: str) -> tuple[str, str | None]:
    """사용자 메시지에서 의도 + 날짜 감지.

    Returns:
        (intent, target_date) — target_date는 특정 날짜 조회 시 YYYY-MM-DD.
    """
    msg = message.lower()
    target_date = _extract_date(message)

    # 날짜가 있으면 lookup 의도 (다른 의도와 조합 가능)
    if target_date:
        # 날짜 + 레이스 키워드 → race
        for intent, keywords in _INTENT_KEYWORDS.items():
            if any(k in msg for k in keywords):
                return intent, target_date
        return "lookup", target_date

    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return intent, None
    return "general", None


# ── 기본 컨텍스트 (항상 포함) ──────────────────────────────────────────


def _build_base_context(conn: sqlite3.Connection, today: str) -> dict[str, Any]:
    """기본 컨텍스트: 주요 메트릭 + 웰니스 + 피트니스 + 최근 활동 3개."""
    ctx: dict[str, Any] = {"date": today}

    # 주요 메트릭
    for name in ["UTRS", "CIRS", "ACWR", "DI", "RTTI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        ctx[name] = round(float(row[0]), 2) if row and row[0] is not None else None

    # CTL/ATL/TSB
    fit = conn.execute(
        "SELECT ctl, atl, tsb, garmin_vo2max FROM daily_fitness "
        "WHERE date<=? ORDER BY date DESC LIMIT 1", (today,),
    ).fetchone()
    if fit:
        ctx["ctl"] = round(float(fit[0]), 1) if fit[0] else None
        ctx["atl"] = round(float(fit[1]), 1) if fit[1] else None
        ctx["tsb"] = round(float(fit[2]), 1) if fit[2] else None
        ctx["vo2max"] = round(float(fit[3]), 1) if fit[3] else None

    # 웰니스 오늘
    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (today,),
    ).fetchone()
    if well:
        ctx["wellness"] = {"bb": well[0], "sleep": well[1], "hrv": well[2],
                           "stress": well[3], "rhr": well[4]}

    # 최근 활동 3개
    acts = conn.execute(
        "SELECT start_time, distance_km, duration_sec, avg_pace_sec_km, avg_hr "
        "FROM v_canonical_activities WHERE activity_type='running' "
        "ORDER BY start_time DESC LIMIT 3",
    ).fetchall()
    ctx["recent_activities"] = [
        {"date": str(r[0])[:10], "km": r[1], "sec": r[2], "pace": r[3], "hr": r[4]}
        for r in acts
    ]

    return ctx


# ── 의도별 추가 컨텍스트 ──────────────────────────────────────────────


def _add_today_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """오늘 활동 상세 — 메트릭, HR존, 분류, 컨디션."""
    act = conn.execute(
        "SELECT id, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain_m, calories FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? "
        "ORDER BY start_time DESC LIMIT 1", (today,),
    ).fetchone()
    if not act:
        ctx["today_detail"] = None
        return

    aid = act[0]
    detail = {
        "distance_km": act[1], "duration_sec": act[2],
        "pace": seconds_to_pace(act[3]) if act[3] else None,
        "avg_hr": act[4], "max_hr": act[5],
        "elevation": act[6], "calories": act[7],
    }

    # 2차 메트릭
    metrics = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics "
        "WHERE activity_id=? AND metric_value IS NOT NULL", (aid,),
    ).fetchall()
    detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}

    # 운동 분류
    cls = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name='workout_type' AND activity_id=?", (aid,),
    ).fetchone()
    if cls:
        detail["workout_type"] = cls[0]

    ctx["today_detail"] = detail


def _add_race_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """레이스 준비도 — DARP/VDOT 12주 추세 + 목표 + 최근 레이스."""
    # DARP/VDOT 추세 (12주)
    start_12w = (date.fromisoformat(today) - timedelta(weeks=12)).isoformat()
    darp_rows = conn.execute(
        "SELECT date, metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name='DARP_half' AND activity_id IS NULL "
        "AND date>=? ORDER BY date", (start_12w,),
    ).fetchall()
    ctx["darp_trend"] = []
    for r in darp_rows:
        import json
        mj = json.loads(r[2]) if r[2] else {}
        ctx["darp_trend"].append({
            "date": r[0], "time_sec": mj.get("time_sec"), "vdot": mj.get("vdot"),
        })

    # DI 추세
    di_rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name='DI' AND activity_id IS NULL AND date>=? ORDER BY date",
        (start_12w,),
    ).fetchall()
    ctx["di_trend"] = [{"date": r[0], "value": round(float(r[1]), 1)} for r in di_rows if r[1]]

    # 목표 레이스
    try:
        from src.training.goals import get_active_goal
        ctx["goal"] = get_active_goal(conn)
    except Exception:
        ctx["goal"] = None


def _add_compare_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """장기 비교 — 3/6/12개월 전 메트릭 스냅샷 + 레이스 이력."""
    snapshots = {}
    for label, months in [("3개월전", 3), ("6개월전", 6), ("12개월전", 12)]:
        ref = (date.fromisoformat(today) - timedelta(days=months * 30)).isoformat()
        snap = {}
        for name in ["UTRS", "CIRS", "ACWR", "DI"]:
            row = conn.execute(
                "SELECT metric_value FROM computed_metrics "
                "WHERE metric_name=? AND activity_id IS NULL "
                "AND date BETWEEN ? AND date(?, '+7 days') ORDER BY date LIMIT 1",
                (name, ref, ref),
            ).fetchone()
            snap[name] = round(float(row[0]), 2) if row and row[0] is not None else None
        fit = conn.execute(
            "SELECT ctl, garmin_vo2max FROM daily_fitness "
            "WHERE date BETWEEN ? AND date(?, '+7 days') ORDER BY date LIMIT 1",
            (ref, ref),
        ).fetchone()
        if fit:
            snap["ctl"] = round(float(fit[0]), 1) if fit[0] else None
            snap["vo2max"] = round(float(fit[1]), 1) if fit[1] else None

        # 해당 시기 주간 볼륨
        vol = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(distance_km),0), "
            "COALESCE(AVG(avg_pace_sec_km),0) FROM v_canonical_activities "
            "WHERE activity_type='running' "
            "AND start_time BETWEEN ? AND date(?, '+7 days')",
            (ref, ref),
        ).fetchone()
        if vol:
            snap["weekly_runs"] = vol[0]
            snap["weekly_km"] = round(float(vol[1]), 1)
            snap["avg_pace"] = seconds_to_pace(vol[2]) if vol[2] else None

        snapshots[label] = snap

    ctx["past_snapshots"] = snapshots


def _add_plan_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """훈련 계획 — 이번 주 계획 + 웰니스 3일 추세."""
    # 이번 주 계획
    try:
        from src.training.planner import get_planned_workouts
        plans = get_planned_workouts(conn)
        monday = date.fromisoformat(today) - timedelta(days=date.fromisoformat(today).weekday())
        sunday = monday + timedelta(days=6)
        ctx["week_plan"] = [
            p for p in plans
            if monday.isoformat() <= p["date"] <= sunday.isoformat()
        ]
    except Exception:
        ctx["week_plan"] = []

    # 웰니스 3일
    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg "
        "FROM daily_wellness WHERE source='garmin' AND date<=? "
        "ORDER BY date DESC LIMIT 3", (today,),
    ).fetchall()
    ctx["wellness_3d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4]}
        for r in reversed(rows)
    ]


def _add_recovery_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """회복 상세 — 웰니스 7일 + HRV 기준선."""
    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date<=? "
        "ORDER BY date DESC LIMIT 7", (today,),
    ).fetchall()
    ctx["wellness_7d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4], "rhr": r[5]}
        for r in reversed(rows)
    ]

    # HRV 기준선
    bl = conn.execute(
        "SELECT hrv_baseline_low, hrv_baseline_high FROM daily_detail_metrics "
        "WHERE metric_name='hrv_baseline_low' AND date<=? ORDER BY date DESC LIMIT 1",
        (today,),
    ).fetchone()
    if bl:
        ctx["hrv_baseline"] = {"low": bl[0], "high": bl[1]}

    # CIRS 트렌드 7일
    cirs_rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name='CIRS' AND activity_id IS NULL AND date<=? "
        "ORDER BY date DESC LIMIT 7", (today,),
    ).fetchall()
    ctx["cirs_7d"] = [{"date": r[0], "value": round(float(r[1]), 1)}
                      for r in reversed(cirs_rows) if r[1]]


# ── 통합 빌더 ──────────────────────────────────────────────────────────

def _add_lookup_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """특정 날짜 활동 조회 — 해당 날짜의 모든 활동 + 메트릭 + 웰니스."""
    target = ctx.get("_target_date", today)

    # 해당 날짜 활동 (복수 가능)
    acts = conn.execute(
        "SELECT id, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain_m, calories, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? "
        "ORDER BY start_time", (target,),
    ).fetchall()

    lookup_acts = []
    for act in acts:
        aid = act[0]
        detail = {
            "distance_km": act[1], "duration_sec": act[2],
            "pace": seconds_to_pace(act[3]) if act[3] else None,
            "avg_hr": act[4], "max_hr": act[5],
            "elevation": act[6], "calories": act[7],
            "name": act[8],
        }
        # 2차 메트릭
        metrics = conn.execute(
            "SELECT metric_name, metric_value FROM computed_metrics "
            "WHERE activity_id=? AND metric_value IS NOT NULL", (aid,),
        ).fetchall()
        detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}

        # 분류
        cls = conn.execute(
            "SELECT metric_value FROM computed_metrics "
            "WHERE metric_name='workout_type' AND activity_id=?", (aid,),
        ).fetchone()
        if cls:
            detail["workout_type"] = cls[0]
        lookup_acts.append(detail)

    ctx["lookup_date"] = target
    ctx["lookup_activities"] = lookup_acts

    # 해당 날짜 일별 메트릭
    day_metrics = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics "
        "WHERE date=? AND activity_id IS NULL AND metric_value IS NOT NULL",
        (target,),
    ).fetchall()
    ctx["lookup_day_metrics"] = {r[0]: round(float(r[1]), 2) for r in day_metrics}

    # 해당 날짜 웰니스
    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (target,),
    ).fetchone()
    if well:
        ctx["lookup_wellness"] = {"bb": well[0], "sleep": well[1], "hrv": well[2],
                                   "stress": well[3], "rhr": well[4]}


_INTENT_BUILDERS = {
    "today": _add_today_context,
    "race": _add_race_context,
    "compare": _add_compare_context,
    "plan": _add_plan_context,
    "recovery": _add_recovery_context,
    "lookup": _add_lookup_context,
}


# ── 풍부한 컨텍스트 (대형 컨텍스트 윈도우 provider용) ──────────────────


def _add_rich_30d_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Gemini용 30일 풀 데이터 — 활동/메트릭/웰니스/피트니스 전체."""
    start_30d = (date.fromisoformat(today) - timedelta(days=30)).isoformat()

    # 30일 전체 활동
    acts = conn.execute(
        "SELECT date(start_time), distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, max_hr, elevation_gain_m, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? ORDER BY start_time",
        (start_30d,),
    ).fetchall()
    ctx["activities_30d"] = [
        {"date": r[0], "km": r[1], "sec": r[2],
         "pace": seconds_to_pace(r[3]) if r[3] else None,
         "avg_hr": r[4], "max_hr": r[5], "elev": r[6], "name": r[7]}
        for r in acts
    ]

    # 30일 일별 메트릭 (주요 메트릭만)
    key_metrics = ["UTRS", "CIRS", "ACWR", "DI", "RTTI", "REC", "RRI",
                   "Monotony", "LSI", "Strain", "SAPI", "TEROI"]
    metric_rows = conn.execute(
        "SELECT date, metric_name, metric_value FROM computed_metrics "
        "WHERE activity_id IS NULL AND metric_name IN ({}) AND date>=? "
        "ORDER BY date".format(",".join(f"'{m}'" for m in key_metrics)),
        (start_30d,),
    ).fetchall()
    daily_metrics: dict[str, dict] = {}
    for d, name, val in metric_rows:
        if val is None:
            continue
        daily_metrics.setdefault(d, {})[name] = round(float(val), 2)
    ctx["daily_metrics_30d"] = daily_metrics

    # 30일 웰니스
    well_rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date>=? ORDER BY date",
        (start_30d,),
    ).fetchall()
    ctx["wellness_30d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3],
         "stress": r[4], "rhr": r[5]}
        for r in well_rows
    ]

    # 30일 피트니스 (CTL/ATL/TSB)
    fit_rows = conn.execute(
        "SELECT date, ctl, atl, tsb FROM daily_fitness "
        "WHERE date>=? ORDER BY date", (start_30d,),
    ).fetchall()
    ctx["fitness_30d"] = [
        {"date": r[0], "ctl": round(float(r[1]), 1) if r[1] else None,
         "atl": round(float(r[2]), 1) if r[2] else None,
         "tsb": round(float(r[3]), 1) if r[3] else None}
        for r in fit_rows
    ]

    # 러너 프로필 요약
    ctx["runner_profile"] = _build_runner_profile(conn, today)

    # 레이스 활동 이력 (태그 기반)
    race_acts = conn.execute(
        "SELECT a.start_time, a.distance_km, a.duration_sec, a.avg_pace_sec_km, a.avg_hr, a.name "
        "FROM v_canonical_activities a "
        "LEFT JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
        "WHERE a.activity_type='running' AND (c.metric_value='race' OR a.name LIKE '%레이스%' "
        "OR a.name LIKE '%대회%' OR a.name LIKE '%Race%') "
        "ORDER BY a.start_time DESC LIMIT 10",
    ).fetchall()
    if race_acts:
        ctx["race_history"] = [
            {"date": str(r[0])[:10], "km": r[1], "sec": r[2],
             "pace": seconds_to_pace(r[3]) if r[3] else None,
             "hr": r[4], "name": r[5]}
            for r in race_acts
        ]

    # 오늘과 같은 유형의 과거 활동 (비교용)
    today_type = conn.execute(
        "SELECT c.metric_value FROM v_canonical_activities a "
        "JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
        "WHERE a.activity_type='running' AND date(a.start_time)=? "
        "ORDER BY a.start_time DESC LIMIT 1", (today,),
    ).fetchone()
    if today_type and today_type[0]:
        wtype = today_type[0]
        similar = conn.execute(
            "SELECT date(a.start_time), a.distance_km, a.avg_pace_sec_km, a.avg_hr "
            "FROM v_canonical_activities a "
            "JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
            "WHERE c.metric_value=? AND a.activity_type='running' AND date(a.start_time)<? "
            "ORDER BY a.start_time DESC LIMIT 5", (wtype, today),
        ).fetchall()
        if similar:
            ctx["similar_activities"] = {
                "type": wtype,
                "history": [
                    {"date": r[0], "km": r[1],
                     "pace": seconds_to_pace(r[2]) if r[2] else None, "hr": r[3]}
                    for r in similar
                ],
            }


def _add_mid_14d_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Claude/OpenAI용 14일 데이터."""
    start_14d = (date.fromisoformat(today) - timedelta(days=14)).isoformat()

    # 14일 활동
    acts = conn.execute(
        "SELECT date(start_time), distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? ORDER BY start_time",
        (start_14d,),
    ).fetchall()
    ctx["activities_14d"] = [
        {"date": r[0], "km": r[1], "sec": r[2],
         "pace": seconds_to_pace(r[3]) if r[3] else None,
         "avg_hr": r[4], "name": r[5]}
        for r in acts
    ]

    # 14일 웰니스
    well_rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg "
        "FROM daily_wellness WHERE source='garmin' AND date>=? ORDER BY date",
        (start_14d,),
    ).fetchall()
    ctx["wellness_14d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4]}
        for r in well_rows
    ]

    ctx["runner_profile"] = _build_runner_profile(conn, today)


def _build_runner_profile(conn: sqlite3.Connection, today: str) -> dict:
    """러너 프로필 요약 — 주간 볼륨, 수준, 경향 등."""
    profile: dict[str, Any] = {}

    # 최근 4주 주간 평균
    start_4w = (date.fromisoformat(today) - timedelta(weeks=4)).isoformat()
    vol = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_km),0), COALESCE(AVG(avg_pace_sec_km),0) "
        "FROM v_canonical_activities WHERE activity_type='running' AND start_time>=?",
        (start_4w,),
    ).fetchone()
    if vol and vol[0]:
        weeks = 4
        profile["weekly_avg_runs"] = round(vol[0] / weeks, 1)
        profile["weekly_avg_km"] = round(float(vol[1]) / weeks, 1)
        profile["avg_pace"] = seconds_to_pace(vol[2]) if vol[2] else None

    # VDOT / VO2Max
    for name in ["VDOT_ADJ", "DI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        if row and row[0]:
            profile[name.lower()] = round(float(row[0]), 1)

    fit = conn.execute(
        "SELECT garmin_vo2max FROM daily_fitness WHERE date<=? ORDER BY date DESC LIMIT 1",
        (today,),
    ).fetchone()
    if fit and fit[0]:
        profile["vo2max"] = round(float(fit[0]), 1)

    # 목표
    try:
        from src.training.goals import get_active_goal
        goal = get_active_goal(conn)
        if goal:
            profile["goal"] = goal.get("name")
            if goal.get("race_date"):
                try:
                    dl = (date.fromisoformat(goal["race_date"]) - date.fromisoformat(today)).days
                    profile["race_dday"] = dl
                except ValueError:
                    pass
    except Exception:
        pass

    return profile


# Provider별 컨텍스트 전략
_RICH_PROVIDERS = {"gemini"}      # 1M 컨텍스트 → 30일 풀 데이터
_MID_PROVIDERS = {"claude", "openai"}  # 200K → 14일 + 의도별
# groq, rule 등: 의도 기반 선택적 (128K 이하)


def build_chat_context(conn: sqlite3.Connection, message: str,
                       chat_history: list[dict] | None = None,
                       provider: str = "rule") -> str:
    """Provider 컨텍스트 용량에 맞는 채팅 컨텍스트 생성.

    Args:
        conn: DB 연결.
        message: 사용자 메시지.
        chat_history: 최근 대화 이력 (맥락 유지용).
        provider: AI provider 이름 (gemini/groq/claude/openai/rule).
    """
    today = date.today().isoformat()
    intent, target_date = detect_intent(message)

    # 1. 기본 컨텍스트
    ctx = _build_base_context(conn, today)
    ctx["intent"] = intent
    if target_date:
        ctx["_target_date"] = target_date

    # 2. Provider별 전략
    if provider in _RICH_PROVIDERS:
        # Gemini: 30일 풀 데이터 + 의도별 추가
        try:
            _add_rich_30d_context(conn, ctx, today)
        except Exception:
            log.warning("30일 풀 컨텍스트 빌드 실패", exc_info=True)
    elif provider in _MID_PROVIDERS:
        # Claude/OpenAI: 14일 + 의도별
        try:
            _add_mid_14d_context(conn, ctx, today)
        except Exception:
            log.warning("14일 컨텍스트 빌드 실패", exc_info=True)

    # 3. 의도별 추가 컨텍스트 (모든 provider 공통)
    if target_date and intent != "lookup":
        try:
            _add_lookup_context(conn, ctx, today)
        except Exception:
            log.warning("lookup 컨텍스트 빌드 실패", exc_info=True)
    builder = _INTENT_BUILDERS.get(intent)
    if builder:
        try:
            builder(conn, ctx, today)
        except Exception:
            log.warning("의도별 컨텍스트 빌드 실패 (%s)", intent, exc_info=True)

    # 4. 텍스트 조립
    return _format_chat_context(ctx, message, chat_history)


def _format_chat_context(ctx: dict, message: str,
                         chat_history: list[dict] | None = None) -> str:
    """컨텍스트 dict → 프롬프트 텍스트."""
    lines: list[str] = [f"## 러너 현재 상태 ({ctx['date']})"]

    # 주요 지표
    metrics = []
    for name in ["UTRS", "CIRS", "ACWR", "DI", "RTTI"]:
        v = ctx.get(name)
        if v is not None:
            metrics.append(f"{name}={v}")
    if ctx.get("ctl"):
        metrics.append(f"CTL={ctx['ctl']}")
    if ctx.get("tsb") is not None:
        metrics.append(f"TSB={ctx['tsb']:+.1f}")
    if ctx.get("vo2max"):
        metrics.append(f"VO2Max={ctx['vo2max']}")
    if metrics:
        lines.append("주요 지표: " + " | ".join(metrics))

    # 웰니스
    w = ctx.get("wellness")
    if w:
        parts = []
        if w.get("bb") is not None:
            parts.append(f"바디배터리={w['bb']}")
        if w.get("sleep") is not None:
            parts.append(f"수면={w['sleep']}")
        if w.get("hrv") is not None:
            parts.append(f"HRV={int(w['hrv'])}ms")
        if w.get("stress") is not None:
            parts.append(f"스트레스={int(w['stress'])}")
        if w.get("rhr") is not None:
            parts.append(f"안정심박={int(w['rhr'])}")
        if parts:
            lines.append("오늘 컨디션: " + " | ".join(parts))

    # 러너 프로필 (있으면)
    rp = ctx.get("runner_profile", {})
    if rp:
        rp_parts = []
        if rp.get("weekly_avg_km"):
            rp_parts.append(f"주간 평균 {rp['weekly_avg_km']}km/{rp.get('weekly_avg_runs', '?')}회")
        if rp.get("avg_pace"):
            rp_parts.append(f"평균 페이스 {rp['avg_pace']}/km")
        if rp.get("vo2max"):
            rp_parts.append(f"VO2Max={rp['vo2max']}")
        if rp.get("vdot_adj"):
            rp_parts.append(f"VDOT={rp['vdot_adj']}")
        if rp.get("goal"):
            dday = f" D-{rp['race_dday']}" if rp.get("race_dday") else ""
            rp_parts.append(f"목표: {rp['goal']}{dday}")
        if rp_parts:
            lines.append("프로필: " + " | ".join(rp_parts))

    # ── 풍부한 컨텍스트 (Gemini/Claude용) ──

    # 30일 전체 활동 (Gemini)
    acts_30d = ctx.get("activities_30d", [])
    if acts_30d:
        lines.append(f"\n### 최근 30일 활동 ({len(acts_30d)}개)")
        for a in acts_30d:
            dur = _fmt_sec(a.get("sec")) if a.get("sec") else "-"
            name = a.get("name") or "러닝"
            lines.append(f"- {a['date']} {name}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}, {dur}")

    # 14일 활동 (Claude/OpenAI)
    acts_14d = ctx.get("activities_14d", [])
    if acts_14d and not acts_30d:
        lines.append(f"\n### 최근 14일 활동 ({len(acts_14d)}개)")
        for a in acts_14d:
            lines.append(f"- {a['date']}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}")

    # 최근 활동 3개 (Groq/rule — 위 데이터가 없을 때만)
    if not acts_30d and not acts_14d:
        recent = ctx.get("recent_activities", [])
        if recent:
            lines.append("\n### 최근 활동")
            for a in recent:
                pace = seconds_to_pace(a["pace"]) if a.get("pace") else "-"
                lines.append(f"- {a['date']}: {a.get('km', '-')}km, {pace}/km, HR {a.get('hr', '-')}")

    # 30일 일별 메트릭 (Gemini)
    dm_30d = ctx.get("daily_metrics_30d", {})
    if dm_30d:
        lines.append(f"\n### 30일 메트릭 추세 ({len(dm_30d)}일)")
        for d in sorted(dm_30d.keys()):
            vals = dm_30d[d]
            parts = [f"{k}={v}" for k, v in vals.items()]
            lines.append(f"- {d}: {', '.join(parts)}")

    # 30일 웰니스 (Gemini)
    w30 = ctx.get("wellness_30d", [])
    if w30:
        lines.append(f"\n### 30일 웰니스 ({len(w30)}일)")
        for d in w30:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')} RHR={d.get('rhr', '-')}")

    # 14일 웰니스 (Claude/OpenAI)
    w14 = ctx.get("wellness_14d", [])
    if w14 and not w30:
        lines.append(f"\n### 14일 웰니스 ({len(w14)}일)")
        for d in w14:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')}")

    # 30일 피트니스 (Gemini)
    f30 = ctx.get("fitness_30d", [])
    if f30:
        lines.append(f"\n### 30일 피트니스 ({len(f30)}일)")
        for d in f30[-10:]:  # 최근 10일만 표시 (나머지는 추세 파악용)
            lines.append(f"- {d['date']}: CTL={d.get('ctl', '-')} ATL={d.get('atl', '-')} "
                        f"TSB={d.get('tsb', '-')}")
        if len(f30) > 10:
            lines.append(f"  (이전 {len(f30)-10}일 데이터 포함)")

    # 레이스 이력
    rh = ctx.get("race_history", [])
    if rh:
        lines.append(f"\n### 레이스 이력 ({len(rh)}개)")
        for r in rh:
            dur = _fmt_sec(r.get("sec")) if r.get("sec") else "-"
            lines.append(f"- {r['date']} {r.get('name', '레이스')}: "
                        f"{r.get('km', '-')}km, {r.get('pace', '-')}/km, {dur}")

    # 같은 유형 과거 활동
    sim = ctx.get("similar_activities")
    if sim:
        lines.append(f"\n### 오늘과 같은 유형({sim['type']}) 과거 활동")
        for a in sim["history"]:
            lines.append(f"- {a['date']}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('hr', '-')}")

    # ── 의도별 추가 데이터 ──

    # 오늘 활동 상세
    td = ctx.get("today_detail")
    if td:
        lines.append(f"\n### 오늘 활동 상세")
        lines.append(f"- {td.get('distance_km', '-')}km, {td.get('pace', '-')}/km, "
                     f"HR {td.get('avg_hr', '-')}/{td.get('max_hr', '-')}")
        if td.get("workout_type"):
            lines.append(f"- 분류: {td['workout_type']}")
        if td.get("metrics"):
            m = td["metrics"]
            for k, v in m.items():
                lines.append(f"- {k}: {v}")
    elif ctx.get("intent") == "today":
        lines.append("\n### 오늘 활동: 아직 없음")

    # 레이스 준비
    if ctx.get("darp_trend"):
        lines.append("\n### DARP/VDOT 12주 추세")
        for d in ctx["darp_trend"][-6:]:  # 최근 6개
            ts = d.get("time_sec")
            vd = d.get("vdot")
            time_str = _fmt_sec(ts) if ts else "-"
            lines.append(f"- {d['date']}: 하프 예측 {time_str}, VDOT {vd or '-'}")
    if ctx.get("di_trend"):
        recent_di = ctx["di_trend"][-3:]
        lines.append("DI 추세: " + ", ".join(f"{d['date']}={d['value']}" for d in recent_di))
    if ctx.get("goal"):
        g = ctx["goal"]
        days_left = ""
        if g.get("race_date"):
            try:
                dl = (date.fromisoformat(g["race_date"]) - date.today()).days
                days_left = f" (D-{dl})"
            except ValueError:
                pass
        lines.append(f"\n### 목표 레이스: {g.get('name', '-')} {g.get('distance_km', '')}km{days_left}")

    # 장기 비교
    if ctx.get("past_snapshots"):
        lines.append("\n### 과거 비교")
        for label, snap in ctx["past_snapshots"].items():
            parts = []
            for k in ["UTRS", "CIRS", "DI", "ctl", "vo2max"]:
                v = snap.get(k)
                if v is not None:
                    parts.append(f"{k}={v}")
            if snap.get("weekly_km"):
                parts.append(f"주간={snap['weekly_km']}km")
            if snap.get("avg_pace"):
                parts.append(f"페이스={snap['avg_pace']}")
            lines.append(f"- {label}: {' | '.join(parts) if parts else '데이터 없음'}")

    # 훈련 계획
    if ctx.get("week_plan"):
        lines.append("\n### 이번 주 계획")
        for p in ctx["week_plan"]:
            lines.append(f"- {p.get('date', '-')}: {p.get('workout_type', '-')} "
                        f"{p.get('distance_km', '')}km")
    if ctx.get("wellness_3d"):
        lines.append("\n### 웰니스 3일")
        for d in ctx["wellness_3d"]:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')}")

    # 날짜 지정 활동 조회
    if ctx.get("lookup_activities") is not None:
        ld = ctx.get("lookup_date", "")
        acts = ctx["lookup_activities"]
        if acts:
            lines.append(f"\n### {ld} 활동 ({len(acts)}개)")
            for a in acts:
                dur = _fmt_sec(a.get("duration_sec")) if a.get("duration_sec") else "-"
                lines.append(f"- {a.get('name', '러닝')}: {a.get('distance_km', '-')}km, "
                            f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}/{a.get('max_hr', '-')}, "
                            f"{dur}")
                if a.get("workout_type"):
                    lines.append(f"  분류: {a['workout_type']}")
                if a.get("metrics"):
                    m_parts = [f"{k}={v}" for k, v in a["metrics"].items()]
                    # 너무 길면 주요 메트릭만
                    if len(m_parts) > 8:
                        m_parts = m_parts[:8] + [f"외 {len(m_parts)-8}개"]
                    lines.append(f"  메트릭: {', '.join(m_parts)}")
        else:
            lines.append(f"\n### {ld}: 활동 기록 없음")

        # 해당 날짜 일별 메트릭
        dm = ctx.get("lookup_day_metrics", {})
        if dm:
            dm_parts = [f"{k}={v}" for k, v in list(dm.items())[:10]]
            lines.append(f"일별 메트릭: {', '.join(dm_parts)}")

        # 해당 날짜 웰니스
        lw = ctx.get("lookup_wellness")
        if lw:
            lines.append(f"컨디션: BB={lw.get('bb', '-')} 수면={lw.get('sleep', '-')} "
                        f"HRV={lw.get('hrv', '-')} 스트레스={lw.get('stress', '-')}")

    # 회복 상세
    if ctx.get("wellness_7d"):
        lines.append("\n### 웰니스 7일 추세")
        for d in ctx["wellness_7d"]:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')}")
    if ctx.get("hrv_baseline"):
        bl = ctx["hrv_baseline"]
        lines.append(f"HRV 기준선: {bl.get('low', '-')}~{bl.get('high', '-')} ms")
    if ctx.get("cirs_7d"):
        lines.append("CIRS 7일: " + ", ".join(f"{d['date'][-5:]}={d['value']}" for d in ctx["cirs_7d"]))

    # 대화 이력 (맥락 유지)
    if chat_history:
        lines.append("\n### 최근 대화")
        for msg in chat_history[-3:]:
            role = "사용자" if msg.get("role") == "user" else "코치"
            content = msg.get("content", "")[:200]
            lines.append(f"- {role}: {content}")

    return "\n".join(lines)


def _fmt_sec(sec) -> str:
    """초를 H:MM:SS로."""
    if sec is None:
        return "-"
    s = int(sec)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
