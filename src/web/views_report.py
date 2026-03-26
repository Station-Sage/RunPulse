"""분석 레포트 뷰 — Flask Blueprint.

/report?period=today|week|month|quarter|year|1year|custom&start=...&end=...

8개 섹션: 기간요약(+델타) / 볼륨추세 / 훈련질추세 / 훈련분포 / 리스크추세 /
         폼/바이오 / 컨디션추세 / 피트니스&레이스 + 메트릭테이블 + AI인사이트.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, render_template, request

from .helpers import db_path, render_sub_nav
from .views_perf import load_activity_metrics_batch
from .views_report_charts import (
    render_form_trend,
    render_risk_trend_chart,
    render_summary_delta,
    render_tids_weekly_chart,
    render_training_quality_chart,
    render_wellness_trend_chart,
)
from .views_report_loaders import (
    load_form_trend_series,
    load_prev_period_stats,
    load_risk_trend_series,
    load_tids_weekly_series,
    load_training_quality_series,
    load_wellness_trend_series,
)
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
    "year":    ("올해",            -1),
    "1year":   ("최근 1년",        365),
    "custom":  ("기간 선택",       0),
}


# ── 데이터 조회 ──────────────────────────────────────────────────────────────

def _load_period_stats(conn: sqlite3.Connection, start: str, end: str) -> dict:
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_km), 0), COALESCE(SUM(duration_sec), 0)
           FROM v_canonical_activities
           WHERE activity_type = 'running' AND start_time BETWEEN ? AND ?""",
        (start, end + "T23:59:59"),
    ).fetchone()
    return {"count": int(row[0]), "total_km": float(row[1]), "total_sec": int(row[2])}


def _load_weekly_distance(conn: sqlite3.Connection, end_date: str, days: int) -> list[dict]:
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
    acts = conn.execute(
        """SELECT id, start_time, distance_km, avg_pace_sec_km
           FROM v_canonical_activities
           WHERE activity_type = 'running' AND start_time BETWEEN ? AND ?
           ORDER BY start_time DESC LIMIT 15""",
        (start, end + "T23:59:59"),
    ).fetchall()
    if not acts:
        return []
    act_ids = [a[0] for a in acts]
    metrics = load_activity_metrics_batch(
        conn, act_ids, ["FEARP", "RelativeEffort", "AerobicDecoupling"])
    result = []
    for act_id, start_time, dist, pace in acts:
        m = metrics.get(act_id, {})
        result.append({
            "date": str(start_time)[:10], "dist_km": dist, "pace": pace,
            "fearp": m.get("FEARP"), "relative_effort": m.get("RelativeEffort"),
            "decoupling": m.get("AerobicDecoupling"),
        })
    return result


# ── 렌더링 헬퍼 ──────────────────────────────────────────────────────────────

