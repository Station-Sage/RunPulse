"""대시보드 카드 렌더 함수 — views_dashboard.py에서 분리."""
from __future__ import annotations

import html as _html
import json

from .helpers import METRIC_DESCRIPTIONS, fmt_duration, fmt_pace, metric_row, no_data_card, svg_radar_chart, svg_semicircle_gauge, tooltip

_UTRS_COLORS = [(0, "#e53935"), (40, "#fb8c00"), (60, "#43a047"), (80, "#00acc1")]
_CIRS_COLORS = [(0, "#43a047"), (20, "#fb8c00"), (50, "#ef6c00"), (75, "#e53935")]


# ── 섹션 1: 오늘의 상태 스트립 ────────────────────────────────────────────────

def _mini_gauge(label: str, value: float | None, max_val: float,
                colors: list, grade: str = "") -> str:
    """60px 미니 반원 게이지 + 툴팁."""
    desc = METRIC_DESCRIPTIONS.get(label, "")
    tip_label = tooltip(label, desc) if desc else label
    if value is None:
        return (f"<div style='text-align:center;min-width:80px;opacity:0.4;'>"
                f"<div style='font-size:0.7rem;color:var(--muted);'>{tip_label}</div>"
                f"<div style='font-size:1.1rem;font-weight:700;'>—</div></div>")
    gauge = svg_semicircle_gauge(value, max_val, grade, colors, width=70)
    return (f"<div style='text-align:center;min-width:80px;'>"
            f"<div style='font-size:0.7rem;color:var(--muted);margin-bottom:2px;'>{tip_label}</div>"
            f"{gauge}</div>")


def _mini_icon_val(icon: str, label: str, value, unit: str = "", color: str = "var(--cyan)") -> str:
    """아이콘 + 값 미니 표시."""
    val_str = f"{value}" if value is not None else "—"
    opacity = "1" if value is not None else "0.4"
    return (f"<div style='text-align:center;min-width:60px;opacity:{opacity};'>"
            f"<div style='font-size:1.1rem;'>{icon}</div>"
            f"<div style='font-size:0.95rem;font-weight:700;color:{color};'>{val_str}{unit}</div>"
            f"<div style='font-size:0.65rem;color:var(--muted);'>{label}</div></div>")


def render_daily_status_strip(utrs_val: float | None, utrs_json: dict,
                              cirs_val: float | None, cirs_json: dict,
                              acwr: float | None, rtti: float | None,
                              wellness: dict,
                              metric_date: str | None = None) -> str:
    """섹션 1: 오늘의 상태 한 줄 스트립."""
    utrs_grade = {"rest": "휴식", "light": "경량", "moderate": "보통", "optimal": "최적"}.get(
        (utrs_json or {}).get("grade", ""), "")
    cirs_grade = {"safe": "안전", "caution": "주의", "warning": "경고", "danger": "위험"}.get(
        (cirs_json or {}).get("grade", ""), "")

    # ACWR 색상
    if acwr is None:
        acwr_clr = "var(--muted)"
    elif acwr > 1.5:
        acwr_clr = "var(--red)"
    elif acwr > 1.3:
        acwr_clr = "var(--orange)"
    else:
        acwr_clr = "var(--green)"
    acwr_str = f"{acwr:.2f}" if acwr is not None else "—"

    bb = wellness.get("body_battery")
    sleep = wellness.get("sleep_score")
    hrv = wellness.get("hrv")

    acwr_tip = tooltip("ACWR", METRIC_DESCRIPTIONS.get("ACWR", ""))
    parts = [
        _mini_gauge("UTRS", utrs_val, 100, _UTRS_COLORS, utrs_grade),
        _mini_gauge("CIRS", cirs_val, 100, _CIRS_COLORS, cirs_grade),
        # ACWR 텍스트
        (f"<div style='text-align:center;min-width:70px;'>"
         f"<div style='font-size:0.7rem;color:var(--muted);margin-bottom:2px;'>{acwr_tip}</div>"
         f"<div style='font-size:1.3rem;font-weight:700;color:{acwr_clr};'>{acwr_str}</div></div>"),
        _mini_gauge("RTTI", rtti, 100, [(0, "#e53935"), (40, "#fb8c00"), (70, "#43a047")]),
        # 웰니스 미니 아이콘
        _mini_icon_val("&#128267;", "BB", bb, "", "var(--orange)"),
        _mini_icon_val("&#128164;", "수면", sleep, "", "var(--cyan)"),
        _mini_icon_val("&#128147;", "HRV", f"{hrv:.0f}" if hrv else None, "", "var(--green)"),
    ]

    from datetime import date as _date
    date_label = "오늘의 상태"
    if metric_date and metric_date != _date.today().isoformat():
        date_label = f"최근 상태 ({metric_date})"
    return (
        "<div class='card' style='padding:0.6rem 0.8rem;'>"
        f"<div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.4rem;'>{date_label}</div>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.6rem;align-items:flex-end;justify-content:space-around;'>"
        + "".join(parts) +
        "</div></div>"
    )


