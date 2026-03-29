"""레포트 추가 섹션 — AI 인사이트 + 요약 카드 + 테이블 + Export.

데이터 로더: views_report_sections_data.py
메트릭 카드: views_report_sections_cards.py
이 파일: AI 인사이트, 요약, 거리 차트, 메트릭 테이블, Export 버튼 + re-export
"""
from __future__ import annotations

import html as _html
import json
import sqlite3

from .helpers import METRIC_DESCRIPTIONS, fmt_duration, fmt_pace, no_data_card, tooltip

# ── re-export (views_report.py 호환) ──────────────────────────────────────────
from .views_report_sections_data import (  # noqa: F401
    _load_adti,
    _load_darp_latest,
    _load_fitness_data,
    _load_risk_overview,
    _load_tids_data,
    _load_trimp_weekly,
)
from .views_report_sections_cards import (  # noqa: F401
    render_darp_card,
    render_endurance_trend,
    render_fitness_trend,
    render_risk_overview,
    render_tids_section,
    render_trimp_weekly_chart,
)


# ── AI 인사이트 ───────────────────────────────────────────────────────────────

def render_ai_insight(conn: sqlite3.Connection, start: str, end: str,
                      config: dict | None = None,
                      ai_override: str | None = None) -> str:
    """AI 인사이트 카드 — ai_override 우선, 규칙 기반 fallback."""
    ai_result = ai_override
    if not ai_result and config and config.get("ai", {}).get("provider", "rule") != "rule":
        try:
            from src.ai.ai_message import get_card_ai_message
            ai_result = get_card_ai_message(
                "report_insight", conn, "", config,
                start_date=start, end_date=end, period=f"{start} ~ {end}",
            )
        except Exception:
            pass
    if ai_result:
        return (
            "<div class='card'>"
            "<h2 style='font-size:1rem;margin-bottom:0.6rem;color:var(--cyan);'>"
            "AI 코치 인사이트 <span style='font-size:0.65rem;color:var(--cyan);'>AI</span></h2>"
            f"<div style='font-size:0.85rem;color:var(--secondary);line-height:1.7;'>{ai_result}</div>"
            "<p class='muted' style='font-size:0.74rem;margin-top:0.5rem;'>"
            "<a href='/ai-coach' style='color:var(--cyan);'>AI 코치</a>에서 전체 분석 보기</p>"
            "</div>"
        )
    return _render_ai_insight_rule(conn, start, end)


def _render_ai_insight_rule(conn: sqlite3.Connection, start: str, end: str) -> str:
    """규칙 기반 AI 인사이트 (fallback)."""
    insights: list[str] = []
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
    cirs_rows = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='CIRS' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if cirs_rows and float(cirs_rows[0][0]) > 50:
        insights.append(f"부상 위험(CIRS) <strong>{int(cirs_rows[0][0])}/100</strong> — 부하 조절 필요")
    mono_rows = conn.execute(
        """SELECT metric_value, metric_json FROM computed_metrics
           WHERE metric_name='Monotony' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if mono_rows and mono_rows[0][0] is not None and float(mono_rows[0][0]) > 1.5:
        insights.append(f"훈련 단조로움 <strong>{float(mono_rows[0][0]):.1f}</strong> — 강도/유형 다양화 권장")
    tids_rows = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name='TIDS' AND activity_id IS NULL
             AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchall()
    if tids_rows and tids_rows[0][0]:
        try:
            td = json.loads(tids_rows[0][0])
            z1_pct = td.get("zone1_pct") or td.get("z1_pct", 0)
            z5_pct = td.get("zone5_pct") or td.get("z5_pct", 0)
            z3_pct = td.get("zone3_pct") or td.get("z3_pct", 0)
            if z1_pct > 60 and z5_pct > 15:
                insights.append("강도 분포: <strong>폴라리제드</strong> 패턴 (효율적)")
            elif z3_pct > 40:
                insights.append("강도 분포: <strong>중강도 집중</strong> — 고/저 강도 분리 권장")
        except Exception:
            pass
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


# ── 요약/차트/테이블/Export ────────────────────────────────────────────────────

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


def render_summary_cards(stats: dict, metrics_avg: dict,
                         teroi: float | None = None, sapi: float | None = None) -> str:
    """요약 지표 카드."""
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
        + _card(tooltip("평균 UTRS", METRIC_DESCRIPTIONS["UTRS"]), utrs_str, "var(--green)" if utrs_avg and utrs_avg >= 60 else "var(--fg)")
        + _card(tooltip("평균 CIRS", METRIC_DESCRIPTIONS["CIRS"]), cirs_str, "var(--red)" if cirs_avg and cirs_avg >= 50 else "var(--fg)")
        + (_card(tooltip("TEROI", METRIC_DESCRIPTIONS.get("TEROI", "")),
                 f"{teroi:+.1f}", "var(--green)" if teroi and teroi > 0 else "var(--red)")
           if teroi is not None else "")
        + (_card(tooltip("SAPI", METRIC_DESCRIPTIONS.get("SAPI", "")),
                 f"{sapi:.0f}%", "var(--cyan)" if sapi and sapi >= 95 else "var(--orange)")
           if sapi is not None else "")
        + "</div>"
    )


def render_weekly_chart(weekly_data: list[dict]) -> str:
    """ECharts 주별 거리 바차트."""
    if not weekly_data:
        return no_data_card("주별 거리 추세", "데이터 수집 중입니다")

    def _week_label(w: str) -> str:
        try:
            from datetime import datetime, timedelta
            year, wk = w.split("-")
            jan1 = datetime(int(year), 1, 1)
            start = jan1 + timedelta(weeks=int(wk), days=-jan1.weekday())
            return f"{start.month}/{start.day}"
        except Exception:
            return w

    labels = [_week_label(d["week"]) for d in weekly_data]
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


def _activity_effect(a: dict) -> str:
    """활동의 효과/영향."""
    rp_effect = a.get("rp_effect", "")
    if rp_effect:
        return rp_effect
    parts = []
    re = a.get("relative_effort")
    dec = a.get("decoupling")
    if re is not None:
        if re >= 150:
            parts.append("고강도 자극")
        elif re >= 80:
            parts.append("적정 부하")
        else:
            parts.append("저강도 회복")
    if dec is not None:
        if dec <= 5:
            parts.append("유산소 기반 양호")
        elif dec <= 10:
            parts.append("지구력 보통")
        else:
            parts.append("지구력 개선 필요")
    return " · ".join(parts) if parts else ""


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
        effect = _activity_effect(a)
        effect_td = f"<td style='font-size:0.75rem;color:var(--muted);'>{effect}</td>" if effect else "<td></td>"
        rows += (
            f"<tr><td>{_html.escape(a['date'])}</td><td>{dist} km</td><td>{pace}</td>"
            f"<td>{fearp}</td><td>{re}</td><td>{dec}</td>{effect_td}</tr>"
        )
    return (
        "<div class='card'><h2 style='font-size:1rem;margin-bottom:0.6rem;'>최근 활동 메트릭</h2>"
        "<div style='overflow-x:auto;'><table><thead><tr>"
        "<th>날짜</th><th>거리</th><th>페이스</th><th>FEARP</th><th>RE</th><th>Dec%</th><th>효과</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table></div></div>"
    )
