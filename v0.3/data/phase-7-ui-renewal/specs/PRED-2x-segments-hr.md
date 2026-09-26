# PRED-2x — Daniels·칼만, 세그먼트, 예측 라이브러리, 심박 프로필·기기 참조 (예측 리뉴얼 r4)

근거: `REVIEW-07-prediction-renewal.md` §R4(r3 §2-5·2-6·4), `REVIEW-09-signal-design-r4.md`. 순서는 `P7-PRED-00-INDEX.md` r4 표.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-20 — Daniels 공식·강도 구간·세트 등가 지속시간 + 로컬 레벨 칼만 (순수, r4 신규)

- 의존: 없음 · UI 노출: 없음(P7-PRED-22·41·51·85가 사용)
- 파일: `src/metrics/prediction/daniels.py`, `src/metrics/prediction/kalman.py`(신규), `tests/test_daniels_kalman.py`(신규). `src/metrics/prediction/__init__.py`는 P7-PRED-22가 만든다 — 이 유닛에서 패키지가 없으면 빈 `__init__.py`를 함께 만든다(P7-PRED-22의 전문과 같은 내용).
- 근거: REVIEW-09 §2·§3·§5. 강도는 기억한 표가 아니라 **Daniels–Gilbert 식**으로 계산한다: VO2(v) = −4.60 + 0.182258v + 0.000104v², %VO2max(t) = 0.8 + 0.1894393e^(−0.012778t) + 0.2989558e^(−0.1932605t). T = 60분 레이스, I = %VO2max 1.0(≈11.03분, `i_minutes()`로 검증), R = 1마일 레이스, M = 마라톤 레이스, E = %VO2max 0.59~0.74 [가정 — P7-PRED-99 U-1].
- 세트 등가 지속시간 t_eq: 휴식/작업 비 ρ ≤ 0.2 → 60분(T), ρ ≥ 1.0 → 11.03분(I), 사이는 ln ρ 선형 보간. 짧은 반복(≤150초)·ρ ≥ 1.5 → R, 연속 ≥40분 → M. 휴식 비율 앵커는 [가정 — U-2].
- 칼만: 상태 = 레이스 능력(VDOT, 15℃ 등가), 랜덤워크 하루 분산 q. `filter_level(obs, as_of, q, low_mult=None)`은 관측 종류별 기여(칼만 이득 분해)를 함께 낸다. `low_mult`는 r4 섀도 비대칭 변형(현재 추정보다 낮은 관측의 분산 배율).

**`src/metrics/prediction/daniels.py`** — 신규, 전문 그대로(116줄)

````python
"""Daniels–Gilbert VDOT 공식과 강도 구간(E/M/T/I/R) 역산 — 표가 아니라 공식으로 계산한다(순수 함수).

근거(REVIEW-09 §2):
  산소 비용  VO2(v) = −4.60 + 0.182258·v + 0.000104·v²          (v: m/min)
  지속 비율  %VO2max(t) = 0.8 + 0.1894393·e^(−0.012778·t) + 0.2989558·e^(−0.1932605·t)   (t: 분)
  VDOT = VO2(d/t) / %VO2max(t)  — 저장소 `src/utils/daniels_table.get_race_predictions`·`training/readiness.py` 와 같은 식.
강도 구간(식으로 정의, 원표 대조는 P7-PRED-99 TODO):
  M = 마라톤 레이스 속도, T = 60분 레이스 속도(%VO2max 0.888), I = VO2max 속도(%VO2max 1.0 ≈ 11.0분 레이스),
  R = 1마일 레이스 속도, E = %VO2max 0.59~0.74 [가정].
세트 등가 지속시간(REVIEW-09 §3): 휴식/작업 비 ρ 가 T 처방(0.2) 이하면 60분, I 처방(1.0) 이상이면 11.03분,
  그 사이는 ln ρ 에 대해 로그-선형 보간. 짧은 반복(≤150초)에 ρ ≥ 1.5 면 R(마일), 40분 이상 연속이면 M.
"""
from __future__ import annotations

import math

MILE_M = 1609.344
MARATHON_M = 42195.0
T_MIN = 60.0                 # T = 60분 레이스 강도
I_MIN = 11.03                # %VO2max(t) = 1.0 이 되는 t(분) — i_minutes() 로 검증
RHO_T = 0.2                  # T 크루즈 처방 휴식/작업 비(5분 작업당 1분 휴식) [가정: 원문 확인 필요]
RHO_I = 1.0                  # I 처방 휴식/작업 비(작업 시간과 같거나 짧게) [가정: 원문 확인 필요]
R_MAX_REP_S = 150.0          # R 반복 길이 상한(초)
R_MIN_RHO = 1.5              # R 휴식/작업 비 하한(원문 2~3배 [가정]의 하단보다 낮춰 오차 흡수)
CONT_MIN_S = 480.0           # 연속 작업 T 최소(8분)
M_MIN_S = 2400.0             # 연속 작업 M 최소(40분)
E_PCT = (0.59, 0.74)         # E 강도 %VO2max 범위 [가정: 원문 확인 필요]


def vo2_cost(v_m_min: float) -> float:
    return -4.60 + 0.182258 * v_m_min + 0.000104 * v_m_min * v_m_min


def pct_vo2max(t_min: float) -> float:
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t_min) + 0.2989558 * math.exp(-0.1932605 * t_min)


def speed_for_vo2(vo2: float) -> float:
    """VO2(ml/kg/min) → 속도(m/s). vo2_cost 의 역함수."""
    a, b, c = 0.000104, 0.182258, -4.60 - vo2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a) / 60.0


def vdot(dist_m: float, time_s: float) -> float:
    tm = time_s / 60.0
    return vo2_cost(dist_m / tm) / pct_vo2max(tm)


