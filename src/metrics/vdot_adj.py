"""VDOT_ADJ — 현재 체력 기반 VDOT 보정.

A안: Strava stream에서 역치 HR 구간(85~92%)의 실제 페이스 추출
B안: 연속 역치런(avg_hr 85~92%, 20~60분) 활동의 평균 페이스
C안: 전체 활동 HR-페이스 회귀 (기존, 최후 fallback)

추출한 역치 페이스 → Daniels T-pace 역산 → VDOT_ADJ

저장: computed_metrics (date, 'VDOT_ADJ', value, extra_json)
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric

log = logging.getLogger(__name__)


def _get_resting_hr(conn: sqlite3.Connection, target_date: str) -> float | None:
    """최근 7일 안정심박 중앙값 (웰니스 데이터)."""
    row = conn.execute(
        "SELECT resting_hr FROM daily_wellness "
        "WHERE source='garmin' AND resting_hr IS NOT NULL AND resting_hr > 30 "
        "AND date <= ? ORDER BY date DESC LIMIT 7",
        (target_date,),
    ).fetchall()
    if not row:
        return None
    vals = sorted([float(r[0]) for r in row])
    return vals[len(vals) // 2]  # 중앙값


def calc_and_save_vdot_adj(conn: sqlite3.Connection, target_date: str) -> float | None:
    """VDOT 보정 계산 후 저장.

    우선순위:
    A. Stream 기반 역치 페이스 (가장 정확)
    B. 연속 역치런 활동 평균 (stream 없을 때)
    C. HR-페이스 회귀 (최후 fallback)
    """
    td = date.fromisoformat(target_date)

    # 기본 VDOT
    base_row = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not base_row:
        return None
    vdot_base = float(base_row[0])

    import json as _json
    vdot_json = _json.loads(base_row[1]) if base_row[1] else {}

    from src.metrics.store import estimate_max_hr
    hr_max = estimate_max_hr(conn, target_date)

    # 레이스 경과 주 수 확인
    # Strava workout_type=1 = race (유일한 신뢰 가능 소스)
    # Garmin/Intervals에는 별도 레이스 필드 없음
    # 3개 소스 중 하나라도 레이스로 태그되어 있으면 레이스로 인정
    race_weeks_ago = None
    race_row = conn.execute(
        """SELECT DATE(start_time) FROM activity_summaries
           WHERE activity_type='running'
             AND (
               (source='strava' AND workout_type=1)
               OR (source='garmin' AND event_type='race')
               OR (source='intervals' AND event_type='race')
             )
             AND DATE(start_time) <= ?
           ORDER BY start_time DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if race_row:
        race_weeks_ago = (td - date.fromisoformat(race_row[0])).days / 7

    # 안정심박 조회 → Karvonen HRR 기반 역치 범위 (개인화)
    # References:
    #   Karvonen (1957): HRR = maxHR - restingHR, LT ≈ 75~85% HRR
    #   Daniels (2014): T-zone ≈ 88~92% maxHR ≈ 80~88% HRR
    resting_hr = _get_resting_hr(conn, target_date)
    if resting_hr and resting_hr > 30:
        hrr = hr_max - resting_hr
        hr_thresh_lo = resting_hr + hrr * 0.75   # LT 하한 (Karvonen 75%)
        hr_thresh_hi = resting_hr + hrr * 0.88   # LT 상한 (Daniels T-zone)
    else:
        # 안정심박 없으면 고정 %maxHR fallback
        hr_thresh_lo = hr_max * 0.85
        hr_thresh_hi = hr_max * 0.92
    start_12w = (td - timedelta(weeks=12)).isoformat()

    # A. Stream 기반 역치 페이스 추출
    threshold_pace, method, sample_count = _extract_threshold_from_streams(
        conn, target_date, start_12w, hr_thresh_lo, hr_thresh_hi)

    # B. 연속 역치런 fallback
    if threshold_pace is None:
        threshold_pace, sample_count = _extract_threshold_from_activities(
            conn, target_date, start_12w, hr_thresh_lo, hr_thresh_hi)
        if threshold_pace:
            method = "threshold_activities"

    # C. HR-페이스 회귀 fallback
    if threshold_pace is None:
        threshold_pace, sample_count = _extract_threshold_from_regression(
            conn, target_date, start_12w, hr_max)
        if threshold_pace:
            method = "hr_regression"

    if threshold_pace is None or threshold_pace < 120:
        save_metric(conn, target_date, "VDOT_ADJ", vdot_base,
                    extra_json={"vdot_base": vdot_base, "method": "none", "sample_count": 0})
        return vdot_base

    # 레이스 직후일수록 레이스 VDOT에서 역산한 T-pace를 블렌딩
    # stream 측정 threshold가 easy run HR 오염으로 느리게 나올 때 보정
    race_implied_t_pace = _vdot_to_t_pace(vdot_base)
    if race_implied_t_pace and race_weeks_ago is not None:
        # 4주 이내: 레이스 비중 60%, 8주까지: 40%, 이후: 0%
        race_weight = max(0.0, 0.6 - (race_weeks_ago / 8) * 0.6)
        threshold_pace = race_implied_t_pace * race_weight + threshold_pace * (1.0 - race_weight)
        method = f"{method}+race_blend({race_weight:.2f})"

    # 역치 페이스 → Daniels T-pace 역산 → VDOT
    vdot_adj = _t_pace_to_vdot(threshold_pace)
    if vdot_adj is None:
        vdot_adj = vdot_base

    # 보정 범위 — 레이스급 고강도 활동(avg_hr≥88% maxHR, ≥10km) 경과 시간에 따라 차등
    # 4주 이내: ±1% (레이스 직후, 거의 보정 없음)
    # 4~8주:   ±3%
    # 8주+:    ±7%
    if race_weeks_ago is not None and race_weeks_ago <= 4:
        max_correction = 0.01
    elif race_weeks_ago is not None and race_weeks_ago <= 8:
        max_correction = 0.03
    else:
        max_correction = 0.07
    if vdot_base > 0:
        ratio = vdot_adj / vdot_base
        lo = 1.0 - max_correction
        hi = 1.0 + max_correction
        if ratio < lo or ratio > hi:
            vdot_adj = round(vdot_base * max(lo, min(hi, ratio)), 1)

    vdot_adj = round(vdot_adj, 1)
    if vdot_adj < 15 or vdot_adj > 90:
        vdot_adj = vdot_base

    save_metric(conn, target_date, "VDOT_ADJ", vdot_adj, extra_json={
        "vdot_base": vdot_base,
        "threshold_pace_sec_km": round(threshold_pace, 1),
        "method": method,
        "sample_count": sample_count,
        "hr_threshold_range": f"{hr_thresh_lo:.0f}-{hr_thresh_hi:.0f}",
        "resting_hr": resting_hr,
        "hr_method": "karvonen" if resting_hr and resting_hr > 30 else "fixed_pct",
        "race_weeks_ago": round(race_weeks_ago, 1) if race_weeks_ago is not None else None,
        "max_correction_pct": round(max_correction * 100),
    })
    return vdot_adj


