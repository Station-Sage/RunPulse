"""실행 전 안전 게이트 — 하나라도 막히면 실행하지 않는다(fail-closed).

run_unit.py의 진입점에서만 호출한다. 확인 순서(싼 것 → 비싼 것):
STOP/PAUSE 파일 → 시간대 → 최근 활동(유휴) → 연속 실패(circuit breaker) → 예산(원장).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import ledger, settings

_KST = ZoneInfo("Asia/Seoul")
# 이 프로젝트의 실제(대화형) 세션 transcript 위치. autopilot 자신의 claude -p 실행은
# --no-session-persistence로 돌기 때문에 여기 기록되지 않는다 — 자기 자신을 유휴로 오判하지 않는다.
_LIVE_SESSIONS_DIR = Path.home() / ".claude" / "projects" / "-home-ubuntu-projects-RunPulse"


@dataclass
class GateResult:
    allowed: bool
    reason: str = ""


def _check_stop() -> GateResult | None:
    if settings.STOP_PATH.exists():
        return GateResult(False, "STOP 파일 존재 — 수동으로 지울 때까지 정지")
    return None


def _check_pause() -> GateResult | None:
    if settings.PAUSE_PATH.exists():
        return GateResult(False, "PAUSE 파일 존재")
    return None


def _check_night_window(now: datetime | None = None) -> GateResult | None:
    now = now or datetime.now(_KST)
    h = now.hour
    in_window = (
        settings.NIGHT_START_HOUR <= h < settings.NIGHT_END_HOUR
        if settings.NIGHT_START_HOUR < settings.NIGHT_END_HOUR
        else (h >= settings.NIGHT_START_HOUR or h < settings.NIGHT_END_HOUR)
    )
    if not in_window:
        return GateResult(False, f"실행 시간대 아님 (KST {h:02d}시, 허용 {settings.NIGHT_START_HOUR:02d}-{settings.NIGHT_END_HOUR:02d}시)")
    return None


def _check_idle() -> GateResult | None:
    if not _LIVE_SESSIONS_DIR.exists():
        return None
    newest = 0.0
    for f in _LIVE_SESSIONS_DIR.glob("*.jsonl"):
        newest = max(newest, f.stat().st_mtime)
    if newest == 0.0:
        return None
    idle_min = (time.time() - newest) / 60
    if idle_min < settings.IDLE_MINUTES_REQUIRED:
        return GateResult(False, f"최근 활동 {idle_min:.0f}분 전 — 유휴 {settings.IDLE_MINUTES_REQUIRED}분 필요")
    return None


def _check_circuit_breaker() -> GateResult | None:
    recent = ledger.last(settings.CIRCUIT_BREAKER_FAILS)
    if len(recent) == settings.CIRCUIT_BREAKER_FAILS and all(
        e.get("outcome") == "error" for e in recent
    ):
        return GateResult(
            False,
            f"연속 실패 {settings.CIRCUIT_BREAKER_FAILS}회 — 원인 확인 전까지 정지 "
            f"({settings.STOP_PATH} 를 만들거나 원인 해결 후 ledger 확인)",
        )
    return None


def _check_budget() -> GateResult | None:
    decision = ledger.check_budget()
    if not decision.allowed:
        return GateResult(False, decision.reason)
    return None


_CHECKS = (_check_stop, _check_pause, _check_night_window, _check_idle,
           _check_circuit_breaker, _check_budget)


def check(
    *, ignore_night_window: bool = False, ignore_idle: bool = False,
    ignore_budget: bool = False,
) -> GateResult:
    """ignore_* 는 사람이 지켜보며 하는 수동 검증 전용 — 스케줄 실행에서는 절대 쓰지 않는다."""
    skip = set()
    if ignore_night_window:
        skip.add(_check_night_window)
    if ignore_idle:
        skip.add(_check_idle)
    if ignore_budget:
        skip.add(_check_budget)
    for fn in _CHECKS:
        if fn in skip:
            continue
        blocked = fn()
        if blocked is not None:
            return blocked
    return GateResult(True, "ok")
