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


def detect_intent(message: str) -> str:
    """사용자 메시지에서 의도 감지. 복수 매칭 시 우선순위 적용."""
    msg = message.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return intent
    return "general"


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

_INTENT_BUILDERS = {
    "today": _add_today_context,
    "race": _add_race_context,
    "compare": _add_compare_context,
    "plan": _add_plan_context,
    "recovery": _add_recovery_context,
}


def build_chat_context(conn: sqlite3.Connection, message: str,
                       chat_history: list[dict] | None = None) -> str:
    """사용자 질문 의도에 맞는 풍부한 컨텍스트 텍스트 생성.

    Args:
        conn: DB 연결.
        message: 사용자 메시지.
        chat_history: 최근 대화 이력 (맥락 유지용).
    """
    today = date.today().isoformat()
    intent = detect_intent(message)

    # 1. 기본 컨텍스트
    ctx = _build_base_context(conn, today)
    ctx["intent"] = intent

    # 2. 의도별 추가 컨텍스트
    builder = _INTENT_BUILDERS.get(intent)
    if builder:
        try:
            builder(conn, ctx, today)
        except Exception:
            log.warning("의도별 컨텍스트 빌드 실패 (%s)", intent, exc_info=True)

    # 3. 텍스트 조립
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

    # 최근 활동
    recent = ctx.get("recent_activities", [])
    if recent:
        lines.append("\n### 최근 활동")
        for a in recent:
            pace = seconds_to_pace(a["pace"]) if a.get("pace") else "-"
            lines.append(f"- {a['date']}: {a.get('km', '-')}km, {pace}/km, HR {a.get('hr', '-')}")

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