def time_for_vdot(vd: float, dist_m: float) -> float:
    """VDOT·거리 → 레이스 시간(s). 이분법."""
    lo, hi = 60.0, 60000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if vdot(dist_m, mid) > vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def i_minutes() -> float:
    """%VO2max(t) = 1 인 t(분). 상수 I_MIN 검증용."""
    lo, hi = 5.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if pct_vo2max(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def zone_speeds(vd: float) -> dict[str, float]:
    """VDOT → 구간 속도(m/s). E 는 (느린, 빠른) 범위."""
    return {"E": (speed_for_vo2(vd * E_PCT[0]), speed_for_vo2(vd * E_PCT[1])),
            "M": MARATHON_M / time_for_vdot(vd, MARATHON_M),
            "T": speed_for_vo2(vd * pct_vo2max(T_MIN)),
            "I": speed_for_vo2(vd),
            "R": MILE_M / time_for_vdot(vd, MILE_M)}


def threshold_speed(vd: float) -> float:
    """VDOT → T 속도(m/s) = 60분 레이스 속도."""
    return speed_for_vo2(vd * pct_vo2max(T_MIN))


def equivalent_minutes(n_reps: int, rho: float) -> float:
    """세트 등가 지속시간(분). 연속(1회)이면 T 60분, ρ≤0.2 → 60, ρ≥1.0 → 11.03, 사이는 ln ρ 로그-선형."""
    if n_reps <= 1 or rho <= RHO_T:
        return T_MIN
    if rho >= RHO_I:
        return I_MIN
    s = math.log(rho / RHO_T) / math.log(RHO_I / RHO_T)
    return math.exp(math.log(T_MIN) + (math.log(I_MIN) - math.log(T_MIN)) * s)


def set_zone(n_reps: int, rep_s: float, rho: float, work_s: float) -> str | None:
    """세트 구조 → 구간(R/I/T/M) — 평균 HR·목표 페이스 없이 구조만 본다. 해당 없으면 None."""
    if n_reps <= 1:
        if work_s >= M_MIN_S:
            return "M"
        return "T" if work_s >= CONT_MIN_S else None
    if rep_s <= R_MAX_REP_S and rho >= R_MIN_RHO:
        return "R"
    if work_s < CONT_MIN_S:
        return None
    return "I" if rho >= math.sqrt(RHO_T * RHO_I) else "T"     # 라벨 경계 = 두 처방의 기하 중간(0.447)


def set_vdot(zone: str, speed_ms: float, n_reps: int, rho: float) -> float:
    """구간별 속도 → VDOT. T/I 는 등가 지속시간, R 은 1마일 레이스, M 은 마라톤 레이스로 역산."""
    if zone == "R":
        return vdot(MILE_M, MILE_M / speed_ms)
    if zone == "M":
        return vdot(MARATHON_M, MARATHON_M / speed_ms)
    return vo2_cost(speed_ms * 60.0) / pct_vo2max(equivalent_minutes(n_reps, rho))
````

**`src/metrics/prediction/kalman.py`** — 신규, 전문 그대로(54줄)

````python
"""로컬 레벨 칼만 필터 — 날짜별 관측(VDOT·분산)을 정밀도 가중으로 결합해 기준일의 체력 VDOT와 분산을 낸다(순수).

상태: x_t = 레이스 능력(VDOT, 15℃ 등가). 과정: 랜덤워크, 하루 분산 q. 관측: y_i = x_t + e_i, e_i ~ N(0, r_i).
관측이 많을수록·최근일수록·분산이 작을수록 가중이 커진다. 기여도는 최종 추정에서 관측 종류별 가중 합.
"""
from __future__ import annotations

from datetime import date

INIT_VAR = 9.0           # 첫 관측 전 사전 분산(VDOT²) — 첫 관측값을 중심으로 둔다(정보 없는 사전, 결과 영향 작음)


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def filter_level(obs: list[dict], as_of: str, q: float, low_mult: dict[str, float] | None = None) -> dict | None:
    """obs: [{"date","y","var","kind"}] (날짜 오름차순, as_of 이전만). 반환 {"x","var","weights","n","last"} 또는 None.

    weights: 종류별 최종 추정 기여(합 1). 사전(첫 관측 중심)의 몫은 첫 관측 종류에 합산한다.
    low_mult: 비대칭 변형 — 관측이 현재 추정보다 낮을 때 분산 배율({"race": 4, "set": 4}). 대회 = 상한 증거,
    세트 = 하한 증거라 '낮은 쪽'이 약한 증거다(REVIEW-07 §R4-8(2)). None 이면 대칭.
    """
    obs = [o for o in obs if o["date"] < as_of]
    if not obs:
        return None
    x = obs[0]["y"]
    p = INIT_VAR
    w: dict[str, float] = {obs[0]["kind"]: 1.0}
    last = obs[0]["date"]
    for o in obs:
        p += q * _days(last, o["date"])
        last = o["date"]
        r = o["var"]
        if low_mult and o["y"] < x:
            r *= low_mult.get("race" if o["kind"] == "race" else "set", 1.0)
        k = p / (p + r)
        x += k * (o["y"] - x)
        p *= 1.0 - k
        w = {key: v * (1.0 - k) for key, v in w.items()}
        w[o["kind"]] = w.get(o["kind"], 0.0) + k
    p += q * _days(last, as_of)
    tot = sum(w.values()) or 1.0
    return {"x": x, "var": p, "weights": {k2: round(v / tot, 3) for k2, v in sorted(w.items())}, "n": len(obs), "last": last}


def add_obs(state: dict, y: float, var: float, kind: str) -> dict:
    """기준일 시점의 추가 관측(예: 심박-속도 H) 1개를 반영한 새 상태."""
    k = state["var"] / (state["var"] + var)
    w = {key: v * (1.0 - k) for key, v in state["weights"].items()}
    w[kind] = w.get(kind, 0.0) + k
    tot = sum(w.values()) or 1.0
    return dict(state, x=state["x"] + k * (y - state["x"]), var=state["var"] * (1.0 - k),
                weights={k2: round(v / tot, 3) for k2, v in sorted(w.items())}, n=state["n"] + 1)
````

**`tests/test_daniels_kalman.py`** — 신규, 전문 그대로(33줄)

````python
"""P7-PRED-20: Daniels–Gilbert 공식·강도 구간·세트 등가 지속시간, 로컬 레벨 칼만(순수)."""
from src.metrics.prediction import daniels as dn
from src.metrics.prediction.kalman import add_obs, filter_level


def test_formula_anchors():
    assert abs(dn.i_minutes() - dn.I_MIN) < 0.05                       # %VO2max = 1 인 레이스 ≈ 11분
    assert abs(dn.time_for_vdot(50, 42195) - 11449) < 60               # VDOT 50 마라톤 ≈ 3:10:49
    assert abs(dn.vdot(10000, dn.time_for_vdot(45, 10000)) - 45) < 0.01


def test_zone_order():
    z = dn.zone_speeds(50)
    assert z["E"][1] < z["M"] < z["T"] < z["I"] < z["R"]
    assert abs(1000 / dn.threshold_speed(50) - 253.3) < 0.5


def test_equivalent_minutes_rest_ratio():
    assert dn.equivalent_minutes(5, 0.1) == dn.T_MIN                  # 크루즈(짧은 휴식) = 60분 레이스
    assert dn.equivalent_minutes(5, 1.2) == dn.I_MIN                  # 휴식 ≥ 작업 = I
    assert dn.I_MIN < dn.equivalent_minutes(5, 0.5) < dn.T_MIN         # 사이는 ln ρ 보간


def test_kalman_weights_and_decay():
    obs = [{"date": "2026-01-01", "y": 44.0, "var": 1.0, "kind": "race"},
           {"date": "2026-06-01", "y": 46.0, "var": 3.0, "kind": "T"}]
    st = filter_level(obs, "2026-06-02", 0.01)
    assert 44.0 < st["x"] < 46.0 and abs(sum(st["weights"].values()) - 1) < 0.01
    near = filter_level(obs, "2026-06-02", 0.05)                      # q 크면 오래된 대회 가중이 준다
    assert near["weights"]["race"] < st["weights"]["race"]
    h = add_obs(st, 47.0, 1.0, "H")
    assert h["x"] > st["x"] and "H" in h["weights"]
    assert filter_level([], "2026-06-02", 0.01) is None
````

검증:
```
python3 -m pytest tests/test_daniels_kalman.py -q
```

## P7-PRED-21 — 세그먼트 분해 r4(순수): 랩 → 작업/휴식 블록, bout, 세트 구조(`work_set`), 세션 형태

- 의존: 없음 · UI 노출: 없음(P7-PRED-22·23·41·43이 사용)
- 파일: `src/metrics/segments.py`(신규), `tests/test_segments.py`(신규)
- r3 대비 변경(REVIEW-07 §R4-1, REVIEW-09 §3-1): 작업구간 W 폐기에 맞춰 **세트 구조**를 낸다.
  - 작업에 붙은 스트라이드 조각은 작업으로 병합한다.
  - 휴식 속도 ≥ 0.75×작업 속도(`FLOAT_RATIO`)인 플로트 휴식은 휴식으로 세지 않는다.
  - `work_set(bouts)`는 반복 수, 반복 중앙 길이, 작업 시간, 평균 작업 속도, 휴식/작업 비 ρ, Daniels 구간(`daniels.set_zone`)을 낸다.
  - 품질 판정은 작업 속도 ≥ 1.18×이지 속도(`QUALITY_CONTRAST`, (b) 전 기간 분포에서 정함)다.
  - `session_type`은 역치 속도 v_t 없이(예측 비의존) 구조·속도 대비로만 판정한다. 활동 전체 평균 HR·페이스는 쓰지 않는다.

**`src/metrics/segments.py`** — 신규, 전문 그대로(219줄)

````python
"""세그먼트 분해 — 랩/스트림 블록을 워밍업·작업·휴식·쿨다운으로 나누고 세트·세션 유형을 판정한다(순수 함수).

평균 HR·평균 페이스·기기 없이(GPS·시간만) 판정한다. 입력 블록 형식:
    {"dur_s": float, "dist_m": float, "speed_ms": float, "hr": float|None, "max_hr": float|None, "itype": str|None}
speed_ms 는 경사 보정 속도(GAP)가 있으면 그것을 넣는다. 세트 구간(R/I/T/M)은 Daniels 처방 구조
(반복 길이·휴식/작업 비·연속 시간)로 정한다(`prediction.daniels.set_zone`, REVIEW-09 §3).
"""
from __future__ import annotations

from statistics import median

from src.metrics.prediction.daniels import set_zone

WORK_RATIO = 1.10       # 작업 블록 후보: 이지 기준 속도의 110% 이상
QUALITY_CONTRAST = 1.18  # 품질 세트: 작업 평균 속도 ≥ 이지 기준 속도 × 1.18 (오토랩 이지런 오탐 제거, REVIEW-09 §3-3)
FLOAT_RATIO = 0.75      # 휴식 속도 ≥ 작업 속도 × 0.75 면 플로트(능동 회복) — 휴식으로 세지 않는다
STRIDE_MAX_S = 40.0     # 이보다 짧은 빠른 블록은 스트라이드(작업 블록에 붙어 있으면 작업의 꼬리로 합친다)
LONG_KM = 16.0
LONG_S = 5400.0
REST_ITYPES = {"REST", "RECOVERY"}


def label_blocks(blocks: list[dict], v_easy: float) -> list[str]:
    """각 블록의 역할: warmup | work | stride | rest | cooldown | easy."""
    labels: list[str] = []
    for b in blocks:
        it = (b.get("itype") or "").upper()
        v = b.get("speed_ms") or 0.0
        if it == "WARMUP":
            labels.append("warmup")
        elif it == "COOLDOWN":
            labels.append("cooldown")
        elif it in REST_ITYPES:
            labels.append("rest")
        elif v >= v_easy * WORK_RATIO:
            labels.append("stride" if b["dur_s"] < STRIDE_MAX_S else "work")
        else:
            labels.append("easy")
    for i, lab in enumerate(labels):      # 오토랩이 반복 끝을 잘라 만든 짧은 조각은 작업의 일부
        if lab == "stride" and ((i > 0 and labels[i - 1] == "work") or (i + 1 < len(labels) and labels[i + 1] == "work")):
            labels[i] = "work"
    work_idx = [i for i, lab in enumerate(labels) if lab == "work"]
    if work_idx:
        first, last = work_idx[0], work_idx[-1]
        for i in range(first + 1, last):
            if labels[i] == "easy":
                labels[i] = "rest"
        for i in range(0, first):
            if labels[i] == "easy":
                labels[i] = "warmup"
        for i in range(last + 1, len(labels)):
            if labels[i] == "easy":
                labels[i] = "cooldown"
    return labels


def build_bouts(blocks: list[dict], labels: list[str]) -> list[dict]:
    """연속 work 블록을 bout 하나로 합친다. 각 bout 직후 첫 rest 의 길이·평균 HR·HR 하강을 붙인다."""
    raw: list[dict] = []
    cur: dict | None = None
    for b, lab in zip(blocks, labels):
        if lab == "work":
            if cur is None:
                cur = {"dur_s": 0.0, "dist_m": 0.0, "hr_sum": 0.0, "hr_dur": 0.0, "max_hr": None}
            cur["dur_s"] += b["dur_s"]
            cur["dist_m"] += b["dist_m"]
            if b.get("hr"):
                cur["hr_sum"] += b["hr"] * b["dur_s"]
                cur["hr_dur"] += b["dur_s"]
            if b.get("max_hr"):
                cur["max_hr"] = max(cur["max_hr"] or 0, b["max_hr"])
            continue
        if cur is not None:
            raw.append(cur)
            cur = None
        if lab == "rest" and raw and "rest_s" not in raw[-1]:
            raw[-1]["rest_s"] = b["dur_s"]
            raw[-1]["rest_hr"] = b.get("hr")
            raw[-1]["rest_speed_ms"] = b.get("speed_ms")
    if cur is not None:
        raw.append(cur)
    out = []
    for o in raw:
        hr = o["hr_sum"] / o["hr_dur"] if o["hr_dur"] else None
        rest_hr = o.get("rest_hr")
        out.append({
            "dur_s": round(o["dur_s"], 1),
            "dist_m": round(o["dist_m"], 1),
            "speed_ms": o["dist_m"] / o["dur_s"] if o["dur_s"] else 0.0,
            "hr": round(hr, 1) if hr else None,
            "max_hr": o["max_hr"],
            "rest_s": o.get("rest_s"),
            "rest_hr": rest_hr,
            "rest_speed_ms": o.get("rest_speed_ms"),
            "hr_drop": round(o["max_hr"] - rest_hr, 1) if (o["max_hr"] and rest_hr) else None,
        })
    return out


def work_set(bouts: list[dict]) -> dict | None:
    """bout 목록 → 세트 구조: 반복 수, 반복 중앙 길이, 작업 시간, 평균 작업 속도, 휴식/작업 비(마지막 bout 제외, 플로트 제외)."""
    if not bouts:
        return None
    n = len(bouts)
    work_s = sum(b["dur_s"] for b in bouts)
    speed = sum(b["dist_m"] for b in bouts) / work_s if work_s else 0.0
    rest = den = 0.0
    for b in bouts[:-1]:
        den += b["dur_s"]
        rv = b.get("rest_speed_ms")
        if b.get("rest_s") and not (rv and b["speed_ms"] and rv >= FLOAT_RATIO * b["speed_ms"]):
            rest += b["rest_s"]
    rho = rest / den if den else 0.0
    rep_s = median(b["dur_s"] for b in bouts)
    return {"n": n, "rep_s": rep_s, "work_s": work_s, "speed_ms": speed, "rho": round(rho, 3),
            "zone": set_zone(n, rep_s, rho, work_s)}


def session_type(bouts: list[dict], total_s: float, total_m: float, v_easy: float,
                 is_race: bool = False, n_strides: int = 0) -> str:
    """race | sprint | repetition | interval | tempo | steady | long | easy (기기 없이 구조·속도 대비로만)."""
    if is_race:
        return "race"
    is_long = total_m >= LONG_KM * 1000 or total_s >= LONG_S
    ws = work_set(bouts)
    if ws is None:
        if n_strides >= 4 and total_s < LONG_S:
            return "sprint"
        return "long" if is_long else "easy"
    quality = ws["speed_ms"] >= QUALITY_CONTRAST * v_easy
    if ws["zone"] is None or not quality:
        if ws["zone"] in ("T", "M") and ws["n"] == 1 and not is_long:
            return "steady"
        return "long" if is_long else "easy"
    return {"R": "repetition", "I": "interval", "T": "tempo"}.get(ws["zone"], "long" if is_long else "steady")


def set_summary(bouts: list[dict]) -> dict | None:
    """세트 요약: 세트 수, 평균 작업 거리·시간, 작업 페이스, 휴식/작업 비율, 세트 간 속도 유지(드롭 %)."""
    if not bouts:
        return None
    n = len(bouts)
    work_s = sum(b["dur_s"] for b in bouts)
    work_m = sum(b["dist_m"] for b in bouts)
    rest_s = sum(b.get("rest_s") or 0 for b in bouts)
    drop = None
    if n >= 4:
        half = n // 2
        v1 = sum(b["speed_ms"] for b in bouts[:half]) / half
        v2 = sum(b["speed_ms"] for b in bouts[-half:]) / half
        drop = round((v1 - v2) / v1 * 100, 1) if v1 else None
    hrs = [b["hr"] for b in bouts if b.get("hr")]
    drops = [b["hr_drop"] for b in bouts if b.get("hr_drop") is not None]
    ws = work_set(bouts)
    return {
        "n_sets": n,
        "zone": ws["zone"],
        "rho": ws["rho"],
        "work_dist_m_avg": round(work_m / n, 1),
        "work_dur_s_avg": round(work_s / n, 1),
        "work_pace_sec_km": round(1000 * work_s / work_m, 1) if work_m else None,
        "work_hr_avg": round(sum(hrs) / len(hrs), 1) if hrs else None,
        "rest_work_ratio": round(rest_s / work_s, 2) if work_s else None,
        "speed_drop_pct": drop,
        "hr_drop_avg": round(sum(drops) / len(drops), 1) if drops else None,
    }


def stream_to_blocks(t: list[float], dist: list[float], hr: list, win_s: float = 30.0, tol: float = 0.08) -> list[dict]:
    """스트림(실제 경과초·누적거리·HR) → 30초 창 블록 → 속도 차 tol 이내 인접 블록 병합."""
    blocks: list[dict] = []
    i, n = 0, len(t)
    while i < n - 1:
        j = i
        while j < n - 1 and t[j] - t[i] < win_s:
            j += 1
        dt = t[j] - t[i]
        dd = max(0.0, (dist[j] or 0) - (dist[i] or 0))
        hs = [h for h in hr[i:j + 1] if h]
        if dt > 0:
            blocks.append({"dur_s": dt, "dist_m": dd, "speed_ms": dd / dt,
                           "hr": sum(hs) / len(hs) if hs else None,
                           "max_hr": max(hs) if hs else None, "itype": None})
        i = j
    merged: list[dict] = []
    for b in blocks:
        if merged and merged[-1]["speed_ms"] > 0 and abs(b["speed_ms"] - merged[-1]["speed_ms"]) / merged[-1]["speed_ms"] <= tol:
            m = merged[-1]
            d = m["dur_s"] + b["dur_s"]
            if m["hr"] and b["hr"]:
                m["hr"] = (m["hr"] * m["dur_s"] + b["hr"] * b["dur_s"]) / d
            else:
                m["hr"] = m["hr"] or b["hr"]
            m["max_hr"] = max(m["max_hr"] or 0, b["max_hr"] or 0) or None
            m["dur_s"] = d
            m["dist_m"] += b["dist_m"]
            m["speed_ms"] = m["dist_m"] / d
        else:
            merged.append(dict(b))
    return merged


def repair_time_axis(elapsed: list[float], duration_s: float) -> list[float]:
    """시간축이 샘플 번호(마지막 값 < 활동시간의 90%)면 활동시간을 균등 분배한 초로 바꾼다."""
    if not elapsed:
        return []
    if elapsed[-1] >= duration_s * 0.9:
        return list(elapsed)
    n = len(elapsed)
    dt = duration_s / max(1, n - 1)
    return [i * dt for i in range(n)]


def cumulative_distance(t: list[float], speed: list) -> list[float]:
    """누적거리가 없는 스트림: 속도 × 시간 적분."""
    out = [0.0]
    for i in range(1, len(t)):
        out.append(out[-1] + (speed[i] or 0.0) * (t[i] - t[i - 1]))
    return out
````

**`tests/test_segments.py`** — 신규, 전문 그대로(99줄)

````python
"""P7-PRED-21: 세그먼트 분해 r4 — 구조 기반 세트 구간·세션 유형(기기 불필요)."""
from src.metrics.segments import (label_blocks, build_bouts, session_type, set_summary, stream_to_blocks,
                                  repair_time_axis, cumulative_distance, work_set)

V_EASY = 1000 / 350          # 5:50/km


def B(d, s, hr=None, it=None, mx=None):
    return {"dur_s": s, "dist_m": d, "speed_ms": d / s, "hr": hr, "max_hr": mx, "itype": it}


def test_interval_6x1000_jog_rest():
    blocks = [B(2000, 720, 130, "WARMUP")]
    for _ in range(6):
        blocks += [B(1000, 250, 165, "ACTIVE", 172), B(300, 120, 140, "RECOVERY")]
    blocks += [B(1500, 540, 135, "COOLDOWN")]
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert len(bouts) == 6 and bouts[0]["hr_drop"] == 32.0 and bouts[0]["rest_speed_ms"] == 2.5
    ws = work_set(bouts)
    assert ws["rho"] == 0.48 and ws["zone"] == "I"
    assert session_type(bouts, 4500, 11300, V_EASY) == "interval"
    s = set_summary(bouts)
    assert s["n_sets"] == 6 and s["zone"] == "I" and s["rest_work_ratio"] == 0.48


def test_float_rest_is_not_rest():
    blocks = []
    for _ in range(3):
        blocks += [B(2000, 520, 170, "ACTIVE"), B(1000, 340, 150, "ACTIVE")]   # 1km 플로트 5:40 (작업의 76%)
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    ws = work_set(bouts)
    assert ws["rho"] == 0.0 and ws["zone"] == "T"


def test_stride_tail_merged_into_work():
    blocks = [B(1000, 360, 130, "WARMUP"), B(1000, 285, 160, "ACTIVE"), B(50, 14, 160, "ACTIVE"), B(200, 90, 140, "RECOVERY"),
              B(1000, 285, 165, "ACTIVE"), B(50, 14, 165, "ACTIVE"), B(500, 200, 140, "COOLDOWN")]
    lab = label_blocks(blocks, V_EASY)
    assert lab.count("stride") == 0
    bouts = build_bouts(blocks, lab)
    assert len(bouts) == 2 and bouts[0]["dur_s"] == 299.0


def test_continuous_tempo_auto_laps_no_itype():
    blocks = [B(1000, 360, 135), B(1000, 355, 138)] + [B(1000, 272, 170) for _ in range(4)] + [B(1000, 370, 150)]
    lab = label_blocks(blocks, V_EASY)
    assert lab[:2] == ["warmup", "warmup"] and lab[-1] == "cooldown"
    bouts = build_bouts(blocks, lab)
    assert len(bouts) == 1 and bouts[0]["dur_s"] == 1088.0
    assert session_type(bouts, 2445, 7000, V_EASY) == "tempo"


def test_slow_block_is_not_quality():
    blocks = [B(1000, 345, 140)] * 2 + [B(1000, 310, 150)] * 3 + [B(1000, 345, 140)]   # 5:10 = 이지의 1.13배
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert session_type(bouts, 1990, 6000, V_EASY) == "steady"


def test_repetition_and_sprint():
    blocks = [B(2000, 700, 130, "WARMUP")]
    for _ in range(8):
        blocks += [B(400, 88, 170, "ACTIVE"), B(200, 180, 120, "REST")]
    bouts = build_bouts(blocks, label_blocks(blocks, V_EASY))
    assert work_set(bouts)["zone"] == "R" and session_type(bouts, 2800, 6800, V_EASY) == "repetition"
    blocks = [B(2000, 700, 130, "WARMUP")]
    for _ in range(6):
        blocks += [B(80, 15, 150, "INTERVAL"), B(300, 120, 125, "REST")]
    lab = label_blocks(blocks, V_EASY)
    assert lab.count("stride") == 6
    assert session_type(build_bouts(blocks, lab), 1500, 4280, V_EASY, n_strides=6) == "sprint"


def test_easy_long_race():
    blocks = [B(1000, 345, 140) for _ in range(10)]
    assert session_type(build_bouts(blocks, label_blocks(blocks, V_EASY)), 3450, 10000, V_EASY) == "easy"
    blocks = [B(1000, 350, 142) for _ in range(20)]
    assert session_type(build_bouts(blocks, label_blocks(blocks, V_EASY)), 7000, 20000, V_EASY) == "long"
    assert session_type([], 2700, 10000, V_EASY, is_race=True) == "race"


def test_set_drop():
    bouts = [{"dur_s": 240, "dist_m": 1000, "speed_ms": 1000 / 240, "hr": 165, "max_hr": 170, "rest_s": 90, "rest_hr": 140, "hr_drop": 30}] * 2 + \
            [{"dur_s": 260, "dist_m": 1000, "speed_ms": 1000 / 260, "hr": 170, "max_hr": 176, "rest_s": 90, "rest_hr": 150, "hr_drop": 26}] * 2
    assert set_summary(bouts)["speed_drop_pct"] == 7.7


def test_stream_blocks_detect_alternation():
    t = list(range(0, 1201)); d = [0.0]; hr = [140] * 1201
    for i in range(1, 1201):
        v = 4.0 if (i // 120) % 2 == 1 else 2.6
        d.append(d[-1] + v)
    blocks = stream_to_blocks(t, d, hr)
    assert len(build_bouts(blocks, label_blocks(blocks, 2.8))) == 5


def test_time_axis_repair():
    assert repair_time_axis([0, 1, 2, 3], 30) == [0.0, 10.0, 20.0, 30.0]
    assert repair_time_axis([0, 10, 20, 29], 30) == [0, 10, 20, 29]
    assert cumulative_distance([0, 10, 20], [None, 3.0, 3.0]) == [0.0, 30.0, 60.0]
````

검증:
```
python3 -m pytest tests/test_segments.py -q
```

## P7-PRED-22 — 예측 순수 라이브러리: r3(기본 표시) + r4(섀도) 신호·결합 + 생리 + 전력 판정

- 의존: 없음 · UI 노출: 없음
- 파일: 모두 신규다.
  - 라이브러리: `src/metrics/prediction/__init__.py`, `core.py`·`signals.py`(r3 — 기본 경로 `darp.py`용), `core_r4.py`·`signals_r4.py`(r4 섀도 `darp_r4.py`용), `physio.py`, `effort.py`
  - 테스트: `tests/test_prediction_core.py`, `tests/test_prediction_signals.py`, `tests/test_prediction_core_r4.py`, `tests/test_prediction_signals_r4.py`, `tests/test_race_effort.py`
- r3 경로(`core.py`·`signals.py`)는 사용자 결정(2026-09-26)으로 **기본 표시**다. 상수는 r3 그대로다(`DECAY_PER_WEEK=0.08`, `K_DOWN=0.25`, `H_WEIGHT=0.20` 등 — REVIEW-07 §0). 바뀐 곳은 전력 판정 하나다(아래).
- r4 경로(`core_r4.py`·`signals_r4.py`, REVIEW-09 §3~7, REVIEW-07 §R4-2·§R4-8):
  - 관측: 전력 대회(15℃ 환산), 품질 세트(휴식 보정 Daniels 강도, 기온 비정규화), H(심박-속도의 LTHR 속도).
  - 최대 이하 대회(effort='paced' 또는 자동 판정 uncertain)는 **하한 관측**(kind `paced`, 세트 분산)으로 쓴다.
  - 결합과 범위: 개인 k(겹치지 않는 대회 쌍), 거리 외삽 분산, 롱런 외삽, Tanda 결합, erf 신뢰도.
  - 섀도 변형 상수: `ASYM_LOW_MULT`(c), `MAINT_ALPHA` 0.14(a 가정).
  - 상수 근거 등급은 각 줄 주석에 있다.
- 전력 판정(`effort.py`, REVIEW-09 §10):
  - 사용자 `race_results.effort`가 우선이다.
  - 없으면 평균 HR/LTHR(대회일 HRmax×0.917) 대 지속시간별 기대값과 최대 HR 도달률로 allout / submax / uncertain을 낸다. 단일 %HRmax 임계는 쓰지 않는다.
  - 이 러너의 대회 표로 검증했다(`tests/test_race_effort.py`). 전력 7건은 유지되고, 9/12(최대 이하)는 submax, 풀 1건은 uncertain이다.

**`src/metrics/prediction/__init__.py`** — 신규, 전문 그대로(1줄)

````python
"""레이스 예측 v2 — 순수 계산(core·physio)과 CalcContext 신호 수집(signals). REVIEW-07 r3."""
````

**`src/metrics/prediction/core.py`** — 신규, 전문 그대로(206줄)

````python
"""레이스 예측 v2 순수 계산 — Daniels VDOT, 앵커 감쇠, 블록 신호, 결합, 개인 내구성 지수, 마라톤(Daniels·Tanda), 범위·신뢰도.

DB·CalcContext 무의존. 모든 속도 m/s, 시간 s, 거리 m.
"""
from __future__ import annotations

import math

DECAY_PER_WEEK = 0.08    # 앵커 감쇠 VDOT/주 (6주 유예 후) — 문헌 기반 가정, 튜닝하지 않음
DECAY_GRACE_WEEKS = 6.0
K_DOWN = 0.25            # 작업구간 < 앵커일 때 하향 반영 비율
H_WEIGHT = 0.20          # HR@LTHR 신호 가중
RIEGEL_K0 = 1.06         # 개인 내구성 사전 평균
RIEGEL_TAU = 0.03        # 사전 표준편차
PAIR_SIGMA0 = 0.04       # 대회 쌍 1개의 k 관측 오차(간격 0일)
SIGMA_RACE = 0.035       # 5K~하프 중앙값 상대오차 SD (백테스트 잔차 SD 3.3~3.6%)
Z80 = 1.2816


def vdot(dist_m: float, time_s: float) -> float:
    """Daniels/Gilbert VDOT."""
    v = dist_m / (time_s / 60.0)
    tm = time_s / 60.0
    vo2 = -4.60 + 0.182258 * v + 0.000104 * v * v
    pct = 0.8 + 0.1894393 * math.exp(-0.012778 * tm) + 0.2989558 * math.exp(-0.1932605 * tm)
    return vo2 / pct


def time_for_vdot(vd: float, dist_m: float) -> float:
    """VDOT·거리 → 예상 시간(s). 이분법."""
    lo, hi = 60.0, 60000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if vdot(dist_m, mid) > vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def threshold_speed(vd: float) -> float:
    """VDOT → 60분 레이스 속도(m/s) = 역치 속도 근사."""
    lo, hi = 1000.0, 30000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if vdot(mid, 3600.0) < vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 / 3600.0


def temp_factor(temp_c: float | None, heat_pct_per_c: float, cold_pct_per_c: float) -> float:
    """기온 T에서의 속도 배율(15℃ 기준=1). heat/cold 는 음수 %/℃ (예: -0.62, -0.84)."""
    if temp_c is None:
        return 1.0
    return 1.0 + (heat_pct_per_c * max(0.0, temp_c - 15.0) + cold_pct_per_c * max(0.0, 5.0 - temp_c)) / 100.0


def vdot_at_15c(dist_m: float, time_s: float, temp_c: float | None, heat: float, cold: float) -> float:
    """기온 T에서 낸 기록을 15℃ 등가 VDOT로."""
    return vdot(dist_m, time_s * temp_factor(temp_c, heat, cold))


def time_at_temp(vd15: float, dist_m: float, temp_c: float | None, heat: float, cold: float) -> float:
    """15℃ VDOT → 기온 T에서의 예상 시간."""
    return time_for_vdot(vd15, dist_m) / temp_factor(temp_c, heat, cold)


def anchor(races: list[dict], weeks_ago_key: str = "weeks") -> dict | None:
    """races: [{"vdot15": float, "weeks": float, "activity_id": int, ...}] (전력 대회, 365일 이내).
    감쇠 적용 후 최대인 대회를 반환(원본 dict + "value")."""
    best = None
    for r in races:
        v = r["vdot15"] - max(0.0, r[weeks_ago_key] - DECAY_GRACE_WEEKS) * DECAY_PER_WEEK
        if best is None or v > best["value"]:
            best = dict(r, value=v)
    return best


def best_block(laps: list[dict], lthr: float | None, v_t: float | None, is_race: bool,
               min_d: float = 2000.0, min_t: float = 480.0) -> float | None:
    """연속 랩 블록(≥2km, ≥8분) 중 GAP-VDOT 최대. 자격: 대회이거나, 블록 평균 HR ≥ 0.92·LTHR,
    또는 블록 GAP 속도 ≥ 0.90·v_t. laps: [{"dist_m","dur_s","speed_ms","hr"}] (speed_ms=GAP 우선)."""
    best = None
    n = len(laps)
    for i in range(n):
        d = tg = tt = hrs = 0.0
        for j in range(i, n):
            lap = laps[j]
            v = lap["speed_ms"]
            if not v or v <= 0:
                break
            d += lap["dist_m"]
            tg += lap["dist_m"] / v
            tt += lap["dur_s"]
            hrs += (lap.get("hr") or 0.0) * lap["dur_s"]
            if d < min_d or tt < min_t:
                continue
            ok = is_race
            if not ok and lthr and hrs / tt >= 0.92 * lthr:
                ok = True
            if not ok and v_t and d / tg >= 0.90 * v_t:
                ok = True
            if ok:
                vd = vdot(d, tg)
                if best is None or vd > best:
                    best = vd
    return best


def combine(a: float | None, w: float | None, h: float | None) -> tuple[float | None, dict]:
    """결합 VDOT와 실제 적용 가중치. 반환 (vdot, {"race","work","hr"})."""
    if a is None and w is None:
        return (h, {"race": 0.0, "work": 0.0, "hr": 1.0}) if h is not None else (None, {})
    if a is None:
        if h is None:
            return w, {"race": 0.0, "work": 1.0, "hr": 0.0}
        return 0.6 * w + 0.4 * h, {"race": 0.0, "work": 0.6, "hr": 0.4}
    if w is None:
        core, wr, ww = a, 1.0, 0.0
    elif w >= a:
        core, wr, ww = w, 0.0, 1.0
    else:
        core, wr, ww = a + K_DOWN * (w - a), 1.0 - K_DOWN, K_DOWN
    if h is None:
        return core, {"race": wr, "work": ww, "hr": 0.0}
    return (1 - H_WEIGHT) * core + H_WEIGHT * h, {"race": round((1 - H_WEIGHT) * wr, 3),
                                                  "work": round((1 - H_WEIGHT) * ww, 3), "hr": H_WEIGHT}


def k_personal(pairs: list[dict]) -> tuple[float, float, int]:
    """개인 내구성(Riegel) 지수. pairs: [{"d1","t1","d2","t2","gap_days"}] 전력 대회 쌍(d2 ≥ 1.6·d1, 90일 이내,
    시간은 15℃ 등가). 사전 N(1.06, 0.03²)에 역분산 가중으로 수축. 반환 (k, sd, 사용 쌍 수)."""
    num = RIEGEL_K0 / RIEGEL_TAU ** 2
    den = 1.0 / RIEGEL_TAU ** 2
    used = 0
    for p in pairs:
        if p["d2"] < 1.6 * p["d1"] or p["gap_days"] > 90:
            continue
        k = math.log(p["t2"] / p["t1"]) / math.log(p["d2"] / p["d1"])
        if not 0.95 <= k <= 1.25:
            continue
        s2 = (PAIR_SIGMA0 * (1 + p["gap_days"] / 30.0)) ** 2
        num += k / s2
        den += 1.0 / s2
        used += 1
    return num / den, (1.0 / den) ** 0.5, used


def convert(vd: float, d_anchor: float, d_target: float, k: float) -> float:
    """Daniels 환산 × 개인 지수 보정: T = Daniels(vd, d_target) × (d_target/d_anchor)^(k − 1.06)."""
    return time_for_vdot(vd, d_target) * (d_target / d_anchor) ** (k - RIEGEL_K0)


def tanda_marathon(weekly_km_8w: float, train_pace_sec_km: float) -> float:
    """Tanda(2011): 마라톤 페이스 Pm = 17.1 + 140·exp(-0.0053·K) + 0.55·P (s/km). 반환 마라톤 시간(s)."""
    pm = 17.1 + 140.0 * math.exp(-0.0053 * weekly_km_8w) + 0.55 * train_pace_sec_km
    return pm * 42.195


def marathon_estimate(daniels_s: float, tanda_s: float, long_runs_28k_12w: int) -> dict:
    """중앙값 = 두 모델의 기하평균. 범위 = [min×0.98, max×1.03×(1.02 if 12주 28km+ 롱런 0회)]."""
    med = math.sqrt(daniels_s * tanda_s)
    low = min(daniels_s, tanda_s) * 0.98
    high = max(daniels_s, tanda_s) * 1.03 * (1.02 if long_runs_28k_12w == 0 else 1.0)
    return {"median_s": med, "low_s": low, "high_s": high, "model_gap_pct": abs(daniels_s - tanda_s) / med * 100}


def f_linear(x: float, x_good: float, x_bad: float, y_good: float, y_bad: float) -> float:
    if x <= x_good:
        return y_good
    if x >= x_bad:
        return y_bad
    return y_good + (y_bad - y_good) * (x - x_good) / (x_bad - x_good)


def confidence(anchor_weeks: float | None, spread_pct: float, dist_ratio: float, n_signals: int,
               model_gap_pct: float | None = None) -> tuple[float, list[str]]:
    """신뢰도(0~1)와 이유. 상한을 임의로 두지 않고 근거(앵커 최근성·신호 일치·신호 수·거리 외삽·모델 차)로만 계산."""
    reasons = []
    f_rec = 0.45 if anchor_weeks is None else f_linear(anchor_weeks, 8, 52, 1.0, 0.5)
    if anchor_weeks is None:
        reasons.append("최근 1년 전력 대회 기록 없음")
    elif anchor_weeks > 8:
        reasons.append(f"기준 대회가 {anchor_weeks:.0f}주 전")
    f_agree = f_linear(spread_pct, 3, 10, 1.0, 0.6)
    if spread_pct > 3:
        reasons.append(f"신호 간 차이 {spread_pct:.1f}%")
    f_n = {0: 0.3, 1: 0.7, 2: 0.9}.get(n_signals, 1.0)
    if n_signals < 3:
        reasons.append(f"근거 신호 {n_signals}개")
    r = max(dist_ratio, 1 / dist_ratio) if dist_ratio > 0 else 1.0
    f_dist = f_linear(r, 1.0, 4.2, 1.0, 0.75)
    if r > 1.5:
        reasons.append(f"거리 외삽 ×{r:.1f}")
    f_model = 1.0 if model_gap_pct is None else f_linear(model_gap_pct, 3, 12, 1.0, 0.5)
    if model_gap_pct is not None and model_gap_pct > 3:
        reasons.append(f"마라톤 모델 간 차이 {model_gap_pct:.1f}%")
    return round(0.9 * f_rec * f_agree * f_n * f_dist * f_model, 2), reasons


def race_range(median_s: float, conf: float, slow_extra_pct: float = 0.0) -> tuple[float, float]:
    """5K~하프 80% 범위. slow_extra_pct: 느린 쪽에만 더하는 %p(볼륨 급감·이행률 저조 등)."""
    s = SIGMA_RACE * (1 + 0.5 * (1 - conf))
    return median_s * (1 - Z80 * s), median_s * (1 + Z80 * s + slow_extra_pct / 100.0)
````

**`src/metrics/prediction/physio.py`** — 신규, 전문 그대로(65줄)

````python
"""HR 프로필 자체 추정 + 기상 보조 계산(순수 함수)."""
from __future__ import annotations

import math


def hrmax_self(activity_max_hrs: list[float]) -> float | None:
    """최근 365일 활동별 최대 HR 목록 → 두 번째로 큰 값(단일 스파이크 배제). 120 초과 205 이하만."""
    v = sorted((x for x in activity_max_hrs if x and 120 < x <= 205), reverse=True)
    if not v:
        return None
    return float(v[1] if len(v) >= 2 else v[0])


def lthr_self(race_second_part_hrs: list[tuple[float, float]]) -> float | None:
    """[(대회 공칭거리 m, 후반 2/3 평균 HR)] (최근 180일 전력 10K~하프) → 보정 후 중앙값.
    10K: ×0.98, 하프: ×1.00. 없으면 None."""
    c = []
    for dist, hr in race_second_part_hrs:
        if abs(dist - 10000) < 1:
            c.append(hr * 0.98)
        elif abs(dist - 21097.5) < 1:
            c.append(hr * 1.00)
    if not c:
        return None
    c.sort()
    m = len(c) // 2
    return c[m] if len(c) % 2 else (c[m - 1] + c[m]) / 2


def lthr_fallback(hrmax: float | None) -> float | None:
    return round(0.917 * hrmax, 1) if hrmax else None


def zones_hrr(hrmax: float, rhr: float) -> list[tuple[float, float]]:
    """Karvonen 5존 경계(bpm): 50-60, 60-70, 70-80, 80-90, 90-100 %HRR."""
    r = hrmax - rhr
    cuts = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    return [(round(rhr + r * a, 1), round(rhr + r * b, 1)) for a, b in zip(cuts, cuts[1:])]


def zones_lthr(lthr: float) -> list[tuple[float, float]]:
    """Friel 러닝 5존(%LTHR): <85, 85-90, 90-95, 95-100, ≥100."""
    cuts = [0.0, 0.85, 0.90, 0.95, 1.00]
    z = [(round(lthr * a, 1), round(lthr * b, 1)) for a, b in zip(cuts, cuts[1:])]
    return z + [(round(lthr, 1), 250.0)]


def vapor_pressure_hpa(temp_c: float, rh_pct: float) -> float:
    return rh_pct / 100.0 * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))


