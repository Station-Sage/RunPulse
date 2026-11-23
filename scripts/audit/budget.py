"""Opus 사용 게이트 — Opus 주간 버킷은 사람 작업용이라 자동 실행은 큰 설계·릴리스 감사에만, 한도 안에서 쓴다.

허용 조건: ① 5시간·주간 관측(rate_limit)이 있으면 5시간 < SESSION_CEILING 이고 주간 < OPUS_WEEK_CAP ② 관측 유무와 무관하게
이번 주(목 22:00 KST 리셋) 자동 Opus 호출 수 < OPUS_CALLS_PER_WEEK. 호출 수는 파일 카운터로 센다(agents.ask 가 기록).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.autopilot import ledger, pacing, settings

OPUS_WEEK_CAP = 0.5            # 주간 사용률이 이 이상이면 Opus 자동 사용 중단(Sonnet 으로 대체)
OPUS_CALLS_PER_WEEK = 15       # 관측이 없어도 지키는 주간 호출 상한
COUNTER_PATH = settings.STATE_DIR / "opus_calls.json"


def _week_key(now: float) -> str:
    return str(int(pacing.week_start(now)))


def calls_this_week(now: float | None = None, path: Path | None = None) -> int:
    now = now or time.time()
    try:
        d = json.loads((path or COUNTER_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return int(d.get(_week_key(now), 0))


def record_call(now: float | None = None, path: Path | None = None) -> None:
    now = now or time.time()
    p = path or COUNTER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({_week_key(now): calls_this_week(now, p) + 1}), encoding="utf-8")


def opus_allowed(now: float | None = None, entries: list[dict] | None = None, path: Path | None = None) -> tuple[bool, str]:
    now = now or time.time()
    entries = ledger.read_all() if entries is None else entries
    if calls_this_week(now, path) >= OPUS_CALLS_PER_WEEK:
        return False, f"이번 주 자동 Opus 호출 {OPUS_CALLS_PER_WEEK}회 소진"
    sess = pacing.latest_observation(entries, "five_hour", now)
    if sess and sess.get("utilization", 0) >= settings.SESSION_CEILING:
        return False, "5시간 세션 사용률 높음"
    wk = pacing.latest_observation(entries, "seven_day", now)
    if wk and wk.get("utilization", 0) >= OPUS_WEEK_CAP:
        return False, f"주간 사용률 {wk['utilization']:.0%} ≥ Opus 상한 {OPUS_WEEK_CAP:.0%}"
    return True, ""
