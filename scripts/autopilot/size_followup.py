"""300줄 초과 파일을 검증 실패로 막지 않고, 단위 성공 후 BACKLOG 후속 항목(SPLIT-*)으로 남긴다.

SPLIT 항목은 needs_decision 으로 등록되고 split_card 결정 카드(분리 진행/보류 + 추천안)가 함께 올라간다 — 자동 분리하지 않는다."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.audit import decisions

from . import queue, split_card

LIMIT = 300
_EXEMPT = {"frontend/src/lib/types/index.ts"}
_SRC = re.compile(r"\.(svelte|ts|py)$")


def oversize_in_scope(item: queue.QueueItem, cwd: Path) -> list[tuple[str, int]]:
    """scope 안에서 이번에 손댄 소스 중 LIMIT 초과 파일 [(경로, 줄 수)]."""
    r = subprocess.run(["git", "ls-files", "--", *[s.rstrip("/") for s in item.scope]],
                       cwd=cwd, capture_output=True, text=True)
    out = []
    for f in r.stdout.splitlines():
        if f in _EXEMPT or not _SRC.search(f) or f.startswith(("tests/", "frontend/tests/")):
            continue
        try:
            n = (cwd / f).read_text(encoding="utf-8").count("\n")
        except OSError:
            continue
        if n > LIMIT:
            out.append((f, n))
    return out


def append_followups(item: queue.QueueItem, cwd: Path, queue_path: Path, decisions_path: Path | None = None) -> list[str]:
    """초과 파일마다 SPLIT-<slug> 항목을 BACKLOG 끝에 추가(이미 있으면 건너뜀). 반환: 추가한 id."""
    existing = {it.item_id for it in queue.parse(queue_path)}
    added, block, cards = [], "", []
    for f, n in oversize_in_scope(item, cwd):
        sid = "SPLIT-" + re.sub(r"[^A-Za-z0-9]+", "-", f).strip("-")[-40:]
        if sid in existing:
            continue
        meta = ('{"stage": "needs_decision", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", '
                f'"scope": ["{f}"], "verify": ["cd frontend && npm run check"]}}')
        block += (f"- **[{sid}]** (후속: {item.item_id} 에서 발견) [refactor] {f} 가 {n}줄로 {LIMIT}줄 상한 초과 → "
                  "동작 변경 없이 하위 컴포넌트·모듈로 분리한다.\n"
                  f"  <!-- autopilot: {meta} -->\n")
        added.append(sid)
        cards.append(split_card.build_split_card(sid, f, n, item.item_id))
    if block:
        with queue_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + block)
        decisions.append(cards, decisions_path)
    return added