def wbgt_approx(temp_c: float, rh_pct: float) -> float:
    """호주 기상청(BoM) 그늘·약풍 근사: WBGT ≈ 0.567·T + 0.393·e + 3.94."""
    return 0.567 * temp_c + 0.393 * vapor_pressure_hpa(temp_c, rh_pct) + 3.94


def ambient_from_device(device_c: float) -> float:
    """손목 기기 온도 → 외기 추정. 이 러너 261개 활동 적합: device ≈ 11.0 + 0.65·ambient."""
    return (device_c - 11.0) / 0.65


def round_coord(x: float) -> float:
    """외부 전송용 좌표 정밀도 축소(소수 2자리 ≈ 1km)."""
    return round(x, 2)
````

**`src/metrics/prediction/effort.py`** — 신규, 전문 그대로(78줄)

````python
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
````

**`src/metrics/prediction/signals.py`** — 신규, 전문 그대로(100줄)

````python
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
````

**`src/metrics/prediction/core_r4.py`** — 신규, 전문 그대로(113줄)

````python
"""레이스 예측 r4 순수 계산 — 기온 환산, 개인 지구력 지수 k, 거리 외삽, 칼만 결합 결과의 범위·신뢰도, 마라톤 Tanda 결합.

DB·CalcContext 무의존. 속도 m/s, 시간 s, 거리 m. 상수 근거 등급은 REVIEW-09 §5~7((a) 문헌 (b) 데이터 (c) 휴리스틱).
"""
from __future__ import annotations

