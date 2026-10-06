"""계획 엔진 백테스트(읽기 전용) — v1/v2 엔진을 같은 시나리오로 돌려 plan_gates 로 판정한다.

DESIGN-U16 §2.2. 시나리오 두 종류: 역사(실DB 사본의 과거 하프 이상 대회) / 합성 격자(시작 부하×롱런×기간×일수×거리).
엔진은 `engine(scn, conn) -> (list[WeekPlan], aux)` 형태다. v1 어댑터만 여기 있고, v2 는 U16f~i 에서 같은 시그니처로 붙인다.
모든 작업은 메모리 DB 에서만 한다(실DB 무변경).
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from src.db_setup import create_tables

from . import plan_gates as G
from . import personalize as PZ
from . import plan_gates_long as GL
from .goals import add_goal
from .long_run_rules import LongCtx
from .planner import generate_weekly_plan, upsert_user_training_prefs
from .planner_rules import plan_start_monday
from .week_structure import _is_shakeout
from .planner_schedule import recent_avg_km, recent_load, recent_long_max

DAY_ORDER = (1, 3, 5, 6, 2, 0, 4)       # 러닝 일수 n 이면 앞의 n 개 요일만 가능
GRID = {"start_km": (25, 40, 55, 70, 90), "long_start": (10, 18, 26), "weeks": (8, 12, 16, 20),
        "days": (3, 4, 5, 6), "distance": ("half", "full", "10k")}
COLD_GRID = {"start_km": (0, 8, 12), "long_start": (0, 6)}      # 콜드스타트(DESIGN-U16-LONGRUN §5.2-7)
DIST_KM = {"10k": 10.0, "half": 21.0975, "full": 42.195}


@dataclass
class Scenario:
    kind: str                 # history | grid
    distance: str
    plan_weeks: int
    race_date: str
    days: int
    goal_sec: int | None = None
    start_km: float = 0.0
    long_start: float = 0.0
    race_sec: int | None = None    # 역사 시나리오의 실제 기록
    aux: dict = field(default_factory=dict)

    @property
    def start_monday(self) -> date:
        return plan_start_monday(self.race_date, self.plan_weeks)


def rest_mask(days: int) -> int:
    avail = set(DAY_ORDER[:days])
    return sum(1 << i for i in range(7) if i not in avail)


def _plan_from_rows(k: int, to_race: int, rows: list[dict]) -> G.WeekPlan:
    race = next((r["date"] for r in rows if r["workout_type"] == "race"), None)
    days = [G.Session("shakeout" if r["workout_type"] != "rest" and _is_shakeout(r, race) else r["workout_type"], 0.0 if r["workout_type"] == "race" else float(r.get("distance_km") or 0.0), mp_km=float(r.get("mp_km") or 0.0),
                      pace_sec=r.get("target_pace_min")) for r in rows]
    ctx = rows[0].get("_long_ctx")
    return G.WeekPlan(k, to_race, rows[0].get("_phase", ""), days, rows[0].get("_mp_sec"), LongCtx(**ctx) if ctx else None)


def engine_v1(scn: Scenario, conn: sqlite3.Connection, rules_version: int | None = None) -> tuple[list[G.WeekPlan], dict]:
    gid = add_goal(conn, f"bt-{scn.race_date}", DIST_KM[scn.distance], scn.race_date, scn.goal_sec,
                   rules_version=rules_version)
    conn.execute("UPDATE goals SET plan_weeks=?, distance_label=? WHERE id=?", (scn.plan_weeks, scn.distance, gid))
    upsert_user_training_prefs(conn, rest_weekdays_mask=rest_mask(scn.days))
    start = scn.start_monday
    weeks = []
    for k in range(scn.plan_weeks):
        rows = generate_weekly_plan(conn, gid, week_start=start + timedelta(weeks=k), as_of=start)
        weeks.append(_plan_from_rows(k, scn.plan_weeks - 1 - k, rows))
    conn.execute("DELETE FROM goals WHERE id=?", (gid,))
    return weeks, {}


def engine_v2(scn: Scenario, conn: sqlite3.Connection) -> tuple[list[G.WeekPlan], dict]:
    return engine_v1(scn, conn, rules_version=2)


def grid_scenarios() -> list[Scenario]:
    race0 = date(2030, 11, 24)       # 일요일. 합성 격자의 기준 대회일

    def grid(loads: dict) -> list[Scenario]:
        return [Scenario("grid", d, w, race0.isoformat(), n, start_km=s, long_start=ls)
                for d in GRID["distance"] for w in GRID["weeks"] for n in GRID["days"]
                for s in loads["start_km"] for ls in loads["long_start"]]
    return grid(GRID) + grid(COLD_GRID)


def seed_grid_history(conn: sqlite3.Connection, scn: Scenario) -> None:
    """계획 시작 직전 6주에 주 start_km(4회, 최장 long_eff)를 시드해 recent_load 가 (start_km, long_eff)가 되게 한다."""
    long_eff = min(scn.long_start, scn.start_km * 0.6)
    scn.aux["long_eff"] = long_eff
    if scn.start_km <= 0:       # 콜드: 기록 없음
        return
    n_rest = min(6, max(3, math.ceil((scn.start_km - long_eff) / long_eff))) if long_eff > 0 else 3
    long_eff = max(long_eff, scn.start_km / (n_rest + 1))
    scn.aux["long_eff"] = long_eff
    rest = (scn.start_km - long_eff) / n_rest
    n = 0
    for w in range(1, 7):
        mon = scn.start_monday - timedelta(weeks=w)
        for d, km in [(i, rest) for i in range(n_rest)] + [(6, long_eff)]:
            conn.execute(
                "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m,"
                " moving_time_sec, duration_sec) VALUES ('garmin', ?, 'r', 'running', ?, ?, ?, ?)",
                (f"g{n}", f"{(mon + timedelta(days=d)).isoformat()} 07:00:00", km * 1000, int(km * 330), int(km * 330)))
            n += 1


def history_inputs(conn: sqlite3.Connection, start: date) -> dict:
    """계획 시작 월요일까지의 실제 부하(그 이후 데이터는 쓰지 않는다)."""
    km4, long6 = recent_load(conn, start)
    rows = conn.execute(
        "SELECT DATE(start_time), SUM(distance_m)/1000.0 FROM v_canonical_activities WHERE activity_type IN "
        "('running','run','virtualrun','treadmill') AND DATE(start_time) >= ? AND DATE(start_time) < ? GROUP BY 1",
        ((start - timedelta(weeks=16)).isoformat(), start.isoformat())).fetchall()
    wk: dict[int, list] = {}
    for d, km in rows:
        wk.setdefault((start - date.fromisoformat(d)).days // 7, []).append(km)
    per_week_days = [len(wk.get(i, [])) for i in range(1, 9)]
    long12 = recent_long_max(conn, start, 12)       # 엔진과 같은 정의(러닝만)
    return {"start_km": km4, "start_long": long6, "days_median_8w": median(per_week_days) if per_week_days else 0,
            "long_max_12w": round(long12, 1), "avg16": recent_avg_km(conn, start, 16), "peak_week_16w": round(max((sum(v) for v in wk.values()), default=0.0), 1)}


def history_scenarios(conn: sqlite3.Connection, factors=(None, 0.97)) -> list[Scenario]:
    """하프 이상 대회(레이스 판정은 get_race_history 와 동일) × plan_weeks {9,12,16} × 목표(없음/기록×0.97). 데이터 시작보다 앞서는 시작일은 생략."""
    first = conn.execute("SELECT MIN(DATE(start_time)) FROM activity_summaries").fetchone()[0]
    out: list[Scenario] = []
    races = conn.execute(
        "SELECT DATE(a.start_time), a.distance_m, COALESCE(a.moving_time_sec, a.duration_sec) "
        "FROM v_canonical_activities a LEFT JOIN metric_store c ON c.scope_id=CAST(a.id AS TEXT)"
        " AND c.scope_type='activity' AND c.metric_name='workout_type_classified' "
        "WHERE a.activity_type='running' AND a.distance_m >= 20500 AND (c.text_value='race' OR a.name LIKE '%레이스%'"
        " OR a.name LIKE '%대회%' OR a.name LIKE '%Race%') ORDER BY 1").fetchall()
    for day, dist, sec in races:
        for w in (9, 12, 16):
            scn = Scenario("history", "full" if dist >= 41000 else "half", w, day, 0, race_sec=int(sec))
            if first and scn.start_monday < date.fromisoformat(first):
                continue
            for f in factors:
                s = Scenario(**{**scn.__dict__, "aux": {}})
                s.goal_sec = int(sec * f) if f else None
                s.aux["goal_assumed"] = bool(f)
                out.append(s)
    return out


def judge(scn: Scenario, v: list[G.WeekPlan], inputs: dict, run, v1: list[G.WeekPlan] | None = None,
          mp_now=None) -> dict[str, G.GateResult]:
    """한 엔진의 한 시나리오 결과를 게이트로 판정. run 은 같은 입력으로 다시 계산하는 콜러블(G8)."""
    start_km = inputs["start_km"]
    long12, long6 = inputs.get("long_max_12w", 0.0), inputs.get("start_long", 0.0)
    peak = max((w.km for w in v), default=0.0)
    res = {
        "G1": G.g1_rest_days(v, scn.days or int(inputs.get("days_median_8w") or 4)),
        "G2a": GL.g2a_long_cap(v, scn.distance, long6, long12),
        "G2b": GL.g2b_long_envelope(v),
        "G3": G.g3_min_session(v),
        "G4": G.g4_mp_sessions(v, scn.distance),
        "G5": G.g5_taper(v, scn.distance, peak, scn.plan_weeks),
        "G6": G.g6_ramp(v, start_km, PZ.comeback_ceiling(start_km, inputs.get("avg16", 0.0))),
        "G7": G.g7_mp_not_faster(v, mp_now or (lambda w: None)),
        "G8": G.g8_deterministic(run),
        "G9": GL.g9_long_floor(v, scn.distance, long6, long12),
        "F6": GL.f6_long_step(v, long12),
    }
    if scn.kind == "history":
        res["F1"] = G.f1_start_fit(v, start_km)
        res["F2ref"] = G.f2_peak_long(v, long12)      # 참고 출력(F6로 대체, DESIGN-U16-LONGRUN §4.4)
        res["F3"] = G.f3_peak_week(v, inputs.get("peak_week_16w", 0.0))
        if v1:
            res["F4"] = G.f4_total_ratio(v, v1)
        if scn.race_sec and not scn.goal_sec:
            res["F5"] = G.f5_race_pace(scn.race_sec / DIST_KM[scn.distance], v[-1].mp_sec)
    return res


def run_scenario(scn: Scenario, base_conn: sqlite3.Connection | None, engine=engine_v1, v1_engine=None) -> dict:
    """한 시나리오를 엔진으로 돌려 게이트 결과 dict 를 반환. 매 실행마다 독립 메모리 DB 를 쓴다."""
    def build() -> tuple[sqlite3.Connection, dict]:
        mem = sqlite3.connect(":memory:")
        mem.row_factory = sqlite3.Row
        create_tables(mem)
        if scn.kind == "history" and base_conn is not None:
            base_conn.backup(mem)
            inp = history_inputs(mem, scn.start_monday)
            scn.days = min(6, max(3, round(inp["days_median_8w"])))
            return mem, inp
        seed_grid_history(mem, scn)
        le = scn.aux["long_eff"]
        return mem, {"start_km": scn.start_km, "start_long": le, "long_max_12w": le, "peak_week_16w": scn.start_km}

    def once() -> tuple[list[G.WeekPlan], dict]:
        conn, inp = build()
        try:
            return engine(scn, conn)[0], inp
        finally:
            conn.close()

    weeks, inputs = once()
    v1w = v1_engine(scn, build()[0])[0] if v1_engine else None
    gates = judge(scn, weeks, inputs, lambda: once()[0], v1=v1w)
    return {"scenario": {k: v for k, v in scn.__dict__.items() if k != "aux"}, "inputs": inputs,
            "weeks": [{"i": w.index, "phase": w.phase, "km": round(w.km, 1), "long": round(w.long_km, 1),
                       "run_days": w.run_days} for w in weeks],
            "gates": {k: {"violations": r.violations, "worst": r.worst} for k, r in gates.items()},
            "pass": all(r.ok for k, r in gates.items() if k.startswith("G"))}


def summarize(results: list[dict]) -> dict:
    per: dict[str, dict] = {}
    for r in results:
        for g, v in r["gates"].items():
            d = per.setdefault(g, {"scenarios_failed": 0, "violations": 0, "worst": ""})
            if v["violations"]:
                d["scenarios_failed"] += 1
                d["violations"] += v["violations"]
                d["worst"] = d["worst"] or v["worst"]
    return {"total": len(results), "passed": sum(r["pass"] for r in results), "gates": per}
