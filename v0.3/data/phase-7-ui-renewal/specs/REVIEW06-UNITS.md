# REVIEW-06 반영 유닛 명세 (autopilot 전용)

`REVIEW-06-design-agent-review.md` 수정 방안 중 사용자 승인분(2026-09-25): 기준일 통일(달력 오늘·현 시각 기준), 3(오늘 할 일 L0), 4(계획 공백 → 행동).
**이 명세의 코드·시그니처·문구는 그대로 구현한다. 바꾸고 싶으면 DECISIONS.md에 사유를 적고 중단.**
이 작업은 main이 아니라 autopilot 워크트리에서만 한다(사용자 지시).

## 결정 (사용자 확정)

- 기준일 = **서버 로컬 달력 오늘**. 최신 데이터일(어제)이나 UTC 날짜가 아니다.
- 오늘은 아직 끝나지 않은 날 — **하루 전체를 휴식으로 가정하지 않는다.** 오늘까지 실제 발생한 부하는 전부 반영하고, 휴식 감쇠는 하루 중 경과 비율만큼만 적용한다(자정 직후 ≈ 어제 값, 하루가 끝나면 기존 일별 EMA와 동일).
- 원인(코드 확인): Today 상태·브리핑·체크인·Coach는 SQLite `date('now')`(UTC → KST 새벽엔 어제)를, 레이스 허브는 `date.today()`(로컬)를 썼다. 백필이 만든 오늘 행은 활동 0(휴식 가정 하루치)이라 TSB가 16.2로 튀었다.

## 유닛 1 — P7-FIX-ASOF-LOCALTIME (백엔드)

파일: `src/services/today_service.py`, `dashboard_service.py`, `wellness_service.py`, `activity_service.py`, `src/ai/chat_context_checkin.py`(docstring만), `src/metrics/pmc.py`, `src/metrics/today_refresh.py`(신규), `src/api/__init__.py`, `tests/test_pmc_intraday.py`(신규).

1. 네 서비스 파일의 SQLite `date('now')` → `date('now','localtime')`, `date('now', ?)` → `date('now','localtime', ?)` (전부 치환. `grep -rn "date('now'" src/services` 로 localtime 없는 잔여가 없어야 함).
2. `chat_context_checkin.py` docstring: 과거 UTC 저장 체크인 때문에 ±1일 범위를 쓴다는 설명으로 수정(동작 변경 없음).
3. `src/metrics/pmc.py`, `src/api/__init__.py`: 아래 diff 그대로.
4. `src/metrics/today_refresh.py`, `tests/test_pmc_intraday.py`: 아래 전문 그대로.
5. `tests/test_api_today.py`에 GET `/api/v1/today`가 (이미 있는 픽스처로) 200이고 `status.date`가 `date.today().isoformat()`인지 확인하는 테스트 1개 추가(UTC와 로컬이 다른 시각에도 로컬이어야 함 — 시각 고정이 어려우면 `status.date == date.today().isoformat()`만 확인).
6. 완료 후 `python3 -m pytest tests/ -q --deselect tests/test_integration_realdb.py`, `python3 scripts/check_docs.py`, `python3 scripts/gen_files_index.py`(신규 파일 반영) 통과.

### diff (pmc.py + api/__init__.py 및 치환 결과 참고)