import math

from src.metrics.prediction.daniels import threshold_speed, time_for_vdot, vdot  # noqa: F401  (재노출)

Q_PER_DAY = 0.01         # (c) 체력 랜덤워크 하루 분산(VDOT²). 데이터로 식별 안 됨(0.001~0.1), 민감도 REVIEW-07 §R4-3
SIGMA_RACE = 1.0         # (b) 전력 대회 관측 SD(VDOT) — 전 관측 MLE
SIGMA_SET = 1.75         # (b) 품질 세트 관측 SD — 전 관측 MLE, 최근접 대회 잔차 SD 1.90
SIGMA_H = 1.25           # (b) 심박-속도 H 관측 SD — D-0 잔차 1.58² − 1.0²
HR_REACH_REF = 0.92      # (c) 세트 후반 최대 HR/HRmax 기준. 미달분 1%p당 분산 배율 e^0.36
HR_REACH_SLOPE = 0.36    # (b, 약함) 로그-분산 회귀 0.36 ± 0.20 (n=39)
RIEGEL_K0 = 1.06         # (a) Riegel
RIEGEL_TAU = 0.03        # (c) 개인 k 사전 SD
TANDA_SIGMA = 0.04       # (c) Tanda 식의 ln 시간 SD
ASYM_LOW_MULT = {"race": 4.0, "set": 4.0}   # (c) 섀도 변형: 현재 추정보다 낮은 관측의 분산 배율
MAINT_ALPHA = 0.14       # (a 가정) 유지 조건부 앵커: Daniels 휴식 표 4주 ≈ VDOT 93% ↔ CTL 51% → 0.07/0.49
CONF_BAND = 0.03         # 신뢰도 정의: 실제 기록이 예측 ±3% 안에 들 확률
Z80 = 1.2816             # (a) 정규 80% 구간


def temp_factor(temp_c: float | None, heat_pct_per_c: float, cold_pct_per_c: float) -> float:
    """기온 T에서의 속도 배율(15℃=1). heat/cold 는 음수 %/℃."""
    if temp_c is None:
        return 1.0
    return 1.0 + (heat_pct_per_c * max(0.0, temp_c - 15.0) + cold_pct_per_c * max(0.0, 5.0 - temp_c)) / 100.0


def vdot_at_15c(dist_m: float, time_s: float, temp_c: float | None, heat: float, cold: float) -> float:
    return vdot(dist_m, time_s * temp_factor(temp_c, heat, cold))


def time_at_temp(vd15: float, dist_m: float, temp_c: float | None, heat: float, cold: float) -> float:
    return time_for_vdot(vd15, dist_m) / temp_factor(temp_c, heat, cold)


def dlnt_dvdot(vd: float, dist_m: float) -> float:
    """VDOT 1 증가당 ln(시간) 감소량(양수)."""
    return math.log(time_for_vdot(vd - 0.5, dist_m) / time_for_vdot(vd + 0.5, dist_m))


def k_personal(races: list[dict], q: float = Q_PER_DAY) -> tuple[float, float, int]:
    """races: [{"nominal_m","vdot15","day"(정수 일)}] 전력 대회. 거리가 다른 겹치지 않는 쌍(간격 가까운 순)으로
    사전 N(1.06, 0.03²)을 역분산 갱신. 반환 (k, sd, 사용 쌍 수)."""
    cand = sorted((abs(a["day"] - b["day"]), i, j) for i, a in enumerate(races) for j, b in enumerate(races)
                  if i < j and a["nominal_m"] != b["nominal_m"])
    num, den, used, taken = RIEGEL_K0 / RIEGEL_TAU ** 2, 1.0 / RIEGEL_TAU ** 2, 0, set()
    for gap, i, j in cand:
        if i in taken or j in taken:
            continue
        s, l = sorted((races[i], races[j]), key=lambda r: r["nominal_m"])
        lr = math.log(l["nominal_m"] / s["nominal_m"])
        k = math.log(time_for_vdot(l["vdot15"], l["nominal_m"]) / time_for_vdot(s["vdot15"], s["nominal_m"])) / lr
        if not 0.95 <= k <= 1.25:
            continue
        e = dlnt_dvdot((s["vdot15"] + l["vdot15"]) / 2, l["nominal_m"])
        sk = e * math.sqrt(2 * SIGMA_RACE ** 2 + q * gap) / lr
        num += k / sk ** 2
        den += 1.0 / sk ** 2
        used += 1
        taken |= {i, j}
    return num / den, (1.0 / den) ** 0.5, used


def to_target(y: float, d_native: float, d: float, k: float, k_sd: float) -> tuple[float, float]:
    """고유 거리 d_native 의 VDOT y → 목표 거리 d 의 VDOT 와 외삽 추가 분산(k 불확실성)."""
    t = time_for_vdot(y, d) * (d / d_native) ** (k - RIEGEL_K0)
    yt = vdot(d, t)
    return yt, (k_sd * abs(math.log(d / d_native)) / dlnt_dvdot(yt, d)) ** 2


def longrun_k_sd(k_sd: float, d: float, d_native: float, longest_m: float | None) -> float:
    """목표 거리가 최근 최장 러닝보다 길면 그 외삽분에 사전 SD 를 더한 k SD(REVIEW-09 §7)."""
    if not longest_m or d <= longest_m or d <= d_native:
        return k_sd
    frac = math.log(d / longest_m) / math.log(d / d_native)
    return math.sqrt(k_sd ** 2 + (RIEGEL_TAU * frac) ** 2)


def hr_reach_mult(peak_ratio: float | None) -> float:
    """세트 후반 최대 HR/HRmax 가 기준 미달이면 관측 분산 배율(>1). HR 없으면 1."""
    if not peak_ratio:
        return 1.0
    return math.exp(HR_REACH_SLOPE * max(0.0, HR_REACH_REF - peak_ratio) * 100.0)


def summarize(x: float, var: float, d: float) -> dict:
    """칼만 상태 → 중앙값·80% 범위·예측 SD(ln 시간)·신뢰도. 대회 날 변동 SIGMA_RACE 포함."""
    sd = math.sqrt(var + SIGMA_RACE ** 2)
    e = dlnt_dvdot(x, d)
    return {"median_s": time_for_vdot(x, d), "low_s": time_for_vdot(x + Z80 * sd, d),
            "high_s": time_for_vdot(x - Z80 * sd, d), "sd_ln": e * sd, "state_sd_ln": e * math.sqrt(var),
            "confidence": round(math.erf(CONF_BAND / (e * sd * math.sqrt(2))), 2)}


def tanda_marathon(weekly_km_8w: float, train_pace_sec_km: float) -> float:
    """(a) Tanda(2011): Pm = 17.1 + 140·exp(−0.0053·K) + 0.55·P (s/km). 반환 마라톤 시간(s)."""
    return (17.1 + 140.0 * math.exp(-0.0053 * weekly_km_8w) + 0.55 * train_pace_sec_km) * 42.195


def combine_marathon(s: dict, tanda_s: float) -> dict:
    """칼만 마라톤(상태 분산)과 Tanda 를 ln 시간 역분산 결합. 대회 날 변동은 결합 후 더한다."""
    w1, w2 = 1 / s["state_sd_ln"] ** 2, 1 / TANDA_SIGMA ** 2
    mu = (w1 * math.log(s["median_s"]) + w2 * math.log(tanda_s)) / (w1 + w2)
    race_ln = math.sqrt(max(0.0, s["sd_ln"] ** 2 - s["state_sd_ln"] ** 2))
    sd = math.sqrt(1 / (w1 + w2) + race_ln ** 2)
    return {"median_s": math.exp(mu), "low_s": math.exp(mu - Z80 * sd), "high_s": math.exp(mu + Z80 * sd),
            "sd_ln": sd, "confidence": round(math.erf(CONF_BAND / (sd * math.sqrt(2))), 2),
            "tanda_weight": round(w2 / (w1 + w2), 3)}
````

**`src/metrics/prediction/signals_r4.py`** — 신규, 전문 그대로(167줄)

