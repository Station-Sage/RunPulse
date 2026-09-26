# PRED-5x — 레이스 예측 v2 (경로 b·c, 개인 내구성, 마라톤) (예측 리뉴얼 r3)

근거: `REVIEW-07-prediction-renewal.md` r3 §3·4, Q1·Q4·Q9. 경로 (a) Garmin 인제스트는 P7-PRED-25.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-51 — DARP: r3 (b)(c) 기본 표시 + r4 섀도 2종(후보, 스냅샷·전향 평가용)

- 의존: P7-PRED-14, P7-PRED-20, P7-PRED-22, P7-PRED-24, P7-PRED-25(경로 b 참조값), P7-PRED-33
- UI 노출: Today 레이스 허브 예측값·범위(기존 `race_pred_*` primary 경로 = r3 (c)) + P7-PRED-72(섀도는 "후보" 행)
- 실DB: 재계산 시 교체(P7-PRED-61)
- 파일: `src/metrics/darp.py`(**전문 교체**, r3), `src/metrics/darp_r4.py`(신규, r4 섀도), `tests/test_darp_v2.py`, `tests/test_darp_r4.py`(신규), `src/metrics/engine.py`, `src/utils/metric_registry.py`, `scripts/check_docs.py`, `tests/test_metric_naming.py`, `tests/test_validator.py`
- **사용자 결정(2026-09-26)**: r3 (c) 기본 표시 유지, r4는 섀도로 병행 계산, 전환은 전향 평가(P7-PRED-63) 뒤 사용자 결정(REVIEW-07 §R4-8(4)).
- r3 (`darp.py`, REVIEW-07 §0·§4). 전력 판정만 r4 보강(`effort.auto_effort`)을 쓴다.
  - 결합: 대회 앵커(15℃, 6주 유예 후 주 0.08 감쇠), 작업 블록 W, H를 `W ≥ A → W, 아니면 A + 0.25(W−A)`, `0.8·core + 0.2·H`로 합친다.
  - 거리 환산: 개인 k(최근 26주 대회 쌍, 사전 N(1.06, 0.03²)).
  - 마라톤: Daniels·Tanda 기하평균. 신뢰도는 곱셈식이다.
  - 경로: `DARPCalculator`(name `darp`, `runpulse:formula_v1`, 자체 HRmax·LTHR), `DARPRefCalculator`(name `darp_ref`, `runpulse:ref_garmin`, 기기 LTHR·HRmax(없으면 LTHR/0.917), 기기 LTHR 없으면 빈 결과).
- r4 섀도 (`darp_r4.py`, REVIEW-09, REVIEW-07 §R4-2·§R4-8):
  - 관측: 전력 대회·최대 이하 대회(하한)·품질 세트·H.
  - 결합: 목표 거리마다 외삽(개인 k, 외삽 분산)한 뒤 로컬 레벨 칼만(q=0.01/일)으로 합친다.
  - 마라톤: Tanda를 ln 시간 역분산으로 결합한다.
  - 범위·신뢰도: 80% 범위 = ±1.2816·√(P+σ대회²), 신뢰도 = erf(0.03/(e_d·SD·√2)).
  - `DARPShadowCalculator`: name `darp_r4`, provider `runpulse:shadow_r4`, variant base.
  - `DARPShadowAsymCalculator`: name `darp_r4_asym`, provider `runpulse:shadow_r4_asym`, variant asym_maint. 낮은 관측 분산 ×4, 유지 조건부 앵커 α 0.14, requires ctl.
  - 섀도 provider는 `metric_priority` 표에 없어(우선순위 999) **is_primary가 되지 않는다**. 전환하려면 별도 유닛에서 provider를 바꾼다.
- 결과(사본 DB, 2026-09-26, effort 입력 없음, 15℃). 수용 백테스트 n=7(in-sample): r3 D-0 1.39 / D-28 2.16, r4 1.39 / 1.79, r4 asym 1.26 / 1.46.

| 경로 | 5K | 10K | 하프 | 마라톤 |
|---|---|---|---|---|
| r3 (c) | 22:01 | 45:39 | 1:41:11 | 3:40:38 |
| r3 (b) | 22:02 | 45:41 | 1:41:15 | 3:40:42 |
| r4 섀도 | 22:07 | 46:15 | 1:43:31 | 3:42:11 |
| r4 asym | 21:50 | 45:42 | 1:42:15 | 3:40:18 |

