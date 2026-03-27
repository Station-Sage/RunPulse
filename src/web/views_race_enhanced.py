"""레이스 예측 보강 — 추세 차트, 목표 갭, 준비 요소, 메트릭 해설.

views_race.py에서 호출되는 신규 섹션 렌더러.
"""
from __future__ import annotations

import json
import sqlite3

from .helpers import fmt_duration, fmt_pace, no_data_card


# ── 데이터 로더 ──────────────────────────────────────────────────────────────

def load_prediction_trend(conn: sqlite3.Connection, darp_key: str, weeks: int = 12) -> dict:
    """DARP 예측 시간 + VDOT 추세 (12주)."""
    days = weeks * 7
    rows = conn.execute(
        """SELECT date, metric_value, metric_json FROM computed_metrics
           WHERE metric_name = ? AND activity_id IS NULL
             AND date >= date('now', '-' || ? || ' days')
           ORDER BY date""",
        (darp_key, days),
    ).fetchall()
    darp_dates, darp_times, vdot_vals = [], [], []
    for d, val, mj_raw in rows:
        if val is None:
            continue
        darp_dates.append(d)
        darp_times.append(round(float(val)))
        mj = json.loads(mj_raw) if isinstance(mj_raw, str) and mj_raw else {}
        vdot_vals.append(round(float(mj["vdot"]), 1) if mj.get("vdot") else None)
    return {"dates": darp_dates, "times": darp_times, "vdot": vdot_vals}


def load_fitness_factors(conn: sqlite3.Connection) -> dict:
    """DI / MarathonShape / EF 최근 12주 추세."""
    days = 84
    result: dict = {}
    for name in ("DI", "MarathonShape"):
        rows = conn.execute(
            """SELECT date, metric_value FROM computed_metrics
               WHERE metric_name = ? AND activity_id IS NULL
                 AND date >= date('now', '-' || ? || ' days')
               ORDER BY date""",
            (name, days),
        ).fetchall()
        result[name] = {
            "dates": [r[0] for r in rows if r[1] is not None],
            "values": [round(float(r[1]), 1) for r in rows if r[1] is not None],
        }
    # EF (활동별)
    ef_rows = conn.execute(
        """SELECT date, metric_value FROM computed_metrics
           WHERE metric_name = 'EF' AND activity_id IS NOT NULL
             AND date >= date('now', '-' || ? || ' days')
           ORDER BY date""",
        (days,),
    ).fetchall()
    result["EF"] = {
        "dates": [r[0] for r in ef_rows if r[1] is not None],
        "values": [round(float(r[1]), 4) for r in ef_rows if r[1] is not None],
    }
    return result


# ── 섹션 1b: 목표 갭 ─────────────────────────────────────────────────────────

