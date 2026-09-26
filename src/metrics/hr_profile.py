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
