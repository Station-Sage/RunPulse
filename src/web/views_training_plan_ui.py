"""훈련탭 — AI 추천 / 훈련 계획 개요 / 동기화 상태 렌더러.

S6:  render_ai_recommendation
S6b: render_plan_overview
S7:  render_sync_status
"""
from __future__ import annotations

import sqlite3

from src.web.views_training_shared import _TYPE_STYLE, _esc

# ── S6: AI 훈련 추천 ──────────────────────────────────────────────────

def render_ai_recommendation(
    utrs_val: float | None,
    cirs_val: float | None,
    cirs_json: dict,
    workouts: list[dict],
    config: dict | None = None,
    conn: "sqlite3.Connection | None" = None,
    ai_override: str | None = None,
) -> str:
    """AI 우선 훈련 추천 카드. 규칙 기반 fallback."""
    if utrs_val is None and cirs_val is None:
        return ""

    lines: list[str] = _build_rule_recommendation(utrs_val, cirs_val, cirs_json, workouts)
    rule_msg = "</p><p style='margin:8px 0;'>".join(lines) if lines else ""

    ai_msg = ai_override
    if ai_msg:
        lines = [ai_msg]

    if not lines:
        return ""

    content = "</p><p style='margin:8px 0;'>".join(lines)
    ai_badge = (
        " <span style='font-size:0.65rem;color:var(--cyan);'>AI</span>"
        if ai_msg and ai_msg != rule_msg else ""
    )

    return (
        "<div style='background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));"
        "border-radius:20px;padding:24px;margin-top:16px;margin-bottom:16px;"
        "border:1px solid rgba(0,212,255,0.3);'>"
        "<div style='display:flex;align-items:center;gap:12px;margin-bottom:14px;'>"
        "<div style='width:44px;height:44px;background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "border-radius:50%;display:flex;align-items:center;justify-content:center;"
        "font-size:22px;'>🤖</div>"
        f"<span style='font-size:16px;font-weight:bold;'>AI 훈련 추천{ai_badge}</span></div>"
        f"<div style='font-size:13px;line-height:1.7;color:rgba(255,255,255,0.9);'>"
        f"<p style='margin:0 0 8px;'>{content}</p></div></div>"
    )


def _build_rule_recommendation(
    utrs_val: float | None,
    cirs_val: float | None,
    cirs_json: dict,
    workouts: list[dict],
) -> list[str]:
    """규칙 기반 훈련 추천 메시지."""
    lines: list[str] = []

    if utrs_val is not None:
        if utrs_val >= 70:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "고강도 훈련 준비가 완료되었습니다."
            )
        elif utrs_val >= 40:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "보통 수준입니다. 중강도 훈련을 권장합니다."
            )
        else:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "회복이 필요합니다. 가벼운 운동이나 휴식을 권장합니다."
            )

    if cirs_val is not None:
        grade = cirs_json.get("grade", "")
        if cirs_val >= 70:
            lines.append(
                f"⚠️ <strong>CIRS {cirs_val:.0f}</strong> — "
                "부상 위험이 높습니다. 훈련 강도를 줄이세요."
            )
        elif cirs_val >= 40:
            lines.append(
                f"CIRS {cirs_val:.0f} ({grade}) — "
                "부상 위험 보통. 워밍업과 쿨다운을 충실히 하세요."
            )

    key_workouts = [
        w for w in workouts
        if w.get("workout_type") in ("interval", "tempo", "long")
        and not w.get("completed")
    ]
    if key_workouts:
        tips: list[str] = []
        for w in key_workouts[:3]:
            wtype = w.get("workout_type", "")
            label = _TYPE_STYLE.get(wtype, ("", wtype, ""))[1]
            d = w.get("distance_km")
            wdate = w.get("date", "")
            d_str = f" {d:.1f}km" if d else ""
            tips.append(f"{wdate} {label}{d_str}")
        if tips:
            lines.append("이번 주 핵심 훈련: " + " / ".join(tips))

    return lines


# ── S6b: 전체 훈련 계획 개요 ──────────────────────────────────────────

_PHASE_INFO: dict[str, tuple[str, str, str]] = {
    "base":  ("기초 체력", "#27ae60", "유산소 기반 구축. 볼륨 점진 증가."),
    "build": ("강화",     "#e67e22", "강도 증가. 템포/인터벌 도입."),
    "peak":  ("정점",     "#e74c3c", "최고 강도. 레이스 시뮬레이션."),
    "taper": ("테이퍼",   "#8e44ad", "볼륨 감소. 신선도 확보."),
}


