"""세그먼트 이행 결과 저장(P7-PRED-43) — 매칭된 계획·활동 쌍에 v2 비교(outcome_v2.compare)와 소스 컴플라이언스를 기록.

planned_workouts.structure_json 이 있을 때만 v2 비교를 하고, 없으면 기존(거리·평균 페이스) 결과를 그대로 둔다.
source_compliance: Garmin 랩 compliance_score 의 시간가중 평균(작업 단계 매칭 랩만, wkt_step_index 있는 랩), 없으면 None.
"""
from __future__ import annotations

import json
import sqlite3

from src.training.outcome_v2 import compare


def _classifier_bouts(conn, activity_id: int) -> list[dict] | None:
    r = conn.execute("SELECT json_value FROM metric_store WHERE scope_type='activity' AND scope_id=? "
                     "AND metric_name='workout_type_classified' AND is_primary=1", (str(activity_id),)).fetchone()
    if not r or not r[0]:
        return None
    return json.loads(r[0]).get("bouts") or []


def _garmin_compliance(conn, activity_id: int) -> float | None:
    rows = conn.execute("SELECT compliance_score, duration_sec FROM activity_laps WHERE activity_id=? "
                        "AND compliance_score IS NOT NULL AND wkt_step_index IS NOT NULL", (activity_id,)).fetchall()
    t = sum(d or 0 for _, d in rows)
    return round(sum(c * (d or 0) for c, d in rows) / t, 1) if t else None


def update_outcome_v2(conn: sqlite3.Connection, planned_id: int, activity_id: int) -> dict | None:
    """session_outcomes(planned_id) 행에 v2 결과를 덧쓴다. 반환: compare() 결과 또는 None(구조 없음·분류 없음)."""
    p = conn.execute("SELECT structure_json, COALESCE(source_system, source) FROM planned_workouts WHERE id=?",
                     (planned_id,)).fetchone()
    src_c = _garmin_compliance(conn, activity_id)
    if not p or not p[0]:
        if src_c is not None:
            conn.execute("UPDATE session_outcomes SET source_compliance=?, source_system='garmin' WHERE planned_id=?",
                         (src_c, planned_id))
        return None
    bouts = _classifier_bouts(conn, activity_id)
    if bouts is None:
        return None
    res = compare(json.loads(p[0]), bouts)
    conn.execute("UPDATE session_outcomes SET compliance_pct=?, segment_match_json=?, source_compliance=?, "
                 "source_system=?, outcome_label=? WHERE planned_id=?",
                 (res["compliance_pct"], json.dumps(res, ensure_ascii=False), src_c, p[1], res["label"], planned_id))
    return res