def render_goal_gap(darp_val: float | None, active_km: float,
                    vdot: float | None = None, di_val: float | None = None) -> str:
    """목표 시간 입력 + 갭 표시 + 구체적 훈련 권장 JS."""
    if darp_val is None:
        return ""
    pred_sec = int(darp_val)
    return (
        f"<div class='card' style='margin:12px 0;'>"
        f"<div style='font-size:0.9rem;color:var(--secondary);margin-bottom:0.4rem;'>목표 시간 설정</div>"
        f"<div style='display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;'>"
        f"<input type='number' id='goalH' placeholder='시' min='0' max='9' style='width:50px;"
        f"background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem;font-size:0.9rem;text-align:center;'/>"
        f"<span>:</span>"
        f"<input type='number' id='goalM' placeholder='분' min='0' max='59' style='width:50px;"
        f"background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem;font-size:0.9rem;text-align:center;'/>"
        f"<span>:</span>"
        f"<input type='number' id='goalS' placeholder='초' min='0' max='59' style='width:50px;"
        f"background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem;font-size:0.9rem;text-align:center;'/>"
        f"<button onclick='calcGap()' style='background:var(--cyan);color:#000;border:none;"
        f"border-radius:8px;padding:0.3rem 0.8rem;font-size:0.85rem;font-weight:600;cursor:pointer;'>계산</button>"
        f"</div>"
        f"<div id='gapResult' style='margin-top:0.4rem;font-size:0.9rem;'></div>"
        f"<div id='gapTips' style='margin-top:0.3rem;font-size:0.82rem;color:var(--secondary);'></div>"
        f"</div>"
        f"<script>"
        f"function calcGap(){{"
        f"var h=parseInt(document.getElementById('goalH').value)||0;"
        f"var m=parseInt(document.getElementById('goalM').value)||0;"
        f"var s=parseInt(document.getElementById('goalS').value)||0;"
        f"var goal=h*3600+m*60+s;if(goal<=0)return;"
        f"var pred={pred_sec};var diff=pred-goal;"
        f"var abs=Math.abs(diff);var dh=Math.floor(abs/3600);var dm=Math.floor((abs%3600)/60);var ds=abs%60;"
        f"var t=(dh?dh+':':'')+(dm<10&&dh?'0':'')+dm+':'+(ds<10?'0':'')+ds;"
        f"var el=document.getElementById('gapResult');"
        f"var tips=document.getElementById('gapTips');"
        f"if(diff>0){{el.innerHTML="
        f"'<span style=\"color:var(--orange)\">목표까지 -'+t+' 더 빨라져야 합니다</span>';"
        f"var pct=((diff/goal)*100).toFixed(1);"
        # 목표 갭 기반 구체적 권장 (#7)
        f"var r=[];"
        f"if(pct>10)r.push('VDOT 3~5 향상 필요 → 주 2회 인터벌(VO2max 구간) + 주 1회 템포런 추가');"
        f"else if(pct>5)r.push('VDOT 1~3 향상 필요 → 주 1회 인터벌 + 장거리 10% 거리 증가');"
        f"else r.push('소폭 개선 필요 → 현재 훈련 유지하면서 레이스 페이스 연습 추가');"
        + (f"if({int(di_val)}<50)r.push('DI 부족 → 90분+ 장거리 러닝 주 1회 이상 확보');" if di_val is not None and di_val < 50 else "")
        + (f"if({int(di_val)}<70)r.push('DI 보통 → 장거리 후반 페이스 유지 훈련(네거티브 스플릿) 권장');" if di_val is not None and 50 <= di_val < 70 else "")
        + f"tips.innerHTML=r.length?'<ul style=\"margin:0.3rem 0;padding-left:1.2rem;\">'+r.map(function(x){{return '<li>'+x+'</li>'}}).join('')+'</ul>':'';"
        f"}}else if(diff<0){{el.innerHTML="
        f"'<span style=\"color:var(--green)\">목표 대비 +'+t+' 여유가 있습니다</span>';"
        f"tips.innerHTML='<p style=\"margin:0.3rem 0;\">현재 체력으로 목표 달성 가능합니다. 컨디션 유지에 집중하세요.</p>';"
        f"}}else{{el.innerHTML="
        f"'<span style=\"color:var(--cyan)\">목표 시간과 정확히 일치합니다!</span>';"
        f"tips.innerHTML='';}}"
        f"}}</script>"
    )


# ── 섹션 2: 예측 추세 차트 ───────────────────────────────────────────────────

def render_prediction_trend_chart(trend: dict) -> str:
    """DARP 예측 시간 + VDOT 12주 추세 차트."""
    dates = trend.get("dates", [])
    if len(dates) < 2:
        return ""
    dj = json.dumps([d[5:] for d in dates])
    # 시간을 분:초 형식으로 표시하되 raw는 초 단위
    tj = json.dumps(trend.get("times", []))
    vj = json.dumps(trend.get("vdot", []))

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>예측 추세</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>빨라지고 있나?</p>
  <div id='predTrendChart' style='height:200px;'></div>
