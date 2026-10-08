"""스키마 v31 — plan_adjustments (계획 조정 제안·수락 이력, ADR-035). 원본 planned_workouts 는 수정하지 않는다."""
from __future__ import annotations

import sqlite3

_DDL = """
CREATE TABLE IF NOT EXISTS plan_adjustments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id      INTEGER,                 -- 생성 시점 활성 목표(planned_workouts에 goal_id 없음). 없으면 NULL
    workout_id   INTEGER NOT NULL,        -- planned_workouts.id (FK 선언 없음: 원본 행은 재생성될 수 있음)
    date         TEXT    NOT NULL,        -- 조정 대상 날짜(YYYY-MM-DD)
    source       TEXT    NOT NULL CHECK (source IN ('crs','user','coach')),
    op           TEXT    NOT NULL DEFAULT 'replace'
                         CHECK (op IN ('replace','reduce','rest','skip','move')),
    before_json  TEXT    NOT NULL,        -- 원본 지문: {workout_type, distance_km, target_pace_min, target_pace_max, description}
    after_json   TEXT    NOT NULL,        -- 적용 값: 같은 키 + move면 {"date": "<to_date>"}
    reasons_json TEXT    NOT NULL DEFAULT '[]',  -- [{key, label, value?, target?}] (근거 칩 원천)
    rule_version TEXT    NOT NULL,        -- 제안 규칙 버전, 예: 'adjuster_v1' (R8 도입 시 'r8_v1')
    decision     TEXT    NOT NULL DEFAULT 'proposed'
                         CHECK (decision IN ('proposed','accepted','reverted')),
    rev          INTEGER NOT NULL DEFAULT 1,     -- proposed 상태에서 내용이 갱신될 때마다 +1
    accepted_at  TEXT,                    -- 한 번이라도 accepted 된 시각(되돌리기와 거절 구분용)
    decided_at   TEXT,                    -- 마지막 결정 시각
    decided_via  TEXT CHECK (decided_via IN ('plan','session','today','coach') OR decided_via IS NULL),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
-- 한 workout·날짜·출처에 살아 있는(proposed|accepted) 조정은 하나
CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_adj_live
    ON plan_adjustments(workout_id, date, source) WHERE decision IN ('proposed','accepted');
CREATE INDEX IF NOT EXISTS idx_plan_adj_date ON plan_adjustments(date, decision);
CREATE INDEX IF NOT EXISTS idx_plan_adj_goal ON plan_adjustments(goal_id, date);
"""


def ensure_v31(conn: sqlite3.Connection) -> None:
    """plan_adjustments 테이블과 인덱스 보장. 멱등."""
    conn.executescript(_DDL)
