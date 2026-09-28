"""스트림·심박 공용 헬퍼 — 정지 제외 이동 샘플, 선수 최대심박.

정지(신호 대기 등)를 포함하면 구간 페이스·디커플링이 오염된다(UX 리뷰 20 F-DATA-02).
정지 기준: 속도 < 0.5 m/s, 또는 Δt > 10s 이면서 Δd < 5m.
"""
from __future__ import annotations

from src.metrics.base import CalcContext

STOP_SPEED_MS = 0.5
GAP_SEC, GAP_DIST_M = 10, 5


def sample_times(streams: list[dict], total_sec: float | None) -> list[float]:
    """샘플별 경과 초. 마지막 elapsed가 총 시간의 90% 미만이면 인덱스 저장으로 보고 총 시간에 비례 환산
    (P7-DATA-STREAM-ELAPSED, 프론트 splits.ts sampleTimes와 같은 규칙)."""
    n = len(streams)
    raw = [float(s.get("elapsed_sec") or 0) for s in streams]
    if n < 2 or not total_sec or raw[-1] >= total_sec * 0.9:
        return raw
    return [i * total_sec / (n - 1) for i in range(n)]


def moving_segments(streams: list[dict], total_sec: float | None) -> list[dict]:
    """연속 샘플 쌍 → 이동 구간 목록 [{dt, dd, speed, hr}] (정지 구간 제외)."""
    t = sample_times(streams, total_sec)
    out = []
    for i in range(1, len(streams)):
        dt = t[i] - t[i - 1]
        if dt <= 0:
            continue
        d0, d1 = streams[i - 1].get("distance_m"), streams[i].get("distance_m")
        dd = (d1 - d0) if d0 is not None and d1 is not None else None
        speed = streams[i].get("speed_ms")
        if speed is None and dd is not None:
            speed = dd / dt
        if speed is None or speed < STOP_SPEED_MS:
            continue
        if dt > GAP_SEC and dd is not None and dd < GAP_DIST_M:
            continue
        hr = streams[i].get("heart_rate")
        out.append({"dt": dt, "dd": dd, "speed": speed, "hr": hr if hr and hr > 0 else None})
    return out


def athlete_max_hr(ctx: CalcContext) -> int:
    """선수 최대심박: 측정값(athlete) → 최근 180일 활동 최대 → 190. TRIMP·RE 공용(활동 자신의 최대심박 금지)."""
    stored = ctx.get_metric("max_hr_measured", scope_type="athlete", scope_id="me")
    if stored:
        return int(stored)
    max_hrs = [a["max_hr"] for a in ctx.get_activities_in_range(days=180) if a.get("max_hr")]
    return max(max_hrs) if max_hrs else 190
