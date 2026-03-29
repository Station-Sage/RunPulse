"""대시보드 권장/예측 카드 — 훈련 권장 + DARP + 게이지/RMR."""
from __future__ import annotations

import html as _html

from .helpers import (
    METRIC_DESCRIPTIONS,
    fmt_pace,
    no_data_card,
    svg_radar_chart,
    svg_semicircle_gauge,
    tooltip,
)


def _render_gauge_card(title: str, value: float | None, max_value: float,
                       color_stops: list, subtitle: str = "", extra_html: str = "",
                       grade_label: str = "") -> str:
    """반원 게이지 카드."""
    if value is None:
        return no_data_card(title)
    gauge = svg_semicircle_gauge(value, max_value, grade_label, color_stops, width=200)
    return (
        f"<div class='card' style='text-align:center;'>"
        f"<h2 style='margin-bottom:0.3rem;font-size:1rem;'>{_html.escape(title)}</h2>"
        f"<p class='muted' style='margin:0 0 0.5rem;font-size:0.8rem;'>{_html.escape(subtitle)}</p>"
        f"{gauge}{extra_html}</div>"
    )


def _render_rmr_card(axes: dict, compare_axes: dict | None = None,
                     config: dict | None = None, conn=None,
                     ai_override: str | None = None) -> str:
    """RMR 러너 성숙도 레이더 카드."""
    if not axes:
        return no_data_card("RMR 러너 성숙도 레이더")
    from datetime import date as _date, timedelta as _td
    radar = svg_radar_chart(axes, max_value=100.0, compare_axes=compare_axes, width=260)
    overall = sum(axes.values()) / len(axes) if axes else 0
    today = _date.today()
    period_text = f"최근 28일 기준 ({(today - _td(days=28)).strftime('%m/%d')}~{today.strftime('%m/%d')})"
    compare_note = (f"<p class='muted' style='margin:0.3rem 0 0;font-size:0.78rem;'>"
                    f"&#128993; 3개월 전 대비</p>"
                   if compare_axes else "")
    rmr_tip = tooltip("RMR 러너 성숙도", METRIC_DESCRIPTIONS.get("RMR", ""))
    return (
        "<div class='card' style='text-align:center;'>"
        f"<h2 style='margin-bottom:0.3rem;font-size:1rem;'>{rmr_tip}</h2>"
        f"<p class='muted' style='margin:0 0 0.5rem;font-size:0.78rem;'>"
        f"종합 {overall:.1f}점 · {period_text}</p>"
        f"{radar}{compare_note}"
        + _rmr_ai_note(axes, config, conn, ai_override=ai_override)
        + "</div>"
    )


def _rmr_ai_note(axes: dict, config, conn, ai_override: str | None = None) -> str:
    """RMR AI 강점/약점 분석."""
    msg = ai_override
    if not msg:
        return ""
    return (f"<p style='text-align:left;margin-top:0.4rem;font-size:0.78rem;"
            f"color:var(--secondary);'>💡 {msg}</p>")


