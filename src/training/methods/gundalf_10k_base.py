"""건달프 10K 베이스 방식(10K 전용) — 화 5K·토 10K 기준 달리기, 나머지는 이지. 지난주 결과로 다음 주 목표 페이스를 갱신한다."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.utils.daniels_table import get_race_predictions, get_training_paces

from .slots import run_rows, set_row, share_out

LOOKBACK_WEEKS = 8
FIVE_OK, FIVE_FAIL = -5, 3        # 5K: 성공 시 5초 단축, 실패 시 남은 거리(0.5km 단위)당 3초 가산
TEN_OK, TEN_FAIL = -3, 2          # 10K: 성공 시 3초 단축(설계값), 실패 시 남은 거리당 2초 가산
TEN_GAP = 10                      # 첫 주 10K 목표 = 5K 목표 + 10초
MIN_GAP = 5                       # 10K 가 5K 보다 5초 이상 느려야 함
LONG_CAP = 15.0


def _d(v) -> date:
    return date.fromisoformat(v[:10]) if isinstance(v, str) else v


def _week_run(conn, mon: date, weekday: int):
    day = (mon + timedelta(days=weekday)).isoformat()
    try:
        return conn.execute(
            "SELECT distance_m, avg_pace_sec_km FROM activity_summaries WHERE activity_type='running'"
            " AND substr(start_time,1,10)=? ORDER BY distance_m DESC LIMIT 1", (day,)).fetchone()
    except sqlite3.Error:
        return None


def _update(target: int, ref_km: float, row, ok: int, fail: int) -> int:
    if not row or not row[0] or not row[1]:
        return target
    dist_km, pace = row[0] / 1000.0, row[1]
    if dist_km >= ref_km - 0.1:
        return target + ok if pace <= target else target
    remaining = round((ref_km - dist_km) * 2) / 2
    return target + int(round(remaining * fail))


def reference_targets(conn, vdot: float, week_start) -> tuple[int, int]:
    """(5K 목표, 10K 목표) sec/km — 최근 LOOKBACK_WEEKS 주의 화·토 결과를 순서대로 반영한 값."""
    t5 = round(get_race_predictions(vdot)["5k"] / 5.0)
    t10 = t5 + TEN_GAP
    mon = _d(week_start)
    if conn is not None:
        for i in range(LOOKBACK_WEEKS, 0, -1):
            w = mon - timedelta(weeks=i)
            t5 = _update(t5, 5.0, _week_run(conn, w, 1), FIVE_OK, FIVE_FAIL)
            t10 = _update(t10, 10.0, _week_run(conn, w, 5), TEN_OK, TEN_FAIL)
            t10 = max(t10, t5 + MIN_GAP)
    return t5, max(t10, t5 + MIN_GAP)


def _mmss(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    rows = run_rows(plan)
    if len(rows) < 3:
        return plan
    total = sum(r["distance_km"] for r in rows)
    wd = {_d(r["date"]).weekday(): r for r in rows}
    days = sorted(wd)
    long_wd = 6 if 6 in wd else days[-1]
    mid = [d for d in days if d != long_wd]
    d5 = 1 if 1 in mid else mid[0]
    d10 = 5 if 5 in mid and 5 != d5 else next((d for d in reversed(mid) if d != d5), None)
    if d10 is None:
        return plan
    t5, t10 = reference_targets(ctx.get("conn"), ctx["vdot"], ctx["week_start"])
    E = get_training_paces(ctx["vdot"])["E"]
    set_row(wd[d5], "tempo", 5.0, f"5K 기준 달리기(목표 {_mmss(t5)}/km)", (t5 - 2, t5 + 2), 4,
            "건달프 10K: 화요일 5K 기준 달리기. 성공 시 다음 주 5초 단축, 미달 시 남은 거리×3초 가산")
    set_row(wd[d10], "tempo", 10.0, f"10K 기준 달리기(목표 {_mmss(t10)}/km)", (t10 - 2, t10 + 2), 4,
            "건달프 10K: 토요일 10K 기준 달리기. 성공 시 3초 단축, 미달 시 남은 거리×2초 가산(5K 와 별개 추적)")
    others = [d for d in days if d not in (d5, d10)]
    km = share_out(max(total - 15.0, 3.0 * len(others)), {d: (1.6 if d == long_wd else 1.0) for d in others},
                   {long_wd: LONG_CAP}) if others else {}
    for d in others:
        if d == long_wd:
            set_row(wd[d], "long", km[d], "이지 롱런", (E + 10, E + 50), 2, "건달프 10K: 주 1회 15km 이하 이지 롱런")
        else:
            set_row(wd[d], "easy", km[d], "이지 조깅", (E - 10, E + 30), 2, "건달프 10K: 기준 달리기 외 날은 가볍게")
    return plan
