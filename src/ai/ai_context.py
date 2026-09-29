"""Phase 5 AI 컨텍스트 빌더 — 서비스 레이어 기반 LLM 프롬프트 생성.

build_daily_briefing()/build_activity_analysis()/build_ai_context()는 서비스 레이어만
호출(직접 SQL 없음). build_context()/format_context_text()/format_activity_context()는
Phase 5 이전부터 chat_engine_rules.py(규칙 기반 fallback)·briefing.py(클립보드 프롬프트)가
쓰던 dict 기반 컨텍스트로, analysis/training 모듈을 직접 호출하는 별도 경로다(레거시,
서비스 레이어 정책 예외 — 두 소비처 모두 서비스 레이어 도입 이전에 작성됨).

설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
"""
from __future__ import annotations

import sqlite3
from datetime import date as date_cls
from datetime import timedelta
from typing import Any

from src.services.activity_service import get_activity_detail
from src.services.dashboard_service import get_dashboard_data
from src.utils import db_helpers
from src.web.template_helpers import (
    confidence_badge,
    format_distance,
    format_duration,
    format_pace,
    format_time_prediction,
    interpret_metric_level,
)


def build_daily_briefing(conn: sqlite3.Connection, date: str | None = None) -> str:
    """오늘의 상태 요약 — LLM에 전달할 markdown 문자열."""
    data = get_dashboard_data(conn, date)
    target_date = data.get("date", "")
    lines: list[str] = [f"## 오늘의 상태 ({target_date})", ""]

    # 훈련 준비도
    readiness = data.get("readiness", {})
    lines.append("### 훈련 준비도")
    for key, display in [("utrs", "UTRS"), ("cirs", "CIRS"), ("crs", "CRS")]:
        entry = readiness.get(key)
        if not entry or entry.get("value") is None:
            continue
        val = entry["value"]
        level = interpret_metric_level(key, val)
        conf = confidence_badge(entry.get("confidence"))
        conf_str = f" [{conf}]" if conf else ""
        lines.append(f"- {display}: {val:.1f}점 ({level}){conf_str}")
    lines.append("")

    # 체력 상태
    ts = data.get("training_status", {})
    if any(ts.get(k) is not None for k in ("ctl", "atl", "tsb")):
        lines.append("### 체력 상태")
        for key, label in [("ctl", "CTL"), ("atl", "ATL"), ("tsb", "TSB")]:
            val = ts.get(key)
            if val is not None:
                lines.append(f"- {label}: {val:.1f}")
        ramp = ts.get("ramp_rate")
        if ramp is not None:
            sign = "+" if ramp >= 0 else ""
            lines.append(f"- 추세: {ts.get('training_phase', '')} (ramp_rate {sign}{ramp:.1f})")
        lines.append("")

    # 수면
    wellness = data.get("wellness", {})
    sleep_items = [
        ("sleep_score", "수면 점수", lambda v: str(v)),
        ("sleep_duration_sec", "수면 시간", format_duration),
        ("hrv_last_night", "HRV (지난밤)", lambda v: f"{v:.0f}ms"),
        ("resting_hr", "안정시 심박", lambda v: f"{v:.0f}bpm"),
    ]
    sleep_lines = []
    for col, label, fmt in sleep_items:
        val = wellness.get(col)
        if val is not None:
            sleep_lines.append(f"- {label}: {fmt(val)}")
    if sleep_lines:
        lines.append("### 수면")
        lines.extend(sleep_lines)
        lines.append("")

    # 레이스 예측
    rp = data.get("race_predictions", {})
    pred_items = [
        ("darp_5k", "5K"), ("darp_10k", "10K"),
        ("darp_half", "하프"), ("darp_marathon", "풀"),
    ]
    pred_parts = [
        f"{label}: {format_time_prediction(rp.get(key))}"
        for key, label in pred_items
        if rp.get(key) is not None
    ]
    if pred_parts:
        lines.append("### 레이스 예측 (DARP)")
        lines.append("- " + " | ".join(pred_parts))
        lines.append("")

    # 최근 활동
    recent = data.get("recent_activities", [])
    if recent:
        lines.append("### 최근 활동")
        for act in recent[:3]:
            dist = format_distance(act.get("distance_m"))
            dur = format_duration(act.get("duration_sec"))
            pace = format_pace(act.get("avg_pace_sec_km"))
            pace_str = f", 페이스 {pace}/km" if pace else ""
            lines.append(
                f"- {act.get('name', '')} {dist}, {dur}{pace_str}"
            )

    return "\n".join(lines)


