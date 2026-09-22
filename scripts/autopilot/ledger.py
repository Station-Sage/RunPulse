"""자율 실행 비용 원장 — claude -p 실행마다 비용/토큰을 append-only로 기록하고 예산을 판정한다.

Claude Code는 5시간 창의 rate_limit_event는 내보내지만(utilization은 정상 상태에서
비어있음) 주간(seven_day) 상태는 관측되지 않는다(2026-09-22 스파이크 확인) — 그래서
이 원장이 예산 판단의 유일한 근거다. 기록 위치는 untracked 런타임 상태
(.claude/autopilot/ledger.jsonl) — 실행 이력이므로 git 추적 대상이 아니다.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import settings


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str = ""
    today_usd: float = 0.0
    week_usd: float = 0.0


def append(entry: dict) -> None:
    """실행 결과 1건을 원장에 추가. ts 없으면 현재 시각(UTC epoch)을 채운다."""
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.time(), **entry}
    with open(settings.LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_all() -> list[dict]:
    if not settings.LEDGER_PATH.exists():
        return []
    out = []
    for line in settings.LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 손상된 줄은 건너뛴다 — 원장 전체를 잃지 않는다
    return out


def since(hours: float, entries: list[dict] | None = None) -> list[dict]:
    cutoff = time.time() - hours * 3600
    entries = read_all() if entries is None else entries
    return [e for e in entries if e.get("ts", 0) >= cutoff]


def total_cost(entries: list[dict]) -> float:
    return sum(float(e.get("cost_usd") or 0) for e in entries)


def last(n: int = 1) -> list[dict]:
    return read_all()[-n:]


def check_budget() -> BudgetDecision:
    """일간/주간 누적이 상한을 넘으면 실행을 막는다. 실행당 상한은 --max-budget-usd가 담당."""
    entries = read_all()
    today = total_cost(since(24, entries))
    week = total_cost(since(24 * 7, entries))
    if today >= settings.DAILY_MAX_USD:
        return BudgetDecision(False, f"일간 예산 초과 (${today:.2f} >= ${settings.DAILY_MAX_USD})", today, week)
    if week >= settings.WEEKLY_MAX_USD:
        return BudgetDecision(False, f"주간 예산 초과 (${week:.2f} >= ${settings.WEEKLY_MAX_USD})", today, week)
    return BudgetDecision(True, "", today, week)
