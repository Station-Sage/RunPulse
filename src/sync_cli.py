"""RunPulse Data Sync CLI.

사용법:
    python -m src.sync_cli sync --source garmin --days 7
    python -m src.sync_cli sync --source garmin strava --days 3 --streams
    python -m src.sync_cli reprocess
    python -m src.sync_cli reprocess --source garmin
    python -m src.sync_cli initial-load --zip-path /path/to/export.zip
    python -m src.sync_cli initial-load --zip-path /path/to/export.zip --steps 1,7,8,9
    python -m src.sync_cli initial-load --dry-run --zip-path /path/to/export.zip
"""
from __future__ import annotations

import argparse
import logging
import sys

from src.utils.log_config import setup_logging
setup_logging()

from src.db_setup import init_db, get_connection
from src.sync.orchestrator import full_sync
from src.sync.reprocess import reprocess_all

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

    # initial-load
    il_parser = sub.add_parser(
        "initial-load",
        help="Steps 1-9: Bulk load all historical data into empty DB",
    )
    il_parser.add_argument("--zip-path", default=None, help="Garmin Bulk Export ZIP path (Step 1)")
    il_parser.add_argument("--garmin-days", type=int, default=30, help="Garmin API supplemental range (days)")
    il_parser.add_argument("--strava-days", type=int, default=730, help="Strava sync range (days)")
    il_parser.add_argument("--intervals-days", type=int, default=730, help="Intervals sync range (days)")
    il_parser.add_argument("--runalyze-days", type=int, default=730, help="Runalyze sync range (days)")
    il_parser.add_argument("--include-streams", action="store_true", help="Include stream data")
    il_parser.add_argument("--recompute-days", type=int, default=730, help="engine.recompute_all days")
    il_parser.add_argument(
        "--steps", default="1,2,3,4,5,6,7,8,9",
        help="Comma-separated step numbers to run (e.g. '1,2,3,7,8,9')",
    )
    il_parser.add_argument("--dry-run", action="store_true", help="Simulate without DB changes")

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

        elif args.command == "initial-load":
            steps = _parse_steps(args.steps)
            _run_initial_load(conn, args, steps)

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


def _parse_steps(steps_str: str) -> list[int]:
    """'1,2,3,7,8,9' → [1, 2, 3, 7, 8, 9]."""
    try:
        return sorted(set(int(s.strip()) for s in steps_str.split(",")))
    except ValueError:
        log.error("Invalid --steps format: %s", steps_str)
        sys.exit(1)


