"""임계값+VO2max 방식(10K) — Daniels 식 T 크루즈 인터벌과 I 페이스 반복, 롱런은 이지. T 합계 ≤주간 10%, I 합계 ≤min(8%, 10km)."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row

LONG_SHARE_CAP = 0.30


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    P = get_training_paces(ctx["vdot"])
    E, T, I = P["E"], P["T"], P["I"]
    total = sum(r["distance_km"] for r in plan if r.get("workout_type") not in ("rest", "race"))
    rep_t = round(300 / T * 1000 / 100) * 100                       # T 5분 반복(m)
    sets_t = max(2, min(4, int(0.10 * total * 1000 // max(rep_t, 1))))
    rx_t = {"sets": sets_t, "rep_m": rep_t, "interval_pace": T, "rest_sec": 60}
    sets_i = max(3, min(5, int(min(0.08 * total, 10.0))))
    rx_i = {"sets": sets_i, "rep_m": 1000, "interval_pace": I, "rest_sec": 180}

    def q_t(row, km):
        set_row(row, "interval", km, f"T 크루즈 {sets_t}×{rep_t}m(1분 휴식)", (T - 3, T + 3), 4,
                "임계값 방식: T 페이스 5분 반복, 휴식 1분. T 합계는 주간 10% 이내", rx_t)

    def q_i(row, km):
        set_row(row, "interval", km, f"VO2max 인터벌 {sets_i}×1000m(3분 조깅)", (I - 3, I + 3), 5,
                "임계값 방식: I 페이스 3~5분 반복. 합계는 주간 8%·10km 이내", rx_i)

    quality = [(sets_t * rep_t / 1000 + 3.5, q_t)]
    if ctx.get("phase") != "base":
        quality.append((sets_i + 4.0, q_i))
    build_week(
        plan, quality,
        lambda r, km: set_row(r, "long", km, "이지 롱런", (E + 10, E + 50), 2, "임계값 방식: 롱런은 이지(주간 30% 이내)"),
        lambda r, km: set_row(r, "easy", km, "이지 조깅", (E - 10, E + 30), 2, "임계값 방식: 품질 세션 외 이지"),
        long_weight=1.4, long_cap=max(total * LONG_SHARE_CAP, 8.0), min_rows=4)
    return plan