def _extract_threshold_from_streams(
    conn: sqlite3.Connection, target_date: str, start_date: str,
    hr_lo: float, hr_hi: float,
) -> tuple[float | None, str, int]:
    """Strava stream에서 HR 85~92% 구간의 평균 페이스 추출.

    Returns:
        (threshold_pace_sec_km, method, sample_count) 또는 (None, "", 0)
    """
    from src.analysis.efficiency import _get_stream_path, _load_stream

    # 최근 12주 활동 중 stream이 있는 것
    acts = conn.execute(
        "SELECT id FROM v_canonical_activities "
        "WHERE activity_type='running' AND distance_km >= 5 "
        "AND DATE(start_time) BETWEEN ? AND ? ORDER BY start_time DESC",
        (start_date, target_date),
    ).fetchall()

    all_threshold_speeds: list[float] = []  # m/s

    for (aid,) in acts:
        path = _get_stream_path(conn, aid)
        if not path:
            continue
        stream = _load_stream(path, conn=conn)
        if not stream:
            continue

        hr = stream.get("heartrate", [])
        vel = stream.get("velocity_smooth", [])
        if not hr or not vel:
            continue

        n = min(len(hr), len(vel))
        # HR 역치 구간(85~92%)의 속도 추출
        # HR 스파이크 제거: 전후 데이터 포인트 대비 급변(±30bpm) 제외
        threshold_speeds = []
        for i in range(n):
            h, v = hr[i], vel[i]
            if h is None or v is None or v <= 0.5:
                continue
            if not (hr_lo <= h <= hr_hi):
                continue
            # HR 스파이크 체크: 전후 값 대비 ±30bpm 급변이면 스킵
            if i > 0 and hr[i - 1] is not None and abs(h - hr[i - 1]) > 30:
                continue
            threshold_speeds.append(v)
        all_threshold_speeds.extend(threshold_speeds)

    if len(all_threshold_speeds) < 30:  # 최소 30초 이상의 역치 데이터
        return None, "", 0

    # 평균 속도(m/s) → 페이스(sec/km) 변환
    avg_speed = sum(all_threshold_speeds) / len(all_threshold_speeds)
    if avg_speed <= 0:
        return None, "", 0
    threshold_pace = 1000.0 / avg_speed  # sec/km

    return threshold_pace, "stream_threshold", len(all_threshold_speeds)


