# PRED-7x — 예측 UI: 3경로 비교·범위·신뢰도·근거·대회 확인 (예측 리뉴얼 r3)

근거: `REVIEW-07-prediction-renewal.md` r3 §5(UI)·B(기기 독립성).

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-71 — 예측 3경로 비교 API + 레이스 허브 필드 + 예측 근거 API + 대회 확인 API

- 의존: P7-PRED-51, P7-PRED-53, P7-PRED-25 · UI 노출: 없음(데이터만, P7-PRED-72~74가 표시) · 실DB: 없음
- 파일: `src/services/prediction_compare_service.py`(신규), `src/api/routes_prediction.py`(신규), `src/api/__init__.py`, `src/services/race_hub_service.py`, `tests/test_prediction_compare.py`, `tests/test_api_prediction.py`(신규)
- 계약:
  - `GET /api/v1/prediction/compare?bucket=5k|10k|half|marathon[&date=]` → `{bucket, as_of, rows: [{key: garmin|ref|self, label, provider, value_sec, as_of, stale_days, low_sec, high_sec, confidence, reasons, contributions}], hr_basis: {self_lthr, ref_lthr, lthr_gap}, notes: [문자열]}`. 값이 없는 경로는 `value_sec: null`만.
  - `GET /api/v1/today/race-hub` 의 `prediction.compare` 에 같은 객체(목표 거리 버킷).
  - `GET /api/v1/prediction/profile[?date=]` → `{as_of, hr_profile, heat_model, training_response}`(각 최신 json + `date`, 없으면 null).
  - `GET /api/v1/races/candidates[?since=]`, `PUT /api/v1/races/<activity_id>/confirm` body `{effort, official_time_sec?, race_name?, distance_m?, note?}`(400: effort·시간 범위, 404: 활동 없음), `DELETE` 같은 경로.
- 차이의 이유(규칙, LLM 없음): Garmin 대 자체 %와 방법 차이(VO2max 추정 vs 최근 대회·작업 구간·심박), Garmin 값이 14일 넘게 묵었으면 표시, 기기 기준 대 자체 차이 < 1%면 "영향 작음", 아니면 LTHR 차이 bpm이 작업 구간 자격·심박 신호를 바꿨다고 표시, 경로가 없으면 이유(동기화 필요·기기 LTHR 미수집).

- r4 추가(REVIEW-07 §R4-8(4)): r4 섀도(`runpulse:shadow_r4`, `runpulse:shadow_r4_asym`) 값이 있으면 `candidate: true` 행(key `r4`, `r4_asym`)을 **뒤에** 붙인다. 없으면 행을 두지 않는다. 기본 행 `self`는 r3 (c) 그대로다. 기여도 키는 r3(race·work·hr·best_effort)와 r4(race·paced·T·I·R·M·H)를 모두 지원한다.

**`src/services/prediction_compare_service.py`** — 신규, 전문 그대로(88줄)

