"""Phase 5 템플릿 헬퍼 — UI와 AI context 공용 포맷/해석 함수.

Jinja2 전역 함수로도 등록 가능하고, Python에서 직접 호출도 가능.

설계 문서: v0.3/data/phase-5-impl/03-template-helpers.md
"""
from __future__ import annotations

from src.utils.metric_registry import get_metric

# ─────────────────────────────────────────────────────────────────────────────
# 메트릭 레벨 테이블 (threshold 이하 첫 번째 레이블 반환)
# ─────────────────────────────────────────────────────────────────────────────

METRIC_LEVELS: dict[str, list[tuple[float, str]]] = {
    "utrs":                 [(30, "미흡"), (50, "낮음"), (70, "보통"), (85, "양호"), (100, "우수")],
    "cirs":                 [(30, "낮음"), (50, "보통"), (70, "높음"), (100, "위험")],
    "acwr":                 [(0.8, "낮음"), (1.3, "최적"), (1.5, "주의"), (5.0, "위험")],
    "lsi":                  [(1.3, "정상"), (1.5, "상승"), (10.0, "급증")],
    "monotony":             [(1.5, "다양함"), (2.0, "보통"), (10.0, "단조로움")],
    "di":                   [(30, "미흡"), (50, "보통"), (70, "양호"), (100, "우수")],
    "rmr":                  [(30, "미흡"), (50, "낮음"), (70, "보통"), (85, "양호"), (100, "우수")],
    "rec":                  [(30, "미흡"), (50, "보통"), (70, "양호"), (100, "우수")],
    "rri":                  [(40, "부족"), (60, "상승 중"), (80, "준비됨"), (100, "피크")],
    "marathon_shape":       [(30, "부족"), (50, "기초"), (70, "상승 중"), (85, "준비됨"), (100, "피크")],
    "crs":                  [(20, "휴식"), (40, "가벼운 운동만"), (60, "보통"), (80, "전면 훈련"), (100, "고강도 가능")],
    "rtti":                 [(70, "여유"), (100, "최적"), (130, "과부하"), (300, "위험")],
    "sapi":                 [(85, "미흡"), (100, "정상"), (150, "양호")],
    "teroi":                [(0, "음수"), (5, "낮음"), (15, "양호"), (100, "우수")],
    "tpdi":                 [(5, "일관됨"), (10, "보통"), (100, "큰 격차")],
    "adti":                 [(-10, "하락"), (10, "안정"), (100, "상승 중")],
    "runpulse_vdot":        [(35, "초보"), (50, "중급"), (60, "상급"), (85, "엘리트")],
    "vdot_adj":             [(35, "초보"), (45, "중급"), (55, "상급"), (85, "엘리트")],
    "aerobic_decoupling_rp": [(5, "우수"), (10, "양호"), (15, "보통"), (100, "미흡")],
    "trimp":                [(50, "회복"), (100, "쉬운 강도"), (200, "보통"), (350, "높은 강도"), (999, "매우 높은 강도")],
    "relative_effort":      [(50, "낮음"), (100, "보통"), (200, "높음"), (999, "매우 높음")],
    "wlei":                 [(50, "낮음"), (100, "보통"), (200, "높음"), (999, "매우 높음")],
    "eftp":                 [(210, "엘리트"), (260, "상급"), (320, "중급"), (600, "초보")],
    "critical_power":       [(200, "낮음"), (280, "보통"), (500, "높음")],
}

# True=높을수록 좋음, False=낮을수록 좋음, None=범위형
HIGHER_IS_BETTER: dict[str, bool | None] = {
    "utrs": True, "crs": True, "rmr": True, "di": True, "rec": True,
    "rri": True, "marathon_shape": True, "vdot_adj": True, "sapi": True,
    "runpulse_vdot": True, "teroi": True, "adti": True, "critical_power": True,
    "efficiency_factor_rp": True, "trimp": True, "relative_effort": True,
    "wlei": True, "hrss": True,
    "cirs": False, "eftp": False, "gap_rp": False, "fearp": False,
    "lsi": False, "monotony": False, "tpdi": False, "aerobic_decoupling_rp": False,
    "acwr": None, "rtti": None,
}