def _extract_threshold_from_activities(
    conn: sqlite3.Connection, target_date: str, start_date: str,
    hr_lo: float, hr_hi: float,
) -> tuple[float | None, int]:
    """연속 역치런(avg_hr 85~92%, 20~60분) 활동의 평균 페이스.

    인터벌 세션은 avg_hr이 이 범위 밖이므로 자동 제외.
    """
    rows = conn.execute(
        "SELECT avg_pace_sec_km FROM v_canonical_activities "
        "WHERE activity_type='running' "
        "AND avg_hr BETWEEN ? AND ? "
        "AND duration_sec BETWEEN 1200 AND 3600 "
        "AND avg_pace_sec_km > 180 "
        "AND DATE(start_time) BETWEEN ? AND ?",
        (hr_lo, hr_hi, start_date, target_date),
    ).fetchall()

    if len(rows) < 3:  # 최소 3개 역치런
        return None, 0

    paces = sorted([float(r[0]) for r in rows])
    # 이상치 제거: 중앙 50% 사용
    q1 = len(paces) // 4
    q3 = len(paces) * 3 // 4
    trimmed = paces[q1:q3 + 1] if q3 > q1 else paces
    avg_pace = sum(trimmed) / len(trimmed) if trimmed else None

    return avg_pace, len(rows)


def _extract_threshold_from_regression(
    conn: sqlite3.Connection, target_date: str, start_date: str,
    hr_max: float,
) -> tuple[float | None, int]:
    """전체 활동 HR-페이스 회귀 → HR 88%에서 예측 (최후 fallback)."""
    rows = conn.execute(
        "SELECT avg_hr, avg_pace_sec_km FROM v_canonical_activities "
        "WHERE activity_type='running' AND avg_hr IS NOT NULL AND avg_hr > 100 "
        "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180 "
        "AND distance_km >= 3 AND DATE(start_time) BETWEEN ? AND ?",
        (start_date, target_date),
    ).fetchall()

    if len(rows) < 5:
        return None, 0

    hrs = [float(r[0]) for r in rows]
    paces = [float(r[1]) for r in rows]

    # 선형 회귀
    n = len(hrs)
    sx = sum(hrs)
    sy = sum(paces)
    sxx = sum(h * h for h in hrs)
    sxy = sum(h * p for h, p in zip(hrs, paces))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-10:
        return None, 0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    predicted_pace = slope * (hr_max * 0.88) + intercept
    return (predicted_pace, len(rows)) if predicted_pace > 120 else (None, 0)


def _vdot_to_t_pace(vdot: float) -> float | None:
    """VDOT → Daniels T-pace (sec/km) 정방향 조회."""
    from src.metrics.daniels_table import _VDOT_PACE_TABLE
    for i in range(len(_VDOT_PACE_TABLE) - 1):
        lo = _VDOT_PACE_TABLE[i]
        hi = _VDOT_PACE_TABLE[i + 1]
        if lo["vdot"] <= vdot <= hi["vdot"]:
            ratio = (vdot - lo["vdot"]) / (hi["vdot"] - lo["vdot"])
            t_lo = lo.get("T", 0)
            t_hi = hi.get("T", 0)
            if t_lo and t_hi:
                return round(t_lo + ratio * (t_hi - t_lo), 1)
    # 범위 밖
    if vdot <= _VDOT_PACE_TABLE[0]["vdot"]:
        return _VDOT_PACE_TABLE[0].get("T")
    if vdot >= _VDOT_PACE_TABLE[-1]["vdot"]:
        return _VDOT_PACE_TABLE[-1].get("T")
    return None


def _t_pace_to_vdot(t_pace_sec_km: float) -> float | None:
    """Daniels T-pace → VDOT 역산 (테이블 역보간)."""
    from src.metrics.daniels_table import _VDOT_PACE_TABLE

    # T-pace가 낮을수록(빠를수록) VDOT이 높음
    for i in range(len(_VDOT_PACE_TABLE) - 1):
        lo = _VDOT_PACE_TABLE[i]
        hi = _VDOT_PACE_TABLE[i + 1]
        t_lo = lo.get("T", 999)
        t_hi = hi.get("T", 999)
        # T-pace는 VDOT이 높을수록 낮아짐 → lo.T > hi.T
        if t_lo >= t_pace_sec_km >= t_hi:
            ratio = (t_lo - t_pace_sec_km) / (t_lo - t_hi) if t_lo != t_hi else 0
            return round(lo["vdot"] + ratio * (hi["vdot"] - lo["vdot"]), 1)

    # 범위 밖
    if t_pace_sec_km >= _VDOT_PACE_TABLE[0].get("T", 999):
        return float(_VDOT_PACE_TABLE[0]["vdot"])
    if t_pace_sec_km <= _VDOT_PACE_TABLE[-1].get("T", 0):
        return float(_VDOT_PACE_TABLE[-1]["vdot"])
    return None
