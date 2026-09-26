"""외부 계획 인제스트(P7-PRED-44) — Garmin 저장 워크아웃·적응형 계획, Intervals 계획 이벤트 → planned_workouts.

실 API 응답 형태(2026-09-26 Garmin 실측):
  get_workout_by_id: {"workoutId", "workoutName", "sportType": {"sportTypeKey"}, "workoutSegments": [{"workoutSteps": [
      {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "warmup|interval|recovery|rest|cooldown|other"},
       "endCondition": {"conditionTypeKey": "lap.button|time|distance"}, "endConditionValue": 초 또는 m,
       "targetType": {"workoutTargetTypeKey": "no.target|pace.zone|heart.rate.zone|..."},
       "targetValueOne"/"targetValueTwo": pace.zone 은 m/s(빠른 쪽·느린 쪽 순서 무관), HR 은 bpm},
      {"type": "RepeatGroupDTO", "numberOfIterations": n, "workoutSteps": [...]}]}]}
  get_adaptive_training_plan_by_id: {"trainingPlanId", "name", "taskList": [{"taskWorkout": {"workoutName",
      "workoutDescription": "5:50/km", "scheduledDate", "estimatedDurationInSecs", "workoutPhrase", "restDay"}}]}
  활동 payload 의 workoutId 로 저장 워크아웃과 실행을 잇는다(135건/16개 id, 2개는 삭제되어 404).
Intervals 이벤트(GET /events?category=WORKOUT)는 이 환경에서 401(키 무효)이라 응답을 직접 확인하지 못했다 —
공개 문서의 필드(start_date_local·name·type·moving_time·distance·workout_doc)만 최소 파싱하고 원문을 저장한다(PRED-99 U-21).
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3

from src.utils.raw_payload import store_raw_payload as upsert_payload

log = logging.getLogger(__name__)

_STEP_TYPES = {"warmup": "warmup", "cooldown": "cooldown", "interval": "work", "recovery": "rest", "rest": "rest"}
_PACE_TEXT = re.compile(r"(\d+):(\d{2})\s*/\s*km")


def _step(s: dict) -> dict | None:
    """ExecutableStepDTO → structure step. 알 수 없는 단계 유형은 work 로 오인하지 않고 None(경고)."""
    key = (s.get("stepType") or {}).get("stepTypeKey")
    typ = _STEP_TYPES.get(key)
    if typ is None:
        log.warning("plan_ingest: 알 수 없는 Garmin 단계 유형 %r — 건너뜀", key)
        return None
    out: dict = {"type": typ}
    cond, val = (s.get("endCondition") or {}).get("conditionTypeKey"), s.get("endConditionValue")
    if cond == "distance" and val:
        out["dist_m"] = float(val)
    elif cond == "time" and val:
        out["dur_s"] = float(val)
    tgt, lo, hi = (s.get("targetType") or {}).get("workoutTargetTypeKey"), s.get("targetValueOne"), s.get("targetValueTwo")
    if lo and hi and tgt == "pace.zone":
        out["speed_lo"], out["speed_hi"] = round(min(lo, hi), 4), round(max(lo, hi), 4)
    elif lo and hi and tgt == "heart.rate.zone":
        out["hr_lo"], out["hr_hi"] = min(lo, hi), max(lo, hi)
    return out


def _steps(items: list[dict]) -> list[dict]:
    out = []
    for s in items or []:
        if s.get("type") == "RepeatGroupDTO":
            inner = _steps(s.get("workoutSteps") or [])
            if inner:
                out.append({"type": "repeat", "count": int(s.get("numberOfIterations") or 1), "steps": inner})
        else:
            st = _step(s)
            if st:
                out.append(st)
    return out


def _guess_type(name: str, steps: list[dict]) -> str:
    """workout_type 어휘(easy|tempo|interval|long|recovery)로. 구조 우선, 이름은 보조."""
    n = name or ""
    rep = next((s for s in steps if s["type"] == "repeat"), None)
    if rep and rep["count"] >= 3:
        return "interval"
    if any(k in n for k in ("장거리", "롱", "Long")):
        return "long"
    if any(k in n for k in ("회복", "Recovery")):
        return "recovery"
    if rep or any(k in n for k in ("템포", "Tempo", "크루즈")):
        return "tempo"
    return "easy"


def parse_garmin_workout(payload: dict) -> dict:
    """Garmin 저장 워크아웃 → {"name","sport","structure","distance_km","workout_type"}. 러닝 외 종목은 sport 로 구분."""
    segs = payload.get("workoutSegments") or []
    steps = _steps([s for seg in segs for s in seg.get("workoutSteps") or []])
    name = payload.get("workoutName") or ""
    dist = payload.get("estimatedDistanceInMeters") or 0
    return {"name": name, "sport": (payload.get("sportType") or {}).get("sportTypeKey"),
            "structure": {"steps": steps} if steps else None,
            "distance_km": round(dist / 1000, 2) if dist else None, "workout_type": _guess_type(name, steps)}


def parse_garmin_adaptive_task(task: dict) -> dict | None:
    """적응형 계획 taskList 항목 → 지속시간 + 페이스 문구만 있는 단일 work 구조. 휴식일은 None."""
    w = task.get("taskWorkout") or {}
    if w.get("restDay") or not w.get("scheduledDate"):
        return None
    step: dict = {"type": "work"}
    if w.get("estimatedDurationInSecs"):
        step["dur_s"] = float(w["estimatedDurationInSecs"])
    m = _PACE_TEXT.search(w.get("workoutDescription") or "")
    if m:
        v = 1000.0 / (int(m.group(1)) * 60 + int(m.group(2)))
        step["speed_lo"] = step["speed_hi"] = round(v, 4)
    name = w.get("workoutName") or ""
    wtype = "long" if w.get("workoutPhrase") == "LONG_WORKOUT" else _guess_type(name, [])
    return {"name": name, "sport": (w.get("sportType") or {}).get("sportTypeKey"), "date": w["scheduledDate"][:10],
            "structure": {"steps": [step]}, "distance_km": None, "workout_type": wtype}


def parse_intervals_event(payload: dict) -> dict | None:
    """Intervals 이벤트(문서 기준, 실응답 미확인) → 날짜·이름·거리·유형. 구조(workout_doc)는 파싱하지 않는다."""
    day = str(payload.get("start_date_local") or "")[:10]
    if not day or (payload.get("category") not in (None, "WORKOUT")):
        return None
    dist = payload.get("distance")
    name = payload.get("name") or ""
    return {"name": name, "sport": payload.get("type"), "date": day, "structure": None,
            "distance_km": round(dist / 1000, 2) if dist else None, "workout_type": _guess_type(name, [])}


def store_planned(conn: sqlite3.Connection, *, source_system: str, external_id: str, date: str, parsed: dict,
                  garmin_workout_id: str | None = None, matched_activity_id: int | None = None) -> int:
    """(source_system, external_id) 로 UPSERT 한다. 같은 날짜의 앱 계획(runpulse)은 건드리지 않는다. 반환: planned_workouts.id"""
    st = json.dumps(parsed["structure"], ensure_ascii=False) if parsed.get("structure") else None
    row = conn.execute("SELECT id FROM planned_workouts WHERE source_system=? AND external_id=?",
                       (source_system, external_id)).fetchone()
    done = 1 if matched_activity_id else 0
    if row:
        conn.execute("UPDATE planned_workouts SET date=?, workout_type=?, distance_km=?, description=?, structure_json=?, "
                     "garmin_workout_id=COALESCE(?, garmin_workout_id), updated_at=datetime('now') WHERE id=?",
                     (date, parsed["workout_type"], parsed.get("distance_km"), parsed.get("name"), st, garmin_workout_id, row[0]))
        return row[0]
    cur = conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, description, completed, "
                       "matched_activity_id, source, source_system, external_id, structure_json, garmin_workout_id) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (date, parsed["workout_type"], parsed.get("distance_km"), parsed.get("name"), done,
                        matched_activity_id, source_system, source_system, external_id, st, garmin_workout_id))
    return cur.lastrowid


def _canonical_id(conn: sqlite3.Connection, garmin_activity_id: str) -> tuple | None:
    """Garmin 활동 id(source_id) → 같은 그룹의 canonical 활동 행(matcher 가 쓰는 형태)."""
    return conn.execute(
        "SELECT c.id, DATE(c.start_time), c.distance_m/1000.0, c.avg_pace_sec_km, c.avg_hr, c.duration_sec, c.activity_type "
        "FROM activity_summaries a JOIN v_canonical_activities c "
        "  ON COALESCE(c.matched_group_id, 'solo_'||c.id) = COALESCE(a.matched_group_id, 'solo_'||a.id) "
        "WHERE a.source='garmin' AND a.source_id=? LIMIT 1", (str(garmin_activity_id),)).fetchone()


def ingest_garmin_executed(conn: sqlite3.Connection, client, pause_s: float = 0.4) -> dict:
    """활동 payload 의 workoutId 로 저장 워크아웃을 조회해 '실행된 계획' 행을 만들고 세그먼트 이행률까지 채운다.

    external_id = "<workoutId>@<활동 날짜>", 이미 실행이 확인된 활동(matched_activity_id)이라 날짜 매칭보다 workoutId 가 우선한다.
    workout 이 삭제(404)됐거나 러닝이 아니면 건너뛴다(원문은 저장). API 실패는 로그 후 계속."""
    import time
    from src.training.matcher import _save_session_outcome
    from src.training.outcome_store import update_outcome_v2
    acts = conn.execute("SELECT entity_id, payload FROM source_payloads WHERE source='garmin' AND entity_type='activity_summary' "
                        "AND payload LIKE '%\"workoutId\": %'").fetchall()
    by_wid: dict[int, list[str]] = {}
    for eid, p in acts:
        wid = json.loads(p).get("workoutId")
        if wid:
            by_wid.setdefault(int(wid), []).append(str(eid))
    stats = {"workouts": 0, "missing": 0, "non_running": 0, "planned": 0, "outcomes": 0}
    for wid, act_ids in by_wid.items():
        try:
            raw = client.get_workout_by_id(wid)
        except Exception as e:
            log.warning("garmin workout %s 조회 실패: %s", wid, e)
            stats["missing"] += 1
            continue
        time.sleep(pause_s)
        upsert_payload(conn, "garmin", "planned_workout", str(wid), raw)
        parsed = parse_garmin_workout(raw)
        stats["workouts"] += 1
        if parsed["sport"] != "running":
            stats["non_running"] += 1
            continue
        for aid in act_ids:
            row = _canonical_id(conn, aid)
            if not row:
                continue
            pid = store_planned(conn, source_system="garmin", external_id=f"{wid}@{row[1]}", date=row[1], parsed=parsed,
                                garmin_workout_id=str(wid), matched_activity_id=row[0])
            stats["planned"] += 1
            if not conn.execute("SELECT 1 FROM session_outcomes WHERE planned_id=?", (pid,)).fetchone():
                _save_session_outcome(conn, plan_id=pid, activity_id=row[0], plan_date=row[1], plan_dist=parsed["distance_km"],
                                      plan_pace=None, plan_hr_zone=None, act_row=row)
            if update_outcome_v2(conn, pid, row[0]):
                stats["outcomes"] += 1
    conn.commit()
    return stats


def ingest_garmin_adaptive(conn: sqlite3.Connection, client, today: str) -> dict:
    """가민 코치(적응형) 계획의 오늘 이후 예정 워크아웃. 계획 목록에서 시작~종료가 오늘을 포함하는 것만."""
    stats = {"plans": 0, "planned": 0}
    try:
        plans = (client.get_training_plans() or {}).get("trainingPlanList") or []
    except Exception as e:
        log.warning("garmin training_plans 조회 실패: %s", e)
        return stats
    for p in plans:
        if p.get("trainingPlanCategory") != "FBT_ADAPTIVE" or (p.get("endDate") or "")[:10] < today:
            continue
        try:
            detail = client.get_adaptive_training_plan_by_id(p["trainingPlanId"])
        except Exception as e:
            log.warning("garmin adaptive plan %s 조회 실패: %s", p.get("trainingPlanId"), e)
            continue
        upsert_payload(conn, "garmin", "planned_workout", f"plan:{p['trainingPlanId']}", detail)
        stats["plans"] += 1
        for task in detail.get("taskList") or []:
            parsed = parse_garmin_adaptive_task(task)
            if parsed and parsed["date"] >= today:
                store_planned(conn, source_system="garmin", external_id=f"fbt:{p['trainingPlanId']}:{parsed['date']}",
                              date=parsed["date"], parsed=parsed)
                stats["planned"] += 1
    conn.commit()
    return stats


def ingest_intervals_events(conn: sqlite3.Connection, events: list[dict]) -> int:
    """Intervals 계획 이벤트 목록 → planned_workouts. 원문 먼저 저장, 파싱 실패 항목은 건너뛴다."""
    n = 0
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("id") is None:
            continue
        upsert_payload(conn, "intervals", "planned_workout", str(ev["id"]), ev)
        parsed = parse_intervals_event(ev)
        if parsed:
            store_planned(conn, source_system="intervals", external_id=str(ev["id"]), date=parsed["date"], parsed=parsed)
            n += 1
    conn.commit()
    return n


def main(argv: list[str] | None = None) -> None:
    """사람 실행용: python3 -m src.sync.plan_ingest --db <db> --user <id> — Garmin 로그인 후 실행 계획·적응형 계획 인제스트."""
    import argparse
    from datetime import date
    from src.sync.garmin_auth import _login
    from src.utils.config import load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", required=True)
    a = ap.parse_args(argv)
    config = load_config(user_id=a.user)
    from pathlib import Path
    ts = Path((config.get("garmin") or {}).get("tokenstore", "")).expanduser()
    if not ts.exists():  # config.json 의 tokenstore 가 컨테이너 경로(/app/...)인 경우 호스트 경로로 대체
        config.setdefault("garmin", {})["tokenstore"] = str(Path("data/users") / a.user / ".garminconnect")
    conn = sqlite3.connect(a.db)
    client = _login(config)
    print("executed:", ingest_garmin_executed(conn, client))
    print("adaptive:", ingest_garmin_adaptive(conn, client, date.today().isoformat()))


if __name__ == "__main__":
    main()
