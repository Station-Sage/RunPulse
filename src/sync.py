"""데이터 동기화 CLI 진입점."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
from concurrent.futures import ThreadPoolExecutor

from src.db_setup import get_db_path, init_db
from src.utils.config import load_config
from src.sync import SOURCES, _sync_source


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

    if len(sources) == 1:
        # 단일 소스: 직접 실행
        source = sources[0]
        print(f"\n--- {source.upper()} 동기화 시작 ---")
        res = _sync_source(source, config, db_path, args.days)
        total_activities += res["activities"]
        total_wellness += res["wellness"]
        print(f"[{source}] 활동 {res['activities']}개, 웰니스 {res['wellness']}개 동기화 완료")
        for err in res["errors"]:
            print(f"[{source}] {err}", file=sys.stderr)
    else:
        # 복수 소스: ThreadPoolExecutor 병렬 실행
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


if __name__ == "__main__":
    main()
