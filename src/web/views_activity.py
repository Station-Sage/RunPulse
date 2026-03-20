"""활동 심층 분석 뷰 — Flask Blueprint.

/activity/deep?id=<activity_id>
/activity/deep?date=YYYY-MM-DD
/activity/deep          → 최근 활동
  - deep_analyze() 결과를 카드 형식으로 표시
  - Garmin daily detail (training readiness, HRV, 수면, body battery, SpO2)
  - 4소스 메트릭 카드 (Garmin, Strava, Intervals, Runalyze)
  - 피트니스 컨텍스트 (CTL/ATL/TSB)
  - 페이스 스플릿 테이블
"""
from __future__ import annotations

import html
import json
import sqlite3

from flask import Blueprint, request

from src.analysis.activity_deep import deep_analyze
from src.utils.pace import seconds_to_pace
from .helpers import (
    db_path,
    fmt_duration,
    fmt_min,
    html_page,
    make_table,
    metric_row,
    readiness_badge,
    safe_str,
)

activity_bp = Blueprint("activity", __name__)


# ── 카드 렌더링 헬퍼 ────────────────────────────────────────────────────

def _render_activity_summary(act: dict) -> str:
    """활동 기본 정보 카드."""
    pace = safe_str(act.get("avg_pace"))
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    return (
        "<div class='card'>"
        "<h2>활동 요약</h2>"
        + metric_row("날짜", act.get("date"))
        + metric_row("유형", act.get("type"))
        + metric_row("거리", dist_str)
        + metric_row("시간", fmt_duration(act.get("duration_sec")))
        + metric_row("평균 페이스", pace)
        + metric_row("평균 심박", act.get("avg_hr"), " bpm")
        + metric_row("최대 심박", act.get("max_hr"), " bpm")
        + metric_row("평균 케이던스", act.get("avg_cadence"), " spm")
        + metric_row("고도 상승", act.get("elevation_gain"), " m")
        + metric_row("칼로리", act.get("calories"), " kcal")
        + "</div>"
    )


def _render_garmin_daily_detail(detail: dict, act_date: str) -> str:
    """Garmin 일별 상세 지표 카드 (Phase 5 핵심)."""
    readiness = detail.get("training_readiness_score")
    badge = readiness_badge(readiness)
    deep_sec = detail.get("sleep_stage_deep_sec")
    rem_sec = detail.get("sleep_stage_rem_sec")
    hrv_avg = detail.get("overnight_hrv_avg")
    hrv_sdnn = detail.get("overnight_hrv_sdnn")
    hrv_low = detail.get("hrv_baseline_low")
    hrv_high = detail.get("hrv_baseline_high")
    baseline_str = (
        f"{safe_str(hrv_low)}–{safe_str(hrv_high)}"
        if (hrv_low is not None or hrv_high is not None)
        else None
    )
    bb_delta = detail.get("body_battery_delta")
    stress_dur = detail.get("stress_high_duration")
    resp_avg = detail.get("respiration_avg")
    spo2 = detail.get("spo2_avg")

    any_data = any(
        v is not None
        for v in [readiness, deep_sec, rem_sec, hrv_avg, hrv_sdnn,
                  bb_delta, stress_dur, resp_avg, spo2]
    )
    if not any_data:
        return (
            "<div class='card'>"
            "<h2>Garmin 일별 상세 지표</h2>"
            f"<p class='muted'>{html.escape(act_date)} 날짜의 Garmin 일별 상세 데이터가 없습니다.</p>"
            "</div>"
        )

    return (
        "<div class='card'>"
        "<h2>Garmin 일별 상세 지표</h2>"
        f"<p><strong>훈련 준비도:</strong> {badge}</p>"
        "<div class='cards-row'>"
        "<div class='card'><h2>수면</h2>"
        + metric_row("딥 슬립", fmt_min(deep_sec))
        + metric_row("REM 슬립", fmt_min(rem_sec))
        + metric_row("뒤척임 횟수", detail.get("sleep_restless_moments"))
        + "</div>"
        "<div class='card'><h2>야간 HRV</h2>"
        + metric_row("야간 평균 HRV", hrv_avg, " ms")
        + metric_row("HRV SDNN", hrv_sdnn, " ms")
        + metric_row("개인 기준선", baseline_str)
        + "</div>"
        "<div class='card'><h2>기타 지표</h2>"
        + metric_row("바디 배터리 변화", bb_delta)
        + metric_row("고스트레스 시간", fmt_min(stress_dur))
        + metric_row("호흡수 평균", resp_avg, " 회/분")
        + metric_row("SpO2 평균", spo2, "%")
        + "</div>"
        "</div>"
        "</div>"
    )


def _render_garmin_metrics(garmin: dict) -> str:
    """Garmin 소스 메트릭 카드."""
    return (
        "<div class='card'>"
        "<h2>Garmin</h2>"
        + metric_row("Training Effect (유산소)", garmin.get("training_effect_aerobic"))
        + metric_row("Training Effect (무산소)", garmin.get("training_effect_anaerobic"))
        + metric_row("Training Load", garmin.get("training_load"))
        + metric_row("VO2Max", garmin.get("vo2max"))
        + "</div>"
    )


