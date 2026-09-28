"""날짜별 유효 계획·이행 수치 — UX 리뷰 31-coach-plan design §4.1 R1·R2·R3·R5 (읽기 시점 계산).

한 날짜에 계획 행이 여러 개(planner 추천안 + Garmin/Intervals 외부 계획)일 수 있다. 날짜마다 하나의
**유효 계획**을 고르고, 나머지는 대안으로 내린다(분모에 넣지 않음). 이행은 한 숫자로 합치지 않고
세션·볼륨·품질 세 수치로 낸다. 결과 라벨(R5)과 status는 서버가 정해 프론트는 렌더만 한다.

이전 결함: `_compliance_pct`가 planner 행만 세고 대체된 추천안을 분모에 넣어 16.7%(1/6)가 나왔다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training.planned_query import get_planned_workouts

RUN_TYPES = ("running", "trail_running", "treadmill", "indoor_running")
QUALITY_TYPES = {"interval", "tempo", "marathon", "long_mp", "threshold"}
EASY_TYPES = {"easy", "recovery", "long"}
DONE_RATIO = 0.75           # 세션 이행 기준(R3, completed 플래그와 같은 값)
UNDER, OVER = 0.85, 1.15    # 결과 라벨 경계(R5)
PACE_FAST_TOL = 0.03        # 이지·회복·롱: 목표 빠른 쪽 경계보다 3% 넘게 빠르면 강도 어긋남(스트림 대신 평균 페이스 근사)

_LABELS = {
    "missed": ("poor", "놓침"),
    "intensity_off": ("caution", "강도 어긋남"),
    "under": ("caution", "부족"),
    "over": ("good", "초과"),
    "on_target": ("excellent", "계획대로"),
    "matched": ("neutral", "수행(기준 없음)"),
}


def _effective(rows: list[dict]) -> tuple[dict, list[dict]]:
    """R1 우선순위: 실행된 외부 계획 > 외부 계획 > planner 원안. (유효, 대안들)"""
    def rank(w: dict) -> tuple:
        external = w["source"] != "planner"
        return (0 if external and w["matched_activity_id"] else
                1 if external else 2, w["id"])
    ordered = sorted(rows, key=rank)
    return ordered[0], ordered[1:]


def _volume_ratio(eff: dict, planned_km: float | None) -> float | None:
    if eff.get("actual_dist_km") and planned_km:
        return eff["actual_dist_km"] / planned_km
    return None


def outcome_label(eff: dict, planned_km: float | None, act: dict | None, is_past: bool) -> str | None:
    """R5 결과 라벨. 미래·오늘 미수행이면 None."""
    if not eff["matched_activity_id"]:
        if eff.get("completed"):
            return "matched"
        return "missed" if is_past else None
    pace_fast = eff.get("target_pace_min")
    if (eff["workout_type"] in EASY_TYPES and pace_fast and act and act.get("avg_pace_sec_km")
            and act["avg_pace_sec_km"] < pace_fast * (1 - PACE_FAST_TOL)):
        return "intensity_off"
    v = _volume_ratio(eff, planned_km)
    if v is None:
        return "matched"
    if v < UNDER:
        return "under"
    if v > OVER:
        return "over"
    return "on_target"


def _label_view(label: str | None, v: float | None) -> dict:
    if label is None:
        return {}
    status, text = _LABELS[label]
    if label == "under" and v is not None:
        text = f"부족 {round(v * 100)}%"
    elif label == "over" and v is not None:
        text = f"초과 +{round((v - 1) * 100)}%"
    return {"label": label, "status": status, "status_label": text}


def _run_activities(conn: sqlite3.Connection, start: str, end: str) -> dict[str, list[dict]]:
    marks = ",".join("?" * len(RUN_TYPES))
    rows = conn.execute(
        f"SELECT id, substr(start_time, 1, 10), distance_m, avg_pace_sec_km FROM v_canonical_activities"
        f" WHERE activity_type IN ({marks}) AND substr(start_time, 1, 10) BETWEEN ? AND ?",
        (*RUN_TYPES, start, end),
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for aid, d, dist_m, pace in rows:
        out.setdefault(d, []).append({"id": aid, "distance_km": (dist_m or 0) / 1000,
                                      "avg_pace_sec_km": pace})
    return out


def compute(conn: sqlite3.Connection, start: date, end: date, effective_start: date | None,
            today: date | None = None) -> dict:
    """start~end(포함) 날짜별 유효 계획·상태와 이행 수치.

    effective_start 이전 날짜는 `pre_plan`(집계 제외). today 이후는 upcoming.
    """
    today = today or date.today()
    rows: list[dict] = []
    ws = start - timedelta(days=start.weekday())
    while ws <= end:
        rows += [w for w in get_planned_workouts(conn, week_start=ws)
                 if start.isoformat() <= w["date"] <= end.isoformat()]
        ws += timedelta(weeks=1)
    by_date: dict[str, list[dict]] = {}
    for w in rows:
        by_date.setdefault(w["date"], []).append(w)
    acts = _run_activities(conn, start.isoformat(), end.isoformat())
    act_by_id = {a["id"]: a for day in acts.values() for a in day}

    days, unplanned = [], []
    sess_done = sess_total = qual_done = qual_total = 0
    planned_km_sum = 0.0
    counted_dates: list[str] = []   # 볼륨 기준(계획 거리)이 있는 집계일
    no_basis = 0                     # 계획 거리가 없어 볼륨에서 뺀 날 수
    d = start
    while d <= end:
        ds = d.isoformat()
        entry: dict = {"date": ds}
        day_rows = by_date.get(ds, [])
        eff = alts = None
        if day_rows:
            eff, alts = _effective(day_rows)
            # 외부 계획에 거리가 없으면 같은 유형 대안(planner)의 거리를 볼륨 기준으로 쓴다(유형이 다르면 기준 없음)
            planned_km = eff["distance_km"] or next(
                (a["distance_km"] for a in alts
                 if a["distance_km"] and a["workout_type"] == eff["workout_type"]), None)
            entry["effective"] = {k: eff[k] for k in ("id", "source", "workout_type", "distance_km",
                                                     "matched_activity_id", "actual_dist_km")}
            entry["planned_km"] = planned_km
            entry["alternatives"] = [a["id"] for a in alts]
            entry["substituted"] = eff["source"] != "planner" and any(a["source"] == "planner" for a in alts)
        claimed = {w["matched_activity_id"] for w in day_rows if w["matched_activity_id"]}
        for a in acts.get(ds, []):
            if a["id"] not in claimed:
                unplanned.append({"date": ds, "activity_id": a["id"], "distance_km": round(a["distance_km"], 2)})

        is_past = d < today
        if effective_start and d < effective_start:
            entry["state"] = "pre_plan"
        elif eff is None or eff["workout_type"] == "rest":
            entry["state"] = "rest"
        else:
            v = _volume_ratio(eff, entry["planned_km"])
            label = outcome_label(eff, entry["planned_km"], act_by_id.get(eff["matched_activity_id"]), is_past)
            entry.update(_label_view(label, v))
            # 활동이 연결됐으면 볼륨으로 판정(저장된 completed 플래그는 옛 규칙 값일 수 있음),
            # 연결 없는 수동 완료(completed=1)는 이행으로 센다
            if eff["matched_activity_id"]:
                done = v is None or v >= DONE_RATIO
            else:
                done = bool(eff["completed"])
            if eff["matched_activity_id"] or eff["completed"]:
                entry["state"] = "done" if done else "partial"
            elif is_past:
                entry["state"] = "missed"
            else:
                entry["state"] = "upcoming"
            if is_past or done:
                sess_total += 1
                sess_done += done
                if entry["planned_km"]:
                    counted_dates.append(ds)
                    planned_km_sum += entry["planned_km"]
                else:
                    no_basis += 1
                if eff["workout_type"] in QUALITY_TYPES:
                    qual_total += 1
                    qual_done += label in ("on_target", "over")
        if d == today:
            entry["today"] = True
        days.append(entry)
        d += timedelta(days=1)

    actual_km = sum(a["distance_km"] for ds in counted_dates for a in acts.get(ds, []))
    return {
        "days": days,
        "unplanned_runs": unplanned,
        "compliance": {
            "sessions": {"done": sess_done, "total": sess_total},
            "volume": {"actual_km": round(actual_km, 1), "planned_km": round(planned_km_sum, 1),
                       "pct": round(actual_km / planned_km_sum * 100) if planned_km_sum else None,
                       "days_without_target": no_basis},
            "quality": {"done": qual_done, "total": qual_total},
        },
    }
