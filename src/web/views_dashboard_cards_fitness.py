"""대시보드 피트니스 카드 — 추세 차트 + PMC + 활동 목록 + 피트니스 미니."""
from __future__ import annotations

import html as _html
import json

from .helpers import (
    METRIC_DESCRIPTIONS,
    fmt_duration,
    fmt_pace,
    no_data_card,
    tooltip,
)


def render_fitness_trends_chart(pmc_data: list[dict], trends: dict) -> str:
    """섹션 4: PMC + Monotony/Strain 오버레이 + EF 스파크라인."""
    if not pmc_data and not trends.get("dates"):
        return no_data_card("피트니스 추세", "데이터 수집 중입니다")

    pmc_labels = json.dumps([r["date"] for r in pmc_data]) if pmc_data else "[]"
    pmc_ctl = json.dumps([round(r["ctl"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"
    pmc_atl = json.dumps([round(r["atl"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"
    pmc_tsb = json.dumps([round(r["tsb"] or 0, 1) for r in pmc_data]) if pmc_data else "[]"

    ms_dates = json.dumps(trends.get("dates", []))
    mono = json.dumps(trends.get("monotony", []))
    strain = json.dumps(trends.get("strain", []))

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


def _render_pmc_chart(pmc_data: list[dict]) -> str:
    """PMC 차트 (CTL/ATL/TSB 60일)."""
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


def _render_activity_list(activities: list[dict]) -> str:
    """최근 활동 목록 카드."""
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
    if shape_dist_key:
        _dist_label_map = {"5k": "5K Shape", "10k": "10K Shape", "half": "Half Shape", "full": "Marathon Shape"}
        shape_label = _dist_label_map.get(shape_dist_key, "Race Shape")
    else:
        shape_label = race_shape_label(shape_json)

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
