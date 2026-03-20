"""마크다운 리포트 생성."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any

from .activity_deep import deep_analyze
from .compare import compare_this_month_vs_last, compare_this_week_vs_last, compare_today_vs_yesterday
from .race_readiness import assess_race_readiness
from .trends import weekly_trends
from .weekly_score import calculate_weekly_score
from .zones_analysis import analyze_zones


def _today_iso() -> str:
    return date.today().isoformat()


def _safe(value, default="-"):
    return default if value is None else value


def _fmt_distance_km(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _fmt_duration(value):
    if value is None:
        return "-"
    try:
        total = int(value)
    except Exception:
        return str(value)

    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _fmt_zone_entry(value):
    if value in (None, "", [], {}):
        return "-"
    if isinstance(value, dict):
        label = value.get("label")
        pct = value.get("pct")
        seconds = value.get("seconds")
        parts = []
        if label:
            parts.append(str(label))
        if pct is not None:
            parts.append(f"{pct}%")
        if seconds is not None:
            parts.append(f"({seconds}s)")
        if parts:
            return " ".join(parts)
    return str(value)


def _pad_mmss_like(text: str) -> str:
    import re

    def repl(match):
        return f"{match.group(1)}m{int(match.group(2)):02d}s"

    return re.sub(r"(\d+)m(\d+)s", repl, text)


def _fmt_interval_token(value) -> str:
    if value in (None, "", [], {}):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    lower = text.lower()
    if lower.endswith("w"):
        core = text[:-1].strip()
        if core:
            return f"{core}W"
    if lower.endswith("x") and text[:-1].strip().isdigit():
        return f"{text[:-1].strip()}회"
    return _pad_mmss_like(text)


def _latest_activity_id(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT id
        FROM activity_summaries
        WHERE activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        ORDER BY start_time DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0] if row else None


def _latest_activity_date(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT substr(start_time, 1, 10)
        FROM activity_summaries
        WHERE activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        ORDER BY start_time DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0] if row else None



def _get_daily_detail_metrics(conn: sqlite3.Connection, date_str: str, source: str = "garmin") -> dict:
    rows = conn.execute(
        "SELECT metric_name, metric_value, metric_json "
        "FROM daily_detail_metrics WHERE date = ? AND source = ?",
        (date_str, source),
    ).fetchall()
    result = {}
    for name, val, js in rows:
        result[name] = js if val is None else val
    return result

def _has_any_activity(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM activity_summaries
        WHERE activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        """
    ).fetchone()
    return bool(row and row[0])


def _basic_today_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 기본 정보\n\n오늘 활동이 없습니다."

    data = deep_analyze(conn, activity_id=activity_id)
    if not data:
        return "## 기본 정보\n\n오늘 활동이 없습니다."

    activity = data.get("activity") or {}
    lines = [
        "## 기본 정보",
        "",
        f"- 날짜: {_safe(activity.get('date'))}",
        f"- 거리: {_fmt_distance_km(activity.get('distance_km'))} km",
        f"- 시간: {_fmt_duration(activity.get('duration_sec'))}",
        f"- 평균 페이스: {_safe(activity.get('avg_pace'))}",
        f"- 평균 심박: {_safe(activity.get('avg_hr'))}",
    ]
    return "\n".join(lines)


def _source_metrics_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 소스 메트릭\n\n- 데이터 없음"

    data = deep_analyze(conn, activity_id=activity_id) or {}
    garmin = data.get("garmin") or {}
    strava = data.get("strava") or {}
    intervals = data.get("intervals") or {}
    runalyze = data.get("runalyze") or {}

    lines = [
        "## 소스 메트릭",
        "",
        f"- Garmin Training Effect: {_safe(garmin.get('training_effect_aerobic'))}",
        f"- Strava Suffer Score: {_safe(strava.get('suffer_score'))}",
        f"- Intervals Training Load: {_safe(intervals.get('icu_training_load'))}",
        f"- Runalyze VO2Max: {_safe(runalyze.get('effective_vo2max'))}",
        f"- Runalyze VDOT: {_safe(runalyze.get('vdot'))}",
    ]
    return "\n".join(lines)


