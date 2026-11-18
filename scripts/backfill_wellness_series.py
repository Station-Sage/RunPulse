"""Garmin raw payload → wellness_series 과거분 백필 CLI (Garmin 호출 없음).

사용: PYTHONPATH=. python3 scripts/backfill_wellness_series.py --user <email> [--days 400]
"""
import argparse
import sqlite3

from src.sync.wellness_series_backfill import backfill_series
from src.db_setup import get_db_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--db", help="DB 경로 직접 지정(워크트리 실행용)")
    ap.add_argument("--days", type=int, default=400)
    a = ap.parse_args()
    conn = sqlite3.connect(a.db or get_db_path(a.user, create=False), timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    print(backfill_series(conn, a.days))


if __name__ == "__main__":
    main()
