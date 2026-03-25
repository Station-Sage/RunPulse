"""활동 상세 — 그룹2: 퍼포먼스.

"얼마나 잘 뛰었나?" — FEARP breakdown, GAP/NGP, EF+스파크라인,
Decoupling+스파크라인, ADTI, VO2Max.
"""
from __future__ import annotations

import json as _json

from .helpers import fmt_pace
from .views_activity_cards_common import (
    fmt_val,
    group_header,
    metric_interp_badge,
    metric_tooltip_icon,
    no_data_msg,
    rp_row,
    source_badge,
)


def _fearp_breakdown(metric_jsons: dict) -> str:
    """FEARP 환경 요인 분해 서브카드."""
    mj = metric_jsons.get("FEARP")
    if not mj:
        return ""
    actual = mj.get("actual_pace") or 0
    fearp = mj.get("fearp") or actual
    diff = fearp - actual if actual > 0 else 0
    if diff > 0:
        diff_str = f"+{fmt_pace(abs(diff))}/km 느린 조건"
    elif diff < 0:
        diff_str = f"{fmt_pace(abs(diff))}/km 빠른 조건"
    else:
        diff_str = "표준 조건"

    def _bar(label: str, factor: float) -> str:
        dev = (factor - 1.0) * 100
        if abs(dev) < 0.5:
            clr, eff = "#00ff88", "영향 없음"
        elif dev > 0:
            clr, eff = "#ffaa00", f"+{dev:.1f}% 불리"
        else:
            clr, eff = "#00d4ff", f"{dev:.1f}% 유리"
        pct = min(100, abs(dev) * 5)
        return (
            f"<div style='margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='color:{clr};'>{eff} ({factor:.4f})</span></div>"
            f"<div style='background:rgba(255,255,255,0.08);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{clr};border-radius:3px;height:5px;'></div></div></div>"
        )

    bars = (
        _bar("기온 영향", mj.get("temp_factor", 1.0))
        + _bar("습도 영향", mj.get("humidity_factor", 1.0))
        + _bar("고도 영향", mj.get("altitude_factor", 1.0))
        + _bar("경사 영향", mj.get("grade_factor", 1.0))
    )
    return (
        "<div style='margin-bottom:0.8rem;'>"
        "<div style='display:flex;gap:1.5rem;margin-bottom:0.6rem;'>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;color:var(--cyan);'>"
        f"{fmt_pace(fearp)}/km</div><div class='muted' style='font-size:0.74rem;'>FEARP (보정)</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;'>"
        f"{fmt_pace(actual)}/km</div><div class='muted' style='font-size:0.74rem;'>실제 페이스</div></div>"
        f"<div style='text-align:center;font-size:0.82rem;color:var(--orange);align-self:center;'>{diff_str}</div>"
        f"</div>{bars}</div>"
    )


def _sparkline_chart(chart_id: str, dates: list, values: list, label: str, color: str) -> str:
    """미니 ECharts 스파크라인 (30일 추세)."""
    if not dates or not values:
        return "<span class='muted' style='font-size:0.72rem;'>추세 데이터 부족</span>"
    return (
        f"<div id='{chart_id}' style='height:60px;margin-top:4px;'></div>"
        f"<script>(function(){{"
        f"var ec=echarts.init(document.getElementById('{chart_id}'),'dark',{{backgroundColor:'transparent'}});"
        f"ec.setOption({{grid:{{top:4,bottom:16,left:30,right:4}},"
        f"xAxis:{{type:'category',data:{_json.dumps(dates)},show:false}},"
        f"yAxis:{{type:'value',axisLabel:{{fontSize:8,color:'#888'}},splitLine:{{lineStyle:{{color:'#2a2a3a'}}}}}},"
        f"tooltip:{{trigger:'axis',textStyle:{{fontSize:10}}}},"
        f"series:[{{type:'line',data:{_json.dumps(values)},lineStyle:{{color:'{color}',width:2}},"
        f"symbol:'none',areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,"
        f"colorStops:[{{offset:0,color:'{color}40'}},{{offset:1,color:'transparent'}}]}}}}}}]}});"
        f"window.addEventListener('resize',function(){{ec.resize();}});"
        f"}})();</script>"
    )


