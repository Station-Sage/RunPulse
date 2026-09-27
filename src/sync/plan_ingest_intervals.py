"""Intervals 계획 이벤트 인제스트(P7-PRED-44) — planned_workouts 저장, paired_activity_id 로 실행 활동 연결.

Intervals 이벤트 실응답(2026-09-27, GET /events?oldest=2023-10-01, category=WORKOUT 30건·2025-02~04):
  {"id", "start_date_local", "name", "type": "Run", "moving_time", "distance"(m), "paired_activity_id": "i69765907"|null,
   "workout_doc": {"steps": [{"warmup": true, "duration"} | {"cooldown": true, "duration"} |
       {"pace": {"start", "end", "units": "%pace"} | {"units": "pace_zone", "value": 3}, "duration"(s), "distance"(m)?} |
       {"reps": n, "steps": [...]}]}}
  %pace 는 역치 페이스 대비 비율이라 속도(m/s)로 바꿀 기준이 없다 → 목표 속도는 구조에 넣지 않고 지속시간·거리·강도 구분만 쓴다.
  (API 키는 config.json 에 Fernet("enc:")으로 저장 — CREDENTIAL_ENCRYPTION_KEY 없이 호출하면 401 이라 컨테이너 안에서 실행한다.)
"""
from __future__ import annotations

import sqlite3

from src.sync.plan_ingest import _canonical_id, _guess_type, store_planned
from src.utils.raw_payload import store_raw_payload as upsert_payload


def _iv_steps(items: list[dict], in_repeat: bool = False) -> list[dict]:
    """Intervals workout_doc.steps → structure. %pace 시작이 95 이상이거나 반복 안의 거리 지정 단계는 work, 반복 안의 나머지는 rest.
    반복 밖의 느린 본 구간(이지런 본체)은 품질 비교 대상이 아니므로 넣지 않는다. 속도 목표는 기준 페이스가 없어 생략."""
    out = []
    for s in items or []:
        if "reps" in s:
            inner = _iv_steps(s.get("steps") or [], True)
            if inner:
                out.append({"type": "repeat", "count": int(s["reps"]), "steps": inner})
            continue
        if s.get("warmup") or s.get("cooldown"):
            out.append({"type": "warmup" if s.get("warmup") else "cooldown", **({"dur_s": float(s["duration"])} if s.get("duration") else {})})
            continue
        pace = s.get("pace") or {}
        start = pace.get("start") if pace.get("units") == "%pace" else None
        hard = (start is not None and start >= 95) or (in_repeat and s.get("distance"))
        if hard:
            step = {"type": "work"}
            if s.get("distance"):
                step["dist_m"] = float(s["distance"])
            elif s.get("duration"):
                step["dur_s"] = float(s["duration"])
            out.append(step)
        elif in_repeat:
            out.append({"type": "rest", **({"dur_s": float(s["duration"])} if s.get("duration") else {})})
    return out


def parse_intervals_event(payload: dict) -> dict | None:
    """Intervals 계획 이벤트(category WORKOUT) → 날짜·이름·거리·유형·구조. 다른 category(NOTE 등)는 None."""
    day = str(payload.get("start_date_local") or "")[:10]
    if not day or payload.get("category") != "WORKOUT":
        return None
    dist = payload.get("distance")
    name = payload.get("name") or ""
    steps = _iv_steps((payload.get("workout_doc") or {}).get("steps") or [])
    structure = {"steps": steps} if any(s["type"] in ("work", "repeat") for s in steps) else None
    return {"name": name, "sport": payload.get("type"), "date": day, "structure": structure,
            "distance_km": round(dist / 1000, 2) if dist else None, "workout_type": _guess_type(name, steps)}


def ingest_intervals_events(conn: sqlite3.Connection, events: list[dict]) -> dict:
    """Intervals 계획 이벤트 → planned_workouts. 원문 먼저 저장. paired_activity_id 가 있으면 그 활동에 바로 연결하고 이행률까지 채운다."""
    from src.training.matcher import _save_session_outcome
    from src.training.outcome_store import update_outcome_v2
    stats = {"planned": 0, "linked": 0, "outcomes": 0}
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("id") is None:
            continue
        upsert_payload(conn, "intervals", "planned_workout", str(ev["id"]), ev)
        parsed = parse_intervals_event(ev)
        if not parsed:
            continue
        row = _canonical_id(conn, ev["paired_activity_id"], "intervals") if ev.get("paired_activity_id") else None
        pid = store_planned(conn, source_system="intervals", external_id=str(ev["id"]), date=parsed["date"], parsed=parsed,
                            matched_activity_id=row[0] if row else None)
        stats["planned"] += 1
        if row:
            stats["linked"] += 1
            if not conn.execute("SELECT 1 FROM session_outcomes WHERE planned_id=?", (pid,)).fetchone():
                _save_session_outcome(conn, plan_id=pid, activity_id=row[0], plan_date=parsed["date"],
                                      plan_dist=parsed["distance_km"], plan_pace=None, plan_hr_zone=None, act_row=row)
            if update_outcome_v2(conn, pid, row[0]):
                stats["outcomes"] += 1
    conn.commit()
    return stats
