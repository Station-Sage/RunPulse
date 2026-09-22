"""BACKLOG 큐 파싱 — 사람이 읽는 마크다운에 기계가 읽는 메타 주석을 병기한 항목을 다룬다.

형식(항목 줄 바로 다음 줄):
    - **[ID]** 설명
      <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->

    (kind="code" 예시 — scope/verify로 파일 범위·완료 판정 커맨드를 명시. 메타 줄은
    반드시 한 줄이어야 한다 — _META_RE가 줄 단위로 매칭하므로 줄바꿈하면 파싱 실패)
    - **[ID]** 설명
      <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[],"kind":"code","scope":["src/metrics/pmc.py","tests/test_pmc.py"],"verify":["python3 -m pytest tests/test_pmc.py -q"]} -->

- mode: "auto"인 항목만 자동 실행 대상 (메타 줄이 없으면 사람 전용 항목 — 파서가 건너뜀).
- stage: queued → in_progress → review → done. blocked는 사람 결정 대기(DECISIONS.md)
  또는 _post_verify() 실패(run_unit.py) — 둘 다 사람이 확인해야 다음으로 못 넘어간다.
- deps: 이 ID들이 전부 stage=done이어야 실행 가능.
- kind: "docs"(기본) | "code". code는 run_unit.py가 다른 프롬프트·도구 허용·검증
  커맨드를 쓴다(settings.CODE_ALLOWED_TOOLS).
- scope: code 전용. 이 unit이 건드려도 되는 경로 목록 — 프롬프트에 그대로 박아 범위를
  제한한다(강제 아님, 안내). 비어있으면 프롬프트가 "위험하니 채워서 등록" 경고를 낸다.
- verify: code 전용. 성공 판정에 쓸 셸 커맨드 목록 — claude -p가 성공을 보고해도
  run_unit.py가 워크트리에서 이 커맨드들을 독립적으로 다시 돌려 전부 0 종료해야
  stage=review로 넘어간다(하나라도 실패하면 blocked). 비어있으면
  "python3 -m pytest tests/ -q" 기본값을 쓴다.

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
    kind: str = "docs"                              # "docs" | "code"
    scope: list[str] = field(default_factory=list)   # code 전용: 건드려도 되는 경로
    verify: list[str] = field(default_factory=list)  # code 전용: 성공 판정 커맨드
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
                item.kind = meta.get("kind", "docs")
                item.scope = list(meta.get("scope", []))
                item.verify = list(meta.get("verify", []))
                item.meta_line_no = j
                break
            j += 1
        items.append(item)
        i += 1
    return items


def find_malformed_meta(path: Path) -> list[str]:
    """`<!-- autopilot:` 로 시작하지만 그 줄에서 _META_RE로 안 닫히는 줄을 찾는다.

    흔한 실수: JSON을 가독성 좋으라고 여러 줄로 줄바꿈 — 파서는 그 항목을 그냥
    mode="manual"로 조용히 취급해버려서(파싱 에러도, 예외도 없음) 무인 실행에서
    영원히 빠지는데 아무 경고도 안 뜬다. status.py가 이 함수로 사전에 잡아낸다.
    """
    if not path.exists():
        return []
    warnings = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if "<!-- autopilot:" in line and not _META_RE.match(line):
            warnings.append(f"{i + 1}행: 메타 주석이 한 줄로 안 닫힘(줄바꿈 의심) — {line.strip()[:80]}")
    return warnings


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
    target.kind = fields.get("kind", target.kind)
    target.scope = fields.get("scope", target.scope)
    target.verify = fields.get("verify", target.verify)

    lines = path.read_text(encoding="utf-8").splitlines()
    indent_m = _META_RE.match(lines[target.meta_line_no])
    indent = indent_m.group(1) if indent_m else "  "
    # kind/scope/verify는 값이 있을 때만 적는다 — docs(기본값) 항목의 메타 줄 모양을
    # 지금까지와 동일하게 유지해 기존 항목 diff를 안 만든다.
    meta = {"stage": target.stage, "mode": target.mode,
             "attempts": target.attempts, "deps": target.deps}
    if target.kind != "docs":
        meta["kind"] = target.kind
    if target.scope:
        meta["scope"] = target.scope
    if target.verify:
        meta["verify"] = target.verify
    lines[target.meta_line_no] = f"{indent}<!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
