"""Data 설정 쓰기 — 소스 동기화 on/off, 자동 동기화 설정 (design 40 §7.3)."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.config import enabled_sources, save_config, set_sync_source

INTERVAL_CHOICES = (1, 2, 4, 6, 12, 24)
_DEFAULTS = {"enabled": True, "interval_hours": 4, "days": 2}


def set_source_enabled(config: dict, user_id: str, provider: str, enabled: bool) -> dict:
    """소스 동기화 포함 여부를 저장한다. 끄면 활성 작업을 cancelled(재개 불가)로 마감한다."""
    set_sync_source(config, provider, enabled)
    save_config(config, user_id=user_id)
    cancelled: list[str] = []
    if not enabled:
        from src.web.bg_sync import cancel_job
        cancelled = cancel_job(provider, user_id)
    return {"provider": provider, "sync_enabled": provider in enabled_sources(config),
            "cancelled_job_ids": cancelled, "auto_sync_applies": "next_run"}


def auto_settings(config: dict, last_run: datetime | None, now: datetime | None = None) -> dict:
    """자동 동기화 설정과 다음 실행 예정 시각."""
    cfg = {**_DEFAULTS, **(config.get("auto_sync") or {})}
    hours = int(cfg["interval_hours"])
    next_run = None
    if cfg["enabled"]:
        now = now or datetime.now()
        due = last_run + timedelta(hours=hours) if last_run else now
        next_run = max(due, now).isoformat(timespec="seconds")
    return {
        "enabled": bool(cfg["enabled"]),
        "interval_h": hours,
        "window_days": int(cfg["days"]),
        "last_run_at": last_run.isoformat(timespec="seconds") if last_run else None,
        "next_run_at": next_run,
    }


def validate_auto_patch(body: dict) -> tuple[dict, str | None]:
    """PATCH 본문 → config.auto_sync 에 합칠 값. 오류면 (빈 dict, 메시지)."""
    out: dict = {}
    if "enabled" in body:
        if not isinstance(body["enabled"], bool):
            return {}, "enabled는 true/false여야 해요"
        out["enabled"] = body["enabled"]
    if "interval_h" in body:
        v = body["interval_h"]
        if isinstance(v, bool) or v not in INTERVAL_CHOICES:
            return {}, f"interval_h는 {list(INTERVAL_CHOICES)} 중 하나여야 해요"
        out["interval_hours"] = v
    if "window_days" in body:
        v = body["window_days"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 30:
            return {}, "window_days는 1~30 사이 정수여야 해요"
        out["days"] = v
    if not out:
        return {}, "바꿀 값이 없어요"
    return out, None


def patch_auto(config: dict, user_id: str, changes: dict) -> dict:
    """auto_sync 설정을 저장하고 스레드를 재시작한다."""
    from src.utils.sync_state import get_last_auto_sync
    from src.web.auto_sync import restart

    config["auto_sync"] = {**_DEFAULTS, **(config.get("auto_sync") or {}), **changes}
    save_config(config, user_id=user_id)
    restart(config, user_id)
    return auto_settings(config, get_last_auto_sync(user_id))


