"""레포트 섹션 — 메트릭 카드 렌더러.

views_report_sections.py에서 분리.
TIDS/TRIMP/Risk/DARP/Fitness/Endurance 렌더.
"""
from __future__ import annotations

import json

from .helpers import METRIC_DESCRIPTIONS, fmt_pace, no_data_card, tooltip


def render_tids_section(tids: dict | None) -> str:
    """TIDS 훈련 강도 분포 섹션."""
    if not tids:
        return no_data_card("TIDS 훈련 강도 분포", "데이터 수집 중입니다")
    z12 = tids.get("z12", 0)
    z3 = tids.get("z3", 0)
    z45 = tids.get("z45", 0)
    dominant = tids.get("dominant_model") or "—"
    model_labels = {"polarized": "폴라리제드", "pyramid": "피라미드", "health": "건강유지"}
    dominant_lbl = model_labels.get(dominant, dominant)

    def _bar(label: str, pct: float, target: float, color: str) -> str:
        diff = pct - target
        diff_str = f"+{diff:.0f}%" if diff > 0 else f"{diff:.0f}%"
        diff_color = "var(--orange)" if abs(diff) > 10 else "var(--muted)"
        return (
            f"<div style='margin-bottom:0.4rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:0.15rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='font-weight:600;'>{pct:.1f}% <span style='color:{diff_color};font-size:0.74rem;'>({diff_str})</span></span></div>"
            f"<div style='background:rgba(255,255,255,0.08);border-radius:4px;height:8px;position:relative;'>"
            f"<div style='width:{min(pct,100):.1f}%;background:{color};border-radius:4px;height:8px;'></div>"
            f"<div style='position:absolute;left:{min(target,100):.1f}%;top:-2px;width:2px;height:12px;"
            f"background:rgba(255,255,255,0.5);border-radius:1px;'></div></div></div>"
        )

    bars = (
        _bar("Zone 1-2 (저강도)", z12, 80, "#00d4ff")
        + _bar("Zone 3 (중강도)", z3, 5, "#ffaa00")
        + _bar("Zone 4-5 (고강도)", z45, 15, "#ff4444")
    )
    deviations = [
        ("폴라리제드", tids.get("polar_dev", 100)),
        ("피라미드", tids.get("pyramid_dev", 100)),
        ("건강유지", tids.get("health_dev", 100)),
    ]
    _MODEL_DESC = {
        "폴라리제드": "80% 저강도 + 20% 고강도. 엘리트 선수가 주로 사용. 효율적 체력 향상",
        "피라미드": "저강도 > 중강도 > 고강도 순. 일반 러너에게 안전. 점진적 강화",
        "건강유지": "대부분 저강도. 건강 목적 러닝. 부상 위험 최소",
    }
    pill_parts = []
    for m, d in deviations:
        is_dom = m == dominant
        bg_alpha = "0.15" if is_dom else "0.06"
        pill_clr = "var(--cyan)" if is_dom else "var(--muted)"
        lbl = model_labels.get(m, m)
        desc = _MODEL_DESC.get(lbl, "")
        tip = tooltip(f"{lbl} {d:.0f}pt", f"{desc}. 편차 점수가 낮을수록 해당 모델에 가까움") if desc else f"{lbl} {d:.0f}pt"
        pill_parts.append(
            f"<span style='background:rgba(255,255,255,{bg_alpha});border-radius:12px;"
            f"padding:0.2rem 0.6rem;font-size:0.76rem;color:{pill_clr};'>{tip}</span>"
        )
    dev_pills = " ".join(pill_parts)
    dominant_desc = _MODEL_DESC.get(dominant_lbl, "")
    dominant_tip = tooltip(dominant_lbl, dominant_desc) if dominant_desc else dominant_lbl
    return (
        "<div class='card'>"
        f"<h2 style='font-size:1rem;margin-bottom:0.3rem;'>{tooltip('TIDS 훈련 강도 분포', METRIC_DESCRIPTIONS['TIDS'])}</h2>"
        f"<p style='font-size:0.8rem;color:var(--secondary);margin-bottom:0.6rem;'>"
        f"현재 모델: <strong style='color:var(--cyan);'>{dominant_tip}</strong> (편차 최소)</p>"
        f"{bars}"
        f"<div style='display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.4rem;'>{dev_pills}</div>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>수직선(|) = 폴라리제드 목표값 기준</p>"
        "</div>"
    )


