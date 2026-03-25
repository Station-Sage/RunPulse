"""활동 상세 — 그룹7: 피트니스 컨텍스트.

"장기적으로 어디쯤인가?" — PMC 차트 (CTL/ATL/TSB), DI 카드, DARP 링크.
"""
from __future__ import annotations

import json as _json

from .helpers import fmt_pace, metric_row
from .views_activity_cards_common import group_header, no_data_msg, source_badge


# ── PMC 차트 (기존 _render_pmc_sparkline_card 이동) ──────────────────────

def _pmc_chart(pmc: dict) -> str:
    """TRIMP_daily + ACWR 60일 ECharts 차트."""
    if not pmc or not pmc.get("dates"):
        return "<p class='muted' style='margin:0.3rem 0;'>PMC 데이터 수집 중 — 메트릭 재계산 후 표시됩니다.</p>"
    dates = pmc["dates"]
    trimp = pmc["trimp"]
    acwr = pmc["acwr"]
    target = pmc.get("target_date", "")
    mark = f', markLine:{{data:[{{xAxis:"{target}",lineStyle:{{color:"#fff",type:"dashed",opacity:0.4}}}}]}}' if target in dates else ""
    return f"""<div id="pmc-chart" style="height:180px;"></div>
  <script>(function(){{
    var ec=echarts.init(document.getElementById('pmc-chart'),'dark',{{backgroundColor:'transparent'}});
    ec.setOption({{
      grid:{{top:20,bottom:30,left:36,right:50}},
      legend:{{top:0,right:0,textStyle:{{fontSize:10,color:'#aaa'}},itemWidth:10,itemHeight:6}},
      tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}}}},
      xAxis:{{type:'category',data:{_json.dumps(dates)},
        axisLabel:{{fontSize:9,color:'#888',formatter:function(v){{return v.slice(5);}}}},
        axisLine:{{lineStyle:{{color:'#444'}}}}}},
      yAxis:[
        {{type:'value',name:'TRIMP',nameTextStyle:{{fontSize:9,color:'#74c0fc'}},
          axisLabel:{{fontSize:9,color:'#74c0fc'}},splitLine:{{lineStyle:{{color:'#2a2a3a'}}}}}},
        {{type:'value',name:'ACWR',nameTextStyle:{{fontSize:9,color:'#ffd43b'}},
          axisLabel:{{fontSize:9,color:'#ffd43b'}},min:0,max:2.0,splitLine:{{show:false}},
          markArea:{{silent:true,data:[[{{yAxis:0.8,itemStyle:{{color:'rgba(0,255,136,0.06)'}}}},{{yAxis:1.3}}]]}}}}
      ],
      series:[
        {{name:'TRIMP',type:'bar',data:{_json.dumps(trimp)},itemStyle:{{color:'rgba(116,192,252,0.6)'}}{mark}}},
        {{name:'ACWR',type:'line',yAxisIndex:1,data:{_json.dumps(acwr)},
          lineStyle:{{color:'#ffd43b',width:2}},symbol:'none',
          markLine:{{silent:true,data:[
            {{yAxis:0.8,lineStyle:{{color:'rgba(0,255,136,0.4)',type:'dashed'}}}},
            {{yAxis:1.3,lineStyle:{{color:'rgba(255,68,68,0.4)',type:'dashed'}}}}
          ]}}}}
      ]
    }});
    window.addEventListener('resize',function(){{ec.resize();}});
  }})();</script>"""


# ── DI 카드 (기존 _render_di_card 이동) ──────────────────────────────────

