"""레포트 — 신규 차트 렌더러 (UI 재설계용).

섹션 1 델타, 섹션 3 훈련 질, 섹션 4b 주간 TIDS, 섹션 5 리스크 추세,
섹션 6 폼/바이오, 섹션 7 컨디션 추세.
"""
from __future__ import annotations

import json

from .helpers import fmt_duration, no_data_card, svg_radar_chart


# ── 섹션 1: 요약 델타 ─────────────────────────────────────────────────────────

def render_summary_delta(stats: dict, prev: dict) -> str:
    """현재 기간 vs 이전 기간 델타 행."""
    if not prev or prev.get("count", 0) == 0:
        return ""

    def _delta(cur: float, prv: float, fmt: str = ".1f", suffix: str = "", invert: bool = False) -> str:
        if prv == 0:
            return ""
        diff = cur - prv
        pct = (diff / prv) * 100
        if abs(pct) < 0.5:
            return "<span style='color:var(--muted);font-size:0.75rem;'>±0%</span>"
        up = pct > 0
        color = "var(--green)" if (up != invert) else "var(--red)"
        arrow = "↑" if up else "↓"
        return f"<span style='color:{color};font-size:0.75rem;'>{arrow} {abs(pct):.0f}%</span>"

    return (
        "<div class='card' style='padding:0.5rem 1rem;'>"
        "<div style='display:flex;flex-wrap:wrap;gap:1rem;font-size:0.82rem;color:var(--secondary);'>"
        f"<span>활동 {stats['count']}회 {_delta(stats['count'], prev['count'])}</span>"
        f"<span>거리 {stats['total_km']:.1f}km {_delta(stats['total_km'], prev['total_km'])}</span>"
        f"<span>시간 {fmt_duration(stats['total_sec'])} {_delta(stats['total_sec'], prev['total_sec'])}</span>"
        "</div>"
        "<div style='font-size:0.7rem;color:var(--muted);margin-top:0.2rem;'>이전 동일 기간 대비</div>"
        "</div>"
    )


# ── 섹션 3: 훈련 질 추세 ──────────────────────────────────────────────────────