**`src/metrics/darp.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(140줄)

````python
"""DARP v2 레이스 예측 — 앵커 대회(15℃ 정규화·감쇠) + 작업 블록 + HR@LTHR 결합, 개인 내구성 지수, 마라톤 Daniels·Tanda.

두 경로를 같은 로직으로 산출한다(P7-PRED-51):
  (c) runpulse:formula_v1  — HRmax·LTHR 모두 RunPulse 자체 추정(hr_profile)
  (b) runpulse:ref_garmin  — HRmax·LTHR 에 기기 참조값(hrmax_ref/lthr_ref) 사용
HR 이 전혀 없으면(T0) W 는 역치 속도 기준, H 는 생략된다.
"""
from __future__ import annotations

import json

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import core as pc
from src.metrics.prediction import signals as sg

TARGETS = {"race_pred_5k_sec": 5000.0, "race_pred_10k_sec": 10000.0, "race_pred_half_sec": 21097.5,
           "race_pred_marathon_sec": 42195.0}
DEFAULT_HEAT, DEFAULT_COLD = -0.62, -0.84
TEMP_TABLE = (5, 10, 15, 20, 25, 30)
BE_DAYS = 90             # 5K best effort(구간 기록) 조회 창
TANDA_MIN_KM_WEEK = 15.0   # 가정: 주 15km 미만이면 Tanda 식 적용 범위 밖(원 논문 표본 주 20~130km)


class DARPCalculator(MetricCalculator):
    name = "darp"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "prediction"
    display_name = "레이스 예측 (DARP)"
    description = "최근 전력 대회·작업 구간·심박-속도 관계를 결합한 레이스 시간 예측(15℃ 기준, 80% 범위·신뢰도 포함)."
    unit = "sec"
    format_type = "time"
    higher_is_better = False
    decimal_places = 0
    requires = ["hr_profile", "heat_model"]
    produces = ["race_pred_vdot", *TARGETS]
    path = "c"

    def hr_refs(self, ctx: CalcContext, day: str) -> tuple[float | None, float | None]:
        _, js = ctx.get_latest_daily_metric("hr_profile", day, provider="runpulse:formula_v1", include_json=True)
        s = json.loads(js)["self"] if js else {}
        return s.get("hrmax"), s.get("lthr")

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        hrmax, lthr = self.hr_refs(ctx, day)
        _, hj = ctx.get_latest_daily_metric("heat_model", day, include_json=True)
        hm = json.loads(hj) if hj else {}
        heat, cold = hm.get("heat", DEFAULT_HEAT), hm.get("cold", DEFAULT_COLD)
        runs = ctx.get_runs(365, with_laps=True, include_end=False)
        confirmed = ctx.get_race_results()
        for r in runs:
            r["ambient_c"] = ctx.get_activity_metric(r["id"], "weather_temp_c")
            c = confirmed.get(r["id"])
            r["effort"] = c["effort"] if c else None
            r["official_time_s"] = c["official_time_sec"] if c else None
        races = sg.allout_races(runs, day, hrmax, heat, cold, lthr)
        a = pc.anchor(races)
        av = a["value"] if a else None
        v_t = pc.threshold_speed(av) if av else None
        w, w_id = sg.work_signal(runs, day, lthr, v_t)
        h = sg.hr_signal(runs, day, lthr, heat, cold)
        vd, weights = pc.combine(av, w, h)
        if vd is None:
            return []
        k, k_sd, k_n = pc.k_personal(sg_pairs(races))
        d_anchor = a["nominal_m"] if a else 10000.0
        signals = [x for x in (av, w, h) if x]
        km_w, pace, long28 = sg.tanda_inputs(runs, day)
        base = {"path": self.path, "vdot15": round(vd, 2), "weights": weights,
                "anchor": a and {"activity_id": a["activity_id"], "date": a["date"], "vdot15": round(a["vdot15"], 2),
                                 "value": round(av, 2), "weeks": round(a["weeks"], 1)},
                "work": w and {"vdot": round(w, 2), "activity_id": w_id}, "hr": h and round(h, 2),
                "hrmax": hrmax, "lthr": lthr, "k": round(k, 3), "k_sd": round(k_sd, 3), "k_pairs": k_n,
                "heat": heat, "cold": cold}
        out = [self._result(value=round(vd, 2), metric_name="race_pred_vdot", json_val=base)]
        be5 = ctx.get_best_efforts(BE_DAYS, "5K", end_date=day)
        be5_v = pc.vdot(5000.0, be5[0]["elapsed_s"]) if be5 else None     # 기온 미정규화·구간 기록 → 일치도 신호로만
        for name, dist in TARGETS.items():
            med = pc.convert(vd, d_anchor, dist, k)
            sig = signals + ([be5_v] if dist == 5000.0 and be5_v else [])
            extra, mar = {}, None
            if dist == 42195.0 and pace and km_w >= TANDA_MIN_KM_WEEK:
                mar = pc.marathon_estimate(med, pc.tanda_marathon(km_w, pace), long28)
                med, extra = mar["median_s"], {"daniels_s": round(pc.convert(vd, d_anchor, dist, k)),
                                               "tanda_s": round(pc.tanda_marathon(km_w, pace)),
                                               "weekly_km_8w": round(km_w, 1), "long_runs_28k_12w": long28}
            conf, reasons = pc.confidence(a["weeks"] if a else None, sg.spread_pct(sig, dist),
                                          dist / d_anchor, len(sig), mar and mar["model_gap_pct"])
            short_volume = dist == 42195.0 and mar is None
            if short_volume:
                conf = round(conf * 0.8, 2)         # 볼륨 근거 부재 → 모델 간 교차검증 불가분만큼 감점(가정)
                reasons.append(f"최근 8주 주평균 {km_w:.0f}km — 볼륨 기반 모델 적용 불가")
            lo, hi = (mar["low_s"], mar["high_s"]) if mar else pc.race_range(med, conf, 3.0 if short_volume else 0.0)
            js = {"low_s": round(lo), "high_s": round(hi), "confidence": conf, "reasons": reasons,
                  "contributions": weights, "path": self.path, "temp_c_basis": 15, **extra,
                  "by_temp": {str(t): round(med / pc.temp_factor(t, heat, cold)) for t in TEMP_TABLE},
                  "signals_s": {k2: round(pc.time_for_vdot(v, dist)) for k2, v in
                                (("race", av), ("work", w), ("hr", h), ("best_effort", be5_v if dist == 5000.0 else None)) if v}}
            out.append(self._result(value=round(med), metric_name=name, json_val=js, confidence=conf))
        return out


class DARPRefCalculator(DARPCalculator):
    """(b) 경로 — 기기 참조 HRmax·LTHR. 참조값이 없으면 산출하지 않는다(빈 리스트)."""
    name = "darp_ref"
    provider = "runpulse:ref_garmin"
    display_name = "레이스 예측 (기기 심박 기준)"
    description = "DARP 와 같은 로직에 기기(Garmin 등)가 제공한 최대심박·LTHR 을 넣은 비교용 예측."
    path = "b"

    def hr_refs(self, ctx: CalcContext, day: str) -> tuple[float | None, float | None]:
        _, js = ctx.get_latest_daily_metric("hr_profile", day, provider="runpulse:formula_v1", include_json=True)
        ref = (json.loads(js).get("ref") or {}) if js else {}
        lthr = ref.get("lthr")
        hrmax = ref.get("hrmax") or (round(lthr / 0.917, 1) if lthr else None)   # 기기 HRmax 미제공 → LTHR/0.917
        return hrmax, lthr

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        hrmax, lthr = self.hr_refs(ctx, ctx.scope_id)
        return super().compute(ctx) if lthr else []


K_WINDOW_WEEKS = 26.0     # 개인 내구성 지수에 쓰는 대회 쌍: 최근 180일(백테스트 35 와 동일)


def sg_pairs(races: list[dict]) -> list[dict]:
    """전력 대회 목록 → k_personal 입력 쌍(짧은 거리 d1 < 긴 거리 d2, 15℃ 등가 시간, 최근 26주)."""
    pairs = []
    races = [r for r in races if r["weeks"] <= K_WINDOW_WEEKS]
    for i, x in enumerate(races):
        for y in races[i + 1:]:
            s, l = (x, y) if x["nominal_m"] < y["nominal_m"] else (y, x)
            if s["nominal_m"] == l["nominal_m"]:
                continue
            gap = abs(x["weeks"] - y["weeks"]) * 7
            pairs.append({"d1": s["nominal_m"], "t1": pc.time_for_vdot(s["vdot15"], s["nominal_m"]),
                          "d2": l["nominal_m"], "t2": pc.time_for_vdot(l["vdot15"], l["nominal_m"]), "gap_days": gap})
    return pairs
````

**`src/metrics/darp_r4.py`** — 신규, 전문 그대로(180줄)

````python
"""DARP r4 섀도 예측 — 전력 대회·품질 세트(Daniels 등가 강도)·심박-속도 H 를 칼만 필터로 정밀도 가중 결합.

r4는 **후보**다. 기본 표시는 r3 `darp.py`(runpulse:formula_v1)이고, 이 모듈은 같은 메트릭 이름을 섀도 provider로
매일 계산해 스냅샷·전향 평가(P7-PRED-63)에 쓴다. 섀도 provider 는 우선순위 표에 없어 is_primary 가 되지 않는다.
  runpulse:shadow_r4       — 기본 변형(대칭 칼만, 시간 기반 q)
  runpulse:shadow_r4_asym  — 대회·세트 비대칭 + 유지 조건부 앵커(REVIEW-07 §R4-8(2))
HRmax·LTHR 은 자체 추정(hr_profile.self). HR 이 없으면(T0) 세트·대회만으로 동작한다.
거리마다 관측을 목표 거리로 외삽(개인 k, 외삽 분산)한 뒤 결합하고, 마라톤은 Tanda(볼륨)를 역분산으로 더한다(REVIEW-09).
"""
from __future__ import annotations

import json
import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import core_r4 as pc
from src.metrics.prediction import signals_r4 as sg
from src.metrics.prediction.kalman import add_obs, filter_level

TARGETS = {"race_pred_5k_sec": 5000.0, "race_pred_10k_sec": 10000.0, "race_pred_half_sec": 21097.5,
           "race_pred_marathon_sec": 42195.0}
DEFAULT_HEAT, DEFAULT_COLD = -0.62, -0.84
TEMP_TABLE = (5, 10, 15, 20, 25, 30)
TANDA_MIN_KM_WEEK = 15.0   # (a/가정) Tanda 표본 범위 밖이면 제외
VDOT_REF_M = 10000.0       # race_pred_vdot 대표값 = 10K 기준 결합 VDOT


class DARPShadowCalculator(MetricCalculator):
    name = "darp_r4"
    provider = "runpulse:shadow_r4"
    version = "4.0"
    scope_type = "daily"
    category = "prediction"
    display_name = "레이스 예측 r4 (섀도)"
    description = "전력 대회·품질 세트(휴식 보정 Daniels 강도)·심박-속도 관계를 정밀도 가중으로 결합한 레이스 예측(15℃, 80% 범위·신뢰도)."
    unit = "sec"
    format_type = "time"
    higher_is_better = False
    decimal_places = 0
    requires = ["hr_profile", "heat_model"]
    produces = ["race_pred_vdot", *TARGETS]
    path = "c"
    variant = "base"
    low_mult: dict | None = None

    def ctl_at(self, ctx: CalcContext):
        return None

    def hr_refs(self, ctx: CalcContext, day: str) -> tuple[float | None, float | None]:
        _, js = ctx.get_latest_daily_metric("hr_profile", day, provider="runpulse:formula_v1", include_json=True)
        s = json.loads(js)["self"] if js else {}
        return s.get("hrmax"), s.get("lthr")

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        hrmax, lthr = self.hr_refs(ctx, day)
        _, hj = ctx.get_latest_daily_metric("heat_model", day, include_json=True)
        hm = json.loads(hj) if hj else {}
        heat, cold = hm.get("heat", DEFAULT_HEAT), hm.get("cold", DEFAULT_COLD)
        runs = ctx.get_runs(365, with_laps=True, include_end=False)
        confirmed = ctx.get_race_results()
        for r in runs:
            r["ambient_c"] = ctx.get_activity_metric(r["id"], "weather_temp_c")
            c = confirmed.get(r["id"])
            r["effort"] = c["effort"] if c else None
            r["official_time_s"] = c["official_time_sec"] if c else None
        races = sg.allout_races(runs, day, hrmax, heat, cold, self.ctl_at(ctx), lthr)
        paced = sg.paced_races(runs, day, heat, cold, hrmax, lthr)
        obs = sg.observations(runs, day, races, hrmax, paced)
        h = sg.hr_signal(runs, day, lthr, heat, cold)
        if not obs and h is None:
            return []
        k, k_sd, k_n = pc.k_personal(races)
        longest = sg.longest_run_m(runs, day)
        km_w, pace, long28 = sg.tanda_inputs(runs, day)
        states = {d: self._state(obs, h, day, d, k, k_sd, longest) for d in TARGETS.values()}
        ref = states[VDOT_REF_M]
        if ref is None:
            return []
        base = {"path": self.path, "variant": self.variant, "vdot15": round(ref["x"], 2), "weights": ref["weights"], "n_obs": ref["n"],
                "hr": h and round(h, 2), "hrmax": hrmax, "lthr": lthr, "k": round(k, 3), "k_sd": round(k_sd, 3),
                "k_pairs": k_n, "heat": heat, "cold": cold, "longest_12w_m": longest and round(longest),
                "recent_sets": [{"date": o["date"], "zone": o["kind"], "vdot": round(o["y"], 2), "n": o["n"], "rho": o["rho"]}
                                for o in obs if o["kind"] not in ("race", "paced")][-6:]}
        out = [self._result(value=round(ref["x"], 2), metric_name="race_pred_vdot", json_val=base)]
        for name, d in TARGETS.items():
            st = states[d]
            if st is None:
                continue
            s = pc.summarize(st["x"], st["var"], d)
            extra, reasons = {}, self._reasons(races, st, d, longest, paced)
            if d == 42195.0:
                extra = {"daniels_s": round(s["median_s"]), "weekly_km_8w": round(km_w, 1), "long_runs_28k_12w": long28}
                if pace and km_w >= TANDA_MIN_KM_WEEK:
                    t = pc.tanda_marathon(km_w, pace)
                    s = pc.combine_marathon(s, t)
                    extra.update(tanda_s=round(t), tanda_weight=s["tanda_weight"])
                else:
                    reasons.append(f"최근 8주 주평균 {km_w:.0f}km — 볼륨 모델(Tanda) 적용 범위 밖")
            med = s["median_s"]
            js = {"low_s": round(s["low_s"]), "high_s": round(s["high_s"]), "confidence": s["confidence"],
                  "reasons": reasons, "contributions": st["weights"], "path": self.path, "temp_c_basis": 15, **extra,
                  "by_temp": {str(t): round(med / pc.temp_factor(t, heat, cold)) for t in TEMP_TABLE},
                  "signals_s": self._by_kind(obs, h, day, d, k, k_sd, longest)}
            out.append(self._result(value=round(med), metric_name=name, json_val=js, confidence=s["confidence"]))
        return out

    @staticmethod
    def _convert(obs: list[dict], h: float | None, d: float, k: float, k_sd: float, longest: float | None):
        conv = []
        for o in obs:
            ks = pc.longrun_k_sd(k_sd, d, o["native_m"], longest)
            y, ev = pc.to_target(o["y"], o["native_m"], d, k, ks)
            conv.append({"date": o["date"], "y": y, "var": o["var"] + ev, "kind": o["kind"]})
        hv = None
        if h is not None:
            n = sg.h_native_m(h)
            y, ev = pc.to_target(h, n, d, k, pc.longrun_k_sd(k_sd, d, n, longest))
            hv = (y, pc.SIGMA_H ** 2 + ev)
        return conv, hv

    def _state(self, obs, h, day, d, k, k_sd, longest, kinds: set | None = None) -> dict | None:
        conv, hv = self._convert(obs, h, d, k, k_sd, longest)
        if kinds is not None:
            conv = [o for o in conv if o["kind"] in kinds]
            hv = hv if "H" in kinds else None
        st = filter_level(conv, day, pc.Q_PER_DAY, self.low_mult)
        if hv is not None:
            st = add_obs(st, hv[0], hv[1], "H") if st else {"x": hv[0], "var": hv[1], "weights": {"H": 1.0}, "n": 1}
        if st is None:
            return None
        # k 오차는 모든 관측에 공통(상관) → 관측별 분산(관련성 가중용)과 별도로 결합 결과에 한 번 더한다
        lnd = {}
        for o in obs:
            lnd.setdefault(o["kind"], []).append(math.log(o["native_m"]))
        if h is not None:
            lnd["H"] = [math.log(sg.h_native_m(h))]
        d_eff = math.exp(sum(w * sum(lnd[k2]) / len(lnd[k2]) for k2, w in st["weights"].items() if k2 in lnd))
        ks = pc.longrun_k_sd(k_sd, d, d_eff, longest)
        st["var"] += (ks * abs(math.log(d / d_eff)) / pc.dlnt_dvdot(st["x"], d)) ** 2
        st["d_eff"] = d_eff
        return st

    def _by_kind(self, obs, h, day, d, k, k_sd, longest) -> dict:
        kinds = {o["kind"] for o in obs} | ({"H"} if h is not None else set())
        out = {}
        for kd in sorted(kinds):
            st = self._state(obs, h, day, d, k, k_sd, longest, {kd})
            if st:
                out[kd] = round(pc.time_for_vdot(st["x"], d))
        return out

    @staticmethod
    def _reasons(races: list[dict], st: dict, d: float, longest: float | None, paced: list[dict] | None = None) -> list[str]:
        why = [f"{p['date']} 대회는 전력 여부가 불확실 — 하한 증거로만 사용. 대회 확인에서 입력하세요"
               for p in (paced or []) if p.get("uncertain")]
        if not races:
            why.append("최근 1년 전력 대회 기록 없음 — 훈련 세트·심박만으로 추정")
        elif min(-r["day"] for r in races) > 56:
            why.append(f"가장 최근 전력 대회가 {min(-r['day'] for r in races) // 7}주 전")
        if st["n"] < 5:
            why.append(f"근거 관측 {st['n']}개")
        if longest and d > longest:
            why.append(f"최근 12주 최장 {longest / 1000:.1f}km — 목표 거리까지 외삽")
        return why



class DARPShadowAsymCalculator(DARPShadowCalculator):
    """r4 섀도 변형 — 대회·세트 비대칭(낮은 관측 분산 ×4) + 유지 조건부 앵커(CTL 하락분만큼 대회 VDOT 감쇠)."""
    name = "darp_r4_asym"
    provider = "runpulse:shadow_r4_asym"
    display_name = "레이스 예측 r4 비대칭 (섀도)"
    description = "r4 섀도에 대회 상한·세트 하한 비대칭과 훈련 유지(CTL) 조건부 대회 앵커 감쇠를 더한 후보 변형."
    variant = "asym_maint"
    requires = ["hr_profile", "heat_model", "ctl"]
    low_mult = pc.ASYM_LOW_MULT

    def ctl_at(self, ctx: CalcContext):
        return lambda d: ctx.get_latest_daily_metric("ctl", d, provider="runpulse:formula_v1")
````

**`tests/test_darp_v2.py`** — 신규, 전문 그대로(77줄)

````python
"""P7-PRED-51: DARP v2 (c)/(b) 경로."""
import json

from src.metrics.base import CalcContext
from src.metrics.darp import DARPCalculator, DARPRefCalculator, sg_pairs
from src.metrics.prediction import core as pc
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run

DAY = "2026-09-26"


def _seed(c, with_ref=False):
    rid = seed_run(c, sid="race", date="2026-08-01", name="여름 10K 대회", dist=10000.0, moving=2700,
                   avg_hr=176, max_hr=190, event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?,?,?, 'allout')",
              (rid, 10000.0, 2700))
    upsert_metric(c, "activity", str(rid), "weather_temp_c", "open_meteo", numeric_value=25.0)
    tid = seed_run(c, sid="tempo", date="2026-09-20", name="템포", dist=6000.0, moving=1560, avg_hr=170, max_hr=180)
    seed_laps(c, tid, [(1000, 330, 140, "WARMUP", None, None)] + [(1000, 260, 172, "ACTIVE", None, None)] * 4
              + [(1000, 330, 150, "COOLDOWN", None, None)])
    prof = {"self": {"hrmax": 190.0, "lthr": 175.0}, "ref": {"source": "garmin", "lthr": 177.0, "hrmax": 193.0} if with_ref else None}
    upsert_metric(c, "daily", DAY, "hr_profile", "runpulse:formula_v1", numeric_value=175.0, json_value=prof)


def test_path_c_values():
    c = mem_conn()
    _seed(c)
    res = {r.metric_name: r for r in DARPCalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}
    base = json.loads(res["race_pred_vdot"].json_value)
    a15 = pc.vdot_at_15c(10000, 2700, 25.0, -0.62, -0.84)          # 25℃ 45:00 → 15℃ 등가
    assert base["anchor"]["vdot15"] == round(a15, 2) == 48.78        # 45:00 (VDOT 45.3) @25℃ → 15℃ 등가
    assert base["anchor"]["value"] == round(a15 - 0.16, 2)             # 8주 경과 → (8−6)×0.08 감쇠
    w = pc.vdot(4000, 1040)                                        # 템포 4×1km@4:20, HR 172 ≥ 0.92·175
    assert base["work"]["vdot"] == round(w, 2)
    exp, wts = pc.combine(base["anchor"]["value"], w, None)
    assert res["race_pred_vdot"].numeric_value == round(exp, 2) and base["weights"] == wts
    assert res["race_pred_10k_sec"].numeric_value == round(pc.time_for_vdot(exp, 10000))
    js = json.loads(res["race_pred_10k_sec"].json_value)
    assert js["low_s"] < res["race_pred_10k_sec"].numeric_value < js["high_s"]
    assert js["by_temp"]["15"] == res["race_pred_10k_sec"].numeric_value and js["by_temp"]["25"] > js["by_temp"]["15"]
    assert base["k"] == 1.06 and base["k_pairs"] == 0
    mj = json.loads(res["race_pred_marathon_sec"].json_value)          # 8주 16km → Tanda 미적용
    assert "tanda_s" not in mj and any("볼륨" in x for x in mj["reasons"])
    assert res["race_pred_marathon_sec"].numeric_value == round(pc.time_for_vdot(exp, 42195))


def test_path_b_needs_ref():
    c = mem_conn()
    _seed(c)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id=DAY)
    assert DARPRefCalculator().compute(ctx) == []
    c2 = mem_conn()
    _seed(c2, with_ref=True)
    res = {r.metric_name: r for r in DARPRefCalculator().compute(CalcContext(conn=c2, scope_type="daily", scope_id=DAY))}
    b = json.loads(res["race_pred_vdot"].json_value)
    assert b["lthr"] == 177.0 and b["hrmax"] == 193.0                 # 기기 HRmax 없음 → 177/0.917
    assert DARPRefCalculator.provider == "runpulse:ref_garmin"


def test_pairs_same_distance_skipped():
    r = [{"nominal_m": 10000.0, "vdot15": 45, "weeks": 2}, {"nominal_m": 10000.0, "vdot15": 46, "weeks": 5},
         {"nominal_m": 21097.5, "vdot15": 44, "weeks": 4}, {"nominal_m": 5000.0, "vdot15": 44, "weeks": 30}]
    p = sg_pairs(r)                                              # 30주 전 5K 는 26주 창 밖
    assert len(p) == 2 and all(x["d2"] == 21097.5 for x in p) and p[0]["gap_days"] == 14.0


def test_5k_best_effort_signal():
    c = mem_conn()
    _seed(c)
    c.execute("INSERT INTO activity_best_efforts (activity_id, source, effort_name, elapsed_sec, distance_m) "
              "VALUES (2, 'strava', '5K', 1300, 5000)")
    res = {r.metric_name: r for r in DARPCalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}
    j5 = json.loads(res["race_pred_5k_sec"].json_value)
    assert j5["signals_s"]["best_effort"] == 1300 and set(j5["signals_s"]) == {"race", "work", "best_effort"}
    assert "근거 신호 2개" not in j5["reasons"]                       # 신호 3개
    assert "best_effort" not in json.loads(res["race_pred_10k_sec"].json_value)["signals_s"]
````

**`tests/test_darp_r4.py`** — 신규, 전문 그대로(114줄)

````python
"""P7-PRED-51: DARP r4 섀도 — 칼만 결합, 비대칭·유지 앵커 변형, T0 동작, 섀도는 primary 가 아님."""
import json

from src.metrics.base import CalcContext
from src.metrics.darp_r4 import DARPShadowAsymCalculator, DARPShadowCalculator as DARPCalculator
from src.metrics.prediction import core_r4 as pc
from src.utils.metric_priority import get_provider_priority
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run

DAY = "2026-09-26"
INTER = [(2000, 720, 130, "WARMUP", None, None)] + [(1000, 250, 168, "ACTIVE", None, 182), (300, 150, 140, "RECOVERY", None, None)] * 5 \
    + [(1500, 540, 135, "COOLDOWN", None, None)]


def _seed(c, with_ref=False, hr=True):
    rid = seed_run(c, sid="race", date="2026-08-01", name="여름 10K 대회", dist=10000.0, moving=2700,
                   avg_hr=176 if hr else None, max_hr=190 if hr else None, event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?,?,?, 'allout')",
              (rid, 10000.0, 2700))
    upsert_metric(c, "activity", str(rid), "weather_temp_c", "open_meteo", numeric_value=25.0)
    tid = seed_run(c, sid="tempo", date="2026-09-20", name="템포", dist=6000.0, moving=1560, avg_hr=170, max_hr=180)
    seed_laps(c, tid, [(1000, 360, 140, "WARMUP", None, None)] + [(1000, 262, 172, "ACTIVE", None, None)] * 4
              + [(1000, 360, 150, "COOLDOWN", None, None)])
    iid = seed_run(c, sid="int", date="2026-09-12", name="인터벌", dist=8800.0, moving=3300, avg_hr=155, max_hr=182)
    seed_laps(c, iid, INTER)
    if hr:
        prof = {"self": {"hrmax": 190.0, "lthr": 175.0},
                "ref": {"source": "garmin", "lthr": 177.0, "hrmax": None} if with_ref else None}
        upsert_metric(c, "daily", DAY, "hr_profile", "runpulse:formula_v1", numeric_value=175.0, json_value=prof)


def _res(calc, c):
    return {r.metric_name: r for r in calc.compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}


def test_path_c_kalman_combination():
    c = mem_conn()
    _seed(c)
    res = _res(DARPCalculator(), c)
    base = json.loads(res["race_pred_vdot"].json_value)
    assert base["n_obs"] == 3 and set(base["weights"]) == {"race", "T", "I"} and abs(sum(base["weights"].values()) - 1) < 0.01
    assert [s["zone"] for s in base["recent_sets"]] == ["I", "T"] and base["k"] == 1.06 and base["k_pairs"] == 0
    a15 = pc.vdot_at_15c(10000, 2700, 25.0, -0.62, -0.84)
    assert min(a15, 47.0) - 3 < res["race_pred_vdot"].numeric_value < max(a15, 50.0)
    js = json.loads(res["race_pred_10k_sec"].json_value)
    assert js["low_s"] < res["race_pred_10k_sec"].numeric_value < js["high_s"] and 0 < js["confidence"] < 1
    assert js["by_temp"]["15"] == res["race_pred_10k_sec"].numeric_value and js["by_temp"]["25"] > js["by_temp"]["15"]
    assert set(js["signals_s"]) == {"race", "T", "I"} and js["contributions"] == base["weights"]
    mj = json.loads(res["race_pred_marathon_sec"].json_value)          # 8주 주평균 3km → Tanda 미적용
    assert "tanda_s" not in mj and any("Tanda" in x for x in mj["reasons"])
    assert any("외삽" in x for x in mj["reasons"])                     # 최장 10km < 42.2km


def test_shadow_providers_never_primary():
    assert get_provider_priority(DARPCalculator.provider) > get_provider_priority("runpulse:formula_v1")
    assert get_provider_priority(DARPShadowAsymCalculator.provider) > get_provider_priority("runpulse:formula_v1")


def test_asym_maint_variant():
    c = mem_conn()
    _seed(c)
    upsert_metric(c, "daily", "2026-08-01", "ctl", "runpulse:formula_v1", numeric_value=60.0)
    upsert_metric(c, "daily", "2026-09-25", "ctl", "runpulse:formula_v1", numeric_value=30.0)   # 대회 후 CTL 절반
    base = json.loads(_res(DARPCalculator(), c)["race_pred_vdot"].json_value)
    asym = _res(DARPShadowAsymCalculator(), c)
    aj = json.loads(asym["race_pred_vdot"].json_value)
    assert base["variant"] == "base" and aj["variant"] == "asym_maint"
    assert aj["vdot15"] != base["vdot15"]


def test_maint_loss_only_when_ctl_drops():
    from src.metrics.prediction import signals_r4 as sg
    runs = [{"id": 1, "date": "2026-08-01", "nominal_m": 10000.0, "is_race": True, "avg_hr": None, "perf_time_s": 2700,
             "effort": "allout", "official_time_s": None, "ambient_c": 15.0}]
    up = sg.allout_races(runs, DAY, None, -0.62, -0.84, lambda d: 60.0 if d == "2026-08-01" else 70.0)
    down = sg.allout_races(runs, DAY, None, -0.62, -0.84, lambda d: 60.0 if d == "2026-08-01" else 30.0)
    assert up[0]["maint_loss"] == 0.0 and abs(down[0]["maint_loss"] - pc.MAINT_ALPHA * 0.5) < 1e-9
    assert down[0]["vdot15"] < up[0]["vdot15"]


def test_t0_without_heart_rate():
    c = mem_conn()
    _seed(c, hr=False)
    res = _res(DARPCalculator(), c)                                  # hr_profile 없음 → H 없음, 세트·대회만
    base = json.loads(res["race_pred_vdot"].json_value)
    assert base["hr"] is None and base["lthr"] is None and "race_pred_5k_sec" in res
    assert set(base["weights"]) == {"race", "T", "I"}


def test_no_data_returns_empty():
    assert DARPCalculator().compute(CalcContext(conn=mem_conn(), scope_type="daily", scope_id=DAY)) == []


def test_paced_race_is_lower_bound_not_anchor():
    c = mem_conn()
    _seed(c)
    pid = seed_run(c, sid="paced", date="2026-09-05", name="숲길 10K 대회", dist=10000.0, moving=2820, avg_hr=163, max_hr=178,
                   event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, effort) VALUES (?, 10000, 'paced')", (pid,))
    base = json.loads(_res(DARPCalculator(), c)["race_pred_vdot"].json_value)
    assert "paced" in base["weights"] and base["n_obs"] == 4


def test_auto_effort_by_duration():
    from src.metrics.prediction import signals_r4 as sg
    race = {"id": 1, "date": "2026-09-12", "nominal_m": 10000.0, "is_race": True, "avg_hr": 163, "max_hr": 178,
            "perf_time_s": 2818, "effort": None, "official_time_s": None, "ambient_c": 18.6}
    assert not sg.allout_races([race], DAY, 192.0, -0.62, -0.84, lthr=177.6)          # 9/12 → 자동 submax
    assert not sg.paced_races([race], DAY, -0.62, -0.84, 192.0, 177.6)                  # submax 는 하한으로도 안 씀
    mara = dict(race, id=2, nominal_m=42195.0, avg_hr=147, max_hr=158, perf_time_s=13332, date="2026-06-01")
    p = sg.paced_races([mara], DAY, -0.62, -0.84, 185.0, 170.8)                          # 풀: uncertain → 하한 + 확인 요청
    assert p and p[0]["uncertain"] and not sg.allout_races([mara], DAY, 185.0, -0.62, -0.84, lthr=170.8)
    assert sg.allout_races([dict(race, effort="allout")], DAY, 192.0, -0.62, -0.84, lthr=177.6)   # 사용자 입력 우선
````

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -33,5 +33,6 @@
 from src.metrics.cirs import CIRSCalculator
 from src.metrics.di import DICalculator
-from src.metrics.darp import DARPCalculator
+from src.metrics.darp import DARPCalculator, DARPRefCalculator
+from src.metrics.darp_r4 import DARPShadowAsymCalculator, DARPShadowCalculator
 from src.metrics.hr_profile import HRProfileCalculator
 from src.metrics.heat_model import HeatModelCalculator
@@ -94,4 +95,7 @@
     HRProfileCalculator(),
     HeatModelCalculator(),
+    DARPShadowCalculator(),       # r4 섀도(P7-PRED-51) — 기본 표시 아님, 스냅샷·전향 평가용
+    DARPShadowAsymCalculator(),
+    DARPRefCalculator(),   # (b) — DARP 보다 먼저: producer_map 에서 race_pred_* 생산자가 (c) DARP 로 남도록
     DARPCalculator(),
     TrainingResponseCalculator(),
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -321,4 +321,5 @@
     MetricDef("gap_rp", "capacity", "metric", "sec/km", "RunPulse GAP (경사 보정 페이스)"),
     MetricDef("runpulse_vdot", "capacity", "metric", "", "RunPulse VDOT (Daniels)"),
+    MetricDef("race_pred_vdot", "prediction", "metric", "", "예측 결합 VDOT(15℃ 등가)", scope="daily"),
     MetricDef("hr_profile", "hr", "metric", "bpm", "HR 프로필(자체·참조 HRmax/LTHR, HRR·LTHR 존)", scope="daily"),
     MetricDef("hrmax_self", "hr", "metric", "bpm", "RunPulse 추정 최대심박", scope="daily"),
````

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 34 → 37 (darp_ref + 섀도 2)

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 34개)
+        # ALL_CALCULATORS 수 검증 (설계: 37개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 34:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 34개)")
+            if len(ALL_CALCULATORS) != 37:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 37개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 34개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 37개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

**`tests/test_metric_naming.py`** — 수정, 아래 diff 그대로 — 의도된 provider 분리(darp ↔ darp_ref ↔ darp_r4 ↔ darp_r4_asym) 허용

````diff
--- a/tests/test_metric_naming.py
+++ b/tests/test_metric_naming.py
@@ -28,12 +28,19 @@
     def test_no_duplicate_produces_across_calculators(self):
         """서로 다른 calculator가 같은 metric_name을 produces하면 안 됨
         (같은 이름은 provider로 구분하므로 허용하되, produces 선언 중복은 의도 확인 필요)."""
+        # 의도된 provider 분리(같은 이름, 다른 provider): darp(runpulse:formula_v1) ↔ darp_ref(runpulse:ref_garmin)
+        # ↔ r4 섀도 darp_r4(runpulse:shadow_r4)·darp_r4_asym(runpulse:shadow_r4_asym) — P7-PRED-51
+        family = {"darp", "darp_ref", "darp_r4", "darp_r4_asym"}
+        provider_split = {frozenset({a, b}) for a in family for b in family if a != b}
         seen = {}
         for calc in ALL_CALCULATORS:
             for produced in calc.produces:
                 if produced in seen:
                     # 같은 scope_type이면 충돌
                     other = seen[produced]
+                    if frozenset({calc.name, other.name}) in provider_split:
+                        assert calc.provider != other.provider
+                        continue
                     assert calc.scope_type != other.scope_type or calc.name == other.name, (
                         f"'{produced}' is produced by both "
                         f"'{other.name}' and '{calc.name}' in same scope"
````

**`tests/test_validator.py`** — 수정, 아래 diff 그대로 — 같은 produces 이름을 한 번만 넣는다

````diff
--- a/tests/test_validator.py
+++ b/tests/test_validator.py
@@ -330,13 +330,13 @@
     def test_pass_all_produces_present(self, empty_conn):
         """모든 produces 메트릭이 metric_store에 존재하면 PASS."""
         from src.metrics.engine import ALL_CALCULATORS
-        for calc in ALL_CALCULATORS:
-            for metric in calc.produces:
-                empty_conn.execute(
-                    "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
-                    "VALUES ('daily', '2025-01-01', ?, 'fitness', 'runpulse:formula', 1.0)",
-                    (metric,),
-                )
+        names = sorted({m for calc in ALL_CALCULATORS for m in calc.produces})   # darp/darp_ref 동명 produces
+        for metric in names:
+            empty_conn.execute(
+                "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value) "
+                "VALUES ('daily', '2025-01-01', ?, 'fitness', 'runpulse:formula', 1.0)",
+                (metric,),
+            )
         empty_conn.commit()
         r = DataValidator(empty_conn).run_all()
         assert _find(r, "engine_coverage").status == "PASS"
````

검증:
```
python3 scripts/gen_metric_dictionary.py
python3 -m pytest tests/test_darp_v2.py tests/test_darp_r4.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py tests/test_dashboard_service.py tests/test_ai_context.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-52 — 일별 VDOT 의존 메트릭 복구(rri·eftp → `race_pred_vdot`) + marathon_shape v2(볼륨·롱런 구조)

