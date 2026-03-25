"""회복/웰니스 상세 뷰 — Flask Blueprint.

/wellness?date=YYYY-MM-DD
  - get_recovery_status() 결과를 카드 형식으로 표시
  - Garmin daily detail metrics (training readiness, HRV, 수면, body battery, SpO2 등)
  - 14일 회복 추세 테이블
"""
from __future__ import annotations

import html
import json
import sqlite3
from datetime import date

from flask import Blueprint, request

from src.analysis.recovery import get_recovery_status, recovery_trend
from .helpers import (
    db_path,
    fmt_min,
    html_page,
    make_table,
    metric_row,
    readiness_badge,
    render_sub_nav,
    safe_str,
    score_badge,
)

wellness_bp = Blueprint("wellness", __name__)


# ── 내부 렌더링 헬퍼 ────────────────────────────────────────────────────

def _render_readiness_card(detail: dict) -> str:
    """훈련 준비도 카드."""
    score = detail.get("training_readiness_score")
    badge = readiness_badge(score)
    return (
        "<div class='card'>"
        "<h2>훈련 준비도 (Garmin)</h2>"
        f"<p style='font-size:1.6rem; margin:0.4rem 0;'>{badge}</p>"
        "<p class='muted' style='margin:0;'>Garmin Training Readiness Score 0–100</p>"
        "</div>"
    )


def _render_recovery_card(raw: dict, grade: str | None, score) -> str:
    """RunPulse 회복 점수 + 원시 지표 카드."""
    return (
        "<div class='card'>"
        "<h2>회복 점수 (RunPulse)</h2>"
        f"<p style='font-size:1.3rem; margin:0.4rem 0;'>{score_badge(grade, score)}</p>"
        "<p class='muted' style='margin:0 0 0.8rem;'>"
        "가중 평균: Body Battery 30% · 수면 25% · HRV 25% · 스트레스 15% · 안정심박 5%</p>"
        + metric_row("바디 배터리", raw.get("body_battery"))
        + metric_row("수면 점수", raw.get("sleep_score"))
        + metric_row("HRV", raw.get("hrv_value"), " ms")
        + metric_row("스트레스 평균", raw.get("stress_avg"))
        + metric_row("안정시 심박", raw.get("resting_hr"), " bpm")
        + "</div>"
    )


def _render_sleep_card(raw: dict, detail: dict) -> str:
    """수면 상세 카드."""
    deep_sec = detail.get("sleep_stage_deep_sec")
    rem_sec = detail.get("sleep_stage_rem_sec")
    restless = detail.get("sleep_restless_moments")
    sleep_score = raw.get("sleep_score")
    return (
        "<div class='card'>"
        "<h2>수면 상세</h2>"
        + metric_row("수면 점수", sleep_score)
        + metric_row("딥 슬립", fmt_min(deep_sec))
        + metric_row("REM 슬립", fmt_min(rem_sec))
        + metric_row("뒤척임 횟수", restless)
        + "</div>"
    )


def _render_hrv_card(raw: dict, detail: dict) -> str:
    """야간 HRV 카드."""
    hrv_raw = raw.get("hrv_value")
    hrv_avg = detail.get("overnight_hrv_avg")
    hrv_sdnn = detail.get("overnight_hrv_sdnn")
    hrv_low = detail.get("hrv_baseline_low")
    hrv_high = detail.get("hrv_baseline_high")
    baseline = (
        f"{safe_str(hrv_low)}–{safe_str(hrv_high)}"
        if (hrv_low is not None or hrv_high is not None)
        else None
    )
    return (
        "<div class='card'>"
        "<h2>야간 HRV</h2>"
        + metric_row("일별 HRV (daily_wellness)", hrv_raw, " ms")
        + metric_row("야간 평균 HRV", hrv_avg, " ms")
        + metric_row("HRV SDNN", hrv_sdnn, " ms")
        + metric_row("개인 기준선", baseline)
        + "</div>"
    )


def _render_other_card(detail: dict) -> str:
    """기타 생체 지표 카드."""
    bb_delta = detail.get("body_battery_delta")
    stress_dur = detail.get("stress_high_duration")
    resp_avg = detail.get("respiration_avg")
    spo2 = detail.get("spo2_avg")
    return (
        "<div class='card'>"
        "<h2>기타 생체 지표</h2>"
        + metric_row("바디 배터리 변화", bb_delta)
        + metric_row("고스트레스 시간", fmt_min(stress_dur))
        + metric_row("호흡수 평균", resp_avg, " 회/분")
        + metric_row("SpO2 평균", spo2, "%")
        + "</div>"
    )