def render_training_quality_chart(quality: dict) -> str:
    """EF / Decoupling / VO2Max 3라인 차트."""
    ef_d = quality.get("ef_dates", [])
    dec_d = quality.get("dec_dates", [])
    vo2_d = quality.get("vo2_dates", [])
    if not ef_d and not dec_d and not vo2_d:
        return no_data_card("훈련 질 추세", "EF/Decoupling/VO2Max 데이터 수집 중")

    # 통합 날짜축 (모든 날짜 합침)
    all_dates = sorted(set(ef_d + dec_d + vo2_d))
    ef_map = dict(zip(ef_d, quality.get("ef_values", [])))
    dec_map = dict(zip(dec_d, quality.get("dec_values", [])))
    vo2_map = dict(zip(vo2_d, quality.get("vo2_values", [])))

    labels = json.dumps([d[5:] for d in all_dates])
    ef_vals = json.dumps([ef_map.get(d) for d in all_dates])
    dec_vals = json.dumps([dec_map.get(d) for d in all_dates])
    vo2_vals = json.dumps([vo2_map.get(d) for d in all_dates])

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>훈련 질 추세</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>같은 페이스에서 HR이 낮아지고 있나?</p>
  <div id='qualityChart' style='height:220px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('qualityChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={labels};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:48,bottom:25,top:32}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(dates.length/7)}},
      axisLine:{{lineStyle:{{color:'rgba(255,255,255,0.2)'}}}}}},
    yAxis:[
      {{type:'value',name:'EF/Dec',nameTextStyle:{{color:'rgba(255,255,255,0.5)',fontSize:9}},
        splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'VO2Max',position:'right',splitLine:{{show:false}},
        nameTextStyle:{{color:'#cc88ff',fontSize:9}},axisLabel:{{color:'#cc88ff',fontSize:10}}}}
    ],
    series:[
      {{name:'EF',type:'line',data:{ef_vals},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#00d4ff',width:2}},itemStyle:{{color:'#00d4ff'}},yAxisIndex:0}},
      {{name:'Decoupling %',type:'line',data:{dec_vals},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#ffaa00',width:1.5}},itemStyle:{{color:'#ffaa00'}},yAxisIndex:0}},
      {{name:'VO2Max',type:'line',data:{vo2_vals},smooth:true,symbol:'circle',symbolSize:4,
        connectNulls:true,lineStyle:{{color:'#cc88ff',width:2}},itemStyle:{{color:'#cc88ff'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── 섹션 4b: 주간 TIDS 변화 차트 ─────────────────────────────────────────────

def render_tids_weekly_chart(tids_weekly: dict) -> str:
    """주간 TIDS z12/z3/z45 스택 바 차트."""
    weeks = tids_weekly.get("weeks", [])
    if not weeks:
        return ""
    wj = json.dumps(weeks)
    z12j = json.dumps(tids_weekly.get("z12", []))
    z3j = json.dumps(tids_weekly.get("z3", []))
    z45j = json.dumps(tids_weekly.get("z45", []))

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>주간 강도 분포 변화</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>80/20 밸런스가 개선되고 있나?</p>
  <div id='tidsWeeklyChart' style='height:180px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('tidsWeeklyChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis',axisPointer:{{type:'shadow'}}}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:12,bottom:25,top:32}},
    xAxis:{{type:'category',data:{wj},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
    yAxis:{{type:'value',max:100,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,formatter:'{{value}}%'}},
      splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}}}},
    series:[
      {{name:'Z1-2',type:'bar',stack:'t',data:{z12j},itemStyle:{{color:'#00d4ff'}}}},
      {{name:'Z3',type:'bar',stack:'t',data:{z3j},itemStyle:{{color:'#ffaa00'}}}},
      {{name:'Z4-5',type:'bar',stack:'t',data:{z45j},itemStyle:{{color:'#ff4444'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── 섹션 5: 리스크 추세 차트 ──────────────────────────────────────────────────

def render_risk_trend_chart(risk_series: dict) -> str:
    """ACWR + Monotony + Strain 기간 내 차트."""
    dates = risk_series.get("dates", [])
    if not dates:
        return no_data_card("리스크 추세", "데이터 수집 중")
    dj = json.dumps([d[5:] for d in dates])
    aj = json.dumps(risk_series.get("acwr", []))
    mj = json.dumps(risk_series.get("monotony", []))
    sj = json.dumps(risk_series.get("strain", []))

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>리스크 추세</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>과훈련에 빠지고 있나?</p>
  <div id='riskTrendChart' style='height:220px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('riskTrendChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={dj};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:48,bottom:25,top:32}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(dates.length/7)}}}},
    yAxis:[
      {{type:'value',name:'ACWR/Mono',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'Strain',position:'right',splitLine:{{show:false}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}}
    ],
    series:[
      {{name:'ACWR',type:'line',data:{aj},smooth:true,symbol:'none',lineStyle:{{color:'#ff4444',width:2}},yAxisIndex:0,
        markArea:{{silent:true,data:[[{{yAxis:0.8,itemStyle:{{color:'rgba(0,255,136,0.06)'}}}},{{yAxis:1.3}}],
          [{{yAxis:1.3,itemStyle:{{color:'rgba(255,170,0,0.08)'}}}},{{yAxis:1.5}}],
          [{{yAxis:1.5,itemStyle:{{color:'rgba(255,68,68,0.1)'}}}},{{yAxis:3}}]]}}}},
      {{name:'Monotony',type:'line',data:{mj},smooth:true,symbol:'none',lineStyle:{{color:'#cc88ff',width:1.5}},yAxisIndex:0,
        markLine:{{silent:true,data:[{{yAxis:2.0,lineStyle:{{color:'rgba(255,68,68,0.4)',type:'dashed'}},label:{{show:false}}}}]}}}},
      {{name:'Strain',type:'bar',data:{sj},barWidth:3,itemStyle:{{color:'rgba(255,170,0,0.4)'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── 섹션 6: 폼/바이오메카닉스 추세 ───────────────────────────────────────────

def render_form_trend(form_data: dict) -> str:
    """RMR 레이더 비교 + GCT/수직비율/보폭 라인."""
    rmr_start = form_data.get("rmr_start", {})
    rmr_end = form_data.get("rmr_end", {})
    gct = form_data.get("gct", {})
    vr = form_data.get("vertical_ratio", {})
    stride = form_data.get("stride", {})

    has_rmr = bool(rmr_end.get("axes"))
    has_bio = bool(gct.get("dates") or vr.get("dates") or stride.get("dates"))
    if not has_rmr and not has_bio:
        return no_data_card("폼/바이오메카닉스 추세", "데이터 수집 중")

    parts = []

    # RMR 레이더 (시작 vs 끝)
    if has_rmr:
        axes_end = rmr_end.get("axes", {})
        axes_start = rmr_start.get("axes") if rmr_start else None
        radar = svg_radar_chart(axes_end, max_value=100.0, compare_axes=axes_start, width=200)
        overall = sum(axes_end.values()) / len(axes_end) if axes_end else 0
        note = " (🟡 기간 시작 비교)" if axes_start else ""
        parts.append(
            f"<div style='text-align:center;margin-bottom:0.6rem;'>"
            f"<div style='font-size:0.8rem;color:var(--muted);margin-bottom:4px;'>RMR 종합 {overall:.0f}점{note}</div>"
            f"{radar}</div>"
        )

    # 바이오 라인차트
    if has_bio:
        all_dates = sorted(set(gct.get("dates", []) + vr.get("dates", []) + stride.get("dates", [])))
        gct_map = dict(zip(gct.get("dates", []), gct.get("values", [])))
        vr_map = dict(zip(vr.get("dates", []), vr.get("values", [])))
        stride_map = dict(zip(stride.get("dates", []), stride.get("values", [])))
        labels = json.dumps([d[5:] for d in all_dates])
        gct_j = json.dumps([gct_map.get(d) for d in all_dates])
        vr_j = json.dumps([vr_map.get(d) for d in all_dates])
        stride_j = json.dumps([stride_map.get(d) for d in all_dates])
        parts.append(f"""<div id='bioChart' style='height:180px;'></div>
<script>
(function(){{
  var el=document.getElementById('bioChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={labels};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:48,bottom:25,top:30}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(dates.length/6)}}}},
    yAxis:[
      {{type:'value',name:'GCT(ms)',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'보폭(cm)',position:'right',splitLine:{{show:false}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}}
    ],
    series:[
      {{name:'GCT',type:'line',data:{gct_j},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#00d4ff',width:2}},itemStyle:{{color:'#00d4ff'}},yAxisIndex:0}},
      {{name:'수직비율%',type:'line',data:{vr_j},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#ffaa00',width:1.5}},itemStyle:{{color:'#ffaa00'}},yAxisIndex:0}},
      {{name:'보폭',type:'line',data:{stride_j},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#00ff88',width:1.5}},itemStyle:{{color:'#00ff88'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>""")

    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.3rem;'>폼/바이오메카닉스 추세</h2>"
        "<p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>폼이 나빠지고 있나?</p>"
        + "".join(parts) +
        "</div>"
    )


# ── 섹션 7: 컨디션 추세 ──────────────────────────────────────────────────────

def render_wellness_trend_chart(wellness: dict) -> str:
    """HRV / 수면 / BB / 스트레스 / 안정심박 기간 내 라인 차트."""
    dates = wellness.get("dates", [])
    if not dates:
        return no_data_card("컨디션 추세", "웰니스 데이터 수집 중")

    # 기간 평균 계산
    def _avg(vals: list) -> str:
        clean = [v for v in vals if v is not None]
        return f"{sum(clean)/len(clean):.0f}" if clean else "—"

    hrv_avg = _avg(wellness.get("hrv", []))
    sleep_avg = _avg(wellness.get("sleep", []))
    bb_avg = _avg(wellness.get("bb", []))

    dj = json.dumps([d[5:] for d in dates])
    hrv_j = json.dumps(wellness.get("hrv", []))
    sleep_j = json.dumps(wellness.get("sleep", []))
    bb_j = json.dumps(wellness.get("bb", []))
    stress_j = json.dumps(wellness.get("stress", []))
    rhr_j = json.dumps(wellness.get("rhr", []))

    avg_strip = (
        f"<div style='display:flex;gap:1rem;margin-bottom:0.5rem;font-size:0.8rem;'>"
        f"<span style='color:var(--green);'>HRV 평균 {hrv_avg}ms</span>"
        f"<span style='color:var(--cyan);'>수면 평균 {sleep_avg}</span>"
        f"<span style='color:var(--orange);'>BB 평균 {bb_avg}</span></div>"
    )

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>컨디션 추세</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.3rem;'>회복이 잘 되고 있나?</p>
  {avg_strip}
  <div id='wellnessTrendChart' style='height:200px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('wellnessTrendChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={dj};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:12,bottom:25,top:32}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(dates.length/7)}}}},
    yAxis:{{type:'value',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},
      axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
    series:[
      {{name:'HRV',type:'line',data:{hrv_j},smooth:true,symbol:'none',lineStyle:{{color:'#00ff88',width:2}},connectNulls:true}},
      {{name:'수면',type:'line',data:{sleep_j},smooth:true,symbol:'none',lineStyle:{{color:'#00d4ff',width:1.5}},connectNulls:true}},
      {{name:'BB',type:'line',data:{bb_j},smooth:true,symbol:'none',lineStyle:{{color:'#ffaa00',width:1.5}},connectNulls:true}},
      {{name:'스트레스',type:'line',data:{stress_j},smooth:true,symbol:'none',lineStyle:{{color:'#ff4444',width:1}},connectNulls:true}},
      {{name:'안정심박',type:'line',data:{rhr_j},smooth:true,symbol:'none',lineStyle:{{color:'#cc88ff',width:1}},connectNulls:true}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""
