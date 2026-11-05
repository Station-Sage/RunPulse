#!/usr/bin/env python3
"""첫 활동일 이전의 crs 구버전(1.0) 행 정리. 사용: PYTHONPATH=. python3 scripts/prune_stale_crs.py --db <path> [--apply]

기본은 dry-run. --apply 는 같은 폴더에 sqlite backup API 로 백업한 뒤 삭제한다.
"""
import argparse
import sqlite3
from pathlib import Path


def stale_crs_where(conn: sqlite3.Connection) -> tuple[str, tuple]:
    first = conn.execute("SELECT MIN(substr(start_time,1,10)) FROM activity_summaries").fetchone()[0]
    if not first:
        return "0", ()
    return ("metric_name='crs' AND scope_type='daily' AND algorithm_version='1.0' AND scope_id<?", (first,))


def prune_stale_crs(conn: sqlite3.Connection, apply: bool = False) -> int:
    where, args = stale_crs_where(conn)
    n = conn.execute(f"SELECT COUNT(*) FROM metric_store WHERE {where}", args).fetchone()[0]
    if apply and n:
        conn.execute(f"DELETE FROM metric_store WHERE {where}", args)
        conn.commit()
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    with sqlite3.connect(a.db) as c:
        if a.apply:
            bak = Path(a.db).with_name(Path(a.db).name + ".bak-prune-crs")
            with sqlite3.connect(bak) as b:
                c.backup(b)
            print("backup:", bak)
        print(("deleted" if a.apply else "would delete"), prune_stale_crs(c, a.apply))
