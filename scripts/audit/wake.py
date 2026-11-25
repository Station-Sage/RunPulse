"""pacing 정지 시 재개 시각에 루프를 깨우는 일회성 systemd 타이머 예약 — 100분 주기 타이머를 기다리지 않게 한다."""
from __future__ import annotations

import subprocess
import time

UNIT = "runpulse-pacing-wake"
MARGIN_SEC = 60
SERVICE = "runpulse-audit.service"


def _run(args: list[str]) -> int:
    return subprocess.run(args, capture_output=True, text=True, timeout=30).returncode


def schedule(resume_at: float | None, now: float | None = None, run=_run) -> bool:
    """resume_at 직후에 감사 서비스를 한 번 시작하도록 예약(기존 예약은 교체). 예약했으면 True."""
    if not resume_at:
        return False
    delay = max(int(resume_at - (now or time.time())) + MARGIN_SEC, MARGIN_SEC)
    run(["systemctl", "--user", "stop", f"{UNIT}.timer"])
    return run(["systemd-run", "--user", f"--unit={UNIT}", f"--on-active={delay}s",
                "systemctl", "--user", "start", "--no-block", SERVICE]) == 0
