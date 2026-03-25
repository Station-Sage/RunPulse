"""레포트 추가 섹션 — views_report.py에서 분리.

추가 데이터 로더 및 렌더 함수:
  - TIDS 훈련 강도 분포
  - TRIMP 주간 부하 추세
  - Risk overview (ACWR/LSI/Monotony/CIRS)
  - Endurance trend (ADTI + Decoupling)
  - DARP 레이스 예측 카드
  - Fitness trend (VDOT + Marathon Shape)
  - AI insight placeholder
  - Export/copy 버튼
"""
from __future__ import annotations

import html as _html
import json
import sqlite3

from .helpers import fmt_duration, fmt_pace, no_data_card


# ── 데이터 로더 ───────────────────────────────────────────────────────────────

def _load_tids_data(conn: sqlite3.Connection, start: str, end: str) -> dict | None:
    """기간 내 최신 TIDS metric_json 조회."""
    row = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name = 'TIDS' AND activity_id IS NULL AND date BETWEEN ? AND ?
           ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def _load_trimp_weekly(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """주별 TRIMP 합계 (활동별 합산)."""
    rows = conn.execute(
        """SELECT strftime('%Y-%W', date) AS week, COALESCE(SUM(metric_value), 0) AS total
           FROM computed_metrics
           WHERE metric_name = 'TRIMP' AND activity_id IS NOT NULL AND date BETWEEN ? AND ?
           GROUP BY week ORDER BY week ASC""",
        (start, end),
    ).fetchall()
    return [{"week": r[0], "trimp": round(float(r[1]), 1)} for r in rows]


def _load_risk_overview(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """기간 내 ACWR / LSI / Monotony / CIRS 평균 및 최고값."""
    rows = conn.execute(
        """SELECT metric_name, AVG(metric_value), MAX(metric_value)
           FROM computed_metrics
           WHERE metric_name IN ('ACWR', 'LSI', 'Monotony', 'CIRS')
             AND activity_id IS NULL AND date BETWEEN ? AND ?
           GROUP BY metric_name""",
        (start, end),
    ).fetchall()
    return {r[0]: {"avg": float(r[1]), "max": float(r[2])} for r in rows}


def _load_adti(conn: sqlite3.Connection, end: str) -> float | None:
    """최신 ADTI (유산소 분리 추세) 값 조회."""
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name = 'ADTI' AND activity_id IS NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (end,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _load_darp_latest(conn: sqlite3.Connection, end: str) -> dict:
    """최신 DARP 거리별 예측값 조회."""
    result = {}
    for key in ("DARP_5k", "DARP_10k", "DARP_half", "DARP_full"):
        row = conn.execute(
            """SELECT metric_value, metric_json FROM computed_metrics
               WHERE metric_name = ? AND activity_id IS NULL AND date <= ?
               ORDER BY date DESC LIMIT 1""",
            (key, end),
        ).fetchone()
        if row and row[0] is not None:
            dist_key = key.split("_", 1)[1]
            try:
                mj = json.loads(row[1]) if row[1] else {}
            except Exception:
                mj = {}
            result[dist_key] = mj or {"pace_sec_km": float(row[0])}
    return result


def _load_fitness_data(conn: sqlite3.Connection, end: str) -> tuple[float | None, float | None]:
    """VDOT + Marathon Shape 최신값."""
    vdot_row = conn.execute(
        "SELECT runalyze_vdot FROM daily_fitness WHERE runalyze_vdot IS NOT NULL AND date<=? ORDER BY date DESC LIMIT 1",
        (end,),
    ).fetchone()
    shape_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='MarathonShape' AND activity_id IS NULL AND date<=?
           ORDER BY date DESC LIMIT 1""",
        (end,),
    ).fetchone()
    return (float(vdot_row[0]) if vdot_row else None,
            float(shape_row[0]) if shape_row and shape_row[0] is not None else None)


# ── 렌더 함수 ─────────────────────────────────────────────────────────────────

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

    # 폴라리제드 모델 기준 (z12=80, z3=5, z45=15)
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
    pill_parts = []
    for m, d in deviations:
        is_dom = m == dominant
        bg_alpha = "0.15" if is_dom else "0.06"
        pill_clr = "var(--cyan)" if is_dom else "var(--muted)"
        lbl = model_labels.get(m, m)
        pill_parts.append(
            f"<span style='background:rgba(255,255,255,{bg_alpha});border-radius:12px;"
            f"padding:0.2rem 0.6rem;font-size:0.76rem;color:{pill_clr};'>{lbl} {d:.0f}pt</span>"
        )
    dev_pills = " ".join(pill_parts)
    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.3rem;'>TIDS 훈련 강도 분포</h2>"
        f"<p style='font-size:0.8rem;color:var(--secondary);margin-bottom:0.6rem;'>"
        f"현재 모델: <strong style='color:var(--cyan);'>{dominant_lbl}</strong> (편차 최소)</p>"
        f"{bars}"
        f"<div style='display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.4rem;'>{dev_pills}</div>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>수직선(|) = 폴라리제드 목표값 기준</p>"
        "</div>"
    )


def render_trimp_weekly_chart(trimp_data: list[dict]) -> str:
    """주별 TRIMP 합계 ECharts 바차트."""
    if not trimp_data:
        return no_data_card("주별 TRIMP 부하", "데이터 수집 중입니다")
    labels = [d["week"] for d in trimp_data]
    values = [d["trimp"] for d in trimp_data]
    avg = sum(values) / len(values) if values else 0
    lj = json.dumps(labels)
    vj = json.dumps(values)
    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.8rem;'>주별 TRIMP 훈련 부하</h2>
  <div id='trimpChart' style='height:180px;'></div>
  <p class='muted' style='font-size:0.78rem;margin:0.3rem 0 0;'>주평균 {avg:.0f} TRIMP | 높을수록 고강도/고볼륨</p>
</div>
<script>
(function(){{
  var el=document.getElementById('trimpChart');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis',formatter:function(p){{return p[0].axisValue+'<br>TRIMP: '+p[0].value.toFixed(0);}}}},
    grid:{{left:48,right:12,bottom:36,top:12}},
    xAxis:{{type:'category',data:{lj},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:9,rotate:30}}}},
    yAxis:{{type:'value',axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}},
      splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    series:[{{type:'bar',data:{vj},itemStyle:{{color:'#ffaa00',borderRadius:[3,3,0,0]}},
      markLine:{{silent:true,data:[{{type:'average',label:{{formatter:'avg {{c}}',color:'#00d4ff',fontSize:10}},
        lineStyle:{{color:'#00d4ff',type:'dashed'}}}}]}}}}]
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
            clr = "var(--green)"
        elif avg <= hi:
            clr = "var(--orange)"
        else:
            clr = "var(--red)"
        return (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.83rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<div style='text-align:right;'>"
            f"<span style='color:{clr};font-weight:600;'>평균 {avg:{fmt}}</span>"
            f"<span class='muted' style='font-size:0.74rem;margin-left:0.4rem;'>최고 {mx:{fmt}}</span></div></div>"
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


def render_darp_card(darp: dict) -> str:
    """레이스 예측 (DARP) 카드."""
    if not darp:
        return no_data_card("레이스 예측 (DARP)", "데이터 수집 중입니다")
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
        vdot = d.get("vdot")
        vdot_note = f" (VDOT {vdot:.1f})" if vdot else ""
        rows += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.06);'>"
            f"<span style='font-size:0.85rem;color:var(--secondary);'>{lbl}</span>"
            f"<div style='text-align:right;'>"
            f"<span style='font-size:0.9rem;font-weight:700;color:var(--cyan);'>{t_str}</span>"
            f"<span class='muted' style='font-size:0.76rem;margin-left:0.4rem;'>{fmt_pace(pace)}/km{vdot_note}</span>"
            f"</div></div>"
        )
    if not rows:
        return no_data_card("레이스 예측 (DARP)", "데이터 수집 중입니다")
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.4rem;'>레이스 예측 (DARP)</h2>"
        + rows
        + "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>Jack Daniels VDOT 기반 + DI 내구성 보정</p></div>"
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
        f"<div class='muted' style='font-size:0.76rem;'>Marathon Shape</div>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin-top:0.1rem;'>주간/장거리 달성도</div></div></div>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.5rem;text-align:center;'>Runalyze 기준 | 70%+ 이상적</p></div>"
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


def render_ai_insight(conn: sqlite3.Connection, start: str, end: str) -> str:
    """AI 인사이트 카드 — 기간별 규칙 기반 분석 인사이트.

    briefing.py의 외부 AI 호출 없이, DB 메트릭 기반으로 주요 인사이트 생성.
    데이터 부족 시 graceful placeholder 표시.
    """
    insights: list[str] = []

    # UTRS 추세 (기간 내 첫 값 vs 마지막 값)
    utrs_rows = conn.execute(
        """SELECT date, metric_value FROM computed_metrics
           WHERE metric_name='UTRS' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date ASC""",
        (start, end),
    ).fetchall()
    if len(utrs_rows) >= 2:
        first_utrs, last_utrs = float(utrs_rows[0][1]), float(utrs_rows[-1][1])
        delta = last_utrs - first_utrs
        if delta > 5:
            insights.append(f"훈련 준비도(UTRS) <strong>+{delta:.0f}</strong> 상승 추세 — 컨디션 개선 중")
        elif delta < -5:
            insights.append(f"훈련 준비도(UTRS) <strong>{delta:.0f}</strong> 하락 — 회복 주간 고려")

    # CIRS 경고
    cirs_rows = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='CIRS' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if cirs_rows and float(cirs_rows[0][0]) > 50:
        insights.append(f"부상 위험(CIRS) <strong>{int(cirs_rows[0][0])}/100</strong> — 부하 조절 필요")

    # Monotony 경고
    mono_rows = conn.execute(
        """SELECT metric_value, metric_json FROM computed_metrics
           WHERE metric_name='Monotony' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if mono_rows and mono_rows[0][0] is not None and float(mono_rows[0][0]) > 1.5:
        insights.append(f"훈련 단조로움 <strong>{float(mono_rows[0][0]):.1f}</strong> — 강도/유형 다양화 권장")

    # TIDS 편향 분석
    tids_rows = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name='TIDS' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if tids_rows and tids_rows[0][0]:
        try:
            import json as _json
            td = _json.loads(tids_rows[0][0])
            z1_pct = td.get("zone1_pct") or td.get("z1_pct", 0)
            z5_pct = td.get("zone5_pct") or td.get("z5_pct", 0)
            z3_pct = td.get("zone3_pct") or td.get("z3_pct", 0)
            if z1_pct > 60 and z5_pct > 15:
                insights.append("강도 분포: <strong>폴라리제드</strong> 패턴 (효율적)")
            elif z3_pct > 40:
                insights.append("강도 분포: <strong>중강도 집중</strong> — 고/저 강도 분리 권장")
        except Exception:
            pass

    # ACWR 상태
    acwr_rows = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='ACWR' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if acwr_rows and acwr_rows[0][0] is not None:
        acwr = float(acwr_rows[0][0])
        if acwr > 1.3:
            insights.append(f"ACWR <strong>{acwr:.2f}</strong> — 급성 부하 과다, 볼륨 감소 권장")
        elif acwr < 0.8:
            insights.append(f"ACWR <strong>{acwr:.2f}</strong> — 훈련 자극 부족, 볼륨 증가 고려")

    # 인사이트가 없으면 데이터 부족 안내
    if not insights:
        return (
            "<div class='card' style='border:1px dashed rgba(0,212,255,0.3);'>"
            "<h2 style='font-size:1rem;margin-bottom:0.4rem;color:var(--cyan);'>AI 코치 인사이트</h2>"
            "<p style='font-size:0.82rem;color:var(--secondary);'>데이터 수집 중 — "
            "메트릭이 쌓이면 자동으로 인사이트가 표시됩니다.</p>"
            "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>"
            "<a href='/ai-coach' style='color:var(--cyan);'>AI 코치</a>에서 전체 분석 보기</p>"
            "</div>"
        )

    items_html = "".join(
        f"<li style='margin-bottom:0.4rem;font-size:0.85rem;color:var(--secondary);'>{i}</li>"
        for i in insights
    )
    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.6rem;color:var(--cyan);'>AI 코치 인사이트</h2>"
        f"<ul style='padding-left:1.2rem;margin:0;'>{items_html}</ul>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.5rem;'>"
        "<a href='/ai-coach' style='color:var(--cyan);'>AI 코치</a>에서 전체 분석 보기</p>"
        "</div>"
    )


def render_ai_insight_placeholder() -> str:
    """하위 호환용 placeholder (conn 없이 호출할 때)."""
    return (
        "<div class='card' style='border:1px dashed rgba(0,212,255,0.3);'>"
        "<h2 style='font-size:1rem;margin-bottom:0.4rem;color:var(--cyan);'>AI 코치 인사이트</h2>"
        "<p style='font-size:0.82rem;color:var(--secondary);'>데이터 수집 중입니다.</p>"
        "</div>"
    )


def render_export_buttons(period: str) -> str:
    """주간 요약 텍스트 복사 버튼."""
    return (
        "<div class='card' style='padding:0.6rem 1rem;'>"
        "<div style='display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center;'>"
        "<span style='font-size:0.8rem;color:var(--muted);'>내보내기</span>"
        f"<button onclick='copyReportSummary(\"{period}\")' "
        "style='background:rgba(0,212,255,0.15);color:var(--cyan);border:1px solid rgba(0,212,255,0.3);"
        "border-radius:16px;padding:0.25rem 0.8rem;font-size:0.78rem;cursor:pointer;'>"
        "&#128203; 요약 복사</button></div></div>"
        "<script>"
        "function copyReportSummary(period){"
        "var txt='[RunPulse 레포트 ' + period + '] ' + document.title + '\\n';"
        "var cards=document.querySelectorAll('.card h2');"
        "cards.forEach(function(h){txt+=h.innerText+'\\n';});"
        "if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){"
        "alert('요약이 클립보드에 복사되었습니다.');});}"
        "}</script>"
    )


# ── views_report.py에서 이동된 렌더 함수 ────────────────────────────────────


def render_summary_cards(stats: dict, metrics_avg: dict) -> str:
    """요약 지표 카드 (활동 수/거리/시간 + 평균 UTRS/CIRS)."""
    utrs_avg = metrics_avg.get("UTRS")
    cirs_avg = metrics_avg.get("CIRS")

    def _card(title: str, value: str, color: str = "var(--fg)") -> str:
        return (
            f"<div class='card'>"
            f"<h2 style='font-size:0.8rem;color:var(--muted);margin-bottom:0.3rem;'>{title}</h2>"
            f"<p style='font-size:1.8rem;font-weight:700;margin:0;color:{color};'>{value}</p>"
            f"</div>"
        )

    utrs_str = f"{utrs_avg:.0f}" if utrs_avg is not None else "—"
    cirs_str = f"{cirs_avg:.0f}" if cirs_avg is not None else "—"
    km_per = f"{stats['total_km'] / stats['count']:.1f} km/회" if stats["count"] > 0 else "—"
    return (
        "<div class='cards-row'>"
        + _card("활동 수", f"{stats['count']}회")
        + _card("총 거리", f"{stats['total_km']:.1f} km", "var(--cyan)")
        + _card("총 시간", fmt_duration(stats["total_sec"]))
        + _card("평균 거리", km_per)
        + "</div>"
        "<div class='cards-row'>"
        + _card("평균 UTRS", utrs_str, "var(--green)" if utrs_avg and utrs_avg >= 60 else "var(--fg)")
        + _card("평균 CIRS", cirs_str, "var(--red)" if cirs_avg and cirs_avg >= 50 else "var(--fg)")
        + "</div>"
    )


def render_weekly_chart(weekly_data: list[dict]) -> str:
    """ECharts 주별 거리 바차트."""
    if not weekly_data:
        return no_data_card("주별 거리 추세", "데이터 수집 중입니다")
    labels = [d["week"] for d in weekly_data]
    values = [d["km"] for d in weekly_data]
    avg_km = sum(values) / len(values) if values else 0
    lj, vj = json.dumps(labels), json.dumps(values)
    return f"""
<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.8rem;'>주별 거리 추세</h2>
  <div id='weeklyDistChart' style='height:200px;'></div>
  <p class='muted' style='font-size:0.78rem;margin:0.4rem 0 0;'>주평균 {avg_km:.1f} km</p>
</div>
<script>
(function() {{
  var el = document.getElementById('weeklyDistChart');
  if (!el || typeof echarts === 'undefined') return;
  var c = echarts.init(el, 'dark', {{backgroundColor: 'transparent'}});
  c.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{trigger:'axis',formatter:function(p){{return p[0].axisValue+'<br>거리: '+p[0].value.toFixed(1)+' km';}}}},
    grid: {{left:48,right:12,bottom:40,top:16}},
    xAxis: {{type:'category',data:{lj},axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10,rotate:30}}}},
    yAxis: {{type:'value',name:'km',nameTextStyle:{{color:'rgba(255,255,255,0.5)',fontSize:10}},
      axisLabel:{{color:'rgba(255,255,255,0.5)',fontSize:10}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    series:[{{type:'bar',data:{vj},itemStyle:{{color:'#00d4ff',borderRadius:[4,4,0,0]}},
      markLine:{{silent:true,data:[{{type:'average',label:{{formatter:'avg {{c}} km',color:'#ffaa00',fontSize:10}},
        lineStyle:{{color:'#ffaa00',type:'dashed'}}}}]}}}}]
  }});
  window.addEventListener('resize', function(){{c.resize();}});
}})();
</script>"""


def render_metrics_table(activities: list[dict]) -> str:
    """활동별 메트릭 요약 테이블."""
    if not activities:
        return ""
    rows = ""
    for a in activities:
        fearp = f"{fmt_pace(a['fearp'])}/km" if a["fearp"] is not None else "—"
        re = f"{float(a['relative_effort']):.0f}" if a["relative_effort"] is not None else "—"
        dec = f"{float(a['decoupling']):.1f}%" if a["decoupling"] is not None else "—"
        pace = f"{fmt_pace(a['pace'])}/km" if a["pace"] is not None else "—"
        dist = f"{float(a['dist_km']):.1f}" if a["dist_km"] is not None else "—"
        rows += (
            f"<tr><td>{_html.escape(a['date'])}</td><td>{dist} km</td><td>{pace}</td>"
            f"<td>{fearp}</td><td>{re}</td><td>{dec}</td></tr>"
        )
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.6rem;'>최근 활동 메트릭</h2>"
        "<div style='overflow-x:auto;'><table><thead><tr>"
        "<th>날짜</th><th>거리</th><th>페이스</th><th>FEARP</th><th>Rel.Effort</th><th>Decoupling</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table></div></div>"
    )
