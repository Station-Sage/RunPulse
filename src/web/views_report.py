"""분석 레포트 뷰 — Flask Blueprint.

/report?period=today|week|month|quarter|year|1year|custom&start=...&end=...
  - 기간 선택 탭 (7개 + custom 날짜 선택)
  - 요약 카드 (활동 수/거리/시간/평균 UTRS)
  - 주별 거리 ECharts 바차트
  - 활동별 메트릭 테이블 (FEARP/GAP/Relative Effort/Decoupling)
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, render_template, request

from .helpers import db_path, render_sub_nav
from .views_report_sections import (
    _load_adti,
    _load_darp_latest,
    _load_fitness_data,
    _load_risk_overview,
    _load_tids_data,
    _load_trimp_weekly,
    render_ai_insight,
    render_darp_card,
    render_endurance_trend,
    render_export_buttons,
    render_fitness_trend,
    render_metrics_table,
    render_risk_overview,
    render_summary_cards,
    render_tids_section,
    render_trimp_weekly_chart,
    render_weekly_chart,
)

report_bp = Blueprint("report", __name__)

_PERIODS: dict[str, tuple[str, int]] = {
    "today":   ("오늘",            1),
    "week":    ("7일",             7),
    "month":   ("30일",            30),
    "quarter": ("3개월",           90),
    "year":    ("올해",            -1),   # 1/1~오늘 (days는 동적 계산)
    "1year":   ("최근 1년",        365),
    "custom":  ("기간 선택",       0),    # start/end 쿼리 파라미터
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
                 AND metric_name IN ('FEARP', 'RelativeEffort', 'AerobicDecoupling')""",
            (act_id,),
        ).fetchall()
        m = {r[0]: r[1] for r in mrows}
        result.append({
            "date": str(start_time)[:10],
            "dist_km": dist,
            "pace": pace,
            "fearp": m.get("FEARP"),
            "relative_effort": m.get("RelativeEffort"),
            "decoupling": m.get("AerobicDecoupling"),
        })
    return result


# ── 렌더링 헬퍼 ──────────────────────────────────────────────────────────────


def _render_period_tabs(current: str, custom_start: str = "", custom_end: str = "") -> str:
    """기간 선택 탭 HTML (7개 + custom 날짜 입력)."""
    tabs = []
    for key, (label, _) in _PERIODS.items():
        if key == "custom":
            continue  # custom은 별도 렌더링
        active = "border-bottom:2px solid var(--cyan);color:var(--cyan);" if key == current else ""
        tabs.append(
            f"<a href='/report?period={key}' style='padding:0.4rem 0.7rem;"
            f"text-decoration:none;color:var(--secondary);font-size:0.85rem;"
            f"white-space:nowrap;{active}'>{label}</a>"
        )
    # custom 탭
    custom_active = "border-bottom:2px solid var(--cyan);color:var(--cyan);" if current == "custom" else ""
    tabs.append(
        f"<a href='#' onclick=\"document.getElementById('customRange').style.display="
        f"document.getElementById('customRange').style.display==='none'?'flex':'none';"
        f"return false;\" style='padding:0.4rem 0.7rem;text-decoration:none;"
        f"color:var(--secondary);font-size:0.85rem;white-space:nowrap;{custom_active}'>기간 선택</a>"
    )
    today = date.today().isoformat()
    cs = custom_start or (date.today() - timedelta(days=30)).isoformat()
    ce = custom_end or today
    show = "flex" if current == "custom" else "none"
    custom_row = (
        f"<div id='customRange' style='display:{show};gap:0.5rem;align-items:center;"
        f"padding:0.5rem 0;flex-wrap:wrap;font-size:0.85rem;'>"
        f"<input type='date' id='csInput' value='{cs}' max='{today}' "
        f"style='background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem 0.5rem;font-size:0.85rem;'/>"
        f"<span style='color:var(--muted);'>~</span>"
        f"<input type='date' id='ceInput' value='{ce}' max='{today}' "
        f"style='background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem 0.5rem;font-size:0.85rem;'/>"
        f"<a onclick=\"location.href='/report?period=custom&start='+document.getElementById('csInput').value"
        f"+'&end='+document.getElementById('ceInput').value\" "
        f"style='cursor:pointer;background:var(--cyan);color:#000;padding:0.3rem 0.8rem;"
        f"border-radius:8px;font-size:0.85rem;font-weight:600;text-decoration:none;'>적용</a>"
        f"</div>"
    )
    return (
        "<div style='display:flex;border-bottom:1px solid var(--card-border);"
        "margin-bottom:0.5rem;overflow-x:auto;-webkit-overflow-scrolling:touch;'>"
        + "".join(tabs) + "</div>" + custom_row
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
    if period == "3month":
        period = "quarter"  # 하위 호환
    if period not in _PERIODS:
        period = "week"
    period_label, days = _PERIODS[period]

    today = date.today()
    custom_start_str = ""
    custom_end_str = ""

    if period == "year":
        # 올해 1/1 ~ 오늘
        start_date = date(today.year, 1, 1).isoformat()
        end_date = today.isoformat()
        days = (today - date(today.year, 1, 1)).days or 1
    elif period == "custom":
        custom_start_str = request.args.get("start", "")
        custom_end_str = request.args.get("end", "")
        try:
            sd = date.fromisoformat(custom_start_str)
            ed = date.fromisoformat(custom_end_str)
            if sd > ed:
                sd, ed = ed, sd
            if ed > today:
                ed = today
            start_date = sd.isoformat()
            end_date = ed.isoformat()
            days = (ed - sd).days or 1
            period_label = f"{start_date} ~ {end_date}"
        except (ValueError, TypeError):
            period = "week"
            period_label, days = _PERIODS[period]
            start_date = (today - timedelta(days=days)).isoformat()
            end_date = today.isoformat()
    else:
        end_date = today.isoformat()
        start_date = (today - timedelta(days=days)).isoformat()

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
            ai_insight_html = render_ai_insight(conn, start_date, end_date)
    except Exception as exc:
        return render_template(
            "generic_page.html", title="레포트", active_tab="report",
            body=f"<div class='card'><p>조회 오류: {_html.escape(str(exc))}</p></div>",
        )

    body = (
        render_sub_nav("report")
        + _render_period_tabs(period, custom_start_str, custom_end_str)
        + render_summary_cards(stats, metrics_avg)
        + render_weekly_chart(weekly_data)
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
        + render_metrics_table(activity_metrics)
        + ai_insight_html
        + render_export_buttons(period)
    )

    return render_template(
        "generic_page.html",
        title=f"레포트 — {period_label}",
        body=body,
        active_tab="report",
    )
