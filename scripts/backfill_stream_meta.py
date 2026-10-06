#!/usr/bin/env python3
"""activity_stream_meta 백필(U18e). 사용: PYTHONPATH=. python3 scripts/backfill_stream_meta.py --db <path> [--dry-run]

운영 DB 에 실행하기 전 sqlite3 backup API 로 백업할 것. 재계산(메트릭 삭제·엔진 재실행)은 별도 단계.
"""
import argparse
import sqlite3

from src.sync.stream_meta_backfill import backfill_stream_meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    with sqlite3.connect(a.db) as c:
        print(backfill_stream_meta(c, dry_run=a.dry_run))