def _di_section(day_metrics: dict) -> str:
    """DI (내구성 지수) 섹션."""
    di = day_metrics.get("DI")
    if di is None:
        return (
            "<div style='margin-top:0.6rem;padding-top:0.5rem;border-top:1px solid var(--row-border);'>"
            "<div style='font-size:0.82rem;font-weight:600;color:var(--muted);'>DI 내구성 지수</div>"
            "<p class='muted' style='font-size:0.78rem;margin:4px 0;'>90분+ 세션 3회 이상 필요</p></div>"
        )
    di_f = float(di)
    if di_f >= 1.0:
        badge, color, interp = "우수", "var(--green)", "후반에도 효율 유지"
    elif di_f >= 0.9:
        badge, color, interp = "보통", "var(--orange)", "후반 효율 소폭 저하"
    else:
        badge, color, interp = "부족", "var(--red)", "후반 페이스 저하 뚜렷"
    return (
        "<div style='margin-top:0.6rem;padding-top:0.5rem;border-top:1px solid var(--row-border);'>"
        "<div style='display:flex;align-items:center;gap:0.8rem;'>"
        f"<span style='font-size:0.82rem;color:var(--muted);font-weight:600;'>DI 내구성</span>"
        f"<span style='font-size:1.4rem;font-weight:700;color:var(--cyan);'>{di_f:.3f}</span>"
        f"<span style='font-size:0.78rem;color:{color};background:rgba(255,255,255,0.08);"
        f"border-radius:10px;padding:0.15rem 0.5rem;'>{badge}</span></div>"
        f"<p style='font-size:0.78rem;color:var(--secondary);margin:4px 0 0;'>{interp}</p>"
        "</div>"
    )


# ── DARP 요약 ────────────────────────────────────────────────────────────

def _darp_summary(darp_data: dict | None) -> str:
    """DARP 레이스 예측 요약 + 링크."""
    if not darp_data:
        return (
            "<div style='margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--row-border);'>"
            "<div style='display:flex;justify-content:space-between;align-items:center;'>"
            "<span style='font-size:0.82rem;color:var(--muted);font-weight:600;'>DARP 레이스 예측</span>"
            "<a href='/race' style='font-size:0.78rem;color:var(--cyan);'>레이스 예측 →</a></div>"
            "<p class='muted' style='font-size:0.78rem;margin:4px 0;'>데이터 부족 — 레이스 페이지에서 확인</p></div>"
        )
    rows = ""
    for dist in ("5k", "10k", "half", "full"):
        key = f"DARP_{dist}"
        d = darp_data.get(key)
        if not d:
            continue
        pace = d.get("pace_sec_km")
        time_sec = d.get("time_sec")
        label = {"5k": "5K", "10k": "10K", "half": "하프", "full": "풀"}.get(dist, dist)
        pace_str = fmt_pace(pace) if pace else "—"
        if time_sec:
            h, rem = divmod(int(time_sec), 3600)
            m, s = divmod(rem, 60)
            time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        else:
            time_str = "—"
        rows += (
            f"<div style='display:flex;justify-content:space-between;padding:0.25rem 0;"
            f"font-size:0.82rem;'>"
            f"<span style='color:var(--muted);'>{label}</span>"
            f"<span>{pace_str}/km · {time_str}</span></div>"
        )
    return (
        "<div style='margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--row-border);'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
        "<span style='font-size:0.82rem;color:var(--muted);font-weight:600;'>DARP 레이스 예측</span>"
        "<a href='/race' style='font-size:0.78rem;color:var(--cyan);'>상세 →</a></div>"
        + rows + "</div>"
    )


# ── Fitness Context 행 ───────────────────────────────────────────────────

def _fitness_rows(ctx: dict) -> str:
    """CTL/ATL/TSB 행."""
    parts = ""
    for label, key in [("CTL (만성 부하)", "ctl"), ("ATL (급성 부하)", "atl"), ("TSB (부하 균형)", "tsb")]:
        v = ctx.get(key)
        if v is not None:
            parts += (
                f"<div style='display:flex;justify-content:space-between;padding:0.3rem 0;"
                f"border-bottom:1px solid var(--row-border);font-size:0.85rem;'>"
                f"<span style='color:var(--muted);'>{label}</span>"
                f"<span style='font-weight:600;'>{float(v):.1f}</span></div>"
            )
    return parts


# ── 메인 렌더 ───────────────────────────────────────────────────────────

def render_group7_fitness(
    fitness_ctx: dict,
    pmc_series: dict | None = None,
    day_metrics: dict | None = None,
    darp_data: dict | None = None,
) -> str:
    """그룹7 — 피트니스 컨텍스트 카드."""
    dm = day_metrics or {}
    ctx = fitness_ctx or {}

    pmc_html = _pmc_chart(pmc_series or {})
    ctx_rows = _fitness_rows(ctx)
    di_html = _di_section(dm)
    darp_html = _darp_summary(darp_data)

    return (
        "<div class='card'>"
        + group_header("피트니스 컨텍스트", "장기적으로 어디쯤인가?")
        + ctx_rows
        + pmc_html
        + di_html
        + darp_html
        + "</div>"
    )
