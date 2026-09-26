# PRED-1x — 메트릭 무결성·데이터 보존 (예측 리뉴얼 r3)

근거: `REVIEW-07-prediction-renewal.md` r3 §6, `REVIEW-08-metric-audit.md` r3 §R3. 순서·의존·실DB 시점은 `P7-PRED-00-INDEX.md`.

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-11 — 스키마 v20 (랩 GAP·기온·경과시간·컴플라이언스·워크아웃 단계, race_results, session_outcomes 유일 제약)

- 의존: 없음 · UI 노출: 없음 · 실DB: 다음 앱 기동/동기화 때 `create_tables`가 멱등 ALTER(데이터 삭제 없음)
- 파일: `src/db_schema_v20.py`(신규), `src/db_setup.py`, `src/utils/db_helpers.py`, `tests/helpers_pred.py`(신규·공용 시드), `tests/test_pred_schema_v20.py`(신규), `tests/test_db_setup.py`, `tests/test_phase1_schema.py`
- 왜: Garmin 랩의 경사보정 속도(`avgGradeAdjustedSpeed`)·경과시간·기온·컴플라이언스·워크아웃 단계 번호를 저장할 칸이 없다(REVIEW-08 #5). 대회 확인 입력(race_results)이 없다. `session_outcomes`에 `planned_id` 유일 제약이 없어 매처의 `ON CONFLICT(planned_id)`가 **항상 실패**한다(실DB `session_outcomes` 0행의 원인 — REVIEW-08 R3-4).

**`src/db_schema_v20.py`** — 신규, 전문 그대로(66줄)

````python
"""스키마 v20 — 예측 리뉴얼(REVIEW-07 r3) 데이터 보존용 컬럼·테이블 추가.

activity_laps: 경사보정 속도·고도 손실·기온·경과/이동 시간·컴플라이언스
activity_streams: 경사보정 속도
weather_cache: 체감온도·일사량
planned_workouts: 외부 시스템 식별·구조
session_outcomes: 세그먼트 매칭 결과
race_results: 대회 확인 입력(신규)
"""
from __future__ import annotations

import sqlite3

V20_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "activity_laps": [
        ("gap_speed_ms", "REAL"),
        ("elevation_loss", "REAL"),
        ("avg_temperature_c", "REAL"),
        ("elapsed_duration_sec", "REAL"),
        ("moving_duration_sec", "REAL"),
        ("compliance_score", "REAL"),
        ("wkt_step_index", "INTEGER"),  # Garmin 워크아웃 단계 번호(계획 단계 ↔ 랩 매칭, P7-PRED-43)
    ],
    "activity_streams": [("gap_speed_ms", "REAL")],
    "weather_cache": [("feels_like_c", "REAL"), ("shortwave_wm2", "REAL")],
    "planned_workouts": [
        ("source_system", "TEXT"),      # runpulse | garmin | intervals
        ("external_id", "TEXT"),
        ("structure_json", "TEXT"),     # 단계 목록(P7-PRED-42 형식)
    ],
    "session_outcomes": [
        ("compliance_pct", "REAL"),
        ("segment_match_json", "TEXT"),
        ("source_compliance", "REAL"),
        ("source_system", "TEXT"),
    ],
}

DDL_RACE_RESULTS = """
CREATE TABLE IF NOT EXISTS race_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id       INTEGER NOT NULL UNIQUE,
    race_name         TEXT,
    distance_m        REAL NOT NULL,
    official_time_sec INTEGER,
    effort            TEXT NOT NULL CHECK(effort IN ('allout', 'paced', 'fun', 'dnf')),
    note              TEXT,
    confirmed_at      TEXT DEFAULT (datetime('now'))
);
"""


def ensure_v20(conn: sqlite3.Connection) -> None:
    """v20 컬럼·테이블을 멱등적으로 보장한다(존재하는 테이블에만 ALTER)."""
    for table, cols in V20_COLUMNS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not existing:
            continue
        for name, typ in cols:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
    conn.execute(DDL_RACE_RESULTS)
    # matcher 의 ON CONFLICT(planned_id) 가 요구하는 유일 제약(없어서 session_outcomes 저장이 항상 실패했다)
    conn.execute("DELETE FROM session_outcomes WHERE id NOT IN (SELECT max(id) FROM session_outcomes GROUP BY planned_id) "
                 "AND planned_id IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_session_outcomes_planned ON session_outcomes(planned_id)")
````

