"""대시보드 카드 렌더 함수 — views_dashboard.py에서 분리."""
from __future__ import annotations

import html as _html
import json

from .helpers import fmt_duration, fmt_pace, metric_row, no_data_card, svg_radar_chart, svg_semicircle_gauge

_UTRS_COLORS = [(0, "#e53935"), (40, "#fb8c00"), (60, "#43a047"), (80, "#00acc1")]
_CIRS_COLORS = [(0, "#43a047"), (20, "#fb8c00"), (50, "#ef6c00"), (75, "#e53935")]


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


def _render_rmr_card(axes: dict, compare_axes: dict | None = None) -> str:
    if not axes:
        return no_data_card("RMR 러너 성숙도 레이더")
    radar = svg_radar_chart(axes, max_value=100.0, compare_axes=compare_axes, width=260)
    overall = sum(axes.values()) / len(axes) if axes else 0
    compare_note = ("<p class='muted' style='margin:0.3rem 0 0;font-size:0.8rem;'>&#128993; 3개월 전 비교</p>"
                   if compare_axes else "")
    return (
        "<div class='card' style='text-align:center;'>"
        "<h2 style='margin-bottom:0.3rem;font-size:1rem;'>RMR 러너 성숙도</h2>"
        f"<p class='muted' style='margin:0 0 0.5rem;font-size:0.8rem;'>종합 {overall:.1f}점</p>"
        f"{radar}{compare_note}</div>"
    )


# ── PMC 차트 ──────────────────────────────────────────────────────────────────

def _render_pmc_chart(pmc_data: list[dict]) -> str:
    if not pmc_data:
        return no_data_card("PMC 차트 (CTL/ATL/TSB)", "훈련 데이터 동기화 후 표시됩니다")
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
        return no_data_card("최근 활동", "동기화 후 표시됩니다")
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
        items.append(
            f"<a href='/activity/deep?id={act['id']}' style='text-decoration:none;color:inherit;'>"
            f"<div class='card' style='display:flex;align-items:center;gap:0.8rem;"
            f"padding:0.7rem 0.9rem;margin:0.4rem 0;'>"
            f"<div style='font-size:1.5rem;'>&#127939;</div>"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='font-weight:600;font-size:0.9rem;'>{_html.escape(act['date'])} · {_html.escape(dist)}</div>"
            f"<div class='muted' style='font-size:0.8rem;margin-top:0.1rem;'>"
            f"{fmt_duration(act['duration_sec'])} · {fmt_pace(act['avg_pace_sec_km'])}/km · &#9829; {act['avg_hr'] or '—'} bpm</div>"
            f"<div style='margin-top:0.25rem;'>{' '.join(badges)}</div></div>"
            f"<div style='color:var(--muted);'>&#8250;</div></div></a>"
        )
    return "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>최근 활동</h2>" + "".join(items) + "</div>"


# ── 신규 카드들 ───────────────────────────────────────────────────────────────

