"""대회 캘린더 불변식 3·4 검사 (check_data_consistency 에서 호출) — 3: 활성 목표의 대회는 A·planned|done, 4: 목표 캐시 = 대회 값."""
from __future__ import annotations

import sqlite3


def check_race_invariants(db_path: str) -> list[tuple[str, str]]:
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        if not any(r[1] == "race_id" for r in conn.execute("PRAGMA table_info(goals)")):
            return []
        bad3 = conn.execute(
            "SELECT COUNT(*) FROM goals g LEFT JOIN race_calendar r ON r.id = g.race_id"
            " WHERE g.status='active' AND g.race_id IS NOT NULL"
            " AND (r.id IS NULL OR r.priority <> 'A' OR r.status NOT IN ('planned','done'))").fetchone()[0]
        # 예외(RC-21 b): 비활성 연결 목표의 race_date 캐시 NULL 은 날짜 비교만 건너뛴다
        bad4 = conn.execute(
            "SELECT COUNT(*) FROM goals g JOIN race_calendar r ON r.id = g.race_id WHERE"
            " ((g.race_date IS NOT r.race_date) AND NOT (g.status <> 'active' AND g.race_date IS NULL))"
            " OR g.distance_km IS NOT r.distance_km OR g.target_time_sec IS NOT (CASE WHEN r.goal_type='time' THEN r.goal_value END)").fetchone()[0]
    except sqlite3.Error as e:
        return [("🟠", f"대회 불변식 검사 실패: {e}")]
    finally:
        conn.close()
    out = [("🔴", f"불변식 3 위반 {bad3}건 (활성 목표의 대회가 A·planned|done 아님)") if bad3
           else ("✅", "대회 불변식 3: 활성 목표의 대회는 A·planned|done")]
    out.append(("🔴", f"불변식 4 위반 {bad4}건 (목표 캐시 ≠ 대회 값)") if bad4
               else ("✅", "대회 불변식 4: 목표 캐시 = 대회 값"))
    return out
