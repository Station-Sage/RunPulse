"""데이터 동기화 CLI 진입점."""

import logging
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.log_config import setup_logging
setup_logging()

import argparse
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from src.db_setup import get_db_path, init_db
from src.utils.config import load_config
from src.utils.sync_state import set_current_user

log = logging.getLogger(__name__)

_ALL_SOURCES = ["garmin", "strava", "intervals", "runalyze"]


def _sync_source(source: str, config: dict, db_path, days: int) -> dict:
    """단일 소스 동기화. {"activities": int, "wellness": int, "errors": list} 반환."""
    activities = 0
    wellness = 0
    errors = []
    try:
        with sqlite3.connect(str(db_path), timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            if source == "garmin":
                from src.sync.garmin import sync_garmin
                res = sync_garmin(config, conn, days)
                activities = res.get("activity_summaries", 0)
                wellness = res.get("wellness", 0)
            elif source == "strava":
                from src.sync.strava import sync_strava
                res = sync_strava(config, conn, days)
                activities = res.get("activities", 0)
            elif source == "intervals":
                from src.sync.intervals import sync_intervals
                res = sync_intervals(config, conn, days)
                activities = res.get("activities", 0)
                wellness = res.get("wellness", 0)
            elif source == "runalyze":
                from src.sync.runalyze import sync_activities as sync_runalyze
                activities = sync_runalyze(config, conn, days)
            conn.commit()
    except Exception as e:
        errors.append(str(e))
    return {"activities": activities, "wellness": wellness, "errors": errors}


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="RunPulse 데이터 동기화")
    parser.add_argument(
        "--source",
        choices=["garmin", "strava", "intervals", "runalyze", "all"],
        default="all",
        help="동기화할 데이터 소스 (기본: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="가져올 일수 (기본: 7)",
    )
    parser.add_argument(
        "--user",
        default="default",
        help="사용자 ID (기본: default)",
    )
    args = parser.parse_args()

    set_current_user(args.user)

    config = load_config(user_id=args.user)
    init_db(args.user)
    db_path = get_db_path(args.user)
    sources = _ALL_SOURCES if args.source == "all" else [args.source]

    total_activities = 0
    total_wellness = 0

    if len(sources) == 1:
        source = sources[0]
        log.info("--- %s 동기화 시작 ---", source.upper())
        res = _sync_source(source, config, db_path, args.days)
        total_activities += res["activities"]
        total_wellness += res["wellness"]
        log.info("[%s] 활동 %d개, 웰니스 %d개 동기화 완료", source, res["activities"], res["wellness"])
        for err in res["errors"]:
            log.error("[%s] %s", source, err)
    else:
        log.info("4소스 병렬 동기화 시작 (%s)", ", ".join(sources))
        futures = {}
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            for source in sources:
                future = executor.submit(_sync_source, source, config, db_path, args.days)
                futures[future] = source

        for future, source in futures.items():
            try:
                res = future.result()
                total_activities += res["activities"]
                total_wellness += res["wellness"]
                log.info("[%s] 활동 %d개, 웰니스 %d개 동기화 완료", source, res["activities"], res["wellness"])
                for err in res["errors"]:
                    log.error("[%s] %s", source, err)
            except Exception as e:
                log.error("[%s] 예외 발생: %s", source, e)

    log.info("동기화 완료: 활동 %d개, 웰니스 %d개", total_activities, total_wellness)

    log.info("메트릭 계산 시작...")
    try:
        from src.metrics import engine as metrics_engine
        start_date = (date.today() - timedelta(days=args.days)).isoformat()
        end_date = date.today().isoformat()
        with sqlite3.connect(str(db_path)) as conn:
            metrics_engine.run_for_date_range(conn, start_date, end_date)
        log.info("메트릭 계산 완료 (%s ~ %s)", start_date, end_date)
    except Exception as exc:
        log.error("메트릭 계산 실패 (sync는 정상 완료): %s", exc)


if __name__ == "__main__":
    main()
