# PRED-4x — 훈련 반응과 계획↔실행 수용 구조 (예측 리뉴얼 r3, Q11)

근거: `REVIEW-07-prediction-renewal.md` r3 §2-6·4-10·Q11.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-41 — 훈련 반응(일별 `training_response`): 세그먼트 단위 역치 이상 시간·롱런 MP 구간·작업 블록 추세

- 의존: P7-PRED-14, P7-PRED-22, P7-PRED-24, P7-PRED-33 · UI 노출: P7-PRED-74(훈련 반응 카드) · 실DB: 재계산 시 생성
- 파일: `src/metrics/prediction/response.py`, `src/metrics/training_response.py`(신규), `tests/test_training_response.py`(신규), `src/metrics/engine.py`, `src/utils/metric_registry.py`, `scripts/check_docs.py`
- 정의(활동 평균이 아니라 **랩 단위**):
  - 주간 역치 이상 분: LTHR 있으면 랩 평균 HR ≥ 0.92·LTHR, 없으면(T0) 랩 속도(GAP) ≥ 0.90·v_t 인 랩 시간 합. 최근 16주, as_of 당일 제외.
  - `thr_min_avg_8w` / `thr_min_avg_prev_8w`: 최근 8주·그 이전 8주 주평균.
  - 롱런 MP 근접 거리: 최근 56일, 16km 이상 비대회 러닝에서 마라톤 페이스(현재 `race_pred_vdot` 기준) ±4% 랩 거리 합.
  - 작업 블록 추세: 최근 56일 비대회·실외 세션별 최고 연속 블록 VDOT(랩 속도 ÷ 기온 배율로 15℃ 등가)의 선형 기울기(VDOT/4주), 세션 4개 미만이면 None. **진단용 — 예측 가중에 쓰지 않는다**(롤링 백테스트에서 개선 없음, REVIEW-07 r3 §3-4).
- 실측(사본 DB, 2026-09-26): 8주 주평균 27.0분(직전 8주 13.8분), 롱런 MP 구간 2.0km, 추세 n=12.

**`src/metrics/prediction/response.py`** — 신규, 전문 그대로(76줄)

````python
"""훈련 반응(순수) — 주간 역치 이상 시간, 롱런 내 마라톤 페이스 근접 거리, 작업 블록 성과 추세(P7-PRED-41).

runs: get_runs(with_laps=True) 형식. 강도 판정: LTHR 있으면 랩 HR ≥ 0.92·LTHR, 없으면(T0) 랩 속도(GAP) ≥ 0.90·v_t.
"""
from __future__ import annotations

from datetime import date

from src.metrics.prediction.core import best_block, temp_factor

THR_HR_FRAC = 0.92
THR_SPEED_FRAC = 0.90
MP_TOL = 0.04          # 마라톤 페이스 ±4%
LONG_M = 16000.0
EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running", "trail_running")   # 추세에서 제외(속도 신뢰 불가)