def _run_initial_load(conn, args, steps: list[int]):
    """Steps 1–9 순차 실행."""
    from datetime import datetime, timezone

    print("\n" + "=" * 60)
    print("INITIAL LOAD")
    print(f"Steps: {steps}  dry-run={args.dry_run}")
    print("=" * 60)

    garmin_api = None
    configs = {}

    # Step 1: Garmin Bulk Export ZIP
    if 1 in steps:
        _il_step(1, "Garmin Bulk Export ZIP 로드")
        if not args.zip_path:
            log.warning("Step 1: --zip-path 없음. Skip.")
        elif args.dry_run:
            print("  [dry-run] GarminBulkLoader.load() 호출 생략")
        else:
            from src.sync.garmin_bulk_loader import GarminBulkLoader
            result = GarminBulkLoader(conn).load(args.zip_path)
            print(f"  loaded={result.synced_count} skipped={result.skipped_count} errors={result.error_count}")
        _il_done(1)

    # Step 2: Garmin API 보충
    if 2 in steps:
        _il_step(2, f"Garmin API 보충 sync (days={args.garmin_days})")
        if args.dry_run:
            print("  [dry-run] Garmin sync 생략")
        else:
            garmin_api = garmin_api or _init_garmin_api()
            if garmin_api:
                from src.sync.garmin_activity_sync import sync as garmin_sync
                r = garmin_sync(conn, garmin_api, days=args.garmin_days, include_streams=args.include_streams)
                print(f"  synced={r.synced_count} skipped={r.skipped_count} errors={r.error_count}")
            else:
                log.warning("Step 2: Garmin login failed. Skip.")
        _il_done(2)

    # Step 3: Garmin Wellness
    if 3 in steps:
        _il_step(3, f"Garmin Wellness sync (days={args.garmin_days})")
        if args.dry_run:
            print("  [dry-run] Garmin wellness sync 생략")
        else:
            garmin_api = garmin_api or _init_garmin_api()
            if garmin_api:
                from src.sync.garmin_wellness_sync import sync as gwellness_sync
                r = gwellness_sync(conn, garmin_api, days=args.garmin_days)
                print(f"  synced={r.synced_count} skipped={r.skipped_count} errors={r.error_count}")
            else:
                log.warning("Step 3: Garmin login failed. Skip.")
        _il_done(3)

    # Step 4: Strava 전체 sync
    if 4 in steps:
        _il_step(4, f"Strava 전체 sync (days={args.strava_days})")
        if args.dry_run:
            print("  [dry-run] Strava sync 생략")
        else:
            try:
                from src.utils.config import load_config
                from src.sync.strava_activity_sync import sync as strava_sync
                cfg = load_config().get("strava", {})
                r = strava_sync(
                    conn, cfg,
                    days=args.strava_days,
                    include_streams=args.include_streams,
                )
                print(f"  synced={r.synced_count} skipped={r.skipped_count} errors={r.error_count}")
                if r.retry_after:
                    log.warning("Strava rate limited. Retry after: %s", r.retry_after)
            except Exception as e:
                log.error("Step 4 failed: %s", e)
        _il_done(4)

    # Step 5: Intervals 전체 sync
    if 5 in steps:
        _il_step(5, f"Intervals 전체 sync (days={args.intervals_days})")
        if args.dry_run:
            print("  [dry-run] Intervals sync 생략")
        else:
            try:
                from src.utils.config import load_config
                from src.sync.intervals_activity_sync import sync as intervals_sync
                from src.sync.intervals_wellness_sync import sync as intervals_wellness
                cfg = load_config().get("intervals", {})
                r = intervals_sync(conn, cfg, days=args.intervals_days)
                print(f"  activity: synced={r.synced_count} skipped={r.skipped_count} errors={r.error_count}")
                rw = intervals_wellness(conn, cfg, days=args.intervals_days)
                print(f"  wellness: synced={rw.synced_count} skipped={rw.skipped_count} errors={rw.error_count}")
            except Exception as e:
                log.error("Step 5 failed: %s", e)
        _il_done(5)

    # Step 6: Runalyze 전체 sync
    if 6 in steps:
        _il_step(6, f"Runalyze 전체 sync (days={args.runalyze_days})")
        if args.dry_run:
            print("  [dry-run] Runalyze sync 생략")
        else:
            try:
                from src.utils.config import load_config
                from src.sync.runalyze_activity_sync import sync as runalyze_sync
                cfg = load_config().get("runalyze", {})
                r = runalyze_sync(conn, cfg, days=args.runalyze_days)
                print(f"  synced={r.synced_count} skipped={r.skipped_count} errors={r.error_count}")
            except Exception as e:
                log.error("Step 6 failed: %s", e)
        _il_done(6)

    # Step 7: Dedup
    if 7 in steps:
        _il_step(7, "Dedup")
        if args.dry_run:
            print("  [dry-run] dedup.run() 생략")
        else:
            from src.sync.dedup import run as run_dedup
            groups = run_dedup(conn)
            conn.commit()
            print(f"  {groups} 그룹 생성")
        _il_done(7)

    # Step 8: Metric Engine 전체 재계산
    if 8 in steps:
        _il_step(8, f"Metric Engine 전체 재계산 (days={args.recompute_days})")
        if args.dry_run:
            print("  [dry-run] engine.recompute_all() 생략")
        else:
            from src.metrics.engine import recompute_all
            recompute_all(conn, days=args.recompute_days)
            conn.commit()
            print("  완료")
        _il_done(8)

    # Step 9: Primary Resolution
    if 9 in steps:
        _il_step(9, "Primary Resolution")
        if args.dry_run:
            print("  [dry-run] resolve_all_primaries() 생략")
        else:
            from src.utils.metric_priority import resolve_all_primaries
            count = resolve_all_primaries(conn)
            conn.commit()
            print(f"  {count} 그룹 처리")
        _il_done(9)

    print("\n" + "=" * 60)
    print("INITIAL LOAD COMPLETE")
    print("=" * 60)


def _il_step(n: int, desc: str):
    print(f"\n[Step {n}] {desc}")


def _il_done(n: int):
    print(f"  ✓ Step {n} done")


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