- 의존: P7-PRED-51 · UI 노출: 마라톤 셰이프·RRI·eFTP 카드가 **0행 → 값 있음**. 마라톤 셰이프는 의미가 바뀐다(볼륨 충족률 %). · 실DB: 재계산 시 생성
- 파일: `src/metrics/marathon_shape.py`(**전문 교체**), `src/metrics/rri.py`, `src/metrics/eftp.py`, `tests/test_marathon_shape.py`, `tests/test_rri.py`, `tests/test_eftp.py`
- 왜: rri·eftp가 일별 `runpulse_vdot`(실제로는 활동 scope에만 존재)을 읽어 실DB에서 0행이다(REVIEW-08 #2). vdot_adj는 P7-PRED-90에서 폐기했다.
- marathon_shape v2(REVIEW-09 §7, 추가 요구 A):
  - numeric = 8주 주평균 km ÷ Tanda 역산 필요 km × 100(상한 없음). 목표 풀 goal이 있으면 목표 페이스, 없으면 현재 VDOT의 Daniels M 페이스를 쓴다. 볼륨만으로 도달 불가면 numeric 없음.
  - json: 주당 품질 세션, 롱런 수(12주 ≥21·≥30km), 최장, 롱런 속 MP km, 필요 km.
  - 예측 반영은 darp가 한다. 이 메트릭은 설명·계획용이다.
  - v1 점수식(검증 안 된 표 기반, 100 절단)은 폐기한다.

**`src/metrics/marathon_shape.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(81줄)

````python
"""Marathon Shape v2 — 마라톤 볼륨·롱런 구조(P7-PRED-52, REVIEW-09 §7). 기기 불필요(GPS·시간).

numeric = 볼륨 충족률(%) = 최근 8주 주평균 km ÷ Tanda(2011) 역산 필요 주간 km × 100 (상한 없음).
  필요 km: 목표 마라톤(활성 goal, 42km 이상)이 있으면 목표 페이스, 없으면 현재 race_pred_vdot 의 Daniels 마라톤 페이스를
  현재 평균 훈련 페이스로 Tanda 식 Pm = 17.1 + 140·e^(−0.0053K) + 0.55·P 에 넣어 K 로 푼다. 달성 불가(해 없음)면 None.
json: 주간 km(8주)·평균 페이스·주당 품질 세션·거리별 롱런 수(12주: ≥21km, ≥30km)·최장·롱런 속 MP km(8주)·필요 km.
예측 반영은 darp 가 따로 한다(중앙값 = Tanda, 최장 초과 외삽 = 범위 확대). 이 메트릭은 설명·계획용이다.
v1 의 점수식(검증 안 된 표 기반 목표 볼륨 × 2/3 + 롱런 × 1/3, 100 절단)은 쓰지 않는다.
"""
from __future__ import annotations

import math
from datetime import date

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import response as rs
from src.metrics.prediction.daniels import time_for_vdot
from src.metrics.prediction.signals_r4 import longest_run_m, tanda_inputs

MARATHON_M = 42195.0
LONG_KM = (21.0, 30.0)


def tanda_required_km(goal_pace_s_km: float, train_pace_s_km: float) -> float | None:
    """Tanda 식을 주간 km 로 역산. (Pm − 17.1 − 0.55·P)/140 이 (0, 1) 밖이면 None(볼륨만으로 도달 불가/이미 충분)."""
    x = (goal_pace_s_km - 17.1 - 0.55 * train_pace_s_km) / 140.0
    if x >= 1.0:
        return 0.0
    if x <= 0.0:
        return None
    return -math.log(x) / 0.0053


class MarathonShapeCalculator(MetricCalculator):
    name = "marathon_shape"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "capacity"
    requires = ["race_pred_vdot"]
    produces = ["marathon_shape"]

    display_name = "Marathon Shape"
    description = "마라톤 볼륨 충족률(%) = 8주 주평균 km ÷ Tanda 역산 필요 km. json 에 롱런·MP·품질 세션 구조."
    unit = "%"
    ranges = {"low": [0, 60], "building": [60, 85], "adequate": [85, 110], "high": [110, 300]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        vd = ctx.get_latest_daily_metric("race_pred_vdot", day, provider="runpulse:formula_v1")
        runs = ctx.get_runs(112, with_laps=True, include_end=False)
        if vd is None or not runs:
            return []
        km_w, pace, _ = tanda_inputs(runs, day)
        mp_speed = MARATHON_M / time_for_vdot(float(vd), MARATHON_M)
        goal = ctx.get_active_goal(day)
        if goal and (goal.get("distance_km") or 0) >= 42.0 and goal.get("target_time_sec"):
            goal_pace, basis = goal["target_time_sec"] / goal["distance_km"], "goal"
        else:
            goal_pace, basis = 1000.0 / mp_speed, "current_vdot"
        need = tanda_required_km(goal_pace, pace) if pace else None
        weekly = rs.weekly_zone_minutes(runs, day, weeks=8)
        longs = [r for r in runs if r["date"] < day and not r["is_race"] and (date.fromisoformat(day) - date.fromisoformat(r["date"])).days <= 84]
        js = {
            "weekly_km_8w": round(km_w, 1), "train_pace_s_km": round(pace) if pace else None,
            "quality_sessions_per_week_8w": round(sum(weekly["sessions"]) / 8, 2),
            "long_runs_12w": {f"ge_{int(k)}km": sum(1 for r in longs if r["distance_m"] >= k * 1000) for k in LONG_KM},
            "longest_12w_km": round((longest_run_m(runs, day) or 0) / 1000, 1),
            "mp_km_in_long_8w": round(rs.long_mp_km(runs, day, mp_speed), 1),
            "mp_pace_s_km": round(1000 / mp_speed), "target_pace_s_km": round(goal_pace), "basis": basis,
            "tanda_required_km": round(need, 1) if need is not None else None,
        }
        if need is None:                      # 볼륨만으로 목표 페이스 도달 불가 — 수치 없이 구조만
            return [self._result(value=None, json_val=js)]
        pct = round(km_w / need * 100, 1) if need > 0 else 100.0
        js["label"] = next(k for k, (lo, hi) in self.ranges.items() if pct < hi or k == "high")
        return [self._result(value=pct, json_val=js)]

````

**`src/metrics/rri.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/rri.py
+++ b/src/metrics/rri.py
@@ -18,7 +18,7 @@
     version = "1.0"
     scope_type = "daily"
     category = "capacity"
-    requires = ["runpulse_vdot", "ctl", "di", "cirs"]
+    requires = ["race_pred_vdot", "ctl", "di", "cirs"]
     produces = ["rri"]
 
     display_name = "RRI (레이스 준비도)"
@@ -30,7 +30,7 @@
     decimal_places = 1
 
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
-        vdot = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
+        vdot = ctx.get_metric("race_pred_vdot", provider="runpulse:formula_v1")
         ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
         if vdot is None or ctl is None:
             return []
````

**`src/metrics/eftp.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/eftp.py
+++ b/src/metrics/eftp.py
@@ -19,7 +19,7 @@
     version = "1.0"
     scope_type = "daily"
     category = "capacity"
-    requires = ["runpulse_vdot"]
+    requires = ["race_pred_vdot"]
     produces = ["eftp"]
 
     display_name = "eFTP (역치 페이스)"
@@ -33,7 +33,7 @@
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
         # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
         # 1차: VDOT → Daniels T-pace
-        vdot = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
+        vdot = ctx.get_metric("race_pred_vdot", provider="runpulse:formula_v1")
         if vdot is not None:
             from src.utils.daniels_table import vdot_to_t_pace
             t_pace = vdot_to_t_pace(float(vdot))
````

**`tests/test_marathon_shape.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_marathon_shape.py
+++ b/tests/test_marathon_shape.py
@@ -46,38 +46,48 @@
                       numeric_value=val, category="rp_load")
 
 
