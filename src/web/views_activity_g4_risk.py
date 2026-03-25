"""활동 상세 — 그룹4: 과훈련/부상 위험.

"이대로 계속해도 되나?" — ACWR 60일 + Monotony 30일 + Strain 30일 + LSI
스파이크를 하나의 ECharts 멀티라인 차트로 표시.
"""
from __future__ import annotations

import json as _json

from .views_activity_cards_common import group_header, no_data_msg


def render_group4_risk(risk_series: dict | None = None) -> str:
    """그룹4 — 과훈련 위험 멀티라인 차트.

    risk_series: {dates, acwr, monotony, strain, lsi}
    """
    rs = risk_series or {}
    dates = rs.get("dates", [])
    acwr = rs.get("acwr", [])
    monotony = rs.get("monotony", [])
    strain = rs.get("strain", [])
    lsi = rs.get("lsi", [])

    if not dates:
        return no_data_msg("과훈련 위험", "ACWR·Monotony·Strain 데이터 수집 중 — 메트릭 재계산 후 표시됩니다.")

    dates_j = _json.dumps(dates)
    acwr_j = _json.dumps(acwr)
    mono_j = _json.dumps(monotony)
    strain_j = _json.dumps(strain)
    lsi_j = _json.dumps(lsi)

    return f"""<div class='card'>
  {group_header("과훈련 위험", "이대로 계속해도 되나?")}
  <div id="risk-chart" style="height:220px;"></div>
  <div style='display:flex;gap:0.8rem;font-size:0.7rem;color:var(--muted);margin-top:4px;flex-wrap:wrap;'>
    <span><span style='color:#ffd43b;'>■</span> ACWR (0.8~1.3 적정)</span>
    <span><span style='color:#74c0fc;'>■</span> Monotony (&lt;2.0)</span>
    <span><span style='color:#ff6b6b;'>■</span> Strain</span>
    <span><span style='color:#fff;'>●</span> LSI 스파이크</span>
  </div>
  <script>
  (function() {{
    var el = document.getElementById('risk-chart');
    if (!el || typeof echarts === 'undefined') return;
    var ec = echarts.init(el, 'dark', {{backgroundColor:'transparent'}});
    ec.setOption({{
      grid: {{top:20, bottom:30, left:40, right:50}},
      tooltip: {{trigger:'axis', axisPointer:{{type:'cross'}}}},
      xAxis: {{type:'category', data:{dates_j},
        axisLabel:{{fontSize:9, color:'#888', formatter:function(v){{return v.slice(5);}} }},
        axisLine:{{lineStyle:{{color:'#444'}}}}}},
      yAxis: [
        {{type:'value', name:'ACWR / Mono', nameTextStyle:{{fontSize:9,color:'#ffd43b'}},
          axisLabel:{{fontSize:9,color:'#aaa'}}, min:0, max:3,
          splitLine:{{lineStyle:{{color:'#2a2a3a'}}}},
          markArea:{{silent:true, data:[[
            {{yAxis:0.8, itemStyle:{{color:'rgba(0,255,136,0.06)'}}}}, {{yAxis:1.3}}
          ]]}}}},
        {{type:'value', name:'Strain', nameTextStyle:{{fontSize:9,color:'#ff6b6b'}},
          axisLabel:{{fontSize:9,color:'#ff6b6b'}}, splitLine:{{show:false}}}}
      ],
      series: [
        {{name:'ACWR', type:'line', data:{acwr_j},
          lineStyle:{{color:'#ffd43b',width:2}}, symbol:'none',
          markLine:{{silent:true,data:[
            {{yAxis:0.8,lineStyle:{{color:'rgba(0,255,136,0.3)',type:'dashed'}}}},
            {{yAxis:1.3,lineStyle:{{color:'rgba(255,68,68,0.3)',type:'dashed'}}}},
            {{yAxis:1.5,lineStyle:{{color:'rgba(255,68,68,0.5)',type:'dashed'}}}}
          ]}}}},
        {{name:'Monotony', type:'line', data:{mono_j},
          lineStyle:{{color:'#74c0fc',width:1.5}}, symbol:'none',
          markLine:{{silent:true,data:[
            {{yAxis:2.0,lineStyle:{{color:'rgba(116,192,252,0.4)',type:'dashed'}}}}
          ]}}}},
        {{name:'Strain', type:'bar', yAxisIndex:1, data:{strain_j},
          itemStyle:{{color:'rgba(255,107,107,0.4)'}}}},
        {{name:'LSI', type:'scatter', data:{lsi_j},
          symbolSize:function(v){{return v>1.5?10:v>1.3?6:0;}},
          itemStyle:{{color:'#fff',borderColor:'#ff4444',borderWidth:1}}}}
      ]
    }});
    window.addEventListener('resize', function(){{ec.resize();}});
  }})();
  </script>
</div>"""
