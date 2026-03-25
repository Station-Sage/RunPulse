"""활동 심층 분석 뷰 — Flask Blueprint.

/activity/deep?id=<activity_id>
/activity/deep?date=YYYY-MM-DD
/activity/deep          → 최근 활동
"""
from __future__ import annotations

import html
import sqlite3

from flask import Blueprint, render_template, request

from src.analysis.activity_deep import deep_analyze
from .helpers import db_path

from .views_activity_loaders import (
    _extract_gap,
    _fetch_adjacent,
    _fetch_source_rows,
    _load_activity_computed_metrics,
    _load_activity_metric_jsons,
    _load_day_computed_metrics,
    _load_day_metric_jsons,
    _load_pmc_series,
    _load_service_metrics,
)
from .views_activity_cards import (
    _render_activity_classification_badge,
    _render_activity_nav,
    _render_activity_summary,
    _render_daily_scores_card,
    _render_decoupling_detail_card,
    _render_di_card,
    _render_efficiency,
    _render_fearp_breakdown_card,
    _render_fitness_context,
    _render_garmin_daily_detail,
    _render_garmin_metrics,
    _render_horizontal_scroll,
    _render_intervals_metrics,
    _render_map_placeholder,
    _render_pmc_sparkline_card,
    _render_runalyze_metrics,
    _render_secondary_metrics_card,
    _render_source_comparison,
    _render_splits,
    _render_strava_metrics,
)

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/activity/deep")
def activity_deep_view():
    """활동 심층 분석 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    activity_id_str = request.args.get("id", "").strip()
    date_str = request.args.get("date", "").strip()

    activity_id: int | None = None
    if activity_id_str:
        try:
            activity_id = int(activity_id_str)
        except ValueError:
            body = f"<div class='card'><p>잘못된 activity id: {html.escape(activity_id_str)}</p></div>"
            return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    source_rows: dict = {}
    resolved_id: int | None = None
    act_metrics: dict = {}
    day_metrics_data: dict = {}
    act_metric_jsons: dict = {}
    day_metric_jsons: dict = {}
    service_metrics: dict = {}
    pmc_series: dict = {}
    try:
        with sqlite3.connect(str(dpath)) as conn:
            data = deep_analyze(conn, activity_id=activity_id, date=date_str or None)
            prev_row, next_row = None, None
            if data:
                if activity_id is not None:
                    cur = conn.execute(
                        "SELECT id, start_time FROM activity_summaries WHERE id = ?",
                        (activity_id,),
                    ).fetchone()
                else:
                    act_date = (data.get("activity") or {}).get("date") or ""
                    cur = conn.execute(
                        """SELECT id, start_time FROM activity_summaries
                           WHERE start_time >= ? AND start_time < ?
                           ORDER BY start_time DESC LIMIT 1""",
                        (act_date, act_date + "T99"),
                    ).fetchone() if act_date else None
                if cur:
                    resolved_id = cur[0]
                    prev_row, next_row = _fetch_adjacent(conn, cur[0], cur[1])
                    source_rows = _fetch_source_rows(conn, cur[0])
                    act_metrics = _load_activity_computed_metrics(conn, cur[0])
                    # GAP은 서비스 1차 메트릭 — activity_summaries에서 추출해 주입
                    if "GAP" not in act_metrics:
                        _gap = _extract_gap(source_rows)
                        if _gap is not None:
                            act_metrics["GAP"] = _gap
                    service_metrics = _load_service_metrics(conn, cur[0])
                    act_date_tmp = str(cur[1])[:10]
                    day_metrics_data = _load_day_computed_metrics(conn, act_date_tmp)
                    act_metric_jsons = _load_activity_metric_jsons(conn, cur[0])
                    day_metric_jsons = _load_day_metric_jsons(conn, act_date_tmp)
                    pmc_series = _load_pmc_series(conn, act_date_tmp)
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    query_form = (
        "<div class='card'>"
        "<form method='get' action='/activity/deep' "
        "style='display:flex; gap:1rem; align-items:center; flex-wrap:wrap;'>"
        "<label>날짜: <input type='date' name='date' "
        f"value='{html.escape(date_str)}'></label>"
        "<label>또는 활동 ID: <input type='number' name='id' "
        f"value='{html.escape(activity_id_str)}' style='width:6rem;'></label>"
        "<button type='submit'>조회</button>"
        "</form>"
        "</div>"
    )

    if data is None:
        msg = f"activity id={activity_id_str}" if activity_id_str else f"날짜={date_str or '오늘'}"
        body = (
            query_form
            + "<div class='card'>"
            f"<p class='muted'>분석 가능한 활동이 없습니다 ({html.escape(msg)}).</p>"
            "</div>"
        )
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    act = data.get("activity") or {}
    act_date = act.get("date") or ""
    garmin = data.get("garmin") or {}
    garmin_detail = data.get("garmin_daily_detail") or {}
    strava = data.get("strava") or {}
    intervals = data.get("intervals") or {}
    runalyze = data.get("runalyze") or {}
    fitness_ctx = data.get("fitness_context") or {}
    calculated = data.get("calculated") or {}
    efficiency = calculated.get("efficiency") or {}
    splits = strava.get("pace_splits") or []

    body = (
        query_form
        + _render_activity_nav(prev_row, next_row)
        + _render_horizontal_scroll(act, act_metrics)
        + _render_activity_classification_badge(act)
        + _render_activity_summary(act)
        + _render_source_comparison(source_rows, resolved_id)
        + _render_garmin_daily_detail(garmin_detail, act_date)
        + "<div class='cards-row'>"
        + _render_garmin_metrics(garmin)
        + _render_strava_metrics(strava)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_intervals_metrics(intervals)
        + _render_runalyze_metrics(runalyze)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_fitness_context(fitness_ctx)
        + _render_efficiency(efficiency)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_secondary_metrics_card(act_metrics, day_metrics_data, service_metrics=service_metrics, day_metric_jsons=day_metric_jsons)
        + _render_daily_scores_card(day_metrics_data)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_fearp_breakdown_card(act_metric_jsons)
        + _render_decoupling_detail_card(act_metrics, act_metric_jsons)
        + "</div>"
        + _render_pmc_sparkline_card(pmc_series)
        + "<div class='cards-row'>"
        + _render_di_card(day_metrics_data)
        + _render_map_placeholder()
        + "</div>"
        + _render_splits(splits)
    )

    title = f"활동 심층 분석 — {act_date}"
    return render_template("generic_page.html", title=title, body=body, active_tab="activities")
