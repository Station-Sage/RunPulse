"""활동 심층 분석 뷰 — Flask Blueprint.

/activity/deep?id=<activity_id>
/activity/deep?date=YYYY-MM-DD
/activity/deep          → 최근 활동

7개 목적별 그룹 + 서비스 원시 탭 + 지도 + 스플릿.
"""
from __future__ import annotations

import html
import sqlite3

from flask import Blueprint, render_template, request

from src.analysis.activity_deep import deep_analyze
from .helpers import db_path

# 기존 loaders
from .views_activity_loaders import (
    _extract_gap,
    _fetch_adjacent,
    _fetch_source_rows,
    _load_activity_computed_metrics,
    _load_activity_metric_jsons,
    _load_day_computed_metrics,
    _load_day_metric_jsons,
    _load_hr_zone_times,
    _load_pmc_series,
    _load_running_tolerance,
    _load_service_metrics,
)
# 신규 loaders
from .views_activity_loaders_v2 import (
    load_darp_values,
    load_ef_decoupling_series,
    load_risk_series,
    load_tids_weekly_series,
)
# 공통 카드
from .views_activity_cards_common import (
    render_activity_nav,
    render_activity_summary,
    render_classification_badge,
    render_horizontal_scroll,
    render_splits,
)
from .views_activity_map import render_map_placeholder
# 소스 비교 + 서비스 탭
from .views_activity_source_cards import (
    _render_service_tabs,
    _render_source_comparison,
)
# 7개 그룹
from .views_activity_g1_status import render_group1_daily_status
from .views_activity_g2_performance import render_group2_performance
from .views_activity_g3_load import render_group3_load
from .views_activity_g4_risk import render_group4_risk
from .views_activity_g5_biomechanics import render_group5_biomechanics
from .views_activity_g6_distribution import render_group6_distribution
from .views_activity_g7_fitness import render_group7_fitness

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

    # 데이터 로딩
    source_rows: dict = {}
    resolved_id: int | None = None
    act_metrics: dict = {}
    day_metrics_data: dict = {}
    act_metric_jsons: dict = {}
    day_metric_jsons: dict = {}
    service_metrics: dict = {}
    pmc_series: dict = {}
    hr_zones: list = []
    ef_dec_series: dict = {}
    risk_series: dict = {}
    tids_weekly: dict = {}
    darp_data: dict = {}

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
                    act_date_tmp = str(cur[1])[:10]
                    prev_row, next_row = _fetch_adjacent(conn, cur[0], cur[1])
                    source_rows = _fetch_source_rows(conn, cur[0])
                    act_metrics = _load_activity_computed_metrics(conn, cur[0])
                    if "GAP" not in act_metrics:
                        _gap = _extract_gap(source_rows)
                        if _gap is not None:
                            act_metrics["GAP"] = _gap
                    service_metrics = _load_service_metrics(conn, cur[0])
                    day_metrics_data = _load_day_computed_metrics(conn, act_date_tmp)
                    act_metric_jsons = _load_activity_metric_jsons(conn, cur[0])
                    day_metric_jsons = _load_day_metric_jsons(conn, act_date_tmp)
                    pmc_series = _load_pmc_series(conn, act_date_tmp)
                    hr_zones = _load_hr_zone_times(source_rows)
                    # 신규 loaders
                    ef_dec_series = load_ef_decoupling_series(conn, act_date_tmp)
                    risk_series = load_risk_series(conn, act_date_tmp)
                    tids_weekly = load_tids_weekly_series(conn, act_date_tmp)
                    darp_data = load_darp_values(conn, act_date_tmp)
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    query_form = (
        "<div class='card'>"
        "<form method='get' action='/activity/deep' "
        "style='display:flex; gap:1rem; align-items:center; flex-wrap:wrap;'>"
        f"<label>날짜: <input type='date' name='date' value='{html.escape(date_str)}'></label>"
        f"<label>또는 활동 ID: <input type='number' name='id' value='{html.escape(activity_id_str)}' style='width:6rem;'></label>"
        "<button type='submit'>조회</button></form></div>"
    )

    if data is None:
        msg = f"activity id={activity_id_str}" if activity_id_str else f"날짜={date_str or '오늘'}"
        body = query_form + f"<div class='card'><p class='muted'>분석 가능한 활동이 없습니다 ({html.escape(msg)}).</p></div>"
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

    act = data.get("activity") or {}
    act_date = act.get("date") or ""
    garmin = data.get("garmin") or {}
    garmin_detail = data.get("garmin_daily_detail") or {}
    strava = data.get("strava") or {}
    intervals = data.get("intervals") or {}
    runalyze = data.get("runalyze") or {}
    fitness_ctx = data.get("fitness_context") or {}
    splits = (strava.get("pace_splits") or [])

    # EF/Decoupling 스파크라인 데이터
    ef_series = ef_dec_series.get("ef", {})
    dec_series = ef_dec_series.get("decoupling", {})

    # ── AI 배치 메트릭 해석 (2차 호출) ─────────────────────────────────
    _load_ai_metric_interpretations(conn, act_metrics)

    # ── 7그룹 구조로 렌더링 ─────────────────────────────────────────────
    body = (
        query_form
        + render_activity_nav(prev_row, next_row)
        + render_horizontal_scroll(act, act_metrics)
        + render_classification_badge(act)
        + _render_ai_activity_analysis(conn, resolved_id, act, act_metrics)
        + render_activity_summary(act)
        + _render_source_comparison(source_rows, resolved_id)
        # 그룹 1: 오늘의 상태
        + render_group1_daily_status(day_metrics_data, day_metric_jsons, garmin_detail)
        # 그룹 2: 퍼포먼스
        + render_group2_performance(act_metrics, act_metric_jsons, garmin, fitness_ctx, ef_series, dec_series, day_metrics_data)
        # 그룹 3: 부하/노력
        + render_group3_load(act_metrics, act_metric_jsons, service_metrics, garmin, strava)
        # 그룹 4: 과훈련 위험
        + render_group4_risk(risk_series)
        # 그룹 5: 폼/바이오메카닉스
        + render_group5_biomechanics(day_metric_jsons, garmin, act)
        # 그룹 6: 훈련 분포
        + render_group6_distribution(hr_zones, day_metrics_data, day_metric_jsons, tids_weekly)
        # 그룹 7: 피트니스 컨텍스트
        + render_group7_fitness(fitness_ctx, pmc_series, day_metrics_data, darp_data)
        # 하단: 서비스 원본 (접이식)
        + _render_service_tabs(garmin, strava, intervals, runalyze, garmin_detail, act_date)
        + render_map_placeholder(resolved_id)
        + render_splits(splits)
    )

    title = f"활동 심층 분석 — {act_date}"
    return render_template("generic_page.html", title=title, body=body, active_tab="activities")