def build_activity_analysis(conn: sqlite3.Connection, activity_id: int) -> str:
    """활동 분석 컨텍스트 — LLM에 전달할 markdown 문자열."""
    detail = get_activity_detail(conn, activity_id)
    core = detail.get("core", {})
    metrics = detail.get("metrics_by_category", {})
    comparison = detail.get("source_comparison", {})

    name = core.get("name", f"활동 #{activity_id}")
    start = (core.get("start_time") or "")[:10]
    lines: list[str] = [f"## 활동 분석: {name} ({start})", ""]

    # 기본 정보
    lines.append("### 기본 정보")
    dist = format_distance(core.get("distance_m"))
    dur = format_duration(core.get("duration_sec"))
    pace = format_pace(core.get("avg_pace_sec_km"))
    if dist or dur:
        lines.append(f"- 거리: {dist} | 시간: {dur}" + (f" | 페이스: {pace}/km" if pace else ""))
    avg_hr = core.get("avg_hr")
    max_hr = core.get("max_hr")
    if avg_hr:
        max_str = f" | 최대: {max_hr}bpm" if max_hr else ""
        lines.append(f"- 평균 심박: {avg_hr}bpm{max_str}")
    elev = core.get("elevation_gain")
    if elev:
        lines.append(f"- 고도: +{elev:.0f}m")
    lines.append("")

    # RunPulse 분석 (모든 카테고리 순회)
    rp_items = []
    for category, cat_metrics in sorted(metrics.items()):
        for m in cat_metrics:
            val = m.get("numeric_value") or m.get("text_value")
            if val is None:
                continue
            metric_name = m["metric_name"]
            level = interpret_metric_level(metric_name, m.get("numeric_value"))
            level_str = f" ({level})" if level else ""
            conf = confidence_badge(m.get("confidence"))
            conf_str = f" [{conf}]" if conf else ""
            rp_items.append(f"- {metric_name}: {val}{level_str}{conf_str}")
    if rp_items:
        lines.append("### RunPulse 분석")
        lines.extend(rp_items)
        lines.append("")

    # 소스 비교
    if len(comparison) > 1:
        lines.append("### 소스 비교")
        headers = ["지표"] + list(comparison.keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for col in ("distance_m", "avg_hr", "training_load", "suffer_score"):
            vals = [format_distance(v.get(col)) if col == "distance_m"
                    else str(v.get(col) or "—")
                    for v in comparison.values()]
            lines.append("| " + col + " | " + " | ".join(vals) + " |")

    return "\n".join(lines)


def build_ai_context(
    conn: sqlite3.Connection,
    date: str | None = None,
    activity_id: int | None = None,
) -> str:
    """통합 AI 컨텍스트: daily briefing + (옵션) 활동 분석."""
    parts = [build_daily_briefing(conn, date)]
    if activity_id is not None:
        parts.append(build_activity_analysis(conn, activity_id))
    return "\n\n---\n\n".join(parts)


_RUN_TYPES = (
    "('running','run','virtualrun','treadmill','highintensityintervaltraining')"
)


def build_context(conn: sqlite3.Connection, date_str: str | None = None) -> dict:
    """규칙 기반 fallback·클립보드 프롬프트용 dict 컨텍스트.

    chat_engine_rules.rule_based_response()와 briefing.py의 프롬프트 조립 함수가
    이 dict 키를 그대로 읽는다 — 키 이름을 바꾸면 두 소비처가 동시에 깨진다.
    """
    from src.analysis.recovery import get_recovery_status
    from src.analysis.trends import calculate_acwr, weekly_trends
    from src.analysis.weekly_score import calculate_weekly_score
    from src.training.goals import get_active_goal
    from src.training.planner import get_planned_workouts

    if date_str is None:
        date_str = date_cls.today().isoformat()
    ctx: dict[str, Any] = {"date": date_str}

    row = conn.execute(
        "SELECT id, source, activity_type, start_time, distance_m, duration_sec,"
        "       avg_pace_sec_km, avg_hr"
        " FROM activity_summaries"
        f" WHERE date(start_time) = ? AND activity_type IN {_RUN_TYPES}"
        " ORDER BY start_time DESC LIMIT 1",
        (date_str,),
    ).fetchone()
    if row:
        keys = ["id", "source", "activity_type", "start_time", "distance_m",
                "duration_sec", "avg_pace_sec_km", "avg_hr"]
        act = dict(zip(keys, row))
        dist_m = act.pop("distance_m")
        act["distance_km"] = dist_m / 1000.0 if dist_m is not None else None
        ctx["today_activity"] = act
    else:
        ctx["today_activity"] = None

    try:
        ctx["recovery"] = get_recovery_status(conn, date_str)
    except Exception:
        ctx["recovery"] = {}

    pmc = db_helpers.get_primary_metrics(
        conn, "daily", date_str, names=["ctl", "atl", "tsb", "vo2max"]
    )
    pmc_map = {r["metric_name"]: r.get("numeric_value") for r in pmc}
    vo2_runalyze_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='effective_vo2max' AND provider='runalyze' AND is_primary=1"
        "   AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1"
    ).fetchone()
    ctx["fitness"] = {
        "ctl": pmc_map.get("ctl"),
        "atl": pmc_map.get("atl"),
        "tsb": pmc_map.get("tsb"),
        "vo2max_garmin": pmc_map.get("vo2max"),
        "vo2max_runalyze": vo2_runalyze_row[0] if vo2_runalyze_row else None,
    }

    try:
        wk = calculate_weekly_score(conn) or {}
        wk_data = wk.pop("data", {})
        ctx["weekly"] = {**wk, **wk_data}
    except Exception:
        ctx["weekly"] = {}

    try:
        ctx["trends_4w"] = weekly_trends(conn, weeks=4)
    except Exception:
        ctx["trends_4w"] = []

    try:
        ctx["acwr"] = calculate_acwr(conn)
    except Exception:
        ctx["acwr"] = {}

    try:
        ctx["goal"] = get_active_goal(conn)
    except Exception:
        ctx["goal"] = None

    try:
        today = date_cls.fromisoformat(date_str)
        week_start = today - timedelta(days=today.weekday())
        plans = get_planned_workouts(conn, week_start=week_start)
        ctx["plan_today"] = next((p for p in plans if p["date"] == date_str), None)
    except Exception:
        ctx["plan_today"] = None

    from src.ai.chat_readiness import attach_readiness
    attach_readiness(conn, ctx, date_str)
    return ctx


