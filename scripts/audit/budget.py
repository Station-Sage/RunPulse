"""Opus 사용 게이트 — Opus 주간 버킷은 사람 작업용이라 자동 실행은 큰 설계·릴리스 감사에만, 사용률 한도 안에서 쓴다.

허용 조건: 5시간 사용률 < SESSION_CEILING 이고 주간 사용률 < OPUS_WEEK_CAP (rate_limit 관측 기준). 관측이 없으면 허용.
막히면 호출자가 Sonnet 으로 폴백(agents.ask)하거나 대기한다(release).
"""
from __future__ import annotations

import time

from scripts.autopilot import ledger, pacing, settings

OPUS_WEEK_CAP = 0.5            # 주간 사용률이 이 이상이면 Opus 자동 사용 중단


def opus_allowed(now: float | None = None, entries: list[dict] | None = None) -> tuple[bool, str]:
    now = now or time.time()
    entries = ledger.read_all() if entries is None else entries
    sess = pacing.latest_observation(entries, "five_hour", now)
    if sess and sess.get("utilization", 0) >= settings.SESSION_CEILING:
        return False, "5시간 세션 사용률 높음"
    wk = pacing.latest_observation(entries, "seven_day", now)
    if wk and wk.get("utilization", 0) >= OPUS_WEEK_CAP:
        return False, f"주간 사용률 {wk['utilization']:.0%} ≥ Opus 상한 {OPUS_WEEK_CAP:.0%}"
    return True, ""
