#!/usr/bin/env python3
"""Strava 시작 시각 시간대 백필·되돌리기 CLI (TZ T4). 기본은 dry-run, --apply 일 때만 DB 를 바꾼다.

사용법:
    python3 scripts/normalize_start_time.py --source strava [--limit N] [--apply] [--user USER_ID]
    python3 scripts/normalize_start_time.py --list-run RUN_ID
    python3 scripts/normalize_start_time.py --revert-run RUN_ID [--apply]

--apply 전에는 반드시 DB 를 백업할 것.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db_setup import get_connection  # noqa: E402
from src.import_export.tz_backfill import list_run, revert_run, run_backfill  # noqa: E402


def _config() -> dict | None:
    p = ROOT / "config.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["strava"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--apply", action="store_true", help="실제 반영 (기본 dry-run)")
    ap.add_argument("--list-run", metavar="RUN_ID")
    ap.add_argument("--revert-run", metavar="RUN_ID")
    ap.add_argument("--user", default=None)
    a = ap.parse_args()
    conn = get_connection(a.user)
    if a.list_run:
        rows = list_run(conn, a.list_run)
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    if a.revert_run:
        r = revert_run(conn, a.revert_run, apply=a.apply)
        print(f"[tz_revert] run={r['run_id']} 되돌림 {r['reverted']} ({'적용' if a.apply else 'dry-run'})")
        return 0
    if a.source != "strava":
        ap.error("--source strava 또는 --list-run/--revert-run 필요")
    r = run_backfill(conn, _config(), apply=a.apply, limit=a.limit)
    print(f"[tz_backfill] run={r['run_id']} 확인 {r['checked']}·변경 {r['changed']}"
          f"(날짜 변경 {r['date_changed']}·그룹 변화 {r['group_changed']})·API {r['api_calls']}회"
          f" ({'적용' if a.apply else 'dry-run'})")
    for row in r["rows"][:50]:
        print(f"  {row['source_id']}: {row['from']} → {row['to']} ({row['from_source']} → {row['to_source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
