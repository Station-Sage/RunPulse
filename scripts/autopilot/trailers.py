"""커밋 메시지에서 공동저자·생성기 트레일러 제거 — 에이전트가 붙인 Co-Authored-By 등을 러너가 정리."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_TRAILER_RE = re.compile(
    r"^\s*(co-authored-by:.*|.*generated with \[?claude.*|.*noreply@anthropic\.com.*)$", re.IGNORECASE
)


def strip_trailers(message: str) -> str:
    """트레일러 줄을 지우고 끝 공백을 정리한다."""
    kept = [ln for ln in message.splitlines() if not _TRAILER_RE.match(ln)]
    return "\n".join(kept).rstrip() + "\n"


def scrub_range(cwd: Path, base: str) -> int:
    """base..HEAD 커밋 중 트레일러가 든 메시지를 다시 쓴다. 반환: 고친 커밋 수 (0 = 없음/실패)."""
    log = subprocess.run(["git", "log", "--format=%H%x00%B%x01", f"{base}..HEAD"],
                         cwd=cwd, capture_output=True, text=True)
    if log.returncode != 0:
        return 0
    dirty = [e for e in log.stdout.split("\x01") if e.strip() and strip_trailers(e.split("\x00", 1)[1]) != e.split("\x00", 1)[1].strip() + "\n"]
    if not dirty:
        return 0
    filt = ("sed -E '/^[[:space:]]*co-authored-by:/Id; /generated with \\[?claude/Id; "
            "/noreply@anthropic\\.com/Id'")
    r = subprocess.run(["git", "filter-branch", "-f", "--msg-filter", filt, f"{base}..HEAD"],
                       cwd=cwd, capture_output=True, text=True,
                       env={**__import__("os").environ, "FILTER_BRANCH_SQUELCH_WARNING": "1"})
    return len(dirty) if r.returncode == 0 else 0
