"""생성 화면용 훈련 방식 후보·추천(PLAN-METHODS 6단계 전 보강) — 활성 목표 없이 입력(거리·러닝 요일·목표·기간)만으로 낸다.

후보는 `candidates_for` 가드, 추천은 AI(캐시 범위 'draft', 입력 해시 일치 때만)·없으면 규칙 폴백. 생성은 백그라운드.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import date

from src.services import method_recommend as mr

SCOPE = "draft"
_cooldown: dict[str, float] = {}
_lock = threading.Lock()


def build_draft_input(conn: sqlite3.Connection, distance_km: float, run_days: int | None,
                      target_time_sec: int | None, weeks: int | None, today: date | None = None) -> dict:
    from src.training.methods import candidates_for
    from src.training.planner_rules import resolve_distance_label
    today = today or date.today()
    dlabel = resolve_distance_label(distance_km, None)
    cands = [{"id": m.id, "label": m.label, "summary": m.summary, "pros": list(m.pros), "cons": list(m.cons),
              "target_runners": m.target_runners} for m in candidates_for(dlabel, run_days)]
    goal = {"distance": dlabel, "weeks_to_race": weeks,
            "target_min": int(round(target_time_sec / 60.0)) if target_time_sec else None}
    inp = {"goal": {k: v for k, v in goal.items() if v is not None}, "run_days_per_week": run_days,
           "history": mr._history(conn, today), "vdot": mr._vdot(conn, today), "races": mr._races(conn),
           "current": "balanced", "candidates": cands}
    return {k: v for k, v in inp.items() if v is not None}


def view(conn: sqlite3.Connection, inp: dict) -> dict:
    ai = mr.get_cached_scope(conn, SCOPE, inp)
    return {"source": "ai" if ai else "rule", **(ai or mr.fallback(inp)), "current": inp["current"]}


def warm(db_path: str, config: dict | None, inp: dict, now: float | None = None) -> bool:
    """같은 입력은 30분 쿨다운 안에 한 번만 백그라운드 생성을 예약한다."""
    key, t = f"{db_path}:{mr.src_hash(inp)}", time.monotonic() if now is None else now
    with _lock:
        if t - _cooldown.get(key, -mr.COOLDOWN_SEC) < mr.COOLDOWN_SEC:
            return False
        _cooldown[key] = t

    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                mr.generate_for(c, config, inp, SCOPE)
        except Exception:  # noqa: BLE001
            mr.log.warning("draft method recommend failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="method-recommend-draft").start()
    return True
