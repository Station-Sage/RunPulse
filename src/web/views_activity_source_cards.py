"""활동 상세 — 소스별 서비스 카드 렌더링.

Garmin / Strava / Intervals.icu / Runalyze 원본 데이터 카드 +
소스 비교 테이블 카드.
"""
from __future__ import annotations

import html
from typing import Any

from src.utils.pace import seconds_to_pace
from src.services.unified_activities import SOURCE_COLORS, build_source_comparison
from .helpers import (
    fmt_duration,
    fmt_min,
    make_table,
    metric_row,
    readiness_badge,
    safe_str,
)
from .views_activity_cards import _fmt_int, _fmt_float1, _fmt_min_sec


def _render_garmin_daily_detail(detail: dict, act_date: str) -> str:
    """Garmin 일별 상세 지표 카드 (수면/HRV/바디배터리)."""
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
    training_rows = [
        ("Training Effect (유산소)", _fmt_float1(garmin.get("training_effect_aerobic"))),
        ("Training Effect (무산소)", _fmt_float1(garmin.get("training_effect_anaerobic"))),
        ("Training Load", _fmt_float1(garmin.get("training_load"))),
        ("평균 파워", _fmt_int(garmin.get("avg_power"), " W")),
        ("Normalized Power", _fmt_int(garmin.get("normalized_power"), " W")),
        ("VO2Max", garmin.get("vo2max")),
    ]
    bio_rows = [
        ("걸음 수", _fmt_int(garmin.get("steps"), " 걸음")),
        ("평균 보폭", _fmt_float1(garmin.get("avg_stride_length"), " m")),
        ("평균 케이던스", _fmt_float1(garmin.get("avg_run_cadence"), " spm")),
        ("최대 케이던스", _fmt_int(garmin.get("max_run_cadence"), " spm")),
        ("평균 수직 비율", _fmt_float1(garmin.get("avg_vertical_ratio"), "%")),
        ("지면 접촉 시간", _fmt_int(garmin.get("avg_ground_contact_time"), " ms")),
    ]
    hr_zone_rows = []
    for i in range(1, 6):
        v = garmin.get(f"hr_zone_time_{i}")
        if v is not None:
            hr_zone_rows.append((f"HR 존 {i}", _fmt_min_sec(v)))

    content = "".join(
        metric_row(label, val)
        for label, val in training_rows
        if val not in (None, "—")
    )
    bio_content = "".join(
        metric_row(label, val)
        for label, val in bio_rows
        if val not in (None, "—")
    )
    zone_content = "".join(metric_row(label, val) for label, val in hr_zone_rows)

    if bio_content:
        content += "<p style='margin:0.5rem 0 0.1rem; font-size:0.8rem; color:var(--muted); font-weight:600;'>바이오메카닉스</p>" + bio_content
    if zone_content:
        content += "<p style='margin:0.5rem 0 0.1rem; font-size:0.8rem; color:var(--muted); font-weight:600;'>HR 존별 시간</p>" + zone_content

    if not content:
        content = "<p class='muted' style='margin:0;'>데이터 수집 중입니다</p>"
    return "<div class='card'><h2>Garmin</h2>" + content + "</div>"


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

    max_spd = strava.get("max_speed_mps")
    max_spd_str = f"{max_spd * 3.6:.1f} km/h" if max_spd else None
    moving = strava.get("moving_time_sec")
    elapsed = strava.get("elapsed_time_sec")

    main_rows = [
        ("Suffer Score", strava.get("suffer_score")),
        ("Training Load", _fmt_float1(strava.get("training_load"))),
        ("Intensity", _fmt_float1(strava.get("intensity"))),
        ("최고 속도", max_spd_str),
        ("활동 시간", fmt_duration(moving) if moving else None),
        ("경과 시간", fmt_duration(elapsed) if elapsed else None),
        ("고도 하강", _fmt_float1(strava.get("elevation_loss"), " m")),
        ("Grade Adj. 거리", _fmt_float1(
            strava["grade_adjusted_distance_m"] / 1000
            if strava.get("grade_adjusted_distance_m") else None, " km"
        )),
        ("평균 경사도", _fmt_float1(strava.get("avg_grade"), "%")),
        ("총 스텝", _fmt_int(strava.get("total_steps"))),
    ]
    content = "".join(
        metric_row(label, val)
        for label, val in main_rows
        if val not in (None, "—")
    )

    weather_rows = [
        ("기온 (활동)", _fmt_float1(strava.get("avg_temp_c"), "°C")),
        ("기온 (날씨)", _fmt_float1(strava.get("weather_temp_c"), "°C")),
        ("습도", _fmt_int(strava.get("weather_humidity"), "%")),
        ("풍속", _fmt_float1(strava.get("wind_speed_ms"), " m/s")),
        ("돌풍", _fmt_float1(strava.get("wind_gust_ms"), " m/s")),
        ("UV 지수", _fmt_float1(strava.get("uv_index"))),
        ("운량", _fmt_int(strava.get("cloud_cover"), "%")),
    ]
    weather_content = "".join(
        metric_row(label, val)
        for label, val in weather_rows
        if val not in (None, "—")
    )
    if weather_content:
        content += "<p style='margin:0.5rem 0 0.1rem; font-size:0.8rem; color:var(--muted); font-weight:600;'>날씨</p>" + weather_content

    if not content:
        if strava.get("in_group"):
            content = (
                "<p class='muted' style='margin:0;'>Strava 활동이 연결됨 — 상세 지표 미수집"
                "<br><small>Strava 동기화 재실행 시 자동으로 수집됩니다.</small></p>"
            )
        else:
            content = "<p class='muted' style='margin:0;'>데이터 수집 중입니다</p>"

    return (
        "<div class='card'>"
        "<h2>Strava</h2>"
        + content
        + be_html
        + "</div>"
    )


