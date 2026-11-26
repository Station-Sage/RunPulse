"""등록 전 중복 필터 — 이미 결정함(열림·처리됨)이나 큐에 있는 것과 같은 후보는 제안하지 않는다.

판정: 같은 kind, 또는 같은 소스 파일의 ±LINE_WINDOW 줄 안 셀, 또는 같은 런타임 셀(경로|상태|폭) 이 겹치면 중복.
"""
from __future__ import annotations

import re

LINE_WINDOW = 5
_SRC = re.compile(r"^(.+?):(\d+)")


def _parse(cell: str):
    m = _SRC.match(str(cell))
    return (m.group(1), int(m.group(2))) if m else (str(cell), None)


def _near(a: str, b: str) -> bool:
    (fa, la), (fb, lb) = _parse(a), _parse(b)
    if fa != fb:
        return False
    return la is None or lb is None or abs(la - lb) <= LINE_WINDOW


def duplicate_of(finding: dict, records: list[dict], items: list | None = None) -> str | None:
    """겹치는 기존 결정/큐 항목 ID(없으면 None). records=decisions.load(), items=queue.parse() (폐기된 done 은 제외)."""
    kind, cells = finding.get("kind", ""), [str(c) for c in finding.get("cells", [])]
    for r in records:
        if r.get("kind") == kind and r.get("status") != "applied":  # 처리 끝난 것은 위치로만(회귀·다른 위치 재발은 허용)
            return r["id"]
        if any(_near(c, o) for c in cells for o in r.get("finding", {}).get("cells", [])):
            return r["id"]
    for it in items or []:
        if it.stage == "failed" or getattr(it, "resolution", "") == "dropped":
            continue
        if f"{kind}:" in it.text:
            return it.item_id
    return None