````python
"""예측 r4 관측 생성(순수) — 활동 목록(get_runs 형식) → 전력 대회·품질 세트·심박-속도 H·Tanda·롱런 입력.

runs 원소: get_runs(with_laps=True) dict + "ambient_c"(외기, 없으면 None) + "effort"·"official_time_s"(race_results).
세트는 GPS·시간만으로 만든다(HR 불필요). HR 은 세트 품질 배율과 H 에만 쓴다(REVIEW-09 §3·§5).
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, median

from src.metrics import segments as seg
from src.metrics.prediction.core_r4 import MAINT_ALPHA, SIGMA_RACE, SIGMA_SET, hr_reach_mult, temp_factor, vdot, vdot_at_15c
from src.metrics.prediction.effort import auto_effort
from src.metrics.prediction.daniels import equivalent_minutes, set_vdot, threshold_speed

EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running", "trail_running")
H_DAYS = 60
H_MIN_POINTS = 25
EASY_DAYS = 90
DEFAULT_V_EASY = 1000 / 360.0      # 이력 부족 시 6:00/km


def _days(d_from: str, d_to: str) -> int:
    return (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days


def allout_races(runs: list[dict], as_of: str, hrmax: float | None, heat: float, cold: float,
                 ctl_at=None, lthr: float | None = None) -> list[dict]:
    """전력 대회(365일). 사용자 확인 effort 가 최우선(allout 만 포함). 미확인이면 거리·지속시간별 자동 추정
    (`effort.classify`: 평균 HR/LTHR 대 기대값 + 최대 HR 도달률)이 allout 인 것만. uncertain 은 paced_races 로 간다.
    ctl_at(날짜)→CTL 이 주어지면 유지 조건부 앵커: VDOT × (1 − MAINT_ALPHA·max(0, 1 − CTL(기준일 전날)/CTL(대회일)))."""
    out = []
    for r in runs:
        n = r.get("nominal_m")
        if not r["is_race"] or not n or r["date"] >= as_of or _days(r["date"], as_of) > 365:
            continue
        eff = r.get("effort")
        if eff is not None and eff != "allout":
            continue
        t = r.get("official_time_s") or r["perf_time_s"]
        if eff is None and auto_effort(r, runs, hrmax) != "allout":
            continue
        v = vdot_at_15c(n, t, r.get("ambient_c"), heat, cold)
        loss = 0.0
        if ctl_at:
            c0, c1 = ctl_at(r["date"]), ctl_at(_prev_day(as_of))
            if c0 and c1:
                loss = MAINT_ALPHA * max(0.0, 1.0 - c1 / c0)
        out.append({"activity_id": r["id"], "date": r["date"], "nominal_m": n, "time_s": t,
                    "day": -_days(r["date"], as_of), "vdot15": v * (1.0 - loss), "maint_loss": round(loss, 4),
                    "auto": eff is None})
    return out


def _prev_day(d: str) -> str:
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()


def easy_speeds(runs: list[dict]) -> dict[int, float]:
    """활동별 이지 기준 속도 = 직전 90일 비대회 러닝(≥4km)의 '랩 속도 중앙값'들의 중앙값(5개 미만이면 6:00/km)."""
    meds = [(r["date"], median(b["speed_ms"] for b in r["laps"])) for r in runs
            if not r["is_race"] and r["distance_m"] >= 4000 and r.get("laps")]
    out = {}
    for r in runs:
        m = [v for d, v in meds if 0 < _days(d, r["date"]) <= EASY_DAYS]
        out[r["id"]] = median(m) if len(m) >= 5 else DEFAULT_V_EASY
    return out


def set_obs(r: dict, v_easy: float, hrmax: float | None) -> dict | None:
    """활동 1개 → 품질 세트 관측 1개(없으면 None). 기온 정규화하지 않는다(REVIEW-09 §3-3)."""
    laps = r.get("laps") or []
    if r["is_race"] or r["activity_type"] in EXCLUDE_TYPES or len(laps) < 2:
        return None
    bouts = seg.build_bouts(laps, seg.label_blocks(laps, v_easy))
    ws = seg.work_set(bouts)
    if not ws or ws["zone"] is None or ws["speed_ms"] < seg.QUALITY_CONTRAST * v_easy:
        return None
    peaks = [b["max_hr"] for b in bouts[len(bouts) // 2:] if b.get("max_hr")]
    reach = max(peaks) / hrmax if (peaks and hrmax) else None
    teq = equivalent_minutes(ws["n"], ws["rho"])
    native = {"R": 1609.344, "M": 42195.0}.get(ws["zone"], ws["speed_ms"] * teq * 60.0)
    return {"date": r["date"], "kind": ws["zone"], "y": set_vdot(ws["zone"], ws["speed_ms"], ws["n"], ws["rho"]),
            "var": SIGMA_SET ** 2 * hr_reach_mult(reach), "native_m": native, "activity_id": r["id"],
            "n": ws["n"], "rho": ws["rho"], "rep_s": ws["rep_s"], "hr_reach": reach and round(reach, 3)}


def paced_races(runs: list[dict], as_of: str, heat: float, cold: float, hrmax: float | None = None,
                lthr: float | None = None) -> list[dict]:
    """최대 이하 대회 → 하한 증거 관측(kind 'paced', 세트와 같은 분산). 사용자가 effort='paced'로 확인한 대회와,
    미확인이면서 자동 추정이 uncertain 인 대회(uncertain=True — 이유 문구로 확인 요청). 자동 submax(펀런 등)는 버린다.
    15℃ 환산은 대회와 같게 한다. 앵커(전력 대회)에서는 빠진다."""
    out = []
    for r in runs:
        n = r.get("nominal_m")
        if not (r["is_race"] and n and r["date"] < as_of and _days(r["date"], as_of) <= 365):
            continue
        t = r.get("official_time_s") or r["perf_time_s"]
        eff = r.get("effort")
        unsure = eff is None and auto_effort(r, runs, hrmax) == "uncertain"
        if eff == "paced" or unsure:
            out.append({"date": r["date"], "kind": "paced", "y": vdot_at_15c(n, t, r.get("ambient_c"), heat, cold),
                        "var": SIGMA_SET ** 2, "native_m": n, "activity_id": r["id"], "uncertain": unsure})
    return out


def observations(runs: list[dict], as_of: str, races: list[dict], hrmax: float | None,
                 paced: list[dict] | None = None) -> list[dict]:
    """전력 대회 + 최대 이하 대회(하한) + 세트 관측(날짜순, 365일). 대회 관측의 고유 거리 = 대회 거리."""
    ve = easy_speeds(runs)
    obs = [{"date": x["date"], "kind": "race", "y": x["vdot15"], "var": SIGMA_RACE ** 2, "native_m": x["nominal_m"],
            "activity_id": x["activity_id"]} for x in races] + list(paced or [])
    for r in runs:
        if r["date"] < as_of and _days(r["date"], as_of) <= 365:
            o = set_obs(r, ve[r["id"]], hrmax)
            if o:
                obs.append(o)
    return sorted(obs, key=lambda o: (o["date"], o["kind"] != "race"))


def steady_points(r: dict) -> list[tuple[float, float, float]]:
    """정상 주행 1km 랩(3번째 랩부터, HR 110~190, 3:50~7:30/km) → (hr, speed, ambient)."""
    if r["is_race"] or r["activity_type"] in EXCLUDE_TYPES or r.get("ambient_c") is None:
        return []
    out = []
    for b in (r.get("laps") or [])[2:]:
        if 900 <= b["dist_m"] <= 1100 and b["hr"] and 110 <= b["hr"] <= 190 and 1000 / 450 <= b["speed_ms"] <= 1000 / 230:
            out.append((b["hr"], b["speed_ms"], r["ambient_c"]))
    return out


def hr_signal(runs: list[dict], as_of: str, lthr: float | None, heat: float, cold: float) -> float | None:
    """최근 60일 HR–속도(15℃ 정규화) 직선의 LTHR 속도 → T 구간(60분 레이스) VDOT."""
    if not lthr:
        return None
    pts = [p for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= H_DAYS for p in steady_points(r)]
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


def h_native_m(h: float) -> float:
    return threshold_speed(h) * 3600.0


def tanda_inputs(runs: list[dict], as_of: str) -> tuple[float, float, int]:
    """(최근 8주 주평균 km, 평균 이동 페이스 s/km, 12주 내 28km+ 롱런 수)."""
    r8 = [r for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= 56]
    km = sum(r["distance_m"] for r in r8) / 1000.0
    mv = sum(r["moving_s"] for r in r8)
    long28 = sum(1 for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= 84 and r["distance_m"] >= 28000)
    return km / 8.0, (mv / km if km else 0.0), long28


def longest_run_m(runs: list[dict], as_of: str, days: int = 84) -> float | None:
    """최근 12주 최장 러닝 거리(m) — 롱런 외삽 분산 입력(REVIEW-09 §7)."""
    ds = [r["distance_m"] for r in runs if r["date"] < as_of and _days(r["date"], as_of) <= days
          and r["activity_type"] not in EXCLUDE_TYPES]
    return max(ds) if ds else None
````

**`tests/test_prediction_core.py`** — 신규, 전문 그대로(72줄)

````python
import pytest
from src.metrics.prediction.core import (vdot, time_for_vdot, threshold_speed, temp_factor, vdot_at_15c, time_at_temp, anchor,
                          best_block, combine, k_personal, convert, tanda_marathon, marathon_estimate, confidence, race_range)
from src.metrics.prediction.physio import hrmax_self, lthr_self, lthr_fallback, zones_hrr, zones_lthr, wbgt_approx, ambient_from_device

def test_vdot_roundtrip():
    assert round(vdot(10000, 2653), 1) == 46.2
    assert abs(time_for_vdot(46.2, 10000) - 2653) < 3
    assert round(threshold_speed(45.0), 3) == 3.625

def test_temp():
    assert temp_factor(15, -0.62, -0.84) == 1.0
    assert round(temp_factor(25, -0.62, -0.84), 4) == 0.938
    assert round(temp_factor(0, -0.62, -0.84), 4) == 0.958
    v = vdot_at_15c(10000, 2800, 25, -0.62, -0.84)
    assert abs(time_at_temp(v, 10000, 25, -0.62, -0.84) - 2800) < 3

def test_anchor_decay():
    a = anchor([{"vdot15": 46.2, "weeks": 20, "activity_id": 1}, {"vdot15": 43.1, "weeks": 2, "activity_id": 2}])
    assert a["activity_id"] == 1 and round(a["value"], 2) == 45.08

def test_best_block():
    laps = [{"dist_m": 1000, "dur_s": 360, "speed_ms": 1000/360, "hr": 135}] * 2 + \
           [{"dist_m": 1000, "dur_s": 272, "speed_ms": 1000/272, "hr": 168}] * 3 + \
           [{"dist_m": 1000, "dur_s": 370, "speed_ms": 1000/370, "hr": 150}]
    v = best_block(laps, lthr=177, v_t=None, is_race=False)
    assert round(v, 1) == 41.5          # 3km 13:36
    assert best_block(laps, lthr=None, v_t=None, is_race=False) is None
    assert round(best_block(laps, lthr=None, v_t=3.64, is_race=False), 1) == 41.5

def test_combine():
    v, w = combine(45.1, 43.2, 44.6)
    assert round(v, 2) == 44.62 and w == {"race": 0.6, "work": 0.2, "hr": 0.2}
    v, w = combine(45.1, 47.0, None)
    assert v == 47.0 and w["work"] == 1.0
    v, w = combine(None, 43.0, 44.0)
    assert round(v, 1) == 43.4
    assert combine(None, None, None) == (None, {})

def test_k_personal():
    k, sd, n = k_personal([])
    assert (k, n) == (1.06, 0) and round(sd, 3) == 0.03
    k, sd, n = k_personal([{"d1": 10000, "t1": 2676, "d2": 21097.5, "t2": 6147, "gap_days": 20}])
    assert n == 1 and 1.06 < k < 1.11

def test_convert_equals_daniels_at_k0():
    assert abs(convert(45.0, 10000, 42195, 1.06) - time_for_vdot(45.0, 42195)) < 1e-6

def test_marathon():
    t = tanda_marathon(42.3, 356)
    assert 13600 < t < 13800
    m = marathon_estimate(12588, 13702, 0)
    assert round(m["median_s"]) == 13133 and round(m["high_s"]) == 14395

def test_confidence_and_range():
    c, why = confidence(20, 4.3, 1.0, 3)
    assert c == 0.72 and "기준 대회가 20주 전" in why
    lo, hi = race_range(2734, c)
    assert round(lo) == 2594 and round(hi) == 2874
    c2, _ = confidence(None, 12, 4.2, 1)
    assert c2 < 0.15

def test_hr_profile():
    assert hrmax_self([193, 192, 191, 250, 110]) == 192.0
    assert round(lthr_self([(10000, 181.0), (21097.5, 182.0), (10000, 174.0)]), 1) == 177.4
    assert lthr_fallback(192) == 176.1
    assert zones_hrr(193, 43)[3] == (163.0, 178.0)
    assert zones_lthr(177)[3] == (168.2, 177.0)

def test_weather():
    assert round(wbgt_approx(25, 70), 1) == 26.8
    assert round(ambient_from_device(24.0), 1) == 20.0
````

**`tests/test_prediction_signals.py`** — 신규, 전문 그대로(36줄)

````python
"""P7-PRED-22: 예측 신호(순수)."""
from src.metrics.prediction import signals as sg
from src.metrics.prediction.core import vdot_at_15c


def _run(**k):
    base = {"id": 1, "date": "2026-08-01", "is_race": True, "nominal_m": 10000.0, "avg_hr": 176, "perf_time_s": 2700,
            "activity_type": "running", "ambient_c": 25.0, "effort": None, "official_time_s": None,
            "distance_m": 10000.0, "moving_s": 2700, "laps": []}
    base.update(k)
    return base


def test_allout_rules():
    as_of = "2026-09-26"
    assert len(sg.allout_races([_run()], as_of, 190.0, -0.62, -0.84)) == 1           # 176 ≥ 0.84×190
    assert sg.allout_races([_run(avg_hr=150)], as_of, 190.0, -0.62, -0.84) == []      # HR 미달
    assert len(sg.allout_races([_run(avg_hr=None)], as_of, 190.0, -0.62, -0.84)) == 1  # 대회 HR 없음(T0) → 전력 간주
    assert len(sg.allout_races([_run(avg_hr=150)], as_of, None, -0.62, -0.84)) == 1    # HRmax 없음(T0) → 전력 간주
    assert len(sg.allout_races([_run(avg_hr=150, effort="allout")], as_of, 190.0, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(effort="fun")], as_of, 190.0, -0.62, -0.84) == []
    r = sg.allout_races([_run(effort="allout", official_time_s=2690)], as_of, 190.0, -0.62, -0.84)[0]
    assert r["time_s"] == 2690 and r["vdot15"] == vdot_at_15c(10000.0, 2690, 25.0, -0.62, -0.84) and r["weeks"] == 8.0
    assert sg.allout_races([_run(date="2025-09-01")], as_of, 190.0, -0.62, -0.84) == []  # 52주 초과


def test_tanda_inputs():
    runs = [_run(is_race=False, date="2026-09-20", distance_m=30000.0, moving_s=9900),
            _run(is_race=False, date="2026-09-10", distance_m=10000.0, moving_s=3300)]
    km_w, pace, long28 = sg.tanda_inputs(runs, "2026-09-26")
    assert (km_w, pace, long28) == (5.0, 330.0, 1)


def test_spread_pct():
    assert sg.spread_pct([45.0], 10000.0) == 0.0
    assert round(sg.spread_pct([44.0, 46.0], 10000.0), 1) == 3.7        # (느린−빠른)/ts[n//2]
````

**`tests/test_prediction_core_r4.py`** — 신규, 전문 그대로(84줄)

````python
"""P7-PRED-20·22: Daniels 공식·강도 역산, 칼만 결합, 예측 코어(r4)."""
from src.metrics.prediction import daniels as dn
from src.metrics.prediction.core_r4 import (vdot, time_for_vdot, threshold_speed, temp_factor, vdot_at_15c, time_at_temp,
                                         k_personal, to_target, longrun_k_sd, hr_reach_mult, summarize, tanda_marathon,
                                         combine_marathon)
from src.metrics.prediction.kalman import add_obs, filter_level
from src.metrics.prediction.physio import hrmax_self, lthr_self, lthr_fallback, zones_hrr, zones_lthr, wbgt_approx, ambient_from_device


def test_daniels_formula_and_zones():
    assert round(vdot(10000, 2653), 1) == 46.2 and abs(time_for_vdot(46.2, 10000) - 2653) < 3
    assert round(time_for_vdot(50, 42195)) == 11440                 # 내장 get_race_predictions 와 같은 식
    assert round(dn.i_minutes(), 2) == 11.03 and round(dn.pct_vo2max(60), 3) == 0.888
    z = {k: (round(1000 / v) if not isinstance(v, tuple) else tuple(round(1000 / x) for x in v)) for k, v in dn.zone_speeds(45).items()}
    assert z == {"E": (382, 319), "M": 296, "T": 276, "I": 251, "R": 239}
    assert round(1000 / threshold_speed(45)) == 276


def test_set_zone_and_equivalent_minutes():
    assert [dn.set_zone(1, 1200, 0, 1200), dn.set_zone(1, 3000, 0, 3000), dn.set_zone(1, 300, 0, 300)] == ["T", "M", None]
    assert [dn.set_zone(8, 90, 2.0, 720), dn.set_zone(6, 250, 0.48, 1500), dn.set_zone(6, 300, 0.25, 1800),
            dn.set_zone(3, 100, 0.5, 300)] == ["R", "I", "T", None]
    assert dn.equivalent_minutes(1, 0.0) == 60.0 and dn.equivalent_minutes(5, 0.1) == 60.0
    assert dn.equivalent_minutes(5, 1.2) == dn.I_MIN and round(dn.equivalent_minutes(4, 0.45), 2) == 25.56
    assert round(dn.set_vdot("I", 4.0, 5, 0.6), 2) == 47.18 and round(dn.set_vdot("T", 1000 / 272, 1, 0), 2) == 45.79
    assert round(dn.set_vdot("R", 1000 / 220, 8, 2.0), 2) == 49.33 and round(dn.set_vdot("M", 1000 / 295, 1, 0), 2) == 45.21


def test_temp():
    assert temp_factor(15, -0.62, -0.84) == 1.0 and round(temp_factor(25, -0.62, -0.84), 4) == 0.938
    v = vdot_at_15c(10000, 2800, 25, -0.62, -0.84)
    assert abs(time_at_temp(v, 10000, 25, -0.62, -0.84) - 2800) < 3


def test_k_personal_disjoint_pairs():
    assert k_personal([]) == (1.06, 0.03, 0)
    r = [{"nominal_m": 10000.0, "vdot15": 45.7, "day": -160}, {"nominal_m": 21097.5, "vdot15": 43.9, "day": -180},
         {"nominal_m": 10000.0, "vdot15": 46.2, "day": -140}, {"nominal_m": 21097.5, "vdot15": 43.0, "day": -200}]
    k, sd, n = k_personal(r)
    assert n == 2 and round(k, 4) == 1.0966 and round(sd, 4) == 0.0205       # 4개 대회 → 겹치지 않는 쌍 2개


def test_distance_extrapolation():
    y, ev = to_target(45.0, 10000, 42195, 1.06, 0.03)
    assert round(y, 3) == 45.0 and round(ev, 3) == 5.431                      # k=1.06 → 값 불변, 분산만 증가
    assert round(longrun_k_sd(0.02, 42195, 10000, 24000), 4) == 0.0232       # 최장 24km 넘는 외삽분
    assert longrun_k_sd(0.02, 21097.5, 10000, 24000) == 0.02


def test_quality_multiplier():
    assert round(hr_reach_mult(0.88), 3) == 4.221 and hr_reach_mult(None) == 1.0 and hr_reach_mult(0.95) == 1.0


def test_kalman_weights_and_add():
    obs = [{"date": "2026-01-01", "y": 44, "var": 1, "kind": "race"}, {"date": "2026-02-01", "y": 46, "var": 3.0625, "kind": "T"}]
    st = filter_level(obs, "2026-03-01", 0.01)
    assert round(st["x"], 4) == 44.5664 and round(st["var"], 4) == 1.1473 and st["weights"] == {"T": 0.283, "race": 0.717}
    st2 = add_obs(st, 45, 1.5625, "H")
    assert round(st2["x"], 2) == 44.75 and st2["weights"] == {"H": 0.423, "T": 0.163, "race": 0.413}
    assert filter_level([], "2026-01-01", 0.01) is None


def test_summary_and_marathon():
    s = summarize(45.0, 1.0, 10000)
    assert round(s["median_s"]) == 2713 and round(s["low_s"]) == 2623 and round(s["high_s"]) == 2811 and s["confidence"] == 0.74
    m = combine_marathon(summarize(45.0, 1.0, 42195), 12000)
    assert round(m["median_s"]) == 12407 and m["tanda_weight"] == 0.177 and m["confidence"] == 0.77
    assert 13600 < tanda_marathon(42.3, 356) < 13800


def test_hr_profile_and_weather_helpers():
    assert hrmax_self([193, 192, 191, 250, 110]) == 192.0
    assert round(lthr_self([(10000, 181.0), (21097.5, 182.0), (10000, 174.0)]), 1) == 177.4
    assert lthr_fallback(192) == 176.1 and zones_hrr(193, 43)[3] == (163.0, 178.0) and zones_lthr(177)[3] == (168.2, 177.0)
    assert round(wbgt_approx(25, 70), 1) == 26.8 and round(ambient_from_device(24.0), 1) == 20.0


def test_kalman_low_mult_weakens_low_observations():
    from src.metrics.prediction.kalman import filter_level
    obs = [{"date": "2026-01-01", "y": 50.0, "var": 1.0, "kind": "race"},
           {"date": "2026-01-02", "y": 46.0, "var": 1.0, "kind": "race"}]
    sym = filter_level(obs, "2026-01-03", 0.01)
    asym = filter_level(obs, "2026-01-03", 0.01, {"race": 4.0, "set": 4.0})
    assert asym["x"] > sym["x"]
````

**`tests/test_prediction_signals_r4.py`** — 신규, 전문 그대로(55줄)

````python
"""P7-PRED-22: 예측 관측 생성(순수, r4)."""
from src.metrics.prediction import signals_r4 as sg
from src.metrics.prediction.core_r4 import vdot_at_15c
from src.metrics.prediction.daniels import set_vdot


def _run(**k):
    base = {"id": 1, "date": "2026-08-01", "is_race": True, "nominal_m": 10000.0, "avg_hr": 176, "perf_time_s": 2700,
            "activity_type": "running", "ambient_c": 25.0, "effort": None, "official_time_s": None,
            "distance_m": 10000.0, "moving_s": 2700, "laps": []}
    base.update(k)
    return base


def _lap(d, s, hr=None, it=None, mx=None):
    return {"dist_m": d, "dur_s": s, "speed_ms": d / s, "hr": hr, "max_hr": mx, "itype": it}


def _interval(i, date, hr_peak=180):
    laps = [_lap(2000, 720, 130, "WARMUP")]
    for _ in range(5):
        laps += [_lap(1000, 250, 165, "ACTIVE", hr_peak), _lap(300, 150, 140, "RECOVERY")]
    laps += [_lap(1500, 540, 135, "COOLDOWN")]
    return _run(id=i, date=date, is_race=False, nominal_m=None, distance_m=11000.0, moving_s=4300, laps=laps)


def test_allout_rules():
    as_of = "2026-09-26"
    assert len(sg.allout_races([_run()], as_of, 190.0, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(avg_hr=150)], as_of, 190.0, -0.62, -0.84) == []
    assert len(sg.allout_races([_run(avg_hr=None)], as_of, 190.0, -0.62, -0.84)) == 1      # T0
    assert len(sg.allout_races([_run(avg_hr=150)], as_of, None, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(effort="fun")], as_of, 190.0, -0.62, -0.84) == []
    r = sg.allout_races([_run(effort="allout", official_time_s=2690)], as_of, 190.0, -0.62, -0.84)[0]
    assert r["time_s"] == 2690 and r["vdot15"] == vdot_at_15c(10000.0, 2690, 25.0, -0.62, -0.84) and r["day"] == -56
    assert sg.allout_races([_run(date="2025-09-01")], as_of, 190.0, -0.62, -0.84) == []


def test_set_observation_device_free():
    o = sg.set_obs(_interval(2, "2026-09-10"), 1000 / 360, None)              # HR·HRmax 없음(T0)
    assert o["kind"] == "I" and o["n"] == 5 and o["rho"] == 0.6 and o["var"] == 1.75 ** 2
    assert o["y"] == set_vdot("I", 4.0, 5, 0.6)
    low = sg.set_obs(_interval(3, "2026-09-10", hr_peak=165), 1000 / 360, 192.0)  # 후반 최대 HR 0.86·HRmax → 분산 증가
    assert low["var"] > o["var"] and low["hr_reach"] == 0.859
    assert sg.set_obs(_interval(4, "2026-09-10"), 1000 / 290, None) is None      # 이지 대비 1.16배 < 1.18 → 품질 아님


def test_observations_and_inputs():
    runs = [_run(id=1, date="2026-08-01"), _interval(2, "2026-09-10"),
            _run(id=3, is_race=False, nominal_m=None, date="2026-09-20", distance_m=30000.0, moving_s=9900)]
    obs = sg.observations(runs, "2026-09-26", sg.allout_races(runs, "2026-09-26", None, -0.62, -0.84), None)
    assert [o["kind"] for o in obs] == ["race", "I"]
    km_w, pace, long28 = sg.tanda_inputs(runs, "2026-09-26")
    assert (km_w, round(pace, 2), long28) == (6.375, 331.37, 1)
    assert sg.longest_run_m(runs, "2026-09-26") == 30000.0
````

**`tests/test_race_effort.py`** — 신규, 전문 그대로(39줄)

````python
"""P7-PRED-22(r4 보강): 거리·지속시간별 전력 판정 — 이 러너 대회 값으로 검증(REVIEW-09 §10)."""
from src.metrics.prediction.effort import classify, expected_ratio

# (시간 s, 평균 HR, 최대 HR, HRmax, LTHR, 기대 판정) — 사본 DB 대회(집계값)
CASES = [
    (2757, 168, 184, 185.0, 170.7, "allout"),     # 2025-11-09 10K
    (2676, 173, 194, 191.0, 178.9, "allout"),     # 2026-04-11 10K
    (2759, 179, 187, 191.0, 177.6, "allout"),     # 2026-05-03 10K
    (2653, 165, 186, 191.0, 178.9, "allout"),     # 2026-05-09 10K PB — 평균 HR 낮으나 최대 도달
    (6756, 167, 184, 185.0, 170.8, "allout"),     # 2025-09-14 하프
    (6294, 169, 188, 187.0, 170.8, "allout"),     # 2026-03-02 하프
    (6150, 176, 191, 188.0, 180.2, "allout"),     # 2026-03-22 하프
    (2818, 163, 178, 192.0, 177.6, "submax"),     # 2026-09-12 Forest run — 사용자 확인: 최대 이하
    (3726, 139, 167, 191.0, 178.9, "submax"),     # 2026-05-10 10K 펀런
    (13332, 147, 158, 185.0, 170.8, "uncertain"), # 2025-10-18 풀 — HR 비율은 풀 기대 근처, 최대 도달 낮음 → 사용자 확인
]


def test_runner_races():
    for t, avg, mx, hmax, lthr, want in CASES:
        got, ev = classify(t, avg, mx, hmax, lthr)
        assert got == want, (t, avg, got, ev)


def test_expected_ratio_monotone_and_t0():
    assert expected_ratio(15) == 1.03 and expected_ratio(300) == 0.90
    assert expected_ratio(45) > expected_ratio(105) > expected_ratio(210)
    assert classify(2700, None, None, None)[0] == "allout"


def test_point_in_time_hrmax_and_proxy():
    from src.metrics.prediction.effort import auto_effort, hrmax_at
    runs = [{"date": f"2025-10-0{i}", "max_hr": 180} for i in range(1, 4)] + [
        {"date": "2025-10-10", "max_hr": 185}, {"date": "2025-10-20", "max_hr": 184},
        {"date": "2026-08-01", "max_hr": 193}, {"date": "2026-08-10", "max_hr": 192}]
    race = {"date": "2025-11-09", "perf_time_s": 2784, "avg_hr": 168, "max_hr": 184}
    assert hrmax_at(runs, "2025-11-09") == 184.0 and hrmax_at(runs, "2026-09-26") == 192.0
    assert auto_effort(race, runs + [race]) == "allout"                   # 대회일 HRmax 185 기준
    assert classify(2784, 168, 184, 192.0, 177.6)[0] != "allout"         # 현재 HRmax 192·자체 LTHR 177.6 을 쓰면 전력이 탈락
````

검증:
```
python3 -m pytest tests/test_prediction_core.py tests/test_prediction_signals.py tests/test_prediction_core_r4.py tests/test_prediction_signals_r4.py tests/test_race_effort.py -q
```

## P7-PRED-23 — 세션 분류기 v2(세그먼트 기반, 예측 비의존)

- 의존: P7-PRED-14, P7-PRED-21 · UI 노출: 활동 목록·상세의 "운동 유형" 라벨이 바뀐다.
  - 값 집합: easy/recovery/long_run/steady/tempo/interval/repetition/sprint/race.
  - 새 값(steady·repetition·sprint)의 라벨은 P7-PRED-74에서 붙인다.
- 실DB: 다음 메트릭 재계산 때 `workout_type_classified`가 v2로 덮인다(P7-PRED-61).
- 파일: `src/metrics/classifier.py`(**전문 교체**), `tests/test_activity_calcs.py`. TIDS는 P7-PRED-88로 분리했다.
- 입력과 출력:
  - 입력 우선순위: 랩(GAP 우선) → 스트림(시간축 복구·거리 적분) → 요약 블록 1개.
  - 이지 기준 속도 = 직전 90일 러닝의 "랩 속도 중앙값"의 중앙값(없으면 1000/360 m/s).
  - r3와 달리 `race_pred_vdot`(역치 속도)을 읽지 않는다. 분류가 예측에 의존하면 순환이 되고, 기기·PB 없이도 동작해야 하기 때문이다.
  - json: type, confidence(랩 0.8/스트림 0.6/요약 0.4), source, bouts(최대 30), sets(구간·ρ 포함), n_strides, warmup/work/rest/cooldown_s, v_easy.

**`src/metrics/classifier.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(107줄)

````python
"""Workout Classifier v2 — 세그먼트(랩 구조) 기반 세션 유형 판정(REVIEW-07 r4, REVIEW-09 §3, P7-PRED-23).