def _render_intervals_metrics(intervals: dict) -> str:
    """Intervals.icu 소스 메트릭 카드."""
    api_rows = [
        ("Training Load", _fmt_float1(intervals.get("icu_training_load"))),
        ("HRSS", _fmt_float1(intervals.get("icu_hrss"))),
        ("Intensity", _fmt_float1(intervals.get("icu_intensity"))),
        ("Efficiency Factor", _fmt_float1(intervals.get("icu_efficiency_factor"))),
        ("Decoupling", _fmt_float1(intervals.get("decoupling"), "%")),
        ("TRIMP", _fmt_float1(intervals.get("trimp"))),
        ("Average Stride", _fmt_float1(intervals.get("average_stride"), " m")),
        ("Strain Score", _fmt_float1(intervals.get("strain_score"))),
        ("HR Load", _fmt_float1(intervals.get("hr_load"))),
        ("Pace Load", _fmt_float1(intervals.get("pace_load"))),
        ("Power Load", _fmt_float1(intervals.get("power_load"))),
        ("Session RPE", _fmt_float1(intervals.get("session_rpe"))),
        ("랩 수", _fmt_int(intervals.get("icu_lap_count"))),
    ]
    content = "".join(
        metric_row(label, val)
        for label, val in api_rows
        if val not in (None, "—")
    )

    fit_rows = [
        ("TSS", _fmt_float1(intervals.get("tss"))),
        ("NP", _fmt_float1(intervals.get("normalized_power"), " W")),
        ("최대 파워", _fmt_float1(intervals.get("max_power"), " W")),
        ("랩 수 (FIT)", _fmt_int(intervals.get("num_laps"))),
        ("최고 속도", _fmt_float1(
            intervals["max_speed"] * 3.6 if intervals.get("max_speed") else None, " km/h"
        )),
        ("고도 하강", _fmt_float1(intervals.get("elevation_loss"), " m")),
        ("평균 케이던스", _fmt_int(intervals.get("avg_cadence"), " spm")),
    ]
    fit_content = "".join(
        metric_row(label, val)
        for label, val in fit_rows
        if val not in (None, "—")
    )
    if fit_content:
        content += "<p style='margin:0.5rem 0 0.1rem; font-size:0.8rem; color:var(--muted); font-weight:600;'>FIT 파일</p>" + fit_content

    if not content:
        content = "<p class='muted' style='margin:0;'>데이터 수집 중입니다</p>"
    return "<div class='card'><h2>Intervals.icu</h2>" + content + "</div>"


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