```diff
diff --git a/src/ai/chat_context_checkin.py b/src/ai/chat_context_checkin.py
index 5bb31c2..9115e12 100644
--- a/src/ai/chat_context_checkin.py
+++ b/src/ai/chat_context_checkin.py
@@ -9,8 +9,7 @@ _NOTE_MAX = 200
 def build_checkin_context(conn: sqlite3.Connection, today: str) -> dict | None:
     """today 기준 최근 체크인(user_inputs) — 없거나 값이 전부 비었으면 None.
 
-    save_checkin()은 SQLite date('now')(UTC)로 날짜를 찍고 today는 서버 로컬 날짜라
-    KST 새벽엔 하루 어긋난다 — 그래서 today가 아니라 [today-1일, today+1일] 범위에서
+    과거(UTC 기준 저장) 체크인 행은 KST 새벽엔 서버 로컬 날짜와 하루 어긋날 수 있다 — 그래서 today가 아니라 [today-1일, today+1일] 범위에서
     가장 최근 1건을 쓴다.
     """
     row = conn.execute(
diff --git a/src/api/__init__.py b/src/api/__init__.py
index f70307a..2e640e3 100644
--- a/src/api/__init__.py
+++ b/src/api/__init__.py
@@ -26,4 +26,30 @@ def api_error(code: str, message: str, status: int = 400):
     return jsonify({"error": {"code": code, "message": message}}), status
 
 
+_LIVE_TODAY_PREFIXES = ("/api/v1/today", "/api/v1/library/metrics")
+
+
+@api_bp.before_request
+def _refresh_today_metrics():
+    """오늘 화면·메트릭 브라우저 조회 전에 오늘 행이 오래됐으면 현 시각 기준으로 다시 계산."""
+    from flask import request
+
+    if request.method != "GET" or not request.path.startswith(_LIVE_TODAY_PREFIXES):
+        return None
+    import sqlite3
+
+    from src.metrics.today_refresh import refresh_today_if_stale
+    from src.web.helpers import db_path
+
+    dpath = db_path()
+    if not dpath.exists():
+        return None
+    conn = sqlite3.connect(str(dpath), timeout=30)
+    try:
+        refresh_today_if_stale(conn)
+    finally:
+        conn.close()
+    return None
+
+
 from . import routes_coach, routes_library, routes_plan, routes_today  # noqa: E402,F401
diff --git a/src/metrics/pmc.py b/src/metrics/pmc.py
index f27b968..1859502 100644
--- a/src/metrics/pmc.py
+++ b/src/metrics/pmc.py
@@ -1,6 +1,10 @@
 """PMC (ATL/CTL/TSB/Ramp Rate) Calculator — 설계서 4-3 기준.
 
 ATL = 7일 EMA, CTL = 42일 EMA, TSB = CTL - ATL.
+
+달력 "오늘"은 아직 끝나지 않은 날이라 하루 전체를 휴식으로 가정하지 않는다 —
+오늘까지 실제 발생한 부하는 전부 반영하되, 휴식에 의한 감쇠(1-α)는 하루 중 경과한
+비율만큼만 적용한다(자정 직후 ≈ 어제 값, 하루가 끝나면 기존 일별 EMA와 동일).
 """
 from __future__ import annotations
 
@@ -9,6 +13,15 @@ from datetime import datetime, timedelta
 from src.metrics.base import CalcContext, CalcResult, MetricCalculator
 
 
+def elapsed_day_fraction(date_str: str, now: datetime | None = None) -> float:
+    """date_str이 서버 로컬 "오늘"이면 하루 중 경과 비율(0~1), 과거 날짜는 1.0."""
+    now = now or datetime.now()
+    if date_str != now.strftime("%Y-%m-%d"):
+        return 1.0
+    seconds = now.hour * 3600 + now.minute * 60 + now.second
+    return min(1.0, max(0.0, seconds / 86400))
+
+
 class PMCCalculator(MetricCalculator):
     name = "ctl"
     provider = "runpulse:formula_v1"
@@ -47,9 +60,10 @@ class PMCCalculator(MetricCalculator):
         while current <= target:
             ds = current.strftime("%Y-%m-%d")
             load = daily_loads.get(ds, 0)
-            atl = atl * (1 - atl_decay) + load * atl_decay
+            frac = elapsed_day_fraction(ds) if current == target else 1.0
+            atl = atl * (1 - atl_decay * frac) + load * atl_decay
             prev_ctl = ctl
-            ctl = ctl * (1 - ctl_decay) + load * ctl_decay
+            ctl = ctl * (1 - ctl_decay * frac) + load * ctl_decay
             current += timedelta(days=1)
 
         tsb = ctl - atl
diff --git a/src/services/activity_service.py b/src/services/activity_service.py
index d64f534..a4f6d6a 100644
--- a/src/services/activity_service.py
+++ b/src/services/activity_service.py
@@ -297,7 +297,7 @@ def get_activity_trend(
         "m.scope_type = 'activity'",
         "m.metric_name = ?",
         "m.is_primary = 1",
-        "a.start_time >= date('now', ?)",
+        "a.start_time >= date('now','localtime', ?)",
     ]
     params: list[Any] = [metric_name, date_expr]
 
diff --git a/src/services/dashboard_service.py b/src/services/dashboard_service.py
index 6ff9c11..b244985 100644
--- a/src/services/dashboard_service.py
+++ b/src/services/dashboard_service.py
@@ -68,7 +68,7 @@ def get_dashboard_data(conn: sqlite3.Connection, date: str | None = None) -> dic
     conn.row_factory = sqlite3.Row
 
     if date is None:
-        date_row = conn.execute("SELECT date('now')").fetchone()
+        date_row = conn.execute("SELECT date('now','localtime')").fetchone()
         date = date_row[0]
 
     # wellness
@@ -188,7 +188,7 @@ def get_pmc_chart_data(conn: sqlite3.Connection, days: int = 90) -> list[dict]:
         " WHERE scope_type = 'daily'"
         "   AND metric_name IN ('ctl', 'atl', 'tsb')"
         "   AND is_primary = 1"
-        "   AND scope_id >= date('now', ?)"
+        "   AND scope_id >= date('now','localtime', ?)"
         " ORDER BY scope_id",
         (date_expr,),
     ).fetchall()
@@ -217,7 +217,7 @@ def get_daily_metric_chart(
         " WHERE scope_type = 'daily'"
         "   AND metric_name = ?"
         "   AND is_primary = 1"
-        "   AND scope_id >= date('now', ?)"
+        "   AND scope_id >= date('now','localtime', ?)"
         " ORDER BY scope_id",
         (metric_name, date_expr),
     ).fetchall()
diff --git a/src/services/today_service.py b/src/services/today_service.py
index 2021de8..324dadb 100644
--- a/src/services/today_service.py
+++ b/src/services/today_service.py
@@ -121,7 +121,7 @@ def get_todays_checkin(conn: sqlite3.Connection, date: str | None = None) -> dic
     (03g-common-patterns.md 7-5) 판단에 쓰인다.
     """
     if date is None:
-        date = conn.execute("SELECT date('now')").fetchone()[0]
+        date = conn.execute("SELECT date('now','localtime')").fetchone()[0]
 
     conn.row_factory = sqlite3.Row
     row = conn.execute(
@@ -281,7 +281,7 @@ def save_checkin(
     같은 날짜에 이미 체크인이 있으면 갱신한다(UNIQUE(input_date, input_type)).
     """
     if input_date is None:
-        input_date = conn.execute("SELECT date('now')").fetchone()[0]
+        input_date = conn.execute("SELECT date('now','localtime')").fetchone()[0]
 
     conn.execute(
         """
diff --git a/src/services/wellness_service.py b/src/services/wellness_service.py
index 05671dc..a3d6f05 100644
--- a/src/services/wellness_service.py
+++ b/src/services/wellness_service.py
@@ -33,7 +33,7 @@ def get_wellness_detail(conn: sqlite3.Connection, date: str | None = None) -> di
     conn.row_factory = sqlite3.Row
 
     if date is None:
-        date = conn.execute("SELECT date('now')").fetchone()[0]
+        date = conn.execute("SELECT date('now','localtime')").fetchone()[0]
 
     # core
     core_row = conn.execute(
@@ -104,7 +104,7 @@ def get_wellness_trend(conn: sqlite3.Connection, days: int = 30) -> dict:
         "SELECT date, sleep_score, hrv_last_night, resting_hr,"
         "       body_battery_high, avg_stress, weight_kg"
         " FROM daily_wellness"
-        " WHERE date >= date('now', ?)"
+        " WHERE date >= date('now','localtime', ?)"
         " ORDER BY date",
         (date_expr,),
     ).fetchall()
@@ -116,7 +116,7 @@ def get_wellness_trend(conn: sqlite3.Connection, days: int = 30) -> dict:
         " WHERE scope_type = 'daily'"
         "   AND metric_name = 'utrs'"
         "   AND is_primary = 1"
-        "   AND scope_id >= date('now', ?)"
+        "   AND scope_id >= date('now','localtime', ?)"
         " ORDER BY scope_id",
         (date_expr,),
     ).fetchall()
```

