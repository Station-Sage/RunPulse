"""Hansons 방식(풀) — SOS 3세션(스피드/스트렝스 인터벌·마라톤 페이스 템포·롱런)과 나머지 이지 6일. 롱런 상한 26km."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row

LONG_CAP = 26.0       # 16마일
STRENGTH_GAP = 6      # 스트렝스 인터벌: 마라톤 페이스보다 마일당 약 10초(≈6초/km) 빠르게


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    P = get_training_paces(ctx["vdot"])
    E, M, I = P["E"], P["M"], P["I"]
    total = sum(r["distance_km"] for r in plan if r.get("workout_type") not in ("rest", "race"))
    speed = ctx.get("phase") in ("base", "recovery_week")
    if speed:
        sets, rep, pace, rest, name = 8, 400, I, 120, "스피드"
    else:
        sets = 6 if ctx.get("phase") == "build" else 4
        rep, pace, rest, name = 1600, M - STRENGTH_GAP, 150, "스트렝스"
    rx = {"sets": sets, "rep_m": rep, "interval_pace": pace, "rest_sec": rest}
    tempo_km = min(max(0.2 * total, 6.0), 16.0)

    def q_int(row, km):
        set_row(row, "interval", km, f"{name} 인터벌 {sets}×{rep}m", (pace - 3, pace + 3), 5 if speed else 4,
                f"Hansons SOS: {name} 세션(스트렝스는 마라톤 페이스보다 마일당 약 10초 빠르게)", rx)

    def q_mp(row, km):
        set_row(row, "tempo", km, f"마라톤 페이스 템포 {tempo_km:.0f}km", (M - 3, M + 3), 4,
                "Hansons SOS: 마라톤 페이스 템포로 레이스 페이스 적응")
    build_week(
        plan, [(sets * rep / 1000 + 4.0, q_int), (tempo_km + 3.0, q_mp)],
        lambda r, km: set_row(r, "long", km, "롱런(누적 피로 상태)", (E + 5, E + 45), 2,
                              "Hansons SOS: 롱런은 26km 이내, 피로 누적 상태에서 수행"),
        lambda r, km: set_row(r, "easy", km, "이지 조깅", (E - 5, E + 35), 2, "Hansons: SOS 외 날은 이지로 누적 거리 확보"),
        long_weight=1.5, long_cap=LONG_CAP, min_rows=5)
    return plan
