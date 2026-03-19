"""데이터 동기화 CLI 진입점."""

import argparse
import sqlite3
import sys

from src.db_setup import get_db_path, init_db
from src.utils.config import load_config
from src.sync.garmin import sync_activities as garmin_act, sync_wellness as garmin_well
from src.sync.strava import sync_activities as strava_act
from src.sync.intervals import sync_activities as intervals_act, sync_wellness as intervals_well
from src.sync.runalyze import sync_activities as runalyze_act


# (sync_activities, sync_wellness or None)
SOURCES: dict[str, tuple] = {
    "garmin": (garmin_act, garmin_well),
    "strava": (strava_act, None),
    "intervals": (intervals_act, intervals_well),
    "runalyze": (runalyze_act, None),
}


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
    args = parser.parse_args()

    config = load_config()
    init_db()
    db_path = get_db_path()
    sources = list(SOURCES.keys()) if args.source == "all" else [args.source]

    total_activities = 0
    total_wellness = 0

    with sqlite3.connect(db_path) as conn:
        for source in sources:
            sync_act_fn, sync_well_fn = SOURCES[source]
            print(f"\n--- {source.upper()} 동기화 시작 ---")

            try:
                count = sync_act_fn(config, conn, args.days)
                total_activities += count
                print(f"[{source}] 활동 {count}개 동기화 완료")
            except Exception as e:
                print(f"[{source}] 활동 동기화 실패: {e}", file=sys.stderr)

            if sync_well_fn:
                try:
                    count = sync_well_fn(config, conn, args.days)
                    total_wellness += count
                    print(f"[{source}] 웰니스 {count}개 동기화 완료")
                except Exception as e:
                    print(f"[{source}] 웰니스 동기화 실패: {e}", file=sys.stderr)

    print(f"\n동기화 완료: 활동 {total_activities}개, 웰니스 {total_wellness}개")


if __name__ == "__main__":
    main()
