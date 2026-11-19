"""출처별 마일스톤 훅 (ADR-057) — 대회 결과·목표·대회 등록·재계획·질병/부상 에피소드.

모든 함수는 호출자 트랜잭션 안에서 실행되고 commit 하지 않으며, 예외를 삼킨다(본 API 를 실패시키지 않음).
제목·상세는 출처 행에서 다시 만든다 — 백필(milestone_backfill)도 같은 함수를 쓴다.
질병·부상 제목은 일반 문구만 쓰고 자유 입력(부위 등)은 넣지 않는다.
"""
from __future__ import annotations

import functools
import logging
import sqlite3
from datetime import date as _date

from src.services.milestone_events import find_event, record_event, ref, remove_event, today_local

log = logging.getLogger(__name__)

_KM_LABELS = ((4.5, 5.5, "5K"), (9.0, 11.0, "10K"), (20.0, 22.5, "하프마라톤"), (40.0, 43.0, "풀마라톤"))
_GOAL_FIELDS = (("name", "이름"), ("race_date", "대회일"), ("distance_km", "거리"),
                ("target_time_sec", "목표 기록"), ("target_pace_sec_km", "목표 페이스"))
EPISODE_TYPES = {"illness": ("illness_start", "질병 시작", "질병에서 회복"),
                 "injury": ("injury_start", "부상 발생", "부상에서 회복")}


def _safe(fn):
    @functools.wraps(fn)
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as exc:  # noqa: BLE001 — 마일스톤은 부가 기록
            log.warning("마일스톤 훅 %s 실패: %s", fn.__name__, exc)
            return None
    return wrap


def dist_label(km: float | None) -> str:
    """거리(km) → '5K'·'하프마라톤' 등, 그 밖은 '15.3km'."""
    if not km:
        return "거리 미상"
    for lo, hi, label in _KM_LABELS:
        if lo <= km <= hi:
            return label
    return f"{km:.1f}".rstrip("0").rstrip(".") + "km"


def fmt_time(sec: int | float | None) -> str | None:
    if not sec:
        return None
    s = int(sec)
    h, rem = divmod(s, 3600)
    m, x = divmod(rem, 60)
    return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"


def _join(*parts) -> str | None:
    s = " · ".join(p for p in parts if p)
    return s or None


# ── 대회 결과 ─────────────────────────────────────────────────────

@_safe
def on_race_result(conn: sqlite3.Connection, activity_id: int) -> bool | None:
    """race_finish — 날짜 = 대회(활동) 날짜. DNF 도 '도전 (DNF)' 로 남긴다."""
    r = conn.execute(
        "SELECT r.race_name, r.distance_m, r.official_time_sec, r.effort, DATE(a.start_time), a.name,"
        " COALESCE(a.elapsed_time_sec, a.duration_sec) FROM race_results r"
        " JOIN activity_summaries a ON a.id = r.activity_id WHERE r.activity_id=?", (activity_id,)).fetchone()
    if r is None or not r[4]:
        return False
    race_name, dist_m, official, effort, day, act_name, elapsed = r
    label = dist_label((dist_m or 0) / 1000.0)
    dnf = effort == "dnf"
    title = f"{label} 도전 (DNF)" if dnf else f"{label} 완주"
    detail = _join(race_name or act_name, None if dnf else fmt_time(official or elapsed))
    return record_event(conn, "race_finish", day, title, detail=detail, activity_id=activity_id,
                        source_ref=ref("race_result", activity_id))


@_safe
def on_race_result_removed(conn: sqlite3.Connection, activity_id: int) -> int | None:
    return remove_event(conn, ref("race_result", activity_id))


# ── 목표 ─────────────────────────────────────────────────────────

def _goal(conn, goal_id: int) -> dict | None:
    r = conn.execute("SELECT name, distance_km, race_date, target_time_sec, target_pace_sec_km, created_at"
                     " FROM goals WHERE id=?", (goal_id,)).fetchone()
    keys = ("name", "distance_km", "race_date", "target_time_sec", "target_pace_sec_km", "created_at")
    return dict(zip(keys, r)) if r else None


def _goal_value(g: dict, field: str) -> str | None:
    v = g.get(field)
    if v in (None, ""):
        return None
    if field == "distance_km":
        return dist_label(v)
    if field == "target_time_sec":
        return fmt_time(v)
    if field == "target_pace_sec_km":
        return f"{fmt_time(v)}/km"
    return str(v)


def goal_detail(g: dict) -> str | None:
    tt = fmt_time(g.get("target_time_sec"))
    return _join(dist_label(g.get("distance_km")), f"목표 {tt}" if tt else None,
                 f"대회일 {g['race_date']}" if g.get("race_date") else None)


