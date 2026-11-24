"""구조화 결정함(A2) — 사용자 결정 대기 건을 pending_decisions.json 에 기록한다. 관제 콘솔 결정함이 그대로 읽는다.

레코드: {id, kind, status(open|chosen|redo), summary, why, options[{key,name,pros,cons}], recommendation, revert, created, choice}.
마크다운 보고서(pending_decisions.md)는 사람이 파일로 읽을 때를 위해 유지한다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DECISIONS_PATH = Path(".claude/autopilot/pending_decisions.json")
REVERT = "git revert <커밋>; 관련 BACKLOG 항목 stage 를 needs_decision 으로 되돌림"


def build(iid: str, finding: dict, d: dict) -> dict:
    dz = d.get("design", {}) or {}
    opts = [{"key": chr(65 + i), "name": str(o.get("name", "")), "pros": str(o.get("pros", "")), "cons": str(o.get("cons", ""))}
            for i, o in enumerate(dz.get("options", []))]
    return {"id": iid, "kind": finding["kind"], "status": "open", "summary": dz.get("summary", ""), "why": d.get("why", ""),
            "options": opts, "recommendation": dz.get("recommendation", ""), "revert": REVERT,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "choice": None}


def load(path: Path | None = None) -> list[dict]:
    try:
        return json.loads((path or DECISIONS_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def append(recs: list[dict], path: Path | None = None) -> None:
    p = path or DECISIONS_PATH
    have = {r["id"] for r in load(p)}
    data = load(p) + [r for r in recs if r["id"] not in have]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def choose(iid: str, choice: str, path: Path | None = None) -> dict | None:
    """choice = 옵션 key(A,B…) → status chosen, 'redo' → status redo(다른 제안 요청). 대상 레코드를 돌려준다."""
    p = path or DECISIONS_PATH
    data = load(p)
    rec = next((r for r in data if r["id"] == iid), None)
    if rec is None:
        return None
    rec["status"] = "redo" if choice == "redo" else "chosen"
    rec["choice"] = choice
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec
