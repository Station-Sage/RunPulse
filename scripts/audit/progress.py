"""진행 상황 기록 — 단계 경계마다 한 줄(progress.log + stderr)과 구조화 이벤트(events.jsonl, 콘솔 진행 시각화의 소스)를 남긴다."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from scripts.audit import inventory

LOG_PATH = inventory.LEDGER_PATH.parent / "progress.log"
EVENTS_PATH = inventory.LEDGER_PATH.parent / "events.jsonl"
EVENTS_MAX_BYTES = 256_000  # 초과 시 뒤쪽 절반만 유지(최근 라운드 위주)


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


def event(kind: str, path: Path | None = None, **fields) -> None:
    """구조화 이벤트 1건(JSONL, 날짜 포함 ts). kind: phase|sub|design|unit_start|unit_end|deploy_start|deploy_end.
    기록 실패는 루프를 막지 않는다."""
    p = path or EVENTS_PATH
    rec = {"ts": round(time.time(), 1), "kind": kind, **fields}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > EVENTS_MAX_BYTES:
            lines = p.read_text(encoding="utf-8").splitlines()
            p.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8")
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_events(path: Path | None = None) -> list[dict]:
    p = path or EVENTS_PATH
    out = []
    try:
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    except OSError:
        pass
    return out
