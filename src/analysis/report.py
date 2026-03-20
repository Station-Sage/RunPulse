"""마크다운 리포트 생성."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

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


def _latest_activity_id(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT id
        FROM activities
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
        FROM activities
        WHERE activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        ORDER BY start_time DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0] if row else None


def _has_any_activity(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM activities
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
        f"- 날짜: {_safe(activity.get('start_time'))}",
        f"- 거리: {_safe(activity.get('distance_km'))} km",
        f"- 시간: {_safe(activity.get('duration_sec'))} 초",
        f"- 평균 페이스: {_safe(activity.get('avg_pace_sec_km'))} sec/km",
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
    eff = data.get("efficiency") or {}
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
    latest_date = _latest_activity_date(conn)
    if not latest_date:
        return "## 존 분포\n\n- 데이터 없음"

    zones = analyze_zones(conn, latest_date, latest_date) or {}
    dist = zones.get("zone_distribution") or {}
    if not dist:
        return "## 존 분포\n\n- 데이터 없음"

    lines = [
        "## 존 분포",
        "",
        f"- Z1: {_safe(dist.get('z1'))}",
        f"- Z2: {_safe(dist.get('z2'))}",
        f"- Z3: {_safe(dist.get('z3'))}",
        f"- Z4: {_safe(dist.get('z4'))}",
        f"- Z5: {_safe(dist.get('z5'))}",
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
        _efficiency_section(conn),
        "",
        _zones_section(conn),
        "",
        _condition_section(conn),
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
