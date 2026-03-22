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


def _load_day_computed_metrics(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 computed_metrics 조회 (activity_id IS NULL) → {metric_name: value}."""
    rows = conn.execute(
        """SELECT metric_name, metric_value FROM computed_metrics
           WHERE date = ? AND activity_id IS NULL""",
        (act_date,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


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


def _render_secondary_metrics_card(metrics: dict) -> str:
    """2차 메트릭 카드 (FEARP/GAP/NGP/RE/Decoupling/EF/TRIMP, V2-4-1~4)."""
    pairs = [
        ("FEARP (환경 보정 페이스)", metrics.get("FEARP"), "pace"),
        ("GAP (경사 보정 페이스)", metrics.get("GAP"), "pace"),
        ("NGP (정규화 경사 페이스)", metrics.get("NGP"), "pace"),
        ("Relative Effort", metrics.get("RelativeEffort"), "f0"),
        ("Aerobic Decoupling", metrics.get("Decoupling"), "f1%"),
        ("Efficiency Factor (EF)", metrics.get("EF"), "f4"),
        ("TRIMP", metrics.get("TRIMP"), "f1"),
    ]
    rows = []
    for label, val, fmt in pairs:
        if val is None:
            continue
        if fmt == "pace":
            val_str = f"{fmt_pace(val)}/km"
        elif fmt == "f0":
            val_str = f"{float(val):.0f}"
        elif fmt == "f1%":
            val_str = f"{float(val):.1f}%"
        elif fmt == "f4":
            val_str = f"{float(val):.4f}"
        else:
            val_str = f"{float(val):.1f}"
        rows.append(metric_row(label, val_str))

    if not rows:
        return (
            "<div class='card'>"
            "<h2>2차 메트릭</h2>"
            "<p class='muted' style='margin:0;'>메트릭 미계산 — 설정 → 재계산 실행 후 확인하세요.</p>"
            "</div>"
        )
    return "<div class='card'><h2>2차 메트릭</h2>" + "".join(rows) + "</div>"


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
                    act_date_tmp = str(cur[1])[:10]
                    day_metrics_data = _load_day_computed_metrics(conn, act_date_tmp)
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
        + _render_secondary_metrics_card(act_metrics)
        + _render_daily_scores_card(day_metrics_data)
        + "</div>"
        + _render_splits(splits)
    )

    title = f"활동 심층 분석 — {act_date}"
    return render_template("generic_page.html", title=title, body=body, active_tab="activities")