def render_trimp_weekly_chart(trimp_data: list[dict], prev_trimp: list[dict] | None = None) -> str:
    """주별 TRIMP 합계 ECharts 바차트 + 이전 기간 비교선."""
    if not trimp_data:
        return no_data_card("주별 TRIMP 부하", "데이터 수집 중입니다")

    def _week_label(w: str) -> str:
        try:
            from datetime import datetime, timedelta
            year, wk = w.split("-")
            jan1 = datetime(int(year), 1, 1)
            start = jan1 + timedelta(weeks=int(wk), days=-jan1.weekday())
            return f"{start.month}/{start.day}"
        except Exception:
            return w

    labels = [_week_label(d["week"]) for d in trimp_data]
    values = [d["trimp"] for d in trimp_data]
    avg = sum(values) / len(values) if values else 0
    lj = json.dumps(labels)
    vj = json.dumps(values)
    prev_series = ""
    prev_note = ""
    if prev_trimp and len(prev_trimp) >= 2:
        prev_vals = [d["trimp"] for d in prev_trimp]
        while len(prev_vals) < len(values):
            prev_vals.append(None)
        prev_vals = prev_vals[:len(values)]
        pj = json.dumps(prev_vals)
        prev_series = (
            f",{{name:'이전 기간',type:'line',data:{pj},smooth:true,symbol:'none',"
            f"lineStyle:{{color:'rgba(255,255,255,0.25)',width:1.5,type:'dashed'}},"
            f"itemStyle:{{color:'rgba(255,255,255,0.25)'}}}}"
        )
        prev_note = " | 점선 = 이전 동일 기간"
    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.8rem;'>주별 TRIMP 훈련 부하</h2>
  <div id='trimpChart' style='height:180px;'></div>
  <p class='muted' style='font-size:0.78rem;margin:0.3rem 0 0;'>주평균 {avg:.0f} TRIMP | 높을수록 고강도/고볼륨{prev_note}</p>
</div>
<script>
(function(){{
  var el=document.getElementById('trimpChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    grid:{{left:48,right:12,bottom:36,top:12}},
    xAxis:{{type:'category',data:{lj},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:9,rotate:30}}}},
    yAxis:{{type:'value',axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}},
      splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    series:[{{name:'이번 기간',type:'bar',data:{vj},itemStyle:{{color:'#ffaa00',borderRadius:[3,3,0,0]}},
      markLine:{{silent:true,data:[{{type:'average',label:{{formatter:'avg {{c}}',color:'#00d4ff',fontSize:10}},
        lineStyle:{{color:'#00d4ff',type:'dashed'}}}}]}}}}{prev_series}]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


def render_risk_overview(risk: dict) -> str:
    """ACWR / LSI / Monotony / CIRS 위험 개요 카드."""
    if not risk:
        return no_data_card("위험 지표 개요", "데이터 수집 중입니다")

    def _risk_row(label: str, key: str, lo: float, hi: float, fmt: str = ".2f") -> str:
        d = risk.get(key)
        if not d:
            return ""
        avg, mx = d["avg"], d["max"]
        if avg <= lo:
            clr, status = "var(--green)", "적정"
        elif avg <= hi:
            clr, status = "var(--orange)", "주의"
        else:
            clr, status = "var(--red)", "위험"
        desc = METRIC_DESCRIPTIONS.get(key, "")
        tip = tooltip(label, desc) if desc else label
        return (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.83rem;'>"
            f"<span style='color:var(--secondary);'>{tip}</span>"
            f"<div style='text-align:right;'>"
            f"<span style='color:{clr};font-weight:600;'>평균 {avg:{fmt}}</span>"
            f"<span class='muted' style='font-size:0.74rem;margin-left:0.4rem;'>최고 {mx:{fmt}}</span>"
            f"<span style='font-size:0.7rem;margin-left:0.3rem;color:{clr};'>({status})</span>"
            f"<span class='muted' style='font-size:0.68rem;margin-left:0.3rem;'>적정 ≤{lo:{fmt}}</span>"
            f"</div></div>"
        )

    rows = (
        _risk_row("ACWR (급성/만성 부하비)", "ACWR", 1.3, 1.5)
        + _risk_row("LSI (부하 스파이크)", "LSI", 1.0, 1.5)
        + _risk_row("Monotony (훈련 단조로움)", "Monotony", 1.5, 2.0)
        + _risk_row("CIRS (복합 부상 위험)", "CIRS", 50, 75, ".0f")
    )
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>위험 지표 개요</h2>"
        + (rows if rows else "<p class='muted' style='margin:0;'>데이터 수집 중</p>")
        + "</div>"
    )


def render_darp_card(darp: dict, vdot: float | None = None, di: float | None = None) -> str:
    """레이스 예측 (DARP) 카드."""
    if not darp:
        return no_data_card("레이스 예측 (DARP)", "데이터 수집 중입니다")
    header_badges = ""
    if vdot is not None:
        vdot_tip = tooltip("VDOT", METRIC_DESCRIPTIONS.get("VDOT", ""))
        header_badges += (
            f"<span style='background:rgba(0,212,255,0.15);color:var(--cyan);"
            f"border-radius:12px;padding:0.15rem 0.6rem;font-size:0.78rem;'>"
            f"{vdot_tip} {vdot:.1f}</span>"
        )
    if di is not None:
        di_tip = tooltip("DI", METRIC_DESCRIPTIONS.get("DI", ""))
        di_clr = "var(--green)" if di >= 70 else "var(--orange)" if di >= 40 else "var(--red)"
        header_badges += (
            f"<span style='background:rgba(0,255,136,0.12);color:{di_clr};"
            f"border-radius:12px;padding:0.15rem 0.6rem;font-size:0.78rem;margin-left:0.3rem;'>"
            f"{di_tip} {di:.0f}</span>"
        )
    _LABELS = {"5k": "5K", "10k": "10K", "half": "하프마라톤", "full": "마라톤"}
    rows = ""
    for key, lbl in _LABELS.items():
        d = darp.get(key)
        if not d:
            continue
        ts = int(d.get("time_sec") or 0)
        pace = d.get("pace_sec_km") or 0
        h, rem = divmod(ts, 3600)
        m, s = divmod(rem, 60)
        t_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        rows += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.06);'>"
            f"<span style='font-size:0.85rem;color:var(--secondary);'>{lbl}</span>"
            f"<div style='text-align:right;'>"
            f"<span style='font-size:0.9rem;font-weight:700;color:var(--cyan);'>{t_str}</span>"
            f"<span class='muted' style='font-size:0.76rem;margin-left:0.4rem;'>{fmt_pace(pace)}/km</span>"
            f"</div></div>"
        )
    if not rows:
        return no_data_card("레이스 예측 (DARP)", "데이터 수집 중입니다")
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.4rem;'>레이스 예측 (DARP)</h2>"
        + (f"<div style='margin-bottom:0.5rem;'>{header_badges}</div>" if header_badges else "")
        + rows
        + "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>VDOT 기반 + DI 내구성 보정</p></div>"
    )


