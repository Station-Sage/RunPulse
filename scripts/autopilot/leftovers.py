"""실행 후 미커밋 scope 변경 수습 — git이 막혀 모델이 커밋을 못 한 채 끝난 실행 대응."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import queue


def commit_leftovers(item: queue.QueueItem, cwd: Path) -> str:
    """실행이 끝났는데 scope 파일이 미커밋이면 러너가 대신 커밋한다. 반환: 사람용 노트("" = 할 일 없음).

    git이 승인 대기 등으로 막히면 모델이 작업을 끝내고도 커밋을 못 하는데, 러너는 그걸 모르고
    `success`로 보고했다(2026-09-24 ACTIVITY-ENV-CARD). 검증(_post_verify)을 통과한 뒤에만 호출하며,
    scope 밖 파일(예: 테스트가 만든 부산물)은 절대 커밋하지 않는다 — 남아 있으면 노트로만 알린다.
    """
    status = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=cwd, capture_output=True, text=True)
    dirty = [ln[3:].strip() for ln in status.stdout.splitlines() if ln.strip()]
    if not dirty:
        return ""
    scope = [s.rstrip("/") for s in (item.scope or [])]
    in_scope = [f for f in dirty if any(f == s or f.startswith(s + "/") for s in scope)]
    out_scope = [f for f in dirty if f not in in_scope]
    note = ""
    if in_scope:
        subprocess.run(["git", "add", "--", *in_scope], cwd=cwd, capture_output=True, text=True)
        r = subprocess.run(
            ["git", "commit", "-m",
             f"chore(autopilot): {item.item_id} — 실행이 남긴 미커밋 scope 변경을 러너가 커밋 (리뷰 필요)\n\n"
             + "\n".join(f"- {f}" for f in in_scope)],
            cwd=cwd, capture_output=True, text=True,
        )
        note = (f"미커밋 변경 {len(in_scope)}개를 러너가 커밋함" if r.returncode == 0
                else f"미커밋 변경 커밋 실패: {r.stderr[-200:]}")
    if out_scope:
        note += (" · " if note else "") + f"scope 밖 미커밋 파일 {len(out_scope)}개 남음: {', '.join(out_scope[:5])}"
    return note