# ── 섹션 3: 이번 주 훈련 요약 ─────────────────────────────────────────────────

def render_weekly_summary(weekly: dict, weekly_target_km: float = 40.0) -> str:
    """섹션 3: 주간 거리/시간 진행률 + TIDS 도넛."""
    if not weekly or weekly.get("count", 0) == 0:
        return no_data_card("이번 주 훈련 요약", "이번 주 활동이 없습니다")

    dist = weekly["distance_km"]
    dur = weekly["duration_sec"]
    count = weekly["count"]
    pct = min(100, round(dist / weekly_target_km * 100)) if weekly_target_km > 0 else 0

    # 진행률 바
    bar_clr = "var(--green)" if pct >= 80 else ("var(--orange)" if pct >= 50 else "var(--cyan)")
    progress = (
        f"<div style='margin-bottom:0.6rem;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px;'>"
        f"<span>{dist:.1f} km / {weekly_target_km:.0f} km</span>"
        f"<span style='color:{bar_clr};font-weight:600;'>{pct}%</span></div>"
        f"<div style='background:rgba(255,255,255,0.1);border-radius:4px;height:8px;'>"
        f"<div style='width:{pct}%;background:{bar_clr};border-radius:4px;height:8px;"
        f"transition:width 0.5s;'></div></div></div>"
    )

    stats = (
        f"<div style='display:flex;gap:1rem;font-size:0.8rem;color:var(--secondary);'>"
        f"<span>{count}회</span><span>{fmt_duration(dur)}</span></div>"
    )

    # TIDS 도넛 (CSS 원형)
    z12 = weekly.get("tids_z12") or 0
    z3 = weekly.get("tids_z3") or 0
    z45 = weekly.get("tids_z45") or 0
    total = z12 + z3 + z45
    tids_html = ""
    if total > 0:
        p12 = round(z12 / total * 100)
        p3 = round(z3 / total * 100)
        p45 = 100 - p12 - p3
        # conic-gradient 도넛
        tids_html = (
            f"<div style='display:flex;align-items:center;gap:0.8rem;margin-top:0.6rem;'>"
            f"<div style='width:60px;height:60px;border-radius:50%;"
            f"background:conic-gradient(#00d4ff 0% {p12}%, #ffaa00 {p12}% {p12 + p3}%, #ff4444 {p12 + p3}% 100%);"
            f"position:relative;'>"
            f"<div style='position:absolute;inset:12px;border-radius:50%;background:var(--bg);'></div></div>"
            f"<div style='font-size:0.75rem;line-height:1.5;'>"
            f"<div><span style='color:#00d4ff;'>&#9632;</span> Z1-2 {p12}%</div>"
            f"<div><span style='color:#ffaa00;'>&#9632;</span> Z3 {p3}%</div>"
            f"<div><span style='color:#ff4444;'>&#9632;</span> Z4-5 {p45}%</div></div></div>"
        )

    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.5rem;'>이번 주 훈련 요약</h2>"
        + progress + stats + tids_html +
        "</div>"
    )


# ── 섹션 4: 피트니스 추세 확장 ─────────────────────────────────────────────────