**`src/db_setup.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/db_setup.py
+++ b/src/db_setup.py
@@ -29,7 +29,7 @@
 
 _PROJECT_ROOT = Path(__file__).resolve().parent.parent
 DEFAULT_USER = "default"
-SCHEMA_VERSION = 19  # v0.3.9: chat_messages.evidence_json
+SCHEMA_VERSION = 20  # v0.3.10: 예측 리뉴얼 컬럼·race_results (db_schema_v20)
 
 
 # ─────────────────────────────────────────────────────────────────────────────
@@ -713,6 +713,10 @@
     # Indexes (컬럼 존재 확인 후 안전 생성)
     _safe_create_indexes(conn)
 
+    # v20: 예측 리뉴얼 컬럼·race_results (멱등)
+    from src.db_schema_v20 import ensure_v20
+    ensure_v20(conn)
+
     conn.commit()
 
 
@@ -857,7 +861,7 @@
         if existing and "evidence_json" not in existing:
             conn.execute("ALTER TABLE chat_messages ADD COLUMN evidence_json TEXT")
 
-    # 새 테이블 생성 (IF NOT EXISTS이므로 기존 테이블 무시)
+    # 새 테이블 생성 (IF NOT EXISTS이므로 기존 테이블 무시) — v20 컬럼은 create_tables 안에서 보장
     create_tables(conn)
 
     _set_user_version(conn, SCHEMA_VERSION)
````

**`src/utils/db_helpers.py`** — 수정, 아래 diff 그대로 — 랩·스트림 저장 컬럼 목록

````diff
--- a/src/utils/db_helpers.py
+++ b/src/utils/db_helpers.py
@@ -598,6 +598,8 @@
         "distance_m", "avg_hr", "max_hr", "avg_pace_sec_km",
         "avg_cadence", "avg_power", "max_power",
         "elevation_gain", "calories", "lap_trigger",
+        "gap_speed_ms", "elevation_loss", "avg_temperature_c",
+        "elapsed_duration_sec", "moving_duration_sec", "compliance_score", "wkt_step_index",
     ]
     count = 0
     for lap in laps:
@@ -646,6 +648,7 @@
         "activity_id", "source", "elapsed_sec", "distance_m",
         "heart_rate", "cadence", "power_watts", "altitude_m",
         "speed_ms", "latitude", "longitude", "grade_pct", "temperature_c",
+        "gap_speed_ms",
     ]
 
     sources = {r.get("source", "") for r in rows}
````

**`tests/helpers_pred.py`** — 신규, 전문 그대로(29줄)

````python
"""예측 v2 테스트 공용 시드 헬퍼(P7-PRED-11)."""
import sqlite3

from src.db_setup import create_tables


def mem_conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def seed_run(c, *, source="garmin", sid="1", date="2026-05-09", t="07:30:00", name="Run", dist=10000.0,
             moving=2700, elapsed=None, avg_hr=150, max_hr=175, event_type=None, group=None, atype="running",
             lat=37.52, lon=126.92, temp=None):
    c.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m, moving_time_sec,"
        " elapsed_time_sec, duration_sec, avg_hr, max_hr, event_type, matched_group_id, start_lat, start_lon, avg_temperature)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, sid, name, atype, f"{date} {t}", dist, moving, elapsed or moving, elapsed or moving, avg_hr, max_hr,
         event_type, group, lat, lon, temp))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def seed_laps(c, aid, laps, source="garmin"):
    """laps: [(dist_m, dur_s, hr, itype, gap_speed_ms|None, max_hr|None)]"""
    for i, (d, s, hr, it, gap, mx) in enumerate(laps):
        c.execute("INSERT INTO activity_laps (activity_id, source, lap_index, distance_m, duration_sec, avg_hr, max_hr,"
                  " lap_trigger, gap_speed_ms) VALUES (?,?,?,?,?,?,?,?,?)", (aid, source, i, d, s, hr, mx, it, gap))
````

**`tests/test_pred_schema_v20.py`** — 신규, 전문 그대로(46줄)

````python
"""P7-PRED-11: 스키마 v20 컬럼·race_results·session_outcomes 유일 제약."""
import sqlite3

from src.db_setup import SCHEMA_VERSION, create_tables, migrate_db
from src.db_schema_v20 import V20_COLUMNS, ensure_v20


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_v20_columns_exist_after_create():
    c = _conn()
    for table, cols in V20_COLUMNS.items():
        existing = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        for name, _ in cols:
            assert name in existing, (table, name)
    assert c.execute("SELECT count(*) FROM race_results").fetchone()[0] == 0


def test_ensure_v20_idempotent():
    c = _conn()
    ensure_v20(c)
    ensure_v20(c)
    assert "gap_speed_ms" in {r[1] for r in c.execute("PRAGMA table_info(activity_laps)")}


def test_migrate_from_19_adds_columns():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("PRAGMA user_version = 19")
    migrate_db(c)
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION   # v20 이후 버전(P7-PRED-63 v21)까지


def test_session_outcomes_unique_planned_id():
    import sqlite3 as _s
    from src.db_setup import create_tables as _ct
    c = _s.connect(":memory:")
    _ct(c)
    c.execute("INSERT INTO session_outcomes (planned_id, date) VALUES (1, '2026-09-22')")
    c.execute("INSERT INTO session_outcomes (planned_id, date) VALUES (1, '2026-09-22') "
              "ON CONFLICT(planned_id) DO UPDATE SET date=excluded.date")
    assert c.execute("SELECT count(*) FROM session_outcomes").fetchone()[0] == 1
````

**`tests/test_db_setup.py`** — 수정, 아래 diff 그대로

````diff
--- a/tests/test_db_setup.py
+++ b/tests/test_db_setup.py
@@ -86,11 +86,11 @@
         yield
         self.conn.close()
 
-    def test_schema_version_is_19(self):
-        """조건 2 — v19: chat_messages.evidence_json 추가"""
+    def test_schema_version_is_20(self):
+        """v20: 예측 리뉴얼 컬럼·race_results (db_schema_v20)"""
         ver = self.conn.execute("PRAGMA user_version").fetchone()[0]
         assert ver == SCHEMA_VERSION
-        assert ver == 19
+        assert ver == 20
 
     def test_pipeline_tables_count(self):
         """조건 3: pipeline 테이블 (daily_fitness 제거됨, ADR-005)"""
@@ -160,7 +160,7 @@
 
     cols_after = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
     assert "evidence_json" in cols_after
-    assert conn.execute("PRAGMA user_version").fetchone()[0] == 19
+    assert conn.execute("PRAGMA user_version").fetchone()[0] == 20
     conn.close()
 
 
````

**`tests/test_phase1_schema.py`** — 수정, 아래 diff 그대로 — 스키마 버전 줄만(19 → 20). v21 은 P7-PRED-63

````diff
--- a/tests/test_phase1_schema.py
+++ b/tests/test_phase1_schema.py
@@ -96,7 +96,7 @@
     def test_schema_version(self, db_conn):
         ver = _get_user_version(db_conn)
         assert ver == SCHEMA_VERSION
-        assert ver == 19  # v0.3.9: chat_messages.evidence_json (Coach 근거)
+        assert ver == 20  # v0.3.10: 예측 v2 (laps GAP·race_results 등, P7-PRED-11)
 
     def test_activity_summaries_column_count(self, db_conn):
         cols = db_conn.execute("PRAGMA table_info(activity_summaries)").fetchall()
````

검증:
```
python3 -m pytest tests/test_pred_schema_v20.py tests/test_db_setup.py tests/test_phase1_schema.py -q
python3 scripts/check_docs.py
```

## P7-PRED-12 — Garmin 추출기: 랩 확장 필드 보존 + 스트림 시간축·거리·GAP 수정

- 의존: P7-PRED-11 · UI 노출: 없음 · 실DB: **이 유닛만으로는 기존 행이 바뀌지 않는다** → P7-PRED-13 재추출(P7-PRED-61 런북 2단계)이 있어야 채워진다
- 파일: `src/sync/extractors/garmin_lap_fields.py`(신규), `src/sync/extractors/garmin_extractor.py`, `tests/test_garmin_lap_fields.py`(신규)
- 활동 GAP: registry `gap`(sec/km, garmin 별칭 `avgGradeAdjustedSpeed`)이 추출되지 않아 0행이었다 → 활동 메트릭 `gap` = 1000/avgGradeAdjustedSpeed 로 저장(Garmin payload 261개에 존재, REVIEW-08 R3-5).
- 왜: 스트림 추출이 `directElapsedDuration`(없음)만 찾아 **샘플 인덱스를 시간(초)으로 저장**하고 `sumDistance`·`directGradeAdjustedSpeed`를 버린다(REVIEW-08 #5). 랩은 `avgGradeAdjustedSpeed`·`elapsedDuration`·`averageTemperature`·`directWorkoutComplianceScore`·`wktStepIndex`를 버린다.
- 실측(사본 DB 재추출 결과): Garmin 랩 3,360개 중 GAP 2,786개(83%)·경과시간 3,360개·랩 기온 2,778개가 채워지고, 스트림 최대 경과시간이 2,013(샘플 수) → 13,334초(실제)로 바뀐다.

**`src/sync/extractors/garmin_lap_fields.py`** — 신규, 전문 그대로(36줄)

````python
"""Garmin 랩(lapDTOs)·스트림 확장 필드 — 예측 리뉴얼(P7-PRED-12)에서 보존하는 값."""
from __future__ import annotations

# Garmin details(metricDescriptors) key → activity_streams 컬럼. 기존 direct* 매핑보다 우선.
STREAM_KEY_ALIASES = {
    "elapsed_sec": ("sumElapsedDuration", "directElapsedDuration"),
    "distance_m": ("sumDistance", "directDistance"),
    "gap_speed_ms": ("directGradeAdjustedSpeed",),
}


def lap_extras(lap: dict) -> dict:
    """lapDTO → activity_laps 확장 컬럼(None 은 제외)."""
    out = {
        "gap_speed_ms": lap.get("avgGradeAdjustedSpeed"),
        "elevation_loss": lap.get("elevationLoss"),
        "avg_temperature_c": lap.get("averageTemperature"),
        "elapsed_duration_sec": lap.get("elapsedDuration"),
        "moving_duration_sec": lap.get("movingDuration"),
        "compliance_score": lap.get("directWorkoutComplianceScore"),
        "wkt_step_index": lap.get("wktStepIndex"),
    }
    return {k: v for k, v in out.items() if v is not None}


def pick(metrics, idx_map: dict[str, int], keys: tuple[str, ...]):
    """스트림 한 점(metrics: list 또는 dict)에서 keys 순서대로 첫 값."""
    for k in keys:
        if isinstance(metrics, dict):
            if metrics.get(k) is not None:
                return metrics[k]
            continue
        pos = idx_map.get(k)
        if pos is not None and pos < len(metrics) and metrics[pos] is not None:
            return metrics[pos]
    return None
````

**`src/sync/extractors/garmin_extractor.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/sync/extractors/garmin_extractor.py
+++ b/src/sync/extractors/garmin_extractor.py
@@ -12,6 +12,7 @@
 from datetime import datetime, timezone
 from src.sync.extractors.base import BaseExtractor, MetricRecord
 from src.utils.activity_types import normalize_activity_type
