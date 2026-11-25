"""버전 계획 상태(원본) — 버전 → 이니셔티브 → 항목 구조. 사람이 읽는 사본은 v0.3/data/releases/<버전>/PLAN.md.

파일: .claude/autopilot/release_plan.json
  {"current": "v1", "versions": {"v1": {"title", "status": "active|planned|closed", "goal": "제품 목표 한 줄(선택)",
     "phases": [{"id": "I", "title", "initiatives": [INI-id...]}](선택, planner 가 생성),
     "initiatives": {"INI-MAINT": {"title", "status": "proposed|approved|designed|done", "items": [BACKLOG ID...]}}}}}
INI-MAINT 는 기존 감사 결함(AUD-*)을 묶는 상시 이니셔티브 — 어느 이니셔티브에도 속하지 않은 AUD 항목은 sync_maint 가 자동 편입한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import inventory
from scripts.autopilot import queue, settings

PLAN_PATH = inventory.LEDGER_PATH.parent / "release_plan.json"
MAINT = "INI-MAINT"
_INIT = {"current": "v1", "versions": {"v1": {"title": "현행 기준선", "status": "active", "initiatives": {
    MAINT: {"title": "유지보수 결함 처리", "status": "approved", "items": []}}}}}


def load(path: Path | None = None) -> dict:
    try:
        d = json.loads((path or PLAN_PATH).read_text(encoding="utf-8"))
        if d.get("versions"):
            return d
    except (OSError, ValueError):
        pass
    return json.loads(json.dumps(_INIT))


def save(plan: dict, path: Path | None = None) -> None:
    p = path or PLAN_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def current(plan: dict) -> str:
    return plan.get("current") or next(iter(plan["versions"]))


def initiatives(plan: dict, version: str | None = None) -> dict:
    return plan["versions"][version or current(plan)].setdefault("initiatives", {})


def linked_ids(plan: dict) -> set[str]:
    return {i for v in plan["versions"].values() for ini in v.get("initiatives", {}).values() for i in ini.get("items", [])}


def link(plan: dict, ini_id: str, item_id: str, version: str | None = None) -> bool:
    """항목을 이니셔티브에 연결. 이미 어느 이니셔티브에든 있으면 False."""
    if item_id in linked_ids(plan):
        return False
    initiatives(plan, version)[ini_id]["items"].append(item_id)
    return True


def sync_maint(plan: dict, queue_path: Path | None = None) -> list[str]:
    """어느 이니셔티브에도 없는 AUD 항목을 현재 버전의 INI-MAINT 에 편입. 새로 편입한 ID 목록."""
    ini = initiatives(plan)
    ini.setdefault(MAINT, {"title": "유지보수 결함 처리", "status": "approved", "items": []})
    return [it.item_id for it in queue.parse(queue_path or settings.QUEUE_PATH)
            if it.item_id.startswith("AUD-") and link(plan, MAINT, it.item_id)]


def rollup(plan: dict, queue_path: Path | None = None) -> dict:
    """현재 버전의 이니셔티브별 항목 진행 집계 — {version, title, status, initiatives:[{id,title,status,total,done,by_stage}]}."""
    ver = current(plan)
    v = plan["versions"][ver]
    stage = {it.item_id: it.stage for it in queue.parse(queue_path or settings.QUEUE_PATH)}
    out = []
    for iid, ini in v.get("initiatives", {}).items():
        by: dict[str, int] = {}
        for i in ini.get("items", []):
            s = stage.get(i, "missing")
            by[s] = by.get(s, 0) + 1
        out.append({"id": iid, "title": ini.get("title", iid), "status": ini.get("status", "proposed"),
                    "total": len(ini.get("items", [])), "done": by.get("done", 0), "by_stage": by})
    return {"version": ver, "title": v.get("title", ver), "status": v.get("status", "active"), "goal": v.get("goal", ""),
            "phases": _phase_rollup(v.get("phases"), out), "initiatives": out}


def _phase_rollup(phases, inis: list[dict]) -> list[dict]:
    """단계별 {id,title,total,done,active,initiatives} — active=아직 안 끝났고 첫 번째인 단계(진행 중)."""
    by = {i["id"]: i for i in inis}
    out = []
    for p in phases or []:
        mine = [by[i] for i in p.get("initiatives", []) if i in by]
        out.append({"id": p.get("id", ""), "title": p.get("title", ""), "initiatives": mine,
                    "total": sum(i["total"] for i in mine), "done": sum(i["done"] for i in mine), "active": False})
    for p in out:
        if p["done"] < p["total"] or not p["total"]:
            p["active"] = True
            break
    return out
