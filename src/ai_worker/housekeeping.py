"""워커 정리 작업 — 작업 디렉터리에 쌓이는 CLI 세션 jsonl 을 보존기간 뒤 지운다."""
from __future__ import annotations

import re
import time
from pathlib import Path

TRANSCRIPT_RETENTION_DAYS = 14


def transcript_dir(work_dir: Path, home: Path | None = None) -> Path:
    """CLI 가 work_dir 기준으로 세션을 저장하는 `~/.claude/projects/<경로 치환>` 위치."""
    key = re.sub(r"[^A-Za-z0-9]", "-", str(Path(work_dir).resolve()))
    return (home or Path.home()) / ".claude" / "projects" / key


def purge_transcripts(work_dir: Path, *, days: int = TRANSCRIPT_RETENTION_DAYS, home: Path | None = None,
                      now: float | None = None) -> int:
    d = transcript_dir(work_dir, home)
    if not d.is_dir():
        return 0
    cutoff = (now or time.time()) - days * 86400
    n = 0
    for f in d.glob("*.jsonl"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                n += 1
        except OSError:
            pass
    return n