### src/metrics/today_refresh.py 전문

```python
"""달력 오늘의 일별 메트릭을 "현 시각 기준"으로 유지하는 지연 갱신.

오늘 행(PMC·UTRS·CIRS…)은 하루가 끝나기 전엔 잠정값이다 — PMC는 하루 중 경과 비율만큼만
휴식 감쇠를 적용한다(pmc.elapsed_day_fraction). 그래서 마지막 계산이 오래됐으면 조회 시점에
오늘 하루치만 다시 계산한다. sync를 안 돌려도 아침부터 저녁까지 값이 시각에 맞게 따라간다.
실패해도 조회는 막지 않는다(로그만).
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date

log = logging.getLogger(__name__)

_lock = threading.Lock()


def refresh_today_if_stale(conn: sqlite3.Connection, max_age_min: int = 30) -> bool:
    """오늘 tsb 행이 없거나 max_age_min분보다 오래됐으면 오늘만 재계산. 갱신했으면 True."""
    today = date.today().isoformat()  # 서버 로컬 날짜 (SQLite date('now')는 UTC라 쓰지 않는다)
    with _lock:
        try:
            fresh = conn.execute(
                "SELECT 1 FROM metric_store WHERE scope_type = 'daily' AND scope_id = ?"
                " AND metric_name = 'tsb' AND is_primary = 1"
                " AND updated_at >= datetime('now', ?)",
                (today, f"-{int(max_age_min)} minutes"),
            ).fetchone()
            if fresh:
                return False
            from src.metrics import engine

            engine.compute_for_dates(conn, [today])
            conn.commit()
            return True
        except Exception:  # noqa: BLE001 — 조회를 막지 않는다
            log.warning("today 메트릭 갱신 실패", exc_info=True)
            return False
```