def _days(d_from: str, d_to: str) -> int:
    return (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days


def _hard(lap: dict, lthr: float | None, v_t: float | None) -> bool:
    if lthr:
        return bool(lap.get("hr")) and lap["hr"] >= THR_HR_FRAC * lthr
    return bool(v_t) and lap["speed_ms"] >= THR_SPEED_FRAC * v_t


def weekly_threshold_minutes(runs: list[dict], as_of: str, lthr: float | None, v_t: float | None,
                             weeks: int = 16) -> list[float]:
    """[이번 주(as_of 이전 7일), 1주 전, ...] 역치 이상 랩 시간(분)."""
    out = [0.0] * weeks
    for r in runs:
        d = _days(r["date"], as_of)
        if d <= 0 or d > weeks * 7:
            continue
        w = (d - 1) // 7
        out[w] += sum(b["dur_s"] for b in (r.get("laps") or []) if _hard(b, lthr, v_t)) / 60.0
    return [round(x, 1) for x in out]


def long_mp_km(runs: list[dict], as_of: str, v_mp: float, days: int = 56) -> float:
    """최근 56일 롱런(≥16km)에서 마라톤 페이스 ±4% 랩 거리 합(km)."""
    km = 0.0
    for r in runs:
        d = _days(r["date"], as_of)
        if 0 < d <= days and r["distance_m"] >= LONG_M and not r["is_race"]:
            km += sum(b["dist_m"] for b in (r.get("laps") or []) if abs(b["speed_ms"] / v_mp - 1) <= MP_TOL) / 1000.0
    return round(km, 1)


def work_trend(runs: list[dict], as_of: str, lthr: float | None, v_t: float | None, days: int = 56,
               heat: float = -0.62, cold: float = -0.84) -> dict:
    """세션별 최고 작업 블록 VDOT(15℃ 등가: 랩 속도 ÷ temp_factor(run["ambient_c"]))의 선형 추세(VDOT/4주).
    세션 4개 미만이면 slope None."""
    pts = []
    for r in runs:
        d = _days(r["date"], as_of)
        if 0 < d <= days and not r["is_race"] and r["activity_type"] not in EXCLUDE_TYPES:
            f = temp_factor(r.get("ambient_c"), heat, cold)
            laps = [dict(b, speed_ms=b["speed_ms"] / f) for b in (r.get("laps") or [])]
            v = best_block(laps, lthr, None if lthr else v_t, False)
            if v:
                pts.append((-d, v))
    if len(pts) < 4:
        return {"n": len(pts), "slope_4w": None}
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sxx if sxx else 0.0
    return {"n": len(pts), "slope_4w": round(slope * 28, 2), "mean": round(my, 2)}


def summarize(weekly: list[float]) -> dict:
    a = weekly[:8]
    b = weekly[8:16]
    return {"thr_min_avg_8w": round(sum(a) / 8, 1), "thr_min_avg_prev_8w": round(sum(b) / 8, 1) if len(b) == 8 else None}
````

**`src/metrics/training_response.py`** — 신규, 전문 그대로(46줄)

````python
"""훈련 반응(일별) — 역치 이상 주간 시간·롱런 MP 근접 거리·작업 블록 추세(P7-PRED-41). 예측에는 설명·신뢰도로만 쓴다.

produces training_response: numeric = 최근 8주 주평균 역치 이상 분, json = 주별 값·이전 8주·MP 거리·추세·판정 기준.
"""
from __future__ import annotations

import json

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import response as rs
from src.metrics.prediction.core import threshold_speed, time_for_vdot


class TrainingResponseCalculator(MetricCalculator):
    name = "training_response"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "load"
    display_name = "훈련 반응"
    description = "최근 8주 역치 이상 훈련 시간(주평균)과 이전 8주 비교, 롱런 속 마라톤 페이스 구간, 작업 구간 성과 추세."
    unit = "min/wk"
    format_type = "number"
    requires = ["hr_profile", "heat_model", "race_pred_vdot"]
    produces = ["training_response"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        _, js = ctx.get_latest_daily_metric("hr_profile", day, provider="runpulse:formula_v1", include_json=True)
        lthr = json.loads(js)["self"].get("lthr") if js else None
        vd = ctx.get_latest_daily_metric("race_pred_vdot", day, provider="runpulse:formula_v1")
        v_t = threshold_speed(vd) if vd else None
        if not lthr and not v_t:
            return []
        runs = ctx.get_runs(16 * 7, with_laps=True, include_end=False)
        for r in runs:
            r["ambient_c"] = ctx.get_activity_metric(r["id"], "weather_temp_c")
        _, hj = ctx.get_latest_daily_metric("heat_model", day, include_json=True)
        hm = json.loads(hj) if hj else {}
        weekly = rs.weekly_threshold_minutes(runs, day, lthr, v_t)
        out = {"basis": "hr" if lthr else "pace", "lthr": lthr, "v_t": v_t and round(v_t, 3),
               "weekly_thr_min": weekly, **rs.summarize(weekly),
               "trend": rs.work_trend(runs, day, lthr, v_t, heat=hm.get("heat", -0.62), cold=hm.get("cold", -0.84))}
        if vd:
            out["long_mp_km_8w"] = rs.long_mp_km(runs, day, 42195.0 / time_for_vdot(vd, 42195.0))
        return [self._result(value=out["thr_min_avg_8w"], json_val=out, confidence=0.7 if lthr else 0.5)]
````

**`tests/test_training_response.py`** — 신규, 전문 그대로(40줄)

````python
"""P7-PRED-41: 훈련 반응 순수 함수."""
from src.metrics.prediction import response as rs


def _run(date, laps, dist=10000.0, race=False, atype="running", amb=None):
    return {"date": date, "distance_m": dist, "is_race": race, "activity_type": atype, "ambient_c": amb,
            "laps": [{"dist_m": d, "dur_s": t, "speed_ms": d / t, "hr": h} for d, t, h in laps]}


def test_weekly_threshold_minutes_hr_basis():
    runs = [_run("2026-09-25", [(1000, 240, 170), (1000, 300, 150)]),     # 1일 전 → 0주차, 4분
            _run("2026-09-18", [(2000, 480, 175)]),                       # 8일 전 → 1주차, 8분
            _run("2026-09-26", [(1000, 240, 170)])]                       # 당일 → 제외
    w = rs.weekly_threshold_minutes(runs, "2026-09-26", lthr=180.0, v_t=None, weeks=2)
    assert w == [4.0, 8.0]


def test_weekly_threshold_minutes_pace_basis():
    runs = [_run("2026-09-25", [(1000, 250, None), (1000, 330, None)])]   # 4.0 m/s ≥ 0.9×4.0
    assert rs.weekly_threshold_minutes(runs, "2026-09-26", None, 4.0, weeks=1) == [4.2]


def test_long_mp_km():
    v_mp = 3.2
    laps = [(1000, 1000 / 3.2, 150)] * 5 + [(1000, 360, 140)] * 12
    assert rs.long_mp_km([_run("2026-09-20", laps, dist=17000.0)], "2026-09-26", v_mp) == 5.0
    assert rs.long_mp_km([_run("2026-09-20", laps, dist=12000.0)], "2026-09-26", v_mp) == 0.0


def test_work_trend_excludes_treadmill_and_needs_4():
    blk = [(3000, 780, 172)]
    runs = [_run(f"2026-09-{d:02d}", blk) for d in (1, 8, 15)] + [_run("2026-09-20", blk, atype="treadmill")]
    assert rs.work_trend(runs, "2026-09-26", 180.0, None) == {"n": 3, "slope_4w": None}
    runs.append(_run("2026-09-22", blk))
    t = rs.work_trend(runs, "2026-09-26", 180.0, None)
    assert t["n"] == 4 and t["slope_4w"] == 0.0


def test_summarize():
    assert rs.summarize([10.0] * 8 + [5.0] * 8) == {"thr_min_avg_8w": 10.0, "thr_min_avg_prev_8w": 5.0}
````

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -36,4 +36,5 @@
 from src.metrics.hr_profile import HRProfileCalculator
 from src.metrics.heat_model import HeatModelCalculator
+from src.metrics.training_response import TrainingResponseCalculator
 from src.metrics.tids import TIDSCalculator
 from src.metrics.rmr import RMRCalculator
@@ -95,4 +96,5 @@
     HeatModelCalculator(),
     DARPCalculator(),
+    TrainingResponseCalculator(),
     TIDSCalculator(),
     RMRCalculator(),
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -328,4 +328,5 @@
     MetricDef("lt_speed_ref", "hr", "metric", "m/s", "기기 제공 역치 속도(참조)", scope="daily"),
     MetricDef("garmin_ftp", "capacity", "metric", "W", "Garmin 러닝 FTP", scope="daily"),
+    MetricDef("training_response", "load", "metric", "min/wk", "훈련 반응(역치 이상 주간 분·추세)", scope="daily"),
     MetricDef("fearp", "capacity", "metric", "sec/km", "Field-Equivalent Adjusted Running Pace"),
     MetricDef("critical_power", "capacity", "metric", "W", "Critical Power (CP)", scope="daily"),
````

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 34 → 35

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 34개)
+        # ALL_CALCULATORS 수 검증 (설계: 35개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 34:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 34개)")
+            if len(ALL_CALCULATORS) != 35:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 35개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 34개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 35개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

검증:
```
python3 scripts/gen_metric_dictionary.py
python3 -m pytest tests/test_training_response.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-42 — 계획 구조(`structure_json`) 형식 + 계획↔실행 세그먼트 비교(순수)

- 의존: P7-PRED-11(컬럼), P7-PRED-21 · UI 노출: 없음(P7-PRED-43·74)
- 파일: `src/training/outcome_v2.py`(신규), `tests/test_outcome_v2.py`(신규)
- 데이터 모델(세 출처 공통, `planned_workouts`):
  - `source_system`: `runpulse` | `garmin` | `intervals`, `external_id`: 원천 id(Garmin workoutId / Intervals event id), `structure_json`: 아래 형식. 기존 `workout_type`·`distance_km`·`target_pace_*`는 그대로 둔다(구조 없는 계획은 기존 거리·평균 페이스 비교를 유지).
  - `structure_json` = `{"steps": [{"type": "warmup"|"work"|"rest"|"cooldown", "dur_s"|"dist_m": 숫자, "speed_lo"/"speed_hi"(m/s) 또는 "hr_lo"/"hr_hi"(bpm)}, {"type": "repeat", "count": n, "steps": [...]}]}`
- 이행률 = `100 × (0.4·min(1, 실행 세트/계획 세트) + 0.3·볼륨 일치(각 세트 min(r, 1/r) 평균) + 0.3·목표 적중률(목표 범위 ±3%))`. 라벨: 세트 0 → skipped / 세트 다 했고 과반이 목표보다 3% 넘게 빠름 → overperformed / ≥85 → on_target / <60 → underperformed / 그 외 세트 수 다르면 modified, 같으면 underperformed.
- 예측 사용 1단계(`prediction_note`): 최근 4주 구조화 세션이 4개 이상이고 평균 이행률 < 70%면 **느린 쪽 범위만 +1%p** 와 이유 문구. 중앙값 가중은 하지 않는다 — 구조화 세션 20개 이상 쌓인 뒤 롤링 백테스트로 검증해 2단계에서 결정(REVIEW-07 r3 Q11).

**`src/training/outcome_v2.py`** — 신규, 전문 그대로(81줄)

````python
"""계획↔실행 세그먼트 비교(순수, P7-PRED-42) — 계획 단계 구조(structure_json)와 실행 bout(classifier v2 json)를 맞춰 이행률 산출.

structure_json 형식(P7-PRED-42):
  {"steps": [{"type": "warmup", "dur_s": 600},
             {"type": "repeat", "count": 6, "steps": [{"type": "work", "dist_m": 1000, "speed_lo": 3.9, "speed_hi": 4.1},
                                                      {"type": "rest", "dur_s": 90}]},
             {"type": "cooldown", "dur_s": 600}]}
  work 단계는 dist_m 또는 dur_s 중 하나, 목표는 speed_lo/hi(m/s) 또는 hr_lo/hi(bpm) 중 하나(없어도 됨).
"""
from __future__ import annotations

PACE_TOL = 0.03       # 목표 범위 ±3% 까지 적중으로 본다
W_SETS, W_VOL, W_TGT = 0.4, 0.3, 0.3


def expand_work(steps: list[dict]) -> list[dict]:
    """repeat 를 펼쳐 work 단계만 순서대로."""
    out = []
    for s in steps:
        if s.get("type") == "repeat":
            for _ in range(int(s.get("count", 1))):
                out.extend(expand_work(s.get("steps", [])))
        elif s.get("type") == "work":
            out.append(s)
    return out


def _in_target(step: dict, bout: dict) -> bool | None:
    if step.get("speed_lo") and step.get("speed_hi"):
        v = bout["speed_ms"]
        return step["speed_lo"] * (1 - PACE_TOL) <= v <= step["speed_hi"] * (1 + PACE_TOL)
    if step.get("hr_lo") and step.get("hr_hi") and bout.get("hr"):
        return step["hr_lo"] * (1 - PACE_TOL) <= bout["hr"] <= step["hr_hi"] * (1 + PACE_TOL)
    return None


def compare(structure: dict, bouts: list[dict]) -> dict:
    """반환 {"sets_planned", "sets_done", "volume_ratio", "target_hit_pct", "compliance_pct", "label", "pairs"}."""
    plan = expand_work(structure.get("steps", []))
    n_p, n_d = len(plan), len(bouts)
    if n_p == 0:
        return {"sets_planned": 0, "sets_done": n_d, "volume_ratio": None, "target_hit_pct": None,
                "compliance_pct": None, "label": "modified" if n_d else "on_target", "pairs": []}
    pairs, vols, hits = [], [], []
    for st, b in zip(plan, bouts):
        r = b["dist_m"] / st["dist_m"] if st.get("dist_m") else (b["dur_s"] / st["dur_s"] if st.get("dur_s") else None)
        hit = _in_target(st, b)
        if r:
            vols.append(min(r, 1 / r))
        if hit is not None:
            hits.append(hit)
        pairs.append({"ratio": r and round(r, 2), "hit": hit, "speed_ms": round(b["speed_ms"], 3)})
    set_score = min(1.0, n_d / n_p)
    vol = sum(vols) / len(vols) if vols else set_score
    tgt = sum(hits) / len(hits) if hits else 1.0
    comp = round(100 * (W_SETS * set_score + W_VOL * vol + W_TGT * tgt), 1) if n_d else 0.0
    fast = [p for p, st in zip(pairs, plan) if st.get("speed_hi") and p["speed_ms"] > st["speed_hi"] * (1 + PACE_TOL)]
    if n_d == 0:
        label = "skipped"
    elif set_score == 1.0 and len(fast) > len(pairs) / 2:
        label = "overperformed"          # 세트는 다 했고 과반이 목표보다 3% 넘게 빠름
    elif comp >= 85:
        label = "on_target"
    elif comp < 60:
        label = "underperformed"
    else:
        label = "modified" if n_d != n_p else "underperformed"
    return {"sets_planned": n_p, "sets_done": n_d, "volume_ratio": round(vol, 2), "target_hit_pct": round(100 * tgt, 1),
            "compliance_pct": comp, "label": label, "pairs": pairs}


def prediction_note(outcomes: list[dict], min_n: int = 4) -> dict | None:
    """최근 4주 품질 세션 이행 결과 → 예측 1단계 사용(설명·범위만). 가중 반영은 검증 후(P7-PRED-42 §단계)."""
    q = [o for o in outcomes if o.get("compliance_pct") is not None and o.get("sets_planned")]
    if len(q) < min_n:
        return None
    avg = sum(o["compliance_pct"] for o in q) / len(q)
    note = {"n": len(q), "avg_compliance_pct": round(avg, 1), "slow_extra_pct": 0.0, "reason": None}
    if avg < 70:
        note.update(slow_extra_pct=1.0, reason=f"최근 4주 품질 세션 이행률 {avg:.0f}%")
    return note
````

**`tests/test_outcome_v2.py`** — 신규, 전문 그대로(45줄)

````python
"""P7-PRED-42: 계획↔실행 세그먼트 비교."""
from src.training.outcome_v2 import compare, expand_work, prediction_note

PLAN = {"steps": [{"type": "warmup", "dur_s": 600},
                  {"type": "repeat", "count": 6, "steps": [
                      {"type": "work", "dist_m": 1000, "speed_lo": 3.9, "speed_hi": 4.1},
                      {"type": "rest", "dur_s": 90}]},
                  {"type": "cooldown", "dur_s": 600}]}


def _b(d=1000.0, v=4.0, hr=172):
    return {"dist_m": d, "dur_s": d / v, "speed_ms": v, "hr": hr}


def test_expand():
    assert len(expand_work(PLAN["steps"])) == 6


def test_full_on_target():
    r = compare(PLAN, [_b()] * 6)
    assert (r["sets_done"], r["compliance_pct"], r["label"]) == (6, 100.0, "on_target")


def test_five_of_six_sets():                       # 실제 사례: 6회 계획 → 5회 실행
    r = compare(PLAN, [_b()] * 5)
    assert r["compliance_pct"] == round(100 * (0.4 * 5 / 6 + 0.3 + 0.3), 1) == 93.3
    assert r["label"] == "on_target"


def test_slow_and_short():
    r = compare(PLAN, [_b(d=800, v=3.6)] * 4)
    assert r["target_hit_pct"] == 0.0 and r["label"] == "underperformed"
    assert r["compliance_pct"] == round(100 * (0.4 * 4 / 6 + 0.3 * 0.8 + 0), 1)


def test_fast():
    assert compare(PLAN, [_b(v=4.4)] * 6)["label"] == "overperformed"


def test_skipped_and_note():
    assert compare(PLAN, [])["label"] == "skipped"
    outs = [{"compliance_pct": 60, "sets_planned": 6}] * 4
    assert prediction_note(outs) == {"n": 4, "avg_compliance_pct": 60.0, "slow_extra_pct": 1.0,
                                     "reason": "최근 4주 품질 세션 이행률 60%"}
    assert prediction_note(outs[:3]) is None
````

검증:
```
python3 -m pytest tests/test_outcome_v2.py -q
```

## P7-PRED-43 — 매처에 세그먼트 이행 결과 저장 (session_outcomes v2)

- 의존: P7-PRED-11(유일 제약·컬럼), P7-PRED-23(분류기 bouts), P7-PRED-42 · UI 노출: P7-PRED-74 · 실DB: 다음 매칭부터(기존 계획 소급은 P7-PRED-61 6단계)
- 파일: `src/training/outcome_store.py`(신규), `src/training/matcher.py`, `tests/test_outcome_store.py`(신규)
- 동작: 매칭 성공 시 `update_outcome_v2(conn, plan_id, activity_id)` — 계획에 `structure_json`이 있으면 분류기 json의 `bouts`와 비교해 `compliance_pct`, `segment_match_json`, `source_system`, `outcome_label`(v2 라벨로 덮음)을 쓰고, Garmin 랩 `compliance_score`(워크아웃 단계 랩만, 시간가중)를 `source_compliance`로 쓴다. 구조가 없으면 `source_compliance`만.
- 실측(사본 DB): P7-PRED-11 유일 제약 적용 후 2026-09-21 주 매칭 2건 저장(기존에는 0건 — 저장 SQL이 항상 실패).

**`src/training/outcome_store.py`** — 신규, 전문 그대로(46줄)

````python
"""세그먼트 이행 결과 저장(P7-PRED-43) — 매칭된 계획·활동 쌍에 v2 비교(outcome_v2.compare)와 소스 컴플라이언스를 기록.

planned_workouts.structure_json 이 있을 때만 v2 비교를 하고, 없으면 기존(거리·평균 페이스) 결과를 그대로 둔다.
source_compliance: Garmin 랩 compliance_score 의 시간가중 평균(작업 단계 매칭 랩만, wkt_step_index 있는 랩), 없으면 None.
"""
from __future__ import annotations

import json
import sqlite3

from src.training.outcome_v2 import compare


def _classifier_bouts(conn, activity_id: int) -> list[dict] | None:
    r = conn.execute("SELECT json_value FROM metric_store WHERE scope_type='activity' AND scope_id=? "
                     "AND metric_name='workout_type_classified' AND is_primary=1", (str(activity_id),)).fetchone()
    if not r or not r[0]:
        return None
    return json.loads(r[0]).get("bouts") or []


def _garmin_compliance(conn, activity_id: int) -> float | None:
    rows = conn.execute("SELECT compliance_score, duration_sec FROM activity_laps WHERE activity_id=? "
                        "AND compliance_score IS NOT NULL AND wkt_step_index IS NOT NULL", (activity_id,)).fetchall()
    t = sum(d or 0 for _, d in rows)
    return round(sum(c * (d or 0) for c, d in rows) / t, 1) if t else None


def update_outcome_v2(conn: sqlite3.Connection, planned_id: int, activity_id: int) -> dict | None:
    """session_outcomes(planned_id) 행에 v2 결과를 덧쓴다. 반환: compare() 결과 또는 None(구조 없음·분류 없음)."""
    p = conn.execute("SELECT structure_json, COALESCE(source_system, source) FROM planned_workouts WHERE id=?",
                     (planned_id,)).fetchone()
    src_c = _garmin_compliance(conn, activity_id)
    if not p or not p[0]:
        if src_c is not None:
            conn.execute("UPDATE session_outcomes SET source_compliance=?, source_system='garmin' WHERE planned_id=?",
                         (src_c, planned_id))
        return None
    bouts = _classifier_bouts(conn, activity_id)
    if bouts is None:
        return None
    res = compare(json.loads(p[0]), bouts)
    conn.execute("UPDATE session_outcomes SET compliance_pct=?, segment_match_json=?, source_compliance=?, "
                 "source_system=?, outcome_label=? WHERE planned_id=?",
                 (res["compliance_pct"], json.dumps(res, ensure_ascii=False), src_c, p[1], res["label"], planned_id))
    return res
````

**`src/training/matcher.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/training/matcher.py
+++ b/src/training/matcher.py
@@ -17,6 +17,8 @@
 import logging
 import sqlite3
 from datetime import date, timedelta
+
+from src.training.outcome_store import update_outcome_v2
 
 log = logging.getLogger(__name__)
 
@@ -87,6 +89,7 @@
                 plan_dist=plan_dist, plan_pace=pace_min, plan_hr_zone=hr_zone,
                 act_row=best,
             )
