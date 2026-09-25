# PRED-5x — 레이스 예측 v2 (경로 b·c, 개인 내구성, 마라톤) (예측 리뉴얼 r3)

근거: `REVIEW-07-prediction-renewal.md` r3 §3·4, Q1·Q4·Q9. 경로 (a) Garmin 인제스트는 P7-PRED-25.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-51 — DARP v2: 경로 (c) 자체 추정·(b) 기기 심박 기준, 5K 다중 신호, 개인 내구성 지수, 마라톤 Daniels·Tanda

- 의존: P7-PRED-14, P7-PRED-22, P7-PRED-24, P7-PRED-25(경로 b의 참조값), P7-PRED-33 · UI 노출: Today 레이스 허브 예측값·범위(기존 `race_pred_*` primary 경로 그대로) + P7-PRED-72 · 실DB: 재계산 시 교체(P7-PRED-61 4단계)
- 파일: `src/metrics/darp.py`(**전문 교체**), `tests/test_darp_v2.py`(신규), `src/metrics/engine.py`, `src/utils/metric_registry.py`, `scripts/check_docs.py`, `tests/test_metric_naming.py`, `tests/test_validator.py`
- 계산(2026-09-26 기준 사본 DB 결과를 괄호에):
  1. 전력 대회(365일, 확인 effort 우선, 없으면 HR 규칙) → 15℃ 등가 VDOT(`heat_model` 계수) → 6주 유예 후 주 0.08 감쇠 → 최대값이 앵커 A (2026-05-09 10K 44:13, 15℃ 46.2 → 20주 경과 45.08).
  2. W = 최근 42일 연속 랩 블록(≥2km·≥8분, GAP) 최고 VDOT, 자격: 대회 또는 블록 HR ≥ 0.92·LTHR, LTHR 없으면(T0) 블록 속도 ≥ 0.90·v_t. **기온 정규화하지 않는다**(여름 블록 과대 — 백테스트). (43.17)
  3. H = 최근 60일 정상 주행 랩의 HR–속도(15℃ 정규화) 직선에서 LTHR 속도 → 60분 레이스 VDOT. 점 25개 미만이면 없음. (44.1)
  4. 결합: W ≥ A → W, 아니면 A + 0.25(W−A); H 있으면 0.8·core + 0.2·H. 기여도 json. (44.5, 대회 0.6·작업 0.2·심박 0.2)
  5. 거리 환산 = Daniels × (d/d_앵커)^(k−1.06), k = 최근 26주 전력 대회 쌍(거리비 ≥1.6, 간격 ≤90일)으로 사전 N(1.06, 0.03²)을 역분산 수축. 쌍 0~2개에서도 동작(0개면 1.06). (k 1.06, 쌍 0)
  6. 5K: A·W·H + 최근 90일 5K best effort(구간 기록 — 일치도 신호로만, 중앙값에는 안 들어감)로 신호 수·신호 간 차이를 계산 → 신뢰도. **0.5 상한 없음, "5K TT 하라" 문구 없음.**
  7. 마라톤: Daniels 환산과 Tanda(최근 8주 주평균 km, 평균 이동 페이스)의 기하평균, 범위 `[min×0.98, max×1.03×(1.02 if 12주 28km+ 롱런 0)]`. 주 15km 미만이면 Tanda 제외·신뢰도 ×0.8·느린 쪽 +3%p (가정: Tanda 표본 범위 밖).
  8. 출력(15℃ 기준): `race_pred_vdot`(json: path, weights, anchor, work, hr, hrmax, lthr, k, k_sd, k_pairs, heat, cold), `race_pred_{5k,10k,half,marathon}_sec`(json: low_s, high_s, confidence, reasons, contributions, path, temp_c_basis=15, by_temp{5,10,15,20,25,30}, signals_s, 마라톤은 daniels_s·tanda_s·weekly_km_8w·long_runs_28k_12w).
  9. 경로: `DARPCalculator`(name `darp`, provider `runpulse:formula_v1`, 자체 HRmax·LTHR) / `DARPRefCalculator`(name `darp_ref`, provider `runpulse:ref_garmin`, 기기 LTHR·HRmax(없으면 LTHR/0.917) — 기기 LTHR 없으면 산출 안 함). 같은 metric_name을 provider로 구분한다(우선순위: formula 20 > garmin 100 > ref_garmin 999 → 화면 기본값은 (c)).
  - 결과(사본 DB, 15℃): (c) 5K 22:01 / 10K 45:39 / 하프 1:41:12 / 마라톤 3:40:39(범위 3:25:59~4:03:20, Daniels 3:30:12·Tanda 3:51:37), (b) 5K 22:02 / 10K 45:41 / 하프 1:41:15 / 마라톤 3:40:42. 25℃면 10K 49:11.

**`src/metrics/darp.py`** — 신규, 전문 그대로(140줄)

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
        races = sg.allout_races(runs, day, hrmax, heat, cold)
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

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -33,5 +33,5 @@
 from src.metrics.cirs import CIRSCalculator
 from src.metrics.di import DICalculator
