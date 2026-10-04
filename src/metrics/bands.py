"""메트릭 등급 밴드 SSOT — 값 → (status, 한국어 라벨).

등급 경계는 여기 한 곳에만 둔다(UX 리뷰 10-today F-DATA-04: 같은 값에 탭마다 다른 등급이 나오던
코드 속 등급표 4벌 제거). API는 값과 함께 status·status_label을 내려주고, 프론트는 경계값 없이
그 값만 렌더한다. `scripts/check_data_consistency.py`가 프론트에 등급 경계 함수가 다시 생기면 실패시킨다.

status 어휘는 프론트 SemanticStatus와 같다: excellent / good / neutral / caution / poor.
UTRS·CIRS·CRS·ACWR 경계는 각 Calculator의 `ranges`와 같다(metric_dictionary 기준).
"""
from __future__ import annotations

# (상한 미만, status, 라벨) 순서대로 검사, 모두 넘으면 마지막 (status, 라벨)
_Band = tuple[list[tuple[float, str, str]], tuple[str, str]]

BANDS: dict[str, _Band] = {
    # 높을수록 좋음 — utrs.py ranges
    "utrs": ([(30, "poor", "매우 낮음"), (50, "caution", "낮음"), (70, "neutral", "보통"),
              (85, "good", "좋음")], ("excellent", "매우 좋음")),
    # crs.py ranges(rest/easy_only/moderate/full/boost)
    "crs": ([(20, "poor", "휴식 권장"), (40, "caution", "가볍게만"), (60, "neutral", "보통"),
             (80, "good", "정상 훈련")], ("excellent", "강화 가능")),
    # 낮을수록 좋음(부상 위험) — cirs.py ranges
    "cirs": ([(30, "good", "낮음"), (50, "neutral", "보통"), (70, "caution", "높음")],
             ("poor", "매우 높음")),
    # 관행 밴드(10-today design §4): −30 과부하 / −10 생산적 부하 / +5 유지 / +25 신선
    "tsb": ([(-30, "poor", "과부하"), (-10, "good", "생산적 부하"), (5, "neutral", "유지"),
             (25, "excellent", "신선")], ("caution", "휴식 과다")),
    # rri.py ranges(insufficient/building/ready/peak) — 높을수록 좋음
    "rri": ([(40, "poor", "부족"), (60, "caution", "준비 중"), (80, "good", "준비됨")],
            ("excellent", "최적")),
    # acwr.py ranges
    "acwr": ([(0.8, "caution", "저부하"), (1.3, "good", "적정"), (1.5, "caution", "주의")],
             ("poor", "위험")),
    # Garmin TE 척도: 0~0.9 없음 / 1~1.9 미미 / 2~2.9 유지 / 3~3.9 향상 / 4~4.9 크게 향상 / 5.0 과도
    "training_effect_aerobic": ([(1, "neutral", "효과 없음"), (2, "neutral", "효과 미미"),
                                 (3, "neutral", "유지"), (4, "good", "향상"),
                                 (5, "excellent", "크게 향상")], ("caution", "과도")),
    # 디커플링은 절댓값(%)으로 판정
    "aerobic_decoupling": ([(5, "excellent", "유산소 안정"), (8, "good", "양호"),
                            (10, "neutral", "보통")], ("caution", "심박 드리프트")),
}
BANDS["training_effect_anaerobic"] = BANDS["training_effect_aerobic"]
BANDS["aerobic_decoupling_rp"] = BANDS["aerobic_decoupling"]

_ABS_METRICS = {"aerobic_decoupling", "aerobic_decoupling_rp"}

# 레이스 국면(테이퍼·레이스 주간)에는 생산적 부하 구간도 피로로 본다.
_RACE_PHASES = {"taper", "race_week", "race"}


def grade(metric_name: str, value: float | None, phase: str | None = None) -> dict | None:
    """값 → {"status", "label"}. 밴드가 없거나 값이 없으면 None."""
    band = BANDS.get(metric_name)
    if band is None or value is None:
        return None
    v = abs(value) if metric_name in _ABS_METRICS else value
    cuts, last = band
    status, label = last
    for upper, s, lab in cuts:
        if v < upper:
            status, label = s, lab
            break
    if metric_name == "tsb":
        if phase in _RACE_PHASES and status == "good":
            status, label = "caution", "피로 누적"
        elif phase in _RACE_PHASES and status == "excellent":
            label = "레이스 최적"
    return {"status": status, "label": label}


def band_ranges(metric_name: str) -> list[dict]:
    """차트 배경용 구간 목록 [{from, to, status, label}] — 하한/상한이 없는 끝은 None. 밴드 없으면 [].

    절댓값 판정 메트릭(디커플링)은 |값| 기준 구간이라 차트 구간으로 쓸 수 없어 제외한다.
    """
    band = BANDS.get(metric_name)
    if band is None or metric_name in _ABS_METRICS:
        return []
    cuts, (last_status, last_label) = band
    out, lo = [], None
    for upper, status, label in cuts:
        out.append({"from": lo, "to": upper, "status": status, "label": label})
        lo = upper
    out.append({"from": lo, "to": None, "status": last_status, "label": last_label})
    return out


def with_grade(item: dict, metric_name: str, value: float | None, phase: str | None = None) -> dict:
    """item에 status·status_label을 붙여 반환(밴드 없으면 그대로)."""
    g = grade(metric_name, value, phase)
    if g:
        item["status"] = g["status"]
        item["status_label"] = g["label"]
    return item