def _decode_interval_summary(raw: Any):
    if raw in (None, "", [], {}):
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return raw
    return raw


def _format_interval_piece(item: dict) -> str:
    if not isinstance(item, dict):
        return _fmt_interval_token(item)

    labels = []
    kind = item.get("type") or item.get("kind") or item.get("label") or item.get("name")
    if kind:
        labels.append(str(kind))

    reps = item.get("reps") or item.get("repeat") or item.get("count")
    if reps not in (None, ""):
        labels.append(f"{reps}회")

    duration = (
        item.get("duration")
        or item.get("seconds")
        or item.get("secs")
        or item.get("time")
        or item.get("workDuration")
        or item.get("recoverDuration")
    )
    if duration not in (None, ""):
        try:
            duration = int(duration)
            minutes, seconds = divmod(duration, 60)
            if minutes:
                labels.append(f"{minutes}m{seconds:02d}s")
            else:
                labels.append(f"{seconds}s")
        except Exception:
            labels.append(_fmt_interval_token(duration))

    distance = (
        item.get("distance")
        or item.get("meters")
        or item.get("metres")
        or item.get("length")
    )
    if distance not in (None, ""):
        try:
            dist_value = float(distance)
            if dist_value >= 1000:
                labels.append(f"{dist_value/1000:.2f}km")
            else:
                labels.append(f"{int(dist_value)}m")
        except Exception:
            labels.append(f"{distance}m")

    pace = item.get("pace") or item.get("target_pace") or item.get("avg_pace")
    if pace not in (None, ""):
        labels.append(f"pace {pace}")

    hr = item.get("hr") or item.get("avg_hr") or item.get("target_hr")
    if hr not in (None, ""):
        labels.append(f"HR {hr}")

    power = item.get("power") or item.get("avg_power") or item.get("target_power")
    if power not in (None, ""):
        labels.append(f"{power}W")

    return " / ".join(labels) if labels else json.dumps(item, ensure_ascii=False)


def _intervals_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 인터벌 요약\n\n- 데이터 없음"

    data = deep_analyze(conn, activity_id=activity_id) or {}
    intervals = (data.get("intervals") or {}).get("interval_summary")
    parsed = _decode_interval_summary(intervals)

    if not parsed:
        return "## 인터벌 요약\n\n- 데이터 없음"

    lines = [
        "## 인터벌 요약",
        "",
    ]

    if isinstance(parsed, str):
        pretty = " ".join(_fmt_interval_token(part) for part in str(parsed).split())
        lines.append(f"- {pretty}".rstrip())
        return "\n".join(lines)

    if isinstance(parsed, dict):
        summary_keys = [
            ("type", "유형"),
            ("name", "이름"),
            ("reps", "반복"),
            ("count", "개수"),
            ("work", "메인"),
            ("recovery", "회복"),
            ("duration", "시간"),
            ("distance", "거리"),
        ]
        added = 0
        for key, label in summary_keys:
            value = parsed.get(key)
            if value not in (None, "", [], {}):
                lines.append(f"- {label}: {value}")
                added += 1

        blocks = (
            parsed.get("intervals")
            or parsed.get("steps")
            or parsed.get("sets")
            or parsed.get("repeats")
            or parsed.get("summary")
        )
        if isinstance(blocks, list) and blocks:
            for idx, item in enumerate(blocks[:12], 1):
                lines.append(f"- #{idx}: {_format_interval_piece(item)}")
            if len(blocks) > 12:
                lines.append(f"- ... 총 {len(blocks)}개 구간")
            return "\n".join(lines)

        if added == 0:
            lines.append(f"- {json.dumps(parsed, ensure_ascii=False)}")
        return "\n".join(lines)

    if isinstance(parsed, list):
        for idx, item in enumerate(parsed[:12], 1):
            if isinstance(item, dict):
                lines.append(f"- #{idx}: {_format_interval_piece(item)}")
            else:
                pretty = " ".join(_fmt_interval_token(part) for part in str(item).split())
                lines.append(f"- #{idx}: {pretty}".rstrip())
        if len(parsed) > 12:
            lines.append(f"- ... 총 {len(parsed)}개 구간")
        return "\n".join(lines)

    lines.append(f"- {parsed}")
    return "\n".join(lines)