def _render_training_recommendation(utrs_val: float | None, utrs_json: dict,
                                    cirs_val: float | None, tsb_last: float | None,
                                    config: dict | None = None, conn=None,
                                    ai_override: str | None = None,
                                    acwr_val: float | None = None,
                                    di_val: float | None = None,
                                    planned_workout: dict | None = None) -> str:
    """오늘의 훈련 권장 카드 — AI 우선, 규칙 기반 fallback.

    UTRS만 보지 않고 ACWR/CIRS/DI를 종합해 강도 조정:
      - CIRS ≥75: 완전 휴식 (부상 위험)
      - UTRS < 40 또는 TSB < -30: 완전 휴식
      - ACWR 적정(1.0-1.3) + CIRS < 30 + DI > 80 → UTRS 등급 한 단계 상향 보정
      - ACWR 과부하(> 1.5) 또는 TSB < -20 → 한 단계 하향 보정
    """
    if utrs_val is None and cirs_val is None:
        return no_data_card("오늘의 훈련 권장", "데이터 수집 중입니다")
    grade = (utrs_json or {}).get("grade", "")
    effective_level = 0  # 0=휴식, 1=가벼운, 2=중강도, 3=고강도

    if cirs_val and cirs_val >= 75:
        icon, intensity, desc, dur = "&#128683;", "완전 휴식", "부상 위험 매우 높음. 훈련 중단, 회복 집중.", ""
    elif not utrs_val:
        icon, intensity, desc, dur = "&#128310;", "데이터 부족", "UTRS 데이터가 부족합니다.", ""
    elif grade == "rest" or utrs_val < 40:
        icon, intensity, desc, dur = "&#128564;", "완전 휴식 권장", "피로 회복 집중. 스트레칭만 권장.", "15-20분 이내"
        effective_level = 0
    else:
        if utrs_val < 60:
            base_level = 1
        elif utrs_val < 75:
            base_level = 2
        else:
            base_level = 3

        boost = (
            acwr_val is not None and 1.0 <= acwr_val <= 1.3
            and (cirs_val is None or cirs_val < 30)
            and (di_val is None or di_val > 80)
        )
        suppress = acwr_val is not None and acwr_val > 1.5

        if boost and not suppress:
            effective_level = min(base_level + 1, 3)
        elif suppress:
            effective_level = max(base_level - 1, 1)
        else:
            effective_level = base_level

        if effective_level == 1:
            icon, intensity, desc, dur = "&#128694;", "가벼운 활동", "이지런 또는 회복런 권장.", "30-40분, Z1-Z2"
        elif effective_level == 2:
            icon, intensity, desc, dur = "&#127939;", "중강도 훈련", "템포런 또는 유산소 훈련 가능.", "40-60분, Z2-Z3"
        else:
            icon, intensity, desc, dur = "&#128293;", "고강도 훈련 최적", "인터벌, 레이스페이스 훈련 최적 상태.", "60분+, Z4-Z5 포함"

    if ai_override:
        desc = ai_override

    planned_html = ""
    if planned_workout and planned_workout.get("type") != "rest":
        pw_type = planned_workout.get("type", "")
        pw_dist = planned_workout.get("distance_km")
        pw_desc = planned_workout.get("description", "")
        _pw_level_map = {"recovery": 0, "easy": 1, "long": 1, "tempo": 2, "threshold": 2, "interval": 3, "race": 3}
        pw_level = _pw_level_map.get(pw_type, 1)
        _type_labels = {"easy": "이지런", "long": "장거리런", "tempo": "템포런",
                        "threshold": "역치런", "interval": "인터벌", "race": "레이스", "recovery": "회복런"}
        pw_label = _type_labels.get(pw_type, pw_type)
        dist_str = f" {pw_dist:.1f}km" if pw_dist else ""

        if not utrs_val or utrs_val < 40:
            plan_advice = f"계획된 {pw_label}{dist_str}은 오늘 컨디션에 너무 과합니다. 대체: 완전 휴식 또는 회복런."
            plan_color = "var(--red)"
        elif effective_level >= pw_level:
            plan_advice = f"계획된 {pw_label}{dist_str} — 컨디션 양호, 계획대로 진행하세요."
            plan_color = "var(--green,#27ae60)"
        elif effective_level == pw_level - 1:
            _downgrade = {"interval": "템포런", "tempo": "이지런", "threshold": "이지런", "long": "이지런"}
            alt = _downgrade.get(pw_type, "이지런")
            plan_advice = f"계획된 {pw_label}{dist_str}을 {alt}으로 강도 낮춰 진행 권장."
            plan_color = "var(--orange)"
        else:
            plan_advice = f"계획된 {pw_label}{dist_str} — 오늘은 건너뛰고 내일로 미루는 것을 권장합니다."
            plan_color = "var(--red)"

        planned_html = (
            f"<div style='margin-top:0.5rem;padding:0.4rem 0.6rem;"
            f"background:rgba(255,255,255,0.05);border-radius:6px;"
            f"border-left:3px solid {plan_color};'>"
            f"<div style='font-size:0.75rem;color:var(--muted);margin-bottom:0.15rem;'>📋 오늘 계획</div>"
            f"<div style='font-size:0.8rem;color:{plan_color};'>{plan_advice}</div>"
            f"</div>"
        )
    elif planned_workout and planned_workout.get("type") == "rest":
        planned_html = (
            "<div style='margin-top:0.5rem;padding:0.4rem 0.6rem;"
            "background:rgba(255,255,255,0.05);border-radius:6px;"
            "border-left:3px solid var(--muted);'>"
            "<div style='font-size:0.8rem;color:var(--muted);'>📋 오늘 계획: 휴식일</div>"
            "</div>"
        )

    notes = ""
    if tsb_last is not None and tsb_last < -30:
        notes += f"<p style='color:var(--red);font-size:0.78rem;margin-top:0.3rem;'>&#9888; TSB {tsb_last:.0f} — 과부하. 휴식 우선</p>"
    elif tsb_last is not None and tsb_last < -20:
        notes += f"<p style='color:var(--orange);font-size:0.78rem;margin-top:0.3rem;'>&#9889; TSB {tsb_last:.0f} — 누적 피로 높음. 강도 조절 권장</p>"
    if cirs_val and 50 <= cirs_val < 75:
        notes += f"<p style='color:var(--orange);font-size:0.78rem;margin-top:0.3rem;'>&#127973; CIRS {cirs_val:.0f} — 부상 주의. 충격 운동 자제</p>"
    if acwr_val is not None and acwr_val > 1.5:
        notes += f"<p style='color:var(--red);font-size:0.78rem;margin-top:0.3rem;'>&#9888; ACWR {acwr_val:.2f} — 훈련 급증. 강도 낮춤</p>"
    elif acwr_val is not None and acwr_val > 1.3:
        notes += f"<p style='color:var(--orange);font-size:0.78rem;margin-top:0.3rem;'>&#9889; ACWR {acwr_val:.2f} — 부하 주의</p>"
    dur_html = f"<div style='font-size:0.8rem;color:var(--secondary);margin-top:0.1rem;'>&#8987; {dur}</div>" if dur else ""
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>오늘의 훈련 권장</h2>"
        "<div style='display:flex;align-items:center;gap:0.8rem;'>"
        f"<div style='font-size:2.2rem;'>{icon}</div>"
        "<div>"
        f"<div style='font-size:0.95rem;font-weight:700;color:var(--cyan);'>{intensity}</div>"
        f"<div style='font-size:0.8rem;color:var(--muted);margin-top:0.1rem;'>{desc}</div>"
        f"{dur_html}</div></div>"
        f"{planned_html}{notes}</div>"
    )


