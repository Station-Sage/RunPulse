"""공용 피로도·컨디션 판정 — wellness(Body Battery/수면/스트레스) + TSB 결합.

adjuster.py(당일 계획 조정)와 today_service.py(Today 브리핑)가 서로 다른 판정 로직을
쓰던 문제(10-today/design.md §4, "Today는 핵심 세션, Coach는 항상 휴식" 모순)를 없애기
위해 wellness+TSB 판정을 이 모듈 하나로 통합한다.

adjuster.py(계획 다운그레이드)와 ai/chat_readiness.py(Coach 채팅)도 `readiness_decision`을 그대로 호출한다.
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date

from src.metrics.bands import grade

# TSB 등급(src/metrics/bands.py) → 헤드라인. 피로도가 낮을 때(wellness 특이사항 없음)만 쓴다.
_TSB_HEADLINES: dict[str, str] = {
    "caution": "충분히 쉬었습니다 — 계획된 세션을 진행해 감각을 유지하세요.",
    "excellent": "컨디션이 좋습니다 — 계획된 세션을 그대로 진행해도 좋습니다.",
    "neutral": "정상적인 훈련 부하 구간입니다 — 평소대로 진행하세요.",
    "good": "훈련 부하가 쌓이는 구간입니다 — 계획대로 하되 회복을 챙기세요.",
    "poor": "피로가 과도합니다 — 완전 휴식이나 회복 위주 세션을 권합니다.",
}

# 피로도(wellness+TSB 결합)가 moderate/high면 TSB 등급과 무관하게 이 헤드라인을 우선한다.
_FATIGUE_HEADLINES: dict[str, str] = {
    "high": "피로가 과도합니다 — 완전 휴식이나 회복 위주 세션을 권합니다.",
    "moderate": "피로가 누적되고 있습니다 — 강도를 낮추고 회복을 우선하세요.",
}


def get_todays_wellness(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """지정 날짜(기본 오늘) Garmin 웰니스 데이터 조회."""
    target = date or _date.today().isoformat()
    row = conn.execute(
        "SELECT body_battery_high, sleep_score, sleep_duration_sec, hrv_last_night, avg_stress "
        "FROM daily_wellness WHERE date = ?",
        (target,),
    ).fetchone()
    if row:
        sleep_hours = row[2] / 3600.0 if row[2] else None
        return {
            "body_battery": row[0], "sleep_score": row[1],
            "sleep_hours": sleep_hours, "hrv_value": row[3], "stress_avg": row[4],
        }
    return {}


def get_latest_tsb(conn: sqlite3.Connection, date: str | None = None) -> float | None:
    """최근 TSB 조회 (metric_store daily). date 지정 시 그 날짜 이전의 최신 값."""
    if date is not None:
        row = conn.execute(
            "SELECT numeric_value FROM metric_store"
            " WHERE scope_type='daily' AND metric_name='tsb' AND is_primary=1"
            " AND scope_id <= ?"
            " ORDER BY scope_id DESC LIMIT 1",
            (date,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT numeric_value FROM metric_store"
            " WHERE scope_type='daily' AND metric_name='tsb' AND is_primary=1"
            " ORDER BY scope_id DESC LIMIT 1"
        ).fetchone()
    return row[0] if row else None


def fatigue_level(wellness: dict, tsb: float | None) -> str:
    """피로도 수준 판정.

    Returns:
        'high' | 'moderate' | 'low'
    """
    score = 0

    bb = wellness.get("body_battery")
    if bb is not None:
        if bb < 30:
            score += 2
        elif bb < 50:
            score += 1

    ss = wellness.get("sleep_score")
    if ss is not None:
        if ss < 40:
            score += 2
        elif ss < 60:
            score += 1

    stress = wellness.get("stress_avg")
    if stress is not None and stress > 75:
        score += 1

    if tsb is not None:
        if tsb < -25:
            score += 2
        elif tsb < -15:
            score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "moderate"
    return "low"


def readiness_decision(
    conn: sqlite3.Connection,
    date: str | None = None,
    tsb: float | None = None,
) -> dict:
    """오늘(또는 지정 날짜) 컨디션 판정 — wellness+TSB 결합, 한 줄 헤드라인 + 근거.

    Args:
        conn: SQLite 연결.
        date: 조회 날짜(ISO). None이면 오늘.
        tsb: 이미 조회된 TSB 값(호출부의 단일 소스 유지용). None이면 이 함수가
             get_latest_tsb()로 직접 조회한다(날짜 이전 최신값 폴백).

    Returns:
        {date, fatigue_level, tsb, wellness, headline, evidence}
    """
    target = date or _date.today().isoformat()
    wellness = get_todays_wellness(conn, date=date)
    if tsb is None:
        tsb = get_latest_tsb(conn, date=date)
    fatigue = fatigue_level(wellness, tsb)

    evidence: list[dict] = []
    if tsb is not None:
        g = grade("tsb", tsb)
        evidence.append({
            "type": "metric", "metric": "tsb", "value": tsb,
            "label": f"TSB {tsb:+.0f} ({g['label']})",
            "status": g["status"], "status_label": g["label"],
        })

    bb = wellness.get("body_battery")
    if bb is not None and bb < 50:
        evidence.append({"type": "wellness", "metric": "body_battery", "value": bb,
                         "label": f"Body Battery {bb}"})
    ss = wellness.get("sleep_score")
    if ss is not None and ss < 60:
        evidence.append({"type": "wellness", "metric": "sleep_score", "value": ss,
                         "label": f"수면 점수 {ss}"})

    if fatigue in _FATIGUE_HEADLINES:
        headline = _FATIGUE_HEADLINES[fatigue]
    elif tsb is None:
        headline = "아직 훈련 부하 데이터가 충분하지 않습니다 — 데이터 수집 중입니다."
    else:
        g = grade("tsb", tsb)
        headline = _TSB_HEADLINES[g["status"]]

    return {
        "date": target, "fatigue_level": fatigue, "tsb": tsb, "wellness": wellness,
        "headline": headline, "evidence": evidence,
    }
