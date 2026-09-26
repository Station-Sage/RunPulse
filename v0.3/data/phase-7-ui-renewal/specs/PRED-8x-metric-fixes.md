# PRED-8x — 메트릭 수정 번들 (예측과 별도, 우선순위 표 포함) (예측 리뉴얼 r4)

근거: `REVIEW-08-metric-audit.md` r3. 근거 `REVIEW-08-metric-audit.md` §R4. 모든 유닛이 코드 명세를 갖는다(85~90 사용자 승인).

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
| P3 **승인** | P7-PRED-86 | `src/weather/provider.py` 가 없는 `weather_data` 테이블 사용(죽은 코드) | 없음 | **통합**(단일 Open-Meteo 클라이언트) — `PRED-3x` |
| P3 **승인** | P7-PRED-87 | `recompute-all` 이 runpulse 메트릭을 **전부 지우고 90일만** 다시 계산 | 과거 메트릭 소실 | 기본 기간을 데이터 전체로 바꿀지 결정 |
| P3 **승인** | P7-PRED-88 | TIDS 가 세션 **수** 기준이라 이 러너는 v2 분류 뒤에도 "mixed" 79%(사본 재계산: 2025-09 이후 mixed 306·pyramidal 79·polarized 5) | 화면 | 세그먼트 **시간** 기준(Seiler 3구역)으로 재정의할지 결정 |
| P3 **승인** | P7-PRED-89 | acwr·lsi 분모 하한 없음(0·5.0 상한 포화), adti·rtti 포화, hrss = trimp×1.54 중복, di 87%가 100 | 화면 | 각각 재정의 여부 결정(REVIEW-08 §5) |
| P3 **승인** | P7-PRED-90 | vdot_adj 폐기, fearp 외기 기반 재정의 | 화면 | 결정 |
| P2 **승인(2026-09-26)** | P7-PRED-85 | 내장 Daniels 표가 공식과 불일치 + 없는 `src.metrics.daniels_table` import(R4-1·R4-2) | 플래너 처방 페이스 | 아래 |

87~90·85는 사용자 승인으로 자동 유닛이 됐다. 각 정의의 생리학적 근거는 REVIEW-08 §R4.

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

## P7-PRED-87 — `recompute-all` 기본 기간 = 데이터 전 기간, 삭제 범위 = 재계산 범위 — **승인**

- 의존: 없음 · UI 노출: 없음 · 실DB: 없음(도구 동작만). 런북(P7-PRED-61)은 계속 `recompute --days 1100`을 쓴다.
- 파일: `src/metrics/engine.py`, `src/metrics/cli.py`, `tests/test_recompute_all_range.py`(신규), `tests/test_phase4_dod.py`
- 결함(REVIEW-08 R3-7): `recompute_all(days=90)`이 runpulse 메트릭을 **전부 지운 뒤 90일만** 다시 계산해 과거 이력이 사라졌다.
- 규칙:
  - `days=None`(기본)이면 가장 이른 활동일부터 오늘까지 계산한다.
  - `days`를 주면 최근 days일만 계산한다.
  - 삭제는 `clear_runpulse_metrics(conn, start, end)`로 그 기간 일별 행과 그 기간 활동의 활동 행만 한다.
  - CLI `recompute-all [--days N]`.

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로 — 기간 한정 삭제·전 기간 기본

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -637,9 +637,16 @@
 
 
-def clear_runpulse_metrics(conn: sqlite3.Connection) -> int:
-    """RunPulse 계산 메트릭만 삭제 (소스 메트릭 보존)."""
-    cur = conn.execute(
-        "DELETE FROM metric_store WHERE provider LIKE 'runpulse%'"
-    )
+def clear_runpulse_metrics(conn: sqlite3.Connection, start: str | None = None, end: str | None = None) -> int:
+    """RunPulse 계산 메트릭만 삭제 (소스 메트릭 보존). start~end(YYYY-MM-DD)를 주면 그 기간의 일별 행과
+    그 기간 활동의 활동 행만 삭제한다(P7-PRED-87 — 재계산하지 않는 과거 이력을 지우지 않는다)."""
+    if start is None and end is None:
+        cur = conn.execute("DELETE FROM metric_store WHERE provider LIKE 'runpulse%'")
+    else:
+        lo, hi = start or "0000-00-00", end or "9999-12-31"
+        cur = conn.execute(
+            "DELETE FROM metric_store WHERE provider LIKE 'runpulse%' AND ("
+            " (scope_type = 'daily' AND scope_id BETWEEN ? AND ?) OR"
+            " (scope_type = 'activity' AND scope_id IN (SELECT CAST(id AS TEXT) FROM activity_summaries"
+            "   WHERE substr(start_time, 1, 10) BETWEEN ? AND ?)))", (lo, hi, lo, hi))
     deleted = cur.rowcount
     conn.commit()