````python
"""레이스 예측 3경로 비교(P7-PRED-71) — (a) Garmin 예측, (b) RunPulse·기기 심박 기준, (c) RunPulse·자체 추정(기본, r3)
+ 값이 있으면 r4 섀도 후보 2개(candidate=True, 기본 표시 아님 — REVIEW-07 §R4-8(4)).

같은 metric_name(race_pred_{bucket}_sec)을 provider 로 구분해 읽고, 차이의 이유를 규칙으로 만든다(LLM 없음).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

PATHS = (("garmin", "garmin", "Garmin 예측"),
         ("ref", "runpulse:ref_garmin", "RunPulse · 기기 심박 기준"),
         ("self", "runpulse:formula_v1", "RunPulse · 자체 추정"))
CANDIDATES = (("r4", "runpulse:shadow_r4", "후보 r4 · 섀도"),
              ("r4_asym", "runpulse:shadow_r4_asym", "후보 r4 비대칭 · 섀도"))
STALE_DAYS = 14
SMALL_PCT = 1.0


def _latest(conn, metric: str, provider: str, as_of: str):
    return conn.execute(
        "SELECT scope_id, numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
        "AND provider=? AND numeric_value IS NOT NULL AND scope_id <= ? ORDER BY scope_id DESC LIMIT 1",
        (metric, provider, as_of)).fetchone()


def _pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 1)


def compare(conn: sqlite3.Connection, bucket: str, as_of: str | None = None) -> dict:
    as_of = as_of or _date.today().isoformat()
    metric = f"race_pred_{bucket}_sec"
    rows = []
    for key, prov, label in PATHS + CANDIDATES:
        r = _latest(conn, metric, prov, as_of)
        cand = (key, prov, label) in CANDIDATES
        if r is None:
            if not cand:                      # 섀도 값이 없으면 행 자체를 두지 않는다
                rows.append({"key": key, "label": label, "provider": prov, "value_sec": None})
            continue
        j = json.loads(r[2]) if r[2] else {}
        rows.append({"key": key, "label": label, "provider": prov, "value_sec": int(round(r[1])), "as_of": r[0],
                     "stale_days": (_date.fromisoformat(as_of) - _date.fromisoformat(r[0])).days,
                     "low_sec": j.get("low_s"), "high_sec": j.get("high_s"), "confidence": j.get("confidence"),
                     "reasons": j.get("reasons", []), "contributions": j.get("contributions"),
                     **({"candidate": True} if cand else {})})
    by = {r["key"]: r for r in rows}
    hp = _latest(conn, "hr_profile", "runpulse:formula_v1", as_of)
    hj = json.loads(hp[2]) if hp and hp[2] else {}
    hr_basis = {"self_lthr": (hj.get("self") or {}).get("lthr"), "ref_lthr": (hj.get("ref") or {}).get("lthr"),
                "lthr_gap": hj.get("lthr_gap")}
    return {"bucket": bucket, "as_of": as_of, "rows": rows, "hr_basis": hr_basis, "notes": _notes(by, hr_basis)}


def _notes(by: dict, hb: dict) -> list[str]:
    out = []
    s, g, r = by["self"].get("value_sec"), by["garmin"].get("value_sec"), by["ref"].get("value_sec")
    if g and s:
        d = _pct(g, s)
        out.append(f"Garmin 예측이 자체 추정보다 {abs(d)}% {'느림' if d > 0 else '빠름'} — Garmin은 VO2max 추정 기반, "
                   "RunPulse는 최근 전력 대회·품질 세트(휴식 보정 Daniels 강도)·심박-속도 관계 기반")
        if by["garmin"]["stale_days"] > STALE_DAYS:
            out.append(f"Garmin 값은 {by['garmin']['stale_days']}일 전 스냅샷")
    elif not g:
        out.append("Garmin 예측 없음(동기화 필요)")
    if r and s:
        d = _pct(r, s)
        gap = hb.get("lthr_gap")
        if abs(d) < SMALL_PCT:
            out.append(f"심박 기준(자체 LTHR {hb.get('self_lthr')} vs 기기 {hb.get('ref_lthr')})에 따른 차이 {abs(d)}% — 영향 작음")
        else:
            out.append(f"기기 심박 기준 예측이 {abs(d)}% {'느림' if d > 0 else '빠름'} — LTHR 차이 {gap} bpm 이 "
                       "심박 신호(H)·세트 품질 가중을 바꿈")
    elif not r:
        out.append("기기 심박 기준값 없음 — 기기 LTHR 미수집")
    return out


def profile(conn: sqlite3.Connection, as_of: str | None = None) -> dict:
    """P7-PRED-74 카드용: 최신 hr_profile·heat_model·training_response json(없으면 None)."""
    as_of = as_of or _date.today().isoformat()
    out = {"as_of": as_of}
    for key in ("hr_profile", "heat_model", "training_response"):
        r = _latest(conn, key, "runpulse:formula_v1", as_of)
        out[key] = ({"date": r[0], **json.loads(r[2])} if r and r[2] else None)
    return out
````

**`src/api/routes_prediction.py`** — 신규, 전문 그대로(85줄)

````python
"""GET /api/v1/prediction/compare, GET /api/v1/prediction/profile, GET /api/v1/races/candidates, PUT·DELETE /api/v1/races/<activity_id>/confirm — P7-PRED-53·71."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from flask import request

from src.services import prediction_compare_service, race_result_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok

_BUCKETS = ("5k", "10k", "half", "marathon")


def _conn():
    p = db_path()
    return sqlite3.connect(str(p)) if p.exists() else None


@api_bp.get("/prediction/compare")
def get_prediction_compare():
    bucket = request.args.get("bucket", "10k")
    if bucket not in _BUCKETS:
        return api_error("BAD_REQUEST", f"bucket must be one of {_BUCKETS}")
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(prediction_compare_service.compare(conn, bucket, request.args.get("date")))
    finally:
        conn.close()


@api_bp.get("/prediction/profile")
def get_prediction_profile():
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(prediction_compare_service.profile(conn, request.args.get("date")))
    finally:
        conn.close()


@api_bp.get("/races/candidates")
def get_race_candidates():
    since = request.args.get("since") or (date.today() - timedelta(days=365)).isoformat()
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"items": race_result_service.candidates(conn, since)})
    finally:
        conn.close()


@api_bp.put("/races/<int:activity_id>/confirm")
def put_race_confirm(activity_id: int):
    body = request.get_json(silent=True) or {}
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        res = race_result_service.confirm(conn, activity_id, body.get("effort", ""), body.get("official_time_sec"),
                                          body.get("race_name"), body.get("distance_m"), body.get("note"))
        return api_ok(res)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e))
    except LookupError:
        return api_error("NOT_FOUND", "activity not found", 404)
    finally:
        conn.close()


@api_bp.delete("/races/<int:activity_id>/confirm")
def delete_race_confirm(activity_id: int):
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"deleted": race_result_service.remove(conn, activity_id)})
    finally:
        conn.close()
````

**`src/api/__init__.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/api/__init__.py
+++ b/src/api/__init__.py
@@ -52,4 +52,4 @@
     return None
 
 
-from . import routes_coach, routes_library, routes_plan, routes_today  # noqa: E402,F401
+from . import routes_coach, routes_library, routes_plan, routes_prediction, routes_today  # noqa: E402,F401
````

**`src/services/race_hub_service.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/services/race_hub_service.py
+++ b/src/services/race_hub_service.py
@@ -3,6 +3,7 @@
 
 import sqlite3
 
+from src.services import prediction_compare_service
 from src.services.race_projection_service import project_race_form
 from datetime import date as _date, timedelta  # noqa: F401
 
