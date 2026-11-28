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
TUNABLES = {"SESSION_PACING_ENABLED": (int, 0, 1),   # name: (type, min, max)
    "WEEKLY_PACING_ENABLED": (int, 0, 1),
    "AUDIT_TOOL_CALLS_PER_ROUND": (int, 1, 40),
}
TIMERS = ("runpulse-audit", "runpulse-watch")
ACTIONS = ("start", "resume", "pause", "stop")


def _sh(cmd: list[str]) -> bool:
    return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0


def audit(action: str, detail: dict, ok: bool, state_dir: Path | None = None) -> None:
    d = state_dir or settings.STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    with (d / "console_audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, "detail": detail, "ok": ok}, ensure_ascii=False) + "\n")


def _clear_stopped(d: Path) -> None:
    """사람이 시작/재개를 눌렀으면 stopreason.resume(human) 정책대로 정지를 풀어 정지 지점부터 이어간다."""
    from scripts.audit import stopreason
    p = d / "cycle_state.json"
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if stopreason.resume(st, human=True):
        p.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


_ACTION_KO = {"start": "시작", "resume": "재개", "pause": "일시중지", "stop": "즉시중지"}


def _mark_progress(action: str, killed, d: Path) -> None:
    """사람이 누른 제어를 진행 로그에도 남긴다(감사 로그와 별개로 로그 탭에서 흐름이 보이도록)."""
    from scripts.audit import progress
    extra = f" · 프로세스 {len(killed)}개 종료" if isinstance(killed, (list, tuple)) and killed else ""
    progress.mark(f"[콘솔] {_ACTION_KO[action]} 요청{extra}", d / "progress.log")


def _sync_wake() -> None:
    """페이싱 설정·재개 직후 wake 타이머를 현재 판정에 맞춘다(실패해도 제어 동작은 성공)."""
    try:
        from scripts.audit import wake
        wake.sync()
    except Exception:
        pass


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
            _clear_stopped(d)
            run(["systemctl", "--user", "start", "--no-block", "runpulse-audit.service"])
        res = {"ok": True, "action": action, "killed": killed, "pause": pause.exists(), "stop": stop.exists()}
        audit(action, {"killed": killed}, True, d)
        _mark_progress(action, killed, d)
    if state_dir is None and action != "stop":
        _sync_wake()
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
    if state_dir is None:
        _sync_wake()
    return {"ok": True, "tunables": cur}
