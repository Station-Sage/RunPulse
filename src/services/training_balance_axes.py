"""Training Balance 6축 순수 계산 — target 우선순위·score·band·status·state (balance-radar 설계 §3·§4).

DB 를 읽지 않는다. 입력은 training_balance_service 가 기존 서비스 함수로 모아 넘긴다.
점수 = clamp(actual / target, 0, 1.5) × 100. 100 = 목표 도달. 데이터 부족은 score=None + reason 코드.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.services.metric_freshness_spec import STALE_DAYS

SCORE_CAP = 1.5
ORDER = ("volume", "long_run", "easy_base", "quality", "load", "recovery")
LABELS = {"volume": "볼륨", "long_run": "롱런", "easy_base": "이지 기반", "quality": "품질 강도",
          "load": "부하 균형", "recovery": "회복"}
UNITS = {"volume": "km/주", "long_run": "km", "easy_base": "%", "quality": "%", "load": "ACWR",
         "recovery": "기준선 대비"}
BANDS = {"volume": (80, 120), "long_run": (80, 120), "easy_base": (90, 115), "quality": (75, 125),
         "load": (80, 130), "recovery": (90, 110)}
EASY_TARGET_PCT = 80.0      # Seiler 80/20 [가정] (D2: 가정 상태로 출시)
QUALITY_TARGET_PCT = 20.0
ACWR_TARGET = 1.0
LONG_RUN_BY_GOAL = ((40.0, 30.0), (20.0, 18.0), (9.5, 14.0), (0.0, 12.0))  # (목표 거리 하한 km, 롱런 목표 km)
MIN_PLAN_WEEKS = 4
MIN_HISTORY_WEEKS = 8
MIN_DAYS_7, MIN_DAYS_60 = 4, 30

REASON_TEXT = {
    "no_shape": "주간 볼륨·롱런 계산이 아직 없어요",
    "insufficient_history": "기준을 잡을 볼륨 이력이 8주보다 짧아요",
    "insufficient_runs": "최근 8주 러닝 기록이 적어 강도 분포를 아직 계산하지 못했어요",
    "acwr_warmup": "부하 비율을 계산할 만큼 훈련 이력이 쌓이지 않았어요",
    "no_wellness": "수면·HRV·스트레스 기록이 부족해요",
}


def score(actual: float | None, target: float | None) -> float | None:
    """actual/target 을 0~150 으로 자른 점수. 값이 없거나 target≤0 이면 None."""
    if actual is None or not target or target <= 0:
        return None
    return round(min(max(actual / target, 0.0), SCORE_CAP) * 100, 1)


def status(value: float | None, band: tuple[float, float]) -> str | None:
    """band 경계는 균형에 포함한다."""
    if value is None:
        return None
    return "low" if value < band[0] else "high" if value > band[1] else "balanced"


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def build_axis(key: str, as_of: str, actual: float | None, target: float | None, basis: str | None,
               *, reason: str | None = None, source: list[str] | None = None,
               computed_on: str | None = None, ndigits: int = 1) -> dict:
    """축 1개 응답 dict. score 가 있으면 reason 은 지운다(점수가 있는 축은 사유가 없다)."""
    sc = score(actual, target)
    if sc is not None:
        reason = None
    band = BANDS[key]
    return {
        "key": key, "label": LABELS[key], "unit": UNITS[key],
        "actual": round(actual, ndigits) if actual is not None else None,
        "target": round(target, ndigits) if target is not None else None,
        "basis": basis, "score": sc, "band": list(band), "status": status(sc, band),
        "reason": reason, "reason_text": REASON_TEXT.get(reason) if reason else None,
        "source": source or [], "computed_on": computed_on,
        "stale": bool(computed_on and _days(as_of, computed_on) >= STALE_DAYS),
    }


def _week_of(day: str) -> str:
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


def volume_target(plan_weeks: dict[str, float], history: list[tuple[str, float]]) -> tuple[float | None, str | None, str | None]:
    """A1 (target, basis, reason). ① 계획 주 ≥4 → 계획 주평균 ② 26주 weekly_km_8w 최댓값(이력 ≥8주)."""
    if len(plan_weeks) >= MIN_PLAN_WEEKS and sum(plan_weeks.values()) > 0:
        return sum(plan_weeks.values()) / len(plan_weeks), "plan", None
    weeks = {_week_of(d) for d, km in history if km is not None}
    peak = max((km for _, km in history if km is not None), default=0.0)
    if len(weeks) < MIN_HISTORY_WEEKS or peak <= 0:
        return None, None, "insufficient_history"
    return peak, "personal_peak", None


def goal_long_run_km(distance_km: float | None) -> float | None:
    if not distance_km:
        return None
    return next(km for lo, km in LONG_RUN_BY_GOAL if distance_km >= lo)


def long_run_target(plan_longest: float | None, goal_distance_km: float | None,
                    volume_tgt: float | None) -> tuple[float, str]:
    """A2 (target, basis). ① 계획 최장 롱런 ② 목표 거리표 ③ max(10, 0.3 × A1 target)."""
    if plan_longest:
        return plan_longest, "plan"
    g = goal_long_run_km(goal_distance_km)
    if g is not None:
        return g, "goal"
    return max(10.0, 0.3 * (volume_tgt or 0.0)), "default_rule"


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def recovery_ratio(dates: list[str], series: dict[str, list], as_of: str) -> tuple[float | None, str | None]:
    """A6 (actual, 마지막 기록일). 수면·HRV 는 7일/60일 평균, 스트레스는 역수. 가용 항목만 평균."""
    cut = (date.fromisoformat(as_of) - timedelta(days=7)).isoformat()
    ratios: list[float] = []
    last: str | None = None
    for col, inverse in (("sleep_score", False), ("hrv_last_night", False), ("avg_stress", True)):
        pairs = [(d, v) for d, v in zip(dates, series.get(col) or []) if v is not None and d <= as_of]
        recent = [v for d, v in pairs if d > cut]
        if len(recent) < MIN_DAYS_7 or len(pairs) < MIN_DAYS_60:
            continue
        m7, m60 = _mean(recent), _mean([v for _, v in pairs])
        num, den = (m60, m7) if inverse else (m7, m60)
        if not den or den <= 0:
            continue
        ratios.append(num / den)
        last = max(last or "", pairs[-1][0])
    return (_mean(ratios), last) if ratios else (None, None)


def overall_state(axes: list[dict]) -> str:
    """유효 축 6 → ready, 4~5 → partial, ≤3 → collecting."""
    n = sum(1 for a in axes if a["score"] is not None)
    return "ready" if n == len(ORDER) else "partial" if n >= 4 else "collecting"
