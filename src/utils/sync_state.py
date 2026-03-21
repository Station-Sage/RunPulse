"""동기화 상태 관리 — 실행 중 여부, 마지막 동기화 시각, rate limit 상태, 오류.

상태는 sync_state.json 파일에 저장된다 (gitignore).
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_SERVICES = ("garmin", "strava", "intervals", "runalyze")


def _state_path() -> Path:
    """sync_state.json 경로 — 프로젝트 루트에 저장."""
    return Path(__file__).resolve().parent.parent.parent / "sync_state.json"


def _load() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(state: dict) -> None:
    path = _state_path()
    try:
        path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[sync_state] 상태 저장 실패: {e}")


# ── 조회 함수 ────────────────────────────────────────────────────────────

def get_service_state(service: str) -> dict:
    """서비스의 전체 상태 반환."""
    return _load().get(service, {})


def is_running(service: str) -> bool:
    """현재 동기화 실행 중 여부."""
    return bool(_load().get(service, {}).get("is_running", False))


def get_last_sync_at(service: str) -> datetime | None:
    """마지막 동기화 완료 시각 반환."""
    val = _load().get(service, {}).get("last_sync_at")
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        return None


def get_retry_after_sec(service: str) -> int | None:
    """재시도 가능까지 남은 초. 없거나 만료됐으면 None."""
    retry_at_str = _load().get(service, {}).get("retry_after")
    if not retry_at_str:
        return None
    try:
        retry_at = datetime.fromisoformat(retry_at_str)
        remain = int((retry_at - datetime.now()).total_seconds())
        return remain if remain > 0 else None
    except Exception:
        return None


def get_rate_state(service: str) -> dict:
    """저장된 rate limit 상태 반환."""
    return _load().get(service, {}).get("rate_state", {})


def get_all_states() -> dict[str, dict]:
    """전체 서비스 상태 요약 반환 (UI 표시용).

    Returns:
        {"garmin": {"is_running": bool, "last_sync_at": str|None,
                    "cooldown_sec": int|None, "last_error": str|None}, ...}
    """
    from src.utils.sync_policy import check_incremental_guard

    raw = _load()
    result = {}
    for svc in _SERVICES:
        s = raw.get(svc, {})
        last_sync_at = get_last_sync_at(svc)
        guard = check_incremental_guard(svc, last_sync_at)
        result[svc] = {
            "is_running": bool(s.get("is_running", False)),
            "last_sync_at": s.get("last_sync_at"),
            "cooldown_sec": guard.retry_after_sec if not guard.allowed else None,
            "cooldown_msg": guard.message_ko if not guard.allowed else None,
            "last_error": s.get("last_error"),
            "last_count": s.get("last_count", 0),
            "last_partial": bool(s.get("last_partial", False)),
            "rate_state": s.get("rate_state", {}),
        }
    return result


# ── 변경 함수 ────────────────────────────────────────────────────────────

def mark_running(service: str, mode: str) -> None:
    """동기화 시작 기록."""
    with _LOCK:
        state = _load()
        state.setdefault(service, {})
        state[service]["is_running"] = True
        state[service]["current_mode"] = mode
        state[service]["started_at"] = datetime.now().isoformat(timespec="seconds")
        state[service]["last_error"] = None  # 이전 오류 초기화
        _save(state)


def mark_finished(
    service: str,
    count: int = 0,
    partial: bool = False,
    error: str | None = None,
    rate_state: dict | None = None,
) -> None:
    """동기화 완료 기록."""
    with _LOCK:
        state = _load()
        state.setdefault(service, {})
        now_str = datetime.now().isoformat(timespec="seconds")
        state[service]["is_running"] = False
        state[service]["last_sync_at"] = now_str
        state[service]["last_count"] = count
        state[service]["last_partial"] = partial
        state[service]["last_error"] = error
        if rate_state:
            state[service]["rate_state"] = rate_state
        _save(state)


def set_retry_after(service: str, seconds: int) -> None:
    """429 등 발생 시 재시도 가능 시각 설정."""
    with _LOCK:
        state = _load()
        state.setdefault(service, {})
        retry_at = (datetime.now() + timedelta(seconds=seconds)).isoformat(
            timespec="seconds"
        )
        state[service]["retry_after"] = retry_at
        _save(state)


def clear_retry_after(service: str) -> None:
    """재시도 제한 해제."""
    with _LOCK:
        state = _load()
        if service in state:
            state[service].pop("retry_after", None)
            _save(state)