활동 전체 평균 HR·평균 페이스를 강도 판정에 쓰지 않는다. 랩(없으면 스트림)을 워밍업·작업·휴식·쿨다운으로
분해하고 작업 구간 강도·세트 수·휴식 비율로 유형을 정한다.
text_value: easy | recovery | long_run | steady | tempo | interval | repetition | sprint | race
json_value: {"type", "source", "bouts", "sets", "n_strides", "warmup_s", "work_s", "rest_s", "cooldown_s", "v_easy"}
"""
from __future__ import annotations

from statistics import median

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics import segments as seg

RUN_TYPES = ("running", "trail_running", "treadmill", "indoor_running", "virtual_running")
DEFAULT_V_EASY = 1000 / 360.0     # 6:00/km — 이력이 없을 때


class WorkoutClassifier(MetricCalculator):
    name = "workout_type_classified"
    provider = "runpulse:rule_v1"
    version = "2.0"
    scope_type = "activity"
    category = "meta"
    display_name = "운동 유형"
    description = "랩·스트림 세그먼트(작업/휴식/세트) 기반 세션 유형."
    format_type = "json"
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in RUN_TYPES:
            return []
        date = (act.get("start_time") or "")[:10]
        v_easy = self._easy_speed(ctx, date)
        blocks, source = self._blocks(ctx, act)
        if not blocks:
            return []
        labels = seg.label_blocks(blocks, v_easy)
        bouts = seg.build_bouts(blocks, labels)
        n_strides = labels.count("stride")
        total_s = act.get("moving_time_sec") or act.get("duration_sec") or 0
        total_m = act.get("distance_m") or 0
        runs = ctx.get_runs(1, end_date=date, include_end=True) if date else []
        is_race = any(r["id"] == act.get("id") and r["is_race"] for r in runs)
        typ = seg.session_type(bouts, total_s, total_m, v_easy, is_race, n_strides)
        if typ == "long":
            typ = "long_run"
        if typ == "easy" and total_m < 7000 and self._slow(blocks, v_easy):
            typ = "recovery"
        spans = {k: round(sum(b["dur_s"] for b, lab in zip(blocks, labels) if lab == k), 1)
                 for k in ("warmup", "work", "rest", "cooldown")}
        conf = {"laps": 0.8, "streams": 0.6}.get(source, 0.4)
        payload = {"type": typ, "confidence": conf, "source": source, "bouts": bouts[:30], "sets": seg.set_summary(bouts),
                   "n_strides": n_strides, **{f"{k}_s": v for k, v in spans.items()},
                   "v_easy": round(v_easy, 3)}
        return [self._result(json_val=payload, text=typ, confidence=conf)]

    @staticmethod
    def _slow(blocks: list[dict], v_easy: float) -> bool:
        d = sum(b["dist_m"] for b in blocks)
        t = sum(b["dur_s"] for b in blocks)
        return bool(t) and d / t < 0.93 * v_easy

    @staticmethod
    def _easy_speed(ctx: CalcContext, date: str) -> float:
        """직전 90일 비대회 러닝의 '랩 속도 중앙값'들의 중앙값."""
        if not date:
            return DEFAULT_V_EASY
        meds = []
        for r in ctx.get_runs(90, end_date=date, with_laps=True, include_end=False):
            if r["is_race"] or r["distance_m"] < 4000 or not r.get("laps"):
                continue
            meds.append(median(b["speed_ms"] for b in r["laps"]))
        return median(meds) if len(meds) >= 5 else DEFAULT_V_EASY

    @staticmethod
    def _summary_block(act: dict) -> list[dict]:
        """랩·스트림이 없는 활동: 활동 전체를 블록 1개로(정확도 낮음, confidence 0.4)."""
        d = act.get("distance_m") or 0
        t = act.get("moving_time_sec") or act.get("duration_sec") or 0
        if d <= 0 or t <= 0:
            return []
        return [{"dist_m": d, "dur_s": t, "speed_ms": d / t, "hr": act.get("avg_hr"),
                 "max_hr": act.get("max_hr"), "itype": None}]

    @staticmethod
    def _blocks(ctx: CalcContext, act: dict) -> tuple[list[dict], str]:
        laps = ctx.get_laps()
        blocks = []
        for lap in laps:
            d = lap.get("distance_m") or 0
            t = lap.get("duration_sec") or 0
            if d > 0 and t > 0:
                blocks.append({"dist_m": d, "dur_s": t, "speed_ms": lap.get("gap_speed_ms") or d / t,
                               "hr": lap.get("avg_hr"), "max_hr": lap.get("max_hr"), "itype": lap.get("lap_trigger")})
        if len(blocks) >= 2:
            return blocks, "laps"
        streams = ctx.get_streams()
        if len(streams) < 60:
            return WorkoutClassifier._summary_block(act), "summary"
        dur = act.get("elapsed_time_sec") or act.get("duration_sec") or act.get("moving_time_sec") or 0
        t = seg.repair_time_axis([s.get("elapsed_sec") or 0 for s in streams], dur)
        dist = [s.get("distance_m") for s in streams]
        if any(x is None for x in dist):
            dist = seg.cumulative_distance(t, [s.get("gap_speed_ms") or s.get("speed_ms") for s in streams])
        return seg.stream_to_blocks(t, dist, [s.get("heart_rate") for s in streams]), "streams"
````

**`tests/test_activity_calcs.py`** — 수정, 아래 diff 그대로 — 회복 랩을 플로트가 아닌 휴식(300m/120초)으로

````diff
--- a/tests/test_activity_calcs.py
+++ b/tests/test_activity_calcs.py
@@ -144,3 +144,29 @@
         aid = _seed_activity(conn, avg_hr=None)
         ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
         assert EfficiencyFactorCalculator().compute(ctx) == []
+
+
+class TestClassifierV2Segments:
+    """P7-PRED-23: 랩 구조 기반 v2."""
+
+    def _laps(self, conn, aid, laps):
+        for i, (d, s, hr, it) in enumerate(laps):
+            conn.execute("INSERT INTO activity_laps (activity_id, source, lap_index, distance_m, duration_sec, avg_hr, max_hr, lap_trigger)"
+                         " VALUES (?,?,?,?,?,?,?,?)", (aid, "garmin", i, d, s, hr, hr + 5, it))
+        conn.commit()
+
+    def test_interval_from_laps(self):
+        conn = _conn()
+        aid = _seed_activity(conn, distance_m=11300, moving_time_sec=4500)
+        laps = [(2000, 720, 130, "WARMUP")] + [(1000, 250, 165, "ACTIVE"), (300, 120, 140, "RECOVERY")] * 6 + [(1500, 540, 135, "COOLDOWN")]
+        self._laps(conn, aid, laps)
+        res = WorkoutClassifier().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid)))
+        data = json.loads(res[0].json_value)
+        assert res[0].text_value == "interval" and data["sets"]["n_sets"] == 6 and data["source"] == "laps"
+
+    def test_continuous_tempo_auto_laps(self):
+        conn = _conn()
+        aid = _seed_activity(conn, distance_m=7000, moving_time_sec=2350)
+        self._laps(conn, aid, [(1000, 360, 135, None), (1000, 355, 138, None)] + [(1000, 262, 170, None)] * 4 + [(1000, 370, 150, None)])
+        res = WorkoutClassifier().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid)))
+        assert res[0].text_value == "tempo"
````

검증:
```
python3 -m pytest tests/test_activity_calcs.py tests/test_mock_calcs.py -q
```

## P7-PRED-24 — HR 프로필(일별): 자체 추정과 기기 참조를 나란히, HRR·LTHR 두 존 체계

- 의존: P7-PRED-14, P7-PRED-22 · UI 노출: P7-PRED-74(프로필 카드) · 실DB: 재계산 시 생성
- 파일: `src/metrics/hr_profile.py`(신규), `tests/test_hr_profile.py`(신규), `src/metrics/engine.py`, `src/utils/metric_registry.py`, `scripts/check_docs.py`, `v0.3/data/metric_dictionary.md`(스크립트 재생성)
- 출력: `hr_profile`(numeric = 자체 LTHR, json = `{"self": {"hrmax","lthr","lthr_source": "races"|"hrmax_ratio","rhr","n_race_candidates"}, "ref": {"source","lthr","hrmax"}|null, "zones": {"self": {"hrr","lthr"}, "ref": {...}}, "lthr_gap"}`), `lthr_self`, `hrmax_self`. 기기 참조는 일별 `lthr_ref`/`hrmax_ref`(provider garmin → intervals 순)를 as_of 이전 최신으로 읽는다(P7-PRED-25가 채움).
- 전력 대회 판정: `race_results.effort`가 있으면 allout만, 없으면 `prediction.effort.auto_effort`(대회일 HRmax 비례 — 자체 LTHR 은 이 계산의 결과라 쓰지 않음, REVIEW-09 §10).
- 실측(사본 DB, 2026-09-26): 자체 HRmax 192, 자체 LTHR 177.4(대회 3건), 안정심박 44, 기기 LTHR 177 → 차이 +0.4 bpm.

**`src/metrics/hr_profile.py`** — 신규, 전문 그대로(97줄)

````python
"""HR 프로필(일별) — RunPulse 자체 추정(HRmax·LTHR·RHR)과 소스 참조값(Garmin 등)을 나란히 산출(P7-PRED-24).

