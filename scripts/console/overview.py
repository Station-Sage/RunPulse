"""관제 콘솔 읽기 API 데이터 — 루프 상태·큐·페이싱·예산·결정함을 JSON 직렬화 가능한 dict 로 모은다."""
from __future__ import annotations

import time
from pathlib import Path

from scripts.audit import roles, decisions, loop, release_plan
from scripts.console import flow
from scripts.autopilot import ledger, pacing, queue, settings

STAGES = ("queued", "in_progress", "review", "done", "needs_decision", "failed")


def queue_summary(path: Path | None = None) -> dict:
    items = [it for it in queue.parse(path or settings.QUEUE_PATH) if it.mode == "auto"]
    by = {s: 0 for s in STAGES}
    for it in items:
        by[it.stage] = by.get(it.stage, 0) + 1
    nr = queue.next_runnable(items)
    attention = [{"id": it.item_id, "stage": it.stage, "text": it.text if it.stage == "review" else it.text[:120]}
                 for it in items if it.stage in ("needs_decision", "review")]
    blocked = [{"id": it.item_id, "kind": it.fail_kind, "reason": it.fail_reason, "text": it.text, "attempts": it.attempts}
               for it in items if it.stage == "failed"]
    return {"total": len(items), "by_stage": by, "next": nr.item_id if nr else None, "attention": attention,
            "blocked": blocked, "blocked_count": len(blocked), "waiting_count": by.get("needs_decision", 0)}


CLOSED_SHOWN = 10


def budget_summary(now: float, entries: list[dict] | None = None) -> dict:
    es = ledger.read_all() if entries is None else entries
    pc = pacing.check(now, es)
    obs = {k: pacing.latest_observation(es, k, now) for k in ("five_hour", "seven_day")}
    return {"week_usd": round(ledger.total_cost(ledger.since(168, es, now)), 2), "weekly_max": settings.WEEKLY_MAX_USD,
            "five_hour": obs["five_hour"], "seven_day": obs["seven_day"], "weekly_target": round(pacing.weekly_target(now), 3),
            "pacing_ok": pc.allowed, "pacing_reason": pc.reason, "pacing_resume_at": pc.resume_at}


def release_summary(queue_path: Path | None = None, plan_path: Path | None = None) -> dict:
    """버전 헤더·범위 카드 — 저장하지 않고 자동 이니셔티브 편입을 메모리에서만 반영한다."""
    plan = release_plan.load(plan_path)
    release_plan.sync_groups(plan, queue_path)
    return release_plan.rollup(plan, queue_path)


def overview(now: float | None = None, state_path: Path | None = None, queue_path: Path | None = None,
             entries: list[dict] | None = None, dpath: Path | None = None, plan_path: Path | None = None) -> dict:
    now = now or time.time()
    st = loop.load_state(state_path)
    recs = decisions.load(dpath)
    open_n = sum(1 for d in recs if d["status"] == "open")  # redo 는 재제안 대기라 사용자 조치 대상이 아니다
    redo_n = sum(1 for d in recs if d["status"] == "redo")
    return {"now": now, "state": {k: st.get(k) for k in ("phase", "round", "unit", "units_done", "fails", "stop_reason")},
            "flags": {"pause": settings.PAUSE_PATH.exists(), "stop": settings.STOP_PATH.exists()},
            "queue": queue_summary(queue_path), "budget": budget_summary(now, entries), "decisions_open": open_n, "decisions_redo": redo_n,
            "release": release_summary(queue_path, plan_path), "roles": roles.load(),
            "progress": flow.build(st, now, queue_path, unit_cap=loop.UNIT_CAP)}


def decision_list(dpath: Path | None = None) -> list[dict]:
    """결정함 — 열린 것(open/redo) 먼저, 최신순. 닫힌(applied) 카드는 CLOSED_SHOWN 건까지만."""
    rank = {"open": 0, "redo": 0, "chosen": 1, "applied": 2}
    newest_first = sorted(decisions.load(dpath), key=lambda d: str(d.get("created", "")), reverse=True)
    ordered = sorted(newest_first, key=lambda d: rank.get(d["status"], 3))
    shown_closed = 0
    out = []
    for d in ordered:
        if d["status"] == "applied":
            shown_closed += 1
            if shown_closed > CLOSED_SHOWN:
                continue
        out.append(d)
    return out