def render_plan_overview(
    goal: dict | None,
    current_phase: str = "base",
    weeks_left: int | None = None,
) -> str:
    """전체 훈련 계획 개요 — 단계별 타임라인."""
    if not goal or not goal.get("race_date"):
        return ""

    from datetime import date as _date
    try:
        race = _date.fromisoformat(goal["race_date"])
        today = _date.today()
        total_weeks = max(1, (race - today).days // 7)
    except ValueError:
        return ""

    if total_weeks <= 0:
        return ""

    phases = []
    if total_weeks > 16:
        phases.append(("base", total_weeks - 16))
        phases.append(("build", 8))
        phases.append(("peak", 5))
        phases.append(("taper", 3))
    elif total_weeks > 8:
        phases.append(("build", total_weeks - 8))
        phases.append(("peak", 5))
        phases.append(("taper", 3))
    elif total_weeks > 3:
        phases.append(("peak", total_weeks - 3))
        phases.append(("taper", 3))
    else:
        phases.append(("taper", total_weeks))

    bar_parts = ""
    for phase, weeks in phases:
        label, color, _ = _PHASE_INFO[phase]
        pct = weeks / total_weeks * 100
        is_current = phase == current_phase
        border = "border:2px solid #fff;" if is_current else ""
        bar_parts += (
            f"<div style='flex:{pct};background:{color};padding:4px 6px;font-size:10px;"
            f"color:#fff;text-align:center;white-space:nowrap;{border}'>"
            f"{label} {weeks}주</div>"
        )

    phase_label, phase_color, phase_desc = _PHASE_INFO.get(current_phase, _PHASE_INFO["base"])
    wl_str = f"D-{(weeks_left or 0) * 7}" if weeks_left else ""

    return (
        "<div class='card' style='margin-top:16px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>"
        f"<h3 style='margin:0;font-size:1rem;'>📋 전체 훈련 계획</h3>"
        f"<span style='font-size:0.85rem;color:var(--cyan);'>"
        f"{goal.get('name', '')} · {total_weeks}주 남음 {wl_str}</span></div>"
        f"<div style='display:flex;border-radius:8px;overflow:hidden;height:28px;margin-bottom:10px;'>"
        f"{bar_parts}</div>"
        f"<div style='display:flex;align-items:center;gap:8px;'>"
        f"<span style='background:{phase_color};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:12px;font-weight:600;'>현재: {phase_label}</span>"
        f"<span style='font-size:0.82rem;color:var(--muted);'>{phase_desc}</span></div>"
        "</div>"
    )


# ── S7: 캘린더 연동 상태 ──────────────────────────────────────────────

_SERVICE_LABEL: dict[str, tuple[str, str]] = {
    "garmin":    ("⌚", "Garmin Connect"),
    "strava":    ("🏃", "Strava"),
    "intervals": ("📊", "Intervals.icu"),
    "runalyze":  ("📈", "Runalyze"),
}


def render_sync_status(sync_info: list[dict]) -> str:
    """소스별 동기화 상태 표시."""
    if not sync_info:
        return ""

    has_recent = any(s.get("status") == "completed" for s in sync_info)
    status_dot = (
        "<div style='display:flex;align-items:center;gap:6px;font-size:12px;"
        + (f"color:#00ff88;'>"
           "<span style='width:7px;height:7px;background:#00ff88;border-radius:50%;"
           "display:inline-block;'></span>동기화 완료"
           if has_recent else
           "color:var(--muted);'>"
           "<span style='width:7px;height:7px;background:var(--muted);border-radius:50%;"
           "display:inline-block;'></span>대기 중")
        + "</div>"
    )

    platforms = ""
    for s in sync_info:
        svc = s.get("service", "")
        icon, label = _SERVICE_LABEL.get(svc, ("📌", svc))
        last = s.get("last_sync", "")
        short_date = last[:16] if last else "—"
        platforms += (
            f"<div style='display:flex;align-items:center;gap:8px;"
            f"background:rgba(255,255,255,0.08);border-radius:20px;"
            f"padding:8px 14px;font-size:12px;'>"
            f"<span>{icon}</span>"
            f"<span>{_esc(label)}</span>"
            f"<span style='color:var(--muted);font-size:10px;'>{short_date}</span>"
            f"</div>"
        )

    return (
        "<div class='card'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:14px;'>"
        "<span style='font-size:16px;font-weight:bold;'>데이터 연동</span>"
        + status_dot
        + "</div>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;'>{platforms}</div>"
        "</div>"
    )
