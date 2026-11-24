"""review 단계 항목 중 커밋이 이미 BASE_BRANCH 에 병합된 것을 done 으로 올린다 (사람이 review→done 을 손으로 옮기지 않도록).

promote_merged(path, branch=BASE_BRANCH, cwd=PROJECT_ROOT) → 승격한 항목 ID 목록. 판정: BASE_BRANCH 에서 도달 가능한 커밋 메시지에 항목 ID 가 있음.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.autopilot import queue, settings


def _merged(item_id: str, branch: str, cwd: Path) -> bool:
    r = subprocess.run(["git", "log", branch, "-E", f"--grep={re.escape(item_id)}([^0-9A-Za-z-]|$)", "-1", "--format=%H"],
                       cwd=cwd, capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def promote_merged(path: Path | None = None, branch: str | None = None, cwd: Path | None = None) -> list[str]:
    path, branch, cwd = path or settings.QUEUE_PATH, branch or settings.BASE_BRANCH, cwd or settings.PROJECT_ROOT
    done = []
    for it in queue.parse(path):
        if it.stage == "review" and _merged(it.item_id, branch, cwd):
            queue.update_item(path, it.item_id, stage="done")
            done.append(it.item_id)
    return done


def prune_pending(path: Path, pending: Path, archive: Path | None = None) -> list[str]:
    """pending 보고서에서 더는 needs_decision 이 아닌 항목의 `## ID` 섹션을 archive(기본 <pending>.resolved.md)로 옮긴다."""
    if not pending.exists():
        return []
    stage = {it.item_id: it.stage for it in queue.parse(path)}
    parts = re.split(r"(?m)^(?=## )", pending.read_text(encoding="utf-8"))
    keep, moved, ids = [], [], []
    for p in parts:
        m = re.match(r"## (\S+)", p)
        if m and stage.get(m.group(1)) != "needs_decision":
            moved.append(p)
            ids.append(m.group(1))
        else:
            keep.append(p)
    if moved:
        archive = archive or pending.with_suffix(".resolved.md")
        with archive.open("a", encoding="utf-8") as fh:
            fh.write("".join(moved))
        pending.write_text("".join(keep), encoding="utf-8")
    return ids
