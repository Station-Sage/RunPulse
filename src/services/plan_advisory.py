"""skip/rest 반복 경고 A1~A6 — 거부하지 않고 안내만 한다 (ADR-035, DESIGN-PLAN-ROW-ACTION-COACHING §3).

같은 코드는 ISO 주당 1회만 낸다(발급 사실은 조정 행 reasons 의 {"key":"advisory"}). 통증 사유 조정은 세지도 띄우지도 않는다.
A6(계획 다시 맞추기)이 켜지면 A1 은 숨긴다. 문구는 사실 + 영향 + 선택지 하나, 비난·느낌표 없음.
"""
from __future__ import annotations

from src.training.goals import get_active_goal
import json
import sqlite3
from datetime import date, timedelta

from src.training import week_compliance

WINDOW_DAYS = 7
REST_STREAK_MIN = 3
WEEK_DROP_PCT = -30.0
ACWR_LOW = 0.8
LONG_MIN_KM = 16.0
FULL_MARATHON_KM = 40.0
REPLAN_COMPLIANCE = 0.5
EASY_TYPES = ("easy", "recovery")
LONG_TYPES = ("long", "long_mp")


def _events(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """[start, end] 의 accepted 조정 중 쉼/건너뜀/품질→이지 전환(통증 사유 제외)."""
    out = []
    for adj_id, wid, d, op, bj, aj, rj in conn.execute(
            "SELECT id, workout_id, date, op, before_json, after_json, reasons_json FROM plan_adjustments"
            " WHERE decision='accepted' AND date >= ? AND date <= ? AND op IN ('rest','skip','replace')"
            " ORDER BY date, id", (start, end)):
        if any(r.get("key") == "pain" for r in json.loads(rj or "[]")):
            continue
        before, after = json.loads(bj or "{}"), json.loads(aj or "{}")
        if before.get("workout_type") in (None, "rest"):
            continue
        if op == "replace" and not (before.get("workout_type") in week_compliance.QUALITY_TYPES
                                    and after.get("workout_type") in EASY_TYPES):
            continue
        out.append({"id": adj_id, "workout_id": wid, "date": d, "op": op})
    return out


def _rest_days(conn: sqlite3.Connection, start: str, end: str) -> int:
    return len({e["date"] for e in _events(conn, start, end)})


def _week(day: date) -> tuple[date, date]:
    ws = day - timedelta(days=day.weekday())
    return ws, ws + timedelta(days=6)


def _q_dropped_2(conn: sqlite3.Connection, today: date) -> bool:
    qs = ",".join("?" * len(week_compliance.QUALITY_TYPES))
    rows = conn.execute(
        f"SELECT id FROM planned_workouts WHERE workout_type IN ({qs}) AND date <= ? AND date >= ?"
        " ORDER BY date DESC LIMIT 2", (*week_compliance.QUALITY_TYPES, today.isoformat(),
                                        (today - timedelta(days=28)).isoformat())).fetchall()
    if len(rows) < 2:
        return False
    dropped = {e["workout_id"] for e in _events(conn, (today - timedelta(days=28)).isoformat(), today.isoformat())}
    return all(r[0] in dropped for r in rows)


def _long_dropped_2w(conn: sqlite3.Connection, today: date) -> int | None:
    """풀 마라톤 목표에서 직전 2주 연속 롱런이 건너뜀/16km 미만이면 남은 롱런 횟수, 아니면 None."""
    goal = get_active_goal(conn)
    if not goal or (goal["distance_km"] or 0) < FULL_MARATHON_KM:
        return None
    ws, _ = _week(today)
    ph = ",".join("?" * len(LONG_TYPES))
    for k in (1, 2):
        start, end = ws - timedelta(weeks=k), ws - timedelta(weeks=k) + timedelta(days=6)
        longs = conn.execute(f"SELECT id FROM planned_workouts WHERE workout_type IN ({ph}) AND date >= ? AND date <= ?",
                             (*LONG_TYPES, start.isoformat(), end.isoformat())).fetchall()
        if not longs:
            return None
        dropped = {e["workout_id"] for e in _events(conn, start.isoformat(), end.isoformat())}
        best = conn.execute(
            "SELECT MAX(distance_m) / 1000.0 FROM v_canonical_activities WHERE activity_type='running'"
            " AND substr(start_time,1,10) >= ? AND substr(start_time,1,10) <= ?",
            (start.isoformat(), end.isoformat())).fetchone()[0] or 0.0
        if not (all(r[0] in dropped for r in longs) or best < LONG_MIN_KM):
            return None
    return conn.execute(f"SELECT COUNT(*) FROM planned_workouts WHERE workout_type IN ({ph}) AND date > ? AND date <= ?",
                        (*LONG_TYPES, today.isoformat(), goal["race_date"] or "9999-12-31")).fetchone()[0]


def _replan(conn: sqlite3.Connection, today: date, a1: bool) -> str | None:
    """직전 2주 세션 이행 < 50% 이거나, 이번 주 A1 이 직전 주에도 이어졌으면 문구."""
    ws, _ = _week(today)
    done = total = 0
    for k in (1, 2):
        s = ws - timedelta(weeks=k)
        sess = week_compliance.compute(conn, s, s + timedelta(days=6), None, today)["compliance"]["sessions"]
        done, total = done + sess["done"], total + sess["total"]
    if total >= 4 and done / total < REPLAN_COMPLIANCE:
        return f"최근 2주 세션 {total}개 중 {done}개를 했어요. 계획을 지금 흐름에 맞추면 남은 기간을 더 잘 쓸 수 있어요."
    prev = (ws - timedelta(weeks=1)).isoformat(), (ws - timedelta(days=1)).isoformat()
    if a1 and _rest_days(conn, *prev) >= REST_STREAK_MIN:
        return "2주 연속 쉬는 날이 많았어요. 계획을 지금 흐름에 맞추면 남은 기간을 더 잘 쓸 수 있어요."
    return None


def compute(conn: sqlite3.Connection, today: str, delta: dict | None) -> list[dict]:
    """오늘 기준 해당 경고 전부(주 1회 제한 전). 데이터가 없으면 빈 리스트."""
    t = date.fromisoformat(today)
    n = _rest_days(conn, (t - timedelta(days=WINDOW_DAYS - 1)).isoformat(), today)
    a1 = n >= REST_STREAK_MIN
    a4 = bool(delta) and delta["week_pct"] <= WEEK_DROP_PCT
    out = []
    replan = _replan(conn, t, a1)
    if replan:
        out.append({"code": "REPLAN", "severity": "info", "text": replan})
    elif a1:
        out.append({"code": "REST_STREAK", "severity": "info",
                    "text": f"최근 7일 중 {n}일을 쉬었어요. 지금 주간 계획이 일정에 비해 많을 수 있어요."})
    if _q_dropped_2(conn, t):
        out.append({"code": "Q_DROPPED_2", "severity": "caution",
                    "text": "품질 세션 두 번을 이어서 쉬었어요. 다음 품질 세션은 반복을 하나 줄여서 시작하면 부담이 덜해요."})
    left = _long_dropped_2w(conn, t)
    if left is not None:
        out.append({"code": "LONG_DROPPED_2W", "severity": "caution",
                    "text": f"2주째 롱런이 짧았어요. 대회까지 롱런 기회가 {left}번 남았어요."})
    if a4:
        out.append({"code": "WEEK_LOAD_DROP", "severity": "info",
                    "text": f"이번 주 부하가 원래 계획보다 약 {abs(round(delta['week_pct']))}% 줄어요."})
    acwr = (delta or {}).get("acwr_after")
    if acwr is not None and acwr < ACWR_LOW and (a1 or a4):
        out.append({"code": "ACWR_LOW", "severity": "info", "text": f"이번 주는 회복 주에 가까워요(ACWR {acwr})."})
    return out


def _issued(conn: sqlite3.Connection, today: date) -> set[str]:
    ws, we = _week(today)
    codes = set()
    for (rj,) in conn.execute("SELECT reasons_json FROM plan_adjustments WHERE date >= ? AND date <= ?",
                              (ws.isoformat(), we.isoformat())):
        codes |= {r["code"] for r in json.loads(rj or "[]") if r.get("key") == "advisory"}
    return codes


def issue(conn: sqlite3.Connection, adj_id: int, today: str, delta: dict | None) -> list[dict]:
    """이번 주 아직 안 낸 경고를 골라 adj_id 조정 행에 발급 사실을 기록하고 돌려준다. 통증 조정에는 내지 않는다."""
    row = conn.execute("SELECT reasons_json FROM plan_adjustments WHERE id = ?", (adj_id,)).fetchone()
    reasons = json.loads(row[0] or "[]") if row else []
    if not row or any(r.get("key") == "pain" for r in reasons):
        return []
    done = _issued(conn, date.fromisoformat(today))
    new = [a for a in compute(conn, today, delta) if a["code"] not in done]
    if new:
        reasons += [{"key": "advisory", "code": a["code"]} for a in new]
        conn.execute("UPDATE plan_adjustments SET reasons_json = ? WHERE id = ?",
                     (json.dumps(reasons, ensure_ascii=False), adj_id))
        conn.commit()
    return new
