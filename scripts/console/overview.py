"""관제 콘솔 읽기 API 데이터 — 루프 상태·큐·페이싱·예산·결정함을 JSON 직렬화 가능한 dict 로 모은다."""
from __future__ import annotations

import time
from pathlib import Path

from scripts.audit import decisions, loop
from scripts.console import flow
from scripts.autopilot import ledger, pacing, queue, settings

STAGES = ("queued", "in_progress", "review", "done", "needs_decision", "failed")


def queue_summary(path: Path | None = None) -> dict:
    items = [it for it in queue.parse(path or settings.QUEUE_PATH) if it.mode == "auto"]
    by = {s: 0 for s in STAGES}
    for it in items:
        by[it.stage] = by.get(it.stage, 0) + 1
    nr = queue.next_runnable(items)
    attention = [{"id": it.item_id, "stage": it.stage, "text": it.text[:120]}
                 for it in items if it.stage in ("needs_decision", "failed", "review")]
    return {"total": len(items), "by_stage": by, "next": nr.item_id if nr else None, "attention": attention}


def budget_summary(now: float, entries: list[dict] | None = None) -> dict:
    es = ledger.read_all() if entries is None else entries
    pc = pacing.check(now, es)
    obs = {k: pacing.latest_observation(es, k, now) for k in ("five_hour", "seven_day")}
    return {"today_usd": round(ledger.total_cost(ledger.since(24, es, now)), 2), "daily_max": settings.DAILY_MAX_USD,
            "week_usd": round(ledger.total_cost(ledger.since(168, es, now)), 2), "weekly_max": settings.WEEKLY_MAX_USD,
            "five_hour": obs["five_hour"], "seven_day": obs["seven_day"], "weekly_target": round(pacing.weekly_target(now), 3),
            "pacing_ok": pc.allowed, "pacing_reason": pc.reason, "pacing_resume_at": pc.resume_at}


def overview(now: float | None = None, state_path: Path | None = None, queue_path: Path | None = None,
             entries: list[dict] | None = None, dpath: Path | None = None) -> dict:
    now = now or time.time()
    st = loop.load_state(state_path)
    open_dec = [d for d in decisions.load(dpath) if d["status"] in ("open", "redo")]
    return {"now": now, "state": {k: st.get(k) for k in ("phase", "round", "unit", "units_done", "fails", "stop_reason")},
            "flags": {"pause": settings.PAUSE_PATH.exists(), "stop": settings.STOP_PATH.exists()},
            "queue": queue_summary(queue_path), "budget": budget_summary(now, entries), "decisions_open": len(open_dec),
            "progress": flow.build(st, now, queue_path, unit_cap=loop.UNIT_CAP)}


def decision_list(dpath: Path | None = None) -> list[dict]:
    """결정함 — 열린 것(open/redo) 먼저, 최신순."""
    rank = {"open": 0, "redo": 0, "chosen": 1, "applied": 2}
    newest_first = sorted(decisions.load(dpath), key=lambda d: str(d.get("created", "")), reverse=True)
    return sorted(newest_first, key=lambda d: rank.get(d["status"], 3))
