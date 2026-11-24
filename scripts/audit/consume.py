"""결정함 소비(C1) — 사용자가 고른 결정(chosen)은 BACKLOG 항목을 queued 로 승격하고, 다른 제안 요청(redo)은 설계를 다시 받는다.

관제 콘솔·CLI 가 pending_decisions.json 에 쓴 status 를 루프가 develop 단계 시작 때 읽어 반영한다. 반영된 레코드는 applied(승격) 또는 open(재제안)이 된다.
"""
from __future__ import annotations

from pathlib import Path

from scripts.audit import decisions
from scripts.autopilot import queue

REDO_LIMIT = 3


def _promote(rec: dict, path: Path) -> str:
    opt = next((o for o in rec["options"] if o["key"] == rec["choice"]), None)
    fields = {"stage": "queued"}
    if rec.get("scope") and rec.get("verify"):
        fields.update(scope=rec["scope"], verify=rec["verify"])
    queue.update_item(path, rec["id"], **fields)
    rec["status"] = "applied"
    return f"{rec['id']} 선택 {rec['choice']}({opt['name'] if opt else '-'}) → queued"


def _redo(rec: dict, path: Path, decide) -> str:
    if rec.get("rounds", 1) >= REDO_LIMIT:
        rec["status"] = "open"
        rec["why"] = f"재제안 {REDO_LIMIT}회 소진 — 직접 지시 필요. " + rec.get("why", "")
        return f"{rec['id']} 재제안 상한({REDO_LIMIT}) — 사용자 직접 결정 대기"
    f = dict(rec.get("finding") or {"kind": rec["kind"]})
    f["fix"] = f"{f.get('fix', '')} (이전 제안 '{rec['summary'][:80]}' 은 거절됨 — 다른 접근으로 설계)"
    d = decide(f)
    dz = d.get("design", {}) or {}
    new = decisions.build(rec["id"], rec.get("finding") or f, {**d, "design": dz})
    new.update(rounds=rec.get("rounds", 1) + 1, created=rec["created"])
    new["finding"] = rec.get("finding") or new["finding"]
    rec.clear()
    rec.update(new)
    return f"{rec['id']} 다른 제안 {rec['rounds']}차 수신 — 결정 대기"


def apply(path: Path, decide, dpath: Path | None = None) -> list[str]:
    """chosen/redo 레코드를 반영하고 한 줄 결과 목록을 돌려준다. 항목이 needs_decision 이 아니면 레코드만 applied 로 닫는다."""
    data = decisions.load(dpath)
    stages = {i.item_id: i.stage for i in queue.parse(path)}
    out = []
    for rec in data:
        if rec["status"] == "chosen":
            if stages.get(rec["id"]) == "needs_decision":
                out.append(_promote(rec, path))
            else:
                rec["status"] = "applied"
        elif rec["status"] == "redo":
            out.append(_redo(rec, path, decide))
    if out or any(r["status"] == "applied" for r in data):
        decisions.save(data, dpath)
    return out