+def _seed_block(conn, weeks=8, km=12.0, pace=330, long_km=None):
+    from datetime import datetime, timedelta
+    n = 0
+    for i in range(1, weeks * 7 + 1, 2):                   # 이틀에 한 번
+        d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
+        dist = (long_km if (long_km and i % 14 == 1) else km) * 1000
+        _seed_activity(conn, d, source_id=f"b{i}", distance_m=dist, moving_time_sec=int(dist / 1000 * pace))
+        n += 1
+    return n
+
+
 class TestMarathonShape:
+    """P7-PRED-52: v2 — Tanda 역산 필요 km 대비 볼륨 충족률, 롱런 구조 json."""
+
     def test_with_data(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
-        from datetime import datetime, timedelta
-        for i in range(28):
-            d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
-            _seed_activity(conn, d, source_id=f"ms{i}",
-                           distance_m=8500, moving_time_sec=2800)
-        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
-        results = MarathonShapeCalculator().compute(ctx)
-        assert len(results) == 1
-        assert 0 < results[0].numeric_value <= 100
-        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
-        assert jv["label"] in ["insufficient", "base", "building", "ready", "peak"]
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
+        _seed_block(conn, long_km=24)
+        r = MarathonShapeCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
+        jv = json.loads(r[0].json_value)
+        assert r[0].numeric_value > 0 and jv["label"] in MarathonShapeCalculator.ranges
+        assert jv["basis"] == "current_vdot" and jv["long_runs_12w"]["ge_21km"] >= 4 and jv["longest_12w_km"] == 24.0
+        assert abs(r[0].numeric_value - jv["weekly_km_8w"] / jv["tanda_required_km"] * 100) < 0.2
 
     def test_no_vdot(self):
         conn = _conn()
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
-        results = MarathonShapeCalculator().compute(ctx)
-        assert len(results) == 0
+        assert MarathonShapeCalculator().compute(ctx) == []
 
-    def test_json_structure(self):
+    def test_goal_basis_and_unreachable(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
-        from datetime import datetime, timedelta
-        for i in range(28):
-            d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
-            _seed_activity(conn, d, source_id=f"mj{i}",
-                           distance_m=8500, moving_time_sec=2800)
-        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
-        results = MarathonShapeCalculator().compute(ctx)
-        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
-        assert "label" in jv
-        assert "weekly_km_avg" in jv or "target_weekly_km" in jv
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=45.0)
+        _seed_block(conn, pace=420)
+        conn.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) "
+                     "VALUES ('풀', '2026-11-22', 42.195, 9000, 'active')")      # 2:30 — 볼륨으로 도달 불가
+        r = MarathonShapeCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
+        jv = json.loads(r[0].json_value)
+        assert jv["basis"] == "goal" and jv["tanda_required_km"] is None and r[0].numeric_value is None
+
+
+def test_tanda_required_roundtrip():
+    from src.metrics.marathon_shape import tanda_required_km
+    from src.metrics.prediction.core_r4 import tanda_marathon
+    k = tanda_required_km(300.0, 330.0)
+    assert k and abs(tanda_marathon(k, 330.0) / 42.195 - 300.0) < 0.5
````

