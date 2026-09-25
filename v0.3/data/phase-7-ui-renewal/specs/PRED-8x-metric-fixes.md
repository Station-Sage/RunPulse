# PRED-8x — 메트릭 수정 번들 (예측과 별도, 우선순위 표 포함) (예측 리뉴얼 r3, Q12)

근거: `REVIEW-08-metric-audit.md` r3. 코드 명세가 있는 유닛은 autopilot 실행 가능, "판단 필요"는 사용자 결정 전 진행 금지.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## 우선순위 표 (Q12)

| 우선 | 유닛 | 결함(REVIEW-08 번호) | 영향 | 상태 |
|---|---|---|---|---|
| P0 | P7-PRED-13 | `reprocess_all` 이 활동 id 재발급·payload 없는 활동 삭제·랩/스트림 고아(R3-1) | **데이터 파손**(실행 시) | 코드 명세 완료 |
| P0 | P7-PRED-11 | `session_outcomes` 유일 제약 없음 → 매처 저장 항상 실패(R3-4) | 계획 이행 데이터 0 | 코드 명세 완료 |
| P1 | P7-PRED-12 | 스트림 시간축=샘플 인덱스, 거리·GAP 유실, 랩 GAP·기온 유실, 활동 `gap` 0행(#5, R3-2) | 예측·GAP·디커플링 입력 | 코드 명세 완료 |
| P1 | P7-PRED-25 | Garmin LT 파서 키 경로 오류 → garmin_lthr·ftp 0건(R3-6) | 기기 참조 경로 (b) | 코드 명세 완료 |
| P1 | P7-PRED-52 | marathon_shape·rri·eftp·vdot_adj 가 존재하지 않는 일별 VDOT 의존 → 0행(#2) | 예측·화면 | 코드 명세 완료 |
| P1 | **P7-PRED-81** | 활동 시리즈가 비canonical 행 합산 → teroi 28일 TRIMP 2.03배(#3) | 화면·부하 | 아래 |
| P1 | **P7-PRED-84** | runpulse_vdot moving_time 붕괴(287.9, 397.4)(#4) | 예측 입력 | 아래 |
| P2 | **P7-PRED-82** | rec 958일 모두 100(스케일 가정 오류)(#6) | 화면 | 아래 |
| P2 | **P7-PRED-83** | sapi 0행: fearp json 에 기온 없음 + 없는 `weather_cache.temperature` 조회(R3-3) | 화면 | 아래(P7-PRED-32 뒤) |
| P2 | P7-PRED-23 | 분류기 품질 재현율 27%(#8) | 세션·TIDS | 코드 명세 완료 |
| P3 판단 필요 | P7-PRED-86 | `src/weather/provider.py` 가 없는 `weather_data` 테이블 사용(죽은 코드, `_v02_backup/fearp.py`만 참조) | 없음 | 삭제 여부 사용자 결정 |
| P3 판단 필요 | P7-PRED-87 | `recompute-all` 이 runpulse 메트릭을 **전부 지우고 90일만** 다시 계산 | 과거 메트릭 소실 | 기본 기간을 데이터 전체로 바꿀지 결정 |
| P3 판단 필요 | P7-PRED-88 | TIDS 가 세션 **수** 기준이라 이 러너는 v2 분류 뒤에도 "mixed" 79%(사본 재계산: 2025-09 이후 mixed 306·pyramidal 79·polarized 5) | 화면 | 세그먼트 **시간** 기준(Seiler 3구역)으로 재정의할지 결정 |
| P3 판단 필요 | P7-PRED-89 | acwr·lsi 분모 하한 없음(0·5.0 상한 포화), adti·rtti 포화, hrss = trimp×1.54 중복, di 87%가 100 | 화면 | 각각 재정의 여부 결정(REVIEW-08 §5) |
| P3 판단 필요 | P7-PRED-90 | vdot_adj 폐기, fearp 외기 기반 재정의 | 화면 | 결정 |

## P7-PRED-81 — 활동 시리즈 집계를 canonical·primary 로 (teroi·rec·sapi·tpdi·critical_power)

- 의존: P7-PRED-14(`canonical_only`/`primary_only` 인자) · UI 노출: 해당 카드 값 변화(teroi 28일 TRIMP 4,537 → 2,233, 2026-09-25 teroi 0.48 → 0.99) · 실DB: 재계산 시
- 파일: `src/metrics/teroi.py`, `src/metrics/rec.py`(이 줄은 P7-PRED-82가 파일 전체를 다시 바꾸므로 **P7-PRED-82와 한 커밋**), `src/metrics/sapi.py`(P7-PRED-83과 한 커밋), `src/metrics/tpdi.py`, `src/metrics/critical_power.py`
- 변경: 각 `ctx.get_activity_metric_series(...)` 호출에 `canonical_only=True, primary_only=True` 를 붙인다. 아래 diff는 P7-PRED-82·83 변경까지 포함한 최종본이다(teroi·tpdi·critical_power는 이 한 줄씩만 바뀐다).

**`src/metrics/teroi.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/teroi.py
+++ b/src/metrics/teroi.py
@@ -44,7 +44,7 @@
         ctl_start = series[0][1] if series else 0.0
 
         # 28일간 총 TRIMP
-        trimp_series = ctx.get_activity_metric_series("trimp", days=28)
+        trimp_series = ctx.get_activity_metric_series("trimp", days=28, canonical_only=True, primary_only=True)
         total_trimp = sum(d["numeric"] for d in trimp_series) if trimp_series else 0.0
 
         if total_trimp <= 0:
````

**`src/metrics/tpdi.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/tpdi.py
+++ b/src/metrics/tpdi.py
@@ -35,10 +35,10 @@
         start = (td - timedelta(weeks=8)).isoformat()
 
         # 실외/실내 FEARP — CalcContext API
-        outdoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="running")
-        trail_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="trail_running")
+        outdoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="running", canonical_only=True, primary_only=True)
+        trail_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="trail_running", canonical_only=True, primary_only=True)
         outdoor_data = outdoor_data + trail_data
-        indoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="treadmill")
+        indoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="treadmill", canonical_only=True, primary_only=True)
 
         if not outdoor_data or not indoor_data:
             return []
