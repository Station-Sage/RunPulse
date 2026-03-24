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

from flask import Blueprint, render_template, request

from src.analysis.activity_deep import deep_analyze
from src.utils.pace import seconds_to_pace
from src.services.unified_activities import (
    SOURCE_COLORS,
    build_source_comparison,
    _COLS as _SUMMARY_COLS,
)
from .helpers import (
    db_path,
    fmt_duration,
    fmt_min,
    fmt_pace,
    make_table,
    metric_row,
    readiness_badge,
    safe_str,
)

activity_bp = Blueprint("activity", __name__)


# ── 카드 렌더링 헬퍼 ────────────────────────────────────────────────────

def _fmt_int(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{int(round(float(v)))}{unit}"


def _fmt_float1(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{float(v):.1f}{unit}"


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
        + metric_row("평균 심박", _fmt_int(act.get("avg_hr"), " bpm"))
        + metric_row("최대 심박", _fmt_int(act.get("max_hr"), " bpm"))
        + metric_row("평균 케이던스", _fmt_int(act.get("avg_cadence"), " spm"))
        + metric_row("고도 상승", _fmt_int(act.get("elevation_gain"), " m"))
        + metric_row("칼로리", _fmt_int(act.get("calories"), " kcal"))
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


def _fmt_min_sec(sec) -> str:
    """초 → 'Mm Ss' 형식."""
    if sec is None:
        return "—"
    try:
        s = int(round(float(sec)))
        m, r = divmod(s, 60)
        return f"{m}분 {r:02d}초" if m else f"{r}초"
    except Exception:
        return str(sec)


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
    # HR 존 시간
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
        content = "<p class='muted' style='margin:0;'>데이터 없음 (동기화 필요)</p>"
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
        ("Grade Adj. 거리", _fmt_float1(strava.get("grade_adjusted_distance_m") and strava["grade_adjusted_distance_m"] / 1000 if strava.get("grade_adjusted_distance_m") else None, " km")),
        ("평균 경사도", _fmt_float1(strava.get("avg_grade"), "%")),
        ("총 스텝", _fmt_int(strava.get("total_steps"))),
    ]
    content = "".join(
        metric_row(label, val)
        for label, val in main_rows
        if val not in (None, "—")
    )

    # 날씨 섹션
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
            content = "<p class='muted' style='margin:0;'>데이터 없음 (Strava API 동기화 필요)</p>"

    return (
        "<div class='card'>"
        "<h2>Strava</h2>"
        + content
        + be_html
        + "</div>"
    )


def _render_intervals_metrics(intervals: dict) -> str:
    """Intervals.icu 소스 메트릭 카드."""
    # API sync 필드
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

    # FIT 파일 임포트 필드 (API 없을 때 표시)
    fit_rows = [
        ("TSS", _fmt_float1(intervals.get("tss"))),
        ("NP", _fmt_float1(intervals.get("normalized_power"), " W")),
        ("최대 파워", _fmt_float1(intervals.get("max_power"), " W")),
        ("랩 수 (FIT)", _fmt_int(intervals.get("num_laps"))),
        ("최고 속도", _fmt_float1(intervals.get("max_speed") and intervals["max_speed"] * 3.6 if intervals.get("max_speed") else None, " km/h")),
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
        content = "<p class='muted' style='margin:0;'>데이터 없음 (intervals 동기화 필요)</p>"
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
            f"{item.get('km')} (부분)" if item.get("partial") else item.get("km"),
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


# ── 소스 비교 테이블 ─────────────────────────────────────────────────────

def _fetch_source_rows(conn: sqlite3.Connection, activity_id: int) -> dict[str, dict]:
    """activity_id와 같은 그룹에 속한 모든 소스의 row 반환."""
    row = conn.execute(
        f"SELECT {', '.join(_SUMMARY_COLS)} FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        return {}

    rd = dict(zip(_SUMMARY_COLS, row))
    group_id = rd.get("matched_group_id")

    if group_id:
        rows = conn.execute(
            f"SELECT {', '.join(_SUMMARY_COLS)} FROM activity_summaries "
            "WHERE matched_group_id = ?",
            (group_id,),
        ).fetchall()
    else:
        rows = [row]

    source_rows: dict[str, dict] = {}
    for r in rows:
        d = dict(zip(_SUMMARY_COLS, r))
        src = d["source"]
        if src not in source_rows:
            source_rows[src] = d

    # avg_power가 activity_summaries에 없으면 activity_detail_metrics에서 보완
    for d in source_rows.values():
        if d.get("avg_power") is None:
            pw = conn.execute(
                "SELECT metric_value FROM activity_detail_metrics "
                "WHERE activity_id = ? AND metric_name = 'avg_power' LIMIT 1",
                (d["id"],),
            ).fetchone()
            if pw and pw[0] is not None:
                d["avg_power"] = pw[0]

    return source_rows


def _render_source_comparison(
    source_rows: dict[str, dict], activity_id: int | None = None
) -> str:
    """소스별 기본 지표 비교 테이블 카드.

    - 통합값 열: Garmin 우선 선택값 + 출처 배지
    - 소스별 원본값 열: 차이가 있는 셀은 노란 배경으로 강조
    - 하단: 원본 payload 링크
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

    # 소숫점 없이 표시할 필드
    _INT_FIELDS = {"케이던스(spm)", "고도 상승(m)", "평균 심박(bpm)", "최대 심박(bpm)", "칼로리(kcal)", "파워(W)"}

    def _fmt_v(v: Any, field_label: str = "") -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            if field_label in _INT_FIELDS:
                return str(int(round(v)))
            return str(round(v, 2))
        return str(v)

    def _is_diff(v: Any, unified_v: Any) -> bool:
        """소스값이 통합값과 다른지 판별 (0.5% 이상 차이)."""
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

    # 헤더: 지표 | 통합값 | source …
    th_cells = (
        "<th>지표</th><th>통합값</th>"
        + "".join(
            f"<th><span style='background:{SOURCE_COLORS.get(s, '#888')}; "
            f"color:#fff; border-radius:3px; padding:1px 6px; font-size:0.8rem;'>"
            f"{html.escape(s)}</span></th>"
            for s in sources
        )
    )

    # intervals 고도는 DEM 보정값으로 부정확 — 비교에서 제외
    _INTERVALS_ELEV_NOTE = (
        "<span style='font-size:0.72rem; color:var(--muted);' "
        "title='intervals.icu는 DEM 보정값 사용 — 부정확할 수 있음'>*DEM</span>"
    )

    body_rows = []
    for item in comparison:
        uv = item.get("unified_value")
        us = item.get("unified_source")
        field = item["field"]

        # 모든 소스가 None이면 행 숨김
        all_none = all(item.get(src) is None for src in sources)
        if all_none:
            continue

        uv_str = _fmt_v(uv, field)

        # 통합값 셀: 값 + 출처 이니셜 배지
        src_badge = ""
        if us:
            color = SOURCE_COLORS.get(us, "#888")
            src_badge = (
                f" <span style='background:{color}; color:#fff; border-radius:2px; "
                f"padding:0 4px; font-size:0.7rem; vertical-align:middle;'>"
                f"{html.escape(us[0].upper())}</span>"
            )
        unified_cell = f"<td><strong>{html.escape(uv_str)}</strong>{src_badge}</td>"

        # 소스별 셀: 차이 있으면 노란 배경, intervals 고도에 경고 표시
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


# ── 이전/다음 네비게이션 ─────────────────────────────────────────────────

def _fetch_adjacent(conn, activity_id: int, start_time: str) -> tuple:
    """현재 활동 기준 이전/다음 활동 (id, date) 반환."""
    prev_row = conn.execute(
        """SELECT id, start_time FROM activity_summaries
           WHERE start_time < ? ORDER BY start_time DESC LIMIT 1""",
        (start_time,),
    ).fetchone()
    next_row = conn.execute(
        """SELECT id, start_time FROM activity_summaries
           WHERE start_time > ? ORDER BY start_time ASC LIMIT 1""",
        (start_time,),
    ).fetchone()
    return prev_row, next_row


def _render_activity_nav(
    prev_row: tuple | None, next_row: tuple | None
) -> str:
    """이전/다음 활동 네비 바."""
    parts = []
    if prev_row:
        prev_date = str(prev_row[1])[:10]
        parts.append(
            f"<a href='/activity/deep?id={prev_row[0]}'>← {html.escape(prev_date)}</a>"
        )
    else:
        parts.append("<span class='muted'>← (없음)</span>")

    parts.append("<a href='/activities'>목록으로</a>")

    if next_row:
        next_date = str(next_row[1])[:10]
        parts.append(
            f"<a href='/activity/deep?id={next_row[0]}'>{html.escape(next_date)} →</a>"
        )
    else:
        parts.append("<span class='muted'>(없음) →</span>")

    return (
        "<div style='display:flex; justify-content:space-between; "
        "align-items:center; margin:0.5rem 0; flex-wrap:wrap; gap:0.5rem;'>"
        + " ".join(parts)
        + "</div>"
    )


# ── 2차 메트릭 / computed_metrics 조회 ─────────────────────────────────────

def _load_activity_computed_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동별 computed_metrics 조회 → {metric_name: value} 딕셔너리."""
    rows = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics WHERE activity_id = ?",
        (activity_id,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_service_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """서비스 1차 메트릭 조회 (Garmin/Strava/Intervals 제공값).

    Returns:
        {service: {label: (value, unit)}} 딕셔너리.
    """
    row = conn.execute(
        """SELECT source,
                  aerobic_training_effect, anaerobic_training_effect,
                  training_load_acute, training_load_chronic,
                  suffer_score, avg_power, normalized_power,
                  icu_training_load, icu_trimp, icu_hrss,
                  icu_intensity, icu_efficiency_factor, icu_atl, icu_ctl, icu_tsb
           FROM activity_summaries WHERE id=?""",
        (activity_id,),
    ).fetchone()
    if row is None:
        return {}

    source = row[0] or ""
    result: dict = {}

    # Garmin 1차 메트릭
    garmin = {}
    if row[1] is not None:
        garmin["에어로빅 훈련 효과 (ATE)"] = (float(row[1]), "/ 5.0")
    if row[2] is not None:
        garmin["무산소 훈련 효과 (AnTE)"] = (float(row[2]), "/ 5.0")
    if row[3] is not None:
        garmin["급성 훈련 부하 (ATL)"] = (float(row[3]), "")
    if row[4] is not None:
        garmin["만성 훈련 부하 (CTL)"] = (float(row[4]), "")
    if garmin:
        result["Garmin"] = garmin

    # Strava 1차 메트릭
    strava = {}
    if row[5] is not None:
        strava["Suffer Score"] = (float(row[5]), "")
    if row[6] is not None:
        strava["평균 파워"] = (float(row[6]), " W")
    if row[7] is not None:
        strava["정규화 파워 (NP)"] = (float(row[7]), " W")
    if strava:
        result["Strava"] = strava

    # Intervals.icu 1차 메트릭
    icu = {}
    if row[8] is not None:
        icu["훈련 부하 (Training Load)"] = (float(row[8]), "")
    if row[9] is not None:
        icu["TRIMP"] = (float(row[9]), "")
    if row[10] is not None:
        icu["HRSS"] = (float(row[10]), "")
    if row[11] is not None:
        icu["강도 (Intensity)"] = (float(row[11]), "")
    if row[12] is not None:
        icu["효율 계수 (EF)"] = (float(row[12]), "")
    if row[13] is not None:
        icu["ATL"] = (float(row[13]), "")
    if row[14] is not None:
        icu["CTL"] = (float(row[14]), "")
    if row[15] is not None:
        icu["TSB"] = (float(row[15]), "")
    if icu:
        result["Intervals.icu"] = icu

    # activity_detail_metrics에서 날씨 + zone 스코어
    detail_rows = conn.execute(
        """SELECT metric_name, metric_value FROM activity_detail_metrics
           WHERE activity_id=? AND metric_name IN (
             'weather_temp_c','weather_humidity_pct','weather_wind_speed_ms',
             'heartrate_zone_score','power_zone_score'
           )""",
        (activity_id,),
    ).fetchall()
    detail = {r[0]: r[1] for r in detail_rows if r[1] is not None}

    weather = {}
    if "weather_temp_c" in detail:
        weather["기온"] = (float(detail["weather_temp_c"]), " °C")
    if "weather_humidity_pct" in detail:
        weather["습도"] = (float(detail["weather_humidity_pct"]), " %")
    if "weather_wind_speed_ms" in detail:
        weather["풍속"] = (float(detail["weather_wind_speed_ms"]), " m/s")
    if weather:
        result["날씨 (서비스)"] = weather

    zones_svc = {}
    if "heartrate_zone_score" in detail:
        zones_svc["HR Zone Score (Strava)"] = (float(detail["heartrate_zone_score"]), "")
    if "power_zone_score" in detail:
        zones_svc["Power Zone Score (Strava)"] = (float(detail["power_zone_score"]), "")
    if zones_svc:
        result["존 점수 (서비스)"] = zones_svc

    return result


def _load_day_computed_metrics(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 computed_metrics 조회 (activity_id IS NULL) → {metric_name: value}."""
    rows = conn.execute(
        """SELECT metric_name, metric_value FROM computed_metrics
           WHERE date = ? AND activity_id IS NULL""",
        (act_date,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_activity_metric_jsons(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동별 computed_metrics metric_json 조회 → {metric_name: dict}."""
    rows = conn.execute(
        "SELECT metric_name, metric_json FROM computed_metrics WHERE activity_id = ? AND metric_json IS NOT NULL",
        (activity_id,),
    ).fetchall()
    result = {}
    for name, mj in rows:
        try:
            result[name] = json.loads(mj)
        except Exception:
            pass
    return result


def _load_day_metric_jsons(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 computed_metrics metric_json 조회 (activity_id IS NULL) → {metric_name: dict}."""
    rows = conn.execute(
        """SELECT metric_name, metric_json FROM computed_metrics
           WHERE date = ? AND activity_id IS NULL AND metric_json IS NOT NULL""",
        (act_date,),
    ).fetchall()
    result = {}
    for name, mj in rows:
        try:
            result[name] = json.loads(mj)
        except Exception:
            pass
    return result


def _render_horizontal_scroll(act: dict, metrics: dict) -> str:
    """핵심 메트릭 수평 스크롤 바 (V2-4-6, 모바일 최적화)."""
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    pace_str = act.get("avg_pace") or "—"
    fearp_val = metrics.get("FEARP")
    gap_val = metrics.get("GAP")

    items = [
        ("🏃", "거리", dist_str),
        ("⏱", "시간", fmt_duration(act.get("duration_sec"))),
        ("⚡", "페이스", f"{pace_str}/km" if pace_str != "—" else "—"),
        ("❤️", "심박수", _fmt_int(act.get("avg_hr"), " bpm")),
        ("📈", "고도↑", _fmt_int(act.get("elevation_gain"), " m")),
        ("🔥", "칼로리", _fmt_int(act.get("calories"), " kcal")),
    ]
    if fearp_val is not None:
        items.append(("🌡", "FEARP", f"{fmt_pace(fearp_val)}/km"))
    if gap_val is not None:
        items.append(("⛰", "GAP", f"{fmt_pace(gap_val)}/km"))

    chips = "".join(
        f"<div style='display:inline-flex;flex-direction:column;align-items:center;"
        f"min-width:76px;padding:0.55rem 0.7rem;"
        f"background:rgba(255,255,255,0.06);border-radius:12px;margin:0 4px;'>"
        f"<span style='font-size:1.3rem;line-height:1;'>{icon}</span>"
        f"<span style='font-size:0.68rem;color:var(--muted);margin-top:3px;'>{label}</span>"
        f"<span style='font-size:0.88rem;font-weight:600;margin-top:2px;'>{val}</span>"
        f"</div>"
        for icon, label, val in items
    )
    return (
        "<div style='overflow-x:auto;white-space:nowrap;padding:0.5rem 0 0.8rem;"
        "-webkit-overflow-scrolling:touch;'>"
        + chips
        + "</div>"
    )


# 메트릭 메타 정보: {key: (title_tooltip, interpret_fn)}
# interpret_fn(value) → (text, color_css) | None
_METRIC_META: dict[str, tuple[str, object]] = {
    "FEARP":          ("환경 보정 페이스 — 기온·습도·경사·고도를 표준 조건(15°C, 50%, 평지, 0m)으로 환산한 등가 페이스. 낮을수록 실제로 빠름.",
                       lambda v: ("표준 조건 기준 빠름" if v < 270 else "표준 조건 기준 보통" if v < 360 else "표준 조건 기준 느림", "var(--green)" if v < 270 else "var(--orange)" if v < 360 else "var(--red)")),
    "GAP":            ("경사 보정 페이스 (Grade-Adjusted Pace) — 오르막·내리막 효과를 제거한 평지 등가 페이스.",
                       None),
    "NGP":            ("정규화 경사 페이스 (Normalized Graded Pace) — 강도 변화를 4차 멱승으로 가중 평균한 실효 페이스.",
                       None),
    "RelativeEffort": ("상대 노력도 — 심박존별 시간에 Strava 가중치(0.5/1.0/2.0/3.5/5.5)를 적용한 운동 강도 점수.",
                       lambda v: ("가벼운 운동" if v < 50 else "적당한 강도" if v < 100 else "높은 강도" if v < 200 else "매우 높은 강도", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 200 else "var(--red)")),
    "AerobicDecoupling": ("유산소 분리 (Aerobic Decoupling) — 후반 PA:HR 대비 전반 PA:HR 저하율. 낮을수록 심폐 효율 유지.",
                           lambda v: ("심폐 안정적" if v < 5 else "약간 분리" if v < 10 else "유산소 드리프트 큼", "var(--green)" if v < 5 else "var(--orange)" if v < 10 else "var(--red)")),
    "EF":             ("효율 계수 (Efficiency Factor) — 페이스÷심박수 비율. 높을수록 같은 심박에서 더 빠름.",
                       None),
    "TRIMP":          ("훈련 충격 점수 (TRIMP) — 심박존별 운동 시간에 지수 가중치를 적용한 훈련 부하 지수.",
                       lambda v: ("가벼운 부하" if v < 50 else "중간 부하" if v < 100 else "고부하" if v < 150 else "매우 고부하", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 150 else "var(--red)")),
    "WLEI":           ("날씨 가중 노력 지수 (WLEI) — TRIMP에 기온·습도 스트레스를 곱한 실제 신체 부담 지수. 더운 날은 동일 페이스도 WLEI가 더 높음.",
                       lambda v: ("낮은 날씨 부담" if v < 60 else "중간 날씨 부담" if v < 120 else "높은 날씨 부담", "var(--green)" if v < 60 else "var(--orange)" if v < 120 else "var(--red)")),
    "DI":             ("내구성 지수 (DI) — 90분+ 세션에서 후반 PA:HR 효율 / 전반 PA:HR 효율. 1.0 이상이면 끝까지 효율 유지.",
                       lambda v: ("내구성 우수" if v >= 1.0 else "내구성 보통" if v >= 0.9 else "내구성 저하", "var(--green)" if v >= 1.0 else "var(--orange)" if v >= 0.9 else "var(--red)")),
    "LSI":            ("부하 스파이크 지수 (LSI) — 오늘 TRIMP / 21일 평균 TRIMP. 1.5 초과 시 급격한 과부하.",
                       lambda v: ("정상 범위" if v < 1.3 else "주의 — 과부하 경향" if v < 1.5 else "위험 — 급격한 과부하", "var(--green)" if v < 1.3 else "var(--orange)" if v < 1.5 else "var(--red)")),
    "Monotony":       ("훈련 단조로움 (Monotony) — 최근 7일 TRIMP 평균÷표준편차. 낮을수록 변화 있는 훈련.",
                       lambda v: ("다양한 훈련" if v < 1.5 else "약간 단조로움" if v < 2.0 else "매우 단조로운 훈련", "var(--green)" if v < 1.5 else "var(--orange)" if v < 2.0 else "var(--red)")),
    "ACWR":           ("급성/만성 부하 비율 (ACWR) — 7일 부하÷28일 부하. 0.8~1.3이 안전 구간.",
                       lambda v: ("부하 부족" if v < 0.8 else "적절한 훈련량" if v <= 1.3 else "과부하 위험", "var(--cyan)" if v < 0.8 else "var(--green)" if v <= 1.3 else "var(--red)")),
    "ADTI":           ("유산소 분리 추세 (ADTI) — 8주 Decoupling 선형 회귀 기울기. 음수면 개선 추세.",
                       lambda v: ("유산소 개선 추세" if v < 0 else "유산소 정체" if v < 0.5 else "유산소 저하 추세", "var(--green)" if v < 0 else "var(--cyan)" if v < 0.5 else "var(--orange)")),
    "MarathonShape":  ("마라톤 상태 (Marathon Shape) — 주간 거리·장거리런 기준 훈련 준비도 (0~100%).",
                       lambda v: ("레이스 준비 미흡" if v < 40 else "기본 준비됨" if v < 70 else "레이스 준비 완료", "var(--red)" if v < 40 else "var(--orange)" if v < 70 else "var(--green)")),
    "RTTI":           ("러닝 내성 훈련 지수 (RTTI) — Garmin 권장 최대 부하 대비 실제 훈련 부하 비율. 100% = 권장 한계.",
                       lambda v: ("훈련 여유 있음" if v < 80 else "권장 범위 내" if v <= 100 else "권장 한계 초과", "var(--cyan)" if v < 80 else "var(--green)" if v <= 100 else "var(--red)")),
    "TPDI":           ("실내/야외 퍼포먼스 격차 (TPDI) — 실외 vs 실내 평균 FEARP 차이. 양수면 실외 더 빠름.",
                       lambda v: ("격차 없음" if abs(v) < 5 else "약간 격차" if abs(v) < 15 else "큰 격차", "var(--green)" if abs(v) < 5 else "var(--orange)" if abs(v) < 15 else "var(--red)")),
}


def _metric_tooltip_icon(key: str) -> str:
    """메트릭 설명 툴팁 아이콘 HTML."""
    meta = _METRIC_META.get(key)
    if not meta:
        return ""
    desc = html.escape(meta[0])
    return (
        f" <span style='cursor:help; color:var(--muted); font-size:0.75rem;' title='{desc}'>ⓘ</span>"
    )


def _metric_interp_badge(key: str, value: float) -> str:
    """현재 수치 해설 뱃지 HTML."""
    meta = _METRIC_META.get(key)
    if not meta or meta[1] is None:
        return ""
    try:
        text, color = meta[1](value)
        return (
            f" <span style='font-size:0.72rem; color:{color}; margin-left:6px;'>{text}</span>"
        )
    except Exception:
        return ""


def _render_secondary_metrics_card(
    metrics: dict,
    day_metrics: dict | None = None,
    service_metrics: dict | None = None,
) -> str:
    """RunPulse 분석 (primary) + 서비스 원본 (secondary subtab) 탭 카드."""
    dm = day_metrics or {}
    svc = service_metrics or {}

    # ── RunPulse 1차/2차 메트릭 ──────────────────────────────────────
    act_pairs = [
        ("FEARP",          metrics.get("FEARP"),          "pace"),
        ("GAP",            metrics.get("GAP"),            "pace"),
        ("NGP",            metrics.get("NGP"),            "pace"),
        ("RelativeEffort", metrics.get("RelativeEffort"), "f0"),
        ("AerobicDecoupling", metrics.get("AerobicDecoupling"), "f1%"),
        ("EF",             metrics.get("EF"),             "f4"),
        ("TRIMP",          metrics.get("TRIMP"),          "f1"),
        ("WLEI",           metrics.get("WLEI"),           "f1"),
    ]
    day_pairs = [
        ("DI",          dm.get("DI"),          "f2"),
        ("LSI",         dm.get("LSI"),         "f2"),
        ("Monotony",    dm.get("Monotony"),    "f2"),
        ("ACWR",        dm.get("ACWR"),        "f2"),
        ("ADTI",        dm.get("ADTI"),        "f4"),
        ("MarathonShape", dm.get("MarathonShape"), "f1%"),
        ("RTTI",        dm.get("RTTI"),        "f1%"),
        ("TPDI",        dm.get("TPDI"),        "f1%"),
    ]

    def _fmt_val(val, fmt: str) -> str:
        v = float(val)
        if fmt == "pace":
            return f"{fmt_pace(val)}/km"
        if fmt == "f0":
            return f"{v:.0f}"
        if fmt == "f1%":
            return f"{v:.1f}%"
        if fmt == "f4":
            return f"{v:.4f}"
        return f"{v:.1f}"

    def _rp_row(key: str, val, fmt: str) -> str:
        if val is None:
            return ""
        v = float(val)
        val_str = _fmt_val(val, fmt)
        badge = _metric_interp_badge(key, v)
        icon = _metric_tooltip_icon(key)
        label_html = f"{key}{icon}"
        return (
            "<div style='display:flex; justify-content:space-between; align-items:center;"
            "padding:0.4rem 0; border-bottom:1px solid var(--row-border);'>"
            f"<span style='font-size:0.85rem; color:var(--muted);'>{label_html}</span>"
            f"<span style='font-size:0.9rem; font-weight:600;'>{val_str}{badge}</span>"
            "</div>"
        )

    rp_rows = [_rp_row(k, v, f) for k, v, f in act_pairs if v is not None]
    if any(dm.get(k) is not None for k, _, _ in day_pairs):
        rp_rows.append(
            "<p style='font-size:0.75rem;color:var(--muted);margin:0.5rem 0 0.2rem;"
            "font-weight:600;'>당일 종합 지표</p>"
        )
    rp_rows += [_rp_row(k, v, f) for k, v, f in day_pairs if v is not None]

    if not rp_rows:
        rp_content = "<p class='muted' style='margin:0.5rem 0;'>메트릭 미계산 — 설정 → 재계산 후 확인하세요.</p>"
    else:
        rp_content = "".join(rp_rows)

    # ── 서비스 1차 메트릭 ────────────────────────────────────────────
    svc_html_parts = []
    _SVC_COLORS = {
        "Garmin": "#0055b3",
        "Strava": "#FC4C02",
        "Intervals.icu": "#00884e",
        "날씨 (서비스)": "#7b2d8b",
        "존 점수 (서비스)": "#666",
    }
    for svc_name, svc_data in svc.items():
        color = _SVC_COLORS.get(svc_name, "#555")
        inner = ""
        for label, (val, unit) in svc_data.items():
            val_str = f"{val:.1f}{unit}" if isinstance(val, float) else f"{val}{unit}"
            inner += (
                "<div style='display:flex; justify-content:space-between;"
                "padding:0.3rem 0; border-bottom:1px solid var(--row-border);'>"
                f"<span style='font-size:0.82rem; color:var(--muted);'>{label}</span>"
                f"<span style='font-size:0.85rem; font-weight:600;'>{val_str}</span>"
                "</div>"
            )
        svc_html_parts.append(
            f"<div style='margin-bottom:0.8rem;'>"
            f"<p style='font-size:0.75rem; font-weight:700; color:{color};"
            f"margin:0 0 0.3rem;'>{svc_name}</p>"
            f"{inner}</div>"
        )

    svc_content = "".join(svc_html_parts) if svc_html_parts else (
        "<p class='muted' style='margin:0.5rem 0;'>서비스 메트릭 없음 — 해당 서비스 동기화 후 확인하세요.</p>"
    )

    # ── 탭 HTML ──────────────────────────────────────────────────────
    card_id = "metrics-tab-card"
    return f"""<div class='card' id='{card_id}'>
  <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;'>
    <h2 style='margin:0;'>메트릭 분석</h2>
    <div style='display:flex; gap:4px;'>
      <button id='mtab-rp' onclick='switchMetricTab("rp")'
        style='padding:0.3rem 0.8rem; font-size:0.8rem; border:1px solid var(--cyan);
               background:var(--cyan); color:#000; border-radius:4px; cursor:pointer; font-weight:600;'>
        RunPulse
      </button>
      <button id='mtab-svc' onclick='switchMetricTab("svc")'
        style='padding:0.3rem 0.8rem; font-size:0.8rem; border:1px solid var(--card-border);
               background:none; color:var(--muted); border-radius:4px; cursor:pointer;'>
        서비스 원본
      </button>
    </div>
  </div>
  <div id='mtab-content-rp'>{rp_content}</div>
  <div id='mtab-content-svc' style='display:none;'>{svc_content}</div>
</div>
<script>
function switchMetricTab(tab) {{
  document.getElementById('mtab-content-rp').style.display = tab==='rp' ? 'block' : 'none';
  document.getElementById('mtab-content-svc').style.display = tab==='svc' ? 'block' : 'none';
  var btnRp = document.getElementById('mtab-rp');
  var btnSvc = document.getElementById('mtab-svc');
  if (tab==='rp') {{
    btnRp.style.background='var(--cyan)'; btnRp.style.color='#000'; btnRp.style.borderColor='var(--cyan)';
    btnSvc.style.background='none'; btnSvc.style.color='var(--muted)'; btnSvc.style.borderColor='var(--card-border)';
  }} else {{
    btnSvc.style.background='var(--cyan)'; btnSvc.style.color='#000'; btnSvc.style.borderColor='var(--cyan)';
    btnRp.style.background='none'; btnRp.style.color='var(--muted)'; btnRp.style.borderColor='var(--card-border)';
  }}
}}
</script>"""


def _render_daily_scores_card(day_metrics: dict) -> str:
    """당일 UTRS/CIRS/ACWR 점수 카드 (V2-4-3)."""
    utrs = day_metrics.get("UTRS")
    cirs = day_metrics.get("CIRS")
    acwr = day_metrics.get("ACWR")

    if all(v is None for v in (utrs, cirs, acwr)):
        return (
            "<div class='card'>"
            "<h2>당일 훈련 지수</h2>"
            "<p class='muted' style='margin:0;'>해당 날짜의 UTRS/CIRS 데이터가 없습니다.</p>"
            "</div>"
        )
    return (
        "<div class='card'>"
        "<h2>당일 훈련 지수</h2>"
        + metric_row("UTRS (훈련 준비도)", f"{float(utrs):.0f}" if utrs is not None else "—")
        + metric_row("CIRS (부상 위험도)", f"{float(cirs):.0f}" if cirs is not None else "—")
        + metric_row("ACWR (급성/만성 부하비)", f"{float(acwr):.2f}" if acwr is not None else "—")
        + "</div>"
    )


# ── 신규 분석 카드 ─────────────────────────────────────────────────────────

def _render_activity_classification_badge(act: dict) -> str:
    """활동 유형 자동 분류 뱃지 (easy/tempo/interval/long/recovery/race)."""
    duration = act.get("duration_sec") or 0
    avg_hr = act.get("avg_hr") or 0
    if duration >= 90 * 60:
        cls, icon, desc = "장거리런", "&#127959;", "90분+ 장거리 훈련"
    elif avg_hr >= 175:
        cls, icon, desc = "인터벌/경기", "&#9889;", "고강도 — 인터벌 또는 레이스 수준"
    elif avg_hr >= 160:
        cls, icon, desc = "템포런", "&#128293;", "유산소 역치 훈련"
    elif avg_hr and avg_hr < 135:
        cls, icon, desc = "회복런", "&#128564;", "가벼운 회복 조깅"
    elif avg_hr:
        cls, icon, desc = "유산소런", "&#127939;", "기본 유산소 훈련"
    else:
        return ""
    return (
        f"<div style='padding:0.3rem 0;'>"
        f"<span style='background:rgba(0,212,255,0.12);color:var(--cyan);"
        f"border-radius:16px;padding:0.28rem 0.8rem;font-size:0.8rem;'>"
        f"{icon} {cls} — {desc}</span></div>"
    )


def _render_di_card(day_metrics: dict) -> str:
    """DI (내구성 지수) 카드 — 장거리 지구력 평가."""
    di = day_metrics.get("DI")
    if di is None:
        return (
            "<div class='card'><h2>DI 내구성 지수</h2>"
            "<p class='muted' style='margin:0;'>90분 이상 세션 3회+ 필요. 장거리 훈련 후 표시됩니다.</p></div>"
        )
    di_f = float(di)
    if di_f >= 1.0:
        badge, badge_color, interp = "&#10003; 우수", "var(--green)", "후반에도 페이스·심박 효율 유지. 내구성 양호."
    elif di_f >= 0.9:
        badge, badge_color, interp = "&#9888; 보통", "var(--orange)", "후반 효율 소폭 저하. 장거리 훈련으로 개선 가능."
    else:
        badge, badge_color, interp = "&#10007; 부족", "var(--red)", "후반 페이스 저하 뚜렷. 지구력 강화 훈련 필요."
    return (
        "<div class='card'><h2>DI 내구성 지수</h2>"
        "<div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;'>"
        f"<span style='font-size:2rem;font-weight:700;color:var(--cyan);'>{di_f:.3f}</span>"
        f"<span style='background:rgba(255,255,255,0.08);color:{badge_color};"
        f"border-radius:12px;padding:0.2rem 0.6rem;font-size:0.82rem;'>{badge}</span></div>"
        f"<p style='font-size:0.82rem;color:var(--secondary);margin:0;'>{interp}</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>&#8805;1.0 우수 / 0.9-1.0 보통 / &lt;0.9 부족 | 최근 8주 90분+ 세션 평균</p>"
        "</div>"
    )


def _render_fearp_breakdown_card(metric_jsons: dict) -> str:
    """FEARP 환경 요인 분해 카드."""
    mj = metric_jsons.get("FEARP")
    if not mj:
        return ""
    actual = mj.get("actual_pace") or 0
    fearp = mj.get("fearp") or actual
    diff = fearp - actual if actual > 0 else 0
    diff_str = (f"+{fmt_pace(abs(diff))}/km 느린 조건" if diff > 0
                else f"{fmt_pace(abs(diff))}/km 빠른 조건") if diff else "표준 조건"

    def _factor_bar(label: str, factor: float, baseline: float = 1.0) -> str:
        deviation = (factor - baseline) / baseline * 100 if baseline else 0
        if abs(deviation) < 0.5:
            clr, effect = "#00ff88", "영향 없음"
        elif deviation > 0:
            clr, effect = "#ffaa00", f"+{deviation:.1f}% 불리"
        else:
            clr, effect = "#00d4ff", f"{deviation:.1f}% 유리"
        pct = min(100, abs(deviation) * 5)
        return (
            f"<div style='margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='color:{clr};'>{effect} ({factor:.4f})</span></div>"
            f"<div style='background:rgba(255,255,255,0.08);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{clr};border-radius:3px;height:5px;'></div></div></div>"
        )

    bars = (
        _factor_bar("기온 영향 (temp_factor)", mj.get("temp_factor", 1.0))
        + _factor_bar("습도 영향 (humidity_factor)", mj.get("humidity_factor", 1.0))
        + _factor_bar("고도 영향 (altitude_factor)", mj.get("altitude_factor", 1.0))
        + _factor_bar("경사 영향 (grade_factor)", mj.get("grade_factor", 1.0))
    )
    return (
        "<div class='card'><h2>FEARP 환경 요인 분해</h2>"
        "<div style='display:flex;gap:1.5rem;margin-bottom:0.6rem;'>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;color:var(--cyan);'>"
        f"{fmt_pace(fearp)}/km</div><div class='muted' style='font-size:0.74rem;'>FEARP (보정)</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;'>"
        f"{fmt_pace(actual)}/km</div><div class='muted' style='font-size:0.74rem;'>실제 페이스</div></div>"
        f"<div style='text-align:center;font-size:0.82rem;color:var(--orange);align-self:center;'>{diff_str}</div>"
        f"</div>{bars}</div>"
    )


def _render_decoupling_detail_card(metrics: dict, metric_jsons: dict) -> str:
    """Aerobic Decoupling 해석 카드 (EF + aerobic stability 판단)."""
    dec = metrics.get("AerobicDecoupling")
    mj = metric_jsons.get("AerobicDecoupling") or {}
    ef = mj.get("ef") or metrics.get("EF")
    grade = mj.get("grade", "")
    if dec is None and ef is None:
        return ""
    dec_f = float(dec) if dec is not None else None
    ef_f = float(ef) if ef is not None else None
    if dec_f is None:
        badge, badge_color = "—", "var(--muted)"
        comment = "랩 데이터 부족 — 분할 기록이 있을 경우 표시됩니다."
    elif grade == "good" or dec_f < 5.0:
        badge, badge_color = "&#128994; 양호 (Decoupling &lt;5%)", "var(--green)"
        comment = "전/후반 심박 효율이 잘 유지됨. 장거리 적합 유산소 베이스."
    elif grade == "moderate" or dec_f < 10.0:
        badge, badge_color = "&#128993; 보통 (5-10%)", "var(--orange)"
        comment = "후반 효율 소폭 저하. 기본 유산소 훈련 지속 권장."
    else:
        badge, badge_color = "&#128308; 낮음 (&gt;10%)", "var(--red)"
        comment = "후반 급격한 효율 저하. 유산소 베이스 강화 필요."
    dec_str = f"{dec_f:.1f}%" if dec_f is not None else "—"
    ef_str = f"{ef_f:.4f}" if ef_f is not None else "—"
    return (
        "<div class='card'><h2>유산소 디커플링 분석</h2>"
        "<div style='display:flex;gap:1.5rem;margin-bottom:0.5rem;'>"
        f"<div style='text-align:center;'><div style='font-size:1.5rem;font-weight:700;color:var(--cyan);'>{dec_str}</div>"
        f"<div class='muted' style='font-size:0.74rem;'>Decoupling</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.5rem;font-weight:700;'>{ef_str}</div>"
        f"<div class='muted' style='font-size:0.74rem;'>EF (m/min/bpm)</div></div>"
        "</div>"
        f"<div style='background:rgba(255,255,255,0.06);border-radius:10px;padding:0.5rem 0.7rem;margin-bottom:0.4rem;'>"
        f"<span style='color:{badge_color};font-size:0.84rem;'>{badge}</span></div>"
        f"<p style='font-size:0.8rem;color:var(--secondary);margin:0;'>{comment}</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>EF = NGP / avg_HR | Decoupling = (EF전반-EF후반)/EF전반 × 100</p>"
        "</div>"
    )


def _render_map_placeholder() -> str:
    """지도 플레이스홀더 (Mapbox 토큰 미설정 시 graceful fallback)."""
    return (
        "<div class='card' style='text-align:center;min-height:120px;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;'>"
        "<div style='font-size:2.5rem;margin-bottom:0.4rem;'>&#128506;</div>"
        "<h2 style='font-size:0.95rem;margin-bottom:0.3rem;'>활동 경로 지도</h2>"
        "<p class='muted' style='font-size:0.8rem;margin:0;'>Mapbox 토큰 설정 후 표시됩니다.</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.2rem;'>설정 → Mapbox 토큰 입력</p>"
        "</div>"
    )


# ── 라우트 ───────────────────────────────────────────────────────────────

@activity_bp.get("/activity/deep")
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
    try:
        with sqlite3.connect(str(dpath)) as conn:
            data = deep_analyze(conn, activity_id=activity_id, date=date_str or None)
            prev_row, next_row = None, None
            if data:
                # 실제 id/start_time은 deep_analyze 반환값에 없으므로 DB 재조회
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
                    service_metrics = _load_service_metrics(conn, cur[0])
                    act_date_tmp = str(cur[1])[:10]
                    day_metrics_data = _load_day_computed_metrics(conn, act_date_tmp)
                    act_metric_jsons = _load_activity_metric_jsons(conn, cur[0])
                    day_metric_jsons = _load_day_metric_jsons(conn, act_date_tmp)
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return render_template("generic_page.html", title="활동 심층 분석", body=body, active_tab="activities")

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
        + _render_secondary_metrics_card(act_metrics, day_metrics_data, service_metrics=service_metrics)
        + _render_daily_scores_card(day_metrics_data)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_fearp_breakdown_card(act_metric_jsons)
        + _render_decoupling_detail_card(act_metrics, act_metric_jsons)
        + "</div>"
        + "<div class='cards-row'>"
        + _render_di_card(day_metrics_data)
        + _render_map_placeholder()
        + "</div>"
        + _render_splits(splits)
    )

    title = f"활동 심층 분석 — {act_date}"
    return render_template("generic_page.html", title=title, body=body, active_tab="activities")