def _render_darp_mini(darp_data: dict, vdot: float | None = None,
                      vdot_adj: float | None = None,
                      di: float | None = None,
                      goal_dist_key: str | None = None) -> str:
    """DARP 레이스 예측 미니 카드 + VDOT/DI/Shape/EF 배지."""
    if not darp_data:
        return no_data_card("레이스 예측 (DARP)", "VDOT 데이터 수집 중입니다")

    _badge = lambda lbl, val, clr: (
        f"<span style='background:rgba(255,255,255,0.06);border:1px solid {clr};"
        f"color:{clr};border-radius:12px;padding:2px 8px;font-size:0.72rem;"
        f"font-weight:600;white-space:nowrap;'>{lbl} {val}</span>"
    )
    badges = []
    if vdot is not None:
        _vdot_str = f"{vdot:.1f}"
        if vdot_adj and abs(vdot - vdot_adj) > 0.3:
            _vdot_str += f" (보정 {vdot_adj:.1f})"
        badges.append(_badge("VDOT", _vdot_str, "var(--cyan)"))
    if di is not None:
        di_clr = "var(--green)" if di >= 70 else "var(--orange)" if di >= 40 else "var(--red)"
        badges.append(_badge("DI", f"{di:.0f}" if di >= 2 else f"{di:.2f}", di_clr))
    _fallback = ("half", "full", "10k", "5k")
    _target_keys = (
        (goal_dist_key,) + tuple(k for k in _fallback if k != goal_dist_key)
        if goal_dist_key else _fallback
    )
    _sample = {}
    _sample_key = None
    for _tk in _target_keys:
        if _tk in darp_data and isinstance(darp_data[_tk], dict):
            _sample = darp_data[_tk]
            _sample_key = _tk
            break
    if not _sample:
        _sample = next((d for d in darp_data.values() if isinstance(d, dict)), {})
    _sh = _sample.get("race_shape")
    _ef = _sample.get("ef")
    if _sh is not None:
        sh_clr = "var(--green)" if _sh >= 70 else "var(--orange)" if _sh >= 50 else "var(--red)"
        _sh_dist_labels = {"5k": "5K Shape", "10k": "10K Shape", "half": "Half Shape", "full": "Full Shape"}
        _sh_badge_label = _sh_dist_labels.get(_sample_key, "Shape")
        badges.append(_badge(_sh_badge_label, f"{_sh:.0f}%", sh_clr))
    if _ef is not None:
        ef_clr = "var(--green)" if _ef >= 1.0 else "var(--orange)"
        badges.append(_badge("EF", f"{_ef:.2f}", ef_clr))
    badge_row = (
        f"<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:0.5rem;'>"
        f"{''.join(badges)}</div>"
    ) if badges else ""

    _LABELS = {"5k": "5K", "10k": "10K", "half": "하프", "full": "마라톤"}
    rows = ""
    for key, lbl in _LABELS.items():
        d = darp_data.get(key)
        if not d:
            continue
        ts = int(d.get("time_sec") or 0)
        pace = d.get("pace_sec_km") or 0
        if ts <= 0 and pace > 0:
            _dist = {"5k": 5, "10k": 10, "half": 21.0975, "full": 42.195}.get(key, 21)
            ts = int(pace * _dist)
        h, rem = divmod(ts, 3600)
        m, s = divmod(rem, 60)
        t_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        rows += (f"<tr><td style='padding:0.28rem 0.5rem;font-size:0.83rem;'>{lbl}</td>"
                 f"<td style='padding:0.28rem 0.5rem;font-size:0.83rem;font-weight:700;color:var(--cyan);'>{t_str}</td>"
                 f"<td style='padding:0.28rem 0.5rem;font-size:0.8rem;color:var(--muted);'>{fmt_pace(pace)}/km</td></tr>")
    if not rows:
        return no_data_card("레이스 예측 (DARP)", "VDOT 데이터 수집 중입니다")
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>레이스 예측 (DARP)</h2>"
        + badge_row
        + f"<table style='width:100%;border-collapse:collapse;'>{rows}</table></div>"
    )
