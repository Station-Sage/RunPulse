"""관제 제어(C2) — 시작·재개·일시중지·즉시중지, 조정값(tunables), 자동 재개 타이머 간격. 모든 쓰기는 여기서만, 감사 로그를 남긴다.

일시중지 = PAUSE 플래그(현재 단계는 끝내고 다음 단계부터 멈춤), 즉시중지 = STOP 플래그 + 등록된 PID 종료(procs.reap, 미등록 프로세스는 건드리지 않음).
조정값은 화이트리스트·범위 검증 후 tunables.json 에 병합, 타이머 간격은 systemd user drop-in 으로 쓰고 daemon-reload 한다.
외부 명령(systemctl)은 run 으로 주입해 테스트에서 실제 호출하지 않는다.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path

from scripts.autopilot import settings

LOCK = threading.Lock()
TUNABLES = {  # name: (type, min, max)
    "AUDIT_TOOL_CALLS_PER_ROUND": (int, 1, 40),
    "FALLBACK_SESSION_MAX_RUNS": (int, 1, 60),
    "FALLBACK_SESSION_MAX_USD": (float, 1.0, 100.0),
}
TIMERS = ("runpulse-audit", "runpulse-watch")
INTERVAL_RANGE = (10, 1440)  # 분
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
ACTIONS = ("start", "resume", "pause", "stop")


def _sh(cmd: list[str]) -> bool:
    return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0


def audit(action: str, detail: dict, ok: bool, state_dir: Path | None = None) -> None:
    d = state_dir or settings.STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    with (d / "console_audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, "detail": detail, "ok": ok}, ensure_ascii=False) + "\n")


def act(action: str, state_dir: Path | None = None, run=_sh, reap=None) -> dict:
    """start/resume/pause/stop. start 는 플래그를 지우고 감사 서비스를 즉시 1회 기동한다."""
    if action not in ACTIONS:
        return {"ok": False, "error": f"알 수 없는 동작: {action}"}
    d = state_dir or settings.STATE_DIR
    pause, stop = d / "PAUSE", d / "STOP"
    d.mkdir(parents=True, exist_ok=True)
    killed: list[int] = []
    with LOCK:
        if action == "pause":
            pause.touch()
        elif action == "stop":
            stop.touch()
            if reap is None:
                from scripts.audit import procs
                reap = procs.reap
            killed = reap()
        else:
            pause.unlink(missing_ok=True)
            stop.unlink(missing_ok=True)
            if action == "start":
                run(["systemctl", "--user", "start", "--no-block", "runpulse-audit.service"])
        res = {"ok": True, "action": action, "killed": killed, "pause": pause.exists(), "stop": stop.exists()}
        audit(action, {"killed": killed}, True, d)
    return res


def set_tunables(values: dict, state_dir: Path | None = None) -> dict:
    """화이트리스트·범위 검증 후 tunables.json 에 병합. 하나라도 어긋나면 전부 거부한다."""
    d = state_dir or settings.STATE_DIR
    clean: dict = {}
    for k, v in values.items():
        if k not in TUNABLES:
            return {"ok": False, "error": f"조정 불가 항목: {k}"}
        typ, lo, hi = TUNABLES[k]
        try:
            n = typ(v)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"{k}: 숫자가 아님"}
        if not lo <= n <= hi:
            return {"ok": False, "error": f"{k}: {lo}~{hi} 범위만 허용"}
        clean[k] = n
    with LOCK:
        p = d / "tunables.json"
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cur = {}
        cur.update(clean)
        d.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
        audit("tunables", clean, True, d)
    return {"ok": True, "tunables": cur}


def set_interval(timer: str, minutes: int, state_dir: Path | None = None, unit_dir: Path | None = None, run=_sh) -> dict:
    """자동 재개 타이머 간격(직전 실행 종료 후 N분)을 drop-in 으로 바꾸고 daemon-reload."""
    lo, hi = INTERVAL_RANGE
    if timer not in TIMERS:
        return {"ok": False, "error": f"알 수 없는 타이머: {timer}"}
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return {"ok": False, "error": "분은 정수"}
    if not lo <= m <= hi:
        return {"ok": False, "error": f"{lo}~{hi}분만 허용"}
    dd = (unit_dir or UNIT_DIR) / f"{timer}.timer.d"
    with LOCK:
        dd.mkdir(parents=True, exist_ok=True)
        (dd / "interval.conf").write_text(f"[Timer]\nOnUnitInactiveSec=\nOnUnitInactiveSec={m}min\n", encoding="utf-8")
        ok = run(["systemctl", "--user", "daemon-reload"]) and run(["systemctl", "--user", "restart", f"{timer}.timer"])
        audit("interval", {"timer": timer, "minutes": m}, ok, state_dir)
    return {"ok": ok, "timer": timer, "minutes": m} if ok else {"ok": False, "error": "systemctl 실패"}