**`tests/test_rri.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_rri.py
+++ b/tests/test_rri.py
@@ -50,7 +50,7 @@
     def test_with_all_inputs(self):
         conn = _conn()
         _seed_daily_metrics(conn, "2026-04-01",
-                            runpulse_vdot=50.0, ctl=45.0, di=75.0, cirs=25.0)
+                            race_pred_vdot=50.0, ctl=45.0, di=75.0, cirs=25.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = RRICalculator().compute(ctx)
         assert len(results) == 1
@@ -59,7 +59,7 @@
     def test_high_cirs_lowers_rri(self):
         conn = _conn()
         _seed_daily_metrics(conn, "2026-04-01",
-                            runpulse_vdot=50.0, ctl=45.0, di=75.0, cirs=80.0)
+                            race_pred_vdot=50.0, ctl=45.0, di=75.0, cirs=80.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = RRICalculator().compute(ctx)
         assert results[0].numeric_value < 50
@@ -74,7 +74,7 @@
     def test_category(self):
         conn = _conn()
         _seed_daily_metrics(conn, "2026-04-01",
-                            runpulse_vdot=50.0, ctl=45.0, di=75.0, cirs=25.0)
+                            race_pred_vdot=50.0, ctl=45.0, di=75.0, cirs=25.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = RRICalculator().compute(ctx)
         assert results[0].category == "capacity"
@@ -90,7 +90,7 @@
         ctx = MockCalcContext(
             scope_type="daily", scope_id="2026-04-01",
             metrics={
-                "runpulse_vdot": {"numeric": 50.0, "text": None, "json": None},
+                "race_pred_vdot": {"numeric": 50.0, "text": None, "json": None},
                 "ctl": {"numeric": 45.0, "text": None, "json": None},
                 "di": {"numeric": 75.0, "text": None, "json": None},
                 "cirs": {"numeric": 25.0, "text": None, "json": None},
````

**`tests/test_eftp.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_eftp.py
+++ b/tests/test_eftp.py
@@ -49,7 +49,7 @@
 class TestEFTP:
     def test_from_vdot(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = EFTPCalculator().compute(ctx)
         assert len(results) == 1
@@ -64,7 +64,7 @@
 
     def test_confidence(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = EFTPCalculator().compute(ctx)
         assert results[0].confidence == 0.85
````

검증:
```
python3 -m pytest tests/test_marathon_shape.py tests/test_rri.py tests/test_eftp.py -q
```

## P7-PRED-53 — 대회 확인 서비스(race_results)

- 의존: P7-PRED-11 · UI 노출: P7-PRED-73 · 실DB: 사용자가 UI에서 입력(자동 백필 없음)
- 파일: `src/services/race_result_service.py`(신규), `tests/test_race_result_service.py`(신규)
- 규칙: effort ∈ allout/paced/fun/dnf. 공식 기록 600초~8시간. 거리 미입력이면 활동 거리. 예측은 allout만 앵커로 쓰고 공식 기록이 있으면 기기 기록 대신 쓴다(P7-PRED-22 `allout_races`). 후보 = canonical 러닝 중 `event_type='race'` 또는 이름이 대회처럼 보이는 것(TT·템포 제외) + 이미 확인한 것.
- 주의: race_results는 activity id를 참조한다 — `reprocess_all(clear_first)`는 id를 바꾸므로 P7-PRED-13의 가드를 우회(`force=True`)하지 말 것.

**`src/services/race_result_service.py`** — 신규, 전문 그대로(62줄)

````python
"""대회 확인(race_results, P7-PRED-53) — 사용자가 대회 여부·전력 여부·공식 기록을 확정한다.

예측(P7-PRED-51)은 확정된 effort 가 'allout' 인 대회만 앵커로 쓰고, 공식 기록이 있으면 기기 기록 대신 쓴다.
미확정 대회는 기존 규칙(이름·event_type + 평균 HR ≥ 0.84·HRmax)으로 추정한다.
"""
from __future__ import annotations

import re
import sqlite3

EFFORTS = ("allout", "paced", "fun", "dnf")
_RACE_NAME = re.compile(r"대회|마라톤|marathon|half|하프|10k|10km|race|레이스", re.I)
_NOT_RACE = re.compile(r"TT|템포|tempo", re.I)


def confirm(conn: sqlite3.Connection, activity_id: int, effort: str, official_time_sec: int | None = None,
            race_name: str | None = None, distance_m: float | None = None, note: str | None = None) -> dict:
    if effort not in EFFORTS:
        raise ValueError(f"effort must be one of {EFFORTS}")
    if official_time_sec is not None and not 600 <= official_time_sec <= 8 * 3600:
        raise ValueError("official_time_sec out of range")
    row = conn.execute("SELECT distance_m FROM activity_summaries WHERE id=?", (activity_id,)).fetchone()
    if row is None:
        raise LookupError("activity not found")
    distance_m = distance_m or row[0]              # 미입력 시 기기 거리
    conn.execute(
        "INSERT INTO race_results (activity_id, race_name, distance_m, official_time_sec, effort, note, confirmed_at) "
        "VALUES (?,?,?,?,?,?, datetime('now')) ON CONFLICT(activity_id) DO UPDATE SET race_name=excluded.race_name, "
        "distance_m=excluded.distance_m, official_time_sec=excluded.official_time_sec, effort=excluded.effort, "
        "note=excluded.note, confirmed_at=excluded.confirmed_at",
        (activity_id, race_name, distance_m, official_time_sec, effort, note))
    conn.commit()
    return get(conn, activity_id)


def remove(conn: sqlite3.Connection, activity_id: int) -> bool:
    n = conn.execute("DELETE FROM race_results WHERE activity_id=?", (activity_id,)).rowcount
    conn.commit()
    return n > 0


def get(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    r = conn.execute("SELECT activity_id, race_name, distance_m, official_time_sec, effort, note, confirmed_at "
                     "FROM race_results WHERE activity_id=?", (activity_id,)).fetchone()
    keys = ("activity_id", "race_name", "distance_m", "official_time_sec", "effort", "note", "confirmed_at")
    return dict(zip(keys, r)) if r else None


def candidates(conn: sqlite3.Connection, since: str) -> list[dict]:
    """확인이 필요한 대회 후보(since 이후, canonical 러닝, 이름 또는 event_type 으로 대회로 보이는 것) — 최신순."""
    rows = conn.execute(
        "SELECT v.id, substr(v.start_time,1,10), v.name, v.distance_m, COALESCE(v.elapsed_time_sec, v.duration_sec), "
        "v.event_type, r.effort FROM v_canonical_activities v LEFT JOIN race_results r ON r.activity_id = v.id "
        "WHERE v.start_time >= ? AND v.activity_type IN ('running','trail_running') ORDER BY v.start_time DESC",
        (since,)).fetchall()
    out = []
    for aid, d, name, dist, t, ev, eff in rows:
        looks = ev == "race" or (bool(_RACE_NAME.search(name or "")) and not _NOT_RACE.search(name or ""))
        if looks or eff:
            out.append({"activity_id": aid, "date": d, "name": name, "distance_m": dist, "time_sec": t,
                        "confirmed_effort": eff})
    return out
````

**`tests/test_race_result_service.py`** — 신규, 전문 그대로(35줄)

````python
"""P7-PRED-53: 대회 확인 서비스."""
import pytest

from src.services import race_result_service as rr
from tests.helpers_pred import mem_conn, seed_run


def test_confirm_update_remove():
    c = mem_conn()
    aid = seed_run(c, sid="1", name="양천 마라톤 10k")
    assert rr.confirm(c, aid, "allout", official_time_sec=2653)["effort"] == "allout"
    assert rr.confirm(c, aid, "paced")["official_time_sec"] is None
    assert rr.remove(c, aid) and rr.get(c, aid) is None


def test_validation():
    c = mem_conn()
    aid = seed_run(c, sid="1")
    with pytest.raises(ValueError):
        rr.confirm(c, aid, "hard")
    with pytest.raises(ValueError):
        rr.confirm(c, aid, "allout", official_time_sec=30)
    with pytest.raises(LookupError):
        rr.confirm(c, 999, "allout")


def test_candidates():
    c = mem_conn()
    seed_run(c, sid="1", date="2026-09-12", name="Forest run", event_type="race")
    seed_run(c, sid="2", date="2026-09-10", name="템포 10k")
    b = seed_run(c, sid="3", date="2026-09-05", name="하프 대회")
    seed_run(c, sid="4", date="2026-09-01", name="Easy")
    rr.confirm(c, b, "fun")
    got = rr.candidates(c, "2026-08-01")
    assert [(x["name"], x["confirmed_effort"]) for x in got] == [("Forest run", None), ("하프 대회", "fun")]
````

검증:
```
python3 -m pytest tests/test_race_result_service.py -q
```