def render_fitness_trends_chart(pmc_data: list[dict], trends: dict) -> str:
    """섹션 4: PMC + Monotony/Strain 오버레이 + EF 스파크라인."""
    if not pmc_data and not trends.get("dates"):
        return no_data_card("피트니스 추세", "데이터 수집 중입니다")

    # PMC 데이터
    pmc_labels = json.dumps([r["date"] for r in pmc_data]) if pmc_data else "[]"
    pmc_ctl = json.dumps([round(r["ctl"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"
    pmc_atl = json.dumps([round(r["atl"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"
    pmc_tsb = json.dumps([round(r["tsb"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"

    # Monotony/Strain
    ms_dates = json.dumps(trends.get("dates", []))
    mono = json.dumps(trends.get("monotony", []))
    strain = json.dumps(trends.get("strain", []))

    # EF
    ef_dates = json.dumps(trends.get("ef_dates", []))
    ef_vals = json.dumps(trends.get("ef_values", []))

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.5rem;'>피트니스 추세</h2>
  <div id='fitTrendChart' style='height:260px;'></div>
  <p class='muted' style='font-size:0.74rem;margin:0.3rem 0 0;'>
    CTL/ATL/TSB 60일 + Monotony/Strain 오버레이
  </p>
  <h3 style='font-size:0.9rem;margin:0.8rem 0 0.3rem;color:var(--secondary);'>EF 효율 추세</h3>
  <div id='efTrendChart' style='height:120px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('fitTrendChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var pDates={pmc_labels},pCtl={pmc_ctl},pAtl={pmc_atl},pTsb={pmc_tsb};
  var msDates={ms_dates},mono={mono},strain={strain};
  var sl=pDates.map(function(d){{return d.slice(5);}});
  var msSl=msDates.map(function(d){{return d.slice(5);}});
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:48,bottom:28,top:34}},
    xAxis:{{type:'category',data:sl,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(sl.length/7)}},
      axisLine:{{lineStyle:{{color:'rgba(255,255,255,0.2)'}}}}}},
    yAxis:[
      {{type:'value',name:'CTL/ATL',nameTextStyle:{{color:'rgba(255,255,255,0.5)',fontSize:9}},
        splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'TSB/Mono',position:'right',splitLine:{{show:false}},
        nameTextStyle:{{color:'#ffaa00',fontSize:9}},axisLabel:{{color:'#ffaa00',fontSize:10}}}}
    ],
    series:[
      {{name:'CTL',type:'line',data:pCtl,smooth:true,symbol:'none',lineStyle:{{color:'#00d4ff',width:2}},yAxisIndex:0}},
      {{name:'ATL',type:'line',data:pAtl,smooth:true,symbol:'none',lineStyle:{{color:'#00ff88',width:2}},yAxisIndex:0}},
      {{name:'TSB',type:'line',data:pTsb,smooth:true,symbol:'none',lineStyle:{{color:'#ffaa00',width:1.5,type:'dashed'}},yAxisIndex:1}},
      {{name:'Monotony',type:'line',data:mono,smooth:true,symbol:'none',lineStyle:{{color:'#cc88ff',width:1.5}},yAxisIndex:1,
        markLine:{{silent:true,data:[{{yAxis:2.0,lineStyle:{{color:'rgba(255,68,68,0.5)',type:'dashed'}},label:{{show:false}}}}]}}}},
      {{name:'Strain',type:'bar',data:strain,barWidth:3,itemStyle:{{color:'rgba(255,68,68,0.35)'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
  // EF 스파크라인
  var el2=document.getElementById('efTrendChart');
  if(!el2) return;
  var c2=echarts.init(el2,'dark',{{backgroundColor:'transparent'}});
  var efD={ef_dates},efV={ef_vals};
  var efSl=efD.map(function(d){{return d.slice(5);}});
  c2.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis',formatter:function(p){{return p[0]?p[0].axisValue+'<br>EF: '+p[0].value:''}}}},
    grid:{{left:48,right:16,bottom:20,top:8}},
    xAxis:{{type:'category',data:efSl,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(efSl.length/6)}},
      axisLine:{{lineStyle:{{color:'rgba(255,255,255,0.15)'}}}}}},
    yAxis:{{type:'value',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
    series:[{{type:'line',data:efV,smooth:true,symbol:'circle',symbolSize:4,
      lineStyle:{{color:'#00d4ff',width:2}},itemStyle:{{color:'#00d4ff'}},
      areaStyle:{{color:'rgba(0,212,255,0.08)'}}}}]
  }});
  window.addEventListener('resize',function(){{c2.resize();}});
}})();
</script>"""


# ── 섹션 6: 리스크 상세 확장 ──────────────────────────────────────────────────

def render_risk_pills_v2(risk_data: dict, trends_7d: dict,
                         config: dict | None = None, conn=None,
                         ai_override: str | None = None) -> str:
    """섹션 6: 위험지표 pills + AI 요약."""
    if not risk_data:
        return ""

    def _trend_arrow(vals: list) -> str:
        """7일 추세 화살표."""
        clean = [v for v in vals if v is not None]
        if len(clean) < 2:
            return ""
        diff = clean[-1] - clean[0]
        if abs(diff) < 0.01:
            return "<span style='color:var(--muted);font-size:0.7rem;'>&#8594;</span>"
        if diff > 0:
            return "<span style='color:var(--red);font-size:0.7rem;'>&#8593;</span>"
        return "<span style='color:var(--green);font-size:0.7rem;'>&#8595;</span>"

    def _pill(label: str, val: float | None, lo: float, hi: float,
              fmt: str = ".2f", invert: bool = False, trend_key: str = "",
              desc_key: str = "") -> str:
        trend = _trend_arrow(trends_7d.get(trend_key, [])) if trend_key else ""
        # 범위 + 상태 설명
        desc = METRIC_DESCRIPTIONS.get(desc_key or trend_key, "")
        if val is not None:
            if not invert:
                status = "위험" if val > hi else "주의" if val > lo else "적정"
            else:
                status = "위험" if val < lo else "주의" if val < hi else "적정"
            range_text = f" (적정: {lo}~{hi})"
            desc = f"{desc}{range_text} | 현재: {status}" if desc else f"적정 범위: {lo}~{hi} | 현재: {status}"
        tip_label = tooltip(label, desc) if desc else label

        if val is None:
            return (f"<span style='background:rgba(255,255,255,0.08);color:var(--muted);"
                    f"border-radius:16px;padding:0.25rem 0.7rem;font-size:0.78rem;"
                    f"white-space:nowrap;'>{tip_label} — {trend}</span>")
        bad = val > hi if not invert else val < lo
        warn = (lo < val <= hi) if not invert else (lo <= val < hi)
        if bad:
            bg, clr = "rgba(255,68,68,0.18)", "var(--red)"
        elif warn:
            bg, clr = "rgba(255,170,0,0.18)", "var(--orange)"
        else:
            bg, clr = "rgba(0,255,136,0.15)", "var(--green)"
        return (f"<span style='background:{bg};color:{clr};border-radius:16px;"
                f"padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>"
                f"{tip_label} {val:{fmt}} {trend}</span>")

    tsb = risk_data.get("tsb")
    strain = risk_data.get("strain")

    return (
        "<div class='card' style='padding:0.6rem 1rem;'>"
        "<div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.3rem;'>리스크 상세</div>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.4rem;align-items:center;'>"
        + _pill("ACWR", risk_data.get("acwr"), 1.3, 1.5, ".2f", trend_key="ACWR")
        + _pill("LSI", risk_data.get("lsi"), 1.0, 1.5, ".1f", trend_key="LSI")
        + _pill("단조로움", risk_data.get("monotony"), 1.5, 2.0, ".1f", trend_key="Monotony")
        + _pill("Strain", strain, 200, 400, ".0f", trend_key="Strain")
        + _pill("TSB", tsb, -20, -10, ".0f", invert=True, trend_key="TSB")
        + "</div>"
        + _risk_ai_summary(risk_data, config, conn, ai_override=ai_override)
        + "</div>"
    )


def _risk_ai_summary(risk_data: dict, config, conn, ai_override: str | None = None) -> str:
    """리스크 AI 한 줄 요약."""
    msg = ai_override
    if not msg:
        return ""
    return (f"<div style='margin-top:0.4rem;font-size:0.78rem;color:var(--secondary);'>"
            f"💡 {msg}</div>")


# ── 경고 배너 ─────────────────────────────────────────────────────────────────

def _render_cirs_banner(cirs: float) -> str:
    if cirs >= 75:
        return (
            "<div style='background:rgba(229,57,53,0.15);color:#ff4444;"
            "border-left:4px solid #ff4444;padding:0.7rem 1rem;"
            "border-radius:6px;margin-bottom:1rem;'>"
            f"&#9888; <strong>부상 위험 (CIRS {cirs:.0f})</strong> — 훈련 강도를 즉시 낮추세요."
            "</div>"
        )
    if cirs >= 50:
        return (
            "<div style='background:rgba(251,140,0,0.15);color:#ffaa00;"
            "border-left:4px solid #ffaa00;padding:0.7rem 1rem;"
            "border-radius:6px;margin-bottom:1rem;'>"
            f"&#9889; <strong>부상 주의 (CIRS {cirs:.0f})</strong> — 회복·부하 관리가 필요합니다."
            "</div>"
        )
    return ""


# ── UTRS / CIRS 게이지 카드 ───────────────────────────────────────────────────

def _render_utrs_factors(utrs_json: dict) -> str:
    """UTRS 하위 요인 progress bar 표시."""
    labels = {"sleep": "수면점수", "hrv": "HRV 지수", "tsb_norm": "TSB", "rhr": "안정심박", "consistency": "수면일관성"}
    rows = []
    for key, label in labels.items():
        val = utrs_json.get(key)
        pct = max(0, min(100, val)) if val is not None else 0
        val_str = f"{val:.0f}" if val is not None else "—"
        opacity = "1" if val is not None else "0.4"
        clr = "#00ff88" if pct >= 60 else ("#ffaa00" if pct >= 40 else "#ff4444")
        rows.append(
            f"<div style='opacity:{opacity};margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='font-weight:600;'>{val_str}</span></div>"
            f"<div style='background:rgba(255,255,255,0.1);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{clr};border-radius:3px;height:5px;'></div></div></div>"
        )
    return "<div style='margin-top:0.7rem;'>" + "".join(rows) + "</div>"


def _render_cirs_breakdown(cirs_json: dict) -> str:
    """CIRS 구성요소 breakdown (progress bar + 상태 뱃지)."""
    factors = [("acwr_risk", "ACWR 과부하", "×0.4"), ("mono_risk", "훈련 단조로움", "×0.2"),
               ("spike_risk", "부하 급증", "×0.3")]
    if cirs_json.get("has_asym_data"):
        factors.append(("asym_risk", "비대칭", "×0.1"))
    rows = []
    for key, label, weight in factors:
        val = float(cirs_json.get(key) or 0)
        pct = max(0, min(100, val))
        if val < 30:
            sc, bc = "var(--green)", "#00ff88"
            status = "안전"
        elif val < 60:
            sc, bc = "var(--orange)", "#ffaa00"
            status = "주의"
        else:
            sc, bc = "var(--red)", "#ff4444"
            status = "위험"
        rows.append(
            f"<div style='margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label} <span style='color:var(--muted);font-size:0.68rem;'>{weight}</span></span>"
            f"<span style='color:{sc};font-weight:600;'>{status} {val:.0f}</span></div>"
            f"<div style='background:rgba(255,255,255,0.1);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{bc};border-radius:3px;height:5px;'></div></div></div>"
        )
    return "<div style='margin-top:0.6rem;'>" + "".join(rows) + "</div>"


def _render_gauge_card(title: str, value: float | None, max_value: float,
                       color_stops: list, subtitle: str = "", extra_html: str = "",
                       grade_label: str = "") -> str:
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


# ── PMC 차트 ──────────────────────────────────────────────────────────────────

def _render_pmc_chart(pmc_data: list[dict]) -> str:
    if not pmc_data:
        return no_data_card("PMC 차트 (CTL/ATL/TSB)", "데이터 수집 중입니다")
    labels = [r["date"] for r in pmc_data]
    ctl = [round(r["ctl"] or 0, 1) for r in pmc_data]
    atl = [round(r["atl"] or 0, 1) for r in pmc_data]
    tsb = [round(r["tsb"] or 0, 1) for r in pmc_data]
    lj = json.dumps(labels); cj = json.dumps(ctl); aj = json.dumps(atl); tj = json.dumps(tsb)
    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.8rem;'>PMC 훈련 부하 차트</h2>
  <div id='pmcChart' style='height:240px;'></div>
  <p class='muted' style='font-size:0.78rem;margin:0.4rem 0 0;'>
    CTL(만성부하) · ATL(급성부하) · TSB(훈련 스트레스 균형) — 최근 60일
    &nbsp;|&nbsp; <span style='color:#ffaa00'>&#9632;</span> TSB&lt;-20 주의
    &nbsp;<span style='color:#ff4444'>&#9632;</span> TSB&lt;-30 위험
  </p>
</div>
<script>
(function(){{
  var el=document.getElementById('pmcChart');
  if(!el||typeof echarts==='undefined') return;
  var chart=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var labels={lj},sl=labels.map(function(d){{return d.slice(5);}});
  var ctlD={cj},atlD={aj},tsbD={tj};
  var wA=[],dA=[],wS=null,dS=null;
  for(var i=0;i<tsbD.length;i++){{
    var v=tsbD[i];
    if(v<-30){{if(dS===null)dS=i;if(wS===null)wS=i;}}
    else if(v<-20){{if(wS===null)wS=i;if(dS!==null){{dA.push([{{xAxis:sl[dS]}},{{xAxis:sl[i-1]}}]);dS=null;}}}}
    else{{if(wS!==null){{wA.push([{{xAxis:sl[wS]}},{{xAxis:sl[i-1]}}]);wS=null;}}if(dS!==null){{dA.push([{{xAxis:sl[dS]}},{{xAxis:sl[i-1]}}]);dS=null;}}}}
  }}
  if(wS!==null)wA.push([{{xAxis:sl[wS]}},{{xAxis:sl[sl.length-1]}}]);
  if(dS!==null)dA.push([{{xAxis:sl[dS]}},{{xAxis:sl[sl.length-1]}}]);
  chart.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}},
      formatter:function(p){{var s=p[0].axisValue+'<br>';p.forEach(function(x){{s+=x.marker+x.seriesName+': '+(x.value==null?'—':x.value.toFixed(1))+'<br>';}}); return s;}}}},
    legend:{{top:4,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:11}}}},
    grid:{{left:48,right:48,bottom:30,top:36}},
    xAxis:{{type:'category',data:sl,axisLine:{{lineStyle:{{color:'rgba(255,255,255,0.2)'}}}},
      axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(sl.length/8)}}}},
    yAxis:[
      {{type:'value',name:'CTL/ATL',nameTextStyle:{{color:'rgba(255,255,255,0.5)',fontSize:10}},
        splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'TSB',nameTextStyle:{{color:'#ffaa00',fontSize:10}},
        position:'right',splitLine:{{show:false}},axisLabel:{{color:'#ffaa00',fontSize:10}}}}
    ],
    series:[
      {{name:'CTL',type:'line',data:ctlD,smooth:true,symbol:'none',
        lineStyle:{{color:'#00d4ff',width:2}},areaStyle:{{color:'rgba(0,212,255,0.08)'}},yAxisIndex:0}},
      {{name:'ATL',type:'line',data:atlD,smooth:true,symbol:'none',
        lineStyle:{{color:'#00ff88',width:2}},areaStyle:{{color:'rgba(0,255,136,0.08)'}},yAxisIndex:0}},
      {{name:'TSB',type:'line',data:tsbD,smooth:true,symbol:'none',
        lineStyle:{{color:'#ffaa00',width:1.5,type:'dashed'}},yAxisIndex:1,
        markArea:{{silent:true,data:[
          ...wA.map(function(a){{return[{{xAxis:a[0].xAxis,itemStyle:{{color:'rgba(255,170,0,0.12)'}}}},{{xAxis:a[1].xAxis}}];}}),
          ...dA.map(function(a){{return[{{xAxis:a[0].xAxis,itemStyle:{{color:'rgba(255,68,68,0.18)'}}}},{{xAxis:a[1].xAxis}}];}})
        ]}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();
</script>"""


# ── 최근 활동 목록 ────────────────────────────────────────────────────────────

def _render_activity_list(activities: list[dict]) -> str:
    if not activities:
        return no_data_card("최근 활동", "데이터 수집 중입니다")
    items = []
    for act in activities:
        dist = f"{act['distance_km']:.1f} km" if act["distance_km"] else "—"
        badges = []
        if act.get("fearp") is not None:
            badges.append(
                f"<span style='background:rgba(0,212,255,0.15);color:var(--cyan);"
                f"border-radius:12px;padding:0.1rem 0.5rem;font-size:0.76rem;'>FEARP {fmt_pace(act['fearp'])}</span>"
            )
        if act.get("relative_effort") is not None:
            badges.append(
                f"<span style='background:rgba(0,255,136,0.12);color:var(--green);"
                f"border-radius:12px;padding:0.1rem 0.5rem;font-size:0.76rem;'>RE {act['relative_effort']:.0f}</span>"
            )
        name = _html.escape(act.get("name", "")) or "러닝"
        route_svg = act.get("route_svg", "")
        thumb = route_svg if route_svg else "<div style='font-size:1.5rem;'>&#127939;</div>"
        items.append(
            f"<a href='/activity/deep?id={act['id']}' style='text-decoration:none;color:inherit;'>"
            f"<div class='card' style='display:flex;align-items:center;gap:0.8rem;"
            f"padding:0.7rem 0.9rem;margin:0.4rem 0;'>"
            f"{thumb}"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='font-weight:600;font-size:0.9rem;'>{name}</div>"
            f"<div class='muted' style='font-size:0.8rem;margin-top:0.1rem;'>"
            f"{_html.escape(act['date'])} · {_html.escape(dist)} · "
            f"{fmt_duration(act['duration_sec'])} · {fmt_pace(act['avg_pace_sec_km'])}/km · &#9829; {act['avg_hr'] or '—'} bpm</div>"
            f"<div style='margin-top:0.25rem;'>{' '.join(badges)}</div></div>"
            f"<div style='color:var(--muted);'>&#8250;</div></div></a>"
        )
    return "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>최근 활동</h2>" + "".join(items) + "</div>"


# ── 신규 카드들 ───────────────────────────────────────────────────────────────

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

    # 절대 제약 먼저 확인
    if cirs_val and cirs_val >= 75:
        icon, intensity, desc, dur = "&#128683;", "완전 휴식", "부상 위험 매우 높음. 훈련 중단, 회복 집중.", ""
    elif not utrs_val:
        icon, intensity, desc, dur = "&#128310;", "데이터 부족", "UTRS 데이터가 부족합니다.", ""
    elif grade == "rest" or utrs_val < 40:
        icon, intensity, desc, dur = "&#128564;", "완전 휴식 권장", "피로 회복 집중. 스트레칭만 권장.", "15-20분 이내"
        effective_level = 0
    else:
        # UTRS 기반 기준 등급 결정
        if utrs_val < 60:
            base_level = 1   # 가벼운
        elif utrs_val < 75:
            base_level = 2   # 중강도
        else:
            base_level = 3   # 고강도

        # ACWR/CIRS/DI 종합 조정
        # 좋은 컨디션: ACWR 적정(1.0-1.3) + 낮은 부상 위험(CIRS<30) + 높은 지구력(DI>80)
        boost = (
            acwr_val is not None and 1.0 <= acwr_val <= 1.3
            and (cirs_val is None or cirs_val < 30)
            and (di_val is None or di_val > 80)
        )
        # 과부하 신호: ACWR 높음(>1.5) → 보수적으로
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
    # AI 오버라이드 (탭별 통합 호출에서 전달)
    if ai_override:
        desc = ai_override

    # ── 계획된 훈련 비교 블록 ──────────────────────────────────────────
    planned_html = ""
    if planned_workout and planned_workout.get("type") != "rest":
        pw_type = planned_workout.get("type", "")
        pw_dist = planned_workout.get("distance_km")
        pw_desc = planned_workout.get("description", "")
        # workout_type → 강도 레벨 매핑
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
    # ACWR 과부하 경고
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


def _render_risk_pills(risk_data: dict) -> str:
    """ACWR / LSI / Monotony / TSB 상태 pill 행."""
    if not risk_data:
        return ""

    def _pill(label: str, val: float | None, lo: float, hi: float, fmt: str = ".2f", invert: bool = False) -> str:
        if val is None:
            return f"<span style='background:rgba(255,255,255,0.08);color:var(--muted);border-radius:16px;padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>{label} —</span>"
        bad = val > hi if not invert else val < lo
        warn = (lo < val <= hi) if not invert else (lo <= val < hi)
        if bad:
            bg, clr = "rgba(255,68,68,0.18)", "var(--red)"
        elif warn:
            bg, clr = "rgba(255,170,0,0.18)", "var(--orange)"
        else:
            bg, clr = "rgba(0,255,136,0.15)", "var(--green)"
        return (f"<span style='background:{bg};color:{clr};border-radius:16px;"
                f"padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>"
                f"{label} {val:{fmt}}</span>")

    tsb = risk_data.get("tsb")
    tsb_pill = _pill("TSB", tsb, -20, -10, ".0f", invert=True)
    return (
        "<div class='card' style='padding:0.6rem 1rem;'>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.4rem;align-items:center;'>"
        "<span style='font-size:0.78rem;color:var(--muted);margin-right:0.2rem;'>위험지표</span>"
        + _pill("ACWR", risk_data.get("acwr"), 1.3, 1.5, ".2f")
        + _pill("LSI", risk_data.get("lsi"), 1.0, 1.5, ".1f")
        + _pill("단조로움", risk_data.get("monotony"), 1.5, 2.0, ".1f")
        + tsb_pill
        + "</div></div>"
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
    # Shape/EF from DARP data — 목표 거리 우선, 없으면 half→full→10k→5k
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


def _render_fitness_mini(vdot: float | None, marathon_shape_pct: float | None,
                         eftp: float | None = None, rec: float | None = None,
                         rri: float | None = None, vdot_adj: float | None = None,
                         vdot_json: dict | None = None, shape_json: dict | None = None,
                         config: dict | None = None, conn=None,
                         ai_override: str | None = None,
                         shape_dist_key: str | None = None) -> str:
    """VDOT / Race Shape / eFTP / REC / RRI 피트니스 미니 카드."""
    if all(v is None for v in [vdot, marathon_shape_pct, eftp, rec]):
        return no_data_card("피트니스 현황", "데이터 수집 중입니다")
    vdot_str = f"{vdot:.1f}" if vdot is not None else "—"
    if vdot_adj and vdot and abs(vdot_adj - vdot) > 0.3:
        vdot_str += f" <span style='font-size:0.7rem;color:var(--muted);'>(보정 {vdot_adj:.1f})</span>"
    # VDOT 소스 비교 (RunPulse vs Runalyze vs Garmin)
    vj = vdot_json or {}
    vdot_compare = ""
    ref_parts = []
    r_vdot = vj.get("runalyze_vdot")
    g_vdot = vj.get("garmin_vo2max")
    if r_vdot is not None:
        ref_parts.append(f"Runalyze {r_vdot:.1f}")
    if g_vdot is not None:
        ref_parts.append(f"Garmin {g_vdot:.1f}")
    if ref_parts:
        vdot_compare = (
            f"<div style='font-size:0.68rem;color:var(--muted);margin-top:2px;'>"
            f"{' · '.join(ref_parts)}</div>"
        )
    shape_str = f"{marathon_shape_pct:.0f}%" if marathon_shape_pct is not None else "—"
    s_clr = ("var(--green)" if (marathon_shape_pct or 0) >= 70
             else ("var(--orange)" if (marathon_shape_pct or 0) >= 50 else "var(--muted)"))
    from .helpers import race_shape_label
    # shape_dist_key가 있으면 DARP 소스 거리 기준으로 라벨 결정 (값과 라벨 소스 일치)
    if shape_dist_key:
        _dist_label_map = {"5k": "5K Shape", "10k": "10K Shape", "half": "Half Shape", "full": "Marathon Shape"}
        shape_label = _dist_label_map.get(shape_dist_key, "Race Shape")
    else:
        shape_label = race_shape_label(shape_json)

    # 추가 메트릭 행
    extra_items = []
    if eftp is not None:
        extra_items.append(
            f"<div style='text-align:center;'>"
            f"<div style='font-size:1.2rem;font-weight:700;color:var(--cyan);'>{fmt_pace(int(eftp))}</div>"
            f"<div class='muted' style='font-size:0.72rem;'>{tooltip('eFTP', METRIC_DESCRIPTIONS.get('eFTP', ''))}</div></div>"
        )
    if rec is not None:
        rec_clr = "var(--green)" if rec >= 60 else "var(--orange)" if rec >= 30 else "var(--red)"
        extra_items.append(
            f"<div style='text-align:center;'>"
            f"<div style='font-size:1.2rem;font-weight:700;color:{rec_clr};'>{rec:.0f}</div>"
            f"<div class='muted' style='font-size:0.72rem;'>{tooltip('REC', METRIC_DESCRIPTIONS.get('REC', ''))}</div></div>"
        )
    if rri is not None:
        rri_clr = "var(--green)" if rri >= 70 else "var(--orange)" if rri >= 50 else "var(--red)"
        extra_items.append(
            f"<div style='text-align:center;'>"
            f"<div style='font-size:1.2rem;font-weight:700;color:{rri_clr};'>{rri:.0f}</div>"
            f"<div class='muted' style='font-size:0.72rem;'>{tooltip('RRI', METRIC_DESCRIPTIONS.get('RRI', ''))}</div></div>"
        )
    extra_row = (
        "<div style='display:flex;gap:1rem;justify-content:space-around;margin-top:0.5rem;'>"
        + "".join(extra_items) + "</div>"
    ) if extra_items else ""

    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>피트니스 현황</h2>"
        "<div style='display:flex;gap:1rem;justify-content:space-around;'>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:var(--cyan);'>{vdot_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>{tooltip('VDOT', METRIC_DESCRIPTIONS.get('VDOT', ''))}</div>"
        + vdot_compare + "</div>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:{s_clr};'>{shape_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>{tooltip(shape_label, METRIC_DESCRIPTIONS.get('MarathonShape', ''))}</div></div></div>"
        + extra_row
        + _fitness_ai_note(config, conn, ai_override=ai_override)
        + "</div>"
    )


def _fitness_ai_note(config, conn, ai_override: str | None = None) -> str:
    """피트니스 AI 평가."""
    msg = ai_override
    if not msg:
        return ""
    return (f"<p style='margin-top:0.4rem;font-size:0.78rem;color:var(--secondary);'>"
            f"💡 {msg}</p>")
