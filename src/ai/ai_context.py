"""분석 데이터를 AI 프롬프트 컨텍스트로 변환."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


def build_context(conn: sqlite3.Connection, date_str: str | None = None) -> dict:
    """오늘 분석 데이터를 수집하여 dict로 반환.

    Args:
        conn: SQLite 연결.
        date_str: 기준 날짜 (YYYY-MM-DD). None이면 오늘.

    Returns:
        today_activity, recovery, fitness, weekly, trends_4w, acwr, goal,
        plan_today 키를 가진 dict.
    """
    from src.analysis.recovery import get_recovery_status
    from src.analysis.trends import calculate_acwr, weekly_trends
    from src.analysis.weekly_score import calculate_weekly_score
    from src.training.goals import get_active_goal
    from src.training.planner import get_planned_workouts

    if date_str is None:
        date_str = date.today().isoformat()

    ctx: dict[str, Any] = {"date": date_str}

    # 오늘 활동 (running 계열만)
    _RUN_TYPES = "('running','run','virtualrun','treadmill','highintensityintervaltraining')"
    row = conn.execute(
        f"SELECT id, source, activity_type, start_time, distance_km, duration_sec,"
        f"       avg_pace_sec_km, avg_hr"
        f" FROM activity_summaries"
        f" WHERE date(start_time) = ? AND activity_type IN {_RUN_TYPES}"
        f" ORDER BY start_time DESC LIMIT 1",
        (date_str,),
    ).fetchone()
    ctx["today_activity"] = (
        dict(zip(
            ["id", "source", "activity_type", "start_time",
             "distance_km", "duration_sec", "avg_pace_sec_km", "avg_hr"],
            row,
        ))
        if row else None
    )

    # 회복 상태
    try:
        ctx["recovery"] = get_recovery_status(conn, date_str)
    except Exception:
        ctx["recovery"] = {}

    # 피트니스 (CTL/ATL/TSB/VO2Max) — 최근 1행
    fit_row = conn.execute(
        "SELECT date, ctl, atl, tsb, garmin_vo2max, runalyze_evo2max"
        " FROM daily_fitness ORDER BY date DESC LIMIT 1"
    ).fetchone()
    ctx["fitness"] = (
        dict(zip(["date", "ctl", "atl", "tsb", "vo2max_garmin", "vo2max_runalyze"], fit_row))
        if fit_row else {}
    )

    # 이번 주 요약
    try:
        ctx["weekly"] = calculate_weekly_score(conn)
    except Exception:
        ctx["weekly"] = {}

    # 4주 추세
    try:
        ctx["trends_4w"] = weekly_trends(conn, weeks=4)
    except Exception:
        ctx["trends_4w"] = []

    # ACWR 부상 위험도
    try:
        ctx["acwr"] = calculate_acwr(conn)
    except Exception:
        ctx["acwr"] = {}

    # 활성 목표
    try:
        ctx["goal"] = get_active_goal(conn)
    except Exception:
        ctx["goal"] = None

    # 오늘 계획
    try:
        plans = get_planned_workouts(conn)
        ctx["plan_today"] = next((p for p in plans if p["date"] == date_str), None)
    except Exception:
        ctx["plan_today"] = None

    # 훈련 계획 이행 현황 (이번 주 + 어제)
    try:
        td = date.fromisoformat(date_str)
        week_start = td - timedelta(days=td.weekday())
        week_end = week_start + timedelta(days=6)
        yesterday = (td - timedelta(days=1)).isoformat()

        # 어제 계획 상태
        yrow = conn.execute(
            "SELECT workout_type, distance_km, completed, skip_reason "
            "FROM planned_workouts WHERE date=? AND workout_type!='rest' "
            "ORDER BY id DESC LIMIT 1",
            (yesterday,),
        ).fetchone()
        if yrow:
            c = yrow[2]
            ctx["yesterday_plan"] = {
                "type": yrow[0], "km": yrow[1],
                "status": "completed" if c == 1 else "skipped" if c == -1 else "unknown",
                "skip_reason": yrow[3],
            }

        # 이번 주 이행률 (과거 날짜만)
        week_rows = conn.execute(
            "SELECT workout_type, completed FROM planned_workouts "
            "WHERE date BETWEEN ? AND ? AND date <= ? AND workout_type!='rest'",
            (week_start.isoformat(), week_end.isoformat(), date_str),
        ).fetchall()
        if week_rows:
            total = len(week_rows)
            done = sum(1 for r in week_rows if r[1] == 1)
            skipped = sum(1 for r in week_rows if r[1] == -1)
            ctx["plan_compliance"] = {
                "total": total, "completed": done, "skipped": skipped,
                "pending": total - done - skipped,
                "pct": round(done / total * 100) if total else 0,
            }
    except Exception:
        pass

    return ctx


def format_context_text(ctx: dict) -> str:
    """build_context() 결과를 마크다운 텍스트로 변환.

    Returns:
        템플릿 {{CONTEXT}} 자리에 들어갈 문자열.
    """
    from src.utils.pace import seconds_to_pace

    lines: list[str] = [f"## 분석 기준일: {ctx.get('date', '-')}"]

    # 오늘 활동
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

    # 회복 상태
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

    # 피트니스
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

    # ACWR
    acwr = ctx.get("acwr") or {}
    av = (acwr.get("average") or {}) if acwr else {}
    if av.get("acwr") is not None:
        lines += [
            "\n### 부하 비율 (ACWR)",
            f"- ACWR: {av['acwr']} ({av.get('status', '-')})",
        ]

    # 이번 주 요약
    wk = ctx.get("weekly") or {}
    if wk:
        lines += [
            "\n### 이번 주 훈련",
            f"- 총 점수: {wk.get('total_score', '-')} ({wk.get('grade', '-')})",
            f"- 거리: {wk.get('total_distance_km', '-')} km",
            f"- 횟수: {wk.get('run_count', '-')}회",
        ]

    # 4주 추세
    trends = ctx.get("trends_4w") or []
    if trends:
        lines.append("\n### 4주 추세")
        for t in trends:
            lines.append(
                f"- {t['week_start']}: {t['total_distance_km']} km ({t['run_count']}회)"
            )

    # 활성 목표
    goal = ctx.get("goal")
    if goal:
        race = goal.get("race_date")
        days_str = ""
        if race:
            try:
                days_left = (date.fromisoformat(race) - date.today()).days
                days_str = f" (D-{days_left})"
            except ValueError:
                pass
        lines += ["\n### 목표", f"- {goal.get('name', '-')}: {goal.get('distance_km', '-')} km{days_str}"]
        if goal.get("target_time_sec"):
            h, r = divmod(int(goal["target_time_sec"]), 3600)
            m, s = divmod(r, 60)
            lines.append(f"- 목표 기록: {h}:{m:02d}:{s:02d}")

    # 오늘 계획
    plan = ctx.get("plan_today")
    if plan:
        dist_str = f"{plan.get('distance_km')} km" if plan.get("distance_km") else ""
        lines += [
            "\n### 오늘 계획",
            f"- 훈련: {plan.get('workout_type', '-')} {dist_str}",
            f"- 설명: {plan.get('description', '-')}",
            f"- 근거: {plan.get('rationale', '-')}",
        ]

    # 훈련 계획 이행 현황
    yp = ctx.get("yesterday_plan")
    pc = ctx.get("plan_compliance")
    if yp or pc:
        lines.append("\n### 훈련 계획 이행 현황")
        if yp:
            _status_ko = {"completed": "완료 ✅", "skipped": "건너뜀 ❌", "unknown": "미확인 ❓"}
            status_str = _status_ko.get(yp["status"], yp["status"])
            dist_str = f" {yp['km']:.1f}km" if yp.get("km") else ""
            lines.append(f"- 어제 계획: {yp['type']}{dist_str} → {status_str}")
            if yp.get("skip_reason"):
                lines.append(f"  (사유: {yp['skip_reason']})")
        if pc:
            lines.append(
                f"- 이번 주: {pc['completed']}/{pc['total']} 완료 "
                f"({pc['pct']}%), 건너뜀 {pc['skipped']}회"
            )

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
    from src.utils.pace import seconds_to_pace

    try:
        data = deep_analyze(conn, activity_id=activity_id)
    except Exception:
        data = None
    if not data:
        return f"## 활동 상세 — (id={activity_id} 없음)"
    act = data.get("activity") or {}

    lines = [f"## 활동 상세 — {str(act.get('start_time', ''))[:10]}"]
    pace = (
        seconds_to_pace(act["avg_pace_sec_km"]) if act.get("avg_pace_sec_km") else "-"
    )
    lines.append(
        f"- 거리: {act.get('distance_km', '-')} km"
        f" | 페이스: {pace}/km | HR: {act.get('avg_hr', '-')} bpm"
    )

    # 4소스 지표
    for source in ("garmin", "strava", "intervals", "runalyze"):
        src_data = data.get(source) or {}
        if src_data:
            lines.append(f"\n### {source.capitalize()} 지표")
            for k, v in src_data.items():
                lines.append(f"- {k}: {v}")

    # Garmin 일별 상세
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

    # 효율성
    calc = data.get("calculated") or {}
    eff = calc.get("efficiency") or {}
    if eff:
        lines.append("\n### 효율성")
        if eff.get("aerobic_ef") is not None:
            lines.append(f"- Aerobic EF: {eff['aerobic_ef']:.3f}")
        if eff.get("decoupling_pct") is not None:
            lines.append(f"- Cardiac Decoupling: {eff['decoupling_pct']:.1f}%")

    return "\n".join(lines)