def _decoupling_detail(metrics: dict, metric_jsons: dict) -> str:
    """Decoupling + EF 해석 서브카드."""
    dec = metrics.get("AerobicDecoupling")
    mj = metric_jsons.get("AerobicDecoupling") or {}
    ef = mj.get("ef") or metrics.get("EF")
    grade = mj.get("grade", "")
    if dec is None and ef is None:
        return ""
    dec_f = float(dec) if dec is not None else None
    ef_f = float(ef) if ef is not None else None
    if dec_f is None:
        badge_html = "<span style='color:var(--muted);font-size:0.84rem;'>랩 데이터 부족</span>"
        comment = "분할 기록이 있을 경우 표시됩니다."
    elif grade == "good" or (dec_f is not None and dec_f < 5.0):
        badge_html = "<span style='color:var(--green);font-size:0.84rem;'>&#128994; 양호 (&lt;5%)</span>"
        comment = "전/후반 심박 효율 잘 유지됨. 장거리 적합."
    elif grade == "moderate" or (dec_f is not None and dec_f < 10.0):
        badge_html = "<span style='color:var(--orange);font-size:0.84rem;'>&#128993; 보통 (5-10%)</span>"
        comment = "후반 효율 소폭 저하. 유산소 훈련 지속 권장."
    else:
        badge_html = "<span style='color:var(--red);font-size:0.84rem;'>&#128308; 낮음 (&gt;10%)</span>"
        comment = "후반 급격한 효율 저하. 유산소 베이스 강화 필요."
    dec_str = f"{dec_f:.1f}%" if dec_f is not None else "—"
    ef_str = f"{ef_f:.4f}" if ef_f is not None else "—"
    return (
        "<div style='display:flex;gap:1.5rem;margin:0.5rem 0;'>"
        f"<div style='text-align:center;'><div style='font-size:1.3rem;font-weight:700;color:var(--cyan);'>{dec_str}</div>"
        f"<div class='muted' style='font-size:0.72rem;'>Decoupling</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.3rem;font-weight:700;'>{ef_str}</div>"
        f"<div class='muted' style='font-size:0.72rem;'>EF</div></div></div>"
        f"<div style='background:rgba(255,255,255,0.06);border-radius:10px;padding:0.4rem 0.6rem;margin-bottom:0.3rem;'>"
        f"{badge_html}</div>"
        f"<p style='font-size:0.78rem;color:var(--secondary);margin:0;'>{comment}</p>"
    )


def _vo2max_row(garmin: dict, fitness_ctx: dict) -> str:
    """VO2Max 승격 행 (Garmin + Runalyze 소스 배지)."""
    g_vo2 = garmin.get("vo2max") or fitness_ctx.get("garmin_vo2max")
    r_evo2 = fitness_ctx.get("runalyze_evo2max")
    r_vdot = fitness_ctx.get("runalyze_vdot")
    if not any(v is not None for v in (g_vo2, r_evo2, r_vdot)):
        return ""
    parts = []
    if g_vo2 is not None:
        parts.append(f"{float(g_vo2):.1f}{source_badge('G')}")
    if r_evo2 is not None:
        parts.append(f"eVO2 {float(r_evo2):.1f}{source_badge('R')}")
    if r_vdot is not None:
        parts.append(f"VDOT {float(r_vdot):.1f}{source_badge('R')}")
    vals = " / ".join(parts)
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:0.4rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.85rem;color:var(--muted);'>VO2Max{metric_tooltip_icon('EF')}</span>"
        f"<span style='font-size:0.9rem;font-weight:600;'>{vals}</span></div>"
    )


# ── 메인 렌더 ───────────────────────────────────────────────────────────

def render_group2_performance(
    act_metrics: dict,
    act_metric_jsons: dict,
    garmin: dict,
    fitness_ctx: dict,
    ef_series: dict | None = None,
    dec_series: dict | None = None,
    day_metrics: dict | None = None,
) -> str:
    """그룹2 — 퍼포먼스 카드.

    FEARP breakdown, GAP/NGP, EF+스파크라인, Decoupling+스파크라인, ADTI, VO2Max.
    """
    parts = [
        "<div class='card'>",
        group_header("퍼포먼스", "얼마나 잘 뛰었나?"),
    ]

    # FEARP breakdown
    fearp_html = _fearp_breakdown(act_metric_jsons)
    if fearp_html:
        parts.append(fearp_html)

    # GAP / NGP 행
    parts.append(rp_row("GAP", act_metrics.get("GAP"), "pace"))
    parts.append(rp_row("NGP", act_metrics.get("NGP"), "pace"))

    # EF + 스파크라인
    ef_val = act_metrics.get("EF")
    if ef_val is not None:
        parts.append(rp_row("EF", ef_val, "f4"))
        ef_s = ef_series or {}
        parts.append(_sparkline_chart("ef-spark", ef_s.get("dates", []), ef_s.get("values", []), "EF", "#69db7c"))

    # Decoupling + 스파크라인 + 해석
    dec_html = _decoupling_detail(act_metrics, act_metric_jsons)
    if dec_html:
        parts.append(dec_html)
        dec_s = dec_series or {}
        parts.append(_sparkline_chart("dec-spark", dec_s.get("dates", []), dec_s.get("values", []), "Decoupling", "#ffd43b"))

    # ADTI (day-level metric, weekly computed)
    adti_val = (day_metrics or {}).get("ADTI") or act_metrics.get("ADTI")
    parts.append(rp_row("ADTI", adti_val, "f4"))

    # VO2Max (승격)
    parts.append(_vo2max_row(garmin, fitness_ctx))

    content = "".join(p for p in parts if p)
    if len(content) <= len("<div class='card'>" + group_header("퍼포먼스", "얼마나 잘 뛰었나?")):
        return no_data_msg("퍼포먼스", "FEARP·EF·Decoupling 데이터 수집 중입니다")

    return content + "</div>"