@@ -98,6 +99,7 @@
                 "as_of":     as_of,
                 "gap_sec":   gap_sec,
                 "history":   [{"date": r["date"], "value": int(r["value"])} for r in history_rows],
+                "compare":   prediction_compare_service.compare(conn, bucket, date),   # P7-PRED-71 3경로 비교
             }
 
     return {
````

**`tests/test_prediction_compare.py`** — 신규, 전문 그대로(68줄)

````python
"""P7-PRED-71: 3경로 비교 서비스."""
from src.services.prediction_compare_service import compare
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn


def _seed(c):
    upsert_metric(c, "daily", "2026-05-11", "race_pred_10k_sec", "garmin", numeric_value=2585)
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:ref_garmin", numeric_value=2741,
                  json_value={"low_s": 2602, "high_s": 2879, "confidence": 0.75, "reasons": [], "contributions": {}})
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739,
                  json_value={"low_s": 2601, "high_s": 2878, "confidence": 0.75, "reasons": ["기준 대회가 20주 전"]})
    upsert_metric(c, "daily", "2026-09-26", "hr_profile", "runpulse:formula_v1", numeric_value=177.4,
                  json_value={"self": {"lthr": 177.4}, "ref": {"lthr": 177.0}, "lthr_gap": 0.4})


def test_three_rows_and_notes():
    c = mem_conn()
    _seed(c)
    r = compare(c, "10k", "2026-09-26")
    assert [x["value_sec"] for x in r["rows"]] == [2585, 2741, 2739]
    assert r["rows"][0]["stale_days"] == 138
    assert r["notes"][0].startswith("Garmin 예측이 자체 추정보다 5.6% 빠름")
    assert r["notes"][1] == "Garmin 값은 138일 전 스냅샷"
    assert "영향 작음" in r["notes"][2] and r["hr_basis"]["lthr_gap"] == 0.4


def test_missing_paths():
    c = mem_conn()
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    r = compare(c, "10k", "2026-09-26")
    assert r["rows"][0]["value_sec"] is None
    assert r["notes"] == ["Garmin 예측 없음(동기화 필요)", "기기 심박 기준값 없음 — 기기 LTHR 미수집"]


def test_race_hub_includes_compare():
    from src.services.race_hub_service import get_race_hub
    c = mem_conn()
    _seed(c)
    c.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) "
              "VALUES ('가을 10K', '2026-11-01', 10.0, 2700, 'active')")
    hub = get_race_hub(c, "2026-09-26")
    assert hub["prediction"]["value_sec"] == 2739
    assert [r["value_sec"] for r in hub["prediction"]["compare"]["rows"]] == [2585, 2741, 2739]


def test_profile_reads_latest():
    from src.services.prediction_compare_service import profile
    c = mem_conn()
    _seed(c)
    p = profile(c, "2026-09-30")
    assert p["hr_profile"]["date"] == "2026-09-26" and p["hr_profile"]["lthr_gap"] == 0.4 and p["heat_model"] is None


def test_shadow_candidates_only_when_present():
    """P7-PRED-71: r4 섀도는 값이 있을 때만 candidate 행으로 붙는다(기본 'self' 는 r3)."""
    import sqlite3
    from src.db_setup import create_tables
    from src.services.prediction_compare_service import compare
    from src.utils.db_helpers import upsert_metric
    c = sqlite3.connect(":memory:")
    create_tables(c)
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    assert [r["key"] for r in compare(c, "10k", "2026-09-26")["rows"]] == ["garmin", "ref", "self"]
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:shadow_r4", numeric_value=2775,
                  json_value={"contributions": {"T": 0.4}})
    rows = compare(c, "10k", "2026-09-26")["rows"]
    assert rows[-1]["key"] == "r4" and rows[-1]["candidate"] is True and rows[-1]["value_sec"] == 2775
````

**`tests/test_api_prediction.py`** — 신규, 전문 그대로(55줄)