def _load_ai_metric_interpretations(conn, act_metrics: dict) -> None:
    """활동 메트릭을 배치로 AI 해석 → 캐시에 저장."""
    from .views_activity_cards_common import clear_ai_metric_cache, set_ai_metric_cache
    clear_ai_metric_cache()
    try:
        from src.utils.config import load_config
        config = load_config()
        if config.get("ai", {}).get("provider", "rule") == "rule":
            return
        # 해석할 메트릭 수집
        items = {k: round(float(v), 2) for k, v in act_metrics.items()
                 if v is not None and k not in ("id", "date", "activity_id")}
        if not items:
            return
        # 배치 프롬프트
        metric_list = "\n".join(f"- {k}: {v}" for k, v in items.items())
        prompt = (
            "당신은 러닝 코치입니다. 아래 메트릭을 각각 한국어 1줄(15자 이내)로 해석하세요.\n"
            "JSON 형식으로 답변: {\"메트릭명\": \"해석\"}\n\n"
            f"{metric_list}"
        )
        from src.ai.ai_message import get_ai_message
        result = get_ai_message(prompt, "", config, cache_key=f"batch_metrics:{hash(metric_list)}")
        if not result:
            return
        # JSON 파싱
        import json
        # AI 응답에서 JSON 추출
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(result[start:end])
            if isinstance(parsed, dict):
                set_ai_metric_cache(parsed)
    except Exception:
        pass


def _render_ai_activity_analysis(conn, activity_id: int, act: dict, metrics: dict) -> str:
    """활동 AI 종합 분석 카드. API 없으면 빈 문자열."""
    try:
        from src.utils.config import load_config
        config = load_config()
        if config.get("ai", {}).get("provider", "rule") == "rule":
            return ""
        from src.ai.ai_message import get_card_ai_message
        msg = get_card_ai_message("activity_analysis", conn, "", config, activity_id=activity_id)
        if not msg:
            return ""
        return (
            "<div class='card' style='border-left:4px solid var(--cyan);margin-bottom:16px;'>"
            "<h3 style='margin:0 0 8px;font-size:0.95rem;'>"
            "🤖 AI 활동 분석 <span style='font-size:0.65rem;color:var(--cyan);'>AI</span></h3>"
            f"<div style='font-size:0.85rem;color:var(--secondary);line-height:1.7;'>{msg}</div>"
            "</div>"
        )
    except Exception:
        return ""