+from src.sync.extractors.garmin_lap_fields import STREAM_KEY_ALIASES, lap_extras, pick
 
 
 class GarminExtractor(BaseExtractor):
@@ -105,6 +106,9 @@
             # activity_summaries → metric_store 이동 (Phase 5-G)
             self._metric("calories", raw.get("calories"),
                          raw_name="calories"),
+            # 활동 GAP: Garmin 은 속도(m/s)로 주고 registry 단위는 sec/km (P7-PRED-12)
+            self._metric("gap", _pace_from_speed(raw.get("avgGradeAdjustedSpeed")),
+                         raw_name="avgGradeAdjustedSpeed"),
             self._metric("normalized_power", raw.get("normPower"),
                          raw_name="normPower"),
             self._metric("training_effect_aerobic",
@@ -270,6 +274,7 @@
             }
             if avg_speed and avg_speed > 0:
                 lap_dict["avg_pace_sec_km"] = round(1000.0 / avg_speed, 2)
+            lap_dict.update(lap_extras(lap))
             laps.append({k: v for k, v in lap_dict.items() if v is not None})
         return laps
 
@@ -314,7 +319,6 @@
             if k is not None and idx is not None:
                 idx_map[str(k)] = int(idx)
 
-        has_elapsed = "directElapsedDuration" in idx_map
         rows: list[dict] = []
 
         for i, point in enumerate(detail_metrics):
@@ -332,8 +336,8 @@
                     return _m.get(garmin_key)
                 return None
 
-            elapsed_raw = _get("directElapsedDuration") if has_elapsed else None
-            elapsed = int(elapsed_raw) if elapsed_raw is not None else i
+            elapsed_raw = pick(metrics, idx_map, STREAM_KEY_ALIASES["elapsed_sec"])
+            elapsed = int(round(elapsed_raw)) if elapsed_raw is not None else i
 
             # directAirTemperature 우선, 없으면 directTemperature
             temp = _get("directAirTemperature")
@@ -346,13 +350,14 @@
                 "latitude":    _get("directLatitude"),
                 "longitude":   _get("directLongitude"),
                 "altitude_m":  _get("directElevation"),
-                "distance_m":  _get("directDistance"),
+                "distance_m":  pick(metrics, idx_map, STREAM_KEY_ALIASES["distance_m"]),
                 "speed_ms":    _get("directSpeed"),
                 "heart_rate":  _positive_int(_get("directHeartRate")),
                 "cadence":     _int(_get("directDoubleCadence")),
                 "power_watts": _get("directPower"),
                 "temperature_c": temp,
                 "grade_pct":   _get("directGrade"),