### tests/test_pmc_intraday.py 전문

```python
"""PMC 오늘 부분일 처리 + 오늘 메트릭 지연 갱신 테스트."""
import sqlite3
from datetime import date, datetime, timedelta

from src.db_setup import create_tables
from src.metrics import pmc
from src.metrics.base import CalcContext
from src.metrics.pmc import PMCCalculator, elapsed_day_fraction
from src.metrics.today_refresh import refresh_today_if_stale
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _seed_run(conn, day: date, trimp: float, sid: str):
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, moving_time_sec, avg_hr, max_hr) VALUES (?,?,?,?,?,?,?,?,?)",
        ["garmin", sid, "Run", "running", f"{day.isoformat()} 08:00:00", 10000, 3000, 155, 185],
    )
    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    upsert_metric(conn, "activity", str(aid), "trimp", "runpulse:formula_v1",
                  numeric_value=trimp, category="rp_load")


def _seed_history(conn, today: date, days: int = 50):
    for i in range(1, days):
        _seed_run(conn, today - timedelta(days=i), 100.0, f"h{i}")
    conn.commit()


def _val(results, name):
    return next(r.numeric_value for r in results if r.metric_name == name)


def test_elapsed_day_fraction():
    noon = datetime(2026, 9, 25, 12, 0, 0)
    assert elapsed_day_fraction("2026-09-25", noon) == 0.5
    assert elapsed_day_fraction("2026-09-24", noon) == 1.0  # 과거 날짜는 하루 전체
    assert elapsed_day_fraction("2026-09-25", datetime(2026, 9, 25, 0, 0, 0)) == 0.0


def test_today_rest_decay_is_prorated(monkeypatch):
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today.isoformat())

    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 1.0)
    full_day = PMCCalculator().compute(ctx)
    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 0.02)
    just_after_midnight = PMCCalculator().compute(ctx)

    # 하루를 통째로 휴식 가정하면 ATL이 더 많이 감쇠 → TSB 상승. 자정 직후엔 어제 값에 가깝다.
    assert _val(just_after_midnight, "atl") > _val(full_day, "atl")
    assert _val(just_after_midnight, "tsb") < _val(full_day, "tsb")


def test_today_actual_load_counts_fully(monkeypatch):
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today.isoformat())
    monkeypatch.setattr(pmc, "elapsed_day_fraction", lambda d, now=None: 0.3)
    rest = _val(PMCCalculator().compute(ctx), "atl")
    _seed_run(conn, today, 150.0, "today")
    conn.commit()
    ran = _val(PMCCalculator().compute(ctx), "atl")
    assert ran > rest  # 오늘 이미 한 운동은 시각과 무관하게 전부 반영


def test_refresh_today_if_stale():
    conn = _conn()
    today = date.today()
    _seed_history(conn, today)
    assert refresh_today_if_stale(conn) is True  # 오늘 행 없음 → 계산
    row = conn.execute(
        "SELECT 1 FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name='tsb'",
        (today.isoformat(),),
    ).fetchone()
    assert row is not None
    assert refresh_today_if_stale(conn) is False  # 방금 계산 → 신선
    conn.execute("UPDATE metric_store SET updated_at = datetime('now', '-2 hours')"
                 " WHERE scope_type='daily' AND scope_id=?", (today.isoformat(),))
    conn.commit()
    assert refresh_today_if_stale(conn) is True  # 오래됨 → 재계산
```

