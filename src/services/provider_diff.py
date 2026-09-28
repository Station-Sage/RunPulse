"""소스 비교 차이 판정 — 항목별 임계·정규화(UX 리뷰 20 design §7-2 ③, F-DATA-03).

퍼센트 하나(5%)로 판정하면 소량 고도(5.3 vs 5.0m = 7.6%)가 노이즈 경고가 되고, 한 발 기준 케이던스(87)가
양발 기준(173)과 거짓 차이를 낸다. 임계는 항목별로 절대값 또는 퍼센트를 쓴다.
"""
from __future__ import annotations

DEFAULT_PCT = 5.0
# 컬럼 → (방식, 임계). abs = 단위 그대로의 절대 차이, pct = 최솟값 대비 %
THRESHOLDS: dict[str, tuple[str, float]] = {
    "elevation_gain": ("abs", 10.0),
    "elevation_loss": ("abs", 10.0),
    "avg_temperature": ("abs", 2.0),
    "distance_m": ("pct", 1.0),
    "duration_sec": ("pct", 1.0),
    "moving_time_sec": ("pct", 1.0),
    "elapsed_time_sec": ("pct", 1.0),
}
CADENCE_COLUMNS = {"avg_cadence", "max_cadence"}
SINGLE_LEG_MAX_SPM = 120   # 러닝 케이던스가 이보다 낮으면 한 발 기준 값으로 본다


def normalize(column: str, value):
    """서버 정규화: 한 발 기준 케이던스(Intervals 등) → 양발 spm."""
    if column in CADENCE_COLUMNS and isinstance(value, (int, float)) and 0 < value < SINGLE_LEG_MAX_SPM:
        return value * 2
    return value


def diff(values: list, key: str | None = None, default_pct: float = DEFAULT_PCT) -> dict | None:
    """숫자 2개 이상이면 {abs, pct, significant, threshold}. 판정은 항목별 임계."""
    vals = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(vals) < 2:
        return None
    hi, lo = max(vals), min(vals)
    span = hi - lo
    base = abs(lo) or abs(hi)
    pct = span / base * 100 if base else 0.0
    mode, limit = THRESHOLDS.get(key or "", ("pct", default_pct))
    significant = (span > limit) if mode == "abs" else (pct > limit)
    return {"abs": round(span, 4), "pct": round(pct, 2), "significant": significant,
            "threshold": {"mode": mode, "value": limit}}


def legacy_discrepancy(d: dict | None) -> dict | None:
    """기존 `discrepancy` 필드(프론트 호환) — 판정은 항목별 임계를 따른다."""
    if d is None:
        return None
    return {"detected": d["significant"], "maxDiff": d["abs"], "maxDiffPct": d["pct"],
            "severity": "warning" if d["significant"] else "info"}