````

**`src/metrics/critical_power.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/critical_power.py
+++ b/src/metrics/critical_power.py
@@ -57,7 +57,7 @@
         powers, durations = [], []
 
         # 1. power_curve JSON에서 — CalcContext API
-        pc_data = ctx.get_activity_metric_series("power_curve", days=84, include_json=True)
+        pc_data = ctx.get_activity_metric_series("power_curve", days=84, include_json=True, canonical_only=True, primary_only=True)
         for entry in pc_data:
             try:
                 raw_json = entry.get("json")
````

검증:
```
python3 -m pytest tests/test_teroi.py tests/test_tpdi.py tests/test_critical_power.py -q
```

## P7-PRED-82 — rec 를 개인 백분위로 재정의 (+ P7-PRED-81 canonical)

- 의존: P7-PRED-14 · UI 노출: REC 카드 값·의미("최근 7일 효율이 내 최근 180일 중 어디쯤") · 실DB: 재계산 시(사본: 2026-09-25 100 → 55.2, 2026-08-01 100 → 14.3)
- 식: `raw_i = EF_i × max(0.5, 1 − decoupling_i/100)`(디커플링 없으면 5%), 현재 = 최근 7일 raw 평균, `REC = 100 × (#{raw_j < 현재} + 0.5·#{raw_j = 현재}) / n`(최근 180일, n ≥ 5). 신뢰도 = min(1, n/30).

**`src/metrics/rec.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/rec.py
+++ b/src/metrics/rec.py
@@ -1,11 +1,12 @@
 """REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.
 
-최근 7일 EF/Decoupling 평균으로 0~100 정규화.
+최근 7일 EF(디커플링 보정)가 본인 최근 180일 분포에서 어디쯤인지(백분위, 0~100).
 
-공식:
-    dec_factor = max(0.5, 1.0 - decoupling/100)
-    raw = ef * dec_factor * form_factor
-    REC = clamp((raw - 0.8) / 1.2 * 100, 0, 100)
+공식 (v2, P7-PRED-82):
+    raw_i = ef_i * max(0.5, 1 - decoupling_i/100)   (활동별, 디커플링 없으면 5%)
+    current = 최근 7일 raw 평균
+    REC = 100 * (#{raw_j < current} + 0.5 * #{raw_j == current}) / n   (j: 최근 180일, n >= 5)
+v1 은 EF 를 m/min/bpm(≈1.2) 로 가정했으나 저장값은 m/s/bpm×1000(≈19) 이라 958일 모두 100 으로 포화됐다.
 
 v0.3 포팅: _v02_backup/rec.py → MetricCalculator 형식
 """
@@ -32,33 +33,22 @@
     format_type = "number"
     decimal_places = 1
 
+    MIN_REF = 5
+
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
-        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
-        target = ctx.scope_id
-        td = date.fromisoformat(target)
-        start = (td - timedelta(days=7)).isoformat()
-
-        # 최근 7일 EF — CalcContext API
-        ef_data = ctx.get_activity_metric_series("efficiency_factor_rp", days=7)
-        if not ef_data:
+        ef = ctx.get_activity_metric_series("efficiency_factor_rp", days=180, canonical_only=True, primary_only=True)
+        dec = {d["activity_id"]: d["numeric"] for d in
+               ctx.get_activity_metric_series("aerobic_decoupling_rp", days=180, canonical_only=True, primary_only=True)}
+        if len(ef) < self.MIN_REF:
             return []
-        ef_avg = sum(d["numeric"] for d in ef_data) / len(ef_data)
-
-        # 최근 7일 Decoupling
-        dec_data = ctx.get_activity_metric_series("aerobic_decoupling_rp", days=7)
-        dec_avg = sum(d["numeric"] for d in dec_data) / len(dec_data) if dec_data else 5.0
-
-        dec_factor = max(0.5, 1.0 - dec_avg / 100)
-        raw = ef_avg * dec_factor
-        rec = min(100, max(0, (raw - 0.8) / 1.2 * 100))
-
-        return [self._result(
-            value=round(rec, 1),
-            json_val={
-                "ef_avg": round(ef_avg, 4),
-                "dec_avg": round(dec_avg, 1),
-                "ef_count": len(ef_data),
-            },
-        
-            confidence=1.0,
-        )]
+        raws = [(d["date"], d["numeric"] * max(0.5, 1.0 - dec.get(d["activity_id"], 5.0) / 100)) for d in ef]
+        cut = (date.fromisoformat(ctx.scope_id) - timedelta(days=7)).isoformat()
+        recent = [r for dt, r in raws if dt > cut]
+        if not recent:
+            return []
+        cur = sum(recent) / len(recent)
+        vals = [r for _, r in raws]
+        rank = (sum(1 for v in vals if v < cur) + 0.5 * sum(1 for v in vals if v == cur)) / len(vals)
+        return [self._result(value=round(100 * rank, 1),
+                             json_val={"current_raw": round(cur, 3), "n_ref": len(vals), "n_recent": len(recent)},
+                             confidence=min(1.0, len(vals) / 30))]
````

**`tests/test_rec.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_rec.py
+++ b/tests/test_rec.py
@@ -79,3 +79,16 @@
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = RECCalculator().compute(ctx)
         assert results[0].category == "efficiency"
+
+
+class TestRECPercentile:
+    def test_recent_best_is_high(self):
+        conn = _conn()
+        for i in range(10):                                  # 과거 EF 18, 최근 7일 EF 21
+            d = f"2026-03-{10 + i:02d}"
+            aid = _seed_activity(conn, d, source_id=f"p{i}")
+            upsert_metric(conn, "activity", str(aid), "efficiency_factor_rp", "runpulse:formula_v1", numeric_value=18.0)
+        aid = _seed_activity(conn, "2026-03-30", source_id="pn")
+        upsert_metric(conn, "activity", str(aid), "efficiency_factor_rp", "runpulse:formula_v1", numeric_value=21.0)
+        r = RECCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
+        assert r[0].numeric_value == round(100 * (10 + 0.5) / 11, 1)     # 95.5
````

검증:
```
python3 -m pytest tests/test_rec.py tests/test_teroi.py tests/test_tpdi.py tests/test_critical_power.py -q
```

## P7-PRED-83 — sapi 기온 입력을 외기 메트릭으로 (+ P7-PRED-81 canonical)

- 의존: P7-PRED-14, P7-PRED-32 · UI 노출: SAPI 카드 0행 → 값 있음(사본 재계산 392일) · 실DB: 재계산 시
- 변경: `_extract_temp`(fearp json·`weather_cache.temperature` — 둘 다 존재하지 않음) 삭제, 활동별 `ctx.get_activity_metric(aid, "weather_temp_c")` 사용(Calculator 내부 raw SQL 제거 — ADR-009).

**`src/metrics/sapi.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/sapi.py
+++ b/src/metrics/sapi.py
@@ -8,7 +8,6 @@
 """
 from __future__ import annotations
 
-import json
 from datetime import date, timedelta
 from src.metrics.base import MetricCalculator, CalcResult, CalcContext
 
@@ -46,15 +45,15 @@
         start = (td - timedelta(days=90)).isoformat()
 
         # FEARP + json (기온 정보 포함) — CalcContext API
-        all_fearp = ctx.get_activity_metric_series("fearp", days=90, include_json=True)
+        all_fearp = ctx.get_activity_metric_series("fearp", days=90, include_json=True, canonical_only=True, primary_only=True)
         if len(all_fearp) < 3:
             return []
-        rows = [(d["numeric"], d.get("json"), d["date"]) for d in all_fearp]
+        rows = [(d["numeric"], d["activity_id"]) for d in all_fearp]
 
         # 기온 구간별 집계
         bin_data: dict[str, list[float]] = {b[0]: [] for b in _TEMP_BINS}
-        for fearp_val, mj_raw, dt in rows:
-            temp = self._extract_temp(mj_raw, ctx.conn, dt)
+        for fearp_val, aid in rows:
+            temp = ctx.get_activity_metric(aid, "weather_temp_c")      # 외기(P7-PRED-32), 없으면 구간 집계에서 제외
             if temp is None:
                 continue
             for label, lo, hi in _TEMP_BINS:
@@ -76,7 +75,7 @@
             return []
 
         # 최근 7일 평균 FEARP
-        recent_fearp = ctx.get_activity_metric_series("fearp", days=7)
+        recent_fearp = ctx.get_activity_metric_series("fearp", days=7, canonical_only=True, primary_only=True)
         if not recent_fearp:
             return []
         current_avg = sum(d["numeric"] for d in recent_fearp) / len(recent_fearp)
@@ -103,24 +102,3 @@
         
             confidence=1.0,
         )]
-
-    @staticmethod
-    def _extract_temp(mj_raw, conn, dt) -> float | None:
-        if mj_raw:
-            try:
-                mj = json.loads(mj_raw) if isinstance(mj_raw, str) else mj_raw
-                temp = mj.get("temperature") or mj.get("temp_c")
-                if temp is not None:
-                    return float(temp)
-            except (json.JSONDecodeError, TypeError):
-                pass
-        try:
-            row = conn.execute(
-                "SELECT temperature FROM weather_cache "
-                "WHERE date=? LIMIT 1", (dt,),
-            ).fetchone()
-            if row and row[0] is not None:
-                return float(row[0])
-        except Exception:
-            pass
-        return None
````

**`tests/test_sapi.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_sapi.py
+++ b/tests/test_sapi.py
@@ -64,6 +64,7 @@
                           "runpulse:formula_v1", numeric_value=300.0,
                           category="rp_performance",
                           json_value={"temp_c": 12.0})