## 유닛 2 — P7-IMPL-TODAY-ACTION-FIRST (프론트 전용)

목적: 첫 화면(844px)에 "D-day·예측/목표·오늘 할 일 한 문장"이 함께 보이게 하고, 기준 시점을 밝힌다.

1. 신규 `frontend/src/lib/asOf.ts` (순수 모듈, import 없음):

```ts
// 기준 시점 라벨 — status.date가 서버 로컬 오늘이면 "오늘 지금까지 반영", 아니면 그 날짜 기준.
export function asOfLabel(statusDate: string, todayLocal: string): string {
	const [, m, d] = statusDate.split('-');
	const md = `${Number(m)}월 ${Number(d)}일`;
	return statusDate === todayLocal ? `${md} · 오늘 지금까지 반영` : `${md} 기준`;
}

// 브라우저 로컬 날짜 YYYY-MM-DD
export function localDateString(now: Date = new Date()): string {
	const p = (n: number) => String(n).padStart(2, '0');
	return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}
```

   `frontend/tests/asOf.test.mjs`(신규, 기존 `scoreRing.test.mjs`와 같은 import 스타일): (a) `asOfLabel('2026-09-25','2026-09-25') === '9월 25일 · 오늘 지금까지 반영'`, (b) `asOfLabel('2026-09-24','2026-09-25') === '9월 24일 기준'`, (c) `localDateString(new Date(2026, 8, 5)) === '2026-09-05'`.
2. `frontend/src/lib/components/RaceHub.svelte`: `예측 기록 추이` 블록(`{#if pred && pred.history.length > 1}…{/if}`)과 `{#if proj}…{/if}` 블록 **두 개를 하나의 `<details class="group border-t border-border-subtle pt-3">`로 감싼다.** `<summary class="cursor-pointer list-none text-xs text-fg-muted hover:text-fg-primary">예측 추이 · 레이스 아침 폼 보기 ▾</summary>` 다음에 두 블록을 그대로 둔다(내부 마크업 변경 금지, 기존 `proj` 블록의 자체 `border-t … pt-3`는 제거). 두 블록이 모두 없으면 `<details>`도 렌더하지 않는다(`{#if (pred && pred.history.length > 1) || proj}`). 마지막 `{#if tsb != null && !proj}` 줄은 그대로.
3. `frontend/src/routes/today/+page.svelte`: 순서는 `RaceHub` → `RecommendationCard`(현행 유지 — RaceHub가 접히면 카드가 첫 뷰포트에 들어온다). L1 섹션의 ScoreRing 그리드 바로 위에 `<p class="text-[11px] text-fg-muted">{asOfLabel(status.date, localDateString())}</p>` 추가(`import { asOfLabel, localDateString } from '$lib/asOf';`).
4. 검증: `cd frontend && npm install && npm run test:unit && npm run check && npm run build`.

## 유닛 3 — P7-IMPL-PLAN-EMPTY-TO-ACTION (프론트 전용, 유닛 2 이후)

목적: 목표 레이스가 있는데 플랜이 없을 때 "만들기" 원탭 CTA + 목표 프리필.

1. 신규 `frontend/src/lib/planPrefill.ts` (순수, 런타임 import 없음):