@_safe
def on_goal_set(conn: sqlite3.Connection, goal_id: int, day: str | None = None) -> bool | None:
    """goal_set — 날짜 = 설정한 날(현지)."""
    g = _goal(conn, goal_id)
    if g is None:
        return False
    return record_event(conn, "goal_set", day or today_local(conn), f"목표 설정: {g['name']}",
                        detail=goal_detail(g), source_ref=ref("goal", goal_id))


@_safe
def on_goal_changed(conn: sqlite3.Connection, goal_id: int, fields) -> bool | None:
    """goal_changed — 같은 날 여러 번 바꾸면 1건으로 합친다. 같은 날 설정한 목표면 goal_set 을 갱신."""
    g = _goal(conn, goal_id)
    fields = {f for f in fields if f in dict(_GOAL_FIELDS)}
    if g is None or not fields:
        return False
    day = today_local(conn)
    key = ref("goal", goal_id)
    set_row = find_event(conn, "goal_set", key)
    if set_row and set_row["date"] == day:
        return record_event(conn, "goal_set", day, f"목표 설정: {g['name']}", detail=goal_detail(g), source_ref=key)
    prev = find_event(conn, "goal_changed", key)
    if prev and prev["date"] == day:
        fields |= {f for f, label in _GOAL_FIELDS if label in (prev["detail"] or "")}
    parts = [f"{label} {_goal_value(g, f) or '없음'}" for f, label in _GOAL_FIELDS if f in fields]
    return record_event(conn, "goal_changed", day, f"목표 수정: {g['name']}", detail="변경: " + " · ".join(parts),
                        source_ref=key, per_day=True)


@_safe
def on_goal_removed(conn: sqlite3.Connection, goal_id: int) -> int | None:
    """사용자가 목표를 취소·삭제 — 그 목표의 설정·수정 마일스톤 삭제(새 목표로 교체된 경우는 호출하지 않음)."""
    return remove_event(conn, ref("goal", goal_id))


# ── 대회 등록 ─────────────────────────────────────────────────────

@_safe
def on_race_registered(conn: sqlite3.Connection, race_id: int, day: str | None = None) -> bool | None:
    """race_registered — 날짜 = 등록한 날(대회일 아님). 기존 행이 있으면 그 날짜를 유지하고 내용만 갱신."""
    r = conn.execute("SELECT name, race_date, distance_km, status FROM race_calendar WHERE id=?",
                     (race_id,)).fetchone()
    if r is None or r[3] == "cancelled":
        return False
    key = ref("race", race_id)
    if day is None:
        prev = find_event(conn, "race_registered", key)
        day = prev["date"] if prev else today_local(conn)
    return record_event(conn, "race_registered", day, f"대회 등록: {r[0]}",
                        detail=_join(dist_label(r[2]), f"대회일 {r[1]}"), source_ref=key)


@_safe
def on_race_cancelled(conn: sqlite3.Connection, race_id: int) -> int | None:
    return remove_event(conn, ref("race", race_id))


# ── 재계획 ───────────────────────────────────────────────────────

@_safe
def on_replan(conn: sqlite3.Connection, replan_id: int, day: str | None = None) -> bool | None:
    """plan_replan — 날짜 = 적용한 날."""
    r = conn.execute("SELECT anchor_monday, start_km, status FROM plan_replans WHERE id=?", (replan_id,)).fetchone()
    if r is None or r[2] != "applied":
        return False
    detail = _join(f"{r[0]} 주부터", f"시작 주간 {r[1]:.0f}km" if r[1] else None)
    return record_event(conn, "plan_replan", day or today_local(conn), "훈련 계획 재조정", detail=detail,
                        source_ref=ref("replan", replan_id))


@_safe
def on_replan_undone(conn: sqlite3.Connection, replan_id: int) -> int | None:
    return remove_event(conn, ref("replan", replan_id))


# ── 질병·부상 에피소드 ───────────────────────────────────────────

@_safe
def on_episode(conn: sqlite3.Connection, episode_id: int) -> int | None:
    """확정된 질병·부상의 시작(start_date)·회복(end_date) 마일스톤을 현재 상태에 맞춘다. 기록 건수."""
    r = conn.execute("SELECT kind, start_date, end_date, status FROM context_episodes WHERE id=?",
                     (episode_id,)).fetchone()
    if r is None or r[0] not in EPISODE_TYPES:
        return 0
    kind, start, end, status = r
    key = ref("episode", episode_id)
    if status != "confirmed":
        remove_event(conn, key)
        return 0
    start_type, start_title, end_title = EPISODE_TYPES[kind]
    n = int(record_event(conn, start_type, start, start_title, source_ref=key))
    if end:
        days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
        n += int(record_event(conn, "recovery", end, end_title,
                              detail=f"{days}일 만" if days > 0 else "같은 날", source_ref=key))
    else:
        remove_event(conn, key, ("recovery",))
    return n


@_safe
def on_episode_removed(conn: sqlite3.Connection, episode_id: int) -> int | None:
    return remove_event(conn, ref("episode", episode_id))
