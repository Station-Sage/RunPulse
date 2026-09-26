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
