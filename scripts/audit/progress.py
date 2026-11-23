"""진행 상황 기록 — 루프·사이클·에이전트 단계 경계마다 한 줄씩 남긴다(.claude/autopilot/progress.log + stderr 즉시 flush)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from scripts.audit import inventory

LOG_PATH = inventory.LEDGER_PATH.parent / "progress.log"


def mark(msg: str, path: Path | None = None) -> str:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    p = path or LOG_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line, file=sys.stderr, flush=True)
    return line