def _splits_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 페이스 스플릿\n\n- 데이터 없음"

    data = deep_analyze(conn, activity_id=activity_id) or {}
    splits = data.get("pace_splits") or []
    if not splits:
        return "## 페이스 스플릿\n\n- 데이터 없음"

    lines = [
        "## 페이스 스플릿",
        "",
        "| km | pace_sec_km |",
        "|---:|------------:|",
    ]
    for idx, item in enumerate(splits, 1):
        lines.append(f"| {idx} | {_safe(item.get('pace_sec_km'))} |")
    return "\n".join(lines)


def _efficiency_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 효율\n\n- 데이터 없음"

    data = deep_analyze(conn, activity_id=activity_id) or {}
    eff = (data.get("calculated") or {}).get("efficiency") or {}
    if not eff:
        return "## 효율\n\n- 데이터 없음"

    lines = [
        "## 효율",
        "",
        f"- EF: {_safe(eff.get('ef'))}",
        f"- Decoupling: {_safe(eff.get('decoupling_pct'))}",
        f"- 상태: {_safe(eff.get('status'))}",
    ]
    return "\n".join(lines)


def _zones_section(conn: sqlite3.Connection) -> str:
    activity_id = _latest_activity_id(conn)
    if not activity_id:
        return "## 존 분포\n\n- 데이터 없음"

    data = deep_analyze(conn, activity_id=activity_id) or {}
    zones = (data.get("calculated") or {}).get("zones") or {}
    dist = zones.get("zone_distribution") or {}
    if not dist:
        return "## 존 분포\n\n- 데이터 없음"

    lines = [
        "## 존 분포",
        "",
        f"- Z1: {_fmt_zone_entry(dist.get('z1'))}",
        f"- Z2: {_fmt_zone_entry(dist.get('z2'))}",
        f"- Z3: {_fmt_zone_entry(dist.get('z3'))}",
        f"- Z4: {_fmt_zone_entry(dist.get('z4'))}",
        f"- Z5: {_fmt_zone_entry(dist.get('z5'))}",
        f"- 상태: {_safe(zones.get('polarization_status'))}",
    ]
    return "\n".join(lines)


def _condition_section(conn: sqlite3.Connection) -> str:
    readiness = assess_race_readiness(conn)
    lines = [
        "## 컨디션",
        "",
        f"- 상태: {_safe(readiness.get('status'))}",
        f"- 준비도 점수: {_safe(readiness.get('readiness_score'))}",
        f"- 등급: {_safe(readiness.get('grade'))}",
    ]
    warning = readiness.get("warning")
    if warning:
        lines.append(f"- 안내: {warning}")
    return "\n".join(lines)