produces:
  hr_profile  numeric=LTHR(자체), json={"self":{...},"ref":{...}|None,"zones":{"self":{"hrr","lthr"},"ref":{...}}}
  hrmax_self, lthr_self  numeric
소스 참조값은 metric_store daily 의 hrmax_ref / lthr_ref (provider=garmin 등, P7-PRED-25 인제스트)에서 읽는다.
"""
from __future__ import annotations

from statistics import median

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction.effort import auto_effort
from src.metrics.prediction.physio import hrmax_self, lthr_fallback, lthr_self, zones_hrr, zones_lthr

LTHR_RACE_DIST = (10000.0, 21097.5)   # LTHR 추정에 쓰는 대회 거리(전력 판정은 effort.classify)
REF_PROVIDERS = ("garmin", "intervals")


def race_second_part_hr(laps: list[dict]) -> float | None:
    """랩 HR 시간가중 평균 — 앞 1/3 랩 제외(HR 지연 구간)."""
    ls = [b for b in laps if b.get("hr")]
    if len(ls) < 6:
        return None
    sec = ls[len(ls) // 3:]
    t = sum(b["dur_s"] for b in sec)
    return sum(b["hr"] * b["dur_s"] for b in sec) / t if t else None


class HRProfileCalculator(MetricCalculator):
    name = "hr_profile"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "hr"
    display_name = "심박 프로필"
    description = "최대심박·젖산역치심박(LTHR)·안정심박과 두 존 체계(HRR·LTHR). 자체 추정과 기기 참조값을 함께 제공."
    unit = "bpm"
    format_type = "json"
    requires = []
    produces = ["hr_profile", "hrmax_self", "lthr_self"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        runs = ctx.get_runs(365, with_laps=True)
        hmax = hrmax_self([r["max_hr"] for r in runs if r["max_hr"]])
        rhrs = [w["resting_hr"] for w in ctx.get_wellness_series(30, ["resting_hr"]) if w.get("resting_hr") and 30 <= w["resting_hr"] <= 90]
        rhr = float(median(rhrs)) if rhrs else None
        confirmed = ctx.get_race_results()
        cands = []
        for r in runs:
            if r["date"] < _minus_days(day, 180) or not r["is_race"] or r["nominal_m"] not in LTHR_RACE_DIST:
                continue
            c = confirmed.get(r["id"])
            if c is not None and c["effort"] != "allout":
                continue
            # 미확인: 거리·지속시간별 자동 추정. LTHR 은 이 계산의 결과라 쓰지 않고 HRmax 비례값으로 판정(순환 방지)
            if c is None and not (hmax and r["avg_hr"] and auto_effort(r, runs, hmax) == "allout"):
                continue
            hr2 = race_second_part_hr(r.get("laps") or [])
            if hr2:
                cands.append((r["nominal_m"], hr2))
        lt = lthr_self(cands)
        lt_src = "races" if lt else "hrmax_ratio"
        if lt is None:
            lt = lthr_fallback(hmax)
        if lt is None:
            return []
        ref = self._ref(ctx, day)
        zones = {"self": {"hrr": zones_hrr(hmax, rhr) if (hmax and rhr) else None, "lthr": zones_lthr(lt)}}
        if ref:
            zones["ref"] = {"hrr": zones_hrr(ref["hrmax"], rhr) if (ref.get("hrmax") and rhr) else None,
                            "lthr": zones_lthr(ref["lthr"]) if ref.get("lthr") else None}
        payload = {"self": {"hrmax": hmax, "lthr": round(lt, 1), "lthr_source": lt_src, "rhr": rhr,
                            "n_race_candidates": len(cands)},
                   "ref": ref, "zones": zones,
                   "lthr_gap": round(lt - ref["lthr"], 1) if ref and ref.get("lthr") else None}
        conf = 0.8 if lt_src == "races" and len(cands) >= 2 else (0.6 if lt_src == "races" else 0.4)
        out = [self._result(value=round(lt, 1), json_val=payload, confidence=conf),
               self._result(value=round(lt, 1), metric_name="lthr_self", confidence=conf)]
        if hmax:
            out.append(self._result(value=hmax, metric_name="hrmax_self", confidence=0.7))
        return out

    @staticmethod
    def _ref(ctx: CalcContext, day: str) -> dict | None:
        for p in REF_PROVIDERS:
            lt = ctx.get_latest_daily_metric("lthr_ref", day, provider=p)
            hm = ctx.get_latest_daily_metric("hrmax_ref", day, provider=p)
            if lt or hm:
                return {"source": p, "lthr": lt, "hrmax": hm}
        return None


def _minus_days(day: str, n: int) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(day) - timedelta(days=n)).isoformat()
````

**`tests/test_hr_profile.py`** — 신규, 전문 그대로(45줄)

````python
"""P7-PRED-24: HR 프로필 자체 추정 + 참조값."""
import json

from src.metrics.base import CalcContext
from src.metrics.hr_profile import HRProfileCalculator, race_second_part_hr
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def _race(c, sid, date, hr_series, dist=10000.0, avg_hr=175, max_hr=192):
    aid = seed_run(c, sid=sid, date=date, name="양천 마라톤 10k", dist=dist, moving=2676, avg_hr=avg_hr, max_hr=max_hr, event_type="race")
    seed_laps(c, aid, [(1000, 268, h, None, None, h + 3) for h in hr_series])
    return aid


def test_second_part_hr():
    laps = [{"dur_s": 100, "hr": h} for h in (140, 150, 170, 180, 180, 180)]
    assert race_second_part_hr(laps) == 177.5


def test_self_profile_from_race():
    c = mem_conn()
    _race(c, "r1", "2026-04-11", [158, 163, 167, 177, 180, 179, 186, 188, 192, 191])
    seed_run(c, sid="x", date="2026-04-20", max_hr=190, avg_hr=150)
    for d in ("2026-04-01", "2026-04-02", "2026-04-03"):
        c.execute("INSERT INTO daily_wellness (date, resting_hr) VALUES (?, 43)", (d,))
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-04-25")
    res = {r.metric_name: r for r in HRProfileCalculator().compute(ctx)}
    data = json.loads(res["hr_profile"].json_value)
    assert data["self"]["hrmax"] == 190.0            # 192(대회), 190 → 두 번째
    assert data["self"]["lthr_source"] == "races"
    assert res["lthr_self"].numeric_value == round(0.98 * (180 + 179 + 186 + 188 + 192 + 191 + 177) / 7, 1)
    assert data["ref"] is None


def test_fallback_and_ref():
    c = mem_conn()
    seed_run(c, sid="a", date="2026-09-01", max_hr=192)
    seed_run(c, sid="b", date="2026-09-02", max_hr=190)
    upsert_metric(c, "daily", "2026-05-01", "lthr_ref", "garmin", numeric_value=177.0)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")
    data = json.loads({r.metric_name: r for r in HRProfileCalculator().compute(ctx)}["hr_profile"].json_value)
    assert data["self"]["lthr"] == 174.2 and data["self"]["lthr_source"] == "hrmax_ratio"
    assert data["ref"] == {"source": "garmin", "lthr": 177.0, "hrmax": None} and data["lthr_gap"] == -2.8
    assert data["zones"]["ref"]["lthr"][3] == [168.2, 177.0] or tuple(data["zones"]["ref"]["lthr"][3]) == (168.2, 177.0)
````

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -34,4 +34,5 @@
 from src.metrics.di import DICalculator
 from src.metrics.darp import DARPCalculator
+from src.metrics.hr_profile import HRProfileCalculator
 from src.metrics.tids import TIDSCalculator
 from src.metrics.rmr import RMRCalculator
@@ -90,4 +91,5 @@
     CIRSCalculator(),
     DICalculator(),
+    HRProfileCalculator(),
     DARPCalculator(),
     TIDSCalculator(),
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -321,4 +321,7 @@
     MetricDef("gap_rp", "capacity", "metric", "sec/km", "RunPulse GAP (경사 보정 페이스)"),
     MetricDef("runpulse_vdot", "capacity", "metric", "", "RunPulse VDOT (Daniels)"),
+    MetricDef("hr_profile", "hr", "metric", "bpm", "HR 프로필(자체·참조 HRmax/LTHR, HRR·LTHR 존)", scope="daily"),
+    MetricDef("hrmax_self", "hr", "metric", "bpm", "RunPulse 추정 최대심박", scope="daily"),
+    MetricDef("lthr_self", "hr", "metric", "bpm", "RunPulse 추정 LTHR", scope="daily"),
     MetricDef("fearp", "capacity", "metric", "sec/km", "Field-Equivalent Adjusted Running Pace"),
     MetricDef("critical_power", "capacity", "metric", "W", "Critical Power (CP)", scope="daily"),
````

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 32 → 33

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 32개)
+        # ALL_CALCULATORS 수 검증 (설계: 33개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 32:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 32개)")
+            if len(ALL_CALCULATORS) != 33:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 33개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 32개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 33개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

그다음 `python3 scripts/gen_metric_dictionary.py`로 `v0.3/data/metric_dictionary.md`를 재생성한다(손으로 고치지 않는다).

검증:
```
python3 -m pytest tests/test_hr_profile.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-25 — Garmin 참조값 동기화: LTHR·역치속도 스냅샷 + 레이스 예측 스냅샷·이력 백필 (경로 (a) 인제스트)

- 의존: P7-PRED-11 · UI 노출: P7-PRED-72(Garmin 행), P7-PRED-74(기기 LTHR) · **실DB: P7-PRED-61 5단계에서 사용자가 이력 백필 실행(Garmin API 호출)**
- 파일: `src/sync/garmin_ref_parsers.py`, `src/sync/garmin_ref_sync.py`(신규), `src/sync/garmin_daily_extensions.py`, `tests/test_garmin_ref_parsers.py`, `tests/test_garmin_ref_sync.py`(신규), `src/utils/metric_registry.py`
- 왜: 기존 LT 파서는 `lactateThresholdHeartRate.heartRate`를 찾지만 실제 payload는 `speed_and_heart_rate.heartRate`·`power.functionalThresholdPower`라 **garmin_lthr·garmin_ftp가 0건**이다(REVIEW-08 R3-6). 레이스 예측은 스냅샷 2개뿐이다. `garminconnect`는 `get_race_predictions(startdate, enddate, _type)`와 `get_lactate_threshold(latest=False, start_date, end_date, aggregation)`를 제공한다(설치본 시그니처 확인). **이력 응답 형태는 미확인(가정: 스냅샷 dict의 리스트)** — 파싱 0건이면 raw만 `source_payloads`에 남기고 결과에 `*_parsed: 0`으로 보고한다.
- 저장: 일별 `metric_store`, provider `garmin`: `lthr_ref`, `lt_speed_ref`(= speed × 10 m/s — **가정**, 0.38055 → 3.806 m/s = 4:23/km. 첫 실동기화 후 역치 페이스와 대조), `garmin_ftp`, `race_pred_{5k,10k,half,marathon}_sec`. 측정일(`calendarDate`) 기준으로 저장한다(동기화일 아님).

**`src/sync/garmin_ref_parsers.py`** — 신규, 전문 그대로(52줄)

````python
"""Garmin 참조값 파서(순수) — 젖산역치(LTHR·역치속도·FTP)와 레이스 예측 payload → 날짜별 값(P7-PRED-25).

