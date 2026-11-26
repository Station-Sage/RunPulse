"""버전 오케스트레이터 — 라운드 종료 시 안정화 게이트를 판정하고 다음 행동(감사 루프 계속 / 버전 계획)을 결정한다.

라우팅 우선순위(처음 일치): 저장된 cursor 재개 → 개발·테스트 대기 항목 → 설계 대상 → 큐가 비면 일반 감사 → 게이트 통과 후에만 버전 계획.
앞 4단계는 loop.step 의 단계 순서가 그대로 구현한다. 여기서는 마지막 관문(안정화 게이트)만 다룬다.
게이트 = 열린 항목 없음 + 새 확정 결함 0건인 라운드 GATE_ROUNDS 연속 + 실패 항목 없음(테스트 통과). 결정함에서 사용자 응답을 기다리는 항목(needs_decision·결정 레코드 있는 failed)은 게이트를 막지 않는다. 버전당 MAX_ROUNDS 를 넘으면 상한으로 통과시킨다.
상태: st["gate"] = {clean_rounds, version_rounds}, st["round_new"] = 이번 라운드에 새로 확정된 후보 수.
"""
from __future__ import annotations

from scripts.audit import decisions, stopreason

GATE_ROUNDS = 2
MAX_ROUNDS = 8
OPEN_STAGES = ("queued", "in_progress", "review")  # needs_decision 은 사용자 결정 대기 — 개발·게이트를 막지 않는다


def _gate(st: dict) -> dict:
    return st.setdefault("gate", {"clean_rounds": 0, "version_rounds": 0})


def record_round(st: dict, new_confirmed: int) -> dict:
    """라운드 종료 기록 — 새 확정 결함이 없으면 clean 연속 카운트 증가, 있으면 0."""
    g = _gate(st)
    g["version_rounds"] += 1
    g["clean_rounds"] = g["clean_rounds"] + 1 if new_confirmed == 0 else 0
    return g


def critical_open(items: list) -> list[str]:
    """아직 처리되지 않은 치명 항목 ID(사용자 결정 대기 제외) — 있으면 버전 작업(plan·idesign)보다 먼저 develop 으로."""
    return [i.item_id for i in items if getattr(i, "critical", False) and i.stage in ("queued", "in_progress", "review", "failed")]


def gate_passed(st: dict, items: list, dpath=None) -> tuple[bool, str]:
    """안정화 게이트 판정 — (통과 여부, 사유)."""
    g = _gate(st)
    if g["version_rounds"] >= MAX_ROUNDS:
        return True, f"라운드 상한 {MAX_ROUNDS} 도달"
    crit = critical_open(items)
    if crit:
        return False, f"치명 결함 {len(crit)}건 미처리"
    open_n = sum(1 for i in items if i.stage in OPEN_STAGES)
    waiting = {r.get("id") for r in decisions.load(dpath) if r.get("status") in ("open", "chosen", "redo")}
    failed = sum(1 for i in items if i.stage == "failed" and getattr(i, "item_id", None) not in waiting)
    if open_n:
        return False, f"열린 항목 {open_n}건"
    if failed:
        return False, f"실패 항목 {failed}건"
    if g["clean_rounds"] < GATE_ROUNDS:
        return False, f"무결함 라운드 {g['clean_rounds']}/{GATE_ROUNDS}"
    return True, f"무결함 {GATE_ROUNDS}라운드 연속"


def after_round(st: dict, items: list) -> str | None:
    """_end_round 훅 — 라운드 기록 후 게이트 통과면 phase 를 plan 으로. 통과 사유(아니면 None)."""
    record_round(st, st.pop("round_new", 0))
    ok, why = gate_passed(st, items)
    if ok:
        st["phase"] = "plan"
        return why
    return None


def plan_step(st: dict, planner=None, dpath=None) -> str:
    """plan 단계 — 버전 기획자(planner)를 호출한다. 없으면 사용자 결정 대기, 비전 개정 결정이 미해결이면 옛 비전으로 제안하지 않도록 대기."""
    if planner is None:
        stopreason.stop(st, stopreason.AWAIT_DECISION)
        return "버전 계획 단계 — 기획자 미연결, 사용자 결정 대기"
    if any(r.get("kind") == "vision" and r["status"] in ("open", "chosen", "redo") for r in decisions.load(dpath)):
        stopreason.stop(st, stopreason.AWAIT_DECISION)
        return "비전 개정 결정 대기 — 새 비전 확정 후 버전 계획"
    return planner(st)
