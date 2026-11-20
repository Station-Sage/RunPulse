"""훈련 방식 AI 추천 (PLAN-METHODS 3단계, ADR-060) — 장기 데이터를 AI 가 판단하고 규칙은 후보 가드·검증·폴백만 맡는다.

후보는 `candidates_for`(거리·러닝 요일 하드 가드)가 정하고, AI 는 그 안에서 순위·이유·주의를 낸다. 응답은 후보 id 만 허용하는
게이트를 통과해야 ai_outputs(kind='method_recommend', scope_key='goal:<id>')에 저장된다. 캐시·동의·큐 불가면 규칙 폴백
(`first_run3`(주 3일 이하)·없으면 `balanced`). 요청 스레드는 캐시만 읽고 생성은 백그라운드(쿨다운 30분)에서 한다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KIND = "method_recommend"
VERSION = "v1"
HISTORY_WEEKS = 26
COOLDOWN_SEC = 1800
_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "method_recommend.txt"
_MAX_TEXT = 120
_cooldown: dict[str, float] = {}
_lock = threading.Lock()


def _r5(x: float) -> int:
    return int(round(x / 5.0) * 5)


def _history(conn: sqlite3.Connection, today: date) -> dict:
    """최근 26주 러닝 요약(주별 km·횟수·최장거리) — 5km 단위로 반올림해 미세 변화가 캐시를 깨지 않게 한다."""
    start = (today - timedelta(weeks=HISTORY_WEEKS)).isoformat()
    rows = conn.execute(
        "SELECT substr(start_time,1,10), COALESCE(distance_m,0)/1000.0 FROM v_canonical_activities"
        " WHERE activity_type='running' AND start_time>=? AND start_time<?", (start, (today + timedelta(days=1)).isoformat())
    ).fetchall()
    weeks: dict[str, list[float]] = {}
    for d, km in rows:
        dd = date.fromisoformat(d)
        weeks.setdefault((dd - timedelta(days=dd.weekday())).isoformat(), []).append(float(km))
    this_monday = today - timedelta(days=today.weekday())
    series = []
    for i in range(HISTORY_WEEKS, 0, -1):
        ks = weeks.get((this_monday - timedelta(weeks=i)).isoformat(), [])
        series.append({"km": _r5(sum(ks)), "runs": len(ks), "long": _r5(max(ks)) if ks else 0})
    km = [s["km"] for s in series]
    recent = series[-8:]
    return {"weekly_km_26w": km, "weekly_runs_26w": [s["runs"] for s in series],
            "avg_km_8w": _r5(sum(s["km"] for s in recent) / len(recent)), "peak_km_26w": max(km),
            "longest_run_8w": max(s["long"] for s in recent),
            "active_weeks_26w": sum(1 for s in series if s["runs"]),
            "avg_runs_8w": round(sum(s["runs"] for s in recent) / len(recent), 1)}


def _vdot(conn: sqlite3.Connection, today: date) -> int | None:
    try:
        r = conn.execute("SELECT numeric_value FROM metric_store WHERE metric_name='VDOT_ADJ' AND scope_type='daily'"
                         " AND is_primary=1 AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
                         (today.isoformat(),)).fetchone()
    except sqlite3.Error:
        return None
    return int(round(float(r[0]))) if r and r[0] else None


def _races(conn: sqlite3.Connection) -> list[dict]:
    try:
        rows = conn.execute("SELECT distance_m, official_time_sec, effort FROM race_results"
                            " ORDER BY confirmed_at DESC LIMIT 5").fetchall()
    except sqlite3.Error:
        return []
    return [{"km": round(r[0] / 1000.0, 1), "min": int(round(r[1] / 60.0)) if r[1] else None, "effort": r[2]} for r in rows]


def build_input(conn: sqlite3.Connection, today: date | None = None) -> dict | None:
    """AI 입력(건강 정보 없음). 활성 목표가 없으면 None."""
    from src.services.plan_replan_service import methods_state
    from src.training.goals import get_active_goal
    from src.training.planner_config import load_prefs
    today = today or date.today()
    goal = get_active_goal(conn)
    if goal is None:
        return None
    st = methods_state(conn, today)
    mask = load_prefs(conn).get("workout_weekdays_mask")
    days_left = None
    if goal.get("race_date"):
        try:
            days_left = (date.fromisoformat(goal["race_date"]) - today).days // 7
        except ValueError:
            pass
    goal_part = {"distance": st["distance_label"], "weeks_to_race": days_left,
                 "target_min": int(round(goal["target_time_sec"] / 60.0)) if goal.get("target_time_sec") else None}
    inp = {"goal": {k: v for k, v in goal_part.items() if v is not None},
           "run_days_per_week": bin(mask).count("1") if mask else None,
           "history": _history(conn, today), "vdot": _vdot(conn, today), "races": _races(conn),
           "current": st["current"],
           "candidates": [{k: m[k] for k in ("id", "label", "summary", "pros", "cons", "target_runners")}
                          for m in st["methods"]]}
    return {k: v for k, v in inp.items() if v is not None}


def fallback(inp: dict) -> dict:
    """규칙 폴백 — 주 3일 이하면 first_run3(있을 때), 아니면 balanced. 후보 안에서만 고른다."""
    ids = [c["id"] for c in inp["candidates"]]
    days = inp.get("run_days_per_week")
    pick = "first_run3" if days is not None and days <= 3 and "first_run3" in ids else \
        ("balanced" if "balanced" in ids else ids[0])
    return {"recommended": pick, "ranking": [pick] + [i for i in ids if i != pick], "reasons": {}, "warnings": {}}


def src_hash(inp: dict) -> str:
    blob = json.dumps([VERSION, inp], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def validate(inp: dict, out: str | None) -> dict | None:
    """응답 → {recommended, ranking, reasons, warnings}. 후보 밖 id·스키마·길이·금지어·새 숫자 위반이면 None."""
    from src.services.ai_wording import _HEALTH_RE, numbers_ok
    m = re.search(r"\{.*\}", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else None
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    ids = [c["id"] for c in inp["candidates"]]
    rec, rank = d.get("recommended"), d.get("ranking")
    if rec not in ids or not isinstance(rank, list) or any(r not in ids for r in rank) or len(set(rank)) != len(rank):
        return None
    ranking = [rec] + [r for r in rank if r != rec]
    ranking += [i for i in ids if i not in ranking]
    src = json.dumps(inp, ensure_ascii=False)
    clean: dict[str, dict] = {}
    for field in ("reasons", "warnings"):
        v = d.get(field) or {}
        if not isinstance(v, dict):
            return None
        clean[field] = {}
        for k, t in v.items():
            if k not in ids or not isinstance(t, str):
                return None
            t = t.strip()
            if not t or len(t) > _MAX_TEXT or "#" in t or "*" in t or _HEALTH_RE.search(t) or not numbers_ok(src, t):
                return None
            clean[field][k] = t
    if rec not in clean["reasons"]:
        return None
    return {"recommended": rec, "ranking": ranking, **clean}


def _scope(goal_id: int) -> str:
    return f"goal:{goal_id}"


def _consent_ok(conn: sqlite3.Connection) -> bool:
    from src.services.ai_wording import _consent_ok as ok   # 단일 동의 기준(ADR-059)
    return ok(conn)


def get_cached(conn: sqlite3.Connection, goal_id: int, inp: dict) -> dict | None:
    """입력 해시가 맞는 AI 추천만(동의 없으면 숨김). 큐·LLM 을 부르지 않는다."""
    if not _consent_ok(conn):
        return None
    r = conn.execute("SELECT src_hash, body_json FROM ai_outputs WHERE kind=? AND scope_key=?",
                     (KIND, _scope(goal_id))).fetchone()
    if not r or r[0] != src_hash(inp):
        return None
    try:
        return json.loads(r[1])
    except ValueError:
        return None


def generate(conn: sqlite3.Connection, config: dict | None, today: date | None = None) -> dict | None:
    """캐시 → 동의·예산·큐 확인 → AI 호출 → 게이트 → 저장. 불가·실패는 None(규칙 폴백)."""
    from src.ai import llm_budget
    from src.ai import provider_claude_queue as pcq
    from src.training.goals import get_active_goal
    inp = build_input(conn, today)
    goal = get_active_goal(conn)
    if inp is None or goal is None:
        return None
    cached = get_cached(conn, goal["id"], inp)
    if cached:
        return cached
    if not _consent_ok(conn) or llm_budget.global_ratio() >= llm_budget.limits()["warm_stop_ratio"] \
            or not pcq.available(conn, config):
        return None
    prompt = _TEMPLATE.read_text(encoding="utf-8").replace("{{INPUT}}", json.dumps(inp, ensure_ascii=False))
    body = validate(inp, pcq.try_complete(conn, config, kind="plan_draft", prompt=prompt, deadline_sec=150))
    if body is None:
        return None
    conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) VALUES (?,?,?,?,?)",
                 (KIND, _scope(goal["id"]), src_hash(inp), json.dumps(body, ensure_ascii=False),
                  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    conn.commit()
    return body


def view(conn: sqlite3.Connection, today: date | None = None) -> dict | None:
    """화면용 {source:'ai'|'rule', recommended, ranking, reasons, warnings, current}. 활성 목표 없으면 None."""
    from src.training.goals import get_active_goal
    inp = build_input(conn, today)
    goal = get_active_goal(conn)
    if inp is None or goal is None:
        return None
    ai = get_cached(conn, goal["id"], inp)
    return {"source": "ai" if ai else "rule", **(ai or fallback(inp)), "current": inp["current"]}


def warm_in_background(db_path: str, config: dict | None, now: float | None = None) -> bool:
    """캐시가 없을 때만, 쿨다운(30분) 안에 한 번 백그라운드 생성을 예약한다. 예약했으면 True."""
    t = time.monotonic() if now is None else now
    with _lock:
        if t - _cooldown.get(db_path, -COOLDOWN_SEC) < COOLDOWN_SEC:
            return False
        _cooldown[db_path] = t

    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                generate(c, config)
        except Exception:  # noqa: BLE001
            log.warning("method recommend failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="method-recommend").start()
    return True
