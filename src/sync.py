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
from src.utils.config import enabled_sources, load_config
from src.utils.sync_state import set_current_user

log = logging.getLogger(__name__)

_ALL_SOURCES = ["garmin", "strava", "intervals", "runalyze"]


def _sync_source(
    source: str, config: dict, db_path, days: int, user_id: str = "default",
    job_id: str | None = None, trigger: str = "cli",
) -> dict:
    """단일 소스 동기화. {"activities": int, "wellness": int, "errors": list} 반환. 원장(sync_jobs.db)에도 기록."""
    from src.utils.sync_state import mark_finished
    from src.sync.ledger import start_run, finish_run
    from src.sync.sync_errors import SyncSourceError, classify_exception
    try:
        job_id = start_run(source, source_path=trigger, job_id=job_id, days=days)
    except Exception as led_exc:
        log.warning("[%s] 원장 기록 시작 실패: %s", source, led_exc)
        job_id = None
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
        err_msg = str(e)
        errors.append(err_msg)
        try:
            mark_finished(source, count=0, error=err_msg, user_id=user_id)
        except Exception:
            pass
        if job_id:
            try:
                if isinstance(e, SyncSourceError):
                    sse = e
                else:
                    code, http = classify_exception(e)
                    sse = SyncSourceError(code, err_msg, http)
                finish_run(job_id, synced=activities, error=sse)
            except Exception as led_exc:
                log.warning("[%s] 원장 기록 실패: %s", source, led_exc)
    else:
        if job_id:
            try:
                finish_run(job_id, synced=activities)
            except Exception as led_exc:
                log.warning("[%s] 원장 기록 실패: %s", source, led_exc)
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
    parser.add_argument("--job-id", default=None, help="원장 job id (단일 소스 수동 실행용)")
    parser.add_argument(
        "--trigger", default="cli", choices=["manual", "auto", "cli", "bg"],
        help="실행 경로 (원장 source_path, 기본: cli)",
    )
    args = parser.parse_args()

    set_current_user(args.user)

    config = load_config(user_id=args.user)
    init_db(args.user)
    db_path = get_db_path(args.user)
    sources = enabled_sources(config) if args.source == "all" else [args.source]

    total_activities = 0
    total_wellness = 0

    if len(sources) == 1:
        source = sources[0]
        log.info("--- %s 동기화 시작 ---", source.upper())
        res = _sync_source(source, config, db_path, args.days, user_id=args.user,
                           job_id=args.job_id, trigger=args.trigger)
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
                future = executor.submit(_sync_source, source, config, db_path, args.days, args.user,
                                         None, args.trigger)
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
        from src.services import milestone_service
        start_date = (date.today() - timedelta(days=args.days)).isoformat()
        end_date = date.today().isoformat()
        with sqlite3.connect(str(db_path)) as conn:
            try:  # 외기 기상(P7-PRED-32) — 예측·기온 보정 입력이므로 메트릭 계산 전에
                from src.utils.api import get as api_get
                from src.weather.activity_weather import ingest_activity_weather
                log.info("기상 인제스트: %s", ingest_activity_weather(conn, api_get, since=start_date, max_requests=200))
            except Exception as w_exc:
                log.error("기상 인제스트 실패 (sync는 정상 완료): %s", w_exc)
            metrics_engine.run_for_date_range(conn, start_date, end_date)
            try:
                filled = metrics_engine.backfill_missing_loads(conn)
                if filled:
                    log.info("부하 누락 보정: %d일 재계산", len(filled))
            except Exception as bf_exc:
                log.error("부하 누락 보정 실패 (sync는 정상 완료): %s", bf_exc)
            try:
                new_milestones = milestone_service.detect_and_store_milestones(
                    conn, start_date, end_date
                )
                if new_milestones:
                    log.info("마일스톤 %d건 신규 등록", len(new_milestones))
            except Exception as ms_exc:
                log.error("마일스톤 탐지 실패 (sync는 정상 완료): %s", ms_exc)
        log.info("메트릭 계산 완료 (%s ~ %s)", start_date, end_date)
    except Exception as exc:
        log.error("메트릭 계산 실패 (sync는 정상 완료): %s", exc)


if __name__ == "__main__":
    main()