</div>
<script>
(function(){{
  var el=document.getElementById('predTrendChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={dj},times={tj},vdot={vj};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis',formatter:function(p){{
      var s=p[0].axisValue+'<br>';
      p.forEach(function(x){{
        if(x.seriesName==='예측시간'){{
          var t=x.value;var h=Math.floor(t/3600);var m=Math.floor((t%3600)/60);var sc=t%60;
          s+=x.marker+'예측: '+(h?h+':':'')+(m<10&&h?'0':'')+m+':'+(sc<10?'0':'')+sc+'<br>';
        }}else{{s+=x.marker+x.seriesName+': '+x.value+'<br>';}}
      }});return s;}}}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:55,right:48,bottom:25,top:30}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
    yAxis:[
      {{type:'value',name:'시간(초)',inverse:true,
        splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,
          formatter:function(v){{var m=Math.floor(v/60);var s=v%60;return m+':'+(s<10?'0':'')+s;}}}}}},
      {{type:'value',name:'VDOT',position:'right',splitLine:{{show:false}},
        axisLabel:{{color:'#cc88ff',fontSize:10}}}}
    ],
    series:[
      {{name:'예측시간',type:'line',data:times,smooth:true,symbol:'circle',symbolSize:4,
        lineStyle:{{color:'#00d4ff',width:2}},itemStyle:{{color:'#00d4ff'}},yAxisIndex:0}},
      {{name:'VDOT',type:'line',data:vdot,smooth:true,symbol:'circle',symbolSize:4,
        connectNulls:true,lineStyle:{{color:'#cc88ff',width:1.5}},itemStyle:{{color:'#cc88ff'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── 섹션 3: 레이스 준비 요소 ─────────────────────────────────────────────────

def render_fitness_factors_chart(factors: dict) -> str:
    """DI / MarathonShape / EF 추세 차트."""
    di = factors.get("DI", {})
    ms = factors.get("MarathonShape", {})
    ef = factors.get("EF", {})
    if not di.get("dates") and not ms.get("dates") and not ef.get("dates"):
        return ""

    all_dates = sorted(set(di.get("dates", []) + ms.get("dates", []) + ef.get("dates", [])))
    di_map = dict(zip(di.get("dates", []), di.get("values", [])))
    ms_map = dict(zip(ms.get("dates", []), ms.get("values", [])))
    ef_map = dict(zip(ef.get("dates", []), ef.get("values", [])))

    labels = json.dumps([d[5:] for d in all_dates])
    di_j = json.dumps([di_map.get(d) for d in all_dates])
    ms_j = json.dumps([ms_map.get(d) for d in all_dates])
    ef_j = json.dumps([ef_map.get(d) for d in all_dates])

    # DI 해석
    di_latest = di.get("values", [None])[-1] if di.get("values") else None
    di_interp = ""
    if di_latest is not None:
        if di_latest >= 70:
            di_interp = f"DI {di_latest:.0f} → 후반 페이스 유지력 우수, 네거티브 스플릿 전략 가능"
        elif di_latest >= 40:
            di_interp = f"DI {di_latest:.0f} → 후반 소폭 페이스 드롭 예상, 이븐 스플릿 전략 권장"
        else:
            di_interp = f"DI {di_latest:.0f} → 후반 페이스 급락 위험, 보수적 전략 + 장거리 훈련 필요"

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.3rem;'>레이스 준비 요소</h2>
  <p class='muted' style='font-size:0.74rem;margin:0 0 0.5rem;'>어떤 체력 요소가 개선/부족한가?</p>
  <div id='factorsChart' style='height:200px;'></div>
  {"<p style='font-size:0.82rem;color:var(--secondary);margin:0.4rem 0 0;'>" + di_interp + "</p>" if di_interp else ""}
</div>
<script>
(function(){{
  var el=document.getElementById('factorsChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  var dates={labels};
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:48,right:48,bottom:25,top:30}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,interval:Math.floor(dates.length/6)}}}},
    yAxis:[
      {{type:'value',name:'DI/Shape',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}},
      {{type:'value',name:'EF',position:'right',splitLine:{{show:false}},
        axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}}}}
    ],
    series:[
      {{name:'DI',type:'line',data:{di_j},smooth:true,symbol:'circle',symbolSize:4,
        connectNulls:true,lineStyle:{{color:'#00ff88',width:2}},itemStyle:{{color:'#00ff88'}},yAxisIndex:0}},
      {{name:'Race Shape',type:'line',data:{ms_j},smooth:true,symbol:'circle',symbolSize:4,
        connectNulls:true,lineStyle:{{color:'#ffaa00',width:1.5}},itemStyle:{{color:'#ffaa00'}},yAxisIndex:0}},
      {{name:'EF',type:'line',data:{ef_j},smooth:true,symbol:'circle',symbolSize:3,
        connectNulls:true,lineStyle:{{color:'#00d4ff',width:1.5}},itemStyle:{{color:'#00d4ff'}},yAxisIndex:1}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── Race Shape 3거리 비교 ──────────────────────────────────────────────────


def render_race_shape_trio(conn, target_date: str | None = None) -> str:
    """10K / Half / Marathon Race Shape를 나란히 표시."""
    from datetime import date as _d
    from src.metrics.marathon_shape import (
        calc_marathon_shape, _get_vdot, _get_recent_running_data,
        _calc_consistency, _calc_long_run_stats, _get_race_targets,
    )

    today = target_date or _d.today().isoformat()
    vdot = _get_vdot(conn, today)
    if vdot is None:
        return ""

    distances = [
        ("10K", 10.0),
        ("하프", 21.0975),
        ("마라톤", 42.195),
    ]

    cards = []
    for label, km in distances:
        targets = _get_race_targets(vdot, km)
        weeks = targets["consistency_weeks"]
        data_weeks = min(weeks, 4)
        weekly_avg, longest = _get_recent_running_data(conn, today, weeks=data_weeks)
        consistency = _calc_consistency(conn, today, weeks=weeks)
        long_count, long_quality = _calc_long_run_stats(
            conn, today, weeks=weeks,
            threshold_km=targets["long_threshold"], vdot=vdot)
        shape = calc_marathon_shape(
            weekly_avg, longest, vdot,
            consistency_score=consistency,
            race_distance_km=km,
            long_run_count=long_count,
            long_run_quality=long_quality,
        )
        if shape is None:
            continue

        color = "#00ff88" if shape >= 70 else "#ffaa00" if shape >= 50 else "#ff4444"
        target_w = targets["weekly_target"]
        target_l = targets["long_max"]
        target_cnt = targets["long_count_target"]
        weekly_pct = min(100, int(weekly_avg / target_w * 100)) if target_w > 0 else 0
        long_pct = min(100, int(longest / target_l * 100)) if target_l > 0 else 0
        freq_pct = min(100, int(long_count / target_cnt * 100)) if target_cnt > 0 else 0

        cards.append(
            f"<div style='flex:1;min-width:130px;text-align:center;padding:12px;"
            f"background:rgba(255,255,255,0.03);border-radius:12px;'>"
            f"<div style='font-size:0.8rem;color:var(--muted);margin-bottom:4px;'>{label}</div>"
            f"<div style='font-size:1.6rem;font-weight:700;color:{color};'>{shape:.0f}%</div>"
            f"<div style='font-size:0.68rem;color:var(--muted);margin-top:6px;'>"
            f"주간 {weekly_avg:.0f}/{target_w:.0f}km ({weekly_pct}%)</div>"
            f"<div style='font-size:0.68rem;color:var(--muted);'>"
            f"최장 {longest:.0f}/{target_l:.0f}km ({long_pct}%)</div>"
            f"<div style='font-size:0.68rem;color:var(--muted);'>"
            f"장거리 {long_count}/{target_cnt}회 ({freq_pct}%)</div>"
            f"<div style='font-size:0.65rem;color:var(--muted);'>"
            f"일관성 {weeks}주</div>"
            f"</div>"
        )

    if not cards:
        return ""

    return (
        "<div class='card' style='margin-top:12px;'>"
        "<h2 style='font-size:1rem;margin-bottom:10px;'>거리별 Race Shape</h2>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;'>{''.join(cards)}</div>"
        "</div>"
    )


# ── DI 해설 보강 (기존 카드에 추가) ──────────────────────────────────────────

def render_di_interpretation(di_val: float | None, ai_override: str | None = None) -> str:
    """DI 점수에 따른 레이스 영향 해설 — ai_override(탭 통합 AI) 우선, 규칙 기반 fallback."""
    if di_val is None:
        return ""

    # AI 탭 통합 결과 우선
    if ai_override:
        return (
            f"<div style='background:rgba(0,255,136,0.06);border-radius:12px;padding:12px 16px;"
            f"margin:8px 0;font-size:0.82rem;color:var(--secondary);'>"
            f"💡 {ai_override} <span style='font-size:0.6rem;color:var(--cyan);'>AI</span></div>"
        )

    score = int(di_val)
    if score >= 80:
        msg = f"DI {score} = 후반 페이스 드롭 1~2% 이내. 네거티브 스플릿 전략이 효과적입니다."
    elif score >= 60:
        msg = f"DI {score} = 후반 약 3~5% 페이스 드롭 예상. 이븐 페이스 전략이 안전합니다."
    elif score >= 40:
        msg = f"DI {score} = 후반 5~10% 페이스 드롭 가능. 전반 보수적 출발 권장."
    else:
        msg = f"DI {score} = 후반 10%+ 급격한 페이스 드롭 위험. 장거리 훈련 강화가 시급합니다."

    return (
        f"<div style='background:rgba(0,255,136,0.06);border-radius:12px;padding:12px 16px;"
        f"margin:8px 0;font-size:0.82rem;color:var(--secondary);'>"
        f"💡 {msg}</div>"
    )


# ── 섹션 6: 메트릭 해설 (접이식) ─────────────────────────────────────────────

def render_metric_glossary() -> str:
    """VDOT/DI/DARP/MarathonShape 해설 접이식."""
    entries = [
        ("VDOT이란?",
         "Jack Daniels의 VDOT은 러너의 유산소 능력을 단일 숫자로 표현합니다. "
         "최근 레이스 기록이나 훈련 데이터로 추정하며, 값이 높을수록 체력 수준이 좋습니다. "
         "VDOT 1 향상 ≈ 5K 약 15~20초, 마라톤 약 3~4분 기록 단축."),
        ("DI (Durability Index)란?",
         "내구성 지수는 장거리 후반부에서 페이스를 유지하는 능력입니다. "
         "90분 이상 세션에서 전반/후반 페이스 비율로 계산합니다. "
         "70+ = 우수(네거티브 스플릿 가능), 40~70 = 양호, 40 미만 = 장거리 훈련 필요."),
        ("DARP (Dynamic Adjusted Race Prediction)란?",
         "Daniels VDOT 테이블 기반 예측에 내구성(DI)과 훈련 준비도(Race Shape)를 "
         "반영한 보정 레이스 예측입니다. DI가 낮으면 후반 페이스 드롭 반영, "
         "Race Shape가 낮으면 훈련 부족에 따른 시간 추가. 거리별 보정 비율 차등 적용."),
        ("Race Shape이란?",
         "목표 레이스 거리별 훈련 준비도입니다. 주간 볼륨(50%) + 장거리런(30%) + "
         "일관성(20%)을 종합하여 0~100%로 표현합니다. 목표가 10K면 6주, 하프 8주, "
         "마라톤 12주 기준. 70%+ = 준비 양호, 50% 미만 = 훈련 보강 필요."),
    ]
    items = ""
    for title, desc in entries:
        items += (
            f"<details style='margin-bottom:0.4rem;'>"
            f"<summary style='cursor:pointer;font-size:0.88rem;color:var(--cyan);padding:0.3rem 0;'>{title}</summary>"
            f"<p style='font-size:0.82rem;color:var(--secondary);margin:0.3rem 0 0.5rem 1rem;line-height:1.5;'>{desc}</p>"
            f"</details>"
        )
    return (
        "<div class='card' style='margin:20px 0;'>"
        "<h2 style='font-size:1rem;margin-bottom:0.5rem;'>메트릭 해설</h2>"
        + items +
        "</div>"
    )
