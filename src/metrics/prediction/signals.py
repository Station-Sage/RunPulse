"""예측 v2 신호 계산(순수) — 활동 목록(get_runs 형식) → 앵커 A·작업블록 W·HR@LTHR H·Tanda 입력·5K 다중 신호.

runs 원소: get_runs(with_laps=True) dict + "ambient_c"(외기 기온, 없으면 None) + "effort"(race_results, 없으면 None).
"""
from __future__ import annotations

from datetime import date
from statistics import mean

from src.metrics.prediction.effort import auto_effort
from src.metrics.prediction.core import anchor, best_block, time_for_vdot, vdot, vdot_at_15c

EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running", "trail_running")
W_DAYS = 42
H_DAYS = 60
H_MIN_POINTS = 25


def _weeks(d_from: str, d_to: str) -> float:
    return (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days / 7.0


def allout_races(runs: list[dict], as_of: str, hrmax: float | None, heat: float, cold: float,
                 lthr: float | None = None) -> list[dict]:
    """전력 대회(365일 이내) → anchor() 입력. 확인된 effort 가 allout 이 아니면 제외.
    미확인이면 거리·지속시간별 자동 추정(`effort.classify`)이 allout 인 것만 — uncertain·submax 는 제외(r4 보강).
    HR 이 없으면(T0) 대회로 판정된 활동을 전력으로 간주한다(가정 — 확인 입력 권장)."""
    out = []
    for r in runs:
        n = r.get("nominal_m")
        if not r["is_race"] or not n or r["date"] >= as_of or _weeks(r["date"], as_of) > 52:
            continue
        eff = r.get("effort")
        if eff is not None and eff != "allout":
            continue
        t = r.get("official_time_s") or r["perf_time_s"]
        if eff is None and auto_effort(r, runs, hrmax) != "allout":
            continue
        out.append({"activity_id": r["id"], "date": r["date"], "nominal_m": n, "time_s": t,
                    "weeks": _weeks(r["date"], as_of), "vdot15": vdot_at_15c(n, t, r.get("ambient_c"), heat, cold)})
    return out


def work_signal(runs: list[dict], as_of: str, lthr: float | None, v_t: float | None) -> tuple[float | None, int | None]:
    """최근 42일 연속 랩 블록 최고 GAP-VDOT(기온 정규화 안 함 — 백테스트 결과). 반환 (W, activity_id)."""
    best, best_id = None, None
    for r in runs:
        if r["date"] >= as_of or _weeks(r["date"], as_of) * 7 > W_DAYS or r["activity_type"] in EXCLUDE_TYPES:
            continue
        w = best_block(r.get("laps") or [], lthr if lthr else None, None if lthr else v_t, r["is_race"])
        if w is not None and (best is None or w > best):
            best, best_id = w, r["id"]
    return best, best_id


def steady_points(r: dict) -> list[tuple[float, float, float]]:
    """정상 주행 1km 랩(3번째 랩부터, HR 110~190, 페이스 3:50~7:30/km) → (hr, speed, ambient)."""
    if r["is_race"] or r["activity_type"] in EXCLUDE_TYPES or r.get("ambient_c") is None:
        return []
    out = []
    for b in (r.get("laps") or [])[2:]:
        if 900 <= b["dist_m"] <= 1100 and b["hr"] and 110 <= b["hr"] <= 190 and 1000 / 450 <= b["speed_ms"] <= 1000 / 230:
            out.append((b["hr"], b["speed_ms"], r["ambient_c"]))
    return out


def hr_signal(runs: list[dict], as_of: str, lthr: float | None, heat: float, cold: float) -> float | None:
    """최근 60일 HR–속도(15℃ 정규화) 선형 적합 → LTHR에서의 속도를 60분 레이스 속도로 보고 VDOT."""
    from src.metrics.prediction.core import temp_factor
    if not lthr:
        return None
    pts = [p for r in runs if r["date"] < as_of and _weeks(r["date"], as_of) * 7 <= H_DAYS for p in steady_points(r)]
    if len(pts) < H_MIN_POINTS:
        return None
    x = [h for h, _, _ in pts]
    y = [v / temp_factor(t, heat, cold) for _, v, t in pts]
    mx, my = mean(x), mean(y)
    sxx = sum((q - mx) ** 2 for q in x)
    if not sxx:
        return None
    b = sum((q - mx) * (w - my) for q, w in zip(x, y)) / sxx
    v = my + b * (lthr - mx)
    return vdot(v * 3600, 3600) if v > 0 else None


def tanda_inputs(runs: list[dict], as_of: str) -> tuple[float, float, int]:
    """(최근 8주 주평균 km, 같은 기간 평균 훈련 페이스 s/km(이동시간 기준), 12주 내 28km+ 롱런 수)."""
    r8 = [r for r in runs if r["date"] < as_of and _weeks(r["date"], as_of) <= 8]
    km = sum(r["distance_m"] for r in r8) / 1000.0
    mv = sum(r["moving_s"] for r in r8)
    long28 = sum(1 for r in runs if r["date"] < as_of and _weeks(r["date"], as_of) <= 12 and r["distance_m"] >= 28000)
    return km / 8.0, (mv / km if km else 0.0), long28


def spread_pct(values: list[float], dist_m: float) -> float:
    """신호(VDOT) 목록을 해당 거리 시간으로 바꾼 뒤 (최대-최소)/중앙 %."""
    ts = sorted(time_for_vdot(v, dist_m) for v in values if v)
    if len(ts) < 2:
        return 0.0
    return (ts[-1] - ts[0]) / ts[len(ts) // 2] * 100.0
