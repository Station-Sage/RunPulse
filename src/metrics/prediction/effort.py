"""대회 노력(전력 여부) 자동 추정 — 사용자 확인(race_results.effort)이 없을 때만 쓴다(순수).

단일 %HRmax 임계는 거리와 무관해 쓸 수 없다: 10K는 LTHR 근처·그 이상, 풀은 LTHR의 약 0.9로 뛴다.
그래서 (A) 평균 HR/LTHR 를 레이스 지속시간별 기대값과 비교하고, (B) 최대 HR 도달률(최대/HRmax)을 지속시간별 기준과
비교해 각각 +1(전력 증거)/0(중립)/−1(최대 이하 증거)을 준다.
  allout: 합 ≥ 1 이고 −1 없음 · submax: 합 ≤ −1 이고 +1 없음 · 그 외 uncertain(대회 확인 화면에서 사용자에게 묻는다).
근거(REVIEW-09 §10): 기대값은 문헌 범위(Daniels M 80~90%·T 88~92% HRmax, LTHR ≈ 1시간 레이스 HR — (a/c))와
이 러너의 전력 대회(10K 0.967~1.008, 하프 0.977~0.989 — (b), n=7)로 정했다. 경계 ±0.04/0.08 와 도달률 기준은 (b/c).
보조 신호(심박 표류·전후반 페이스·예측 대비 기록)는 이 러너 데이터에서 전력/최대 이하를 가르지 못해 판정에 넣지 않는다
(9/12 최대 이하: 표류 4.3%, 예측 대비 +1.4% — 전력 10K 범위 안).
"""
from __future__ import annotations

import math
from datetime import date

from src.metrics.prediction.physio import hrmax_self

# 레이스 지속시간(분) → 기대 평균 HR/LTHR. 사이는 ln(분) 선형 보간, 양끝은 고정.
EXPECTED_LTHR_RATIO = ((20.0, 1.03), (45.0, 0.99), (105.0, 0.965), (210.0, 0.90))
AVG_OK, AVG_LOW = -0.04, -0.08          # 기대 대비 차이: ≥ −0.04 전력 증거, < −0.08 최대 이하 증거
MAX_OK_SHORT, MAX_LOW_SHORT = 0.96, 0.94   # 2시간 이하 레이스: 최대 HR/HRmax
MAX_OK_LONG, MAX_LOW_LONG = 0.92, 0.88     # 2시간 초과(마라톤): 막판 스퍼트 전 HR이 낮은 게 정상
LONG_MIN = 120.0
MIN_HR_ACTS = 5                        # 대회일 HRmax 추정에 필요한 최소 활동 수(미만이면 현재 HRmax)
LTHR_PROXY = 0.917                     # LTHR 없을 때 HRmax × 0.917 (hr_profile 폴백과 같음)


def expected_ratio(t_min: float) -> float:
    pts = EXPECTED_LTHR_RATIO
    if t_min <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if t_min <= x1:
            return y0 + (y1 - y0) * (math.log(t_min) - math.log(x0)) / (math.log(x1) - math.log(x0))
    return pts[-1][1]


def hrmax_at(runs: list[dict], day: str, fallback: float | None = None) -> float | None:
    """대회일 시점 HRmax(그 날 포함 이전 365일 활동 최대 HR 중 두 번째 값). 현재 HRmax 를 과거 대회에 쓰면
    측정 범위가 넓어진 만큼 과거 대회가 최대 이하로 보인다(사본: 2025 185 → 2026 192)."""
    d = date.fromisoformat(day)
    hrs = [r.get("max_hr") for r in runs if r.get("date") and 0 <= (d - date.fromisoformat(r["date"])).days <= 365]
    hrs = [x for x in hrs if x]
    return (hrmax_self(hrs) if len(hrs) >= MIN_HR_ACTS else None) or fallback


def auto_effort(r: dict, runs: list[dict], hrmax: float | None = None) -> str:
    """러닝 dict(get_runs) → 자동 추정. 대회일 HRmax 와 그 비례 LTHR(×0.917)로 판정한다 — 자체 LTHR 은 전력 대회에서
    추정되므로 쓰지 않는다(순환 방지). 사용자 effort 가 있으면 호출하지 말 것."""
    t = r.get("official_time_s") or r["perf_time_s"]
    return classify(t, r.get("avg_hr"), r.get("max_hr"), hrmax_at(runs, r["date"], hrmax))[0]


def classify(time_s: float, avg_hr: float | None, max_hr: float | None, hrmax: float | None,
             lthr: float | None = None) -> tuple[str, dict]:
    """→ ("allout"|"submax"|"uncertain", 근거). HR 이 전혀 없으면(T0) allout 가정(basis "no_hr")."""
    t_min = time_s / 60.0
    ref = lthr or (hrmax * LTHR_PROXY if hrmax else None)
    ev: dict = {"t_min": round(t_min, 1), "expected": round(expected_ratio(t_min), 3)}
    a = b = None
    if avg_hr and ref:
        ev["avg_lthr"] = round(avg_hr / ref, 3)
        diff = ev["avg_lthr"] - ev["expected"]
        a = 1 if diff >= AVG_OK else (-1 if diff < AVG_LOW else 0)
    if max_hr and hrmax:
        ev["max_hrmax"] = round(max_hr / hrmax, 3)
        ok, low = (MAX_OK_LONG, MAX_LOW_LONG) if t_min > LONG_MIN else (MAX_OK_SHORT, MAX_LOW_SHORT)
        b = 1 if ev["max_hrmax"] >= ok else (-1 if ev["max_hrmax"] < low else 0)
    ev.update(avg_score=a, max_score=b)
    if a is None and b is None:
        return "allout", dict(ev, basis="no_hr")
    s = [x for x in (a, b) if x is not None]
    if sum(s) >= 1 and min(s) >= 0:
        return "allout", ev
    if sum(s) <= -1 and max(s) <= 0:
        return "submax", ev
    return "uncertain", ev
