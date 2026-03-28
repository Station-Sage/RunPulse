"""RunPulse 운동 유형 자동 분류기 — HR존/페이스/거리/시간 기반.

각 활동을 데이터 기반으로 분류하고, 분류에 따른 훈련 효과를 함께 반환.
소스(Garmin/Strava/Intervals) 태그와 독립적으로 RunPulse 자체 판단.

분류:
    easy     → 유산소 기반 강화
    tempo    → 젖산역치 개선
    threshold→ 역치 페이스 향상
    interval → VO2Max 자극
    long     → 지구력/지방 연소
    race     → 최대 퍼포먼스
    recovery → 피로 해소

저장: computed_metrics (date, 'WorkoutType', value=None, extra_json={type, effect, ...})
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from src.metrics.store import estimate_max_hr


@dataclass
class WorkoutClassification:
    """운동 분류 결과."""
    workout_type: str       # easy/tempo/threshold/interval/long/race/recovery
    effect: str             # 훈련 효과 설명 (한국어)
    confidence: float       # 분류 신뢰도 (0~1)
    reason: str             # 분류 근거 요약

    def to_dict(self) -> dict:
        return {
            "type": self.workout_type,
            "effect": self.effect,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
        }


# 분류별 훈련 효과
_EFFECTS: dict[str, str] = {
    "easy": "유산소 기반 강화",
    "tempo": "젖산역치 개선",
    "threshold": "역치 페이스 향상",
    "interval": "VO2Max 자극",
    "long": "지구력/지방 연소",
    "race": "최대 퍼포먼스",
    "recovery": "피로 해소",
}

# 분류별 태그 색상
TAG_COLORS: dict[str, str] = {
    "easy": "#27ae60",
    "tempo": "#e67e22",
    "threshold": "#8e44ad",
    "interval": "#e74c3c",
    "long": "#2980b9",
    "race": "#c0392b",
    "recovery": "#7f8c8d",
}

# 분류별 한국어 라벨
TAG_LABELS: dict[str, str] = {
    "easy": "이지런",
    "tempo": "템포",
    "threshold": "역치",
    "interval": "인터벌",
    "long": "장거리",
    "race": "레이스",
    "recovery": "회복",
}


def classify_workout(
    duration_sec: int | None = None,
    distance_km: float | None = None,
    avg_hr: int | None = None,
    max_hr: int | None = None,
    avg_pace_sec_km: int | None = None,
    hr_zone_pcts: list[float] | None = None,
    eftp_sec_km: int | None = None,
    relative_effort: float | None = None,
    decoupling: float | None = None,
    event_type: str | None = None,
) -> WorkoutClassification:
    """데이터 기반 운동 유형 분류 (순수 함수).

    Args:
        duration_sec: 운동 시간 (초).
        distance_km: 거리 (km).
        avg_hr: 평균 심박.
        max_hr: 최대 심박 (maxHR 기준).
        avg_pace_sec_km: 평균 페이스 (sec/km).
        hr_zone_pcts: [z1%, z2%, z3%, z4%, z5%] 존별 시간 비율.
        eftp_sec_km: 역치 페이스 (sec/km).
        relative_effort: 상대적 노력.
        decoupling: 심박-페이스 분리율 (%).

    Returns:
        WorkoutClassification.
    """
    dur_min = (duration_sec or 0) / 60
    dist = distance_km or 0
    z = hr_zone_pcts or [0, 0, 0, 0, 0]
    z12 = z[0] + z[1] if len(z) >= 2 else 0
    z3 = z[2] if len(z) >= 3 else 0
    z45 = (z[3] if len(z) >= 4 else 0) + (z[4] if len(z) >= 5 else 0)

    # HR 강도 비율 (avg_hr / max_hr)
    hr_intensity = avg_hr / max_hr if avg_hr and max_hr and max_hr > 0 else 0

    # 페이스 대비 eFTP 비율
    pace_ratio = avg_pace_sec_km / eftp_sec_km if avg_pace_sec_km and eftp_sec_km and eftp_sec_km > 0 else 1.0

    # ── 분류 규칙 (우선순위 순) ──────────────────────────────────────
    # 레이스는 분류하지 않음 — 원본 event_type='race'를 그대로 사용
    # (activity_summaries.event_type → UI/VDOT에서 직접 참조)

    # 1. 인터벌: Z4-5 > 25% (고강도 비율 높음)
    if z45 > 25:
        return WorkoutClassification("interval", _EFFECTS["interval"], 0.85,
                                     f"Z4-5 {z45:.0f}%")

    # 3. 장거리: 90분+ 또는 15km+, 저강도 위주
    if (dur_min >= 90 or dist >= 15) and z12 > 50:
        return WorkoutClassification("long", _EFFECTS["long"], 0.85,
                                     f"{dist:.1f}km / {dur_min:.0f}분, Z1-2 {z12:.0f}%")

    # 4. 역치: 페이스 ≈ eFTP (±5%), Z3-4 위주
    if 0.93 <= pace_ratio <= 1.07 and (z3 + z45) > 40:
        return WorkoutClassification("threshold", _EFFECTS["threshold"], 0.8,
                                     f"페이스 eFTP ×{pace_ratio:.2f}, Z3+ {z3 + z45:.0f}%")

    # 5. 템포: Z3 > 30% 또는 HR 75~88%
    if z3 > 30 or (0.75 < hr_intensity < 0.88 and z3 > 15):
        return WorkoutClassification("tempo", _EFFECTS["tempo"], 0.75,
                                     f"Z3 {z3:.0f}%, HR {hr_intensity:.0%}")

    # 6. 회복: 짧은 거리 + 느린 페이스 + Z1 위주
    if dist < 5 and dur_min < 40 and z12 > 85:
        return WorkoutClassification("recovery", _EFFECTS["recovery"], 0.7,
                                     f"{dist:.1f}km / {dur_min:.0f}분, Z1-2 {z12:.0f}%")

    # 7. 이지런: Z1-2 > 70% (기본)
    if z12 > 70:
        return WorkoutClassification("easy", _EFFECTS["easy"], 0.7,
                                     f"Z1-2 {z12:.0f}%")

    # HR존 데이터 없을 때 fallback
    if hr_intensity > 0.88:
        return WorkoutClassification("tempo", _EFFECTS["tempo"], 0.5,
                                     f"HR {hr_intensity:.0%} (존 데이터 없음)")
    if dist >= 15 or dur_min >= 90:
        return WorkoutClassification("long", _EFFECTS["long"], 0.5,
                                     f"{dist:.1f}km / {dur_min:.0f}분")

    return WorkoutClassification("easy", _EFFECTS["easy"], 0.4,
                                 "기본 분류 (데이터 부족)")


def classify_activity(conn: sqlite3.Connection, activity_id: int) -> WorkoutClassification | None:
    """DB에서 활동 데이터를 읽어 분류.

    소스 레이스 태그 우선:
      - Garmin: event_type='race'
      - Strava: workout_type=1
    3개 소스 중 하나라도 레이스이면 레이스로 확정.

    Returns:
        WorkoutClassification 또는 None.
    """
    row = conn.execute(
        "SELECT duration_sec, distance_km, avg_hr, max_hr, avg_pace_sec_km, event_type "
        "FROM activity_summaries WHERE id=?",
        (activity_id,),
    ).fetchone()
    if not row:
        return None

    duration_sec, distance_km, avg_hr, max_hr_act = row[0], row[1], row[2], row[3]
    _event_type = row[5] if len(row) > 5 else None

    # 동일 matched_group_id의 모든 소스에서 레이스 태그 확인
    is_source_race = False
    group_row = conn.execute(
        "SELECT matched_group_id FROM activity_summaries WHERE id=?", (activity_id,)
    ).fetchone()
    if group_row and group_row[0]:
        race_check = conn.execute(
            """SELECT 1 FROM activity_summaries
               WHERE matched_group_id=?
                 AND (
                   (source='garmin' AND event_type='race')
                   OR (source='strava' AND workout_type=1)
                   OR (source='intervals' AND event_type='race')
                 ) LIMIT 1""",
            (group_row[0],),
        ).fetchone()
        is_source_race = race_check is not None
    elif _event_type == 'race':
        is_source_race = True

    if is_source_race:
        return WorkoutClassification(
            "race", _EFFECTS["race"], 1.0, "소스 레이스 태그 (Garmin event_type=race 또는 Strava workout_type=1)"
        )

    # maxHR: 활동 max_hr가 아닌 사용자 maxHR (전체 최대)
    max_hr_est = estimate_max_hr(conn)
    max_hr = int(max_hr_est) if max_hr_est != 190.0 else (max_hr_act or 190)

    # HR존 시간 비율
    hr_zone_pcts = _load_hr_zone_pcts(conn, activity_id, duration_sec)

    # eFTP
    eftp_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='eFTP' "
        "AND activity_id IS NULL AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    eftp = int(eftp_row[0]) if eftp_row else None

    # RelativeEffort, Decoupling
    re_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE activity_id=? AND metric_name='RelativeEffort'",
        (activity_id,),
    ).fetchone()
    dec_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE activity_id=? AND metric_name='AerobicDecoupling'",
        (activity_id,),
    ).fetchone()

    return classify_workout(
        duration_sec=duration_sec,
        distance_km=distance_km,
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_sec_km=row[4],
        hr_zone_pcts=hr_zone_pcts,
        eftp_sec_km=eftp,
        relative_effort=float(re_row[0]) if re_row and re_row[0] else None,
        decoupling=float(dec_row[0]) if dec_row and dec_row[0] else None,
        event_type=_event_type,
    )


def _load_hr_zone_pcts(conn: sqlite3.Connection, activity_id: int,
                       duration_sec: int | None) -> list[float]:
    """활동의 HR존별 시간 비율(%) 로드."""
    total = duration_sec or 1
    pcts = [0.0] * 5

    # Garmin hr_zone_time_1~5
    for i in range(1, 6):
        row = conn.execute(
            "SELECT metric_value FROM activity_detail_metrics "
            "WHERE activity_id=? AND metric_name=?",
            (activity_id, f"hr_zone_time_{i}"),
        ).fetchone()
        if row and row[0] is not None:
            pcts[i - 1] = float(row[0]) / total * 100

    # Intervals icu_hr_zone_times (JSON array)
    if sum(pcts) < 1:
        icu_row = conn.execute(
            "SELECT metric_value FROM activity_detail_metrics "
            "WHERE activity_id=? AND metric_name='icu_hr_zone_times'",
            (activity_id,),
        ).fetchone()
        if icu_row and icu_row[0]:
            try:
                raw = icu_row[0]
                zones = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(zones, list):
                    for i, z in enumerate(zones[:5]):
                        pcts[i] = float(z) / total * 100 if z else 0
            except (json.JSONDecodeError, TypeError):
                pass

    return pcts


def classify_and_save(conn: sqlite3.Connection, activity_id: int,
                      activity_date: str) -> WorkoutClassification | None:
    """활동 분류 후 computed_metrics에 저장."""
    from src.metrics.store import save_metric

    result = classify_activity(conn, activity_id)
    if result is None:
        return None

    save_metric(
        conn, date=activity_date, metric_name="WorkoutType",
        activity_id=activity_id, extra_json=result.to_dict(),
    )
    return result