def _wellness_visibility_section(conn: sqlite3.Connection) -> str:
    activity_date = _latest_activity_date(conn)
    if not activity_date:
        return "## 웰니스 참고\n\n- 데이터 없음"

    row = conn.execute(
        """
        SELECT steps, weight_kg, sleep_score, sleep_hours, hrv_value, resting_hr
        FROM daily_wellness
        WHERE date = ? AND source = 'intervals'
        ORDER BY id DESC
        LIMIT 1
        """,
        (activity_date,),
    ).fetchone()

    steps = weight_kg = sleep_score = sleep_hours = hrv_value = resting_hr = None
    detail = _get_daily_detail_metrics(conn, activity_date, source="garmin")
    if row:
        steps, weight_kg, sleep_score, sleep_hours, hrv_value, resting_hr = row

    if steps is None or weight_kg is None:
        payload_row = conn.execute(
            """
            SELECT payload_json
            FROM raw_source_payloads
            WHERE source = 'intervals' AND entity_type = 'wellness' AND entity_id = ?
            LIMIT 1
            """,
            (activity_date,),
        ).fetchone()

        if payload_row and payload_row[0]:
            try:
                payload = json.loads(payload_row[0])
            except Exception:
                payload = {}
            if steps is None:
                steps = payload.get("steps")
            if weight_kg is None:
                weight_kg = payload.get("weight")
            if sleep_score is None:
                sleep_score = payload.get("sleepQuality")
            if sleep_hours is None:
                sleep_secs = payload.get("sleepSecs")
                sleep_hours = sleep_secs / 3600 if sleep_secs else None
            if hrv_value is None:
                hrv_value = payload.get("hrv")
            if resting_hr is None:
                resting_hr = payload.get("restingHR")

    if all(v is None for v in [steps, weight_kg, sleep_score, sleep_hours, hrv_value, resting_hr]) and not detail:
        return "## 웰니스 참고\n\n- 데이터 없음"

    lines = [
        "## 웰니스 참고",
        "",
        f"- 걸음 수: {_safe(steps)}",
        f"- 체중: {_safe(weight_kg)}",
        f"- 수면 점수: {_safe(sleep_score)}",
        f"- 수면 시간: {_safe(sleep_hours)}",
        f"- HRV: {_safe(hrv_value)}",
        f"- 안정시 심박: {_safe(resting_hr)}",
    ]

    detail_lines = [
        ("Garmin deep sleep(s)", detail.get("sleep_stage_deep_sec")),
        ("Garmin REM sleep(s)", detail.get("sleep_stage_rem_sec")),
        ("Garmin overnight HRV", detail.get("overnight_hrv_avg")),
        ("Garmin overnight HRV SDNN", detail.get("overnight_hrv_sdnn")),
        ("Garmin body battery delta", detail.get("body_battery_delta")),
        ("Garmin stress high duration(s)", detail.get("stress_high_duration")),
        ("Garmin respiration avg", detail.get("respiration_avg")),
        ("Garmin SpO2 avg", detail.get("spo2_avg")),
        ("Garmin training readiness", detail.get("training_readiness_score")),
    ]
    for label, value in detail_lines:
        if value is not None:
            lines.append(f"- {label}: {value}")

    return "\n".join(lines)


def _fitness_section(conn: sqlite3.Connection) -> str:
    try:
        weekly = calculate_weekly_score(conn)
    except Exception:
        weekly = None

    if not weekly:
        return "## 피트니스\n\n- 데이터 없음"

    lines = [
        "## 피트니스",
        "",
        f"- 주간 점수: {_safe(weekly.get('total_score'))}",
        f"- 등급: {_safe(weekly.get('grade'))}",
        f"- 거리: {_safe((weekly.get('data') or {}).get('total_distance_km'))} km",
        f"- 런 횟수: {_safe((weekly.get('data') or {}).get('run_count'))}",
    ]
    return "\n".join(lines)


def _race_section(conn: sqlite3.Connection, config=None) -> str:
    target_date = None
    target_distance = None
    if config:
        user = config.get("user", {})
        target_date = user.get("race_date")
        target_distance = user.get("race_distance_km")

    readiness = assess_race_readiness(conn, race_date=target_date, race_distance_km=target_distance, config=config)

    lines = [
        "# 레이스 준비도 리포트",
        "",
        f"- 레이스 날짜: {_safe(readiness.get('race_date'))}",
        f"- 레이스 거리(km): {_safe(readiness.get('race_distance_km'))}",
        f"- D-day: {_safe(readiness.get('days_to_race'))}",
        f"- 상태: {_safe(readiness.get('status'))}",
    ]

    if readiness.get("status") == "insufficient_data":
        lines.extend(
            [
                "",
                "## 안내",
                "",
                readiness.get("warning") or "충분한 데이터가 쌓이지 않았습니다.",
                "",
                "## 권장 사항",
                "",
                readiness.get("recommendation") or "최근 3~4주 이상 데이터를 누적한 뒤 다시 확인해 주세요.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"- 준비도 점수: {_safe(readiness.get('readiness_score'))}",
            f"- 등급: {_safe(readiness.get('grade'))}",
            "",
            "## 점수 구성",
            "",
        ]
    )

    for key, value in (readiness.get("scores") or {}).items():
        lines.append(f"- {key}: {_safe(value)}")

    lines.extend(
        [
            "",
            "## 예측 기록",
            "",
        ]
    )

    preds = readiness.get("race_predictions") or {}
    if preds:
        for key in ["5k", "10k", "half", "full"]:
            if key in preds:
                lines.append(f"- {key}: {preds[key]} 초")
    else:
        lines.append("- 예측 데이터 없음")

    lines.extend(
        [
            "",
            "## 권장 사항",
            "",
            readiness.get("recommendation") or "-",
        ]
    )

    return "\n".join(lines)


