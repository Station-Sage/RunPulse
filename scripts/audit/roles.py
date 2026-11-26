"""역할 패널 제어(S1) — 콘솔에서 역할별 일시정지·건너뛰기·재실행을 지정하면 루프가 단계 시작 때 반영한다.

파일: .claude/autopilot/roles.json  {"<role>": {"paused": bool, "skip": bool, "rerun": bool}}
- paused : 해당 역할 단계 진입 시 정지(ROLE_PAUSE — 단계 유지, 해제 후 재개). 해제 후 재개는 콘솔의 '재개'.
- skip   : 해당 단계를 건너뛴다(다음 단계로). 사용자가 해제할 때까지 유지(소비되지 않음).
- rerun  : 해당 역할 단계로 되돌린다(1회). 소비되면 해제.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import inventory, stopreason

ROLES_PATH = inventory.LEDGER_PATH.parent / "roles.json"
PHASE_ROLE = {"audit": "auditor", "design": "designer", "idesign": "designer", "develop": "developer",
              "test": "verifier", "plan": "planner"}
NEXT_PHASE = {"audit": "design", "design": "develop", "idesign": "develop", "plan": "idesign", "develop": "test", "test": "audit"}
FLAGS = ("paused", "skip", "rerun")
ROLES = ("steward", "planner", "designer", "developer", "verifier", "auditor", "deployer")


def load(path: Path | None = None) -> dict:
    try:
        d = json.loads((path or ROLES_PATH).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def set_flag(role: str, flag: str, value: bool, path: Path | None = None) -> dict:
    if role not in ROLES or flag not in FLAGS:
        return {"ok": False, "error": "없는 역할/동작"}
    p = path or ROLES_PATH
    d = load(p)
    d.setdefault(role, {})[flag] = bool(value)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "roles": d}


def gate(st: dict, path: Path | None = None) -> str | None:
    """단계 시작 시 호출 — 역할 지정이 있으면 상태를 바꾸고 한 줄 결과를 반환(없으면 None)."""
    d = load(path)
    role = PHASE_ROLE.get(st.get("phase"))
    f = d.get(role or "", {})
    if not f:
        return None
    if f.get("paused"):
        stopreason.stop(st, stopreason.ROLE_PAUSE)
        return f"{role} 일시정지 중 — 콘솔 역할 패널에서 해제 후 재개"
    if f.get("skip"):
        st["phase"] = NEXT_PHASE[st["phase"]]
        return f"{role} 단계 건너뜀 → {st['phase']}"
    if f.get("rerun"):
        set_flag(role, "rerun", False, path)
        st["phase"] = next(p for p, r in PHASE_ROLE.items() if r == role)
        return f"{role} 단계 재실행 지정"
    return None


def blocked(role: str, path: Path | None = None) -> bool:
    """단계 게이트가 없는 보조 역할(steward 등)이 일시정지·건너뛰기 지정을 받았는지 — 지정이 있으면 해제할 때까지 실행하지 않는다."""
    f = load(path).get(role, {})
    if f.get("paused"):
        return True
    return bool(f.get("skip"))
