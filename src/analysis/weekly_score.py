"""주간 Training Quality Score (0-100) 종합 계산."""

import json
import sqlite3
from datetime import date, timedelta

from .recovery import get_recovery_status
from .trends import calculate_acwr


def _week_start(d: date) -> date:
    """월요일 기준 주 시작일."""
    return d - timedelta(days=d.weekday())


# ── 개별 점수 계산 함수 (각 항목 만점 기준) ────────────────────────────

def _volume_score(total_km: float, target_km: float) -> float:
    """볼륨 점수 (25점): 목표 대비 90-110%면 만점, 초과/미달 시 감점."""
    if target_km <= 0:
        return 0.0
    ratio = total_km / target_km
    if 0.9 <= ratio <= 1.1:
        return 25.0
    if ratio < 0.9:
        return round(ratio / 0.9 * 25.0, 1)
    # 110% 초과: 과훈련 감점
    over = ratio - 1.1
    return round(max(0.0, 25.0 - over * 50.0), 1)


def _intensity_score(easy_ratio: float | None) -> float:
    """강도 점수 (20점): Easy 비율 75-85%면 만점."""
    if easy_ratio is None:
        return 10.0  # 데이터 없으면 중간값
    if 0.75 <= easy_ratio <= 0.85:
        return 20.0
    if easy_ratio < 0.75:
        return round(easy_ratio / 0.75 * 20.0, 1)
    over = easy_ratio - 0.85
    return round(max(0.0, 20.0 - over * 100.0), 1)


def _acwr_score(acwr: float | None) -> float:
    """ACWR 점수 (20점): 0.8-1.3 범위면 만점."""
    if acwr is None:
        return 10.0
    if 0.8 <= acwr <= 1.3:
        return 20.0
    if acwr < 0.8:
        return round(acwr / 0.8 * 20.0, 1)
    over = acwr - 1.3
    return round(max(0.0, 20.0 - over * 40.0), 1)


def _recovery_comp_score(recovery_avg: float | None) -> float:
    """회복 점수 (15점): 평균 회복 점수 80+이면 만점."""
    if recovery_avg is None:
        return 7.5
    return round(min(15.0, recovery_avg / 80.0 * 15.0), 1)


def _consistency_score(actual: int, planned: int) -> float:
    """일관성 점수 (10점): 계획 대비 실제 러닝일 비율."""
    if planned == 0:
        return 5.0
    ratio = min(1.0, actual / planned)
    return round(ratio * 10.0, 1)


def _efficiency_score(
    avg_hr: int | None, avg_pace: int | None,
    prev_hr: int | None, prev_pace: int | None,
) -> float:
    """효율성 점수 (10점): 페이스/HR 비율의 전주 대비 개선."""
    if avg_hr is None or avg_pace is None or avg_hr == 0:
        return 5.0
    if prev_hr is None or prev_pace is None or prev_hr == 0:
        return 5.0
    curr_ef = avg_pace / avg_hr   # sec/km per bpm (낮을수록 효율 좋음)
    prev_ef = prev_pace / prev_hr
    if prev_ef == 0:
        return 5.0
    improvement = (prev_ef - curr_ef) / prev_ef  # 양수 = 개선
    if improvement >= 0:
        return 10.0
    return round(max(0.0, 10.0 + improvement * 50.0), 1)


# ── 보조 데이터 수집 ────────────────────────────────────────────────────

