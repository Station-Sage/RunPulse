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
        from src.sync.bg_sync import cancel_job
        cancelled = cancel_job(provider, user_id)
    return {"provider": provider, "sync_enabled": provider in enabled_sources(config),
            "cancelled_job_ids": cancelled, "auto_sync_applies": "next_run"}


def auto_settings(config: dict, last_run: datetime | None, now: datetime | None = None,
                  user_id: str | None = None) -> dict:
    """자동 동기화 설정·다음 실행 예정 시각·상태(state: active|dormant|auth_suspended).

    multi 스케줄러면 next_run_at 은 ops.db 의 next_due_at(지터·백오프·휴면 반영)을 쓴다.
    """
    cfg = {**_DEFAULTS, **(config.get("auto_sync") or {})}
    hours = int(cfg["interval_hours"])
    next_run = None
    now = now or datetime.now()
    if cfg["enabled"]:
        due = last_run + timedelta(hours=hours) if last_run else now
        next_run = max(due, now).isoformat(timespec="seconds")
    state, sched_due = _sched_state(config, user_id)
    if cfg["enabled"] and sched_due is not None:
        next_run = max(sched_due, now).isoformat(timespec="seconds")
    if state == "dormant":
        next_run = None
    return {
        "state": state,
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


def _sched_state(config: dict, user_id: str | None) -> tuple[str, datetime | None]:
    """(state, multi 스케줄러 next_due 또는 None). 조회 실패는 active 로 본다."""
    if user_id is None:
        return "active", None
    state, due = "active", None
    try:
        from src.sync.auto_sync import _connected_sources, scheduler_mode
        from src.utils.sync_gates import gate
        if scheduler_mode() == "multi":
            from src.ops.store import default_store
            st = default_store().get_state(user_id)
            if st:
                due = st["next_due_at"]
                state = "dormant" if st["state"] == "dormant" else state
        srcs = _connected_sources(config)
        if state == "active" and srcs and all(
                (g := gate(s, user_id)) is not None and g.reason_code == "auth_suspended" for s in srcs):
            state = "auth_suspended"
    except Exception:  # noqa: BLE001 — 표시용, 실패해도 설정 응답은 낸다
        return "active", None
    return state, due


def patch_auto(config: dict, user_id: str, changes: dict) -> dict:
    """auto_sync 설정을 저장하고 스케줄러에 반영한다.

    legacy: 스레드 재시작(현행). multi: 단일 스케줄러를 이 사용자로 바꾸지 않고 poke(uid)만 — 다른 사용자 설정
    저장이 스케줄러를 가로채던 결함 해소(multiuser-sync §2.1·§6).
    """
    from src.utils.sync_ledger_query import last_auto_run
    from src.sync.auto_sync import restart, scheduler_mode

    config["auto_sync"] = {**_DEFAULTS, **(config.get("auto_sync") or {}), **changes}
    save_config(config, user_id=user_id)
    if scheduler_mode() == "multi":
        from src.sync.scheduler_run import poke
        poke(user_id)
    else:
        restart(config, user_id)
    return auto_settings(config, last_auto_run(user_id), user_id=user_id)


