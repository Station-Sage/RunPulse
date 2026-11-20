"""마라톤 특이성 방식(풀, Pfitzinger 계열) — LT 데이, 중장거리(미디엄롱), 마라톤 페이스 구간이 든 롱런, 롱런 다음날 회복."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row

MP_KM = {"build": 8, "peak": 12}


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    P = get_training_paces(ctx["vdot"])
    E, M, T = P["E"], P["M"], P["T"]
    total = sum(r["distance_km"] for r in plan if r.get("workout_type") not in ("rest", "race"))
    lt_km = {"base": 4.0, "recovery_week": 4.0}.get(ctx.get("phase"), 8.0)
    lt_km = min(lt_km, max(0.15 * total, 3.0))
    mp_km = MP_KM.get(ctx.get("phase"), 0)

    def q_lt(row, km):
        set_row(row, "tempo", km, f"LT 데이(T 페이스 {lt_km:.0f}km 포함)", (T - 3, T + 3), 4,
                "마라톤 특이 방식: 주 1회 젖산 역치 세션")

    def q_ml(row, km):
        set_row(row, "easy", km, "중장거리(미디엄롱)", (E, E + 40), 2, "마라톤 특이 방식: 주중 18~24km 유산소 지구력")

    def long_fn(row, km):
        if mp_km and km >= mp_km + 8:
            set_row(row, "long", km, f"롱런(후반 {mp_km}km 마라톤 페이스)", (M, E + 50), 3,
                    "마라톤 특이 방식: 롱런 중 마라톤 페이스 구간으로 레이스 페이스 적응")
        else:
            set_row(row, "long", km, "이지 롱런", (E + 10, E + 50), 2, "마라톤 특이 방식: 장거리 지구력")
    ml_km = min(max(0.22 * total, 12.0), 24.0)
    quality = [(lt_km + 4.0, q_lt)]
    if total >= 55:
        quality.append((ml_km, q_ml))
    build_week(
        plan, quality, long_fn,
        lambda r, km: set_row(r, "easy", km, "이지 조깅", (E - 10, E + 35), 2, "마라톤 특이 방식: 회복·이지"),
        long_weight=1.8, long_cap=35.0, min_rows=4, rest_after_long=True)
    return plan
