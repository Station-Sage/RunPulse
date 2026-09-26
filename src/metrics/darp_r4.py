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