_GOOD_LABELS = {"우수", "양호", "최적", "정상", "준비됨", "피크", "고강도 가능", "전면 훈련"}
_WARN_LABELS = {"보통", "다양함", "상승 중", "일관됨", "안정", "기초"}
_BAD_LABELS = {"미흡", "낮음", "위험", "과부하", "급증", "단조로움", "큰 격차", "부족", "하락"}

_PROVIDER_DISPLAY = {
    "runpulse:formula_v1": "RunPulse",
    "runpulse:rule_v1": "RunPulse",
    "garmin": "Garmin",
    "strava": "Strava",
    "intervals": "Intervals.icu",
    "runalyze": "Runalyze",
    "user": "사용자",
}


def _find_level(levels: list[tuple[float, str]], value: float) -> str:
    for threshold, label in levels:
        if value <= threshold:
            return label
    return levels[-1][1]


# ─────────────────────────────────────────────────────────────────────────────
# 단위 변환
# ─────────────────────────────────────────────────────────────────────────────

def format_distance(meters: float | None, unit: str = "km", decimals: int = 2) -> str:
    """미터 → 거리 문자열. 예: 10020.0 → "10.02km"."""
    if meters is None:
        return ""
    if unit == "km":
        return f"{meters / 1000:.{decimals}f}km"
    return f"{meters:.{decimals}f}m"


def format_pace(sec_per_km: float | None) -> str:
    """초/km → MM:SS 문자열. 예: 312.5 → "5:13"."""
    if not sec_per_km:
        return ""
    total = int(sec_per_km)
    return f"{total // 60}:{total % 60:02d}"


def format_duration(seconds: float | None) -> str:
    """초 → 시간 문자열. 1시간 미만 MM:SS, 이상 HH:MM:SS."""
    if seconds is None:
        return ""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_speed(ms: float | None, unit: str = "km/h") -> str:
    """m/s → 속도 문자열."""
    if ms is None:
        return ""
    if unit == "km/h":
        return f"{ms * 3.6:.1f}km/h"
    return f"{ms:.2f}m/s"


def format_time_prediction(seconds: float | None) -> str:
    """레이스 예측 시간 포맷 (format_duration과 동일)."""
    return format_duration(seconds)


def format_metric(metric_name: str, value: float | None, unit: str | None = None) -> str:
    """메트릭 이름과 값에 맞는 포맷 적용."""
    if value is None:
        return ""
    meta = get_metric(metric_name)
    effective_unit = unit if unit is not None else (meta.unit if meta else "")
    if effective_unit == "sec/km":
        return format_pace(value)
    if effective_unit == "sec":
        category = meta.category if meta else ""
        if category == "prediction":
            return format_time_prediction(value)
        return format_duration(value)
    if effective_unit:
        return f"{value}{effective_unit}"
    return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# 메트릭 해석
# ─────────────────────────────────────────────────────────────────────────────

def interpret_metric_level(metric_name: str, value: float | None) -> str:
    """메트릭 값 → 레이블. 미등록 메트릭은 "" 반환."""
    if value is None:
        return ""
    levels = METRIC_LEVELS.get(metric_name)
    if not levels:
        return ""
    return _find_level(levels, value)


def metric_level_color(metric_name: str, value: float | None) -> str:
    """메트릭 레벨 → CSS 색상 클래스 (green/yellow/red)."""
    level = interpret_metric_level(metric_name, value)
    if not level:
        return ""
    if level in _GOOD_LABELS:
        return "green"
    if level in _WARN_LABELS:
        return "yellow"
    if level in _BAD_LABELS:
        higher = HIGHER_IS_BETTER.get(metric_name)
        if higher is False:
            return "green"
        return "red"
    return ""


def confidence_badge(confidence: float | None) -> str:
    """신뢰도 → 한국어 레이블."""
    if confidence is None:
        return ""
    if confidence >= 0.8:
        return "높음"
    if confidence >= 0.5:
        return "보통"
    return "낮음"


def provider_badge(provider: str | None) -> str:
    """provider 식별자 → 표시 이름."""
    if not provider:
        return ""
    return _PROVIDER_DISPLAY.get(provider, provider)


def metric_display_name(metric_name: str) -> str:
    """metric_registry에서 표시 이름 조회."""
    meta = get_metric(metric_name)
    if meta and meta.description:
        return meta.description
    return metric_name


def metric_unit(metric_name: str) -> str:
    """metric_registry에서 단위 조회."""
    meta = get_metric(metric_name)
    if meta:
        return meta.unit
    return ""
