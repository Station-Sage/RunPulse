"""Coach 컨텍스트 해석 보강 — Lap 요약·플랜 이행·HRV 분포 (V2-REPAIR C-2).

세 항목 모두 ctx 에 dict/list 로 넣고, 문장화는 `format_insight_lines` 가 한다.
데이터가 없으면 해당 키를 넣지 않는다(에러 raise 금지).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from .chat_context_utils import seconds_to_pace

_REST_KINDS = {"REST", "RECOVERY", "COOLDOWN", "WARMUP"}


def _lap_summary(conn: sqlite3.Connection, today: str) -> dict | None:
    since = (date.fromisoformat(today) - timedelta(days=14)).isoformat()
    act = conn.execute(
        "SELECT id, date(start_time) FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)>=? AND date(start_time)<=? "
        "ORDER BY start_time DESC LIMIT 5", (since, today),
    ).fetchall()
    for aid, day in act:
        rows = conn.execute(
            "SELECT source, lap_kind, duration_sec, distance_m, avg_hr, avg_pace_sec_km "
            "FROM activity_laps WHERE activity_id=? ORDER BY source, lap_index", (aid,),
        ).fetchall()
        if not rows:
            continue
        best = max({r[0] for r in rows}, key=lambda s: sum(1 for r in rows if r[0] == s))
        laps = [r for r in rows if r[0] == best]
        work = [r for r in laps if (r[1] or "").upper() not in _REST_KINDS and r[5]]
        if len(work) < 2:
            continue
        half = len(work) // 2
        first, second = work[:half], work[half:]

        def _avg(seq, idx):
            vals = [r[idx] for r in seq if r[idx]]
            return sum(vals) / len(vals) if vals else None

        p1, p2 = _avg(first, 5), _avg(second, 5)
        h1, h2 = _avg(first, 4), _avg(second, 4)
        fast = min(work, key=lambda r: r[5])
        slow = max(work, key=lambda r: r[5])
        return {
            "date": day, "laps": len(laps), "work_laps": len(work),
            "first_pace": seconds_to_pace(p1), "second_pace": seconds_to_pace(p2),
            "pace_delta_sec": round(p2 - p1, 1) if p1 and p2 else None,
            "first_hr": round(h1) if h1 else None, "second_hr": round(h2) if h2 else None,
            "fastest_pace": seconds_to_pace(fast[5]), "slowest_pace": seconds_to_pace(slow[5]),
        }
    return None


def _plan_adherence(conn: sqlite3.Connection, today: str) -> dict | None:
    since = (date.fromisoformat(today) - timedelta(days=28)).isoformat()
    rows = conn.execute(
        "SELECT workout_type, completed, skip_reason FROM planned_workouts "
        "WHERE date>=? AND date<? AND workout_type!='rest'", (since, today),
    ).fetchall()
    if not rows:
        return None
    done = sum(1 for r in rows if r[1])
    skipped = [r[2] for r in rows if not r[1] and r[2]]
    missed_q = sum(1 for r in rows if not r[1] and r[0] in {"tempo", "interval", "threshold", "long"})
    reasons: dict[str, int] = {}
    for s in skipped:
        reasons[s] = reasons.get(s, 0) + 1
    return {"planned": len(rows), "done": done, "pct": round(done / len(rows) * 100),
            "missed_quality": missed_q, "skip_reasons": reasons}


def _hrv_dist(conn: sqlite3.Connection, today: str) -> dict | None:
    since = (date.fromisoformat(today) - timedelta(days=28)).isoformat()
    vals = [r[0] for r in conn.execute(
        "SELECT hrv_last_night FROM daily_wellness WHERE date>=? AND date<=? "
        "AND hrv_last_night IS NOT NULL ORDER BY date", (since, today)).fetchall()]
    if len(vals) < 7:
        return None
    mean = sum(vals) / len(vals)
    sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    latest = vals[-1]
    return {"days": len(vals), "mean": round(mean, 1), "min": round(min(vals), 1),
            "max": round(max(vals), 1), "sd": round(sd, 1), "latest": round(latest, 1),
            "z": round((latest - mean) / sd, 1) if sd else 0.0}


def add_insight_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Lap 요약·플랜 이행·HRV 분포를 ctx 에 추가한다. 각 항목은 독립적으로 실패를 삼킨다."""
    try:
        from src.services import insight_service
        ev = insight_service.list_events(conn, "open", 3)
        if ev:
            ctx["insight_events"] = [{"severity": e["severity"], "as_of": e["as_of"], "text": e["text"]} for e in ev]
    except sqlite3.Error:
        pass
    for key, fn in (("lap_summary", _lap_summary), ("plan_adherence", _plan_adherence),
                    ("hrv_dist", _hrv_dist)):
        try:
            val = fn(conn, today)
        except sqlite3.Error:
            val = None
        if val:
            ctx[key] = val


def format_insight_lines(ctx: dict) -> list[str]:
    lines: list[str] = []
    ls = ctx.get("lap_summary")
    if ls:
        d = ls.get("pace_delta_sec")
        trend = "" if d is None else (f", 후반 {abs(d):.0f}초/km {'느려짐' if d > 0 else '빨라짐'}")
        lines.append(f"\n### 최근 Lap 요약 ({ls['date']}, 본운동 {ls['work_laps']}/{ls['laps']}랩)")
        lines.append(f"- 전반 {ls['first_pace']}/km HR {ls['first_hr']} → 후반 {ls['second_pace']}/km "
                     f"HR {ls['second_hr']}{trend}")
        lines.append(f"- 최고 랩 {ls['fastest_pace']}/km, 최저 랩 {ls['slowest_pace']}/km")
    pa = ctx.get("plan_adherence")
    if pa:
        lines.append("\n### 플랜 이행(최근 4주)")
        lines.append(f"- 계획 {pa['planned']}회 중 완료 {pa['done']}회({pa['pct']}%), "
                     f"핵심 세션 미수행 {pa['missed_quality']}회")
        if pa["skip_reasons"]:
            lines.append("- 건너뛴 이유: " + ", ".join(f"{k} {v}회" for k, v in pa["skip_reasons"].items()))
    hd = ctx.get("hrv_dist")
    if hd:
        lines.append("\n### HRV 분포(최근 28일)")
        lines.append(f"- 평균 {hd['mean']}ms(표준편차 {hd['sd']}), 범위 {hd['min']}~{hd['max']}, "
                     f"최근 {hd['latest']}ms(평균 대비 z={hd['z']})")
    ie = ctx.get("insight_events")
    if ie:
        lines.append("\n### 앱이 사용자에게 띄운 열린 알림(질문 없이도 참고)")
        lines.extend(f"- [{e['severity']}] {e['as_of']} {e['text']}" for e in ie)
    return lines
