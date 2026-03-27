"""활동 상세 — 그룹6: 훈련 분포.

"훈련 밸런스가 맞는가?" — HR 존 차트, TIDS 주간 추세, MarathonShape, TPDI.
"""
from __future__ import annotations

import json as _json

from .helpers import fmt_pace
from .views_activity_cards_common import (
    group_header,
    metric_interp_badge,
    no_data_msg,
    rp_row,
    source_badge,
)


# ── HR 존 수평 막대 (기존 render_hr_zone_chart 이동) ─────────────────────

def _hr_zone_bars(zones: list[float | None]) -> str:
    """HR 존 1~5 시간 분포 수평 막대."""
    if not any(z is not None and z > 0 for z in zones):
        return ""
    total = sum(z for z in zones if z is not None and z > 0)
    if total <= 0:
        return ""
    colors = ["#00d4ff", "#00ff88", "#ffaa00", "#ff8844", "#ff4444"]
    labels = ["존1 (회복)", "존2 (유산소)", "존3 (템포)", "존4 (역치)", "존5 (최대)"]
    bars = ""
    for z, c, lb in zip(zones, colors, labels):
        if z is None or z <= 0:
            continue
        pct = z / total * 100
        mins, secs = int(z) // 60, int(z) % 60
        bars += (
            f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>"
            f"<span style='width:90px;font-size:0.78rem;color:var(--muted);text-align:right;'>{lb}</span>"
            f"<div style='flex:1;background:var(--row-border);border-radius:3px;height:18px;overflow:hidden;'>"
            f"<div style='height:100%;width:{pct:.1f}%;background:{c};border-radius:3px;"
            f"display:flex;align-items:center;padding-left:6px;'>"
            f"<span style='font-size:0.68rem;color:#000;font-weight:bold;'>"
            + (f"{mins}:{secs:02d}" if pct > 8 else "")
            + "</span></div></div>"
            f"<span style='width:50px;font-size:0.75rem;color:var(--muted);'>{pct:.0f}%</span></div>"
        )
    return bars + f"<p class='muted' style='font-size:0.72rem;margin:6px 0 0;'>총 {int(total)//60}분 {int(total)%60}초</p>"


# ── TIDS 주간 추세 차트 (신규) ───────────────────────────────────────────

def _tids_weekly_chart(tids_series: dict | None) -> str:
    """TIDS 8주 z12/z3/z45 스택 에어리어 차트."""
    ts = tids_series or {}
    weeks = ts.get("weeks", [])
    z12 = ts.get("z12", [])
    z3 = ts.get("z3", [])
    z45 = ts.get("z45", [])
    if not weeks:
        return ""
    return (
        "<div id='tids-weekly' style='height:120px;margin-top:8px;'></div>"
        "<script>(function(){"
        "var el=document.getElementById('tids-weekly');"
        "if(!el||typeof echarts==='undefined')return;"
        "var ec=echarts.init(el,'dark',{backgroundColor:'transparent'});"
        f"ec.setOption({{grid:{{top:10,bottom:22,left:30,right:8}},"
        f"xAxis:{{type:'category',data:{_json.dumps(weeks)},axisLabel:{{fontSize:8,color:'#888'}}}},"
        f"yAxis:{{type:'value',max:100,axisLabel:{{fontSize:8,color:'#888',formatter:function(v){{return v+'%'}}}},"
        f"splitLine:{{lineStyle:{{color:'#2a2a3a'}}}}}},"
        f"tooltip:{{trigger:'axis'}},"
        f"series:["
        f"{{name:'Z1-2',type:'bar',stack:'t',data:{_json.dumps(z12)},itemStyle:{{color:'#4dabf7'}}}},"
        f"{{name:'Z3',type:'bar',stack:'t',data:{_json.dumps(z3)},itemStyle:{{color:'#69db7c'}}}},"
        f"{{name:'Z4-5',type:'bar',stack:'t',data:{_json.dumps(z45)},itemStyle:{{color:'#ff6b6b'}}}}"
        f"]}});"
        "window.addEventListener('resize',function(){ec.resize();});"
        "})();</script>"
        "<div style='display:flex;gap:0.8rem;font-size:0.68rem;color:var(--muted);'>"
        "<span><span style='color:#4dabf7;'>■</span> Z1-2</span>"
        "<span><span style='color:#69db7c;'>■</span> Z3</span>"
        "<span><span style='color:#ff6b6b;'>■</span> Z4-5</span></div>"
    )