-from src.metrics.darp import DARPCalculator
+from src.metrics.darp import DARPCalculator, DARPRefCalculator
 from src.metrics.hr_profile import HRProfileCalculator
 from src.metrics.heat_model import HeatModelCalculator
@@ -95,4 +95,5 @@
     HRProfileCalculator(),
     HeatModelCalculator(),
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

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 35 → 36

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 35개)
+        # ALL_CALCULATORS 수 검증 (설계: 36개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 35:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 35개)")
+            if len(ALL_CALCULATORS) != 36:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 36개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 35개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 36개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

**`tests/test_metric_naming.py`** — 수정, 아래 diff 그대로 — 의도된 provider 분리(darp ↔ darp_ref) 허용

````diff
--- a/tests/test_metric_naming.py
+++ b/tests/test_metric_naming.py
@@ -28,12 +28,17 @@
     def test_no_duplicate_produces_across_calculators(self):
         """서로 다른 calculator가 같은 metric_name을 produces하면 안 됨
         (같은 이름은 provider로 구분하므로 허용하되, produces 선언 중복은 의도 확인 필요)."""
+        # 의도된 provider 분리(같은 이름, 다른 provider): darp_ref(runpulse:ref_garmin) ↔ darp(runpulse:formula_v1)
+        provider_split = {frozenset({"darp", "darp_ref"})}
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
python3 -m pytest tests/test_darp_v2.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py tests/test_dashboard_service.py tests/test_ai_context.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-52 — 일별 VDOT 의존 메트릭 복구(marathon_shape·rri·eftp·vdot_adj → `race_pred_vdot`)

- 의존: P7-PRED-51 · UI 노출: 마라톤 셰이프·RRI·eFTP 카드가 **0행 → 값 있음**으로 바뀐다 · 실DB: 재계산 시 생성
- 파일: `src/metrics/marathon_shape.py`, `src/metrics/rri.py`, `src/metrics/eftp.py`, `src/metrics/vdot_adj.py`와 각 테스트
- 왜: 네 calculator가 일별 `runpulse_vdot`(실제로는 활동 scope에만 존재)을 읽어 실DB에서 0행이다(REVIEW-08 #2). 테스트는 존재하지 않는 일별 `runpulse_vdot`을 시드해서 통과하고 있었다.
- `vdot_adj` 폐기 여부는 **사용자 판단 필요**(REVIEW-08 §R3 표) — 이 유닛은 의존만 바꾼다.

**`src/metrics/marathon_shape.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/marathon_shape.py
+++ b/src/metrics/marathon_shape.py
@@ -19,7 +19,7 @@
     version = "1.0"
     scope_type = "daily"
     category = "capacity"
-    requires = ["runpulse_vdot"]
+    requires = ["race_pred_vdot"]
     produces = ["marathon_shape"]
 
     display_name = "Marathon Shape"
@@ -35,7 +35,7 @@
         # VDOT (vdot_adj 우선, 없으면 runpulse_vdot)
         vdot_val = ctx.get_metric("vdot_adj", provider="runpulse:formula_v1")
         if vdot_val is None:
-            vdot_val = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
+            vdot_val = ctx.get_metric("race_pred_vdot", provider="runpulse:formula_v1")
         if vdot_val is None:
             return []
         vdot = float(vdot_val)
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

**`src/metrics/vdot_adj.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/vdot_adj.py
+++ b/src/metrics/vdot_adj.py
@@ -19,7 +19,7 @@
     version = "1.0"
     scope_type = "daily"
     category = "capacity"
-    requires = ["runpulse_vdot"]
+    requires = ["race_pred_vdot"]
     produces = ["vdot_adj"]
 
     display_name = "VDOT 보정"
@@ -31,7 +31,7 @@
     decimal_places = 1
 
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
-        vdot_base_val = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
+        vdot_base_val = ctx.get_metric("race_pred_vdot", provider="runpulse:formula_v1")
         if vdot_base_val is None:
             return []
         vdot_base = float(vdot_base_val)
````

**`tests/test_marathon_shape.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_marathon_shape.py
+++ b/tests/test_marathon_shape.py
@@ -49,7 +49,7 @@
 class TestMarathonShape:
     def test_with_data(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         from datetime import datetime, timedelta
         for i in range(28):
             d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
@@ -70,7 +70,7 @@
 
     def test_json_structure(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         from datetime import datetime, timedelta
         for i in range(28):
             d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
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

**`tests/test_vdot_adj.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_vdot_adj.py
+++ b/tests/test_vdot_adj.py
@@ -49,7 +49,7 @@
 class TestVDOTAdj:
     def test_passthrough(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         _seed_wellness(conn, "2026-04-01")
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = VDOTAdjCalculator().compute(ctx)
@@ -64,7 +64,7 @@
 
     def test_confidence(self):
         conn = _conn()
-        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
+        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
         _seed_wellness(conn, "2026-04-01")
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = VDOTAdjCalculator().compute(ctx)
````

검증:
```
python3 -m pytest tests/test_marathon_shape.py tests/test_rri.py tests/test_eftp.py tests/test_vdot_adj.py -q
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