def format_context_text(ctx: dict) -> str:
    """build_context() 결과를 마크다운 텍스트로 변환.

    Returns:
        템플릿 {{CONTEXT}} 자리에 들어갈 문자열.
    """
    from src.utils.pace import seconds_to_pace

    lines: list[str] = [f"## 분석 기준일: {ctx.get('date', '-')}"]

    act = ctx.get("today_activity")
    if act:
        pace = (
            seconds_to_pace(act["avg_pace_sec_km"])
            if act.get("avg_pace_sec_km") else "-"
        )
        lines += [
            "\n### 오늘 활동",
            f"- 거리: {act.get('distance_km', '-')} km"
            f" | 페이스: {pace}/km | 평균 HR: {act.get('avg_hr', '-')} bpm",
            f"- 출처: {act.get('source', '-')}",
        ]
    else:
        lines.append("\n### 오늘 활동: 없음")

    rec = ctx.get("recovery") or {}
    raw = rec.get("raw") or {}
    detail = rec.get("detail") or {}
    lines += [
        "\n### 회복 상태",
        f"- 회복 점수: {rec.get('recovery_score', '-')} ({rec.get('grade', '-')})",
        f"- Body Battery: {raw.get('body_battery', '-')}",
        f"- 수면 점수: {raw.get('sleep_score', '-')}",
        f"- HRV: {raw.get('hrv_value', '-')} ms",
        f"- 스트레스 평균: {raw.get('stress_avg', '-')}",
        f"- 안정 심박: {raw.get('resting_hr', '-')} bpm",
    ]
    readiness = detail.get("training_readiness_score")
    hrv_avg = detail.get("overnight_hrv_avg")
    deep_sec = detail.get("sleep_stage_deep_sec")
    rem_sec = detail.get("sleep_stage_rem_sec")
    bb_delta = detail.get("body_battery_delta")
    if any(v is not None for v in [readiness, hrv_avg, deep_sec]):
        if readiness is not None:
            lines.append(f"- 훈련 준비도: {readiness}")
        if hrv_avg is not None:
            lines.append(f"- 야간 HRV 평균: {hrv_avg} ms")
        if deep_sec is not None:
            lines.append(f"- 딥 슬립: {int(deep_sec) // 60}분")
        if rem_sec is not None:
            lines.append(f"- REM 슬립: {int(rem_sec) // 60}분")
        if bb_delta is not None:
            lines.append(f"- 바디 배터리 변화: {bb_delta:+.0f}")

    fit = ctx.get("fitness") or {}
    if fit:
        ctl, atl, tsb = fit.get("ctl"), fit.get("atl"), fit.get("tsb")
        vo2 = fit.get("vo2max_garmin") or fit.get("vo2max_runalyze")
        lines += ["\n### 피트니스 지표"]
        lines.append(f"- CTL(만성부하): {ctl:.1f}" if ctl is not None else "- CTL: -")
        lines.append(f"- ATL(급성부하): {atl:.1f}" if atl is not None else "- ATL: -")
        lines.append(f"- TSB(신선도): {tsb:+.1f}" if tsb is not None else "- TSB: -")
        if vo2:
            lines.append(f"- VO2Max: {vo2:.1f}")

    acwr = ctx.get("acwr") or {}
    av = (acwr.get("average") or {}) if acwr else {}
    if av.get("acwr") is not None:
        lines += [
            "\n### 부하 비율 (ACWR)",
            f"- ACWR: {av['acwr']} ({av.get('status', '-')})",
        ]

    wk = ctx.get("weekly") or {}
    if wk:
        lines += [
            "\n### 이번 주 훈련",
            f"- 총 점수: {wk.get('total_score', '-')} ({wk.get('grade', '-')})",
            f"- 거리: {wk.get('total_distance_km', '-')} km",
            f"- 횟수: {wk.get('run_count', '-')}회",
        ]

    trends = ctx.get("trends_4w") or []
    if trends:
        lines.append("\n### 4주 추세")
        for t in trends:
            lines.append(
                f"- {t['week_start']}: {t['total_distance_km']} km ({t['run_count']}회)"
            )

    goal = ctx.get("goal")
    if goal:
        race = goal.get("race_date")
        days_str = ""
        if race:
            try:
                days_left = (date_cls.fromisoformat(race) - date_cls.today()).days
                days_str = f" (D-{days_left})"
            except ValueError:
                pass
        lines += [
            "\n### 목표",
            f"- {goal.get('name', '-')}: {goal.get('distance_km', '-')} km{days_str}",
        ]
        if goal.get("target_time_sec"):
            h, r = divmod(int(goal["target_time_sec"]), 3600)
            m, s = divmod(r, 60)
            lines.append(f"- 목표 기록: {h}:{m:02d}:{s:02d}")

    from src.ai.chat_readiness import decision_lines, plan_line
    verdict = decision_lines(ctx)
    if verdict:
        lines += ["\n### 오늘 컨디션 판정 (Today·계획 조정과 동일 기준)"] + verdict
    plan = ctx.get("plan_today")
    if plan:
        lines += [
            "\n### 오늘 계획",
            f"- {plan_line(ctx)}",
            f"- 설명: {plan.get('description', '-')}",
            f"- 근거: {plan.get('rationale', '-')}",
        ]

    return "\n".join(lines)


