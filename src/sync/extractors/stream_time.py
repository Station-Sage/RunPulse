"""스트림 시간축 결정(U18a) — 경과시간 키 선택·보간·출처(time_basis) 판정과 meta 요약 (순수 함수).

인덱스를 elapsed_sec 로 저장하지 않는다. 시간키가 없으면 times 는 None 목록이고 basis='scaled'
(summary 시간 비례 환산은 저장 경로 stream_meta_store 가 수행한다).
"""
from __future__ import annotations

import statistics

MEASURED_KEYS = ("sumElapsedDuration", "directElapsedDuration")
DERIVED_KEY = "directTimestamp"
INTERP_LIMIT = 0.05


class StreamRows(list):
    """추출기 반환 리스트(인터페이스 불변) + 시간축 출처 meta(.meta, 없으면 None)."""

    meta: dict | None = None


def _col(metrics_list, idx_map: dict[str, int], key: str) -> list:
    out = []
    for m in metrics_list:
        v = None
        if isinstance(m, dict):
            v = m.get(key)
        else:
            pos = idx_map.get(key)
            if pos is not None and pos < len(m):
                v = m[pos]
        out.append(v)
    return out


def _fill(vals: list) -> tuple[list[float], int]:
    """None 을 앞뒤 값으로 선형 보간(양 끝은 가까운 값). (채운 목록, 채운 개수)."""
    known = [i for i, v in enumerate(vals) if v is not None]
    out: list[float] = [0.0] * len(vals)
    for i, v in enumerate(vals):
        if v is not None:
            out[i] = float(v)
            continue
        lo = max((k for k in known if k < i), default=None)
        hi = min((k for k in known if k > i), default=None)
        if lo is None:
            out[i] = float(vals[hi])
        elif hi is None:
            out[i] = float(vals[lo])
        else:
            frac = (i - lo) / (hi - lo)
            out[i] = float(vals[lo]) + (float(vals[hi]) - float(vals[lo])) * frac
    return out, len(vals) - len(known)


def _monotonic(times: list[float]) -> bool:
    return all(b >= a for a, b in zip(times, times[1:]))


def resolve_time_axis(metrics_list: list, idx_map: dict[str, int]):
    """(times: list[float|None], basis, time_key). 우선순위 sumElapsed → directElapsed(measured) → directTimestamp(derived)."""
    n = len(metrics_list)
    if n == 0:
        return [], "unknown", None
    for key in MEASURED_KEYS:
        raw = _col(metrics_list, idx_map, key)
        if any(v is not None for v in raw):
            return _finish(raw, "measured", key, n)
    raw = _col(metrics_list, idx_map, DERIVED_KEY)
    first = next((v for v in raw if v is not None), None)
    if first is not None:
        rel = [None if v is None else (float(v) - float(first)) / 1000.0 for v in raw]
        return _finish(rel, "derived", DERIVED_KEY, n)
    return [None] * n, "scaled", None


def _finish(raw: list, basis: str, key: str, n: int):
    times, filled = _fill(raw)
    if filled / n > INTERP_LIMIT or not _monotonic(times):
        if basis == "measured":
            return times, "derived", key
        return [None] * n, "scaled", None
    return times, basis, key


def stream_meta(rows: list[dict], basis: str, key: str | None, sample_count: int) -> dict:
    """추출된 행의 시간 통계(span·median_dt) + 출처. stored_count 는 저장 경로가 채운다."""
    ts = [r["elapsed_sec"] for r in rows if r.get("elapsed_sec") is not None]
    dts = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    return {
        "time_basis": basis,
        "time_key": key,
        "sample_count": sample_count,
        "span_sec": float(ts[-1] - ts[0]) if len(ts) > 1 else None,
        "median_dt_sec": float(statistics.median(dts)) if dts else None,
    }
