"""DB 상태 대시보드 — 빠른 현황 확인.

Validator보다 가벼운 요약 정보를 출력합니다:
  - 각 테이블 행 수
  - 소스별 활동 수
  - 최근 sync_job 시각
  - primary violation 수
  - 스키마 버전

사용법:
    python -m src.utils.db_status
"""

from __future__ import annotations

import sqlite3
import sys

from src.db_setup import get_connection, get_db_path, SCHEMA_VERSION


def get_status(conn: sqlite3.Connection) -> dict:
    """DB 상태 딕셔너리 반환.

    Keys: tables, sources, recent_sync, primary_violations, schema_version
    """
    status: dict = {}

    # 테이블 행 수
    table_names = [
        "source_payloads",
        "activity_summaries",
        "daily_wellness",
        "metric_store",
        "activity_streams",
        "activity_laps",
        "activity_best_efforts",
        "sync_jobs",
    ]
    status["tables"] = {}
    for tbl in table_names:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            status["tables"][tbl] = cnt
        except Exception:
            status["tables"][tbl] = None

    # 소스별 활동 수
    try:
        rows = conn.execute(
            "SELECT source, COUNT(*) FROM activity_summaries GROUP BY source ORDER BY source"
        ).fetchall()
        status["sources"] = {r[0]: r[1] for r in rows}
    except Exception:
        status["sources"] = {}

    # 최근 sync_jobs
    try:
        rows = conn.execute(
            "SELECT source, job_type, started_at, status FROM sync_jobs ORDER BY started_at DESC LIMIT 5"
        ).fetchall()
        status["recent_sync"] = [
            {"source": r[0], "job_type": r[1], "started_at": r[2], "status": r[3]}
            for r in rows
        ]
    except Exception:
        status["recent_sync"] = []

    # primary violation 수
    try:
        violations = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT scope_type, scope_id, metric_name
                FROM metric_store
                WHERE is_primary = 1
                GROUP BY scope_type, scope_id, metric_name
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        status["primary_violations"] = violations
    except Exception:
        status["primary_violations"] = None

    # 스키마 버전
    try:
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        status["schema_version"] = ver
    except Exception:
        status["schema_version"] = None

    return status


def print_status(status: dict):
    """상태 딕셔너리를 사람이 읽기 쉬운 형식으로 출력."""
    print("═" * 55)
    print("RunPulse DB Status")
    print("═" * 55)

    # 스키마 버전
    sv = status.get("schema_version")
    print(f"Schema version : v{sv} (current: v{SCHEMA_VERSION})")

    # 테이블 행 수
    print("\n[Table Row Counts]")
    for tbl, cnt in status.get("tables", {}).items():
        cnt_str = str(cnt) if cnt is not None else "ERROR"
        print(f"  {tbl:<30} {cnt_str:>8}")

    # 소스별 활동 수
    print("\n[Activities by Source]")
    sources = status.get("sources", {})
    if sources:
        for src, cnt in sources.items():
            print(f"  {src:<20} {cnt:>6}")
    else:
        print("  (없음)")

    # primary violations
    pv = status.get("primary_violations")
    pv_str = str(pv) if pv is not None else "ERROR"
    print(f"\n[Primary Violations]   {pv_str}")

    # 최근 sync_jobs
    print("\n[Recent Sync Jobs]")
    recent = status.get("recent_sync", [])
    if recent:
        for job in recent:
            print(f"  {job['started_at']}  {job['source']}/{job['job_type']}  {job['status']}")
    else:
        print("  (없음)")

    print("═" * 55)


def main():
    conn = get_connection()
    try:
        status = get_status(conn)
    finally:
        conn.close()
    print_status(status)


if __name__ == "__main__":
    main()
