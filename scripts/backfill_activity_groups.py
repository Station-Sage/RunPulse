#!/usr/bin/env python3
"""activity_groups 마스터 테이블 백필 스크립트 (D2).

기존 activity_summaries.matched_group_id 값으로부터 activity_groups 행을 생성한다.
provider 우선순위: garmin(1) > intervals(2) > strava(3) > runalyze(4).

사용법:
    python scripts/backfill_activity_groups.py [--user USER_ID]

종료 코드:
    0 = 정상 완료
    1 = 오류
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db_setup import get_db_path


_INSERT_SQL = """
INSERT OR IGNORE INTO activity_groups
    (group_id, primary_source, activity_date, distance_m, member_count)
SELECT
    matched_group_id AS group_id,
    CASE MIN(CASE source
             WHEN 'garmin'     THEN 1
             WHEN 'intervals'  THEN 2
             WHEN 'strava'     THEN 3
             WHEN 'runalyze'   THEN 4
             ELSE 5 END)
        WHEN 1 THEN 'garmin'
        WHEN 2 THEN 'intervals'
        WHEN 3 THEN 'strava'
        WHEN 4 THEN 'runalyze'
        ELSE MIN(source) END AS primary_source,
    DATE(MIN(start_time))   AS activity_date,
    AVG(distance_m)         AS distance_m,
    COUNT(*)                AS member_count
FROM activity_summaries
WHERE matched_group_id IS NOT NULL
GROUP BY matched_group_id
"""


def backfill(conn: sqlite3.Connection) -> int:
    """activity_groups 백필 실행. 삽입된 행 수 반환."""
    conn.execute(_INSERT_SQL)
    inserted = conn.execute(
        "SELECT COUNT(*) FROM activity_groups"
    ).fetchone()[0]
    conn.commit()
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="activity_groups 마스터 테이블 백필")
    parser.add_argument("--user", default=None, help="사용자 ID (기본: default)")
    args = parser.parse_args()

    db_path = get_db_path(args.user)
    if not db_path.exists():
        print(f"DB 파일 없음: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    try:
        # activity_groups 테이블이 없으면 생성
        from src.db_setup import create_tables
        create_tables(conn)

        before = conn.execute("SELECT COUNT(*) FROM activity_groups").fetchone()[0]
        inserted = backfill(conn)
        after = conn.execute("SELECT COUNT(*) FROM activity_groups").fetchone()[0]
        print(f"백필 완료: {after}개 그룹 ({after - before}개 신규 삽입)")
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
