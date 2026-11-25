"""진행 흐름 계산 — events.jsonl(없으면 progress.log 추정)에서 현재 라운드의 4단계(감사·설계·개발·반영) 진행도를 만든다."""
from __future__ import annotations

import re
import time
from pathlib import Path

from scripts.audit import progress
from scripts.autopilot import queue, settings

STAGE_OF = {"audit": 1, "design": 2, "develop": 3, "await": 3, "test": 3}
SUBS = ("sweep", "audit", "review")
_LOG_RE = re.compile(r"^(\d\d):(\d\d):(\d\d) \[루프\] 라운드 (\d+) · (\w+) 단계 시작")


def _log_events(now: float, rnd: int, log: Path | None) -> list[dict]:
    """progress.log(시각만 있음)에서 현재 라운드의 phase 이벤트를 추정 — 이벤트 파일이 생기기 전 라운드용."""
    out = []
    try:
        lines = (log or progress.LOG_PATH).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    for ln in lines:
        m = _LOG_RE.match(ln)
        if not m or int(m[4]) != rnd:
            continue
        h, mi, s = int(m[1]), int(m[2]), int(m[3])
        ts = time.mktime(time.strptime(f"{day} {h}:{mi}:{s}", "%Y-%m-%d %H:%M:%S"))
        if ts > now:
            ts -= 86400
        out.append({"ts": ts, "kind": "phase", "round": rnd, "phase": m[5], "inferred": True})
    cut = max((i for i, e in enumerate(out) if e["phase"] == "audit"), default=0)
    return out[cut:]


def _sub_states(evs: list[dict]) -> dict:
    st = {k: {"state": "pending", "ts": None} for k in SUBS}
    for e in evs:
        if e["kind"] == "sub" and e.get("step") in st:
            st[e["step"]] = {"state": "active" if e["state"] == "start" else "done", "ts": e["ts"]}
    return st


def build(state: dict, now: float, queue_path: Path | None = None, events: list[dict] | None = None,
          log: Path | None = None, unit_cap: int = 5) -> dict:
    rnd = state.get("round") or 1
    allev = progress.read_events() if events is None else events
    idx = next((i for i, e in enumerate(allev) if e["kind"] == "phase" and e.get("round") == rnd), None)
    evs = allev[idx:] if idx is not None else _log_events(now, rnd, log)
    inferred = idx is None
    phases = [e for e in evs if e["kind"] == "phase"]
    items = [it for it in queue.parse(queue_path or settings.QUEUE_PATH) if it.mode == "auto"]
    ph = state.get("phase")
    design = next((e for e in reversed(evs) if e["kind"] == "design"), None)
    deploy = next((e for e in reversed(evs) if e["kind"] in ("deploy_start", "deploy_end")), None)
    in_deploy = bool(deploy and deploy["kind"] == "deploy_start" and ph in STAGE_OF)
    stage = 4 if in_deploy else STAGE_OF.get(ph, 0)
    cur = phases[-1] if phases else None
    open_units = sum(1 for it in items if it.stage in ("queued", "in_progress")) + (1 if ph == "test" else 0)
    ustart = next((e for e in reversed(evs) if e["kind"] == "unit_start"), None)
    done = state.get("units_done") or 0
    return {
        "round": rnd, "phase": ph, "stage": stage, "stage_total": 4, "inferred": inferred,
        "round_started": evs[0]["ts"] if evs else None, "phase_started": cur["ts"] if cur else None,
        "now": now, "subs": _sub_states(evs) if stage <= 1 or ph == "audit" else None,
        "design": {k: design[k] for k in ("new", "auto", "user")} if design else None,
        "units": {"done": done, "total": min(unit_cap, done + open_units), "current": state.get("unit"),
                  "started": ustart["ts"] if ustart and ph in ("test", "develop") else None},
        "review_waiting": sum(1 for it in items if it.stage == "review"),
        "deploy": {"active": in_deploy, "ts": deploy["ts"] if deploy else None,
                   "ok": deploy.get("ok") if deploy and deploy["kind"] == "deploy_end" else None,
                   "ran": deploy.get("ran") if deploy and deploy["kind"] == "deploy_end" else None},
    }
