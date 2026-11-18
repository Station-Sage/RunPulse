#!/usr/bin/env python3
"""Garmin 활동 강제 재수집(V2-REPAIR-BACKFILL). 컨테이너에서 실행(자격증명 복호화).

사용: PYTHONPATH=. python3 scripts/backfill_garmin_activities.py --user <email> [--limit 20] [--sport running|other|all]
운영 DB 에 쓰기 전 sqlite3 backup API 로 백업할 것. 재계산(메트릭 재생성)은 별도 단계.
"""
import argparse
import logging
import sqlite3
from pathlib import Path

from src.db_setup import get_db_path
from src.sync.garmin import _login
from src.sync.garmin_backfill_job import run_backfill
from src.utils.config import load_config

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--sport", default="running", choices=["running", "other", "all"])
    a = ap.parse_args()
    db = get_db_path(a.user, create=False)
    api = _login(load_config(user_id=a.user))
    with sqlite3.connect(db, timeout=60) as conn:
        r = run_backfill(conn, api, Path(db).with_name("garmin_backfill_done.json"), a.limit, a.sport)
    print(f"total={r.total_items} done={r.synced_count} err={r.error_count} api={r.api_calls} status={r.status}")