실측 payload 형태(2026-05 저장본):
  lactate_threshold: {"speed_and_heart_rate": {"calendarDate": "2026-05-01T17:56:58.483", "heartRate": 177,
                      "speed": 0.38055}, "power": {"calendarDate": ..., "functionalThresholdPower": 313}}
  race_predictions : {"calendarDate": "2026-05-11", "time5K": 1201, "time10K": 2585, "timeHalfMarathon": 5847,
                      "timeMarathon": 12849}
이력 조회(latest=False / startdate~enddate) 응답은 위 dict 의 리스트라고 가정한다(가정 — 첫 실동기화에서 raw 로 확인).
"""
from __future__ import annotations

LT_SPEED_SCALE = 10.0   # 가정: Garmin speed 0.38055 → 3.8055 m/s (4:23/km). 첫 실데이터에서 역치 페이스와 대조 확인
RACE_KEYS = {"time5K": "race_pred_5k_sec", "time10K": "race_pred_10k_sec",
             "timeHalfMarathon": "race_pred_half_sec", "timeMarathon": "race_pred_marathon_sec"}


def _day(v) -> str | None:
    return str(v)[:10] if v else None


def parse_lactate_threshold(payload, fallback_date: str) -> list[dict]:
    """→ [{"date", "lthr_ref", "lt_speed_ref", "ftp"}] (값 없는 키는 None). 알 수 없는 형태면 []."""
    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        shr = it.get("speed_and_heart_rate") or it.get("lactateThresholdHeartRate") or it
        pw = it.get("power") or {}
        hr = shr.get("heartRate") if isinstance(shr, dict) else None
        sp = shr.get("speed") if isinstance(shr, dict) else None
        ftp = pw.get("functionalThresholdPower") if isinstance(pw, dict) else None
        if hr is None and sp is None and ftp is None:
            continue
        out.append({"date": _day(shr.get("calendarDate")) or fallback_date,
                    "lthr_ref": float(hr) if hr else None,
                    "lt_speed_ref": round(sp * LT_SPEED_SCALE, 4) if sp else None,
                    "ftp": float(ftp) if ftp else None})
    return out


def parse_race_predictions(payload, fallback_date: str) -> list[dict]:
    """→ [{"date", "race_pred_5k_sec", ...}] — 값이 하나도 없는 항목은 제외."""
    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        vals = {m: float(it[k]) for k, m in RACE_KEYS.items() if it.get(k)}
        if vals:
            out.append({"date": _day(it.get("calendarDate")) or fallback_date, **vals})
    return out
````

**`src/sync/garmin_ref_sync.py`** — 신규, 전문 그대로(85줄)

````python
"""Garmin 참조값 동기화(P7-PRED-25) — 젖산역치(LTHR·역치속도) 일별 스냅샷, 레이스 예측 일별 스냅샷 + 이력 백필.

저장: metric_store daily, provider='garmin' — lthr_ref, lt_speed_ref, garmin_ftp, race_pred_{5k,10k,half,marathon}_sec.
원본은 source_payloads(entity_type 'lactate_threshold_day' / 'race_predictions' / 이력은 '*_range') 에 보존.
API 실패는 로그 후 0 반환(동기화 중단 금지). client 는 garminconnect.Garmin (테스트는 가짜 객체).
"""
from __future__ import annotations

import logging
import sqlite3

from src.sync.garmin_helpers import _store_raw_payload
from src.sync.garmin_ref_parsers import parse_lactate_threshold, parse_race_predictions
from src.utils.db_helpers import upsert_metric

log = logging.getLogger(__name__)
RACE_METRICS = ("race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec")


def _store_lt(conn, items: list[dict]) -> int:
    n = 0
    for it in items:
        for name, key in (("lthr_ref", "lthr_ref"), ("lt_speed_ref", "lt_speed_ref"), ("garmin_ftp", "ftp")):
            if it.get(key) is not None:
                upsert_metric(conn, "daily", it["date"], name, "garmin", numeric_value=it[key])
                n += 1
    return n


def _store_rp(conn, items: list[dict]) -> int:
    n = 0
    for it in items:
        for name in RACE_METRICS:
            if it.get(name) is not None:
                upsert_metric(conn, "daily", it["date"], name, "garmin", numeric_value=it[name])
                n += 1
    return n


def sync_lactate_threshold(conn: sqlite3.Connection, client, date_str: str) -> int:
    """최신 LT 스냅샷(측정일 기준 저장). 반환: 저장한 값 수."""
    try:
        raw = client.get_lactate_threshold()
    except Exception as e:
        log.warning("garmin lactate_threshold 실패 %s: %s", date_str, e)
        return 0
    if not raw:
        return 0
    _store_raw_payload(conn, "lactate_threshold_day", date_str, raw)
    return _store_lt(conn, parse_lactate_threshold(raw, date_str))


def sync_race_predictions(conn: sqlite3.Connection, client, date_str: str) -> int:
    """오늘 레이스 예측 스냅샷."""
    try:
        raw = client.get_race_predictions()
    except Exception as e:
        log.warning("garmin race_predictions 실패 %s: %s", date_str, e)
        return 0
    if not raw:
        return 0
    _store_raw_payload(conn, "race_predictions", date_str, raw)
    return _store_rp(conn, parse_race_predictions(raw, date_str))


def backfill_history(conn: sqlite3.Connection, client, start: str, end: str) -> dict:
    """이력 백필: get_race_predictions(start, end, 'daily'), get_lactate_threshold(latest=False, ...).
    응답 형태는 리스트라고 가정(가정) — 파싱 0건이면 raw 만 남기고 {"*_parsed": 0} 로 보고한다."""
    out = {"race_parsed": 0, "lt_parsed": 0}
    try:
        raw = client.get_race_predictions(start, end, "daily")
        if raw:
            _store_raw_payload(conn, "race_predictions_range", f"{start}_{end}", raw)
            out["race_parsed"] = _store_rp(conn, parse_race_predictions(raw, end))
    except Exception as e:
        log.warning("garmin race_predictions 이력 실패: %s", e)
    try:
        raw = client.get_lactate_threshold(latest=False, start_date=start, end_date=end)
        if raw:
            _store_raw_payload(conn, "lactate_threshold_range", f"{start}_{end}", raw)
            out["lt_parsed"] = _store_lt(conn, parse_lactate_threshold(raw, end))
    except Exception as e:
        log.warning("garmin lactate_threshold 이력 실패: %s", e)
    conn.commit()
    return out
````

**`src/sync/garmin_daily_extensions.py`** — 수정, 아래 diff 그대로 — 기존 LT 블록·레이스 예측 본문을 새 모듈 호출로 교체

````diff
--- a/src/sync/garmin_daily_extensions.py
+++ b/src/sync/garmin_daily_extensions.py
@@ -8,6 +8,7 @@
 
 from src.utils.db_helpers import upsert_metric
 from src.sync.garmin_helpers import _store_raw_payload, _upsert_daily_detail_metric
+from src.sync.garmin_ref_sync import sync_lactate_threshold, sync_race_predictions
 
 if TYPE_CHECKING:
     from garminconnect import Garmin
@@ -18,31 +19,8 @@
     client: "Garmin",
     date_str: str,
 ) -> None:
-    """Garmin 레이스 예측 시간 → daily_detail_metrics."""
-    try:
-        data = client.get_race_predictions()
-    except Exception as e:
-        print(f"[garmin] race_predictions 실패 {date_str}: {e}")
-        return
-
-    if not data:
-        return
-
-    _store_raw_payload(conn, "race_predictions", date_str, data)
-
-    predictions = data if isinstance(data, dict) else {}
-    metrics = {
-        "race_pred_5k_sec": predictions.get("time5K"),
-        "race_pred_10k_sec": predictions.get("time10K"),
-        "race_pred_half_sec": predictions.get("timeHalfMarathon"),
-        "race_pred_marathon_sec": predictions.get("timeMarathon"),
-    }
-    for k, v in metrics.items():
-        if v is not None:
-            try:
-                _upsert_daily_detail_metric(conn, date_str, k, metric_value=float(v))
-            except (TypeError, ValueError):
-                pass
+    """Garmin 레이스 예측 스냅샷 → metric_store daily(provider garmin). 파싱은 garmin_ref_sync(P7-PRED-25)."""
+    sync_race_predictions(conn, client, date_str)
 
 
 def sync_daily_training_status(
@@ -159,24 +137,8 @@
     except Exception:
         pass
 
-    # Lactate Threshold (글로벌 값 — 날짜별 API 없음, 당일 date_str로 저장)
-    try:
-        lt = client.get_lactate_threshold()
-        if lt:
-            _store_raw_payload(conn, "lactate_threshold_day", date_str, lt)
-            ftp = lt.get("functionalThresholdPower")
-            lthr_dto = lt.get("lactateThresholdHeartRate") or {}
-            lthr = lthr_dto.get("heartRate") or lt.get("heartRate")
-            if ftp is not None:
-                _upsert_daily_detail_metric(
-                    conn, date_str, "garmin_ftp", metric_value=float(ftp)
-                )
-            if lthr is not None:
-                _upsert_daily_detail_metric(
-                    conn, date_str, "garmin_lthr", metric_value=float(lthr)
-                )
-    except Exception:
-        pass
+    # Lactate Threshold — 측정일 기준 lthr_ref·lt_speed_ref·garmin_ftp (P7-PRED-25; 기존 파싱은 키 경로 오류로 0건)
+    sync_lactate_threshold(conn, client, date_str)
 
 
 def sync_daily_user_summary(
````

**`tests/test_garmin_ref_parsers.py`** — 신규, 전문 그대로(25줄)

````python
"""P7-PRED-25: Garmin 참조값 파서."""
from src.sync.garmin_ref_parsers import parse_lactate_threshold, parse_race_predictions

LT = {"speed_and_heart_rate": {"calendarDate": "2026-05-01T17:56:58.483", "heartRate": 177, "speed": 0.38055449},
      "power": {"calendarDate": "2026-05-01T17:56:58.750", "functionalThresholdPower": 313}}
RP = {"calendarDate": "2026-05-11", "time5K": 1201, "time10K": 2585, "timeHalfMarathon": 5847, "timeMarathon": 12849}


def test_lt_latest_shape():
    assert parse_lactate_threshold(LT, "2026-05-11") == [
        {"date": "2026-05-01", "lthr_ref": 177.0, "lt_speed_ref": 3.8055, "ftp": 313.0}]


def test_lt_history_list_and_garbage():
    assert len(parse_lactate_threshold([LT, LT, "x"], "2026-05-11")) == 2
    assert parse_lactate_threshold({"foo": 1}, "2026-05-11") == []
    assert parse_lactate_threshold(None, "2026-05-11") == []


def test_race_predictions_latest_and_history():
    assert parse_race_predictions(RP, "2026-05-12") == [
        {"date": "2026-05-11", "race_pred_5k_sec": 1201.0, "race_pred_10k_sec": 2585.0,
         "race_pred_half_sec": 5847.0, "race_pred_marathon_sec": 12849.0}]
    h = parse_race_predictions([dict(RP, calendarDate="2026-05-10"), {"calendarDate": "2026-05-09"}], "x")
    assert [x["date"] for x in h] == ["2026-05-10"]
````

**`tests/test_garmin_ref_sync.py`** — 신규, 전문 그대로(41줄)

````python
"""P7-PRED-25: Garmin 참조값 동기화(가짜 클라이언트)."""
from src.sync.garmin_ref_sync import backfill_history, sync_lactate_threshold, sync_race_predictions
from tests.helpers_pred import mem_conn
from tests.test_garmin_ref_parsers import LT, RP


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail

    def get_lactate_threshold(self, latest=True, start_date=None, end_date=None, aggregation="daily"):
        if self.fail:
            raise RuntimeError("401")
        return LT if latest else [LT]

    def get_race_predictions(self, startdate=None, enddate=None, _type=None):
        if self.fail:
            raise RuntimeError("401")
        return RP if startdate is None else [dict(RP, calendarDate="2026-05-10"), RP]


def _val(c, name, day):
    r = c.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name=? "
                  "AND provider='garmin'", (day, name)).fetchone()
    return r and r[0]


def test_snapshots():
    c = mem_conn()
    assert sync_lactate_threshold(c, FakeClient(), "2026-05-11") == 3
    assert _val(c, "lthr_ref", "2026-05-01") == 177.0 and _val(c, "lt_speed_ref", "2026-05-01") == 3.8055
    assert sync_race_predictions(c, FakeClient(), "2026-05-11") == 4
    assert _val(c, "race_pred_5k_sec", "2026-05-11") == 1201.0


def test_history_and_failure():
    c = mem_conn()
    assert backfill_history(c, FakeClient(), "2026-05-01", "2026-05-11") == {"race_parsed": 8, "lt_parsed": 3}
    assert _val(c, "race_pred_10k_sec", "2026-05-10") == 2585.0
    assert sync_race_predictions(c, FakeClient(fail=True), "2026-05-11") == 0
    assert backfill_history(c, FakeClient(fail=True), "2026-05-01", "2026-05-11") == {"race_parsed": 0, "lt_parsed": 0}
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -324,4 +324,8 @@
     MetricDef("hrmax_self", "hr", "metric", "bpm", "RunPulse 추정 최대심박", scope="daily"),
     MetricDef("lthr_self", "hr", "metric", "bpm", "RunPulse 추정 LTHR", scope="daily"),
+    MetricDef("lthr_ref", "hr", "metric", "bpm", "기기 제공 LTHR(참조)", scope="daily"),
+    MetricDef("hrmax_ref", "hr", "metric", "bpm", "기기/설정 최대심박(참조)", scope="daily"),
+    MetricDef("lt_speed_ref", "hr", "metric", "m/s", "기기 제공 역치 속도(참조)", scope="daily"),
+    MetricDef("garmin_ftp", "capacity", "metric", "W", "Garmin 러닝 FTP", scope="daily"),
     MetricDef("fearp", "capacity", "metric", "sec/km", "Field-Equivalent Adjusted Running Pace"),
     MetricDef("critical_power", "capacity", "metric", "W", "Critical Power (CP)", scope="daily"),
````

검증:
```
python3 -m pytest tests/test_garmin_ref_parsers.py tests/test_garmin_ref_sync.py tests/test_doc_sync.py -q
python3 scripts/gen_metric_dictionary.py
python3 scripts/check_data_consistency.py
```