def _render_source_comparison(
    source_rows: dict[str, dict], activity_id: int | None = None
) -> str:
    """소스별 기본 지표 비교 테이블 카드.

    통합값 열(Garmin 우선) + 소스별 원본값 열(차이 강조).
    """
    if not source_rows:
        return ""

    payload_link = ""
    if activity_id is not None:
        payload_link = (
            "<p style='margin-top:0.6rem; font-size:0.85rem;'>"
            f"<a href='/payloads?activity_id={activity_id}'>원본 payload 보기 →</a></p>"
        )

    if len(source_rows) < 2:
        return (
            "<div class='card'><h2>소스 비교</h2>"
            "<p class='muted'>단일 소스 활동 — 비교할 다른 소스가 없습니다.</p>"
            + payload_link
            + "</div>"
        )

    from src.services.unified_activities import SERVICE_PRIORITY as _SP
    comparison = build_source_comparison(source_rows)
    sources = [s for s in _SP if s in source_rows]

    _INT_FIELDS = {"케이던스(spm)", "고도 상승(m)", "평균 심박(bpm)", "최대 심박(bpm)", "칼로리(kcal)", "파워(W)"}

    def _fmt_v(v: Any, field_label: str = "") -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return str(int(round(v))) if field_label in _INT_FIELDS else str(round(v, 2))
        return str(v)

    def _is_diff(v: Any, unified_v: Any) -> bool:
        if (v is None) != (unified_v is None):
            return True
        if v is None:
            return False
        try:
            fv, fu = float(v), float(unified_v)
            if fu == 0:
                return fv != 0
            return abs(fv - fu) / abs(fu) > 0.005
        except (TypeError, ValueError):
            return str(v) != str(unified_v)

    th_cells = (
        "<th>지표</th><th>통합값</th>"
        + "".join(
            f"<th><span style='background:{SOURCE_COLORS.get(s, '#888')}; "
            f"color:#fff; border-radius:3px; padding:1px 6px; font-size:0.8rem;'>"
            f"{html.escape(s)}</span></th>"
            for s in sources
        )
    )

    _INTERVALS_ELEV_NOTE = (
        "<span style='font-size:0.72rem; color:var(--muted);' "
        "title='intervals.icu는 DEM 보정값 사용 — 부정확할 수 있음'>*DEM</span>"
    )

    body_rows = []
    for item in comparison:
        uv = item.get("unified_value")
        us = item.get("unified_source")
        field = item["field"]

        if all(item.get(src) is None for src in sources):
            continue

        uv_str = _fmt_v(uv, field)
        src_badge = ""
        if us:
            color = SOURCE_COLORS.get(us, "#888")
            src_badge = (
                f" <span style='background:{color}; color:#fff; border-radius:2px; "
                f"padding:0 4px; font-size:0.7rem; vertical-align:middle;'>"
                f"{html.escape(us[0].upper())}</span>"
            )
        unified_cell = f"<td><strong>{html.escape(uv_str)}</strong>{src_badge}</td>"

        src_cells = ""
        for src in sources:
            v = item.get(src)
            v_str = _fmt_v(v, field)
            diff = _is_diff(v, uv)
            bg = " style='background:rgba(255,200,0,0.25);'" if diff else ""
            extra = ""
            if src == "intervals" and field == "고도 상승(m)" and v is not None:
                extra = " " + _INTERVALS_ELEV_NOTE
            src_cells += f"<td{bg}>{html.escape(v_str)}{extra}</td>"

        body_rows.append(
            f"<tr><td><strong>{html.escape(field)}</strong></td>"
            f"{unified_cell}{src_cells}</tr>"
        )

    return (
        "<div class='card'>"
        "<h2>소스 비교</h2>"
        f"<table><thead><tr>{th_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
        + payload_link
        + "</div>"
    )
