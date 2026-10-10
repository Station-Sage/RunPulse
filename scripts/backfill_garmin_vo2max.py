#!/usr/bin/env python3
"""Garmin VO2max 정밀값 과거 백필(GARMIN-VO2MAX-PRECISE T8). 기본은 dry-run(조회만, DB 미수정).

사용(컨테이너 안, 토큰이 있는 곳): python3 scripts/backfill_garmin_vo2max.py --db <path> --config <config.json> \
  [--start 2025-05-20] [--end YYYY-MM-DD] [--apply]
--apply 전에 sqlite3 backup API 로 DB 를 백업하고 사용자 승인을 받을 것.
"""
import argparse
import json
import sqlite3
from datetime import date

from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.garmin_maxmet_fields import extract_vo2max_daily
from src.sync.garmin import _login
from src.sync.garmin_maxmet_sync import backfill_vo2max

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--start", default="2025-05-20")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        client = _login(json.load(f))
    if not a.apply:
        items = client.get_max_metrics_range(a.start, a.end)
        days = extract_vo2max_daily(GarminExtractor(), items)
        print({"dry_run": True, "days": len(days), "last": max(days) if days else None})
    else:
        with sqlite3.connect(a.db, timeout=30) as c:
            print(backfill_vo2max(c, client, a.start, a.end))