def format_activity_context(conn: sqlite3.Connection, activity_id: int) -> str:
    """단일 활동 deep_analyze 결과를 텍스트로 변환.

    Args:
        conn: SQLite 연결.
        activity_id: 활동 id.

    Returns:
        활동 상세 컨텍스트 텍스트.
    """
    from src.analysis.activity_deep import deep_analyze

    try:
        data = deep_analyze(conn, activity_id=activity_id)
    except Exception:
        data = None
    if not data:
        return f"## 활동 상세 — (id={activity_id} 없음)"
    act = data.get("activity") or {}

    lines = [f"## 활동 상세 — {act.get('date', '-')}"]
    lines.append(
        f"- 거리: {act.get('distance_km', '-')} km"
        f" | 페이스: {act.get('avg_pace', '-')}/km | HR: {act.get('avg_hr', '-')} bpm"
    )

    for source in ("garmin", "strava", "intervals", "runalyze"):
        src_data = data.get(source) or {}
        if src_data:
            lines.append(f"\n### {source.capitalize()} 지표")
            for k, v in src_data.items():
                if v is not None:
                    lines.append(f"- {k}: {v}")

    daily = data.get("garmin_daily_detail") or {}
    if daily:
        lines.append("\n### Garmin 당일 컨디션")
        for key, label in [
            ("training_readiness_score", "훈련 준비도"),
            ("overnight_hrv_avg", "야간 HRV 평균"),
            ("body_battery_delta", "바디 배터리 변화"),
            ("sleep_stage_deep_sec", "딥 슬립(초)"),
        ]:
            v = daily.get(key)
            if v is not None:
                lines.append(f"- {label}: {v}")

    eff = (data.get("calculated") or {}).get("efficiency") or {}
    if eff:
        lines.append("\n### 효율성")
        if eff.get("decoupling_pct") is not None:
            lines.append(f"- Cardiac Decoupling: {eff['decoupling_pct']:.1f}%")

    return "\n".join(lines)