def _load_7day_wellness(conn, date_str: str) -> list[dict]:
    """최근 7일 웰니스 데이터 로드 (ECharts용)."""
    rows = conn.execute(
        "SELECT date, sleep_score, hrv_value, body_battery, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date <= ? "
        "ORDER BY date DESC LIMIT 7",
        (date_str,),
    ).fetchall()
    result = []
    for r in reversed(rows):
        result.append({
            "date": r[0], "sleep": r[1], "hrv": r[2],
            "bb": r[3], "stress": r[4], "rhr": r[5],
        })
    return result


def _render_7day_chart(data: list[dict]) -> str:
    """7일 웰니스 트렌드 ECharts 차트."""
    if not data:
        return ""
    import json as _json
    dates = [d["date"][-5:] for d in data]  # MM-DD
    sleep = [d.get("sleep") for d in data]
    hrv = [d.get("hrv") for d in data]
    bb = [d.get("bb") for d in data]
    stress = [d.get("stress") for d in data]
    rhr = [d.get("rhr") for d in data]

    option = {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["수면", "HRV", "바디배터리", "스트레스", "안정심박"],
                   "textStyle": {"color": "rgba(255,255,255,0.7)", "fontSize": 11},
                   "top": 0},
        "grid": {"top": 40, "bottom": 25, "left": 40, "right": 10},
        "xAxis": {"type": "category", "data": dates,
                  "axisLabel": {"color": "rgba(255,255,255,0.6)", "fontSize": 11}},
        "yAxis": {"type": "value",
                  "axisLabel": {"color": "rgba(255,255,255,0.6)", "fontSize": 11},
                  "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.08)"}}},
        "series": [
            {"name": "수면", "type": "line", "data": sleep, "color": "#00d4ff", "smooth": True},
            {"name": "HRV", "type": "line", "data": hrv, "color": "#00ff88", "smooth": True},
            {"name": "바디배터리", "type": "line", "data": bb, "color": "#ffaa00", "smooth": True},
            {"name": "스트레스", "type": "line", "data": stress, "color": "#ff4444", "smooth": True},
            {"name": "안정심박", "type": "line", "data": rhr, "color": "#cc88ff", "smooth": True},
        ],
    }
    opt_json = _json.dumps(option, ensure_ascii=False)
    return (
        "<div class='card'>"
        "<h2>7일 웰니스 트렌드</h2>"
        "<div id='wellness7d' style='width:100%;height:280px;'></div>"
        "<script>"
        f"(function(){{var c=echarts.init(document.getElementById('wellness7d'),null,"
        f"{{renderer:'canvas'}});c.setOption({opt_json});"
        f"window.addEventListener('resize',function(){{c.resize();}});}})();"
        "</script></div>"
    )


def _render_recovery_recommendation(status: dict) -> str:
    """회복 권장 사항 카드."""
    if not status.get("available"):
        return ""
    raw = status.get("raw") or {}
    grade = status.get("grade")
    tips = []
    bb = raw.get("body_battery")
    sleep = raw.get("sleep_score")
    stress = raw.get("stress_avg")
    hrv = raw.get("hrv_value")

    if bb is not None and bb < 30:
        tips.append("바디배터리가 매우 낮습니다. 고강도 훈련을 피하고 충분한 휴식을 취하세요.")
    elif bb is not None and bb < 60:
        tips.append("바디배터리가 보통입니다. 가벼운 조깅이나 회복 러닝을 권장합니다.")
    if sleep is not None and sleep < 40:
        tips.append("수면 품질이 낮습니다. 취침 시간을 규칙적으로 유지하세요.")
    if stress is not None and stress > 60:
        tips.append("스트레스 수준이 높습니다. 호흡 운동이나 스트레칭을 시도하세요.")
    if hrv is not None and hrv < 30:
        tips.append("HRV가 낮습니다. 자율신경 회복이 필요하므로 오버트레이닝에 주의하세요.")
    if grade == "good" or (not tips and grade):
        tips.append("전반적인 회복 상태가 양호합니다. 계획대로 훈련을 진행해도 좋습니다.")

    if not tips:
        return ""
    items_html = "".join(
        f"<li style='margin-bottom:6px;font-size:0.88rem;color:rgba(255,255,255,0.85);'>{t}</li>"
        for t in tips
    )
    return (
        "<div class='card' style='border-left:4px solid #00d4ff;'>"
        "<h2>회복 권장</h2>"
        f"<ul style='margin:0;padding-left:1.2rem;'>{items_html}</ul>"
        "</div>"
    )


