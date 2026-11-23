"""감사 자식 프로세스 레지스트리 — 등록된 PID 만 정리한다(미등록 프로세스는 절대 건드리지 않음).

.claude/autopilot/procs.json 에 {pid: 명령 조각} 을 기록하고, 사이클 시작 시 reap() 으로 고아를
terminate → 5초 wait → kill 한다. PID 재사용 방지를 위해 /proc/<pid>/cmdline 에 기록한 조각이 있을 때만 종료한다.
"""
from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

from scripts.audit import inventory

PROCS_PATH = inventory.LEDGER_PATH.parent / "procs.json"


def _load() -> dict[str, str]:
    try:
        return json.loads(PROCS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(d: dict[str, str]) -> None:
    PROCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCS_PATH.write_text(json.dumps(d), encoding="utf-8")


def register(pid: int, tag: str) -> None:
    d = _load()
    d[str(pid)] = tag
    _save(d)


def unregister(pid: int) -> None:
    d = _load()
    if d.pop(str(pid), None) is not None:
        _save(d)


def _cmdline(pid: int) -> str | None:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return None


def reap() -> list[int]:
    """등록됐지만 아직 살아 있는 프로세스를 종료하고 종료한 PID 목록을 돌려준다."""
    killed: list[int] = []
    for spid, tag in _load().items():
        pid = int(spid)
        cmd = _cmdline(pid)
        if cmd is not None and tag in cmd:
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if _cmdline(pid) is None or _is_zombie(pid):
                    break
                time.sleep(0.1)
            else:
                os.kill(pid, signal.SIGKILL)
            killed.append(pid)
    _save({})
    return killed


def _is_zombie(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z"
    except OSError:
        return True