def render_fitness_trend(vdot: float | None, shape: float | None) -> str:
    """VDOT + Marathon Shape 피트니스 현황 카드."""
    if vdot is None and shape is None:
        return no_data_card("피트니스 현황", "데이터 수집 중입니다")
    vdot_str = f"{vdot:.1f}" if vdot is not None else "—"
    shape_str = f"{shape:.0f}%" if shape is not None else "—"
    s_clr = ("var(--green)" if (shape or 0) >= 70
             else ("var(--orange)" if (shape or 0) >= 50 else "var(--muted)"))
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.5rem;'>피트니스 현황</h2>"
        "<div style='display:flex;gap:1.5rem;justify-content:space-around;'>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:2rem;font-weight:700;color:var(--cyan);'>{vdot_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>VDOT</div>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin-top:0.1rem;'>유산소 용량 지수</div></div>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:2rem;font-weight:700;color:{s_clr};'>{shape_str}</div>"
        f"<div class='muted' style='font-size:0.76rem;'>Race Shape</div>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin-top:0.1rem;'>목표 거리별 훈련 준비도</div></div></div>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.5rem;text-align:center;'>RunPulse 추정 | 70%+ 이상적</p></div>"
    )


def render_endurance_trend(adti: float | None) -> str:
    """ADTI 유산소 분리 추세 카드."""
    if adti is None:
        return no_data_card("지구력 추세 (ADTI)", "8주 이상 데이터 필요")
    if adti < -0.002:
        icon, clr, msg = "&#8600;", "var(--red)", "유산소 효율 저하 추세. 쉬운 장거리 훈련 강화 권장."
    elif adti < 0:
        icon, clr, msg = "&#8596;", "var(--orange)", "소폭 저하. 현재 훈련량 유지하며 모니터링 필요."
    elif adti < 0.002:
        icon, clr, msg = "&#8596;", "var(--green)", "지구력 안정 유지 중."
    else:
        icon, clr, msg = "&#8599;", "var(--cyan)", "유산소 효율 개선 추세. 훈련 효과가 나타나고 있음."
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.4rem;'>지구력 추세 (ADTI)</h2>"
        "<div style='display:flex;align-items:center;gap:0.8rem;margin-bottom:0.4rem;'>"
        f"<span style='font-size:2rem;color:{clr};'>{icon}</span>"
        f"<div><div style='font-size:1.3rem;font-weight:700;color:{clr};'>{adti:.4f}</div>"
        f"<div class='muted' style='font-size:0.74rem;'>기울기 (초/km/주)</div></div></div>"
        f"<p style='font-size:0.82rem;color:var(--secondary);margin:0;'>{msg}</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.3rem;'>8주간 Aerobic Decoupling 선형 회귀 기울기</p></div>"
    )