def _render_strava_metrics(strava: dict) -> str:
    """Strava 소스 메트릭 카드."""
    best_efforts = strava.get("best_efforts")
    be_html = ""
    if isinstance(best_efforts, list) and best_efforts:
        be_rows = []
        for item in best_efforts[:6]:
            if isinstance(item, dict):
                name = item.get("name") or "—"
                et = item.get("elapsed_time")
                pace_str = seconds_to_pace(et) if et else "—"
                be_rows.append((name, f"{et}s ({pace_str})"))
        if be_rows:
            be_html = "<h3 style='margin:0.5rem 0 0.2rem;'>Best Efforts</h3>" + make_table(
                ["구간", "시간"], be_rows
            )
    return (
        "<div class='card'>"
        "<h2>Strava</h2>"
        + metric_row("Suffer Score", strava.get("suffer_score"))
        + be_html
        + "</div>"
    )


def _render_intervals_metrics(intervals: dict) -> str:
    """Intervals.icu 소스 메트릭 카드."""
    return (
        "<div class='card'>"
        "<h2>Intervals.icu</h2>"
        + metric_row("Training Load", intervals.get("icu_training_load"))
        + metric_row("HRSS", intervals.get("icu_hrss"))
        + metric_row("Intensity", intervals.get("icu_intensity"))
        + metric_row("Efficiency Factor", intervals.get("icu_efficiency_factor"))
        + metric_row("Decoupling", intervals.get("decoupling"), "%")
        + metric_row("TRIMP", intervals.get("trimp"))
        + metric_row("Average Stride", intervals.get("average_stride"), " m")
        + "</div>"
    )


def _render_runalyze_metrics(runalyze: dict) -> str:
    """Runalyze 소스 메트릭 카드."""
    preds = runalyze.get("race_predictions") or {}
    pred_lines = ""
    if isinstance(preds, dict) and preds:
        pred_lines = "<h3 style='margin:0.5rem 0 0.2rem;'>레이스 예측</h3>"
        for key in ["5k", "10k", "half", "full"]:
            if key in preds:
                pred_lines += metric_row(key, preds[key], " 초")
    return (
        "<div class='card'>"
        "<h2>Runalyze</h2>"
        + metric_row("Effective VO2Max", runalyze.get("effective_vo2max"))
        + metric_row("VDOT", runalyze.get("vdot"))
        + metric_row("TRIMP", runalyze.get("trimp"))
        + metric_row("Marathon Shape", runalyze.get("marathon_shape"), "%")
        + pred_lines
        + "</div>"
    )


def _render_fitness_context(ctx: dict) -> str:
    """피트니스 컨텍스트 카드 (CTL/ATL/TSB + VO2Max)."""
    return (
        "<div class='card'>"
        "<h2>피트니스 컨텍스트</h2>"
        + metric_row("CTL (만성 부하)", ctx.get("ctl"))
        + metric_row("ATL (급성 부하)", ctx.get("atl"))
        + metric_row("TSB (부하 균형)", ctx.get("tsb"))
        + metric_row("Garmin VO2Max", ctx.get("garmin_vo2max"))
        + metric_row("Runalyze eVO2Max", ctx.get("runalyze_evo2max"))
        + metric_row("Runalyze VDOT", ctx.get("runalyze_vdot"))
        + "</div>"
    )


def _render_splits(splits: list) -> str:
    """페이스 스플릿 테이블 카드."""
    if not splits:
        return ""
    rows = [
        (
            item.get("km"),
            item.get("pace") or "—",
            item.get("avg_hr") or "—",
        )
        for item in splits
    ]
    return (
        "<div class='card'>"
        "<h2>페이스 스플릿 (km)</h2>"
        + make_table(["km", "페이스", "평균 심박"], rows)
        + "</div>"
    )


def _render_efficiency(eff: dict) -> str:
    """효율 지표 카드."""
    if not eff:
        return ""
    return (
        "<div class='card'>"
        "<h2>효율 분석</h2>"
        + metric_row("Aerobic EF", eff.get("ef"))
        + metric_row("Cardiac Decoupling", eff.get("decoupling_pct"), "%")
        + metric_row("상태", eff.get("status"))
        + "</div>"
    )


# ── 라우트 ───────────────────────────────────────────────────────────────

@activity_bp.get("/activity/deep")
def activity_deep_view():
    """활동 심층 분석 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("활동 심층 분석", body)

    activity_id_str = request.args.get("id", "").strip()
    date_str = request.args.get("date", "").strip()

    activity_id: int | None = None
    if activity_id_str:
        try:
            activity_id = int(activity_id_str)
        except ValueError:
            body = f"<div class='card'><p>잘못된 activity id: {html.escape(activity_id_str)}</p></div>"
            return html_page("활동 심층 분석", body)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            data = deep_analyze(conn, activity_id=activity_id, date=date_str or None)
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return html_page("활동 심층 분석", body)

    # 쿼리 폼은 항상 표시 (no-data 경로 포함)
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
        return html_page("활동 심층 분석", body)

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
        + _render_activity_summary(act)
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
        + _render_splits(splits)
    )

    title = f"활동 심층 분석 — {act_date}"
    return html_page(title, body)