def _render_training_recommendation(utrs_val: float | None, utrs_json: dict,
                                    cirs_val: float | None, tsb_last: float | None) -> str:
    """오늘의 훈련 권장 카드."""
    if utrs_val is None and cirs_val is None:
        return no_data_card("오늘의 훈련 권장", "데이터 동기화 후 표시됩니다")
    grade = (utrs_json or {}).get("grade", "")
    if cirs_val and cirs_val >= 75:
        icon, intensity, desc, dur = "&#128683;", "완전 휴식", "부상 위험 매우 높음. 훈련 중단, 회복 집중.", ""
    elif not utrs_val:
        icon, intensity, desc, dur = "&#128310;", "데이터 부족", "UTRS 데이터가 부족합니다.", ""
    elif grade == "rest" or utrs_val < 40:
        icon, intensity, desc, dur = "&#128564;", "완전 휴식 권장", "피로 회복 집중. 스트레칭만 권장.", "15-20분 이내"
    elif grade == "light" or utrs_val < 60:
        icon, intensity, desc, dur = "&#128694;", "가벼운 활동", "쉬운 조깅 또는 회복런만 권장.", "30-40분, Z1-Z2"
    elif grade == "moderate" or utrs_val < 75:
        icon, intensity, desc, dur = "&#127939;", "중강도 훈련", "템포런 또는 유산소 훈련 가능.", "40-60분, Z2-Z3"
    else:
        icon, intensity, desc, dur = "&#128293;", "고강도 훈련 최적", "인터벌, 레이스페이스 훈련 최적 상태.", "60분+, Z4-Z5 포함"
    notes = ""
    if tsb_last is not None and tsb_last < -30:
        notes += f"<p style='color:var(--red);font-size:0.78rem;margin-top:0.3rem;'>&#9888; TSB {tsb_last:.0f} — 과부하. 휴식 우선</p>"
    elif tsb_last is not None and tsb_last < -20:
        notes += f"<p style='color:var(--orange);font-size:0.78rem;margin-top:0.3rem;'>&#9889; TSB {tsb_last:.0f} — 누적 피로 높음. 강도 조절 권장</p>"
    if cirs_val and 50 <= cirs_val < 75:
        notes += f"<p style='color:var(--orange);font-size:0.78rem;margin-top:0.3rem;'>&#127973; CIRS {cirs_val:.0f} — 부상 주의. 충격 운동 자제</p>"
    dur_html = f"<div style='font-size:0.8rem;color:var(--secondary);margin-top:0.1rem;'>&#8987; {dur}</div>" if dur else ""
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>오늘의 훈련 권장</h2>"
        "<div style='display:flex;align-items:center;gap:0.8rem;'>"
        f"<div style='font-size:2.2rem;'>{icon}</div>"
        "<div>"
        f"<div style='font-size:0.95rem;font-weight:700;color:var(--cyan);'>{intensity}</div>"
        f"<div style='font-size:0.8rem;color:var(--muted);margin-top:0.1rem;'>{desc}</div>"
        f"{dur_html}</div></div>{notes}</div>"
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


def _render_darp_mini(darp_data: dict) -> str:
    """DARP 레이스 예측 미니 카드."""
    if not darp_data:
        return no_data_card("레이스 예측 (DARP)", "VDOT 데이터 동기화 후 표시됩니다")
    _LABELS = {"5k": "5K", "10k": "10K", "half": "하프", "full": "마라톤"}
    rows = ""
    for key, lbl in _LABELS.items():
        d = darp_data.get(key)
        if not d:
            continue
        ts = int(d.get("time_sec") or 0)
        pace = d.get("pace_sec_km") or 0
        h, rem = divmod(ts, 3600)
        m, s = divmod(rem, 60)
        t_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        rows += (f"<tr><td style='padding:0.28rem 0.5rem;font-size:0.83rem;'>{lbl}</td>"
                 f"<td style='padding:0.28rem 0.5rem;font-size:0.83rem;font-weight:700;color:var(--cyan);'>{t_str}</td>"
                 f"<td style='padding:0.28rem 0.5rem;font-size:0.8rem;color:var(--muted);'>{fmt_pace(pace)}/km</td></tr>")
    if not rows:
        return no_data_card("레이스 예측 (DARP)", "VDOT 데이터 동기화 후 표시됩니다")
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>레이스 예측 (DARP)</h2>"
        f"<table style='width:100%;border-collapse:collapse;'>{rows}</table>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>VDOT + DI 보정 기반 예측</p></div>"
    )


def _render_fitness_mini(vdot: float | None, marathon_shape_pct: float | None) -> str:
    """VDOT / Marathon Shape 피트니스 미니 카드."""
    if vdot is None and marathon_shape_pct is None:
        return no_data_card("피트니스 현황", "Runalyze 동기화 후 표시됩니다")
    vdot_str = f"{vdot:.1f}" if vdot is not None else "—"
    shape_str = f"{marathon_shape_pct:.0f}%" if marathon_shape_pct is not None else "—"
    s_clr = ("var(--green)" if (marathon_shape_pct or 0) >= 70
             else ("var(--orange)" if (marathon_shape_pct or 0) >= 50 else "var(--muted)"))
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>피트니스 현황</h2>"
        "<div style='display:flex;gap:1rem;justify-content:space-around;'>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:var(--cyan);'>{vdot_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>VDOT</div></div>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:{s_clr};'>{shape_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>Marathon Shape</div></div></div>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;text-align:center;'>Runalyze 기준</p></div>"
    )