````python
"""P7-PRED-53·71: 예측 비교·대회 확인 API."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import seed_run


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    aid = seed_run(conn, sid="1", date="2026-09-12", name="Forest run", event_type="race")
    upsert_metric(conn, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    conn.commit()
    conn.close()
    import src.api.routes_prediction as rp
    monkeypatch.setattr(rp, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        c.aid = aid
        yield c


def test_compare(client):
    r = client.get("/api/v1/prediction/compare?bucket=10k&date=2026-09-26")
    assert r.status_code == 200
    rows = r.get_json()["data"]["rows"]
    assert [x["key"] for x in rows] == ["garmin", "ref", "self"] and rows[2]["value_sec"] == 2739
    assert client.get("/api/v1/prediction/compare?bucket=3k").status_code == 400


def test_profile(client):
    d = client.get("/api/v1/prediction/profile?date=2026-09-26").get_json()["data"]
    assert d == {"as_of": "2026-09-26", "hr_profile": None, "heat_model": None, "training_response": None}


def test_confirm_flow(client):
    r = client.get("/api/v1/races/candidates?since=2026-01-01")
    assert r.get_json()["data"]["items"][0]["activity_id"] == client.aid
    r = client.put(f"/api/v1/races/{client.aid}/confirm", json={"effort": "allout", "official_time_sec": 2800})
    assert r.status_code == 200 and r.get_json()["data"]["effort"] == "allout"
    assert client.put(f"/api/v1/races/{client.aid}/confirm", json={"effort": "x"}).status_code == 400
    assert client.put("/api/v1/races/999/confirm", json={"effort": "allout"}).status_code == 404
    assert client.delete(f"/api/v1/races/{client.aid}/confirm").get_json()["data"]["deleted"] is True
````

검증:
```
python3 -m pytest tests/test_prediction_compare.py tests/test_api_prediction.py tests/test_api_today.py -q
python3 scripts/check_docs.py
```

## P7-PRED-72 — 레이스 허브: 80% 범위·신뢰도 + 3경로 비교 카드 (프론트)

- 의존: P7-PRED-71 · **UI 노출: Today 레이스 허브**(예측 기록 아래 "80% 범위 … · 신뢰도 … · 15℃ 기준" 한 줄, 그 아래 3행 비교 표와 이유 문구)
- 파일: `frontend/src/lib/predictionCompare.ts`(신규), `frontend/tests/predictionCompare.test.mjs`(신규), `frontend/src/lib/components/PredictionCompare.svelte`(신규), `frontend/src/lib/types/index.ts`, `frontend/src/lib/api/prediction.ts`(신규), `frontend/src/lib/components/RaceHub.svelte`, `frontend/src/lib/components/PredictionBasis.svelte`(신규, P7-PRED-74 내용), `frontend/src/lib/components/RaceConfirmList.svelte`(신규, P7-PRED-73 내용)
- RaceHub diff는 세 컴포넌트를 한 번에 import 하므로 P7-PRED-72·73·74는 **한 유닛으로 구현**한다(아래 P7-PRED-73·74 절은 화면 설명). 문구·클래스는 그대로.
- 표시 규칙: 신뢰도 ≥0.7 높음 / ≥0.45 보통 / 그 외 낮음. 자체 대비 차이는 부호 있는 % 소수 1자리(0.05% 미만 "같음"). 기여도 0인 항목은 숨김. Garmin 값이 14일 넘으면 "N일 전 값"(amber).

- r4 추가:
  - `CompareRow.key`에 `r4`·`r4_asym`, `candidate?`를 추가한다. 후보 행은 흐린 이탤릭 라벨로 표시한다.
  - 기여도 라벨: r3 키(`work` 작업 블록, `hr` 심박, `best_effort` 5K 구간 기록)와 r4 키(`paced` 최대 이하 대회, T/I/R/M/H)를 모두 표시한다.
  - 훈련 반응 문구는 세트 기반(`quality_*`)이다.

**`frontend/src/lib/predictionCompare.ts`** — 신규, 전문 그대로(70줄)

````ts
// frontend/src/lib/predictionCompare.ts
// 레이스 예측 3경로 비교 표시용 순수 함수(P7-PRED-72). 테스트: frontend/tests/predictionCompare.test.mjs

export interface CompareRow {
	key: 'garmin' | 'ref' | 'self' | 'r4' | 'r4_asym';
	label: string;
	provider: string;
	value_sec: number | null;
	as_of?: string;
	stale_days?: number;
	low_sec?: number | null;
	high_sec?: number | null;
	confidence?: number | null;
	reasons?: string[];
	contributions?: Record<string, number> | null;
	candidate?: boolean; // r4 섀도 후보(기본 표시 아님)
}

/** 초 → 'h:mm:ss' 또는 'm:ss'. */
export function clock(sec: number): string {
	const s = Math.round(sec);
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	const r = s % 60;
	const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
	return (h > 0 ? `${h}:` : '') + `${mm}:${String(r).padStart(2, '0')}`;
}

/** 80% 범위 문구. 둘 중 하나라도 없으면 null. */
export function rangeLabel(row: CompareRow): string | null {
	if (row.low_sec == null || row.high_sec == null) return null;
	return `${clock(row.low_sec)}~${clock(row.high_sec)}`;
}

/** 신뢰도 0~1 → 3단계. ≥0.7 높음, ≥0.45 보통, 그 외 낮음. null이면 null. */
export function confidenceLabel(c: number | null | undefined): '높음' | '보통' | '낮음' | null {
	if (c == null) return null;
	if (c >= 0.7) return '높음';
	if (c >= 0.45) return '보통';
	return '낮음';
}

/** 자체 추정 대비 차이(%) 문구 — 기준 행이나 대상 값이 없으면 null. 양수 = 느림. */
export function diffVsSelf(row: CompareRow, self: CompareRow | undefined): string | null {
	if (!self?.value_sec || !row.value_sec || row.key === 'self') return null;
	const pct = (row.value_sec / self.value_sec - 1) * 100;
	if (Math.abs(pct) < 0.05) return '같음';
	return `${pct > 0 ? '+' : '−'}${Math.abs(pct).toFixed(1)}%`;
}

/** 기여도 키(칼만 이득 분해, REVIEW-09 §5) → 표시 이름. 순서 = 표시 순서. */
export const CONTRIBUTION_LABELS: [string, string][] = [
	['race', '대회'],
	['paced', '최대 이하 대회'],
	['work', '작업 블록'],
	['hr', '심박'],
	['best_effort', '5K 구간 기록'],
	['T', '역치 세트'],
	['I', '인터벌 세트'],
	['R', '반복 세트'],
	['M', '마라톤 구간'],
	['H', '심박']
];

/** 기여도 → '대회 28 · 역치 세트 32 · 인터벌 세트 19 · 심박 21' (1% 미만 생략). */
export function contributionLabel(c: CompareRow['contributions']): string | null {
	if (!c) return null;
	const parts = CONTRIBUTION_LABELS.filter(([k]) => (c[k] ?? 0) >= 0.005).map(([k, l]) => `${l} ${Math.round((c[k] ?? 0) * 100)}`);
	return parts.length ? parts.join(' · ') : null;
}
````

**`frontend/tests/predictionCompare.test.mjs`** — 신규, 전문 그대로(35줄)

````js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clock, rangeLabel, confidenceLabel, diffVsSelf, contributionLabel } from '../src/lib/predictionCompare.ts';

const self = { key: 'self', label: '', provider: '', value_sec: 2739, low_sec: 2601, high_sec: 2878, confidence: 0.75 };

test('clock', () => {
	assert.equal(clock(2739), '45:39');
	assert.equal(clock(13239), '3:40:39');
	assert.equal(clock(59.6), '1:00');
});

test('rangeLabel / confidenceLabel', () => {
	assert.equal(rangeLabel(self), '43:21~47:58');
	assert.equal(rangeLabel({ ...self, low_sec: null }), null);
	assert.equal(confidenceLabel(0.75), '높음');
	assert.equal(confidenceLabel(0.45), '보통');
	assert.equal(confidenceLabel(0.2), '낮음');
	assert.equal(confidenceLabel(null), null);
});

test('diffVsSelf', () => {
	assert.equal(diffVsSelf({ key: 'garmin', label: '', provider: '', value_sec: 2585 }, self), '−5.6%');
	assert.equal(diffVsSelf({ key: 'ref', label: '', provider: '', value_sec: 2741 }, self), '+0.1%');
	assert.equal(diffVsSelf(self, self), null);
	assert.equal(diffVsSelf({ key: 'garmin', label: '', provider: '', value_sec: null }, self), null);
});

test('contributionLabel', () => {
	assert.equal(contributionLabel({ race: 0.277, T: 0.324, I: 0.188, R: 0.0, H: 0.21 }), '대회 28 · 역치 세트 32 · 인터벌 세트 19 · 심박 21');
	assert.equal(contributionLabel({ race: 0.6, work: 0.2, hr: 0.2 }), '대회 60 · 작업 블록 20 · 심박 20'); // r3 기본 키
	assert.equal(contributionLabel({ race: 0.05, paced: 0.09, T: 0.86 }), '대회 5 · 최대 이하 대회 9 · 역치 세트 86');
	assert.equal(contributionLabel({ T: 0.6, H: 0.4 }), '역치 세트 60 · 심박 40');
	assert.equal(contributionLabel(null), null);
});
````

**`frontend/src/lib/types/index.ts`** — 수정, 아래 diff 그대로

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -655,6 +655,65 @@
 	as_of: string;
 	gap_sec: number | null;
 	history: RaceHubPredictionPoint[];
+	compare?: PredictionCompare | null;
+}
+
+/** P7-PRED-71 레이스 예측 3경로 비교 — (a) garmin, (b) ref(기기 심박 기준), (c) self(자체 추정). */
+export interface PredictionCompareRow {
+	key: 'garmin' | 'ref' | 'self';
+	label: string;
+	provider: string;
+	value_sec: number | null;
+	as_of?: string;
+	stale_days?: number;
+	low_sec?: number | null;
+	high_sec?: number | null;
+	confidence?: number | null;
+	reasons?: string[];
+	contributions?: { race: number; work: number; hr: number } | null;
+}
+
+export interface PredictionCompare {
+	bucket: string;
+	as_of: string;
+	rows: PredictionCompareRow[];
+	hr_basis: { self_lthr: number | null; ref_lthr: number | null; lthr_gap: number | null };
+	notes: string[];
+}
+
+export type ZoneBounds = [number, number][];
+
+/** P7-PRED-74 예측 근거 — hr_profile·heat_model·training_response 최신 json(없으면 null). */
+export interface PredictionProfile {
+	as_of: string;
+	hr_profile: {
+		date: string;
+		self: { hrmax: number | null; lthr: number; lthr_source: 'races' | 'hrmax_ratio'; rhr: number | null };
+		ref: { source: string; lthr: number | null; hrmax: number | null } | null;
+		zones: { self: { hrr: ZoneBounds | null; lthr: ZoneBounds }; ref?: { hrr: ZoneBounds | null; lthr: ZoneBounds | null } };
+		lthr_gap: number | null;
+	} | null;
+	heat_model: { date: string; heat: number; cold: number; n: number; weight: number } | null;
+	training_response: {
+		date: string;
+		weekly_zone_min: { R: number[]; I: number[]; T: number[]; M: number[]; sessions: number[] };
+		quality_min_avg_8w: number;
+		quality_min_avg_prev_8w: number | null;
+		quality_sessions_avg_8w: number;
+		long_mp_km_8w?: number;
+		trend: { n: number; slope_4w: number | null };
+	} | null;
+}
+
+export type RaceEffort = 'allout' | 'paced' | 'fun' | 'dnf';
+
+export interface RaceCandidate {
+	activity_id: number;
+	date: string;
+	name: string | null;
+	distance_m: number;
+	time_sec: number | null;
+	confirmed_effort: RaceEffort | null;
 }
 
 export interface RaceHubForm {
````

**`frontend/src/lib/api/prediction.ts`** — 신규, 전문 그대로(21줄)

````ts
import { apiFetch } from './client';
import type { PredictionProfile, RaceCandidate, RaceEffort } from '$lib/types';

export function getPredictionProfile(): Promise<PredictionProfile> {
	return apiFetch<PredictionProfile>('/prediction/profile');
}

export function getRaceCandidates(): Promise<RaceCandidate[]> {
	return apiFetch<{ items: RaceCandidate[] }>('/races/candidates').then((r) => r.items);
}

export function putRaceConfirm(activityId: number, effort: RaceEffort, officialTimeSec?: number): Promise<unknown> {
	return apiFetch(`/races/${activityId}/confirm`, {
		method: 'PUT',
		body: JSON.stringify({ effort, official_time_sec: officialTimeSec ?? null })
	});
}

export function deleteRaceConfirm(activityId: number): Promise<unknown> {
	return apiFetch(`/races/${activityId}/confirm`, { method: 'DELETE' });
}
````

**`frontend/src/lib/components/PredictionCompare.svelte`** — 신규, 전문 그대로(50줄)

````svelte
<script lang="ts">
	// 레이스 예측 3경로 비교(P7-PRED-72): Garmin / RunPulse·기기 심박 기준 / RunPulse·자체 추정 + 차이의 이유.
	import type { PredictionCompare } from '$lib/types';
	import { clock, confidenceLabel, contributionLabel, diffVsSelf, rangeLabel } from '$lib/predictionCompare';

	let { compare }: { compare: PredictionCompare } = $props();
	const self = $derived(compare.rows.find((r) => r.key === 'self'));
</script>

<div class="flex flex-col gap-2" aria-label="예측 비교">
	<span class="text-xs text-fg-muted">예측 비교 · 15℃ 기준</span>
	<ul class="flex flex-col divide-y divide-border-subtle rounded-md border border-border-subtle">
		{#each compare.rows as row (row.key)}
			{@const diff = diffVsSelf(row, self)}
			{@const range = rangeLabel(row)}
			{@const conf = confidenceLabel(row.confidence)}
			<li class="flex items-baseline justify-between gap-3 px-3 py-2">
				<div class="flex min-w-0 flex-col">
					<span class="text-xs {row.key === 'self' ? 'font-semibold' : row.candidate ? 'text-fg-muted italic' : 'text-fg-secondary'}">{row.label}</span>
					{#if row.value_sec != null && (range || conf)}
						<span class="text-[11px] text-fg-muted"
							>{range ? `80% ${range}` : ''}{range && conf ? ' · ' : ''}{conf ? `신뢰도 ${conf}` : ''}</span
						>
					{/if}
					{#if row.key === 'garmin' && row.stale_days != null && row.stale_days > 14}
						<span class="text-[11px] text-semantic-amber">{row.stale_days}일 전 값</span>
					{/if}
				</div>
				<div class="flex shrink-0 items-baseline gap-2">
					<span class="font-mono text-base font-bold">{row.value_sec != null ? clock(row.value_sec) : '—'}</span>
					{#if diff}
						<span class="font-mono text-[11px] text-fg-muted">{diff}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
	{#if self?.contributions}
		{@const c = contributionLabel(self.contributions)}
		{#if c}
			<span class="text-[11px] text-fg-muted">자체 추정 근거 비중 · {c}</span>
		{/if}
	{/if}
	{#if self?.reasons && self.reasons.length}
		<span class="text-[11px] text-fg-muted">불확실성 · {self.reasons.join(' · ')}</span>
	{/if}
	{#each compare.notes as note}
		<p class="text-[11px] leading-tight text-fg-muted">{note}</p>
	{/each}
</div>
````

**`frontend/src/lib/components/RaceHub.svelte`** — 수정, 아래 diff 그대로

````diff
--- a/frontend/src/lib/components/RaceHub.svelte
+++ b/frontend/src/lib/components/RaceHub.svelte
@@ -3,6 +3,10 @@
 	// DECISIONS.md [P7-IMPL-RACE-HUB-UI]: 목표 있으면 D-day, 없으면 등록 유도 카드.
 	import type { RaceHubData } from '$lib/types';
 	import TrendChart from './TrendChart.svelte';
+	import PredictionCompare from './PredictionCompare.svelte';
+	import PredictionBasis from './PredictionBasis.svelte';
+	import RaceConfirmList from './RaceConfirmList.svelte';
+	import { rangeLabel, confidenceLabel } from '$lib/predictionCompare';
 	import { countdownLabel, distanceLabel, formBand, gapVerdict, signedTsb } from '$lib/raceHub';
 	import { formatDuration } from '$lib/format';
 	import { base } from '$app/paths';
@@ -17,6 +21,7 @@
 	};
 
 	const verdict = $derived(data?.prediction ? gapVerdict(data.prediction.gap_sec) : null);
+	const selfRow = $derived(data?.prediction?.compare?.rows.find((r) => r.key === 'self') ?? null);
 	const tsb = $derived(data?.form?.tsb ?? null);
 	const proj = $derived(data?.projection ?? null);
 	const FORM_TONE: Record<string, string> = {
@@ -76,9 +81,25 @@
 			<p class="text-sm font-medium {TONE_CLASS[verdict.tone]}">{verdict.label}</p>
 		{/if}
 
-		{#if (pred && pred.history.length > 1) || proj}
+		{#if selfRow && (rangeLabel(selfRow) || confidenceLabel(selfRow.confidence))}
+			<p class="text-xs text-fg-muted">
+				{rangeLabel(selfRow) ? `80% 범위 ${rangeLabel(selfRow)}` : ''}{rangeLabel(selfRow) && confidenceLabel(selfRow.confidence)
+					? ' · '
+					: ''}{confidenceLabel(selfRow.confidence) ? `신뢰도 ${confidenceLabel(selfRow.confidence)}` : ''} · 15℃ 기준
+			</p>
+		{/if}
+
+		{#if pred?.compare}
+			<PredictionCompare compare={pred.compare} />
+		{/if}
+
+		{#if pred || proj}
 			<details class="group border-t border-border-subtle pt-3">
-				<summary class="cursor-pointer list-none text-xs text-fg-muted hover:text-fg-primary">예측 추이 · 레이스 아침 폼 보기 ▾</summary>
+				<summary class="cursor-pointer list-none text-xs text-fg-muted hover:text-fg-primary">예측 추이 · 근거 · 레이스 아침 폼 보기 ▾</summary>
+				<div class="flex flex-col gap-4 pt-3">
+					<PredictionBasis />
+					<RaceConfirmList />
+				</div>
 				{#if pred && pred.history.length > 1}
 					<div class="flex flex-col gap-1">
 						<span class="text-xs text-fg-muted">예측 기록 추이 · 최근 90일</span>
````

검증:
```
cd frontend && npm run check && node --test tests/predictionCompare.test.mjs tests/raceHub.test.mjs tests/format.test.mjs && npm run build
```
기준: svelte-check **0 errors**(기존 경고 15개는 그대로), node 테스트 전부 통과, build 성공(샌드박스 사본에서 확인).

## P7-PRED-73 — 대회 확인 목록 (프론트, P7-PRED-72와 같은 유닛)

- **UI 노출: 레이스 허브 "예측 추이 · 근거 · 레이스 아침 폼 보기" 펼침 안** — 최근 1년 대회로 보이는 활동마다 [전력][페이스][펀런][DNF] 토글(다시 누르면 해제). 안내 문구: "예측은 '전력'으로 표시한 대회만 기준으로 써요".
- 저장 후 예측 반영 시점: 다음 메트릭 재계산(동기화 또는 `recompute`) — 즉시 재계산은 하지 않는다(열린 질문 O-6).

**`frontend/src/lib/components/RaceConfirmList.svelte`** — 신규, 전문 그대로(73줄)

````svelte
<script lang="ts">
	// 대회 확인(P7-PRED-73): 대회로 보이는 활동에 전력/페이스/펀런/DNF 를 표시 — 예측은 '전력'만 기준으로 쓴다.
	import { onMount } from 'svelte';
	import type { RaceCandidate, RaceEffort } from '$lib/types';
	import { deleteRaceConfirm, getRaceCandidates, putRaceConfirm } from '$lib/api/prediction';
	import { formatDuration } from '$lib/format';

	const EFFORTS: { key: RaceEffort; label: string }[] = [
		{ key: 'allout', label: '전력' },
		{ key: 'paced', label: '페이스' },
		{ key: 'fun', label: '펀런' },
		{ key: 'dnf', label: 'DNF' }
	];

	let items = $state<RaceCandidate[]>([]);
	let loaded = $state(false);
	let busy = $state<number | null>(null);

	onMount(() => {
		getRaceCandidates()
			.then((r) => (items = r))
			.finally(() => (loaded = true));
	});

	async function choose(item: RaceCandidate, effort: RaceEffort) {
		busy = item.activity_id;
		try {
			if (item.confirmed_effort === effort) {
				await deleteRaceConfirm(item.activity_id);
				item.confirmed_effort = null;
			} else {
				await putRaceConfirm(item.activity_id, effort);
				item.confirmed_effort = effort;
			}
		} finally {
			busy = null;
		}
	}
</script>

<div class="flex flex-col gap-2" aria-label="대회 확인">
	<span class="text-xs text-fg-muted">대회 기록 확인 · 예측은 '전력'으로 표시한 대회만 기준으로 써요</span>
	{#if !loaded}
		<p class="text-[11px] text-fg-muted">불러오는 중…</p>
	{:else if items.length === 0}
		<p class="text-[11px] text-fg-muted">최근 1년 대회로 보이는 활동이 없어요</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each items as item (item.activity_id)}
				<li class="flex flex-col gap-1">
					<span class="text-[11px]"
						>{item.date} · {item.name ?? '대회'} · {(item.distance_m / 1000).toFixed(1)}km{item.time_sec != null
							? ` · ${formatDuration(item.time_sec)}`
							: ''}</span
					>
					<div class="flex gap-1">
						{#each EFFORTS as e (e.key)}
							<button
								type="button"
								disabled={busy === item.activity_id}
								aria-pressed={item.confirmed_effort === e.key}
								onclick={() => choose(item, e.key)}
								class="rounded border px-2 py-0.5 text-[11px] {item.confirmed_effort === e.key
									? 'border-fg-primary text-fg-primary'
									: 'border-border-subtle text-fg-muted'}">{e.label}</button
							>
						{/each}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>
````


## P7-PRED-74 — 예측 근거 카드(심박 기준 자체 vs 기기, 두 존 체계, 기온 계수, 훈련 반응) + 새 운동 유형 라벨 (프론트, P7-PRED-72와 같은 유닛)

- **UI 노출: 레이스 허브 펼침 안 "예측 근거"** — 자체 최대/LTHR(출처 문구), 기기 최대/LTHR, LTHR 존(자체)·HRR 존(자체)·LTHR 존(기기), 기온 계수 문장, 역치 이상 훈련 8주 주평균(이전 8주, 롱런 속 MP km). 데이터 없으면 "심박 프로필 데이터 수집 중".
- 운동 유형 라벨: `long_run` 장거리, `steady` 스테디, `repetition` 레피티션, `sprint` 스프린트 추가(P7-PRED-23 새 값).

**`frontend/src/lib/components/PredictionBasis.svelte`** — 신규, 전문 그대로(62줄)

````svelte
<script lang="ts">
	// 예측 근거(P7-PRED-74): 심박 기준(자체 vs 기기)과 두 존 체계, 기온 계수, 훈련 반응. 펼칠 때 한 번만 불러온다.
	import { onMount } from 'svelte';
	import type { PredictionProfile, ZoneBounds } from '$lib/types';
	import { getPredictionProfile } from '$lib/api/prediction';

	let profile = $state<PredictionProfile | null>(null);
	let failed = $state(false);

	onMount(() => {
		getPredictionProfile()
			.then((p) => (profile = p))
			.catch(() => (failed = true));
	});

	function zoneText(z: ZoneBounds | null | undefined): string {
		if (!z) return '—';
		return z.map(([lo, hi], i) => `Z${i + 1} ${Math.round(lo)}–${Math.round(hi)}`).join(' · ');
	}
</script>

<div class="flex flex-col gap-2" aria-label="예측 근거">
	<span class="text-xs text-fg-muted">예측 근거</span>
	{#if failed}
		<p class="text-[11px] text-fg-muted">근거를 불러오지 못했어요</p>
	{:else if !profile}
		<p class="text-[11px] text-fg-muted">불러오는 중…</p>
	{:else}
		{@const hp = profile.hr_profile}
		{#if hp}
			<div class="grid grid-cols-2 gap-2 text-[11px]">
				<div class="flex flex-col">
					<span class="text-fg-muted">자체 추정</span>
					<span class="font-mono">최대 {hp.self.hrmax ?? '—'} · LTHR {Math.round(hp.self.lthr)}</span>
					<span class="text-fg-muted">{hp.self.lthr_source === 'races' ? '최근 대회 심박 기준' : '최대심박의 91.7%'}</span>
				</div>
				<div class="flex flex-col">
					<span class="text-fg-muted">기기 제공{hp.ref ? ` (${hp.ref.source})` : ''}</span>
					<span class="font-mono">{hp.ref ? `최대 ${hp.ref.hrmax ?? '—'} · LTHR ${hp.ref.lthr ?? '—'}` : '없음'}</span>
				</div>
			</div>
			<p class="text-[11px] text-fg-muted">LTHR 존(자체) · {zoneText(hp.zones.self.lthr)}</p>
			<p class="text-[11px] text-fg-muted">HRR 존(자체) · {zoneText(hp.zones.self.hrr)}</p>
			{#if hp.zones.ref}
				<p class="text-[11px] text-fg-muted">LTHR 존(기기) · {zoneText(hp.zones.ref.lthr)}</p>
			{/if}
		{:else}
			<p class="text-[11px] text-fg-muted">심박 프로필 데이터 수집 중</p>
		{/if}
		{#if profile.heat_model}
			<p class="text-[11px] text-fg-muted">
				기온 영향 · 15℃보다 1℃ 더우면 {Math.abs(profile.heat_model.heat).toFixed(2)}%, 5℃보다 1℃ 추우면 {Math.abs(profile.heat_model.cold).toFixed(2)}% 느려짐
			</p>
		{/if}
		{#if profile.training_response}
			{@const tr = profile.training_response}
			<p class="text-[11px] text-fg-muted">
				품질 세트 · 최근 8주 주평균 {tr.quality_min_avg_8w}분 · 주 {tr.quality_sessions_avg_8w}회{tr.quality_min_avg_prev_8w != null ? ` (이전 8주 ${tr.quality_min_avg_prev_8w}분)` : ''}{tr.long_mp_km_8w != null ? ` · 롱런 속 마라톤 페이스 ${tr.long_mp_km_8w}km` : ''}
			</p>
		{/if}
	{/if}
</div>
````

**`frontend/src/lib/format.ts`** — 수정, 아래 diff 그대로

````diff
--- a/frontend/src/lib/format.ts
+++ b/frontend/src/lib/format.ts
@@ -74,8 +74,12 @@
 	recovery: '회복',
 	easy: '쉬운 달리기',
 	long: '장거리',
+	long_run: '장거리',
+	steady: '스테디',
 	tempo: '템포',
 	interval: '인터벌',
+	repetition: '레피티션',
+	sprint: '스프린트',
 	race: '레이스'
 };
 
````