def _today_report(conn: sqlite3.Connection, config=None) -> str:
    if not _has_any_activity(conn):
        return "오늘 활동이 없습니다."

    sections = [
        "# 오늘 리포트",
        "",
        _basic_today_section(conn),
        "",
        _source_metrics_section(conn),
        "",
        _splits_section(conn),
        "",
        _intervals_section(conn),
        "",
        _efficiency_section(conn),
        "",
        _zones_section(conn),
        "",
        _condition_section(conn),
        "",
        _wellness_visibility_section(conn),
        "",
        _fitness_section(conn),
    ]
    return "\n".join(sections)


def _week_report(conn: sqlite3.Connection) -> str:
    compare = compare_this_week_vs_last(conn)
    weekly = calculate_weekly_score(conn)

    lines = [
        "# 주간 리포트",
        "",
        "## 주간 비교",
        "",
        f"- 이번 주 거리: {_safe((compare.get('period2') or {}).get('total_distance_km'))} km",
        f"- 지난 주 거리: {_safe((compare.get('period1') or {}).get('total_distance_km'))} km",
        f"- 변화율: {_safe((compare.get('pct') or {}).get('total_distance_km'))} %",
        "",
        "## 주간 점수",
        "",
        f"- 점수: {_safe(weekly.get('total_score'))}",
        f"- 등급: {_safe(weekly.get('grade'))}",
    ]
    return "\n".join(lines)


def _month_report(conn: sqlite3.Connection) -> str:
    compare = compare_this_month_vs_last(conn)

    lines = [
        "# 월간 리포트",
        "",
        "## 월간 비교",
        "",
        f"- 이번 달 거리: {_safe((compare.get('period2') or {}).get('total_distance_km'))} km",
        f"- 지난 달 거리: {_safe((compare.get('period1') or {}).get('total_distance_km'))} km",
        f"- 변화율: {_safe((compare.get('pct') or {}).get('total_distance_km'))} %",
    ]
    return "\n".join(lines)


def _full_report(conn: sqlite3.Connection, config=None) -> str:
    if not _has_any_activity(conn):
        return "오늘 활동이 없습니다."

    sections = [
        "# 전체 리포트",
        "",
        _today_report(conn, config=config),
        "",
        _week_report(conn),
        "",
        _month_report(conn),
        "",
        _race_section(conn, config=config),
    ]
    return "\n".join(sections)


def generate_report(conn: sqlite3.Connection, report_type="today", config=None) -> str:
    report_type = (report_type or "today").lower()

    if report_type == "today":
        return _today_report(conn, config=config)
    if report_type == "week":
        return _week_report(conn)
    if report_type == "month":
        return _month_report(conn)
    if report_type == "race":
        return _race_section(conn, config=config)
    if report_type == "full":
        return _full_report(conn, config=config)

    return _today_report(conn, config=config)


def generate_ai_context(conn: sqlite3.Connection, context_type="brief", config=None) -> str:
    readiness = assess_race_readiness(conn, config=config)
    weekly = None
    try:
        weekly = calculate_weekly_score(conn)
    except Exception:
        weekly = None

    if readiness.get("status") == "insufficient_data":
        return (
            "[AI_CONTEXT] "
            f"[race_status=insufficient_data] "
            f"[warning={readiness.get('warning')}] "
            f"[recommendation={readiness.get('recommendation')}]"
        )

    return (
        "[AI_CONTEXT] "
        f"[race_status={readiness.get('status')}] "
        f"[readiness_score={readiness.get('readiness_score')}] "
        f"[grade={readiness.get('grade')}] "
        f"[weekly_score={_safe((weekly or {}).get('total_score'))}] "
        f"[recommendation={readiness.get('recommendation')}]"
    )
