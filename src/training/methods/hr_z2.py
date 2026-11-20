"""심박 Z2 중심 방식(풀) — 거의 모든 러닝을 존2 이지로, 빌드·피크에만 짧은 T 템포 1회. 롱런도 존2."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    P = get_training_paces(ctx["vdot"])
    E, T = P["E"], P["T"]
    total = sum(r["distance_km"] for r in plan if r.get("workout_type") not in ("rest", "race"))
    quality = []
    if ctx.get("phase") in ("build", "peak"):
        tkm = min(max(0.08 * total, 2.0), 6.0)

        def q_tempo(row, km):
            set_row(row, "tempo", km, f"짧은 템포(T 페이스 {tkm:.1f}km)", (T - 3, T + 3), 4,
                    "Z2 중심 방식: 주 1회 짧은 템포만 허용(주간 10% 이내)")
        quality.append((tkm + 4.0, q_tempo))
    build_week(
        plan, quality,
        lambda r, km: set_row(r, "long", km, "존2 롱런", (E + 10, E + 50), 2, "Z2 중심 방식: 롱런도 존2 유지"),
        lambda r, km: set_row(r, "easy", km, "존2 이지 조깅", (E + 10, E + 40), 2, "Z2 중심 방식: 대부분 존2 유산소"),
        long_weight=1.6, long_cap=32.0, min_rows=3)
    return plan
