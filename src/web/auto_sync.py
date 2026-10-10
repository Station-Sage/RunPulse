"""자동 주기 동기화 — 설정된 간격마다 incremental sync 트리거.

config.auto_sync:
  enabled (bool, default True)
  interval_hours (int, default 4)
  days (int, default 2)  — 동기화 범위 (오늘 기준 N일 전부터)
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _connected_sources(config: dict) -> list[str]:
    sources = []
    if config.get("garmin", {}).get("email"):
        sources.append("garmin")
    if config.get("strava", {}).get("refresh_token"):
        sources.append("strava")
    if config.get("intervals", {}).get("api_key"):
        sources.append("intervals")
    if config.get("runalyze", {}).get("token"):
        sources.append("runalyze")
    from src.utils.config import enabled_sources
    enabled = enabled_sources(config)
    return [s for s in sources if s in enabled]


def _trigger(config: dict, user_id: str, days: int) -> None:
    from src.web.bg_sync import start_basic_sync
    from src.utils.user_context import set_current_user
    set_current_user(user_id)

    # 화면에서 바꾼 포함 목록·자격증명이 재시작 없이 반영되도록 실행마다 다시 읽는다
    try:
        from src.utils.config import load_config
        config = load_config(user_id=user_id)
    except Exception as exc:
        log.warning("[auto_sync] config 재로딩 실패 — 시작 시점 사본 사용: %s", exc)

    sources = _connected_sources(config)
    if not sources:
        log.info("[auto_sync] 연결된 소스 없음 — 스킵")
        return

    to_date = date.today().isoformat()
    from_date = (date.today() - timedelta(days=days)).isoformat()
    from_dates = {s: from_date for s in sources}

    log.info("[auto_sync] 트리거: sources=%s, %s ~ %s", sources, from_date, to_date)
    try:
        result = start_basic_sync(sources, from_dates, to_date, config, user_id, source_path="auto")
        log.info("[auto_sync] 완료: jobs=%s", result)
    except Exception as exc:
        log.error("[auto_sync] 실패: %s", exc, exc_info=True)


def _loop(config: dict, user_id: str, interval_hours: int, days: int) -> None:
    log.info("[auto_sync] 루프 시작: interval=%dh, days=%d, user=%s", interval_hours, days, user_id)
    while not _stop_event.is_set():
        try:
            from src.utils.sync_ledger_query import last_auto_run
            last = last_auto_run(user_id)
            now = datetime.now()
            if last is None or (now - last) >= timedelta(hours=interval_hours):
                _trigger(config, user_id, days)
            else:
                remaining = timedelta(hours=interval_hours) - (now - last)
                log.debug("[auto_sync] 다음 실행까지 %s", remaining)
        except Exception as exc:
            log.error("[auto_sync] 루프 오류: %s", exc, exc_info=True)
        # 1시간마다 wake-up해서 interval 도달 여부 재확인
        _stop_event.wait(timeout=3600)
    log.info("[auto_sync] 루프 종료")


def start(config: dict, user_id: str = "default") -> None:
    """auto_sync daemon thread 시작. 이미 실행 중이면 스킵."""
    global _thread

    auto_cfg = config.get("auto_sync", {})
    if not auto_cfg.get("enabled", True):
        log.info("[auto_sync] 비활성화됨 (config.auto_sync.enabled=false)")
        return

    if _thread and _thread.is_alive():
        log.debug("[auto_sync] 이미 실행 중")
        return

    interval_hours = max(1, int(auto_cfg.get("interval_hours", 4)))
    days = max(1, int(auto_cfg.get("days", 2)))

    _stop_event.clear()
    _thread = threading.Thread(
        target=_loop,
        args=(config, user_id, interval_hours, days),
        daemon=True,
        name="auto-sync",
    )
    _thread.start()


def stop() -> None:
    """현재 실행 중인 auto_sync thread 중단."""
    _stop_event.set()


def restart(config: dict, user_id: str = "default") -> None:
    """설정 변경 후 thread 재시작."""
    stop()
    if _thread and _thread.is_alive():
        _thread.join(timeout=5)
    start(config, user_id)


def status() -> dict:
    """현재 상태 반환 (UI 표시용)."""
    from src.utils.sync_ledger_query import last_auto_run
    last = last_auto_run()
    return {
        "running": bool(_thread and _thread.is_alive()),
        "last_run": last.isoformat(timespec="seconds") if last else None,
    }