def _render_period_tabs(current: str, custom_start: str = "", custom_end: str = "") -> str:
    tabs = []
    for key, (label, _) in _PERIODS.items():
        if key == "custom":
            continue
        active = "border-bottom:2px solid var(--cyan);color:var(--cyan);" if key == current else ""
        tabs.append(
            f"<a href='/report?period={key}' style='padding:0.4rem 0.7rem;"
            f"text-decoration:none;color:var(--secondary);font-size:0.85rem;"
            f"white-space:nowrap;{active}'>{label}</a>"
        )
    custom_active = "border-bottom:2px solid var(--cyan);color:var(--cyan);" if current == "custom" else ""
    tabs.append(
        f"<a href='#' onclick=\"document.getElementById('customRange').style.display="
        f"document.getElementById('customRange').style.display==='none'?'flex':'none';"
        f"return false;\" style='padding:0.4rem 0.7rem;text-decoration:none;"
        f"color:var(--secondary);font-size:0.85rem;white-space:nowrap;{custom_active}'>기간 선택</a>"
    )
    today_str = date.today().isoformat()
    cs = custom_start or (date.today() - timedelta(days=30)).isoformat()
    ce = custom_end or today_str
    show = "flex" if current == "custom" else "none"
    custom_row = (
        f"<div id='customRange' style='display:{show};gap:0.5rem;align-items:center;"
        f"padding:0.5rem 0;flex-wrap:wrap;font-size:0.85rem;'>"
        f"<input type='date' id='csInput' value='{cs}' max='{today_str}' "
        f"style='background:var(--card-bg);color:var(--fg);border:1px solid var(--card-border);"
        f"border-radius:8px;padding:0.3rem 0.5rem;font-size:0.85rem;'/>"
        f"<span style='color:var(--muted);'>~</span>"
        f"<input type='date' id='ceInput' value='{ce}' max='{today_str}' "
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
    dpath = db_path()
    if not dpath.exists():
        return render_template(
            "generic_page.html", title="레포트", active_tab="report",
            body="<div class='card'><p>running.db 가 없습니다.</p></div>",
        )

    period = request.args.get("period", "week")
    if period == "3month":
        period = "quarter"
    if period not in _PERIODS:
        period = "week"
    period_label, days = _PERIODS[period]

    today = date.today()
    custom_start_str = ""
    custom_end_str = ""

    if period == "year":
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
            # 기존 로더
            stats = _load_period_stats(conn, start_date, end_date)
            weekly_data = _load_weekly_distance(conn, end_date, days)
            metrics_avg = _load_metrics_avg(conn, start_date, end_date)
            activity_metrics = _load_activity_metrics(conn, start_date, end_date)
            tids_data = _load_tids_data(conn, start_date, end_date)
            trimp_weekly = _load_trimp_weekly(conn, start_date, end_date)
            # 이전 기간 TRIMP (#6)
            _sd = date.fromisoformat(start_date)
            _span = (date.fromisoformat(end_date) - _sd).days or 1
            _prev_end = (_sd - timedelta(days=1)).isoformat()
            _prev_start = (_sd - timedelta(days=_span + 1)).isoformat()
            prev_trimp_weekly = _load_trimp_weekly(conn, _prev_start, _prev_end)
            risk_data = _load_risk_overview(conn, start_date, end_date)
            adti_val = _load_adti(conn, end_date)
            darp_data = _load_darp_latest(conn, end_date)
            vdot, shape = _load_fitness_data(conn, end_date)
            # DI (내구성 지수)
            _di_row = conn.execute(
                "SELECT metric_value FROM computed_metrics WHERE metric_name='DI' "
                "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
                (end_date,),
            ).fetchone()
            di_val = float(_di_row[0]) if _di_row and _di_row[0] is not None else None
            # v0.3 메트릭
            _teroi_row = conn.execute(
                "SELECT metric_value FROM computed_metrics WHERE metric_name='TEROI' "
                "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
                (end_date,),
            ).fetchone()
            teroi_val = float(_teroi_row[0]) if _teroi_row and _teroi_row[0] is not None else None
            _sapi_row = conn.execute(
                "SELECT metric_value FROM computed_metrics WHERE metric_name='SAPI' "
                "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
                (end_date,),
            ).fetchone()
            sapi_val = float(_sapi_row[0]) if _sapi_row and _sapi_row[0] is not None else None
            ai_insight_html = render_ai_insight(conn, start_date, end_date)
            # 신규 로더
            prev_stats = load_prev_period_stats(conn, start_date, end_date)
            quality = load_training_quality_series(conn, start_date, end_date)
            risk_series = load_risk_trend_series(conn, start_date, end_date)
            form_data = load_form_trend_series(conn, start_date, end_date)
            wellness = load_wellness_trend_series(conn, start_date, end_date)
            tids_weekly = load_tids_weekly_series(conn, start_date, end_date)
    except Exception as exc:
        return render_template(
            "generic_page.html", title="레포트", active_tab="report",
            body=f"<div class='card'><p>조회 오류: {_html.escape(str(exc))}</p></div>",
        )

    body = (
        render_sub_nav("report")
        + _render_period_tabs(period, custom_start_str, custom_end_str)
        # 섹션 1: 기간 요약 + 델타
        + render_summary_cards(stats, metrics_avg, teroi=teroi_val, sapi=sapi_val)
        + render_summary_delta(stats, prev_stats)
        # 섹션 2: 볼륨 추세
        + render_weekly_chart(weekly_data)
        + render_trimp_weekly_chart(trimp_weekly, prev_trimp_weekly)
        # 섹션 3: 훈련 질 추세 (신규)
        + render_training_quality_chart(quality)
        # 섹션 4: 훈련 분포
        + render_tids_section(tids_data)
        + render_tids_weekly_chart(tids_weekly)
        # 섹션 5: 리스크 추세 (신규 차트 + 기존 테이블 축소)
        + render_risk_trend_chart(risk_series)
        + "<div class='cards-row' style='align-items:start;'>"
        + render_risk_overview(risk_data)
        + render_endurance_trend(adti_val)
        + "</div>"
        # 섹션 6: 폼/바이오 (신규)
        + render_form_trend(form_data)
        # 섹션 7: 컨디션 추세 (신규)
        + render_wellness_trend_chart(wellness)
        # 섹션 8: 피트니스 & 레이스
        + "<div class='cards-row' style='align-items:start;'>"
        + render_darp_card(darp_data, vdot=vdot, di=di_val)
        + render_fitness_trend(vdot, shape)
        + "</div>"
        # 기존 유지
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
