"""데이터 동기화 CLI 진입점."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from src.db_setup import get_db_path, init_db
from src.utils.config import load_config
from src.utils.sync_state import set_current_user

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

    # sync_state가 올바른 유저 파일에 기록되도록 설정
    set_current_user(args.user)

    config = load_config(user_id=args.user)
    init_db(args.user)
    db_path = get_db_path(args.user)
    sources = _ALL_SOURCES if args.source == "all" else [args.source]

    total_activities = 0
    total_wellness = 0

    if len(sources) == 1:
        source = sources[0]
        print(f"\n--- {source.upper()} 동기화 시작 ---")
        res = _sync_source(source, config, db_path, args.days)
        total_activities += res["activities"]
        total_wellness += res["wellness"]
        print(f"[{source}] 활동 {res['activities']}개, 웰니스 {res['wellness']}개 동기화 완료")
        for err in res["errors"]:
            print(f"[{source}] {err}", file=sys.stderr)
    else:
        print(f"4소스 병렬 동기화 시작 ({', '.join(sources)})")
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
                print(f"[{source}] 활동 {res['activities']}개, 웰니스 {res['wellness']}개 동기화 완료")
                for err in res["errors"]:
                    print(f"[{source}] {err}", file=sys.stderr)
            except Exception as e:
                print(f"[{source}] 예외 발생: {e}", file=sys.stderr)

    print(f"\n동기화 완료: 활동 {total_activities}개, 웰니스 {total_wellness}개")

    # 메트릭 자동 재계산
    print("메트릭 계산 시작...")
    try:
        from src.metrics import engine as metrics_engine
        start_date = (date.today() - timedelta(days=args.days)).isoformat()
        end_date = date.today().isoformat()
        with sqlite3.connect(str(db_path)) as conn:
            metrics_engine.run_for_date_range(conn, start_date, end_date)
        print(f"메트릭 계산 완료 ({start_date} ~ {end_date})")
    except Exception as exc:
        print(f"메트릭 계산 실패 (sync는 정상 완료): {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
