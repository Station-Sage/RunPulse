"""훈련 반응(순수) — 품질 세트(구간 R/I/T/M)의 주간 작업 시간, 롱런 속 마라톤 페이스 거리, 세트 VDOT 추세(P7-PRED-41).

기기 없이(GPS·시간) 계산한다. PB·대회 기록에 의존하지 않는다. 세트 판정은 prediction.signals.set_obs 와 같다.
"""
from __future__ import annotations

from datetime import date

from src.metrics import segments as seg
from src.metrics.prediction.signals_r4 import EXCLUDE_TYPES, easy_speeds, set_obs

MP_TOL = 0.04          # 마라톤 페이스 ±4%
LONG_M = 16000.0
ZONES = ("R", "I", "T", "M")


def _days(d_from: str, d_to: str) -> int:
    return (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days


def weekly_zone_minutes(runs: list[dict], as_of: str, weeks: int = 16) -> dict[str, list]:
    """{"R": [이번 주(as_of 이전 7일), 1주 전, …], "I", "T", "M", "sessions"} 품질 세트 작업 시간(분)·세션 수."""
    out: dict[str, list] = {z: [0.0] * weeks for z in ZONES}
    out["sessions"] = [0] * weeks
    ve = easy_speeds(runs)
    for r in runs:
        d = _days(r["date"], as_of)
        if d <= 0 or d > weeks * 7:
            continue
        o = set_obs(r, ve[r["id"]], None)
        if not o:
            continue
        w = (d - 1) // 7
        laps = r.get("laps") or []
        ws = seg.work_set(seg.build_bouts(laps, seg.label_blocks(laps, ve[r["id"]])))
        out[o["kind"]][w] += ws["work_s"] / 60.0
        out["sessions"][w] += 1
    return {k: [round(x, 1) for x in v] for k, v in out.items()}


def long_mp_km(runs: list[dict], as_of: str, v_mp: float, days: int = 56) -> float:
    """최근 56일 롱런(≥16km, 비대회)에서 마라톤 페이스 ±4% 랩 거리 합(km)."""
    km = 0.0
    for r in runs:
        d = _days(r["date"], as_of)
        if 0 < d <= days and r["distance_m"] >= LONG_M and not r["is_race"] and r["activity_type"] not in EXCLUDE_TYPES:
            km += sum(b["dist_m"] for b in (r.get("laps") or []) if abs(b["speed_ms"] / v_mp - 1) <= MP_TOL) / 1000.0
    return round(km, 1)


def set_trend(runs: list[dict], as_of: str, days: int = 56) -> dict:
    """최근 56일 세트 VDOT(휴식 보정 Daniels 환산)의 선형 추세(VDOT/4주). 세트 4개 미만이면 slope None."""
    ve = easy_speeds(runs)
    pts = []
    for r in runs:
        d = _days(r["date"], as_of)
        if 0 < d <= days:
            o = set_obs(r, ve[r["id"]], None)
            if o:
                pts.append((-d, o["y"]))
    if len(pts) < 4:
        return {"n": len(pts), "slope_4w": None}
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sxx if sxx else 0.0
    return {"n": len(pts), "slope_4w": round(slope * 28, 2), "mean": round(my, 2)}


def summarize(weekly: dict[str, list]) -> dict:
    """최근 8주·이전 8주 주평균 품질 분(R+I+T+M)과 주평균 품질 세션 수."""
    tot = [sum(weekly[z][i] for z in ZONES) for i in range(len(weekly["T"]))]
    a, b = tot[:8], tot[8:16]
    return {"quality_min_avg_8w": round(sum(a) / 8, 1),
            "quality_min_avg_prev_8w": round(sum(b) / 8, 1) if len(b) == 8 else None,
            "quality_sessions_avg_8w": round(sum(weekly["sessions"][:8]) / 8, 2)}