+                "gap_speed_ms": pick(metrics, idx_map, STREAM_KEY_ALIASES["gap_speed_ms"]),
             }
             # elapsed_sec, source는 항상 포함; 나머지 None 제거
             rows.append(
@@ -617,6 +622,14 @@
     return int(value)
 
 
+def _pace_from_speed(v) -> float | None:
+    """m/s → sec/km (0·None·비정상은 None)."""
+    try:
+        return round(1000.0 / float(v), 1) if v and float(v) > 0.5 else None
+    except (TypeError, ValueError):
+        return None
+
+
 def _int(value) -> int | None:
     if value is None:
         return None
````

**`tests/test_garmin_lap_fields.py`** — 신규, 전문 그대로(72줄)

````python
"""P7-PRED-12: Garmin 랩 확장 필드·스트림 키 선택."""
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.garmin_lap_fields import lap_extras, pick
from src.utils.db_helpers import upsert_laps_batch, upsert_streams_batch
from tests.helpers_pred import mem_conn as _conn


def test_lap_extras_drops_none():
    assert lap_extras({"avgGradeAdjustedSpeed": 3.4, "elevationLoss": None, "wktStepIndex": 2}) == \
        {"gap_speed_ms": 3.4, "wkt_step_index": 2}


def test_pick_prefers_first_key_list_and_dict():
    idx = {"sumElapsedDuration": 0, "directElapsedDuration": 1}
    assert pick([12.0, 3.0], idx, ("sumElapsedDuration", "directElapsedDuration")) == 12.0
    assert pick([None, 3.0], idx, ("sumElapsedDuration", "directElapsedDuration")) == 3.0
    assert pick({"directElapsedDuration": 7}, {}, ("sumElapsedDuration", "directElapsedDuration")) == 7


def test_extractor_uses_real_time_axis():
    raw = {"metricDescriptors": [{"key": "sumElapsedDuration", "metricsIndex": 0},
                                 {"key": "directElapsedDuration", "metricsIndex": 1},
                                 {"key": "sumDistance", "metricsIndex": 2},
                                 {"key": "directHeartRate", "metricsIndex": 3}],
           "activityDetailMetrics": [{"metrics": [0.0, 0, 0.0, 120]}, {"metrics": [4.6, 1, 13.0, 121]},
                                     {"metrics": [9.4, 2, 27.1, 122]}]}
    rows = GarminExtractor().extract_activity_streams(raw)
    assert [r["elapsed_sec"] for r in rows] == [0, 5, 9]            # 샘플 인덱스(0,1,2)가 아니라 실제 초
    assert rows[2]["distance_m"] == 27.1


def test_laps_keep_gap_and_step():
    laps = GarminExtractor().extract_activity_laps({"lapDTOs": [
        {"duration": 240.0, "distance": 1000.0, "averageSpeed": 4.17, "intensityType": "INTERVAL",
         "avgGradeAdjustedSpeed": 4.2, "wktStepIndex": 1, "directWorkoutComplianceScore": 88}]})
    assert (laps[0]["gap_speed_ms"], laps[0]["wkt_step_index"], laps[0]["compliance_score"], laps[0]["lap_trigger"]) == \
        (4.2, 1, 88, "INTERVAL")


def test_activity_gap_metric_sec_per_km():
    ms = GarminExtractor().extract_activity_metrics({"avgGradeAdjustedSpeed": 3.137, "calories": 500})
    gap = [m for m in ms if m.metric_name == "gap"]
    assert len(gap) == 1 and gap[0].numeric_value == 318.8
    assert not [m for m in GarminExtractor().extract_activity_metrics({"avgGradeAdjustedSpeed": 0}) if m.metric_name == "gap"]


def test_garmin_lap_extras_preserved():
    splits = {"lapDTOs": [{"distance": 1000.0, "duration": 250.0, "averageSpeed": 4.0, "averageHR": 165,
                           "avgGradeAdjustedSpeed": 4.05, "elevationLoss": 3.0, "averageTemperature": 21.0,
                           "elapsedDuration": 252.0, "movingDuration": 250.0, "directWorkoutComplianceScore": 88.0,
                           "intensityType": "ACTIVE"}]}
    laps = GarminExtractor().extract_activity_laps(splits)
    assert laps[0]["gap_speed_ms"] == 4.05 and laps[0]["compliance_score"] == 88.0
    assert laps[0]["lap_trigger"] == "ACTIVE" and laps[0]["elapsed_duration_sec"] == 252.0
    c = _conn()
    upsert_laps_batch(c, 1, laps)
    row = c.execute("SELECT gap_speed_ms, elevation_loss, avg_temperature_c, compliance_score FROM activity_laps").fetchone()
    assert row == (4.05, 3.0, 21.0, 88.0)


def test_garmin_stream_uses_sum_elapsed_and_distance():
    raw = {"metricDescriptors": [{"key": "sumDistance", "metricsIndex": 0}, {"key": "sumElapsedDuration", "metricsIndex": 1},
                                 {"key": "directHeartRate", "metricsIndex": 2}, {"key": "directGradeAdjustedSpeed", "metricsIndex": 3},
                                 {"key": "directSpeed", "metricsIndex": 4}],
           "activityDetailMetrics": [{"metrics": [0.0, 0.0, 120, 3.0, 3.0]}, {"metrics": [6.1, 2.0, 125, 3.1, 3.05]},
                                     {"metrics": [12.4, 4.0, 130, 3.2, 3.1]}]}
    rows = GarminExtractor().extract_activity_streams(raw)
    assert [r["elapsed_sec"] for r in rows] == [0, 2, 4]
    assert rows[2]["distance_m"] == 12.4 and rows[2]["gap_speed_ms"] == 3.2
    c = _conn()
    upsert_streams_batch(c, 7, rows)
    assert c.execute("SELECT max(elapsed_sec), max(gap_speed_ms) FROM activity_streams").fetchone() == (4, 3.2)
````

검증:
```
python3 -m pytest tests/test_garmin_lap_fields.py tests/test_garmin_extractor.py -q
```

## P7-PRED-13 — 제자리 재추출(활동 id 유지) + `reprocess_all` 파손 버그 수정

- 의존: P7-PRED-11, P7-PRED-12 · UI 노출: 없음 · **실DB: P7-PRED-61 런북 2단계에서 사용자가 실행**
- 파일: `src/sync/reextract.py`(신규), `src/sync/reprocess.py`, `tests/test_reextract.py`(신규) — 랩·스트림과 함께 활동 메트릭(예: P7-PRED-12의 활동 `gap`, 사본에서 261개)도 제자리 갱신
- 왜(샌드박스에서 실DB 사본으로 확인한 사실):
  1. `reprocess_all()`(clear_first)은 `activity_summaries`를 지우고 다시 넣어 **활동 id가 전부 바뀐다**(1,423개 중 유지 0). `race_results`·`planned_workouts.matched_activity_id`·`session_outcomes`·활동 scope `metric_store`·채팅 근거가 전부 끊긴다.
  2. summary payload가 없는 활동(Strava 102개)은 **영구 삭제**된다(1,423 → 1,321).
  3. detail/splits/streams payload의 `activity_id`가 옛 id 그대로라 `existing_aid or map` 순서 때문에 **랩 3,360개·스트림 전부가 없는 id에 붙는다**(고아).
  4. `_clear_derived_data(source)`는 요약을 먼저 지운 뒤 id를 모아 랩·스트림이 **지워지지 않는다**.
- 해결: 랩·스트림만 필요한 경우(이번 리뉴얼) `reextract_laps_streams()`로 **기존 id에 제자리 갱신**. `reprocess_all`은 (3)(4) 수정 + payload 없는 활동이 있으면 `force=True` 없이는 거부.
- 사본 검증: 재추출 586개 활동, 오류 0, 고아 0, 활동 수 1,423 유지. 수정된 `reprocess_all(force=True)`도 고아 0.

**`src/sync/reextract.py`** — 신규, 전문 그대로(77줄)

````python
"""제자리 재추출 — 기존 activity_summaries id 를 유지한 채 source_payloads 에서 랩·스트림·활동 메트릭을 다시 뽑는다(P7-PRED-13).

reprocess_all 은 activity_summaries 를 지우고 다시 만들어 id 가 전부 바뀌고(참조 테이블 파손),
payload 없는 활동이 사라지며, detail/streams payload 의 옛 activity_id 로 랩·스트림을 붙인다(BUG, REVIEW-08 §R3).
이 모듈은 API 호출 없이 (source, source_id) → 기존 id 로 매핑해 랩(UPSERT)·스트림(DELETE+INSERT)·활동 메트릭(UPSERT)만 갱신한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from src.sync._helpers import save_laps, save_metrics, save_streams
from src.sync.extractors import get_extractor

log = logging.getLogger(__name__)

_PAYLOAD_SQL = ("SELECT payload FROM source_payloads WHERE source = ? AND entity_type = ? AND entity_id = ? "
                "ORDER BY id DESC LIMIT 1")


def orphan_activity_count(conn: sqlite3.Connection, source: str | None = None) -> int:
    """activity_summary payload 가 없는 활동 수 — reprocess_all(clear_first=True) 시 영구 삭제될 행."""
    q = ("SELECT count(*) FROM activity_summaries a WHERE NOT EXISTS (SELECT 1 FROM source_payloads p "
         "WHERE p.source = a.source AND p.entity_type = 'activity_summary' AND p.entity_id = a.source_id)")
    return conn.execute(q + (" AND a.source = ?" if source else ""), (source,) if source else ()).fetchone()[0]


def reextract_laps_streams(conn: sqlite3.Connection, source: str = "garmin", dry_run: bool = False) -> dict:
    """반환 {"activities", "laps", "streams", "metrics", "missing_payload", "errors"}. dry_run 이면 쓰기 없이 집계만.
    활동 메트릭(예: gap)도 summary/detail payload 에서 다시 뽑아 UPSERT 한다(provider = source)."""
    stats = {"activities": 0, "laps": 0, "streams": 0, "metrics": 0, "missing_payload": 0, "errors": 0}
    ex = get_extractor(source)
    rows = conn.execute("SELECT id, source_id FROM activity_summaries WHERE source = ? ORDER BY id", (source,)).fetchall()
    for aid, sid in rows:
        try:
            splits = (conn.execute(_PAYLOAD_SQL, (source, "activity_splits", str(sid))).fetchone()
                      or conn.execute(_PAYLOAD_SQL, (source, "activity_detail", str(sid))).fetchone())
            streams = conn.execute(_PAYLOAD_SQL, (source, "activity_streams", str(sid))).fetchone()
            if not splits and not streams:
                stats["missing_payload"] += 1
                continue
            stats["activities"] += 1
            summ = conn.execute(_PAYLOAD_SQL, (source, "activity_summary", str(sid))).fetchone()
            det = conn.execute(_PAYLOAD_SQL, (source, "activity_detail", str(sid))).fetchone()
            if summ:
                ms = ex.extract_activity_metrics(json.loads(summ[0]), json.loads(det[0]) if det else None)
                stats["metrics"] += len(ms or [])
                if ms and not dry_run:
                    save_metrics(conn, "activity", str(aid), source, ms)
            if splits:
                laps = ex.extract_activity_laps(json.loads(splits[0]))
                stats["laps"] += len(laps or [])
                if laps and not dry_run:
                    save_laps(conn, aid, laps)
            if streams:
                srows = ex.extract_activity_streams(json.loads(streams[0]))
                stats["streams"] += len(srows or [])
                if srows and not dry_run:
                    save_streams(conn, aid, srows)
        except Exception as e:                      # 한 활동 실패로 전체 중단 금지
            log.error("reextract %s/%s: %s", source, sid, e)
            stats["errors"] += 1
    if not dry_run:
        conn.commit()
    return stats


if __name__ == "__main__":        # python3 -m src.sync.reextract --db <path> [--dry-run]
    import argparse

    ap = argparse.ArgumentParser(description="Garmin 랩·스트림 제자리 재추출(활동 id 유지)")
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    with sqlite3.connect(a.db) as _c:
        print(reextract_laps_streams(_c, dry_run=a.dry_run))
````

**`src/sync/reprocess.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/sync/reprocess.py
+++ b/src/sync/reprocess.py
@@ -12,6 +12,7 @@
 from collections import defaultdict
 
 from src.sync.extractors import get_extractor
+from src.sync.reextract import orphan_activity_count
 from src.sync.dedup import run as run_dedup
 from src.sync._helpers import (
     save_activity_core,
@@ -31,18 +32,16 @@
     conn: sqlite3.Connection,
     source: str | None = None,
     clear_first: bool = True,
+    force: bool = False,
 ) -> dict:
-    """Layer 0 → Layer 1 + Layer 2 전체 재구축.
-
-    Args:
-        conn: SQLite connection
-        source: 특정 소스만 재처리 (None이면 전체)
-        clear_first: True면 Layer 1/2 해당 데이터를 먼저 삭제
-
-    Returns:
-        {"activities": int, "metrics": int, "wellness": int, "errors": int}
+    """Layer 0 → Layer 1 + Layer 2 전체 재구축. source=None 이면 전체, clear_first 면 Layer 1/2 먼저 삭제.
+
+    clear_first 는 활동 id 를 새로 매긴다(참조 테이블 주의). payload 없는 활동이 있으면 force 없이는 거부.
+    Returns: {"activities": int, "metrics": int, "wellness": int, "errors": int}
     """
     stats = {"activities": 0, "metrics": 0, "wellness": 0, "errors": 0}
+    if clear_first and not force and (lost := orphan_activity_count(conn, source)):
+        raise RuntimeError(f"payload 없는 활동 {lost}건 삭제 위험 — reextract_laps_streams 사용 또는 force=True")
 
     log.info("Starting reprocess: source=%s, clear_first=%s", source or "all", clear_first)
 
@@ -85,12 +84,11 @@
 def _clear_derived_data(conn: sqlite3.Connection, source: str | None):
     """Layer 1/2 데이터 삭제 (source_payloads는 유지)."""
     if source:
+        aids = [r[0] for r in conn.execute(
+            "SELECT id FROM activity_summaries WHERE source = ?", (source,)
+        ).fetchall()]  # 요약 삭제 전에 id 수집(laps/streams 는 cascade 안 됨)
         conn.execute("DELETE FROM activity_summaries WHERE source = ?", (source,))
         conn.execute("DELETE FROM metric_store WHERE provider = ?", (source,))
-        # laps/streams는 activity_id 기준이라 cascade 안 되므로 별도 처리
-        aids = [r[0] for r in conn.execute(
-            "SELECT id FROM activity_summaries WHERE source = ?", (source,)
-        ).fetchall()]
         if aids:
             ph = ",".join("?" * len(aids))
             conn.execute(f"DELETE FROM activity_laps WHERE activity_id IN ({ph})", aids)
@@ -129,9 +127,10 @@
             activity_id = save_activity_core(conn, core)
             activity_id_map[(src, eid)] = activity_id
 
-            conn.execute(
-                "UPDATE source_payloads SET activity_id = ? WHERE id = ?",
-                (activity_id, sp_id),
+            conn.execute(  # 같은 활동의 detail/splits/streams payload 도 새 id 로(옛 id 부착 버그)
+                "UPDATE source_payloads SET activity_id = ? WHERE source = ? AND entity_id = ? "
+                "AND entity_type IN ('activity_summary', 'activity_detail', 'activity_splits', 'activity_streams')",
+                (activity_id, src, eid),
             )
             stats["activities"] += 1
         except Exception as e:
@@ -156,7 +155,7 @@
         try:
             detail = json.loads(payload_json)
             extractor = get_extractor(src)
-            activity_id = existing_aid or activity_id_map.get((src, eid))
+            activity_id = activity_id_map.get((src, eid)) or existing_aid
             if not activity_id:
                 continue
 
@@ -232,7 +231,7 @@
         try:
             detail = json.loads(payload_json)
             extractor = get_extractor(src)
-            activity_id = existing_aid or activity_id_map.get((src, eid))
+            activity_id = activity_id_map.get((src, eid)) or existing_aid
             if not activity_id:
                 continue
 
````

**`tests/test_reextract.py`** — 신규, 전문 그대로(70줄)

````python
"""P7-PRED-13: 제자리 재추출 — id 유지, 랩 GAP·스트림 경과시간 채움."""
import json

from src.sync.reextract import reextract_laps_streams
from tests.helpers_pred import mem_conn, seed_run

SPLITS = {"lapDTOs": [
    {"duration": 300.0, "distance": 1000.0, "averageHR": 150, "averageSpeed": 3.333, "intensityType": "WARMUP",
     "avgGradeAdjustedSpeed": 3.40, "elapsedDuration": 305.0, "movingDuration": 300.0, "elevationLoss": 2.0},
    {"duration": 240.0, "distance": 1000.0, "averageHR": 172, "averageSpeed": 4.167, "intensityType": "ACTIVE",
     "avgGradeAdjustedSpeed": 4.20}]}
STREAMS = {"metricDescriptors": [{"key": "sumElapsedDuration", "metricsIndex": 0},
                                 {"key": "sumDistance", "metricsIndex": 1},
                                 {"key": "directGradeAdjustedSpeed", "metricsIndex": 2},
                                 {"key": "directHeartRate", "metricsIndex": 3}],
           "activityDetailMetrics": [{"metrics": [0.0, 0.0, 3.0, 120]}, {"metrics": [5.2, 16.0, 3.1, 125]},
                                     {"metrics": [10.4, 32.5, 3.2, 130]}]}


def _payload(c, et, sid, obj):
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload) VALUES ('garmin', ?, ?, ?)",
              (et, sid, json.dumps(obj)))


