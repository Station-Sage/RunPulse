"""FIRST 주3 방식(10K·하프·풀) — 러닝은 주 3회(트랙 반복·템포·롱런)만, 나머지 요일은 교차훈련 휴식으로 바꾼다."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import parse_day, pick_days, run_rows, set_row, share_out

LONG_CAP = {"10k": 16.0, "half": 24.0, "full": 32.0}
TRACK_CAP, TEMPO_CAP = 12.0, 13.0  # 롱런은 주간의 50% 이하여야 하므로 나머지 두 날 상한 합을 넘지 않게
_DN = ["월", "화", "수", "목", "금", "토", "일"]


def _cross(row: dict) -> None:
    row.update(workout_type="rest", distance_km=0.0, target_pace_min=None, target_pace_max=None, target_hr_zone=None,
               interval_prescription=None, structure=None, rationale="FIRST 주3: 러닝 3회 외 날은 교차훈련(자전거·수영)·휴식",
               description=f"{_DN[parse_day(row['date']).weekday()]}요일 휴식")


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if not ctx.get("vdot"):
        return plan
    rows = run_rows(plan)
    if len(rows) < 3:
        return plan
    P = get_training_paces(ctx["vdot"])
    E, M, T, I = P["E"], P["M"], P["T"], P["I"]
    wd = {parse_day(r["date"]).weekday(): r for r in rows}
    days = sorted(wd)
    long_wd = 6 if 6 in wd else days[-1]
    mids = pick_days(days, long_wd, 2)
    d_track, d_tempo = mids[0], mids[-1]
    keep = {long_wd, d_track, d_tempo}
    total = sum(r["distance_km"] for r in rows)
    km = share_out(total, {long_wd: 0.42, d_track: 0.28, d_tempo: 0.30},
                   {long_wd: min(LONG_CAP.get(ctx.get("dlabel"), 32.0), TRACK_CAP + TEMPO_CAP), d_track: TRACK_CAP, d_tempo: TEMPO_CAP})
    sets = 6
    rx = {"sets": sets, "rep_m": 800, "interval_pace": I, "rest_sec": 150}
    set_row(wd[d_track], "interval", km[d_track], f"트랙 반복 {sets}×800m(400m 조깅)", (I - 3, I + 3), 5,
            "FIRST 주3: 5K 페이스 이상 트랙 반복", rx)
    set_row(wd[d_tempo], "tempo", km[d_tempo], "템포런(5K 페이스보다 마일당 약 25~30초 느리게)", (T - 3, T + 3), 4,
            "FIRST 주3: 중강도 템포로 젖산 역치 향상")
    set_row(wd[long_wd], "long", km[long_wd], "롱런(마라톤 페이스보다 느리게)", (M + 55, M + 75), 3,
            "FIRST 주3: 질 높은 롱런(마라톤 페이스보다 마일당 약 90초~2분 느리게)")
    for d, r in wd.items():
        if d not in keep:
            _cross(r)
    return plan
