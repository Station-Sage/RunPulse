"""알려진 이슈 원장 — 이미 보고된 발견을 기억해 감사가 이전 라운드를 반복하지 않게 하고, 스윕 결과로 해소를 재검증한다.

키는 kind + 대표 셀(정렬 상위 3개). 상태: open(보고됨·미해소) / resolved(스윕에서 해당 kind 가 사라짐).
resolved 였다가 다시 보이면 reopened 로 표시해 재발을 놓치지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.audit import inventory

KNOWN_PATH = inventory.LEDGER_PATH.parent / "known_issues.json"


def current_round() -> int:
    try:
        return int(json.loads((KNOWN_PATH.parent / "cycle_state.json").read_text(encoding="utf-8")).get("round", 1))
    except (OSError, ValueError):
        return 1


def key(f: dict) -> str:
    cells = ",".join(sorted(f.get("cells") or [])[:3])
    return f"{f.get('kind', '')}:{hashlib.sha1(cells.encode()).hexdigest()[:8]}"


def load(path: Path | None = None) -> dict[str, dict]:
    try:
        return json.loads((path or KNOWN_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict[str, dict], path: Path | None = None) -> None:
    p = path or KNOWN_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def filter_new(findings: list[dict], known: dict[str, dict]) -> list[dict]:
    """open 상태로 이미 보고된 발견을 제외한다(resolved 는 재발이므로 통과)."""
    return [f for f in findings if known.get(key(f), {}).get("status") != "open"]


def record(findings: list[dict], round_no: int, path: Path | None = None) -> dict[str, dict]:
    data = load(path)
    for f in findings:
        k = key(f)
        prev = data.get(k)
        status = "open"
        data[k] = {"kind": f.get("kind"), "perspective": f.get("perspective"), "impact": f.get("impact", ""),
                   "first_round": prev["first_round"] if prev else round_no, "round": round_no,
                   "status": status, "reopened": bool(prev and prev["status"] == "resolved")}
    save(data, path)
    return data


def reverify(groups: dict[str, list[dict]], path: Path | None = None) -> dict[str, list[str]]:
    """최신 스윕 그룹 기준으로 open 이슈의 해소 여부를 재검증한다 → {"resolved": [...], "still_open": [...]}."""
    data = load(path)
    out: dict[str, list[str]] = {"resolved": [], "still_open": []}
    for k, rec in data.items():
        if rec["status"] != "open":
            continue
        if rec["kind"] in groups:
            out["still_open"].append(k)
        else:
            rec["status"] = "resolved"
            out["resolved"].append(k)
    save(data, path)
    return out


def render(known: dict[str, dict], limit: int = 20) -> str:
    """프롬프트 주입용 — 이미 보고된 open 이슈 목록(최근 라운드 우선)."""
    rows = sorted((r for r in known.values() if r["status"] == "open"), key=lambda r: -r["round"])[:limit]
    return "\n".join(f"- [{r['kind']}] {r['impact']}"[:140] for r in rows) or "(없음)"