def _get_week_basics(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """주간 기본 집계 (중복 제거)."""
    rows = conn.execute("""
        SELECT COALESCE(matched_group_id, CAST(id AS TEXT)) AS gk,
               AVG(distance_km)     AS dist,
               AVG(avg_pace_sec_km) AS pace,
               AVG(avg_hr)          AS hr
        FROM activity_summaries
        WHERE start_time >= ? AND start_time < ?
          AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        GROUP BY gk
    """, (start, end)).fetchall()

    total_dist = round(sum(r[1] or 0 for r in rows), 2)
    paces = [r[2] for r in rows if r[2] is not None]
    hrs = [r[3] for r in rows if r[3] is not None]
    return dict(
        run_count=len(rows),
        total_distance_km=total_dist,
        avg_pace_sec_km=round(sum(paces) / len(paces)) if paces else None,
        avg_hr=round(sum(hrs) / len(hrs)) if hrs else None,
    )


def _get_easy_ratio(conn: sqlite3.Connection, start: str, end: str) -> float | None:
    """HR Zone 기반 Easy 비율 계산 (intervals zone 데이터 우선, 없으면 HR 추정)."""
    # intervals hr_zone_distribution JSON 활용
    rows = conn.execute("""
        SELECT sm.metric_json
        FROM activity_detail_metrics sm
        JOIN activity_summaries a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
          AND sm.source = 'intervals'
          AND sm.metric_name = 'hr_zone_distribution'
          AND sm.metric_json IS NOT NULL
    """, (start, end)).fetchall()

    if rows:
        total_time = 0
        easy_time = 0
        for (json_str,) in rows:
            try:
                zones = json.loads(json_str)
                for z, t in zones.items():
                    total_time += t
                    if str(z).lower() in ("z1", "z2", "zone1", "zone2", "1", "2"):
                        easy_time += t
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
        if total_time > 0:
            return round(easy_time / total_time, 3)

    # intervals 데이터 없으면 평균 HR로 Easy 비율 추정
    row = conn.execute("""
        SELECT AVG(avg_hr), MAX(max_hr)
        FROM activity_summaries
        WHERE start_time >= ? AND start_time < ?
          AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
          AND avg_hr IS NOT NULL
    """, (start, end)).fetchone()

    if row[0] is None:
        return None

    avg_hr, max_hr = row
    personal_max = (max_hr * 1.2) if max_hr else 180.0
    hr_ratio = avg_hr / personal_max
    # hr_ratio 65% 이하 = 대부분 Easy, 75% 이상 = 강도 높음
    if hr_ratio <= 0.65:
        return 0.85
    if hr_ratio >= 0.75:
        return 0.65
    return round(0.85 - (hr_ratio - 0.65) / 0.10 * 0.20, 3)


def _get_week_recovery_avg(conn: sqlite3.Connection, start: str, end: str) -> float | None:
    """주간 평균 회복 점수."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    scores = []
    d = start_date
    while d < end_date:
        status = get_recovery_status(conn, d.isoformat())
        if status["recovery_score"] is not None:
            scores.append(status["recovery_score"])
        d += timedelta(days=1)
    return round(sum(scores) / len(scores), 1) if scores else None


# ── 공개 API ───────────────────────────────────────────────────────────

def calculate_weekly_score(
    conn: sqlite3.Connection,
    week_start: str | None = None,
    config: dict | None = None,
) -> dict:
    """주간 Training Quality Score 계산 (0-100).

    Args:
        conn: SQLite 연결.
        week_start: 주 시작일 (ISO, 월요일). None이면 이번 주.
        config: 설정 딕셔너리. None이면 config.json을 로드.

    Returns:
        {"week_start", "total_score", "grade" (A-F),
         "components": {volume, intensity, acwr, recovery, consistency, efficiency},
         "data": {raw metrics}}
    """
    if config is None:
        from src.utils.config import load_config
        config = load_config()

    target_km = config.get("user", {}).get("weekly_distance_target", 40.0)

    # 주 범위 설정
    if week_start:
        wk_start = date.fromisoformat(week_start)
    else:
        wk_start = _week_start(date.today())
    wk_end = wk_start + timedelta(weeks=1)
    prev_start = wk_start - timedelta(weeks=1)

    start_str = wk_start.isoformat()
    end_str = wk_end.isoformat()
    prev_str = prev_start.isoformat()

    # 기본 지표
    basics = _get_week_basics(conn, start_str, end_str)
    prev_basics = _get_week_basics(conn, prev_str, start_str)

    # 계획된 운동일 (없으면 주 4회 기준)
    planned_row = conn.execute("""
        SELECT COUNT(*) FROM planned_workouts
        WHERE date >= ? AND date < ? AND workout_type != 'rest'
    """, (start_str, end_str)).fetchone()
    planned_count = (planned_row[0] or 0) if planned_row else 0
    if planned_count == 0:
        planned_count = 4

    # 보조 지표
    easy_ratio = _get_easy_ratio(conn, start_str, end_str)
    acwr_result = calculate_acwr(conn)
    avg_acwr = (
        acwr_result["average"]["acwr"]
        if acwr_result and "average" in acwr_result
        else None
    )
    recovery_avg = _get_week_recovery_avg(conn, start_str, end_str)

    # 점수 계산
    v_score = _volume_score(basics["total_distance_km"], target_km)
    i_score = _intensity_score(easy_ratio)
    a_score = _acwr_score(avg_acwr)
    r_score = _recovery_comp_score(recovery_avg)
    c_score = _consistency_score(basics["run_count"], planned_count)
    e_score = _efficiency_score(
        basics["avg_hr"], basics["avg_pace_sec_km"],
        prev_basics["avg_hr"], prev_basics["avg_pace_sec_km"],
    )

    total = round(v_score + i_score + a_score + r_score + c_score + e_score, 1)

    if total >= 85:
        grade = "A"
    elif total >= 70:
        grade = "B"
    elif total >= 55:
        grade = "C"
    elif total >= 40:
        grade = "D"
    else:
        grade = "F"

    return dict(
        week_start=start_str,
        total_score=total,
        grade=grade,
        components=dict(
            volume=v_score,
            intensity=i_score,
            acwr=a_score,
            recovery=r_score,
            consistency=c_score,
            efficiency=e_score,
        ),
        data=dict(
            total_distance_km=basics["total_distance_km"],
            run_count=basics["run_count"],
            avg_pace_sec_km=basics["avg_pace_sec_km"],
            avg_hr=basics["avg_hr"],
            easy_ratio=easy_ratio,
            acwr=avg_acwr,
            recovery_avg=recovery_avg,
            planned_count=planned_count,
            weekly_distance_target=target_km,
        ),
    )
