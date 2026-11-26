"""사용량 페이싱 — USD 프록시 대신 실제 rate_limit 관측(5시간 세션·주간)으로 실행 여부를 판정한다.

원장의 rate_limit 필드(utilization, resetsAt, status)는 사람 사용량까지 포함한 실제 계정 사용률이다.
- 5시간 세션: utilization 이 SESSION_CEILING 이상이거나 거부 상태면 resetsAt 까지 대기(무한 반복 아님).
- 주간(목 22:00 KST 리셋): 경과 비율을 따라 균등 배분한 목표선(+PACE_SLACK)과 WEEK_CEILING 중 낮은 쪽을 넘으면 대기. 리셋 24시간 전부터는 WEEK_CEILING 까지 허용.
콘솔에서 WEEKLY_PACING_ENABLED=0 으로 끄면 주간 게이트만 건너뛴다(5시간·수동 보류 유지). 재개 시각은 목표선이 사용률에 닿는 때.
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
FINAL_DAY_SEC = 24 * 3600


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
    """해당 유형의 가장 최근 rate_limit 관측 — 이미 리셋된(resetsAt 경과) 것은 무효. unifiedWindows 에 실린 다른 창도 인정."""
    for e in reversed(entries):
        rl = e.get("rate_limit") or {}
        if rl.get("rateLimitType") == rtype:
            return rl if rl.get("resetsAt", 0) > now else None
        nested = (rl.get("unifiedWindows") or {}).get(rtype)  # 다른 유형 관측에 함께 실려 온 창
        if nested and nested.get("resetsAt", 0) > now:
            return nested
    return None


def last_session_reset(entries: list[dict]) -> float:
    """가장 최근 five_hour 관측의 resetsAt — 만료됐다면 그 시각 이후가 새 세션 창이다."""
    for e in reversed(entries):
        rl = e.get("rate_limit") or {}
        if rl.get("rateLimitType") == "five_hour":
            return float(rl.get("resetsAt", 0))
    return 0.0


def weekly_target(now: float, reset_at: float | None = None) -> float:
    """균등 배분 목표 사용률(0~1) — 주 시작 직후에도 최소 PACE_FLOOR 는 허용."""
    reset_at = reset_at or week_start(now) + WEEK_SEC
    elapsed = min(max((now - (reset_at - WEEK_SEC)) / WEEK_SEC, 0.0), 1.0)
    if reset_at - now <= FINAL_DAY_SEC:
        return settings.WEEK_CEILING  # 주 마지막 24시간 — 균등선으로 남는 예산을 묵히지 않고 상한까지 허용
    return min(settings.WEEK_CEILING, settings.PACE_FLOOR + elapsed * settings.PACE_SLACK)


def weekly_resume_at(now: float, util: float, reset_at: float, rejected: bool = False) -> float:
    """주간 균등 게이트가 풀리는 시각 — 목표선이 현재 사용률에 닿는 때(리셋보다 훨씬 이르다). 상한 도달·거부면 리셋."""
    if rejected or util >= settings.WEEK_CEILING:
        return reset_at
    t = reset_at - WEEK_SEC + (util - settings.PACE_FLOOR) / settings.PACE_SLACK * WEEK_SEC
    return min(max(t, now + 60), reset_at - FINAL_DAY_SEC if reset_at - FINAL_DAY_SEC > now else reset_at)


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
    if wk and settings.tunable("WEEKLY_PACING_ENABLED"):
        target = weekly_target(now, wk["resetsAt"])
        if wk.get("status") == "rejected" or wk.get("utilization", 0) >= target:
            # 목표선이 현재 사용률에 닿는 시각(또는 마지막 24시간 시작)에 재개 — 주간 리셋까지 기다리지 않는다.
            resume = weekly_resume_at(now, wk.get("utilization", 1), wk["resetsAt"], wk.get("status") == "rejected")
            if sess:
                resume = min(resume, sess["resetsAt"])
            return Pacing(False, f"주간 사용률 {wk.get('utilization', 1):.0%} ≥ 균등 목표 {target:.0%} — 페이싱 대기", resume)
    if not sess:
        reset = last_session_reset(entries)
        recent = [e for e in ledger.since(SESSION_SEC / 3600, entries, now) if e["ts"] > reset and not str(e.get("unit_id", "")).startswith("audit-ask")]
        if recent and (len(recent) >= settings.tunable("FALLBACK_SESSION_MAX_RUNS") or ledger.total_cost(recent) >= settings.tunable("FALLBACK_SESSION_MAX_USD")):
            return Pacing(False, "5시간 관측 없음 — 대체 한도(실행 수·USD) 도달", recent[0]["ts"] + SESSION_SEC)
    return Pacing(True)