+            upsert_metric(conn, "activity", str(aid), "weather_temp_c", "open_meteo", numeric_value=12.0)
         # 최근 7일 데이터
         for i in range(3):
             conn.execute(
@@ -78,6 +79,7 @@
                           "runpulse:formula_v1", numeric_value=295.0,
                           category="rp_performance",
                           json_value={"temp_c": 12.0})
+            upsert_metric(conn, "activity", str(aid), "weather_temp_c", "open_meteo", numeric_value=12.0)
         conn.commit()
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = SAPICalculator().compute(ctx)
````

검증:
```
python3 -m pytest tests/test_sapi.py -q
```

## P7-PRED-84 — runpulse_vdot 상한 가드

- 의존: 없음 · UI 노출: 활동 VDOT 이상치 사라짐 · 실DB: 재계산 시
- 규칙: VDOT > 85(인간 기록 수준 초과) 이면 저장하지 않는다. 하한은 두지 않는다(이지·트레일의 낮은 값은 "페이스 등가 VDOT"로서 정상 — 예측은 이 메트릭을 쓰지 않는다).

**`src/metrics/vdot.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/vdot.py
+++ b/src/metrics/vdot.py
@@ -30,6 +30,7 @@
     MINIMUM_DISTANCE_M = 1500
     MINIMUM_DURATION_SEC = 300
     MAXIMUM_DURATION_SEC = 14400
+    MAXIMUM_VDOT = 85.0      # 인간 기록(≈85) 초과는 시간 데이터 오류(P7-PRED-84)
 
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
         act = ctx.activity
@@ -56,6 +57,8 @@
             return []
 
         vdot = vo2 / pct_max
+        if vdot > self.MAXIMUM_VDOT:          # moving_time 붕괴(예: 287.9, 397.4) — 기록으로 쓸 수 없는 값
+            return []
 
         confidence = 0.9
         if act.get("activity_type") == "treadmill":
````

**`tests/test_vdot_guard.py`** — 신규, 전문 그대로(19줄)

````python
"""P7-PRED-84: runpulse_vdot moving_time 붕괴 가드."""
from src.metrics.base import CalcContext
from src.metrics.vdot import VDOTCalculator
from tests.helpers_pred import mem_conn, seed_run


def _vd(moving):
    c = mem_conn()
    aid = seed_run(c, sid="1", dist=10000.0, moving=moving)
    return VDOTCalculator().compute(CalcContext(conn=c, scope_type="activity", scope_id=str(aid)))


def test_normal_value():
    r = _vd(2653)
    assert r and r[0].numeric_value == 46.2


def test_collapsed_moving_time_rejected():
    assert _vd(301) == []        # 10km 5분 → VDOT 수백
````

검증:
```
python3 -m pytest tests/test_vdot_guard.py tests/test_activity_calcs.py -q
```