# ── TPDI 서브카드 (기존 render_tpdi_card 축소) ──────────────────────────

def _tpdi_section(day_metrics: dict, day_metric_jsons: dict) -> str:
    val = day_metrics.get("TPDI")
    if val is None:
        return ""
    v = float(val)
    j = day_metric_jsons.get("TPDI") or {}
    outdoor_avg = j.get("outdoor_avg_fearp")
    indoor_avg = j.get("indoor_avg_fearp")
    n_out = j.get("n_outdoor", 0)
    n_in = j.get("n_indoor", 0)

    if v > 0:
        color, label = "#00ff88", f"실외가 {abs(v):.1f}% 빠름"
    elif v < 0:
        color, label = "#ffaa00", f"실내가 {abs(v):.1f}% 빠름"
    else:
        color, label = "var(--muted)", "동일"

    detail = ""
    if outdoor_avg is not None:
        detail += f"<span>실외 {fmt_pace(outdoor_avg)}/km ({n_out}건)</span>"
    if indoor_avg is not None:
        detail += f"<span>실내 {fmt_pace(indoor_avg)}/km ({n_in}건)</span>"
    detail_html = f"<div style='display:flex;gap:8px;font-size:0.75rem;color:var(--muted);'>{detail}</div>" if detail else ""

    return (
        "<div style='margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--row-border);'>"
        f"<div style='display:flex;align-items:baseline;gap:8px;'>"
        f"<span style='font-size:0.82rem;color:var(--muted);font-weight:600;'>TPDI{source_badge('RP')}</span>"
        f"<span style='font-size:1.1rem;font-weight:700;color:{color};'>{v:+.1f}%</span>"
        f"<span style='font-size:0.75rem;color:var(--muted);'>{label}</span></div>"
        f"{detail_html}</div>"
    )


# ── 메인 렌더 ───────────────────────────────────────────────────────────

def render_group6_distribution(
    hr_zones: list[float | None],
    day_metrics: dict,
    day_metric_jsons: dict,
    tids_weekly: dict | None = None,
) -> str:
    """그룹6 — 훈련 분포 카드."""
    zones_html = _hr_zone_bars(hr_zones)
    tids_html = _tids_weekly_chart(tids_weekly)
    tpdi_html = _tpdi_section(day_metrics, day_metric_jsons)

    # MarathonShape
    ms = day_metrics.get("MarathonShape")
    ms_row = ""
    if ms is not None:
        v = float(ms)
        badge = metric_interp_badge("MarathonShape", v)
        ms_row = (
            "<div style='display:flex;justify-content:space-between;align-items:center;"
            "padding:0.4rem 0;border-bottom:1px solid var(--row-border);'>"
            f"<span style='font-size:0.85rem;color:var(--muted);'>Race Shape{source_badge('RP')}</span>"
            f"<span style='font-size:0.9rem;font-weight:600;'>{v:.1f}%{badge}"
            f" <a href='/race' style='font-size:0.72rem;color:var(--cyan);'>레이스 →</a></span></div>"
        )

    if not zones_html and not tids_html and not ms_row and not tpdi_html:
        return no_data_msg("훈련 분포", "HR 존·TIDS 데이터 수집 중입니다")

    return (
        "<div class='card'>"
        + group_header("훈련 분포", "훈련 밸런스가 맞는가?")
        + zones_html
        + tids_html
        + ms_row
        + tpdi_html
        + "</div>"
    )
