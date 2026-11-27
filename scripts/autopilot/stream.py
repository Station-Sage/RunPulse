"""claude -p stream-json 실행기 — 출력을 실시간으로 읽어 rate_limit_event 도착 즉시 원장에 관측을 남긴다."""
from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from . import ledger


def run(cmd: list[str], timeout: float, cwd: Path | None = None, unit_id: str = "observe") -> tuple[str, int, bool]:
    """(stdout, returncode, timed_out). 타임아웃이면 프로세스를 죽이고 returncode=-1."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, text=True)
    lines: list[str] = []

    def reader() -> None:
        for line in proc.stdout:
            lines.append(line)
            if '"rate_limit_event"' in line:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(d, dict) and d.get("rate_limit_info"):
                    ledger.append_observation(d["rate_limit_info"], unit_id)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        timed_out = True
    t.join(5)
    return "".join(lines), (-1 if timed_out else proc.returncode), timed_out
