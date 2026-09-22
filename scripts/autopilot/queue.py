"""BACKLOG 큐 파싱 — 사람이 읽는 마크다운에 기계가 읽는 메타 주석을 병기한 항목을 다룬다.

형식(항목 줄 바로 다음 줄):
    - **[ID]** 설명
      <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->

- mode: "auto"인 항목만 자동 실행 대상 (메타 줄이 없으면 사람 전용 항목 — 파서가 건너뜀).
- stage: queued → in_progress → review → done. blocked는 사람 결정 대기(DECISIONS.md).
- deps: 이 ID들이 전부 stage=done이어야 실행 가능.

기존 BACKLOG.md 포맷(`- **[ID]** ...`)을 그대로 쓰므로 사람이 읽는 문서 하나가
SSOT다 — 별도 JSON 큐 파일을 두지 않는다(문서 중복·불일치 방지).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_ITEM_RE = re.compile(r"^- \*\*\[([A-Za-z0-9_-]+)\]\*\* (.*)$")
_META_RE = re.compile(r"^(\s*)<!-- autopilot: (\{.*\}) -->\s*$")


@dataclass
class QueueItem:
    item_id: str
    text: str
    stage: str = "queued"
    mode: str = "manual"
    attempts: int = 0
    deps: list[str] = field(default_factory=list)
    line_no: int = -1        # 항목 줄 번호 (0-indexed)
    meta_line_no: int = -1   # 메타 주석 줄 번호, 없으면 -1


def parse(path: Path) -> list[QueueItem]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[QueueItem] = []
    i = 0
    while i < len(lines):
        m = _ITEM_RE.match(lines[i])
        if not m:
            i += 1
            continue
        item = QueueItem(item_id=m.group(1), text=m.group(2), line_no=i)
        # 설명이 여러 줄로 줄바꿈될 수 있으므로, 다음 항목/빈 줄 전까지 메타 주석을 찾는다
        # (i+1만 보면 줄바꿈된 설명 뒤에 붙은 메타를 조용히 놓친다 — 항목이 그냥 영원히
        # "manual"로 남아 무인 실행에서 빠지는 나쁜 실패 모드라 관대하게 스캔한다).
        j = i + 1
        while j < len(lines) and lines[j].strip() and not _ITEM_RE.match(lines[j]):
            meta_m = _META_RE.match(lines[j])
            if meta_m:
                try:
                    meta = json.loads(meta_m.group(2))
                except json.JSONDecodeError:
                    meta = {}
                item.stage = meta.get("stage", "queued")
                item.mode = meta.get("mode", "manual")
                item.attempts = int(meta.get("attempts", 0))
                item.deps = list(meta.get("deps", []))
                item.meta_line_no = j
                break
            j += 1
        items.append(item)
        i += 1
    return items


def next_runnable(items: list[QueueItem]) -> QueueItem | None:
    done = {it.item_id for it in items if it.stage == "done"}
    for it in items:
        if it.mode != "auto" or it.stage != "queued":
            continue
        if all(dep in done for dep in it.deps):
            return it
    return None


def update_item(path: Path, item_id: str, **fields) -> None:
    """항목의 메타 주석 한 줄만 갱신. 문서의 나머지 내용은 손대지 않는다."""
    items = parse(path)
    target = next((it for it in items if it.item_id == item_id), None)
    if target is None or target.meta_line_no < 0:
        raise ValueError(f"메타 주석 없는 항목은 갱신 불가: {item_id}")

    target.stage = fields.get("stage", target.stage)
    target.mode = fields.get("mode", target.mode)
    target.attempts = fields.get("attempts", target.attempts)
    target.deps = fields.get("deps", target.deps)

    lines = path.read_text(encoding="utf-8").splitlines()
    indent_m = _META_RE.match(lines[target.meta_line_no])
    indent = indent_m.group(1) if indent_m else "  "
    meta = {"stage": target.stage, "mode": target.mode,
             "attempts": target.attempts, "deps": target.deps}
    lines[target.meta_line_no] = f"{indent}<!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