@@ -684,10 +691,18 @@
 
 
-def recompute_all(conn: sqlite3.Connection, days: int = 90,
+def recompute_all(conn: sqlite3.Connection, days: int | None = None,
                   on_progress=None) -> dict:
-    """전체 재계산: RunPulse 메트릭 삭제 → 활동 → 일별 순서로 재실행."""
-    clear_runpulse_metrics(conn)
+    """재계산 범위의 RunPulse 메트릭만 삭제 → 활동 → 일별 순서로 재실행(P7-PRED-87).
+
+    days=None(기본)이면 가장 이른 활동일부터 오늘까지 전 기간. days 를 주면 최근 days 일(가장 이른 활동일 이전은 자르고),
+    그 범위 밖 이력은 삭제하지 않는다(이전 동작: 전부 삭제 후 90일만 재계산 → 과거 메트릭 소실, REVIEW-08 R3-7).
+    """
     today = date.today()
-    dates = [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
+    first = conn.execute("SELECT min(substr(start_time, 1, 10)) FROM activity_summaries").fetchone()[0]
+    start = date.fromisoformat(first) if first else today
+    if days is not None:
+        start = max(start, today - timedelta(days=days - 1))
+    dates = [(start + timedelta(days=i)).isoformat() for i in range((today - start).days + 1)]
+    clear_runpulse_metrics(conn, dates[0], dates[-1])
     return _recompute_dates(conn, dates, on_progress=on_progress)
 
````

**`src/metrics/cli.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/cli.py
+++ b/src/metrics/cli.py
@@ -66,7 +66,8 @@
     p_recompute = sub.add_parser("recompute", help="최근 N일 재계산")
     p_recompute.add_argument("--days", type=int, default=7)
 
-    sub.add_parser("recompute-all", help="전체 재계산 (90일)")
+    p_all = sub.add_parser("recompute-all", help="재계산(기본: 전 기간, 범위 밖 이력은 보존)")
+    p_all.add_argument("--days", type=int, default=None)
     sub.add_parser("recompute-missing", help="부하(TRIMP) 누락 활동 보정 + CTL/ATL/TSB 재계산")
     sub.add_parser("clear", help="RunPulse 메트릭 삭제")
 
@@ -99,8 +100,8 @@
         print(f"완료: {len(results)}일 처리")
 
     elif args.command == "recompute-all":
-        print("전체 재계산 중 (90일)...")
-        results = recompute_all(conn)
+        print("재계산 중 (" + (f"최근 {args.days}일" if args.days else "전 기간") + ", 범위 밖 이력 보존)...")
+        results = recompute_all(conn, days=args.days)
         print(f"완료: {len(results)}일 처리")
 
     elif args.command == "recompute-missing":
````

**`tests/test_recompute_all_range.py`** — 신규, 전문 그대로(31줄)

````python
"""P7-PRED-87: recompute_all 이 재계산 범위 밖 이력을 지우지 않는다."""
from datetime import date, timedelta

from src.metrics.engine import clear_runpulse_metrics, recompute_all
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_run


def test_clear_range_keeps_history():
    c = mem_conn()
    old = seed_run(c, sid="old", date="2025-01-10")
    new = seed_run(c, sid="new", date="2026-09-20")
    for aid in (old, new):
        upsert_metric(c, "activity", str(aid), "trimp", "runpulse:formula_v1", numeric_value=50.0)
    upsert_metric(c, "daily", "2025-01-10", "ctl", "runpulse:formula_v1", numeric_value=30.0)
    upsert_metric(c, "daily", "2026-09-20", "ctl", "runpulse:formula_v1", numeric_value=40.0)
    upsert_metric(c, "daily", "2026-09-20", "garmin_x", "garmin", numeric_value=1.0)
    assert clear_runpulse_metrics(c, "2026-09-01", "2026-09-30") == 2
    left = {(r[0], r[1]) for r in c.execute("SELECT scope_id, metric_name FROM metric_store")}
    assert left == {(str(old), "trimp"), ("2025-01-10", "ctl"), ("2026-09-20", "garmin_x")}


def test_recompute_all_default_spans_all_history():
    c = mem_conn()
    first = (date.today() - timedelta(days=40)).isoformat()
    seed_run(c, sid="a", date=first)
    upsert_metric(c, "daily", "2000-01-01", "ctl", "runpulse:formula_v1", numeric_value=1.0)   # 활동 이전 행은 범위 밖
    res = recompute_all(c)
    assert len(res) == 41
    assert c.execute("SELECT count(*) FROM metric_store WHERE scope_id='2000-01-01'").fetchone()[0] == 1
    assert len(recompute_all(c, days=5)) == 5
````

**`tests/test_phase4_dod.py`** — 수정, 아래 diff 그대로 — 멱등 테스트: 시드 행을 먼저 비운다

````diff
--- a/tests/test_phase4_dod.py
+++ b/tests/test_phase4_dod.py
@@ -152,5 +152,6 @@
         conn = _conn()
         _seed_full(conn, days=10)
-        # 첫 번째 계산
+        # 첫 번째 계산 — recompute_all 은 범위 밖 행을 지우지 않으므로(P7-PRED-87) 시드 행을 먼저 비운다
+        clear_runpulse_metrics(conn)
         first = recompute_all(conn, days=7)
         first_count = conn.execute(
````

검증:
```
python3 -m pytest tests/test_recompute_all_range.py tests/test_phase4_dod.py tests/test_engine.py -q
python3 scripts/check_docs.py
```

## P7-PRED-88 — TIDS: 세션 수 → 세그먼트 **시간** 기준(Seiler 3구간, 경계 = Daniels M·T 속도) — **승인**

- 의존: P7-PRED-14, P7-PRED-20, P7-PRED-21 · UI 노출: TIDS 카드 분포·패턴 값이 바뀐다 · 실DB: 재계산 시
- 파일: `src/metrics/tids.py`(**전문 교체**), `tests/test_tids_time.py`(신규), `tests/test_phase4_dod.py`
- 결함: 세션 수 기준이라, 70%가 이지인 세션도 "고강도 1회"로 셌다 → 이 러너는 "mixed" 79%로 포화됐다(REVIEW-08 #8).
- 정의:
  - 구간: 랩 시간(GAP)을 Z1(< Daniels M 속도), Z2(M~T), Z3(> T)으로 나눈다. 경계는 최신 `race_pred_vdot`(기본 경로)이다. 없으면 산출하지 않는다.
  - 패턴: PI = log10(Z1/Z2 × Z3 × 100) > 2이면 polarized(Treff 2019 [가정 — 원문 확인 U-1]), 그 외는 Z1 ≥ Z2 ≥ Z3이면 pyramidal, 나머지는 threshold/mixed다.
  - HR 교차 확인은 json 참고값으로만 둔다.

**`src/metrics/tids.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(74줄)

````python
"""TIDS (Training Intensity Distribution Score) — 8주 러닝 시간의 3구간 분포(P7-PRED-88, REVIEW-08 §R4).

세션 수가 아니라 랩 시간으로 센다(세션 수 기준은 품질 세션의 70%가 이지 시간이어도 "고강도 1회"로 세어 포화 → mixed 94.5%).
구간 경계(기기 불필요, Daniels 식): Z1 < M 속도 ≤ Z2 < T 속도 ≤ Z3. M·T 는 최신 race_pred_vdot 에서 계산한다
(Seiler 3구간의 LT1·LT2 를 M·T 로 근사 [가정]). 패턴: Z2 최대 → threshold, Z1 > Z3 > Z2 이고 극화 지수
PI = log10(Z1/Z2 × Z3 × 100) > 2 → polarized(Treff 2019 [가정: 원문 확인]), Z1 ≥ Z2 ≥ Z3 → pyramidal, 그 외 mixed.
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction.daniels import zone_speeds

EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running")
MIN_RUNS = 5


def distribution(runs: list[dict], v_m: float, v_t: float) -> dict | None:
    """runs(get_runs with_laps) → {"z1","z2","z3"} 시간 %. 랩 없는 활동은 활동 평균 속도 1블록."""
    t = [0.0, 0.0, 0.0]
    for r in runs:
        if r["activity_type"] in EXCLUDE_TYPES:
            continue
        blocks = r.get("laps") or ([{"dur_s": r["moving_s"], "speed_ms": r["distance_m"] / r["moving_s"]}] if r["moving_s"] else [])
        for b in blocks:
            v = b["speed_ms"] or 0.0
            t[0 if v < v_m else (1 if v < v_t else 2)] += b["dur_s"] or 0.0
    tot = sum(t)
    if not tot:
        return None
    return {"z1": round(t[0] / tot * 100, 1), "z2": round(t[1] / tot * 100, 1), "z3": round(t[2] / tot * 100, 1)}


def pattern(d: dict) -> tuple[str, float | None]:
    z1, z2, z3 = d["z1"], d["z2"], d["z3"]
    pi = round(math.log10(z1 / 100 / max(z2 / 100, 1e-3) * z3 / 100 * 100), 2) if z3 > 0 else None
    if z2 >= z1 and z2 >= z3:
        return "threshold", pi
    if z1 > z3 > z2 and pi is not None and pi > 2.0:
        return "polarized", pi
    if z1 >= z2 >= z3:
        return "pyramidal", pi
    return "mixed", pi


class TIDSCalculator(MetricCalculator):
    name = "tids"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "load"

    display_name = "강도 분포 (TIDS)"
    description = "8주 러닝 시간의 3구간(마라톤 페이스 미만·마라톤~역치·역치 이상) 분포와 패턴(polarized/threshold/pyramidal/mixed)."
    format_type = "json"
    requires = ["race_pred_vdot"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        vd = ctx.get_latest_daily_metric("race_pred_vdot", ctx.scope_id, provider="runpulse:formula_v1")
        runs = ctx.get_runs(56, with_laps=True)
        if not vd or len(runs) < MIN_RUNS:
            return []
        z = zone_speeds(vd)
        d = distribution(runs, z["M"], z["T"])
        if d is None:
            return []
        pat, pi = pattern(d)
        return [self._result(
            json_val={"basis": "time", "low_pct": d["z1"], "mid_pct": d["z2"], "high_pct": d["z3"], "pattern": pat,
                      "polarization_index": pi, "vdot": round(vd, 2),
                      "m_pace_sec_km": round(1000 / z["M"]), "t_pace_sec_km": round(1000 / z["T"])},
            text=pat,
        )]
````

**`tests/test_tids_time.py`** — 신규, 전문 그대로(18줄)

````python
"""P7-PRED-88: TIDS 시간 기준."""
from src.metrics.tids import distribution, pattern


def _run(laps):
    return {"activity_type": "running", "moving_s": 0, "distance_m": 0, "laps": [{"dur_s": s, "speed_ms": v} for s, v in laps]}


def test_time_based_distribution_and_patterns():
    v_m, v_t = 1000 / 296, 1000 / 276
    runs = [_run([(3000, 2.8)]), _run([(600, 2.8), (1200, 3.7), (300, 2.9)]), _run([(2400, 3.2)])]
    d = distribution(runs, v_m, v_t)
    assert d == {"z1": 84.0, "z2": 0.0, "z3": 16.0} and pattern(d)[0] == "polarized"
    assert pattern({"z1": 80.0, "z2": 15.0, "z3": 5.0})[0] == "pyramidal"
    assert pattern({"z1": 30.0, "z2": 50.0, "z3": 20.0})[0] == "threshold"
    assert pattern({"z1": 60.0, "z2": 10.0, "z3": 30.0}) == ("polarized", 2.26)
    assert pattern({"z1": 40.0, "z2": 25.0, "z3": 35.0})[0] == "mixed"
    assert distribution([], v_m, v_t) is None
````

**`tests/test_phase4_dod.py`** — 수정, 아래 diff 그대로 — TIDS 는 race_pred_vdot 이 있어야 산출

````diff
--- a/tests/test_phase4_dod.py
+++ b/tests/test_phase4_dod.py
@@ -315,4 +315,5 @@
         conn.commit()
         from src.metrics.tids import TIDSCalculator
+        upsert_metric(conn, "daily", "2026-03-31", "race_pred_vdot", "runpulse:formula_v1", numeric_value=45.0)
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = TIDSCalculator().compute(ctx)
````

검증:
```
python3 -m pytest tests/test_tids_time.py tests/test_phase4_dod.py tests/test_activity_calcs.py -q
```

## P7-PRED-89 — 부하·내구 메트릭 재정의: acwr·lsi·adti·rtti·hrss·di — **승인**

- 의존: P7-PRED-14 · UI 노출: 해당 카드 값·"데이터 부족" 상태 · 실DB: 재계산 시
- 파일: `src/metrics/acwr.py`, `lsi.py`, `adti.py`, `rtti.py`, `hrss.py`, `di.py`(**전문 교체**), `tests/test_di_v2.py`(신규), `tests/test_activity_core_sanitize.py`, `tests/test_daily_calcs.py`, `tests/test_rtti.py`, `tests/test_engine.py`
- 정의(REVIEW-08 §R4, 생리학 검토):
  - acwr: CTL < 10 이거나 28일 전 CTL 이력이 없으면 산출하지 않는다("데이터 부족"). 5.0 절단은 없앤다. DB 없는 목 컨텍스트는 이력 판단을 건너뛴다.
  - lsi: 최근 활동일 7일 미만이면 산출하지 않는다(분모 하한).
  - adti: 원 변화율 그대로, 표시 범위 ±2(포화 제거).
  - rtti: acwr과 같은 가드를 두고 200 절단은 없앤다.
  - hrss = 100 × TRIMP ÷ (LTHR로 60분 달린 TRIMP)다. 1시간 역치 = 100(hrTSS 정의)이다. LTHR은 자체 `lthr_self`, 없으면 0.917·HRmax다.
  - di = 90분 이상 러닝에서 워밍업 10분 뒤 앞 25% 대비 뒤 25%의 효율(GAP 속도/HR) 비 × 100이다. 상한은 없고, HR이 없으면 속도 비를 쓴다.

**`src/metrics/acwr.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/acwr.py
+++ b/src/metrics/acwr.py
@@ -1,4 +1,5 @@
-"""ACWR Calculator — 설계서 4-3 기준.
+"""ACWR Calculator — 설계서 4-3 기준. P7-PRED-89: 만성 부하가 형성되기 전(CTL < 10 또는 28일 전 CTL 없음)엔
+산출하지 않는다("데이터 수집 중") — 이전엔 5.0으로 잘라 저장해 공백기 복귀일이 "위험"으로 보였다.
 
 ACWR = ATL / CTL. 최적 범위: 0.8~1.3.
 """
@@ -7,7 +8,8 @@
 from src.metrics.base import CalcContext, CalcResult, MetricCalculator
 
 
-_ACWR_CAP = 5.0
+MIN_CTL = 10.0          # (c) 만성 부하 하한(TRIMP/일). 이 러너 CTL 중앙 ~50
+HISTORY_DAYS = 28      # (a) EWMA 42일 상수에서 28일이면 정상상태의 약 49%
 
 
 class ACWRCalculator(MetricCalculator):
@@ -33,7 +35,15 @@
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
         atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
         ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
-        if atl is None or ctl is None or ctl == 0:
+        if atl is None or ctl is None or ctl < MIN_CTL or not has_history(ctx):
             return []
-        # CTL이 매우 작을 때(데이터 시작, 휴식 후 복귀) 비율이 무한히 커지므로 ranges 상한으로 캡
-        return [self._result(value=min(round(atl / ctl, 2), _ACWR_CAP))]
+        return [self._result(value=round(atl / ctl, 2))]
+
+
+def has_history(ctx: CalcContext) -> bool:
+    """28일 전에도 CTL 이 있었는가(만성 부하 형성 여부). DB 없는 컨텍스트(목)는 판단 불가 → True."""
+    if getattr(ctx, "conn", None) is None:
+        return True
+    from datetime import date, timedelta
+    d = (date.fromisoformat(ctx.scope_id) - timedelta(days=HISTORY_DAYS)).isoformat()
+    return ctx.get_latest_daily_metric("ctl", d, provider="runpulse:formula_v1") is not None
````

**`src/metrics/lsi.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/lsi.py
+++ b/src/metrics/lsi.py
@@ -1,6 +1,7 @@
 """LSI (Load Spike Index) Calculator — 설계서 4-3 기준.
 
 LSI = 당일 부하 / 21일 롤링 평균. >1.5 = 급격한 부하 증가.
+P7-PRED-89: 21일 중 부하 있는 날이 7일 미만이면 분모가 휴식기로 작아져 폭발한다(2024-06-28 LSI 101) → 산출하지 않음.
 """
 from __future__ import annotations
 
@@ -30,6 +31,7 @@
     requires = ["trimp"]
 
     ROLLING_DAYS = 21
+    MIN_ACTIVE_DAYS = 7    # (c) 주 2~3회 러너의 3주 최소 활동일
 
     def compute(self, ctx: CalcContext) -> list[CalcResult]:
         date_str = ctx.scope_id
@@ -44,7 +46,7 @@
             daily_loads.append(self._get_day_load(ctx, d))
 
         avg_load = sum(daily_loads) / len(daily_loads) if daily_loads else 0
-        if avg_load == 0:
+        if avg_load == 0 or sum(1 for x in daily_loads if x > 0) < self.MIN_ACTIVE_DAYS:
             return []
 
         return [self._result(value=round(today_load / avg_load, 2))]
````

**`src/metrics/adti.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/adti.py
+++ b/src/metrics/adti.py
@@ -1,6 +1,7 @@
 """ADTI (Adaptive Training Trend Index) — 설계서 4-4 기준.
 
-4주간 CTL 변화율 + 부하 패턴 → 훈련 적응 방향 (-100 ~ +100).
+4주간 CTL 변화율(%) → 훈련 적응 방향. P7-PRED-89: 이전엔 ×5 후 ±100 절단이라 26%가 포화 →
+변화율(%)을 그대로 저장(상·하한 없음). 해석 밴드 ±2%(이전 ±10 스케일과 같은 경계).
 """
 from __future__ import annotations
 
@@ -16,13 +17,13 @@
     display_name = "훈련 추세 (ADTI)"
     description = "28일간 CTL 변화율. 양수=상승, 음수=하락."
     unit = ""
-    ranges = {"declining": [-100, -10], "stable": [-10, 10], "building": [10, 100]}
+    ranges = {"declining": [-100, -2], "stable": [-2, 2], "building": [2, 100]}
     higher_is_better = True
     decimal_places = 1
     display_name = "훈련 추세 (ADTI)"
     description = "28일간 CTL 변화율. 양수=상승, 음수=하락."
     unit = ""
-    ranges = {"declining": [-100, -10], "stable": [-10, 10], "building": [10, 100]}
+    ranges = {"declining": [-100, -2], "stable": [-2, 2], "building": [2, 100]}
     higher_is_better = True
     decimal_places = 1
     requires = ["ctl"]
@@ -43,6 +44,4 @@
             return []
 
         change_pct = ((avg_second - avg_first) / avg_first) * 100
-        adti = max(-100, min(100, change_pct * 5))
-
-        return [self._result(value=round(adti, 1))]
+        return [self._result(value=round(change_pct, 2))]
````

**`src/metrics/rtti.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/rtti.py
+++ b/src/metrics/rtti.py
@@ -2,6 +2,7 @@
 
 ATL / (CTL × wellness_factor) × 100
 100 = 적정, >100 과부하, <70 여유.
+P7-PRED-89: CTL 이 형성되기 전(ACWR 과 같은 기준)엔 산출하지 않고, 200 절단을 없앴다(이전 15%가 0 또는 200에 포화).
 
 v0.3 포팅: _v02_backup/rtti.py → MetricCalculator 형식
 """
@@ -37,7 +38,8 @@
         atl = float(atl) if atl is not None else 0.0
         ctl = float(ctl) if ctl is not None else 0.0
 
-        if ctl <= 0 and atl <= 0:
+        from src.metrics.acwr import MIN_CTL, has_history
+        if ctl < MIN_CTL or not has_history(ctx):
             return []
 
         # 웰니스 보정
@@ -60,13 +62,8 @@
                     wf *= 0.92
 
         # CTL 기반 용량
-        if ctl <= 0:
-            capacity = max(atl * 0.5, 10.0)
-        else:
-            capacity = ctl * wf
-
-        rtti = round(atl / capacity * 100, 1) if capacity > 0 else 0.0
-        rtti = min(rtti, 200.0)
+        capacity = ctl * wf
+        rtti = round(atl / capacity * 100, 1)
 
         return [self._result(
             value=rtti,
````

**`src/metrics/hrss.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/hrss.py
+++ b/src/metrics/hrss.py
@@ -1,6 +1,7 @@
 """HRSS Calculator — 설계서 4-2 기준.
 
 HRSS = TRIMP / TRIMP_ref × 100 (1hr LTHR = 100).
+P7-PRED-89: LTHR 을 hr_profile 자체 추정(lthr_self)에서 읽는다. 이전엔 항상 0.85·HRmax 로 추정해 TRIMP 의 상수배(1.54)였다.
 """
 from __future__ import annotations
 
@@ -31,7 +32,9 @@
         if trimp is None:
             return []
 
-        lthr = ctx.get_metric("lactate_threshold_hr") or self._estimate_lthr(ctx)
+        day = ((ctx.activity or {}).get("start_time") or "")[:10] if getattr(ctx, "conn", None) is not None else ""
+        lthr = (ctx.get_metric("lactate_threshold_hr")
+                or (ctx.get_latest_daily_metric("lthr_self", day) if day else None) or self._estimate_lthr(ctx))
         if not lthr:
             return []
 
@@ -50,4 +53,4 @@
 
     def _estimate_lthr(self, ctx):
         max_hr = TRIMPCalculator()._get_max_hr(ctx)
-        return int(max_hr * 0.85) if max_hr else None
+        return round(max_hr * 0.917, 1) if max_hr else None      # hr_profile 폴백과 같은 비율
````

**`src/metrics/di.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(71줄)

````python
"""DI (Durability Index) v2 — 90분 이상 러닝에서 후반 효율 유지율(P7-PRED-89).

효율 = 랩 GAP 속도 ÷ 랩 평균 HR. 워밍업(처음 10분)을 뺀 나머지 시간의 앞 25% 대 뒤 25% 효율 비 × 100.
HR 이 없는 활동은 속도 비만 쓴다(json basis). 상한 없음 — 후반이 더 효율적이면 100을 넘는다(네거티브 스플릿).
v1(스트림 절반 속도 비, 0~100 절단)은 100이 87%로 포화였다(REVIEW-08 #7). 더위·탈수에 따른 HR 드리프트가 섞인다.
"""
from __future__ import annotations

from statistics import mean

from src.metrics.base import CalcContext, CalcResult, MetricCalculator

MIN_DURATION_SEC = 5400      # 90분
WARMUP_SEC = 600             # 앞 10분 제외
QUARTER = 0.25
WINDOW_DAYS = 56


def _quarter_eff(laps: list[dict], use_hr: bool) -> tuple[float, float] | None:
    """워밍업 뒤 앞 25%·뒤 25% 시간 구간의 효율(시간 가중). 랩 경계는 시간 비율로 나눠 넣는다."""
    t0, pts = 0.0, []
    for b in laps:
        if not b["dur_s"] or not b["speed_ms"] or (use_hr and not b["hr"]):
            t0 += b["dur_s"] or 0
            continue
        pts.append((t0, t0 + b["dur_s"], b["speed_ms"] / b["hr"] if use_hr else b["speed_ms"]))
        t0 += b["dur_s"]
    body = t0 - WARMUP_SEC
    if body <= 0 or not pts:
        return None

    def win(a: float, z: float) -> float | None:
        w = s = 0.0
        for x0, x1, e in pts:
            ov = min(x1, z) - max(x0, a)
            if ov > 0:
                w += ov
                s += ov * e
        return s / w if w >= 0.5 * (z - a) else None

    first = win(WARMUP_SEC, WARMUP_SEC + QUARTER * body)
    last = win(t0 - QUARTER * body, t0)
    return (first, last) if first and last else None


class DICalculator(MetricCalculator):
    name = "di"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "capacity"
    display_name = "내구성 지수 (DI)"
    description = "90분 이상 러닝에서 워밍업 뒤 앞 25% 대비 뒤 25%의 효율(GAP 속도/HR) 유지율. 100 = 유지, 상한 없음."
    unit = "점"
    higher_is_better = True
    decimal_places = 1
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        runs = [r for r in ctx.get_runs(WINDOW_DAYS, with_laps=True)
                if (r["moving_s"] or 0) >= MIN_DURATION_SEC and len(r.get("laps") or []) >= 4]
        per = []
        for r in runs:
            use_hr = all(b["hr"] for b in r["laps"])
            q = _quarter_eff(r["laps"], use_hr)
            if q:
                per.append({"date": r["date"], "ratio": round(q[1] / q[0] * 100, 1), "basis": "ef" if use_hr else "pace"})
        if not per:
            return []
        return [self._result(value=round(mean(p["ratio"] for p in per), 1),
                             json_val={"runs": per[-8:], "n": len(per), "window_days": WINDOW_DAYS})]
````

**`tests/test_di_v2.py`** — 신규, 전문 그대로(28줄)

````python
"""P7-PRED-89: DI v2 — 랩 기반 후반 효율 유지율, 상한 없음."""
import json

from src.metrics.base import CalcContext
from src.metrics.di import DICalculator
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def _long(c, sid, date, hr_late, speed_late_s=300):
    rid = seed_run(c, sid=sid, date=date, name="롱런", dist=20000.0, moving=6000, avg_hr=150, max_hr=165)
    seed_laps(c, rid, [(1000, 300, 140, "ACTIVE", None, None)] * 10 + [(1000, speed_late_s, hr_late, "ACTIVE", None, None)] * 10)


def test_drift_lowers_di_and_no_cap():
    c = mem_conn()
    _long(c, "a", "2026-09-10", 154)          # 후반 HR +10% → 효율 ≈ 91
    r = DICalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26"))
    assert 88 < r[0].numeric_value < 94 and json.loads(r[0].json_value)["runs"][0]["basis"] == "ef"
    c2 = mem_conn()
    _long(c2, "b", "2026-09-10", 135, 290)    # 후반이 더 빠르고 HR 낮음 → 100 초과
    r2 = DICalculator().compute(CalcContext(conn=c2, scope_type="daily", scope_id="2026-09-26"))
    assert r2[0].numeric_value > 100


def test_short_runs_empty():
    c = mem_conn()
    seed_run(c, sid="s", date="2026-09-10", moving=3000)
    assert DICalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")) == []
````

**`tests/test_activity_core_sanitize.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_activity_core_sanitize.py
+++ b/tests/test_activity_core_sanitize.py
@@ -75,6 +75,7 @@
         for name, val in (("atl", atl), ("ctl", ctl)):
             upsert_metric(conn, "daily", "2026-04-01", name, "runpulse:formula_v1",
                           numeric_value=val, category="rp_load")
+        upsert_metric(conn, "daily", "2026-03-04", "ctl", "runpulse:formula_v1", numeric_value=40.0, category="rp_load")  # 28일 전 CTL(P7-PRED-89)
         conn.commit()
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         return ACWRCalculator().compute(ctx)
@@ -82,8 +83,14 @@
     def test_ratio_below_cap_is_unchanged(self):
         assert self._compute(atl=60.0, ctl=50.0)[0].numeric_value == 1.2
 
-    def test_extreme_ratio_is_capped(self):
-        assert self._compute(atl=17.8, ctl=3.3)[0].numeric_value == 5.0
+    def test_low_chronic_load_returns_empty(self):
+        assert self._compute(atl=17.8, ctl=3.3) == []          # P7-PRED-89: 5.0 절단 대신 "데이터 수집 중"
+
+    def test_no_history_returns_empty(self):
+        conn = _conn()
+        for name, val in (("atl", 60.0), ("ctl", 50.0)):
+            upsert_metric(conn, "daily", "2026-04-01", name, "runpulse:formula_v1", numeric_value=val, category="rp_load")
+        assert ACWRCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")) == []
 
     def test_zero_ctl_returns_empty(self):
         assert self._compute(atl=10.0, ctl=0.0) == []
````

**`tests/test_daily_calcs.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_daily_calcs.py
+++ b/tests/test_daily_calcs.py
@@ -68,6 +68,7 @@
                        "runpulse:formula_v1", numeric_value=80.0, category="rp_load")
         upsert_metric(conn, "daily", "2026-04-01", "ctl",
                        "runpulse:formula_v1", numeric_value=60.0, category="rp_load")
+        upsert_metric(conn, "daily", "2026-03-04", "ctl", "runpulse:formula_v1", numeric_value=40.0, category="rp_load")  # 28일 전 CTL(P7-PRED-89)
         conn.commit()
         ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
         results = ACWRCalculator().compute(ctx)
````

**`tests/test_rtti.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_rtti.py
+++ b/tests/test_rtti.py
@@ -11,6 +11,7 @@
     conn.row_factory = sqlite3.Row
     conn.execute("PRAGMA foreign_keys = ON")
     create_tables(conn)
+    upsert_metric(conn, "daily", "2026-03-04", "ctl", "runpulse:formula_v1", numeric_value=40.0)   # 28일 전 CTL(P7-PRED-89)
     return conn
 
 
````

**`tests/test_engine.py`** — 수정, 아래 diff 그대로 — 28일 전 CTL·부하 이력 시드

````diff
--- a/tests/test_engine.py
+++ b/tests/test_engine.py
@@ -30,6 +30,19 @@
     conn.commit()
 
 
+def _seed_load_history(conn, days: int = 42, trimp: float = 60.0):
+    """기준일(2026-04-01) 이전 매일 러닝 1개 + trimp — CTL ≥ MIN_CTL 과 28일 전 이력을 만든다(P7-PRED-89)."""
+    from datetime import date, timedelta
+    for i in range(1, days + 1):
+        d = (date(2026, 4, 1) - timedelta(days=i)).isoformat()
+        cur = conn.execute(
+            "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m, "
+            "moving_time_sec, avg_hr, max_hr, avg_speed_ms) VALUES (?,?,?,?,?,?,?,?,?,?)",
+            ["garmin", f"h{i}", "Run", "running", f"{d} 07:00:00", 8000, 2700, 145, 170, 2.96])
+        upsert_metric(conn, "activity", str(cur.lastrowid), "trimp", "runpulse:formula_v1", numeric_value=trimp)
+    conn.commit()
+
+
 class TestTopologicalSort:
     def test_trimp_before_hrss(self):
         sorted_calcs = _topological_sort(ALL_CALCULATORS)
@@ -137,6 +150,8 @@
         """cirs_acwr 행의 parent_metric_id가 cirs 행의 id와 일치해야 한다."""
         conn = _conn()
         _seed_full(conn)
+        upsert_metric(conn, "daily", "2026-03-04", "ctl", "runpulse:formula_v1", numeric_value=40.0)   # 28일 전 CTL(P7-PRED-89)
+        _seed_load_history(conn)   # 활동 1개로는 CTL < MIN_CTL 이라 acwr 가 보류된다(P7-PRED-89)
         run_activity_metrics(conn, 1)
         conn.commit()
         run_daily_metrics(conn, "2026-04-01")
````

검증:
```
python3 -m pytest tests/test_di_v2.py tests/test_activity_core_sanitize.py tests/test_daily_calcs.py tests/test_rtti.py tests/test_engine.py tests/test_cirs.py tests/test_crs.py -q
python3 scripts/check_docs.py
```

## P7-PRED-90 — vdot_adj 폐기 + fearp 외기·이슬점 재정의 — **승인**

- 의존: P7-PRED-32(외기 메트릭), P7-PRED-51 이전에도 동작(읽는 쪽이 `race_pred_vdot` 없으면 기존처럼 None). UI 노출: 대시보드·리포트·플래너의 VDOT 출처가 `race_pred_vdot`(대표 = r3 (c))로 바뀐다. · 실DB: 재계산 시. 기존 vdot_adj 행은 남지만 읽지 않는다.
- 파일:
  - 삭제: `src/metrics/vdot_adj.py`, `tests/test_vdot_adj.py`
  - 수정: `src/metrics/engine.py`, `scripts/check_docs.py`, `src/metrics/fearp.py`, `src/web/views_dashboard.py`, `src/web/views_report_sections_data.py`, `src/training/planner_config.py`, `src/training/readiness.py`, `src/services/plan_template_service.py`, `tests/test_readiness.py`, `tests/test_plan_template_service.py`
  - 신규: `tests/test_fearp_v2.py`
- 왜: vdot_adj는 없는 일별 `runpulse_vdot`에 의존해 0행이었다. 역할(현재 VDOT)은 예측 결합 VDOT가 대신한다. fearp는 손목 온도·0행 습도를 썼다.
- fearp v2:
  - 더위: 외기(`weather_temp_c`) + 이슬점(`weather_dew_point_c`)의 화씨 합 표로 보정한다(러너 실무 표, (c)). 이슬점이 없으면 15℃ 초과 1℃당 0.5%, 외기가 없으면 더위 보정은 생략한다(기기 온도 미사용).
  - 추위: 5℃ 미만 1℃당 0.3%. 오르막: 경사 1%당 2%. 둘 다 (c).
  - json: temp_c, dew_point_c, adjust_pct.

**`src/metrics/vdot_adj.py`** — 삭제 — 폐기(P7-PRED-90)

````text
(git rm src/metrics/vdot_adj.py)
````

**`tests/test_vdot_adj.py`** — 삭제 — 폐기(P7-PRED-90)

````text
(git rm tests/test_vdot_adj.py)
````

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로 — VDOTAdjCalculator 제거

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -49,5 +49,4 @@
 from src.metrics.rri import RRICalculator
 from src.metrics.eftp import EFTPCalculator
-from src.metrics.vdot_adj import VDOTAdjCalculator
 from src.metrics.marathon_shape import MarathonShapeCalculator
 from src.metrics.crs import CRSCalculator
@@ -108,5 +107,4 @@
     RRICalculator(),
     EFTPCalculator(),
-    VDOTAdjCalculator(),
     MarathonShapeCalculator(),
     CRSCalculator(),
````

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 34 → 33

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 34개)
+        # ALL_CALCULATORS 수 검증 (설계: 33개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 34:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 34개)")
+            if len(ALL_CALCULATORS) != 33:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 33개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 34개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 33개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

**`src/metrics/fearp.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/fearp.py
+++ b/src/metrics/fearp.py
@@ -1,16 +1,37 @@
-"""FEARP (Fitness & Environment Adjusted Running Pace) — 설계서 4-4 기준.
+"""FEARP (Fitness & Environment Adjusted Running Pace) v2 — 외기 기온·이슬점·고도로 보정한 환경 보정 페이스(P7-PRED-90).
 
-실제 페이스를 기온/습도/고도로 보정한 환경 보정 페이스.
+더위: 외기(weather_temp_c) + 이슬점(weather_dew_point_c)의 화씨 합으로 보정률을 정한다(러너 실무 표, (c) 휴리스틱:
+합 100°F 이하 0%, 110 0.5%, 120 1%, 130 2%, 140 3%, 150 4.5%, 160 6%, 170 8%, 180+ 10% — 사이는 선형).
+이슬점이 없으면 외기만으로 15℃ 초과 1℃당 0.5%. 외기가 없으면 기기 온도(손목, 체온 영향)는 쓰지 않고 더위 보정 생략.
+추위: 5℃ 미만 1℃당 0.3% (c). 오르막: 평균 경사 1%당 2% (c).
 """
 from __future__ import annotations
 
 from src.metrics.base import CalcContext, CalcResult, MetricCalculator
 
 
+_HEAT_TABLE = ((100, 0.0), (110, 0.5), (120, 1.0), (130, 2.0), (140, 3.0), (150, 4.5), (160, 6.0), (170, 8.0), (180, 10.0))
+
+
+def heat_penalty(temp_c: float | None, dew_c: float | None) -> float:
+    """외기·이슬점 → 더위 보정률(%). 이슬점 없으면 15℃ 초과 1℃당 0.5%."""
+    if temp_c is None:
+        return 0.0
+    if dew_c is None:
+        return max(0.0, temp_c - 15) * 0.5
+    s = (temp_c * 9 / 5 + 32) + (dew_c * 9 / 5 + 32)
+    if s <= _HEAT_TABLE[0][0]:
+        return 0.0
+    for (x0, y0), (x1, y1) in zip(_HEAT_TABLE, _HEAT_TABLE[1:]):
+        if s <= x1:
+            return y0 + (y1 - y0) * (s - x0) / (x1 - x0)
+    return _HEAT_TABLE[-1][1]
+
+
 class FEARPCalculator(MetricCalculator):
     name = "fearp"
     provider = "runpulse:formula_v1"
-    version = "1.0"
+    version = "2.0"
     scope_type = "activity"
     category = "capacity"
     display_name = "FEARP (환경 보정 페이스)"
@@ -38,36 +59,18 @@
             else:
                 return []
 
-        temp = act.get("avg_temperature")
+        temp = ctx.get_metric("weather_temp_c")          # 외기(P7-PRED-32). 기기 온도는 쓰지 않는다
+        dew = ctx.get_metric("weather_dew_point_c")
         elevation = act.get("elevation_gain") or 0
         distance_m = act.get("distance_m") or 0
 
-        adjustment = 1.0
-
-        if temp is not None:
-            if temp > 15:
-                adjustment += (temp - 15) * 0.005
-            elif temp < 5:
-                adjustment += (5 - temp) * 0.003
-
+        adjustment = 1.0 + heat_penalty(temp, dew) / 100.0
+        if temp is not None and temp < 5:
+            adjustment += (5 - temp) * 0.003
         if distance_m > 0 and elevation > 0:
-            grade_pct = (elevation / distance_m) * 100
-            adjustment += grade_pct * 0.02
-
-        humidity = ctx.get_metric("weather_humidity_pct")
-        if humidity is not None and humidity > 60:
-            adjustment += (humidity - 60) * 0.001
-
+            adjustment += (elevation / distance_m) * 100 * 0.02
         fearp = pace / adjustment
 
-        # confidence: 보정 데이터 가용성에 따라 조정
-        conf = 0.6  # 기본 (페이스만 있는 경우)
-        if temp is not None:
-            conf += 0.15
-        if humidity is not None:
-            conf += 0.1
-        if elevation and elevation > 0:
-            conf += 0.15
-        conf = min(conf, 1.0)
-
-        return [self._result(value=round(fearp, 1), confidence=conf)]
+        conf = 0.6 + (0.15 if temp is not None else 0) + (0.1 if dew is not None else 0) + (0.15 if elevation > 0 else 0)
+        return [self._result(value=round(fearp, 1), confidence=min(conf, 1.0),
+                             json_val={"temp_c": temp, "dew_point_c": dew, "adjust_pct": round((adjustment - 1) * 100, 2)})]
````

**`tests/test_fearp_v2.py`** — 신규, 전문 그대로(10줄)

````python
"""P7-PRED-90: fearp v2 — 외기·이슬점 보정, 기기 온도 미사용."""
from src.metrics.fearp import heat_penalty


def test_heat_penalty_table():
    assert heat_penalty(None, None) == 0.0
    assert heat_penalty(10.0, 5.0) == 0.0                      # 50+41 = 91°F
    assert abs(heat_penalty(25.0, 20.0) - 3.8) < 0.1           # 77+68 = 145°F → 3~4.5% 사이
    assert heat_penalty(40.0, 30.0) == 10.0                    # 상한
    assert heat_penalty(25.0, None) == 5.0                     # 이슬점 없음 → 15℃ 초과 1℃당 0.5%
````

**`src/web/views_dashboard.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/web/views_dashboard.py
+++ b/src/web/views_dashboard.py
@@ -172,7 +172,7 @@
     """VDOT + MarathonShape 조회 (metric_store daily)."""
     vdot_row = conn.execute(
         "SELECT numeric_value FROM metric_store"
-        " WHERE scope_type='daily' AND metric_name IN ('vdot_adj','runpulse_vdot')"
+        " WHERE scope_type='daily' AND metric_name='race_pred_vdot' AND is_primary=1"   # vdot_adj 폐기(P7-PRED-90)
         "   AND numeric_value IS NOT NULL AND scope_id<=?"
         " ORDER BY scope_id DESC LIMIT 1",
         (target_date,),
````

**`src/web/views_report_sections_data.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/web/views_report_sections_data.py
+++ b/src/web/views_report_sections_data.py
@@ -94,7 +94,7 @@
     """VDOT + Marathon Shape 최신값 (metric_store daily)."""
     vdot_row = conn.execute(
         "SELECT numeric_value FROM metric_store"
-        " WHERE scope_type='daily' AND metric_name IN ('vdot_adj','runpulse_vdot')"
+        " WHERE scope_type='daily' AND metric_name='race_pred_vdot' AND is_primary=1"   # vdot_adj 폐기(P7-PRED-90)
         "   AND numeric_value IS NOT NULL AND scope_id<=?"
         " ORDER BY scope_id DESC LIMIT 1",
         (end,),
````

**`src/training/planner_config.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/training/planner_config.py
+++ b/src/training/planner_config.py
@@ -129,10 +129,10 @@
 
 
 def get_vdot_adj(conn: sqlite3.Connection) -> float | None:
-    """VDOT_ADJ 조회 (최근)."""
+    """현재 VDOT 조회 (최근) — vdot_adj 폐기(P7-PRED-90) 후 레이스 예측 결합 VDOT(race_pred_vdot, 대표 provider)."""
     row = conn.execute(
         "SELECT numeric_value FROM metric_store"
-        " WHERE metric_name='vdot_adj' AND scope_type='daily' AND is_primary=1"
+        " WHERE metric_name='race_pred_vdot' AND scope_type='daily' AND is_primary=1"
         "   AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1"
     ).fetchone()
     return float(row[0]) if row else None
````

**`src/training/readiness.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/training/readiness.py
+++ b/src/training/readiness.py
@@ -290,7 +290,7 @@
     required_vdot = _vdot_from_race(distance_m, goal_time_sec)
 
     # ── 2. 현재 VDOT_ADJ 로드 ──────────────────────────────────────────
-    current_vdot = _get_recent_metric(conn, "VDOT_ADJ", days_back=30)
+    current_vdot = _get_recent_metric(conn, "race_pred_vdot", days_back=30)   # vdot_adj 폐기(P7-PRED-90)
 
     # ── 3. 보조 메트릭 로드 ────────────────────────────────────────────
     di_val   = _get_recent_metric(conn, "DI",   days_back=14)
````

**`src/services/plan_template_service.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/services/plan_template_service.py
+++ b/src/services/plan_template_service.py
@@ -40,12 +40,12 @@
 
 
 def _get_current_vdot(conn: sqlite3.Connection) -> float | None:
-    """metric_store에서 최근 30일 이내 가장 최근 VDOT_ADJ 조회."""
+    """metric_store에서 최근 30일 이내 가장 최근 VDOT 조회(race_pred_vdot — vdot_adj 폐기, P7-PRED-90)."""
     since = (date.today() - timedelta(days=30)).isoformat()
     today = date.today().isoformat()
     row = conn.execute(
         "SELECT numeric_value FROM metric_store"
-        " WHERE metric_name='VDOT_ADJ' AND scope_type='daily' AND is_primary=1"
+        " WHERE metric_name='race_pred_vdot' AND scope_type='daily' AND is_primary=1"
         "   AND scope_id<=? AND scope_id>=? AND numeric_value IS NOT NULL"
         " ORDER BY scope_id DESC LIMIT 1",
         (today, since),
````

**`tests/test_readiness.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_readiness.py
+++ b/tests/test_readiness.py
@@ -181,10 +181,10 @@
 
 @pytest.fixture
 def populated_conn(empty_conn):
-    """VDOT_ADJ=45, DI=60, RTTI=85 데이터가 있는 DB."""
+    """race_pred_vdot=45, DI=60, RTTI=85 데이터가 있는 DB."""
     today = date.today().isoformat()
     rows = [
-        ("daily", today, "VDOT_ADJ", 45.0),
+        ("daily", today, "race_pred_vdot", 45.0),
         ("daily", today, "DI",       60.0),
         ("daily", today, "RTTI",     85.0),
     ]
````

**`tests/test_plan_template_service.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_plan_template_service.py
+++ b/tests/test_plan_template_service.py
@@ -25,7 +25,7 @@
     conn.execute(
         "INSERT INTO metric_store "
         "(metric_name, scope_type, scope_id, numeric_value, is_primary, provider) "
-        "VALUES ('VDOT_ADJ', 'daily', ?, ?, 1, 'test')",
+        "VALUES ('race_pred_vdot', 'daily', ?, ?, 1, 'test')",
         (day, vdot),
     )
     conn.commit()
````

검증:
```
python3 scripts/gen_metric_dictionary.py
python3 -m pytest tests/test_fearp_v2.py tests/test_readiness.py tests/test_plan_template_service.py tests/test_sapi.py tests/test_engine.py tests/test_phase4_dod.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-85 — 내장 Daniels 페이스 표 → 공식 + 없는 import 경로 수정 — **승인(2026-09-26)**

- 의존: P7-PRED-20 · UI 노출: **플래너 처방 페이스가 바뀐다**. 예: VDOT 45 T 4:18 → 4:36/km, VDOT 50 T 3:59 → 4:13/km. · 실DB: 없음
- 파일: `src/utils/daniels_table.py`, `src/ai/tool_exec_context.py`, `src/training/interval_calc.py`, `src/training/planner_rules.py`, `tests/test_daniels_table.py`
- 결함(REVIEW-08 R4-1·R4-2):
  - `VDOT_PACE_TABLE`이 Daniels 식과 맞지 않는다. 표 T의 %VO2max가 VDOT에 따라 0.997→0.861로 흘러간다.
  - 세 파일이 없는 `src.metrics.daniels_table`을 import한다. 그래서 플래너는 조용히 config로 폴백하고 `prescribe_from_vdot`은 ImportError를 낸다.
- 변경:
  - 페이스 표를 삭제하고 `prediction.daniels.zone_speeds`로 계산한다. E는 %VO2max 0.59~0.74 중간 속도, R은 1마일 레이스 속도의 400m 시간이다.
  - `vdot_to_t_pace`·`t_pace_to_vdot`는 60분 레이스 식으로 계산한다. 볼륨 표는 유지한다.
  - VDOT 50 값: M 4:31·T 4:13·R 400m 87초. 원서 값과 ±5초 안이다(원서 대조 U-1).

**`src/utils/daniels_table.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/daniels_table.py
+++ b/src/utils/daniels_table.py
@@ -1,7 +1,9 @@
-"""Jack Daniels VDOT 룩업 테이블 — Running Formula 3rd Edition 기반.
+"""Jack Daniels VDOT 유틸 — 훈련 페이스·레이스 시간은 Daniels–Gilbert 공식(`metrics/prediction/daniels.py`)으로 계산,
+권장 볼륨만 표 보간.
 
-VDOT별 훈련 페이스, 레이스 예측 시간, 권장 볼륨을 정확히 제공.
-선형 보간으로 중간값도 지원.
+P7-PRED-85: 이전 페이스 표(VDOT_PACE_TABLE)는 공식과 불일치했다(표 T의 %VO2max가 VDOT 30→85에서 0.997→0.861로 변동,
+공식은 60분 레이스 강도 고정). E = %VO2max 0.59~0.74 범위의 중간 속도, M = 마라톤 레이스, T = 60분 레이스,
+I = vVO2max(%VO2max 1.0), R = 1마일 레이스 속도(400m 시간으로 반환).
 
 v0.3 포팅: src/metrics/_v02_backup/daniels_table.py → src/utils/daniels_table.py
 """
@@ -10,94 +12,9 @@
 import math
 from typing import Any
 
+from src.metrics.prediction.daniels import threshold_speed, zone_speeds
+from src.metrics.prediction.daniels import vdot as _race_vdot
 
-# ── VDOT → 페이스 테이블 (sec/km) ──────────────────────────────────────
-# E=Easy, M=Marathon, T=Threshold, I=Interval, R=Repetition
-# 출처: Jack Daniels "Daniels' Running Formula" 3rd Ed, Table 3.1~3.2
-
-VDOT_PACE_TABLE: list[dict[str, Any]] = [
-    {"vdot": 30, "E": 437, "M": 384, "T": 348, "I": 318, "R": 72},
-    {"vdot": 31, "E": 427, "M": 375, "T": 340, "I": 311, "R": 70},
-    {"vdot": 32, "E": 418, "M": 366, "T": 333, "I": 304, "R": 69},
-    {"vdot": 33, "E": 409, "M": 358, "T": 325, "I": 298, "R": 67},
-    {"vdot": 34, "E": 400, "M": 350, "T": 318, "I": 292, "R": 66},
-    {"vdot": 35, "E": 392, "M": 342, "T": 311, "I": 286, "R": 64},
-    {"vdot": 36, "E": 384, "M": 335, "T": 305, "I": 280, "R": 63},
-    {"vdot": 37, "E": 377, "M": 328, "T": 299, "I": 275, "R": 62},
-    {"vdot": 38, "E": 370, "M": 321, "T": 293, "I": 270, "R": 61},
-    {"vdot": 39, "E": 363, "M": 315, "T": 287, "I": 265, "R": 60},
-    {"vdot": 40, "E": 356, "M": 309, "T": 282, "I": 260, "R": 59},
-    {"vdot": 41, "E": 350, "M": 303, "T": 277, "I": 256, "R": 58},
-    {"vdot": 42, "E": 344, "M": 298, "T": 272, "I": 251, "R": 57},
-    {"vdot": 43, "E": 338, "M": 293, "T": 267, "I": 247, "R": 56},
-    {"vdot": 44, "E": 333, "M": 288, "T": 263, "I": 243, "R": 55},
-    {"vdot": 45, "E": 327, "M": 283, "T": 258, "I": 239, "R": 54},
-    {"vdot": 46, "E": 322, "M": 279, "T": 254, "I": 235, "R": 53},
-    {"vdot": 47, "E": 317, "M": 274, "T": 250, "I": 232, "R": 53},
-    {"vdot": 48, "E": 312, "M": 270, "T": 247, "I": 228, "R": 52},
-    {"vdot": 49, "E": 308, "M": 266, "T": 243, "I": 225, "R": 51},
-    {"vdot": 50, "E": 303, "M": 259, "T": 239, "I": 222, "R": 50},
-    {"vdot": 51, "E": 299, "M": 255, "T": 236, "I": 219, "R": 50},
-    {"vdot": 52, "E": 295, "M": 252, "T": 233, "I": 216, "R": 49},
-    {"vdot": 53, "E": 291, "M": 248, "T": 230, "I": 213, "R": 48},
-    {"vdot": 54, "E": 287, "M": 245, "T": 227, "I": 211, "R": 48},
-    {"vdot": 55, "E": 283, "M": 242, "T": 224, "I": 208, "R": 47},
-    {"vdot": 56, "E": 280, "M": 239, "T": 221, "I": 206, "R": 47},
-    {"vdot": 57, "E": 276, "M": 236, "T": 219, "I": 203, "R": 46},
-    {"vdot": 58, "E": 273, "M": 233, "T": 216, "I": 201, "R": 46},
-    {"vdot": 59, "E": 270, "M": 230, "T": 214, "I": 199, "R": 45},
-    {"vdot": 60, "E": 267, "M": 228, "T": 211, "I": 197, "R": 45},
-    {"vdot": 62, "E": 261, "M": 223, "T": 207, "I": 193, "R": 44},
-    {"vdot": 65, "E": 253, "M": 216, "T": 201, "I": 187, "R": 42},
-    {"vdot": 68, "E": 245, "M": 209, "T": 195, "I": 182, "R": 41},
-    {"vdot": 70, "E": 240, "M": 205, "T": 191, "I": 178, "R": 40},
-    {"vdot": 75, "E": 229, "M": 196, "T": 183, "I": 171, "R": 38},
-    {"vdot": 80, "E": 219, "M": 188, "T": 176, "I": 164, "R": 37},
-    {"vdot": 85, "E": 210, "M": 181, "T": 169, "I": 158, "R": 35},
-]
-
-# ── VDOT → 레이스 예측 시간 (초) ──────────────────────────────────────
-
-VDOT_RACE_TABLE: list[dict[str, Any]] = [
-    {"vdot": 30, "5k": 1833, "10k": 3822, "half": 8437, "full": 17576},
-    {"vdot": 31, "5k": 1777, "10k": 3702, "half": 8168, "full": 17012},
-    {"vdot": 32, "5k": 1724, "10k": 3588, "half": 7911, "full": 16474},
-    {"vdot": 33, "5k": 1673, "10k": 3479, "half": 7668, "full": 15960},
-    {"vdot": 34, "5k": 1625, "10k": 3375, "half": 7436, "full": 15468},
-    {"vdot": 35, "5k": 1579, "10k": 3275, "half": 7215, "full": 14996},
-    {"vdot": 36, "5k": 1535, "10k": 3180, "half": 7003, "full": 14543},
-    {"vdot": 37, "5k": 1493, "10k": 3089, "half": 6800, "full": 14107},
-    {"vdot": 38, "5k": 1453, "10k": 3001, "half": 6606, "full": 13688},
-    {"vdot": 39, "5k": 1415, "10k": 2918, "half": 6419, "full": 13283},
-    {"vdot": 40, "5k": 1378, "10k": 2837, "half": 6240, "full": 12893},
-    {"vdot": 41, "5k": 1343, "10k": 2760, "half": 6068, "full": 12516},
-    {"vdot": 42, "5k": 1309, "10k": 2686, "half": 5902, "full": 12151},
-    {"vdot": 43, "5k": 1277, "10k": 2614, "half": 5742, "full": 11798},
-    {"vdot": 44, "5k": 1246, "10k": 2546, "half": 5588, "full": 11457},
-    {"vdot": 45, "5k": 1216, "10k": 2480, "half": 5440, "full": 11126},
-    {"vdot": 46, "5k": 1188, "10k": 2417, "half": 5297, "full": 10805},
-    {"vdot": 47, "5k": 1160, "10k": 2356, "half": 5159, "full": 10494},
-    {"vdot": 48, "5k": 1134, "10k": 2298, "half": 5025, "full": 10192},
-    {"vdot": 49, "5k": 1108, "10k": 2242, "half": 4896, "full": 9899},
-    {"vdot": 50, "5k": 1084, "10k": 2188, "half": 4771, "full": 9614},
-    {"vdot": 51, "5k": 1060, "10k": 2136, "half": 4650, "full": 9338},
-    {"vdot": 52, "5k": 1038, "10k": 2086, "half": 4533, "full": 9069},
-    {"vdot": 53, "5k": 1016, "10k": 2038, "half": 4420, "full": 8808},
-    {"vdot": 54, "5k": 995, "10k": 1991, "half": 4310, "full": 8553},
-    {"vdot": 55, "5k": 975, "10k": 1947, "half": 4204, "full": 8306},
-    {"vdot": 56, "5k": 956, "10k": 1904, "half": 4101, "full": 8065},
-    {"vdot": 57, "5k": 937, "10k": 1862, "half": 4001, "full": 7830},
-    {"vdot": 58, "5k": 919, "10k": 1822, "half": 3904, "full": 7601},
-    {"vdot": 59, "5k": 902, "10k": 1783, "half": 3810, "full": 7378},
-    {"vdot": 60, "5k": 885, "10k": 1746, "half": 3719, "full": 7161},
-    {"vdot": 62, "5k": 854, "10k": 1675, "half": 3545, "full": 6744},
-    {"vdot": 65, "5k": 812, "10k": 1581, "half": 3310, "full": 6188},
-    {"vdot": 68, "5k": 774, "10k": 1496, "half": 3098, "full": 5688},
-    {"vdot": 70, "5k": 750, "10k": 1441, "half": 2967, "full": 5366},
-    {"vdot": 75, "5k": 698, "10k": 1327, "half": 2684, "full": 4733},
-    {"vdot": 80, "5k": 653, "10k": 1226, "half": 2435, "full": 4199},
-    {"vdot": 85, "5k": 613, "10k": 1137, "half": 2215, "full": 3742},
-]
 
 # ── VDOT → 권장 주간 볼륨 ────────────────────────────────────────────
 
@@ -137,16 +54,13 @@
 # ── 공개 API ───────────────────────────────────────────────────────────
 
 def get_training_paces(vdot: float) -> dict[str, int]:
-    """VDOT → 훈련 페이스 (sec/km). {"E": 303, "M": 259, "T": 239, "I": 222, "R_400m": 50}"""
-    result = {}
-    for key in ("E", "M", "T", "I"):
-        val = _interpolate(VDOT_PACE_TABLE, vdot, key)
-        if val is not None:
-            result[key] = round(val)
-    r = _interpolate(VDOT_PACE_TABLE, vdot, "R")
-    if r is not None:
-        result["R_400m"] = round(r)
-    return result
+    """VDOT → 훈련 페이스 (sec/km, R 은 400m 초). 예: VDOT 50 → {"E": 324, "M": 258, "T": 252, "I": 227, "R_400m": 86}"""
+    if not vdot or vdot <= 0:
+        return {}
+    z = zone_speeds(vdot)
+    e_speed = (z["E"][0] + z["E"][1]) / 2.0
+    return {"E": round(1000 / e_speed), "M": round(1000 / z["M"]), "T": round(1000 / z["T"]),
+            "I": round(1000 / z["I"]), "R_400m": round(400 / z["R"])}
 
 
 def get_race_predictions(vdot: float) -> dict[str, int]:
@@ -220,23 +134,14 @@
 
 
 def vdot_to_t_pace(vdot: float) -> float | None:
-    """VDOT → Daniels T-pace (sec/km)."""
-    val = _interpolate(VDOT_PACE_TABLE, vdot, "T")
-    return round(val, 1) if val is not None else None
+    """VDOT → Daniels T-pace (sec/km) = 60분 레이스 페이스."""
+    if not vdot or vdot <= 0:
+        return None
+    return round(1000 / threshold_speed(vdot), 1)
 
 
 def t_pace_to_vdot(t_pace_sec_km: float) -> float | None:
-    """Daniels T-pace → VDOT 역산 (테이블 역보간)."""
-    for i in range(len(VDOT_PACE_TABLE) - 1):
-        lo = VDOT_PACE_TABLE[i]
-        hi = VDOT_PACE_TABLE[i + 1]
-        t_lo = lo.get("T", 999)
-        t_hi = hi.get("T", 999)
-        if t_lo >= t_pace_sec_km >= t_hi:
-            ratio = (t_lo - t_pace_sec_km) / (t_lo - t_hi) if t_lo != t_hi else 0
-            return round(lo["vdot"] + ratio * (hi["vdot"] - lo["vdot"]), 1)
-    if t_pace_sec_km >= VDOT_PACE_TABLE[0].get("T", 999):
-        return float(VDOT_PACE_TABLE[0]["vdot"])
-    if t_pace_sec_km <= VDOT_PACE_TABLE[-1].get("T", 0):
-        return float(VDOT_PACE_TABLE[-1]["vdot"])
-    return None
+    """Daniels T-pace(sec/km) → VDOT (60분 레이스 역산)."""
+    if not t_pace_sec_km or t_pace_sec_km <= 0:
+        return None
+    return round(_race_vdot(1000 / t_pace_sec_km * 3600, 3600), 1)
````

**`src/ai/tool_exec_context.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/ai/tool_exec_context.py
+++ b/src/ai/tool_exec_context.py
@@ -218,7 +218,7 @@
         "   AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
     ).fetchone()
     if vdot_row and vdot_row[0]:
-        from src.metrics.daniels_table import get_training_paces
+        from src.utils.daniels_table import get_training_paces
         paces = get_training_paces(float(vdot_row[0]))
         profile["training_paces"] = {
             k: f"{v // 60}:{v % 60:02d}/km" for k, v in paces.items()
````

**`src/training/interval_calc.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/training/interval_calc.py
+++ b/src/training/interval_calc.py
@@ -215,7 +215,7 @@
         vdot: VDOT_ADJ 값.
         eftp_sec_km: eFTP (검증용).
     """
-    from src.metrics.daniels_table import get_training_paces
+    from src.utils.daniels_table import get_training_paces
     paces = get_training_paces(vdot)
     i_pace = paces.get("I", 240)  # fallback 4:00/km
     return prescribe_interval(rep_m, int(i_pace), eftp_sec_km)
````

**`src/training/planner_rules.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/training/planner_rules.py
+++ b/src/training/planner_rules.py
@@ -140,7 +140,7 @@
     """
     if vdot and vdot > 20:
         try:
-            from src.metrics.daniels_table import get_training_paces
+            from src.utils.daniels_table import get_training_paces
             return get_training_paces(vdot)
         except Exception:
             pass
````

**`tests/test_daniels_table.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_daniels_table.py
+++ b/tests/test_daniels_table.py
@@ -4,18 +4,14 @@
     get_training_paces, get_race_predictions,
     get_marathon_volume_targets, get_race_volume_targets,
     vdot_to_t_pace, t_pace_to_vdot,
-    VDOT_PACE_TABLE,
 )
 
 
 class TestTrainingPaces:
     def test_vdot_50_paces(self):
+        """P7-PRED-85: Daniels–Gilbert 공식 값(원서 VDOT 50: M 4:31/km·T 4:15/km·R 400m 88초와 ±5초 이내)."""
         p = get_training_paces(50)
-        assert p["E"] == 303
-        assert p["M"] == 259
-        assert p["T"] == 239
-        assert p["I"] == 222
-        assert p["R_400m"] == 50
+        assert p == {"E": 320, "M": 271, "T": 253, "I": 230, "R_400m": 87}
 
     def test_interpolation(self):
         """중간 VDOT에서 보간 작동"""
@@ -23,10 +19,11 @@
         assert p["E"] > 0
         # 47과 48 사이
         assert get_training_paces(47)["E"] >= p["E"] >= get_training_paces(48)["E"]
+        assert p["E"] > p["M"] > p["T"] > p["I"]
 
     def test_boundary_low(self):
-        p = get_training_paces(20)  # 테이블 최소 30 미만
-        assert "E" in p  # 최소값 반환
+        p = get_training_paces(20)  # 공식은 범위 제한 없음
+        assert "E" in p
 
     def test_boundary_high(self):
         p = get_training_paces(90)  # 테이블 최대 85 초과
@@ -64,13 +61,13 @@
 class TestTpaceConversion:
     def test_vdot_to_t_pace(self):
         t = vdot_to_t_pace(50)
-        assert t == 239
+        assert t == 253.3
 
     def test_t_pace_to_vdot_roundtrip(self):
         """VDOT → T-pace → VDOT 왕복"""
         t = vdot_to_t_pace(50)
         v = t_pace_to_vdot(t)
-        assert abs(v - 50) < 1.0
+        assert abs(v - 50) < 0.1
 
     def test_t_pace_to_vdot_interpolated(self):
         v = t_pace_to_vdot(250)  # 테이블 사이값
````

검증:
```
python3 -m pytest tests/test_daniels_table.py tests/test_eftp.py tests/test_marathon_shape.py tests/test_replanner.py -q
```

