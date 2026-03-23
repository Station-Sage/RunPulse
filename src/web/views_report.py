"""분석 레포트 뷰 — Flask Blueprint.

/report?period=week|month|3month
  - 기간 선택 탭
  - 요약 카드 (활동 수/거리/시간/평균 UTRS)
  - 주별 거리 ECharts 바차트
  - 활동별 메트릭 테이블 (FEARP/GAP/Relative Effort/Decoupling)
"""
from __future__ import annotations

import html as _html
import json
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, render_template, request

from .helpers import db_path, fmt_duration, fmt_pace, no_data_card
from .views_report_sections import (
    _load_adti,
    _load_darp_latest,
    _load_fitness_data,
    _load_risk_overview,
    _load_tids_data,
    _load_trimp_weekly,
    render_ai_insight_placeholder,
    render_darp_card,
    render_endurance_trend,
    render_export_buttons,
    render_fitness_trend,
    render_risk_overview,
    render_tids_section,
    render_trimp_weekly_chart,
)

report_bp = Blueprint("report", __name__)

_PERIODS: dict[str, tuple[str, int]] = {
    "week":   ("이번 주 (7일)",    7),
    "month":  ("이번 달 (30일)",   30),
    "3month": ("최근 3개월 (90일)", 90),
}


# ── 데이터 조회 ──────────────────────────────────────────────────────────────