+            update_outcome_v2(conn, plan_id, best[0])      # 구조화된 계획이면 세그먼트 이행률(P7-PRED-43)
             matched += 1
 
     if matched:
````

**`tests/test_outcome_store.py`** — 신규, 전문 그대로(38줄)

````python
"""P7-PRED-43: 매칭 → 세그먼트 이행률 저장."""
import json
from datetime import date

from src.training.matcher import match_week_activities
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run
from tests.test_outcome_v2 import PLAN


def _setup(structure=True):
    c = mem_conn()
    aid = seed_run(c, sid="1", date="2026-09-22", dist=9000.0, moving=2700)
    seed_laps(c, aid, [(1000, 250, 170, "INTERVAL", None, None)] * 2)
    c.execute("UPDATE activity_laps SET compliance_score=80, wkt_step_index=1 WHERE activity_id=?", (aid,))
    bouts = [{"dist_m": 1000.0, "dur_s": 250.0, "speed_ms": 4.0, "hr": 172}] * 5
    upsert_metric(c, "activity", str(aid), "workout_type_classified", "runpulse:rule_v2", text_value="interval",
                  json_value={"type": "interval", "bouts": bouts})
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, structure_json, source_system) "
              "VALUES ('2026-09-22', 'interval', 9.0, 'planner', ?, 'runpulse')",
              (json.dumps(PLAN) if structure else None,))
    return c, aid


