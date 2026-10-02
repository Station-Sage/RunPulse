"""활동 상세 S1 — km 스플릿·요약 시계열(series) 서버 계산.

프론트 splits.ts 계산을 백엔드로 이관(UX 리뷰 20 F-DATA-02): 스플릿 페이스·평균 심박은 **이동 시간**
기준(정지 제외), 정지 시간은 stop_sec로 따로 내려준다. 읽기 전용·순수 함수(DB 접근 없음).
"""
from __future__ import annotations

import math
from bisect import bisect_left

from src.metrics.stream_utils import GAP_DIST_M, GAP_SEC, STOP_SPEED_MS, sample_times

SERIES_MAX_POINTS = 600
PARTIAL_MIN_M = 200
_SLOWEST_PACE = 900  # 15:00/km 초과는 정지로 보고 페이스 표시 안 함
_ELEV_NOISE_M = 1.0


def cumulative_distance(streams: list[dict], total_sec: float, total_dist_m: float) -> list[float]:
    """샘플별 누적 거리(m). distance_m가 전부 있으면 그대로, 없으면 속도 적분 후 총 거리에 맞춰 스케일."""
    n = len(streams)
    if n == 0:
        return []
    dists = [s.get("distance_m") for s in streams]
    if all(d is not None for d in dists) and dists[-1] and dists[-1] > 0:
        return [float(d) for d in dists]
    t = sample_times(streams, total_sec)
    out, last_speed = [0.0], 0.0
    for i in range(1, n):
        sp = streams[i].get("speed_ms")
        if sp is not None and math.isfinite(sp):
            last_speed = max(0.0, sp)
        out.append(out[-1] + last_speed * max(0.0, t[i] - t[i - 1]))
    if out[-1] > 0 and total_dist_m > 0:
        k = total_dist_m / out[-1]
        out = [v * k for v in out]
    return out


def stopped_flags(streams: list[dict], t: list[float], d: list[float]) -> list[bool]:
    """샘플 i(≥1)가 직전 샘플 이후 정지 상태였는지 (stream_utils.moving_segments와 같은 기준)."""
    flags = [False]
    for i in range(1, len(streams)):
        dt, dd = t[i] - t[i - 1], d[i] - d[i - 1]
        if dt <= 0:
            flags.append(False)
            continue
        sp = streams[i].get("speed_ms")
        sp = dd / dt if sp is None else sp
        flags.append(sp < STOP_SPEED_MS or (dt > GAP_SEC and dd < GAP_DIST_M))
    return flags


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    hi = bisect_left(xs, x)
    lo = hi - 1
    span = xs[hi] - xs[lo]
    return ys[lo] if span <= 0 else ys[lo] + (x - xs[lo]) / span * (ys[hi] - ys[lo])


def _elev_gain(alts: list[float]) -> float | None:
    """고도 노이즈(±1m)를 무시한 누적 상승."""
    vals = [a for a in alts if a is not None]
    if len(vals) < 2:
        return None
    gain, ref = 0.0, vals[0]
    for a in vals[1:]:
        if a - ref >= _ELEV_NOISE_M:
            gain += a - ref
            ref = a
        elif ref - a >= _ELEV_NOISE_M:
            ref = a
    return round(gain, 1)


def compute_splits(streams: list[dict], total_sec: float, total_dist_m: float) -> list[dict]:
    """1km 단위 구간(마지막은 200m 이상 남을 때만 partial). 재구성 불가면 []."""
    n = len(streams)
    if n < 2 or not total_sec or total_sec <= 0 or not total_dist_m or total_dist_m < 1000:
        return []
    t = sample_times(streams, total_sec)
    d = cumulative_distance(streams, total_sec, total_dist_m)
    stopped = stopped_flags(streams, t, d)
    cum_stop = [0.0]
    for i in range(1, n):
        cum_stop.append(cum_stop[-1] + (t[i] - t[i - 1] if stopped[i] else 0.0))
    d_end = d[-1]
    full_km = int(d_end // 1000)

    bounds = [t[0]]
    for k in range(1, full_km + 1):
        bounds.append(_interp(d, t, k * 1000))
    ranges = [(bounds[k - 1], bounds[k], 1000.0, False) for k in range(1, full_km + 1)]
    remainder = d_end - full_km * 1000
    if remainder >= PARTIAL_MIN_M:
        ranges.append((bounds[full_km], t[-1], remainder, True))

    out = []
    for i, (start, end, dist, partial) in enumerate(ranges, 1):
        stop = _interp(t, cum_stop, end) - _interp(t, cum_stop, start)
        moving = end - start - stop
        idx = [s for s in range(n) if t[s] >= start and (t[s] < end or (partial and t[s] <= end))]
        hrs = [streams[s]["heart_rate"] for s in idx if not stopped[s] and streams[s].get("heart_rate")]
        alts = [streams[s].get("altitude_m") for s in idx]
        out.append({
            "idx": i, "dist_m": round(dist), "moving_sec": round(moving), "elapsed_sec": round(end - start),
            "stop_sec": round(stop), "pace_sec_km": round(moving / (dist / 1000), 1) if moving > 0 else None,
            "avg_hr": round(sum(hrs) / len(hrs)) if hrs else None,
            "elev_gain_m": _elev_gain(alts), "partial": partial,
        })
    return out


def series_step_m(total_dist_m: float) -> int:
    """≤600포인트가 되는 5m 배수 간격(최소 10m)."""
    return max(10, int(math.ceil(total_dist_m / SERIES_MAX_POINTS / 5.0) * 5))


def build_series(streams: list[dict], total_sec: float, total_dist_m: float) -> dict | None:
    """공유 거리축 시계열 — 타임라인·지도용. 거리 기준 등간격(step_m) 재표본, 페이스는 ±1칸 이동 구간."""
    n = len(streams)
    if n < 2 or not total_dist_m or total_dist_m <= 0:
        return None
    t = sample_times(streams, total_sec)
    d = cumulative_distance(streams, total_sec, total_dist_m)
    if d[-1] <= 0:
        return None
    step = series_step_m(d[-1])
    grid = [float(g) for g in range(0, int(d[-1]) + 1, step)]
    ti = [_interp(d, t, g) for g in grid]

    def pick(key: str, g: float, nd: int | None = None):
        i = min(max(bisect_left(d, g), 0), n - 1)
        v = streams[i].get(key)
        return None if v is None else (round(v, nd) if nd is not None else v)

    pace = []
    for k in range(len(grid)):
        a, b = max(k - 1, 0), min(k + 1, len(grid) - 1)
        dd, dt = grid[b] - grid[a], ti[b] - ti[a]
        p = dt / (dd / 1000) if dd > 0 and dt > 0 else None
        pace.append(round(p, 1) if p is not None and p <= _SLOWEST_PACE else None)
    return {
        "step_m": step,
        "dist_m": grid,
        "pace_sec_km": pace,
        "hr": [pick("heart_rate", g) for g in grid],
        "alt_m": [pick("altitude_m", g, 1) for g in grid],
        "lat": [pick("latitude", g, 5) for g in grid],
        "lon": [pick("longitude", g, 5) for g in grid],
    }
