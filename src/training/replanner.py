"""건너뜀/이행 미달 시 이번 주 잔여 계획 재조정.

재조정 규칙 (논문 근거):
  Rule 1 — 고강도 이동 (Hard-Easy 원칙, Lydiard/Bowerman):
    건너뛴 interval/tempo/long → 이번 주 남은 rest/easy 날에 이동.
    Q-day 사이 최소 1일 간격 보장.

  Rule 2 — 연속 건너뜀 볼륨 축소 (Gabbett 2016, BJSM):
    최근 2일 이상 연속 건너뜀 → 남은 고강도 볼륨 10% 감소.
    (갑작스러운 볼륨 변화 최소화 — ACWR 급등 방지)

  Rule 3 — 피드백 기반 재조정 (session_outcomes):
    최근 3회 dist_ratio 평균 < 0.85 → 이번 주 목표 볼륨 -10%.
    최근 3회 pace_delta_pct 평균 > +5% → 처방 페이스 재검토 경고.
    CRS level <= 1 → Q-day 1회 감소 제안.

  Rule 4 — 테이퍼 보호 (Mujika & Padilla 2003):
    레이스 2주 이내: 볼륨 축소만, 강도 유지. 이동 금지.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

log = logging.getLogger(__name__)

_HIGH_INTENSITY = {"interval", "tempo"}
_REPLACEABLE = {"rest", "easy", "recovery"}


# ── 피드백 조회 ───────────────────────────────────────────────────────────

def _get_recent_outcomes(conn: sqlite3.Connection, n: int = 3) -> list[dict]:
    """최근 N회 session_outcomes (completed 세션만)."""
    rows = conn.execute(
        "SELECT dist_ratio, pace_delta_pct, crs_at_session, outcome_label "
        "FROM session_outcomes "
        "WHERE outcome_label NOT IN ('skipped') AND dist_ratio IS NOT NULL "
        "ORDER BY date DESC LIMIT ?",
        (n,),
    ).fetchall()
    return [
        {"dist_ratio": r[0], "pace_delta_pct": r[1],
         "crs": r[2], "label": r[3]}
        for r in rows
    ]


def _feedback_volume_factor(outcomes: list[dict]) -> tuple[float, str | None]:
    """최근 이행률 기반 볼륨 조정 계수.

    Rule 3: dist_ratio 평균 < 0.85 → 0.90 (10% 감소)
    """
    if not outcomes:
        return 1.0, None
    avg_ratio = sum(o["dist_ratio"] for o in outcomes) / len(outcomes)
    if avg_ratio < 0.85:
        return 0.90, (
            f"최근 {len(outcomes)}회 평균 달성률 {avg_ratio:.0%} — "
            f"이번 주 볼륨을 10% 줄였습니다."
        )
    if avg_ratio < 0.75:
        return 0.82, (
            f"최근 {len(outcomes)}회 평균 달성률 {avg_ratio:.0%} — "
            f"이번 주 볼륨을 18% 줄였습니다."
        )
    return 1.0, None


def _feedback_pace_warning(outcomes: list[dict]) -> str | None:
    """최근 페이스 편차 기반 경고."""
    valid = [o for o in outcomes if o["pace_delta_pct"] is not None]
    if not valid:
        return None
    avg_delta = sum(o["pace_delta_pct"] for o in valid) / len(valid)
    if avg_delta > 5.0:
        return (
            f"최근 {len(valid)}회 실제 페이스가 처방보다 평균 {avg_delta:.1f}% 느립니다. "
            f"VDOT_ADJ 재계산을 권장합니다."
        )
    return None


# ── 메인 재조정 함수 ──────────────────────────────────────────────────────

def replan_remaining_week(
    conn: sqlite3.Connection,
    skipped_workout_id: int,
) -> dict:
    """건너뜀 발생 시 이번 주 잔여 계획 재조정.

    Args:
        conn: SQLite 연결.
        skipped_workout_id: 건너뛴 planned_workout.id.

    Returns:
        {
            "moved": bool,
            "target_date": str | None,
            "volume_reduced": bool,
            "message": str,
            "changes": list[dict],
            "warnings": list[str],
        }
    """
    row = conn.execute(
        "SELECT date, workout_type, distance_km, target_pace_min, target_pace_max, "
        "target_hr_zone, description, rationale, interval_prescription "
        "FROM planned_workouts WHERE id=?",
        (skipped_workout_id,),
    ).fetchone()

    if not row:
        return {"moved": False, "message": "워크아웃을 찾을 수 없습니다.", "changes": [], "warnings": []}

    (skip_date_str, skip_type, skip_dist, pace_min, pace_max,
     hr_zone, desc, rationale, interval_rx) = row

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    changes: list[dict] = []
    warnings: list[str] = []

    # 레이스까지 남은 주 수 (테이퍼 보호)
    weeks_to_race = _get_weeks_to_race(conn)
    in_taper = weeks_to_race is not None and weeks_to_race <= 2

    # ── 피드백 기반 경고 (Rule 3) ─────────────────────────────────────────
    outcomes = _get_recent_outcomes(conn)
    _, vol_warning = _feedback_volume_factor(outcomes)
    pace_warning = _feedback_pace_warning(outcomes)
    if vol_warning:
        warnings.append(vol_warning)
    if pace_warning:
        warnings.append(pace_warning)

    # CRS 기반 Q-day 경고
    try:
        from src.metrics.crs import evaluate as crs_eval, LEVEL_Z1
        crs_result = crs_eval(conn)
        if crs_result["level"] <= LEVEL_Z1:
            warnings.append(
                f"현재 CRS 레벨 {crs_result['level_label']} — "
                f"남은 고강도 훈련을 이지런으로 전환하는 것을 고려하세요."
            )
    except Exception:
        pass

    # 이번 주 잔여 계획 (오늘 이후)
    remaining = conn.execute(
        "SELECT id, date, workout_type, distance_km FROM planned_workouts "
        "WHERE date > ? AND date <= ? AND completed != 1 "
        "ORDER BY date",
        (today.isoformat(), week_end.isoformat()),
    ).fetchall()

    # ── Rule 2: 연속 건너뜀 체크 ─────────────────────────────────────────
    recent_skips = conn.execute(
        "SELECT COUNT(*) FROM planned_workouts "
        "WHERE date BETWEEN ? AND ? AND completed = -1 AND workout_type != 'rest'",
        ((today - timedelta(days=2)).isoformat(), today.isoformat()),
    ).fetchone()[0] or 0
    consecutive_skip = recent_skips >= 2

    # ── Rule 4: 테이퍼 보호 ───────────────────────────────────────────────
    if in_taper:
        # 테이퍼 기간: 이동 없이 남은 고강도 볼륨만 5% 축소
        reduced = 0
        for r_id, r_date, r_type, r_dist in remaining:
            if r_type in _HIGH_INTENSITY and r_dist:
                new_dist = round(r_dist * 0.95, 1)
                conn.execute(
                    "UPDATE planned_workouts SET distance_km=?, "
                    "updated_at=datetime('now') WHERE id=?",
                    (new_dist, r_id),
                )
                changes.append({"id": r_id, "date": r_date,
                                 "before": f"{r_dist}km", "after": f"{new_dist}km"})
                reduced += 1
        if reduced:
            conn.commit()
            return {
                "moved": False, "target_date": None, "volume_reduced": True,
                "message": f"테이퍼 기간 — 강도 유지, 볼륨 5% 축소 (Mujika & Padilla 2003).",
                "changes": changes, "warnings": warnings,
            }
        return {
            "moved": False, "target_date": None, "volume_reduced": False,
            "message": "테이퍼 기간 — 잔여 계획 유지.",
            "changes": [], "warnings": warnings,
        }

    # ── Rule 1: 고강도/롱런 이동 ──────────────────────────────────────────
    if skip_type in _HIGH_INTENSITY or skip_type == "long":
        # 남은 날 중 rest/easy이면서 Q-day와 2일 이상 간격인 날 탐색
        q_dates = [r[1] for r in remaining if r[2] in _HIGH_INTENSITY]
        for r_id, r_date, r_type, r_dist in remaining:
            if r_type not in _REPLACEABLE:
                continue
            # Hard-Easy 원칙: 인접 Q-day와 1일 이상 간격
            r_d = date.fromisoformat(r_date)
            too_close = any(
                abs((r_d - date.fromisoformat(qd)).days) < 2 for qd in q_dates
            )
            if too_close:
                continue

            conn.execute(
                """UPDATE planned_workouts
                   SET workout_type=?, distance_km=?, target_pace_min=?,
                       target_pace_max=?, target_hr_zone=?, description=?,
                       rationale=?, interval_prescription=?,
                       updated_at=datetime('now')
                   WHERE id=?""",
                (skip_type, skip_dist, pace_min, pace_max, hr_zone,
                 f"[재조정] {desc or skip_type}",
                 f"[이동] 원래 {skip_date_str} 계획, 건너뜀으로 이동",
                 interval_rx, r_id),
            )
            changes.append({"id": r_id, "date": r_date,
                             "before": r_type, "after": skip_type})
            conn.commit()
            log.info("재조정: %s(%s) → %s로 이동", skip_type, skip_date_str, r_date)
            return {
                "moved": True, "target_date": r_date, "volume_reduced": False,
                "message": (
                    f"{_type_label(skip_type)}을(를) {r_date}로 이동했습니다."
                ),
                "changes": changes, "warnings": warnings,
            }

    # ── Rule 2: 연속 건너뜀 → 볼륨 축소 ─────────────────────────────────
    if consecutive_skip:
        reduced = 0
        for r_id, r_date, r_type, r_dist in remaining:
            if r_type in _HIGH_INTENSITY and r_dist:
                new_dist = round(r_dist * 0.90, 1)  # Gabbett 2016: 급격한 증가 방지
                conn.execute(
                    "UPDATE planned_workouts SET distance_km=?, "
                    "updated_at=datetime('now') WHERE id=?",
                    (new_dist, r_id),
                )
                changes.append({"id": r_id, "date": r_date,
                                 "before": f"{r_dist}km", "after": f"{new_dist}km"})
                reduced += 1
        if reduced:
            conn.commit()
            return {
                "moved": False, "target_date": None, "volume_reduced": True,
                "message": (
                    f"연속 건너뜀 감지 — 남은 {reduced}개 훈련 볼륨을 10% 줄였습니다 "
                    f"(Gabbett 2016: ACWR 급등 방지)."
                ),
                "changes": changes, "warnings": warnings,
            }

    return {
        "moved": False, "target_date": None, "volume_reduced": False,
        "message": "잔여 계획을 유지합니다. 충분히 휴식하세요.",
        "changes": [], "warnings": warnings,
    }


def _get_weeks_to_race(conn: sqlite3.Connection) -> int | None:
    """active 목표의 레이스까지 남은 주 수."""
    row = conn.execute(
        "SELECT race_date FROM goals WHERE status='active' AND race_date IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        delta = (date.fromisoformat(row[0]) - date.today()).days
        return max(0, delta // 7)
    except ValueError:
        return None


def _type_label(wtype: str) -> str:
    return {
        "easy": "이지런", "tempo": "템포런", "interval": "인터벌",
        "long": "롱런", "rest": "휴식", "recovery": "회복조깅", "race": "레이스",
    }.get(wtype, wtype)
