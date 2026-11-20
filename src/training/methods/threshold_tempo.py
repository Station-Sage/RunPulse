"""임계값 템포 방식(하프) — 지속 템포(T 페이스)와 크루즈 인터벌 중심, 롱런은 이지. 지속 시간은 단계별로 늘린다(20→40분)."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row

TEMPO_MIN = {"base": 20, "recovery_week": 20, "build": 30, "peak": 40}   # 20분 초과는 일반 규칙으로 보완


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    P = get_training_paces(ctx["vdot"])
    E, T = P["E"], P["T"]
    total = sum(r["distance_km"] for r in plan if r.get("workout_type") not in ("rest", "race"))
    tmin = TEMPO_MIN.get(ctx.get("phase"), 25)
    tempo_km = max(min(tmin * 60 / T, 0.2 * total), 2.5)
    rep = 1600
    sets = max(3, min(5, int(tempo_km * 1000 // rep)))
    rx = {"sets": sets, "rep_m": rep, "interval_pace": T, "rest_sec": 60}

    def q_tempo(row, km):
        set_row(row, "tempo", km, f"지속 템포 {tmin}분(T 페이스 {tempo_km:.1f}km)", (T - 3, T + 3), 4,
                "임계값 템포 방식: 20분 이상 지속 템포로 젖산 역치 확장")

    def q_cruise(row, km):
        set_row(row, "interval", km, f"크루즈 인터벌 {sets}×{rep}m(1분 휴식)", (T - 3, T + 3), 4,
                "임계값 템포 방식: 지속 템포 사이 보조 세션으로 T 페이스 누적", rx)

    quality = [(tempo_km + 3.5, q_tempo)]
    if ctx.get("phase") != "base":
        quality.append((sets * rep / 1000 + 3.5, q_cruise))
    build_week(
        plan, quality,
        lambda r, km: set_row(r, "long", km, "이지 롱런", (E + 10, E + 50), 2, "임계값 템포 방식: 롱런은 이지(주간 30% 이내)"),
        lambda r, km: set_row(r, "easy", km, "이지 조깅", (E - 10, E + 30), 2, "임계값 템포 방식: 품질 세션 외 이지"),
        long_weight=1.4, long_cap=min(max(total * 0.30, 8.0), 26.0), min_rows=4)
    return plan
