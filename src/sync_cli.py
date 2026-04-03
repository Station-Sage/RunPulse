"""RunPulse Data Sync CLI.

사용법:
    python -m src.sync_cli sync --source garmin --days 7
    python -m src.sync_cli sync --source garmin strava --days 3 --streams
    python -m src.sync_cli reprocess
    python -m src.sync_cli reprocess --source garmin
"""
from __future__ import annotations

import argparse
import logging
import sys

from src.db_setup import init_db, get_connection
from src.sync.orchestrator import full_sync
from src.sync.reprocess import reprocess_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="RunPulse Data Sync")
    sub = parser.add_subparsers(dest="command")

    # sync
    sync_parser = sub.add_parser("sync", help="Sync data from sources")
    sync_parser.add_argument(
        "--source", nargs="+", default=None,
        help="Sources to sync (garmin strava intervals runalyze)",
    )
    sync_parser.add_argument("--days", type=int, default=7)
    sync_parser.add_argument("--streams", action="store_true", help="Include stream data")

    # reprocess
    reproc_parser = sub.add_parser("reprocess", help="Rebuild Layer 1/2 from raw payloads")
    reproc_parser.add_argument("--source", default=None, help="Specific source to reprocess")
    reproc_parser.add_argument(
        "--no-clear", action="store_true", help="Don't clear existing data first",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init_db()
    conn = get_connection()

    try:
        if args.command == "sync":
            garmin_api = _init_garmin_api()

            results = full_sync(
                conn,
                sources=args.source,
                days=args.days,
                include_streams=args.streams,
                api_clients={"garmin": garmin_api} if garmin_api else {},
            )
            _print_results(results)

        elif args.command == "reprocess":
            stats = reprocess_all(
                conn, source=args.source, clear_first=not args.no_clear,
            )
            print(f"\nReprocess complete: {stats}")

    finally:
        conn.close()


def _init_garmin_api():
    """Garmin API 로그인. 실패 시 None."""
    try:
        from garminconnect import Garmin
        from src.utils.config import load_config
        cfg = load_config().get("garmin", {})
        api = Garmin(cfg.get("email"), cfg.get("password"))
        api.login()
        log.info("Garmin login OK")
        return api
    except Exception as e:
        log.warning("Garmin login failed: %s", e)
        return None


def _print_results(results: dict):
    """결과 요약 출력."""
    icons = {"success": "✅", "partial": "⚠️", "failed": "❌", "skipped": "⏭️"}
    print("\n" + "=" * 60)
    print("SYNC RESULTS")
    print("=" * 60)
    for source, result_list in results.items():
        for r in result_list:
            icon = icons.get(r.status, "?")
            print(
                f"{icon} {source}/{r.job_type}: {r.status} | "
                f"synced={r.synced_count} skipped={r.skipped_count} "
                f"errors={r.error_count} api_calls={r.api_calls}"
            )
            if r.last_error:
                print(f"   Last error: {r.last_error}")
            if r.retry_after:
                print(f"   Retry after: {r.retry_after}")
    print("=" * 60)


if __name__ == "__main__":
    main()
