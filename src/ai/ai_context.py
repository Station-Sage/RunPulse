"""Phase 5 AI 컨텍스트 빌더 — 서비스 레이어 기반 LLM 프롬프트 생성.

서비스 레이어만 호출. 직접 SQL 없음.
모든 메트릭 값에 해석(레이블) 포함.

설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
"""
from __future__ import annotations

import sqlite3

from src.services.activity_service import get_activity_detail
from src.services.dashboard_service import get_dashboard_data
from src.web.template_helpers import (
    confidence_badge,
    format_distance,
    format_duration,
    format_pace,
    format_time_prediction,
    interpret_metric_level,
)


def build_daily_briefing(conn: sqlite3.Connection, date: str | None = None) -> str:
    """오늘의 상태 요약 — LLM에 전달할 markdown 문자열."""
    data = get_dashboard_data(conn, date)
    target_date = data.get("date", "")
    lines: list[str] = [f"## 오늘의 상태 ({target_date})", ""]

    # 훈련 준비도
    readiness = data.get("readiness", {})
    lines.append("### 훈련 준비도")
    for key, display in [("utrs", "UTRS"), ("cirs", "CIRS"), ("crs", "CRS")]:
        entry = readiness.get(key)
        if not entry or entry.get("value") is None:
            continue
        val = entry["value"]
        level = interpret_metric_level(key, val)
        conf = confidence_badge(entry.get("confidence"))
        conf_str = f" [{conf}]" if conf else ""
        lines.append(f"- {display}: {val:.1f}점 ({level}){conf_str}")
    lines.append("")

    # 체력 상태
    ts = data.get("training_status", {})
    if any(ts.get(k) is not None for k in ("ctl", "atl", "tsb")):
        lines.append("### 체력 상태")
        for key, label in [("ctl", "CTL"), ("atl", "ATL"), ("tsb", "TSB")]:
            val = ts.get(key)
            if val is not None:
                lines.append(f"- {label}: {val:.1f}")
        ramp = ts.get("ramp_rate")
        if ramp is not None:
            sign = "+" if ramp >= 0 else ""
            lines.append(f"- 추세: {ts.get('training_phase', '')} (ramp_rate {sign}{ramp:.1f})")
        lines.append("")

    # 수면
    wellness = data.get("wellness", {})
    sleep_items = [
        ("sleep_score", "수면 점수", lambda v: str(v)),
        ("sleep_duration_sec", "수면 시간", format_duration),
        ("hrv_last_night", "HRV (지난밤)", lambda v: f"{v:.0f}ms"),
        ("resting_hr", "안정시 심박", lambda v: f"{v:.0f}bpm"),
    ]
    sleep_lines = []
    for col, label, fmt in sleep_items:
        val = wellness.get(col)
        if val is not None:
            sleep_lines.append(f"- {label}: {fmt(val)}")
    if sleep_lines:
        lines.append("### 수면")
        lines.extend(sleep_lines)
        lines.append("")

    # 레이스 예측
    rp = data.get("race_predictions", {})
    pred_items = [
        ("darp_5k", "5K"), ("darp_10k", "10K"),
        ("darp_half", "하프"), ("darp_marathon", "풀"),
    ]
    pred_parts = [
        f"{label}: {format_time_prediction(rp.get(key))}"
        for key, label in pred_items
        if rp.get(key) is not None
    ]
    if pred_parts:
        lines.append("### 레이스 예측 (DARP)")
        lines.append("- " + " | ".join(pred_parts))
        lines.append("")

    # 최근 활동
    recent = data.get("recent_activities", [])
    if recent:
        lines.append("### 최근 활동")
        for act in recent[:3]:
            dist = format_distance(act.get("distance_m"))
            dur = format_duration(act.get("duration_sec"))
            pace = format_pace(act.get("avg_pace_sec_km"))
            pace_str = f", 페이스 {pace}/km" if pace else ""
            lines.append(
                f"- {act.get('name', '')} {dist}, {dur}{pace_str}"
            )

    return "\n".join(lines)


def build_activity_analysis(conn: sqlite3.Connection, activity_id: int) -> str:
    """활동 분석 컨텍스트 — LLM에 전달할 markdown 문자열."""
    detail = get_activity_detail(conn, activity_id)
    core = detail.get("core", {})
    metrics = detail.get("metrics_by_category", {})
    comparison = detail.get("source_comparison", {})

    name = core.get("name", f"활동 #{activity_id}")
    start = (core.get("start_time") or "")[:10]
    lines: list[str] = [f"## 활동 분석: {name} ({start})", ""]

    # 기본 정보
    lines.append("### 기본 정보")
    dist = format_distance(core.get("distance_m"))
    dur = format_duration(core.get("duration_sec"))
    pace = format_pace(core.get("avg_pace_sec_km"))
    if dist or dur:
        lines.append(f"- 거리: {dist} | 시간: {dur}" + (f" | 페이스: {pace}/km" if pace else ""))
    avg_hr = core.get("avg_hr")
    max_hr = core.get("max_hr")
    if avg_hr:
        max_str = f" | 최대: {max_hr}bpm" if max_hr else ""
        lines.append(f"- 평균 심박: {avg_hr}bpm{max_str}")
    elev = core.get("elevation_gain")
    if elev:
        lines.append(f"- 고도: +{elev:.0f}m")
    lines.append("")

    # RunPulse 분석 (모든 카테고리 순회)
    rp_items = []
    for category, cat_metrics in sorted(metrics.items()):
        for m in cat_metrics:
            val = m.get("numeric_value") or m.get("text_value")
            if val is None:
                continue
            metric_name = m["metric_name"]
            level = interpret_metric_level(metric_name, m.get("numeric_value"))
            level_str = f" ({level})" if level else ""
            conf = confidence_badge(m.get("confidence"))
            conf_str = f" [{conf}]" if conf else ""
            rp_items.append(f"- {metric_name}: {val}{level_str}{conf_str}")
    if rp_items:
        lines.append("### RunPulse 분석")
        lines.extend(rp_items)
        lines.append("")

    # 소스 비교
    if len(comparison) > 1:
        lines.append("### 소스 비교")
        headers = ["지표"] + list(comparison.keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for col in ("distance_m", "avg_hr", "training_load", "suffer_score"):
            vals = [format_distance(v.get(col)) if col == "distance_m"
                    else str(v.get(col) or "—")
                    for v in comparison.values()]
            lines.append("| " + col + " | " + " | ".join(vals) + " |")

    return "\n".join(lines)


def build_ai_context(
    conn: sqlite3.Connection,
    date: str | None = None,
    activity_id: int | None = None,
) -> str:
    """통합 AI 컨텍스트: daily briefing + (옵션) 활동 분석."""
    parts = [build_daily_briefing(conn, date)]
    if activity_id is not None:
        parts.append(build_activity_analysis(conn, activity_id))
    return "\n\n---\n\n".join(parts)