def _load_period_stats(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """기간 내 러닝 활동 집계."""
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_km), 0), COALESCE(SUM(duration_sec), 0)
           FROM v_canonical_activities
           WHERE activity_type = 'running' AND start_time BETWEEN ? AND ?""",
        (start, end + "T23:59:59"),
    ).fetchone()
    return {"count": int(row[0]), "total_km": float(row[1]), "total_sec": int(row[2])}


def _load_weekly_distance(conn: sqlite3.Connection, end_date: str, days: int) -> list[dict]:
    """주별 러닝 거리 집계 (ECharts용)."""
    weeks = max(days // 7, 4)
    rows = conn.execute(
        """SELECT strftime('%Y-%W', start_time) AS week,
                  COALESCE(SUM(distance_km), 0) AS total_km
           FROM v_canonical_activities
           WHERE activity_type = 'running'
             AND start_time >= date(?, ? || ' days')
           GROUP BY week ORDER BY week ASC""",
        (end_date, f"-{weeks * 7}"),
    ).fetchall()
    return [{"week": r[0], "km": round(float(r[1]), 1)} for r in rows]


def _load_metrics_avg(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """기간 내 UTRS/CIRS 평균값."""
    rows = conn.execute(
        """SELECT metric_name, AVG(metric_value)
           FROM computed_metrics
           WHERE date BETWEEN ? AND ? AND activity_id IS NULL
             AND metric_name IN ('UTRS', 'CIRS')
           GROUP BY metric_name""",
        (start, end),
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _load_activity_metrics(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """기간 내 최근 활동별 메트릭 요약 (최대 15개)."""
    acts = conn.execute(
        """SELECT id, start_time, distance_km, avg_pace_sec_km
           FROM v_canonical_activities
           WHERE activity_type = 'running' AND start_time BETWEEN ? AND ?
           ORDER BY start_time DESC LIMIT 15""",
        (start, end + "T23:59:59"),
    ).fetchall()

    result = []
    for act_id, start_time, dist, pace in acts:
        mrows = conn.execute(
            """SELECT metric_name, metric_value FROM computed_metrics
               WHERE activity_id = ?
                 AND metric_name IN ('FEARP', 'GAP', 'RelativeEffort', 'Decoupling')""",
            (act_id,),
        ).fetchall()
        m = {r[0]: r[1] for r in mrows}
        result.append({
            "date": str(start_time)[:10],
            "dist_km": dist,
            "pace": pace,
            "fearp": m.get("FEARP"),
            "gap": m.get("GAP"),
            "relative_effort": m.get("RelativeEffort"),
            "decoupling": m.get("Decoupling"),
        })
    return result


# ── 렌더링 헬퍼 ──────────────────────────────────────────────────────────────

def _render_period_tabs(current: str) -> str:
    """기간 선택 탭 HTML."""
    tabs = []
    for key, (label, _) in _PERIODS.items():
        active = "border-bottom:2px solid var(--cyan);color:var(--cyan);" if key == current else ""
        tabs.append(
            f"<a href='/report?period={key}' style='padding:0.5rem 1rem;"
            f"text-decoration:none;color:var(--secondary);font-size:0.9rem;{active}'>{label}</a>"
        )
    return (
        "<div style='display:flex;border-bottom:1px solid var(--card-border);"
        "margin-bottom:1rem;flex-wrap:wrap;'>" + "".join(tabs) + "</div>"
    )


def _render_summary_cards(stats: dict, metrics_avg: dict) -> str:
    """요약 지표 카드 4개 (2×2 grid)."""
    utrs_avg = metrics_avg.get("UTRS")
    cirs_avg = metrics_avg.get("CIRS")

    def _stat_card(title: str, value: str, color: str = "var(--fg)") -> str:
        return (
            f"<div class='card'>"
            f"<h2 style='font-size:0.8rem;color:var(--muted);margin-bottom:0.3rem;'>{title}</h2>"
            f"<p style='font-size:1.8rem;font-weight:700;margin:0;color:{color};'>{value}</p>"
            f"</div>"
        )

    utrs_str = f"{utrs_avg:.0f}" if utrs_avg is not None else "—"
    cirs_str = f"{cirs_avg:.0f}" if cirs_avg is not None else "—"
    km_per_act = (
        f"{stats['total_km'] / stats['count']:.1f} km/회"
        if stats["count"] > 0 else "—"
    )

    return (
        "<div class='cards-row'>"
        + _stat_card("활동 수", f"{stats['count']}회")
        + _stat_card("총 거리", f"{stats['total_km']:.1f} km", "var(--cyan)")
        + _stat_card("총 시간", fmt_duration(stats["total_sec"]))
        + _stat_card("평균 거리", km_per_act)
        + "</div>"
        "<div class='cards-row'>"
        + _stat_card("평균 UTRS", utrs_str, "var(--green)" if utrs_avg and utrs_avg >= 60 else "var(--fg)")
        + _stat_card("평균 CIRS", cirs_str, "var(--red)" if cirs_avg and cirs_avg >= 50 else "var(--fg)")
        + "</div>"
    )


def _render_weekly_chart(weekly_data: list[dict]) -> str:
    """ECharts 주별 거리 바차트."""
    if not weekly_data:
        return no_data_card("주별 거리 추세", "훈련 데이터 동기화 후 표시됩니다")

    labels = [d["week"] for d in weekly_data]
    values = [d["km"] for d in weekly_data]
    avg_km = sum(values) / len(values) if values else 0
    labels_json = json.dumps(labels)
    values_json = json.dumps(values)

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
  var chart = echarts.init(el, 'dark', {{backgroundColor: 'transparent'}});
  chart.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{ trigger: 'axis',
      formatter: function(p) {{ return p[0].axisValue + '<br>거리: ' + p[0].value.toFixed(1) + ' km'; }}
    }},
    grid: {{ left: 48, right: 12, bottom: 40, top: 16 }},
    xAxis: {{ type: 'category', data: {labels_json},
      axisLabel: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', name: 'km',
      nameTextStyle: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }},
      axisLabel: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }},
      splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.08)' }} }} }},
    series: [{{
      type: 'bar', data: {values_json},
      itemStyle: {{ color: '#00d4ff', borderRadius: [4,4,0,0] }},
      markLine: {{ silent: true, data: [{{
        type: 'average',
        label: {{ formatter: 'avg {{c}} km', color: '#ffaa00', fontSize: 10 }},
        lineStyle: {{ color: '#ffaa00', type: 'dashed' }}
      }}] }}
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>"""