def test_reextract_keeps_ids_and_fills_fields():
    c = mem_conn()
    seed_run(c, sid="999")                       # id 1: payload 없음(Strava 전용 등) — 그대로 남아야 함
    aid = seed_run(c, sid="12345")
    _payload(c, "activity_splits", "12345", SPLITS)
    _payload(c, "activity_streams", "12345", STREAMS)
    st = reextract_laps_streams(c)
    assert st == {"activities": 1, "laps": 2, "streams": 3, "metrics": 0, "missing_payload": 1, "errors": 0}
    laps = c.execute("SELECT lap_index, gap_speed_ms, elapsed_duration_sec, lap_trigger FROM activity_laps "
                     "WHERE activity_id=? ORDER BY lap_index", (aid,)).fetchall()
    assert laps[0][1:] == (3.40, 305.0, "WARMUP") and laps[1][1] == 4.20
    s = c.execute("SELECT elapsed_sec, distance_m, gap_speed_ms FROM activity_streams WHERE activity_id=? "
                  "ORDER BY elapsed_sec", (aid,)).fetchall()
    assert [r[0] for r in s] == [0, 5, 10] and s[2][1:] == (32.5, 3.2)
    assert c.execute("SELECT count(*) FROM activity_summaries").fetchone()[0] == 2


