"""Higdon 노비스 방식(하프·풀) — 속도훈련 없이 전부 이지(존2), 주 1회 점진 롱런. 스텝백 주는 엔진 회복주가 맡는다."""
from __future__ import annotations

from src.utils.daniels_table import get_training_paces

from .slots import build_week, set_row

LONG_CAP = {"half": 20.0, "full": 32.0}


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper" or not ctx.get("vdot"):
        return plan
    E = get_training_paces(ctx["vdot"])["E"]
    build_week(
        plan, [],
        lambda r, km: set_row(r, "long", km, "이지 롱런", (E + 10, E + 60), 2, "Higdon 노비스: 주 1회 롱런을 점진적으로 늘림"),
        lambda r, km: set_row(r, "easy", km, "이지 조깅", (E + 5, E + 45), 2, "Higdon 노비스: 속도훈련 없이 편안한 페이스"),
        long_weight=1.7, long_cap=LONG_CAP.get(ctx.get("dlabel"), 32.0), min_rows=3)
    return plan