def _render_metrics_table(activities: list[dict]) -> str:
    """활동별 메트릭 요약 테이블."""
    if not activities:
        return ""

    rows_html = ""
    for a in activities:
        fearp_str = f"{fmt_pace(a['fearp'])}/km" if a["fearp"] is not None else "—"
        gap_str = f"{fmt_pace(a['gap'])}/km" if a["gap"] is not None else "—"
        re_str = f"{float(a['relative_effort']):.0f}" if a["relative_effort"] is not None else "—"
        dec_str = f"{float(a['decoupling']):.1f}%" if a["decoupling"] is not None else "—"
        pace_str = f"{fmt_pace(a['pace'])}/km" if a["pace"] is not None else "—"
        dist_str = f"{float(a['dist_km']):.1f}" if a["dist_km"] is not None else "—"

        rows_html += (
            f"<tr>"
            f"<td>{_html.escape(a['date'])}</td>"
            f"<td>{dist_str} km</td>"
            f"<td>{pace_str}</td>"
            f"<td>{fearp_str}</td>"
            f"<td>{gap_str}</td>"
            f"<td>{re_str}</td>"
            f"<td>{dec_str}</td>"
            f"</tr>"
        )

    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.6rem;'>최근 활동 메트릭</h2>"
        "<div style='overflow-x:auto;'>"
        "<table><thead><tr>"
        "<th>날짜</th><th>거리</th><th>페이스</th>"
        "<th>FEARP</th><th>GAP</th><th>Rel.Effort</th><th>Decoupling</th>"
        "</tr></thead><tbody>"
        + rows_html
        + "</tbody></table></div></div>"
    )


# ── 라우트 ───────────────────────────────────────────────────────────────────

@report_bp.get("/report")
def report_view():
    """분석 레포트 페이지."""
    dpath = db_path()
    if not dpath.exists():
        return render_template(
            "generic_page.html", title="레포트", active_tab="report",
            body="<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>",
        )

    period = request.args.get("period", "week")
    if period not in _PERIODS:
        period = "week"
    period_label, days = _PERIODS[period]

    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=days)).isoformat()

    try:
        with sqlite3.connect(str(dpath)) as conn:
            stats = _load_period_stats(conn, start_date, end_date)
            weekly_data = _load_weekly_distance(conn, end_date, days)
            metrics_avg = _load_metrics_avg(conn, start_date, end_date)
            activity_metrics = _load_activity_metrics(conn, start_date, end_date)
            tids_data = _load_tids_data(conn, start_date, end_date)
            trimp_weekly = _load_trimp_weekly(conn, start_date, end_date)
            risk_data = _load_risk_overview(conn, start_date, end_date)
            adti_val = _load_adti(conn, end_date)
            darp_data = _load_darp_latest(conn, end_date)
            vdot, shape = _load_fitness_data(conn, end_date)
    except Exception as exc:
        return render_template(
            "generic_page.html", title="레포트", active_tab="report",
            body=f"<div class='card'><p>조회 오류: {_html.escape(str(exc))}</p></div>",
        )

    body = (
        _render_period_tabs(period)
        + _render_summary_cards(stats, metrics_avg)
        + _render_weekly_chart(weekly_data)
        + render_tids_section(tids_data)
        + render_trimp_weekly_chart(trimp_weekly)
        + "<div class='cards-row' style='align-items:start;'>"
        + render_risk_overview(risk_data)
        + render_endurance_trend(adti_val)
        + "</div>"
        + "<div class='cards-row' style='align-items:start;'>"
        + render_darp_card(darp_data)
        + render_fitness_trend(vdot, shape)
        + "</div>"
        + _render_metrics_table(activity_metrics)
        + render_ai_insight_placeholder()
        + render_export_buttons(period)
    )

    return render_template(
        "generic_page.html",
        title=f"레포트 — {period_label}",
        body=body,
        active_tab="report",
    )