def test_activity_metrics_reextracted():
    c = mem_conn()
    aid = seed_run(c, sid="7")
    _payload(c, "activity_summary", "7", {"avgGradeAdjustedSpeed": 3.137})
    _payload(c, "activity_splits", "7", SPLITS)
    assert reextract_laps_streams(c)["metrics"] == 1
    r = c.execute("SELECT numeric_value FROM metric_store WHERE scope_id=? AND metric_name='gap' AND provider='garmin'",
                  (str(aid),)).fetchone()
    assert r[0] == 318.8


def test_dry_run_writes_nothing():
    c = mem_conn()
    seed_run(c, sid="1")
    _payload(c, "activity_splits", "1", SPLITS)
    assert reextract_laps_streams(c, dry_run=True)["laps"] == 2
    assert c.execute("SELECT count(*) FROM activity_laps").fetchone()[0] == 0


def test_orphan_guard_blocks_destructive_reprocess():
    import pytest
    from src.sync.reextract import orphan_activity_count
    from src.sync.reprocess import reprocess_all
    c = mem_conn()
    seed_run(c, sid="no_payload")                 # payload 없는 활동(Strava 등)
    assert orphan_activity_count(c) == 1
    with pytest.raises(RuntimeError):
        reprocess_all(c)
    assert c.execute("SELECT count(*) FROM activity_summaries").fetchone()[0] == 1
````

검증:
```
python3 -m pytest tests/test_reextract.py tests/test_reprocess.py -q
```

## P7-PRED-14 — CalcContext 러닝 이력 API(`RunHistoryMixin`) + 시리즈 canonical 옵션

