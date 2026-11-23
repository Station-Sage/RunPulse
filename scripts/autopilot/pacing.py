"""사용량 페이싱 — USD 프록시 대신 실제 rate_limit 관측(5시간 세션·주간)으로 실행 여부를 판정한다.

원장의 rate_limit 필드(utilization, resetsAt, status)는 사람 사용량까지 포함한 실제 계정 사용률이다.
- 5시간 세션: utilization 이 SESSION_CEILING 이상이거나 거부 상태면 resetsAt 까지 대기(무한 반복 아님).
- 주간(목 22:00 KST 리셋): 경과 비율을 따라 균등 배분한 목표선(+PACE_SLACK)과 WEEK_CEILING 중 낮은 쪽을 넘으면 대기.
관측이 없거나 만료(resetsAt 경과)면 보수적 대체값(5시간 창 실행 수·USD)으로 판정한다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import ledger, settings

_KST = ZoneInfo("Asia/Seoul")
SESSION_SEC = 5 * 3600
WEEK_SEC = 7 * 24 * 3600


@dataclass
class Pacing:
    allowed: bool
    reason: str = ""
    resume_at: float | None = None


def week_start(now: float) -> float:
    """직전 목요일 22:00 KST (주간 리셋 시각)."""
    dt = datetime.fromtimestamp(now, _KST)
    start = dt.replace(hour=22, minute=0, second=0, microsecond=0) - timedelta(days=(dt.weekday() - 3) % 7)
    if start > dt:
        start -= timedelta(days=7)
    return start.timestamp()


def latest_observation(entries: list[dict], rtype: str, now: float) -> dict | None:
    """해당 유형의 가장 최근 rate_limit 관측 — 이미 리셋된(resetsAt 경과) 것은 무효."""
    for e in reversed(entries):
        rl = e.get("rate_limit") or {}
        if rl.get("rateLimitType") == rtype:
            return rl if rl.get("resetsAt", 0) > now else None
    return None


def weekly_target(now: float, reset_at: float | None = None) -> float:
    """균등 배분 목표 사용률(0~1) — 주 시작 직후에도 최소 PACE_FLOOR 는 허용."""
    reset_at = reset_at or week_start(now) + WEEK_SEC
    elapsed = min(max((now - (reset_at - WEEK_SEC)) / WEEK_SEC, 0.0), 1.0)
    return min(settings.WEEK_CEILING, settings.PACE_FLOOR + elapsed * settings.PACE_SLACK)


def hold_until(now: float) -> float | None:
    """수동 보류 — STATE_DIR/hold_until 에 epoch 초(리셋 시각)를 적으면 그때까지 모든 실행을 막는다."""
    try:
        t = float((settings.STATE_DIR / "hold_until").read_text().strip())
    except (OSError, ValueError):
        return None
    return t if t > now else None


def check(now: float | None = None, entries: list[dict] | None = None) -> Pacing:
    now = now or time.time()
    held = hold_until(now)
    if held:
        return Pacing(False, "수동 보류(hold_until)", held)
    entries = ledger.read_all() if entries is None else entries
    sess = latest_observation(entries, "five_hour", now)
    if sess and (sess.get("status") == "rejected" or sess.get("utilization", 0) >= settings.SESSION_CEILING):
        return Pacing(False, f"5시간 세션 사용률 {sess.get('utilization', 1):.0%} — 리셋까지 대기", sess["resetsAt"])
    wk = latest_observation(entries, "seven_day", now)
    if wk:
        target = weekly_target(now, wk["resetsAt"])
        if wk.get("status") == "rejected" or wk.get("utilization", 0) >= target:
            return Pacing(False, f"주간 사용률 {wk.get('utilization', 1):.0%} ≥ 균등 목표 {target:.0%} — 페이싱 대기", wk["resetsAt"])
    if not sess:
        recent = ledger.since(SESSION_SEC / 3600, entries)
        if len(recent) >= settings.FALLBACK_SESSION_MAX_RUNS or ledger.total_cost(recent) >= settings.FALLBACK_SESSION_MAX_USD:
            return Pacing(False, "5시간 관측 없음 — 대체 한도(실행 수·USD) 도달", recent[0]["ts"] + SESSION_SEC)
    return Pacing(True)