def test_structured_plan_gets_compliance():
    c, aid = _setup()
    assert match_week_activities(c, date(2026, 9, 21)) == 1
    row = c.execute("SELECT compliance_pct, source_compliance, source_system, outcome_label, segment_match_json "
                    "FROM session_outcomes").fetchone()
    assert row[:4] == (93.3, 80.0, "runpulse", "on_target")
    assert json.loads(row[4])["sets_done"] == 5


def test_unstructured_plan_keeps_legacy_label():
    c, aid = _setup(structure=False)
    match_week_activities(c, date(2026, 9, 21))
    row = c.execute("SELECT compliance_pct, source_compliance, outcome_label FROM session_outcomes").fetchone()
    assert row[0] is None and row[1] == 80.0 and row[2] is not None
````

검증:
```
python3 -m pytest tests/test_outcome_store.py tests/test_outcome_v2.py -q
```

## P7-PRED-44 — 외부 계획 인제스트(Garmin 예정 워크아웃, Intervals 계획 이벤트) — **조사 + 구현, 사람 확인 필요(mode manual)**

- 의존: P7-PRED-42 · UI 노출: Plan 화면(출처 배지) · **실DB/API: 필요**(autopilot 실행 환경에는 계정 API가 없다 → 사람이 첫 응답을 저장해 형태를 확정한 뒤 파서 구현)
- 확인된 사실: Garmin 활동 payload에 `workoutId`(135개), 랩 `wktStepIndex`·`directWorkoutComplianceScore`(약 200개)가 있고, Intervals 활동에 `paired_event_id`(8)·`compliance`(9)가 있다. 계획 자체(예정 워크아웃·이벤트)는 수집하지 않는다.
- 계약(구현 시 지킬 것):
  1. 원문은 `source_payloads(source, entity_type='planned_workout', entity_id=<외부 id>)`로 먼저 저장.
  2. 파서는 순수 함수 `parse_garmin_workout(payload) -> dict`, `parse_intervals_event(payload) -> dict` 로 P7-PRED-42 `structure_json` 형식과 `date`·`workout_type`·`distance_km`를 만든다. 알 수 없는 단계 유형은 `work`가 아니라 건너뛰고 경고 로그.
  3. `planned_workouts`에 `source='garmin'|'intervals'`, `source_system` 같은 값, `external_id`로 UPSERT(같은 external_id 재수집 시 갱신). 앱 자체 계획(`source_system='runpulse'`)과 같은 날짜가 겹치면 둘 다 두고 매처는 `external_id` 있는 쪽을 우선.
  4. 활동의 `workoutId`/`paired_event_id`가 있으면 날짜 매칭보다 그것을 우선해 매칭.
- 첫 단계(사람): Garmin `get_workouts()`/`get_scheduled_workout_by_id()`(또는 캘린더), Intervals `GET /api/v1/athlete/{id}/events?oldest=&newest=&category=WORKOUT` 응답 각 1건을 저장하고 이 절에 실제 필드를 기록 → 그다음 autopilot 유닛으로 파서·테스트 명세를 확정한다.

