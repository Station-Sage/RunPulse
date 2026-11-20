"""건달프 서브3 방식(풀 전용) — 팀 DBS(A) 토요일 표와 같은 주간 골격: 화 400m 인터벌·수 AR·토 지속주/장거리 교대·금 휴식."""
from __future__ import annotations

from datetime import date

from src.utils.daniels_table import get_training_paces

from .slots import iso_parity, run_rows, set_row, share_out, week_total

# weekday(0=월) → 비중. 금(4)은 사용자가 러닝 요일로 골랐을 때만 짧은 회복주로 쓴다.
WEIGHTS = {0: 0.10, 1: 0.14, 2: 0.22, 3: 0.10, 4: 0.06, 6: 0.18}
CAPS = {2: 20.0, 6: 20.0}


def adjust(plan: list[dict], ctx: dict) -> list[dict]:
    if ctx.get("phase") == "taper":          # 엔진 테이퍼(3주)가 건달프 테이퍼와 같다
        return plan
    rows = run_rows(plan)
    total = week_total(plan)
    paces = get_training_paces(ctx.get("vdot") or 0)
    if not rows or not total or not paces:
        return plan
    M, E = paces["M"], paces["E"]
    by_wd = {(date.fromisoformat(r["date"]) if isinstance(r["date"], str) else r["date"]).weekday(): r for r in rows}
    sat = by_wd.get(5)
    sat_km = 0.0
    if sat:
        half = iso_parity(ctx["week_start"]) == 0
        sat_km = min(21.0 if half else 35.0, total * 0.5)
    rest_w = {k: v for k, v in WEIGHTS.items() if k in by_wd}
    km = share_out(total - sat_km, rest_w, CAPS) if rest_w else {}
    if sat:
        label = "하프 지속주(마지막 HMP)" if half else "장거리(마지막 4km HMP)"
        set_row(sat, "long", sat_km, label, (E + 10, E + 50), 2,
                "건달프: 토요일은 하프 거리 지속주와 장거리 교대. 후반 하프 페이스로 마무리")
    for wd, r in by_wd.items():
        if wd == 5 or wd not in km:
            continue
        d = km[wd]
        if wd == 1:
            rx = {"rep_m": 400, "sets": 6, "rest_sec": 90, "interval_pace": M - 22, "recovery_pace": E + 40}
            set_row(r, "interval", d, "400m 인터벌(마라톤 페이스보다 약간 빠르게)", (M - 25, M - 20), 4,
                    "건달프: 400m 반복을 마라톤 페이스보다 살짝 빠르게, 총 1~3km", rx)
        elif wd == 2:
            set_row(r, "easy", d, "AR(점진 빌드업 후 MP+30초)", (M + 25, M + 35), 3,
                    "건달프: 0~5km 워밍업, 5~10km 빌드업 후 마라톤 페이스+30초 유지(존3)")
        elif wd == 4:
            set_row(r, "recovery", d, "회복 조깅", (E + 50, E + 90), 1, "건달프: 금요일은 원래 완전 휴식 — 러닝 요일이면 짧게만")
        elif wd == 6:
            set_row(r, "easy", d, "이지런", (E - 10, E + 30), 2, "건달프: 일요일 이지 15~20km")
        else:
            set_row(r, "recovery", d, "회복 조깅", (E + 50, E + 90), 1, "건달프: 월·목은 가벼운 조깅")
    return plan