def _render_trend_card(trend_data: dict) -> str:
    """14일 회복 추세 카드."""
    scores = trend_data.get("scores") or []
    trend = trend_data.get("trend") or "unknown"
    avg = trend_data.get("avg")
    trend_label = {
        "improving": "개선 중",
        "declining": "하락 중",
        "stable": "안정",
        "unknown": "데이터 부족",
    }.get(trend, trend)

    rows = [
        (s["date"], safe_str(s.get("recovery_score")), s.get("grade") or "—")
        for s in scores
    ]
    table_html = make_table(["날짜", "회복 점수", "등급"], rows)

    return (
        "<div class='card'>"
        "<h2>14일 회복 추세</h2>"
        f"<p>추세: <strong>{html.escape(trend_label)}</strong> &nbsp;|&nbsp; "
        f"평균: <strong>{safe_str(avg)}</strong></p>"
        + table_html
        + "</div>"
    )


def _render_activity_card(steps, weight_kg) -> str:
    """걸음 수 / 체중 카드 (intervals 또는 Garmin 소스)."""
    if steps is None and weight_kg is None:
        return ""
    return (
        "<div class='card'>"
        "<h2>일별 활동 지표</h2>"
        + metric_row("걸음 수", steps, " 걸음")
        + metric_row("체중", weight_kg, " kg")
        + "</div>"
    )


def _no_data(date_str: str) -> str:
    return (
        "<div class='card'>"
        f"<p class='muted'>{html.escape(date_str)} 날짜의 Garmin 웰니스 데이터가 없습니다.</p>"
        "<p>Garmin 데이터를 동기화한 뒤 다시 확인하세요.</p>"
        "<pre>python src/sync.py --source garmin --days 7</pre>"
        "</div>"
    )


def _fetch_steps_weight(conn, date_str: str) -> tuple:
    """intervals daily_wellness에서 걸음 수/체중 조회."""
    try:
        row = conn.execute(
            "SELECT steps, weight_kg FROM daily_wellness WHERE date = ? AND source = 'intervals'",
            (date_str,),
        ).fetchone()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return None, None


def _render_wellness_body(
    status: dict, trend_data: dict, date_str: str, steps=None, weight_kg=None
) -> str:
    """회복/웰니스 본문 HTML 조립."""
    # 추세 카드는 데이터 유무와 무관하게 항상 표시
    trend_section = _render_trend_card(trend_data)

    if not status.get("available"):
        return _no_data(date_str) + trend_section

    raw = status.get("raw") or {}
    detail = status.get("detail") or {}
    grade = status.get("grade")
    score = status.get("recovery_score")

    activity_section = _render_activity_card(steps, weight_kg)

    return (
        _render_readiness_card(detail)
        + "<div class='cards-row'>"
        + _render_recovery_card(raw, grade, score)
        + _render_sleep_card(raw, detail)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_hrv_card(raw, detail)
        + _render_other_card(detail)
        + "</div>"
        + activity_section
        + trend_section
    )


# ── 라우트 ───────────────────────────────────────────────────────────────

@wellness_bp.get("/wellness")
def wellness_view():
    """회복/웰니스 상세 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = render_sub_nav("wellness") + "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("회복/웰니스", body, active_tab="dashboard")

    date_str = request.args.get("date", "").strip() or date.today().isoformat()

    try:
        with sqlite3.connect(str(dpath)) as conn:
            status = get_recovery_status(conn, date_str)
            trend_data = recovery_trend(conn, days=14)
            steps, weight_kg = _fetch_steps_weight(conn, date_str)
            wellness_7d = _load_7day_wellness(conn, date_str)
    except Exception as exc:
        body = render_sub_nav("wellness") + f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return html_page("회복/웰니스", body, active_tab="dashboard")

    date_form = (
        "<div class='card'>"
        "<form method='get' action='/wellness' "
        "style='display:flex; gap:1rem; align-items:center;'>"
        f"<label>날짜: <input type='date' name='date' value='{html.escape(date_str)}'></label>"
        "<button type='submit'>조회</button>"
        "</form>"
        "</div>"
    )

    extra = _render_7day_chart(wellness_7d) + _render_recovery_recommendation(status)
    body = render_sub_nav("wellness") + date_form + _render_wellness_body(status, trend_data, date_str, steps, weight_kg) + extra
    return html_page(f"회복/웰니스 — {date_str}", body, active_tab="dashboard")
