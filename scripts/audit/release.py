"""버전업 감사 — frontend/package.json 버전이 마지막 감사 버전과 다르면 Opus 전 관점으로 큰 반복 1회.

상태: .claude/autopilot/release_state.json {"audited": 버전}. 감사 자체는 cycle.run_cycle(release=True)(스윕 + Opus 관점 + Sonnet 교차 검토).
Opus 한도(budget)가 막히면 대기한다 — Sonnet 으로 대체해 '릴리스 감사'를 했다고 기록하지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import budget, cycle
from scripts.autopilot import settings

PKG_PATH = Path("frontend/package.json")
STATE_PATH = settings.STATE_DIR / "release_state.json"


def version(pkg: Path | None = None) -> str:
    try:
        return str(json.loads((pkg or PKG_PATH).read_text(encoding="utf-8")).get("version", ""))
    except (OSError, ValueError):
        return ""


def audited(path: Path | None = None) -> str:
    try:
        return str(json.loads((path or STATE_PATH).read_text(encoding="utf-8")).get("audited", ""))
    except (OSError, ValueError):
        return ""


def due(pkg: Path | None = None, path: Path | None = None) -> bool:
    v = version(pkg)
    return bool(v) and v != audited(path)


def run(pkg: Path | None = None, path: Path | None = None, audit=None, allowed=None) -> dict:
    """due 이고 Opus 허용이면 릴리스 감사 실행. 성공(outcome=done)이면 버전 기록. 항상 entry dict 반환."""
    if not due(pkg, path):
        return {"ran": False, "reason": "버전 변경 없음"}
    ok, why = (allowed or budget.opus_allowed)()
    if not ok:
        return {"ran": False, "reason": f"Opus 한도: {why}"}
    e = (audit or (lambda: cycle.run_cycle(force=True, release=True)))()
    if e.get("ran") and e.get("outcome") == "done":
        p = path or STATE_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"audited": version(pkg)}), encoding="utf-8")
    return e