- 의존: P7-PRED-11 · UI 노출: 없음 · 실DB: 없음
- 파일: `src/metrics/context_runs.py`(신규), `src/metrics/base.py`, `tests/test_context_runs.py`(신규)
- 왜: 예측 v2 calculator는 raw SQL 금지(ADR-009)라 canonical 러닝 + 트윈 HR 병합 + 랩(GAP 우선) + 대회 판정 + race_results + best effort + 일별 최신값 조회 API가 필요하다. `get_activity_metric_series`는 비canonical 행을 합산해 teroi 28일 TRIMP가 2.03배가 된다(REVIEW-08 #3) → `canonical_only`/`primary_only` 인자 추가(기본값 False로 호환 유지, 호출부 전환은 P7-PRED-81).
- API 요약:
  - `get_runs(days, end_date=None, with_laps=False, include_end=True) -> list[dict]` — 키: id, date, start_time, name, activity_type, distance_m, moving_s, elapsed_s, perf_time_s, avg_hr, max_hr, elevation_gain, lat, lon, device_temp_c, is_race, nominal_m, (laps: dist_m, dur_s, speed_ms(GAP 우선), raw_speed_ms, hr, max_hr, itype, temp_c, compliance, wkt_step, elev_gain, elev_loss)
  - `get_activity_metric_json(activity_id, name)`, `get_active_goal(as_of=None)`, `get_latest_daily_metric(name, as_of, provider=None, include_json=False)`, `get_best_efforts(days, effort_name, end_date=None)`, `get_race_results()`
  - 커서 단위 `row_factory`(연결 전역 변경 금지 — 기존 튜플 인덱싱 코드가 깨진다).

**`src/metrics/context_runs.py`** — 신규, 전문 그대로(152줄)

````python
"""CalcContext 러닝 이력 API(RunHistoryMixin) — canonical 러닝 + 트윈 HR 병합 + 랩(경사보정 속도) + 대회 판정.

Calculator 내부 raw SQL 금지(ADR-009) 원칙에 따라 예측 v2 계열 calculator 는 이 API만 쓴다.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

RUN_TYPES = ("running", "trail_running", "treadmill", "indoor_running", "virtual_running")
RACE_NAME = re.compile(r"대회|마라톤|marathon|half|하프|10k|10km|race|레이스", re.I)
NOT_RACE_NAME = re.compile(r"TT|템포|tempo", re.I)
NOMINAL = ((5000.0, 0.04), (10000.0, 0.04), (21097.5, 0.03), (42195.0, 0.02))

_RUNS_SQL = f"""
SELECT v.id, v.name, v.activity_type, v.start_time, v.distance_m, v.moving_time_sec, v.elapsed_time_sec,
       v.duration_sec, v.elevation_gain, v.start_lat, v.start_lon, v.avg_temperature,
       COALESCE(v.avg_hr, (SELECT o.avg_hr FROM activity_summaries o WHERE o.matched_group_id = v.matched_group_id
                           AND o.avg_hr IS NOT NULL ORDER BY CASE o.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2 ELSE 3 END LIMIT 1)) AS avg_hr,
       (SELECT max(o.max_hr) FROM activity_summaries o
         WHERE (o.id = v.id OR (v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id))
           AND NOT (o.source = 'intervals' AND o.max_hr >= 182)) AS max_hr,
       (SELECT group_concat(COALESCE(o.name, ''), ' | ') FROM activity_summaries o
         WHERE v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id) AS group_names,
       (SELECT count(*) FROM activity_summaries o
         WHERE (o.id = v.id OR (v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id))
           AND o.event_type = 'race') AS race_rows
FROM v_canonical_activities v
WHERE v.activity_type IN ({",".join("?" * len(RUN_TYPES))}) AND v.start_time >= ? AND v.start_time <= ?
ORDER BY v.start_time
"""

_LAPS_SQL = """
SELECT activity_id, lap_index, distance_m, duration_sec, elapsed_duration_sec, avg_hr, max_hr, avg_pace_sec_km,
       gap_speed_ms, elevation_gain, elevation_loss, avg_temperature_c, lap_trigger, compliance_score, wkt_step_index
FROM activity_laps WHERE activity_id IN ({ids}) ORDER BY activity_id, lap_index
"""


def nominal_distance(dist_m: float | None) -> float | None:
    if not dist_m:
        return None
    for n, tol in NOMINAL:
        if abs(dist_m - n) / n <= tol:
            return n
    return None


def lap_block(row) -> dict | None:
    """activity_laps 행 → segments 블록. speed_ms 는 GAP 우선."""
    d = row["distance_m"] or 0.0
    t = row["duration_sec"] or row["elapsed_duration_sec"] or 0.0
    if d <= 0 or t <= 0:
        return None
    raw = d / t
    return {"dist_m": d, "dur_s": t, "speed_ms": row["gap_speed_ms"] or raw, "raw_speed_ms": raw,
            "hr": row["avg_hr"], "max_hr": row["max_hr"], "itype": row["lap_trigger"],
            "temp_c": row["avg_temperature_c"], "compliance": row["compliance_score"], "wkt_step": row["wkt_step_index"],
            "elev_gain": row["elevation_gain"], "elev_loss": row["elevation_loss"]}


class RunHistoryMixin:
    """CalcContext 에 섞어 쓰는 러닝 이력 조회."""

    def _end_date(self, end_date: str | None) -> datetime:
        if end_date:
            return datetime.strptime(end_date[:10], "%Y-%m-%d")
        if getattr(self, "scope_type", None) == "daily":
            return datetime.strptime(self.scope_id, "%Y-%m-%d")
        return datetime.now()

    def get_runs(self, days: int, end_date: str | None = None, with_laps: bool = False,
                 include_end: bool = True) -> list[dict]:
        """[end_date-days, end_date] canonical 러닝. include_end=False 면 end_date 당일 제외(예측 누수 방지)."""
        end = self._end_date(end_date)
        start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
        stop = end.strftime("%Y-%m-%d") + (" 23:59:59" if include_end else " 00:00:00")
        cur = self.conn.cursor()
        cur.row_factory = _row_factory          # 연결의 row_factory 는 건드리지 않는다
        rows = cur.execute(_RUNS_SQL, [*RUN_TYPES, start, stop]).fetchall()
        runs = []
        for r in rows:
            mv = r["moving_time_sec"] or r["duration_sec"] or 0
            el = r["elapsed_time_sec"] or r["duration_sec"] or mv
            names = f"{r['name'] or ''} | {r['group_names'] or ''}"
            is_race = bool(r["race_rows"]) or (bool(RACE_NAME.search(names)) and not NOT_RACE_NAME.search(names))
            runs.append({
                "id": r["id"], "date": r["start_time"][:10], "start_time": r["start_time"], "name": r["name"],
                "activity_type": r["activity_type"], "distance_m": r["distance_m"] or 0.0,
                "moving_s": mv, "elapsed_s": el,
                "perf_time_s": el if (el and mv and el <= mv * 1.05) or is_race else mv,
                "avg_hr": r["avg_hr"], "max_hr": r["max_hr"], "elevation_gain": r["elevation_gain"] or 0.0,
                "lat": r["start_lat"], "lon": r["start_lon"], "device_temp_c": r["avg_temperature"],
                "is_race": is_race, "nominal_m": nominal_distance(r["distance_m"]) if is_race else None,
            })
        if with_laps and runs:
            by_id = {x["id"]: x for x in runs}
            for x in runs:
                x["laps"] = []
            ids = ",".join(str(i) for i in by_id)
            for lr in cur.execute(_LAPS_SQL.format(ids=ids)).fetchall():
                b = lap_block(lr)
                if b:
                    by_id[lr["activity_id"]]["laps"].append(b)
        return runs

    def get_activity_metric_json(self, activity_id: int, metric_name: str) -> str | None:
        row = self.conn.execute(
            "SELECT json_value FROM metric_store WHERE scope_type='activity' AND scope_id=? AND metric_name=? AND is_primary=1",
            [str(activity_id), metric_name]).fetchone()
        return row[0] if row else None

    def get_active_goal(self, as_of: str | None = None) -> dict | None:
        d = (as_of or self._end_date(None).strftime("%Y-%m-%d"))[:10]
        row = self.conn.execute(
            "SELECT id, name, race_date, distance_km, target_time_sec FROM goals WHERE status='active' "
            "AND race_date IS NOT NULL AND race_date >= ? ORDER BY race_date LIMIT 1", [d]).fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "race_date": row[2], "distance_km": row[3], "target_time_sec": row[4]}

    def get_latest_daily_metric(self, metric_name: str, as_of: str, provider: str | None = None,
                                include_json: bool = False):
        """as_of(포함) 이전 가장 최근 일별 값. include_json 이면 (numeric, json) 튜플."""
        sql = ("SELECT numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
               "AND scope_id <= ? " + ("AND provider=? " if provider else "AND is_primary=1 ") +
               "ORDER BY scope_id DESC LIMIT 1")
        params = [metric_name, as_of[:10]] + ([provider] if provider else [])
        row = self.conn.execute(sql, params).fetchone()
        if not row:
            return (None, None) if include_json else None
        return (row[0], row[1]) if include_json else row[0]

    def get_best_efforts(self, days: int, effort_name: str, end_date: str | None = None) -> list[dict]:
        """[end_date-days, end_date) 구간 best effort(Strava 등) → [{"activity_id","date","elapsed_s","distance_m"}] 빠른 순."""
        end = self._end_date(end_date)
        start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.conn.execute(
            "SELECT b.activity_id, substr(a.start_time, 1, 10), b.elapsed_sec, b.distance_m FROM activity_best_efforts b "
            "JOIN activity_summaries a ON a.id = b.activity_id WHERE b.effort_name = ? AND a.start_time >= ? "
            "AND a.start_time < ? AND b.elapsed_sec > 0 ORDER BY b.elapsed_sec",
            [effort_name, start, end.strftime("%Y-%m-%d")]).fetchall()
        return [{"activity_id": r[0], "date": r[1], "elapsed_s": r[2], "distance_m": r[3]} for r in rows]

    def get_race_results(self) -> dict[int, dict]:
        """사용자 대회 확인(race_results) activity_id → {effort, official_time_sec, distance_m}."""
        rows = self.conn.execute("SELECT activity_id, effort, official_time_sec, distance_m FROM race_results").fetchall()
        return {r[0]: {"effort": r[1], "official_time_sec": r[2], "distance_m": r[3]} for r in rows}


def _row_factory(cursor, row):
    return {d[0]: v for d, v in zip(cursor.description, row)}
````

**`src/metrics/base.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/base.py
+++ b/src/metrics/base.py
@@ -10,6 +10,8 @@
 from dataclasses import dataclass, field
 from datetime import datetime, timedelta, timezone
 from typing import Optional
+
+from src.metrics.context_runs import RunHistoryMixin
 
 log = logging.getLogger(__name__)
 
@@ -81,7 +83,7 @@
 
 
 @dataclass
-class CalcContext:
+class CalcContext(RunHistoryMixin):
     """Calculator에 전달되는 컨텍스트. prefetch + cache-first, fallback DB."""
     conn: object
     scope_type: str
@@ -363,6 +365,8 @@
     def get_activity_metric_series(self, metric_name: str, days: int,
                                     activity_type: str = None,
                                     include_json: bool = False,
+                                    canonical_only: bool = False,
+                                    primary_only: bool = False,
                                     ) -> list[dict]:
         """activity-scope metric을 날짜 범위로 조회.
 
@@ -384,10 +388,12 @@
 
         sql = (
             f"SELECT {cols} FROM metric_store ms "
-            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
+            f"JOIN {'v_canonical_activities' if canonical_only else 'activity_summaries'} a "
+            "ON CAST(ms.scope_id AS INTEGER) = a.id "
             "WHERE ms.metric_name=? AND ms.scope_type='activity' "
             "AND ms.numeric_value IS NOT NULL "
             "AND DATE(a.start_time) BETWEEN ? AND ?"
+            + (" AND ms.is_primary = 1" if primary_only else "")
         )
         params: list = [metric_name, start_date, end_date]
         if activity_type:
````

**`tests/test_context_runs.py`** — 신규, 전문 그대로(66줄)

````python
"""P7-PRED-14: RunHistoryMixin.get_runs / get_active_goal / get_race_results / canonical 시리즈."""
from src.metrics.base import CalcContext
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def test_get_runs_twin_hr_and_race():
    c = mem_conn()
    g = seed_run(c, sid="g1", name="Forest run", avg_hr=None, max_hr=None, group="G1", event_type="race")
    seed_run(c, source="intervals", sid="i1", name="나는 솔로런 10k", avg_hr=165, max_hr=182, group="G1")
    seed_run(c, source="strava", sid="s1", name="Morning", avg_hr=164, max_hr=186, group="G1")
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    runs = ctx.get_runs(30)
    assert len(runs) == 1
    r = runs[0]
    assert r["id"] == g and r["avg_hr"] == 164 and r["max_hr"] == 186      # intervals 182 절단값 제외
    assert r["is_race"] is True and r["nominal_m"] == 10000.0


def test_get_runs_excludes_end_day_and_laps():
    c = mem_conn()
    a = seed_run(c, sid="a", date="2026-05-09")
    seed_run(c, sid="b", date="2026-05-10")
    seed_laps(c, a, [(1000, 250, 160, "ACTIVE", 4.1, 170), (1000, 360, 140, "RECOVERY", None, 150)])
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    runs = ctx.get_runs(30, with_laps=True, include_end=False)
    assert [x["id"] for x in runs] == [a]
    assert runs[0]["laps"][0]["speed_ms"] == 4.1 and round(runs[0]["laps"][1]["speed_ms"], 3) == 2.778
    assert runs[0]["laps"][0]["itype"] == "ACTIVE"


def test_tempo_name_not_race():
    c = mem_conn()
    seed_run(c, sid="t", name="2. 템포런 10k 빌드")
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    assert ctx.get_runs(5)[0]["is_race"] is False


def test_perf_time_uses_elapsed_when_close():
    c = mem_conn()
    seed_run(c, sid="p", moving=2600, elapsed=2650)
    seed_run(c, sid="q", date="2026-05-08", moving=2600, elapsed=3300)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    times = {x["date"]: x["perf_time_s"] for x in ctx.get_runs(5)}
    assert times == {"2026-05-09": 2650, "2026-05-08": 2600}


def test_active_goal_and_race_results():
    c = mem_conn()
    c.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) VALUES ('풀', '2026-11-22', 42.195, 11940, 'active')")
    a = seed_run(c, sid="r")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?, 10000, 2651, 'allout')", (a,))
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")
    assert ctx.get_active_goal()["target_time_sec"] == 11940
    assert ctx.get_race_results()[a]["effort"] == "allout"


def test_metric_series_canonical_only():
    c = mem_conn()
    a = seed_run(c, sid="g", group="G")
    b = seed_run(c, source="intervals", sid="i", group="G")
    for aid in (a, b):
        upsert_metric(c, "activity", aid, "trimp", "runpulse:formula_v1", numeric_value=100.0)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    assert len(ctx.get_activity_metric_series("trimp", 5)) == 2
    assert len(ctx.get_activity_metric_series("trimp", 5, canonical_only=True)) == 1
````

검증:
```
python3 -m pytest tests/test_context_runs.py tests/test_activity_calcs.py tests/test_sapi.py -q
```

