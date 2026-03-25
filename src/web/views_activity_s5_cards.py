"""S5-C2 신규 메트릭 카드 — RTTI, WLEI, TPDI, Running Tolerance, HR 존 차트.

Sprint 5에서 추가된 데이터의 UI 노출.
"""
from __future__ import annotations

import html as _html
import json

from src.web.helpers import fmt_pace


def _safe_json(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


# ── RTTI (러닝 내성 훈련 지수) ───────────────────────────────────────


def render_rtti_card(day_metrics: dict, day_metric_jsons: dict) -> str:
    """RTTI 전용 카드 — 게이지 바 + 해석."""
    val = day_metrics.get("RTTI")
    if val is None:
        return ""
    v = float(val)
    j = day_metric_jsons.get("RTTI") or {}
    load = j.get("load")
    opt_max = j.get("optimal_max")
    score = j.get("tolerance_score")

    # 색상: 0~80 녹색, 80~100 노랑, 100+ 빨강
    if v <= 80:
        color, label = "#00ff88", "여유 있음"
    elif v <= 100:
        color, label = "#ffaa00", "적정 부하"
    else:
        color, label = "#ff4444", "과부하"
    pct = min(v, 150) / 150 * 100

    detail = ""
    if load is not None and opt_max is not None:
        detail = (
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;"
            f"color:var(--muted);margin-top:8px;'>"
            f"<span>부하: {float(load):.0f}</span>"
            f"<span>권장 최대: {float(opt_max):.0f}</span>"
            + (f"<span>내성 점수: {float(score):.0f}</span>" if score else "")
            + "</div>"
        )
    return (
        "<div class='card'>"
        "<h2>러닝 내성 (RTTI)</h2>"
        f"<div style='display:flex;align-items:baseline;gap:8px;margin:8px 0;'>"
        f"<span style='font-size:1.4rem;font-weight:bold;color:{color};'>{v:.1f}%</span>"
        f"<span style='font-size:0.82rem;color:var(--muted);'>{label}</span></div>"
        "<div style='background:var(--row-border);border-radius:4px;height:10px;overflow:hidden;'>"
        f"<div style='height:100%;width:{pct:.0f}%;background:{color};border-radius:4px;'></div>"
        "</div>"
        "<div style='display:flex;justify-content:space-between;font-size:0.7rem;color:var(--muted);margin-top:2px;'>"
        "<span>0%</span><span>100%</span><span>150%</span></div>"
        + detail
        + "<p class='muted' style='font-size:0.72rem;margin:8px 0 0;'>"
        "Garmin Running Tolerance 기반. 100% = 권장 한계, 초과 시 과부하</p>"
        "</div>"
    )


# ── WLEI (날씨 가중 노력 지수) ──────────────────────────────────────


def render_wlei_card(act_metrics: dict, act_metric_jsons: dict) -> str:
    """WLEI 전용 카드 — TRIMP 대비 날씨 보정 효과."""
    val = act_metrics.get("WLEI")
    if val is None:
        return ""
    v = float(val)
    j = act_metric_jsons.get("WLEI") or {}
    trimp = j.get("trimp")
    temp = j.get("temp_c")
    humidity = j.get("humidity_pct")
    temp_stress = j.get("temp_stress")
    humidity_stress = j.get("humidity_stress")

    # 보정 비율
    if trimp and float(trimp) > 0:
        ratio = v / float(trimp)
        ratio_str = f"{ratio:.2f}x"
        ratio_color = "#00ff88" if ratio < 1.1 else "#ffaa00" if ratio < 1.3 else "#ff4444"
    else:
        ratio_str = "-"
        ratio_color = "var(--muted)"

    env_rows = ""
    if temp is not None:
        env_rows += (
            f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
            f"font-size:0.82rem;border-bottom:1px solid var(--row-border);'>"
            f"<span style='color:var(--muted);'>기온</span>"
            f"<span>{float(temp):.1f}°C"
            + (f" (×{float(temp_stress):.3f})" if temp_stress else "")
            + "</span></div>"
        )
    if humidity is not None:
        env_rows += (
            f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
            f"font-size:0.82rem;border-bottom:1px solid var(--row-border);'>"
            f"<span style='color:var(--muted);'>습도</span>"
            f"<span>{float(humidity):.0f}%"
            + (f" (×{float(humidity_stress):.3f})" if humidity_stress else "")
            + "</span></div>"
        )

    return (
        "<div class='card'>"
        "<h2>날씨 가중 노력 (WLEI)</h2>"
        f"<div style='display:flex;align-items:baseline;gap:12px;margin:8px 0;'>"
        f"<span style='font-size:1.4rem;font-weight:bold;color:#00d4ff;'>{v:.1f}</span>"
        f"<span style='font-size:0.85rem;color:{ratio_color};'>보정 {ratio_str}</span>"
        + (f"<span style='font-size:0.82rem;color:var(--muted);'>TRIMP {float(trimp):.0f}</span>" if trimp else "")
        + "</div>"
        + env_rows
        + "<p class='muted' style='font-size:0.72rem;margin:8px 0 0;'>"
        "TRIMP × 기온 스트레스 × 습도 스트레스. 1.0x = 기준 환경(20°C, 60%)</p>"
        "</div>"
    )


# ── TPDI (실내/실외 퍼포먼스 격차) ──────────────────────────────────


def render_tpdi_card(day_metrics: dict, day_metric_jsons: dict) -> str:
    """TPDI 전용 카드."""
    val = day_metrics.get("TPDI")
    if val is None:
        return ""
    v = float(val)
    j = day_metric_jsons.get("TPDI") or {}
    outdoor_avg = j.get("outdoor_avg_fearp")
    indoor_avg = j.get("indoor_avg_fearp")
    n_outdoor = j.get("n_outdoor")
    n_indoor = j.get("n_indoor")

    if v > 0:
        color, label = "#00ff88", f"실외가 {abs(v):.1f}% 빠름"
    elif v < 0:
        color, label = "#ffaa00", f"실내가 {abs(v):.1f}% 빠름"
    else:
        color, label = "var(--muted)", "동일"

    detail = ""
    if outdoor_avg is not None:
        detail += f"<span>실외 평균: {fmt_pace(outdoor_avg)}/km ({n_outdoor or 0}건)</span>"
    if indoor_avg is not None:
        detail += f"<span>실내 평균: {fmt_pace(indoor_avg)}/km ({n_indoor or 0}건)</span>"
    detail_html = (
        f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;"
        f"color:var(--muted);margin-top:8px;flex-wrap:wrap;gap:4px;'>{detail}</div>"
        if detail else ""
    )

    return (
        "<div class='card'>"
        "<h2>실내/실외 격차 (TPDI)</h2>"
        f"<div style='display:flex;align-items:baseline;gap:8px;margin:8px 0;'>"
        f"<span style='font-size:1.4rem;font-weight:bold;color:{color};'>{v:+.1f}%</span>"
        f"<span style='font-size:0.82rem;color:var(--muted);'>{label}</span></div>"
        + detail_html
        + "<p class='muted' style='font-size:0.72rem;margin:8px 0 0;'>"
        "최근 8주 실내/실외 FEARP 비교. 양수=실외 유리</p>"
        "</div>"
    )


# ── Running Tolerance ────────────────────────────────────────────────


def render_running_tolerance_card(tolerance: dict) -> str:
    """Garmin Running Tolerance 원시 데이터 카드."""
    if not tolerance:
        return ""
    load = tolerance.get("running_tolerance_load")
    opt_max = tolerance.get("running_tolerance_optimal_max")
    score = tolerance.get("running_tolerance_score")

    rows = ""
    if load is not None:
        rows += (
            "<div style='display:flex;justify-content:space-between;padding:6px 0;"
            "border-bottom:1px solid var(--row-border);font-size:0.85rem;'>"
            "<span style='color:var(--muted);'>현재 부하</span>"
            f"<span style='font-weight:600;'>{float(load):.0f}</span></div>"
        )
    if opt_max is not None:
        rows += (
            "<div style='display:flex;justify-content:space-between;padding:6px 0;"
            "border-bottom:1px solid var(--row-border);font-size:0.85rem;'>"
            "<span style='color:var(--muted);'>권장 최대 부하</span>"
            f"<span style='font-weight:600;'>{float(opt_max):.0f}</span></div>"
        )
    if score is not None:
        s = float(score)
        color = "#00ff88" if s >= 70 else "#ffaa00" if s >= 40 else "#ff4444"
        rows += (
            "<div style='display:flex;justify-content:space-between;padding:6px 0;"
            "font-size:0.85rem;'>"
            "<span style='color:var(--muted);'>내성 점수</span>"
            f"<span style='font-weight:bold;color:{color};'>{s:.0f}</span></div>"
        )
    # 게이지: load vs opt_max
    gauge = ""
    if load is not None and opt_max is not None and float(opt_max) > 0:
        pct = float(load) / float(opt_max) * 100
        bar_color = "#00ff88" if pct <= 80 else "#ffaa00" if pct <= 100 else "#ff4444"
        gauge = (
            "<div style='margin-top:8px;'>"
            "<div style='background:var(--row-border);border-radius:4px;height:8px;overflow:hidden;position:relative;'>"
            f"<div style='height:100%;width:{min(pct, 100):.0f}%;background:{bar_color};border-radius:4px;'></div>"
            "<div style='position:absolute;left:66.7%;top:0;width:1px;height:100%;background:rgba(255,255,255,0.3);'></div>"
            "</div>"
            "<div style='display:flex;justify-content:space-between;font-size:0.68rem;color:var(--muted);margin-top:2px;'>"
            f"<span>0</span><span>사용률 {pct:.0f}%</span><span>{float(opt_max):.0f}</span></div>"
            "</div>"
        )
    return (
        "<div class='card'>"
        "<h2>러닝 내성 (Garmin)</h2>"
        + rows + gauge
        + "<p class='muted' style='font-size:0.72rem;margin:8px 0 0;'>"
        "Garmin Running Tolerance 원시 데이터</p>"
        "</div>"
    )


# ── HR 존 시각 차트 ──────────────────────────────────────────────────


def render_hr_zone_chart(zones: list[float | None]) -> str:
    """HR 존 1~5 시간 분포 수평 막대 차트."""
    if not any(z is not None and z > 0 for z in zones):
        return ""
    total = sum(z for z in zones if z is not None and z > 0)
    if total <= 0:
        return ""

    colors = ["#00d4ff", "#00ff88", "#ffaa00", "#ff8844", "#ff4444"]
    labels = ["존1 (회복)", "존2 (유산소)", "존3 (템포)", "존4 (역치)", "존5 (최대)"]
    bars = ""
    for i, (z, c, lb) in enumerate(zip(zones, colors, labels)):
        if z is None or z <= 0:
            continue
        pct = z / total * 100
        mins = int(z) // 60
        secs = int(z) % 60
        bars += (
            f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>"
            f"<span style='width:90px;font-size:0.78rem;color:var(--muted);text-align:right;'>{lb}</span>"
            f"<div style='flex:1;background:var(--row-border);border-radius:3px;height:18px;overflow:hidden;'>"
            f"<div style='height:100%;width:{pct:.1f}%;background:{c};border-radius:3px;"
            f"display:flex;align-items:center;padding-left:6px;'>"
            f"<span style='font-size:0.68rem;color:#000;font-weight:bold;'>"
            + (f"{mins}:{secs:02d}" if pct > 8 else "")
            + "</span></div></div>"
            f"<span style='width:50px;font-size:0.75rem;color:var(--muted);'>{pct:.0f}%</span>"
            "</div>"
        )
    return (
        "<div class='card'>"
        "<h2>HR 존 분포</h2>"
        + bars
        + f"<p class='muted' style='font-size:0.72rem;margin:8px 0 0;'>총 {int(total)//60}분 {int(total)%60}초</p>"
        "</div>"
    )