```ts
export interface PrefillGoal {
	distance_km: number;
	race_date: string;
	target_time_sec: number | null;
}

// 목표 → /coach/plan/new 쿼리 링크
export function planNewHref(base: string, goal: PrefillGoal): string {
	const p = new URLSearchParams({ distance_km: String(goal.distance_km), race_date: goal.race_date });
	if (goal.target_time_sec != null) p.set('target_time_sec', String(goal.target_time_sec));
	return `${base}/coach/plan/new?${p}`;
}

export const PLAN_DISTANCES_KM = [5, 10, 21.097, 42.195];

// 쿼리 → 폼 초기값. distance는 표준 거리에 ±1km 이내일 때만 채택.
export function parsePrefill(search: URLSearchParams): {
	km: number | null; raceDate: string; hh: string; mm: string; ss: string; completion: boolean;
} {
	const raw = Number(search.get('distance_km'));
	const km = PLAN_DISTANCES_KM.find((d) => Math.abs(d - raw) <= 1) ?? null;
	const raceDate = /^\d{4}-\d{2}-\d{2}$/.test(search.get('race_date') ?? '') ? (search.get('race_date') as string) : '';
	const t = Number(search.get('target_time_sec'));
	if (!Number.isFinite(t) || t <= 0) return { km, raceDate, hh: '', mm: '', ss: '', completion: false };
	return { km, raceDate, hh: String(Math.floor(t / 3600)), mm: String(Math.floor((t % 3600) / 60)), ss: String(Math.round(t % 60)), completion: false };
}

// 남은 기간 문구: 28일 이하 → "남은 N주", 아니면 "N주 로드맵"
export function roadmapLabel(daysLeft: number): string {
	const weeks = Math.max(1, Math.ceil(daysLeft / 7));
	return daysLeft <= 28 ? `남은 ${weeks}주 로드맵 만들기` : `${weeks}주 로드맵 만들기`;
}
```

   `frontend/tests/planPrefill.test.mjs`(신규): `planNewHref('/v2', {distance_km:42.195, race_date:'2026-10-25', target_time_sec:15300}) === '/v2/coach/plan/new?distance_km=42.195&race_date=2026-10-25&target_time_sec=15300'`; target null이면 `target_time_sec` 없음; `parsePrefill(new URLSearchParams('distance_km=42.2&race_date=2026-10-25&target_time_sec=15300'))` → `km 42.195, raceDate '2026-10-25', hh '4', mm '15', ss '0'`; `distance_km=30`이면 `km null`; 잘못된 날짜는 `raceDate ''`; `roadmapLabel(30) === '5주 로드맵 만들기'`, `roadmapLabel(28) === '남은 4주 로드맵 만들기'`, `roadmapLabel(3) === '남은 1주 로드맵 만들기'`.
2. `frontend/src/lib/components/NextSessionCard.svelte`: prop `raceGoal?: { name: string; days_left: number; distance_km: number; race_date: string; target_time_sec: number | null } | null`(기본 null) 추가. `plan === null` 분기에서 `raceGoal`이 있으면 기존 문구 대신 `<a href={planNewHref(base, raceGoal)} class="flex flex-col gap-1 rounded-xl border border-semantic-amber/40 bg-semantic-amber/10 p-3 hover:bg-semantic-amber/20"><span class="text-sm font-semibold">{raceGoal.name} D-{raceGoal.days_left} — {roadmapLabel(raceGoal.days_left)}</span><span class="text-xs text-fg-secondary">목표 레이스 정보가 미리 채워집니다 →</span></a>`. `raceGoal` 없으면 기존 마크업 그대로.
3. `frontend/src/routes/today/+page.svelte`: `<NextSessionCard … raceGoal={data.raceHub?.goal ?? null} />` 전달.
4. `frontend/src/routes/coach/plan/+page.ts`: 반환 타입에 `goal: RaceHubGoal | null` 추가 — `getRaceHub().catch(() => null)`을 `getToday()`와 함께 `Promise.all`로 호출해 `goal: hub?.goal ?? null`. `+page.svelte`: `data.goal`이 있으면 기존 안내문 위에 `<p class="text-base font-medium">{data.goal.name} D-{data.goal.days_left}</p>`를 두고 버튼 링크를 `planNewHref(base, data.goal)`, 버튼 문구를 `roadmapLabel(data.goal.days_left) + ' →'`로. 없으면 현행 유지.
5. `frontend/src/routes/coach/plan/new/+page.svelte`: `import { page } from '$app/state';`(프로젝트가 이미 `$app/state`를 쓰는지 grep으로 확인하고, 안 쓰면 `$app/stores`의 `page`를 `$page`로) 와 `parsePrefill`을 써서 `<script>` 초기화 시 `const pre = parsePrefill(page.url.searchParams);` 후 `selectedKm = pre.km; raceDate = pre.raceDate; goalHH = pre.hh; goalMM = pre.mm; goalSS = pre.ss;`로 초기값 설정. `DISTANCES` 상수는 그대로.
6. 검증: `cd frontend && npm install && npm run test:unit && npm run check && npm run build`.
