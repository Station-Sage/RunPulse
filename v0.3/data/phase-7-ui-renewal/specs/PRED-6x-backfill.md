# PRED-6x — 실DB 백필, 수용 검증, 예측 스냅샷 (예측 리뉴얼 r4)

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-61 — 실DB 백필 런북 (**사람 실행, mode manual** — autopilot 금지)

전제: P7-PRED-11~53이 main(또는 운영 브랜치)에 병합됨. 모든 단계는 사용자 계정 DB 하나에 대해 순서대로. 각 단계의 "기대"는 2026-09-25 사본 DB로 샌드박스에서 실제로 돌린 결과다(±는 이후 새 활동만큼).

| 단계 | 명령 | API 호출 | 기대 |
|---|---|---|---|
| 0 백업 | `python3 -c "import sqlite3;s=sqlite3.connect('data/users/<id>/running.db');d=sqlite3.connect('data/users/<id>/running.db.bak-pred');s.backup(d)"` | 없음 | 백업 파일 생성 |
| 1 스키마 | 앱 1회 기동 또는 `python3 -c "import sqlite3;from src.db_setup import create_tables;c=sqlite3.connect('<db>');create_tables(c);c.commit()"` | 없음 | `PRAGMA user_version` = 20, `race_results` 테이블, `uq_session_outcomes_planned` 인덱스 |
| 2 랩·스트림 재추출 | `python3 -m src.sync.reextract --db <db> --dry-run` → 숫자 확인 후 `--dry-run` 없이 | 없음(source_payloads) | activities 586, laps 3,360, missing_payload 0, errors 0. 이후 `SELECT count(gap_speed_ms) FROM activity_laps WHERE source='garmin'` ≈ 2,786, 스트림 `max(elapsed_sec)` 수천 초 |
| 3 외기 기상 백필 | `python3 -m src.weather.activity_weather --db <db> --since 2023-01-01 --max 2000` | Open-Meteo 약 300~600회(좌표·날짜 캐시) | 2025-04 이후 러닝 약 290개 open_meteo, 나머지는 기기 온도 보정 또는 없음. 실패분은 재실행 시 재시도 |
| 4 Garmin 참조 이력(재계산 전에 — 경로 (b)가 과거 LTHR을 쓰도록) | `python3 -c "..."` 로 로그인된 Garmin 클라이언트를 만들어 `from src.sync.garmin_ref_sync import backfill_history; backfill_history(conn, client, '2025-01-01', '<오늘>')` (클라이언트는 `src/sync/garmin_auth.py`의 `_login(config)`로 생성) | Garmin 2회 | `race_parsed`·`lt_parsed` > 0 이면 성공. **0이면 응답 형태가 가정과 다르다** → `source_payloads`의 `*_range` 원문을 확인하고 P7-PRED-25 파서를 보완(열린 질문 O-3) |
| 4b 재계산 전 예측 스냅샷 | `python3 -c "import sqlite3,json;c=sqlite3.connect('<db>');json.dump(c.execute(\"SELECT scope_id,metric_name,provider,numeric_value FROM metric_store WHERE scope_type='daily' AND (metric_name LIKE 'race_pred%' OR metric_name IN ('marathon_shape','ctl','training_response'))\").fetchall(),open('pred_before.json','w'))"` 그리고 `python3 scripts/pred_backtest.py --db <db>.bak-pred`(0단계 백업 대상, 메모리 사본) 출력 보관 | 없음 | 재계산 전 표시값·백테스트 기준선 |
| 5 메트릭 재계산 | `RUNPULSE_DB=<db> python3 -m src.metrics.cli recompute --days 1100` (**`RUNPULSE_DB`를 꼭 지정** — 기본값은 작업 폴더의 `runpulse.db`) (**`recompute-all` 쓰지 말 것** — runpulse 메트릭을 전부 지우고 90일만 다시 계산한다) | 없음 | 400일 기준 약 160초. `race_pred_vdot`·`hr_profile`·`heat_model`·`training_response` 일별 행 생성, `marathon_shape`·`rri`·`vdot_adj`·`sapi`가 0행 → 수백 행 |
| 5b 재계산 전후 예측 비교 | 4b와 같은 명령으로 `pred_after.json` 저장 → 두 파일을 (scope_id, metric_name, provider)로 맞춰 거리별 중앙 \|Δ\|·최대 \|Δ\|와 최근 기준일 값 비교. 수용 백테스트를 재계산 DB에서 다시 실행해 4b 기준선과 나란히 기록 | 없음 | 예측 계산기 입력(랩·요약·대회 확인·외기, 그날 다시 계산하는 hr_profile·heat_model)은 재계산으로 바뀌지 않으므로 **백테스트 수치는 같아야 한다**(사본 검증 2026-09-26: 재계산 전후 D-0 1.40/D-28 1.49 동일). 저장된 표시값은 코드 버전 차이로 바뀐다(사본: 10K 중앙 \|Δ\| 26초, 마라톤 130초). 백테스트가 달라지면 입력 경로가 저장 메트릭에 의존하게 된 것이므로 중단하고 원인 확인 |
| 6 매칭 소급 | 계획이 있는 주마다 `match_week_activities(conn, <월요일>)` 또는 앱의 기존 재매칭 경로 | 없음 | `session_outcomes` 행 생성(현재 0) |
| 7 수용 백테스트 | `python3 scripts/pred_backtest.py --db <db>` | 없음(읽기 전용, 메모리 사본) | D-0 MAE ≈ 1.3%, 최대 ≈ 3.0%, n=8 → `PASS`. FAIL 이면 병합 되돌림 검토 |
| 8 확인 | Today 레이스 허브: 예측 ± 범위·신뢰도·3경로 비교 표시(P7-PRED-72 이후) | – | (c) 10K ≈ 45:40, 하프 ≈ 1:41, 풀 ≈ 3:40 (15℃) |

되돌리기: 1~4·6은 백업 복원으로 완전 복구된다. 2는 활동 id를 바꾸지 않으므로 참조 테이블 손상이 없다.

## P7-PRED-62 — 수용 백테스트 스크립트 (r3 기본·r4 섀도 2종 나란히)

- 의존: P7-PRED-22, P7-PRED-24, P7-PRED-33, P7-PRED-51 · UI 노출: 없음 · 실DB: **읽기 전용**(`mode=ro`로 열어 메모리에 복제, 원본 무변경)
- 파일: `scripts/pred_backtest.py`(신규), `tests/test_pred_backtest.py`(신규)
- 대상 대회: `race_results.effort`가 있으면 allout만, 없으면 `effort.auto_effort`(거리·지속시간별 심박 기대 범위, REVIEW-09 §10).
- 방법: 대회마다 D-0·D-28 시점의 hr_profile·heat_model·예측을 그 시점 이전 데이터로 다시 계산한다. 대회 당일 외기로 환원해 실제 기록과 비교한다. `--out`은 결과를 JSON(`mode: retro`)으로 남긴다. **in-sample 회고라서 전향 평가(P7-PRED-63)와 섞지 않는다.**
- 합격 기준(기본 r3 기준): D-0 MAE ≤ 2.5%, 최대 ≤ 4.5%, 전력 대회 n ≥ 5.
- 사본 결과(effort 입력 없음): n=7, r3 D-0 1.39 / 최대 3.0 / D-28 2.16, r4 1.39 / 3.0 / 1.79, r4 asym 1.26 / 3.6 / 1.46 → PASS.

**`scripts/pred_backtest.py`** — 신규, 전문 그대로(102줄)

````python
"""예측 v2 수용 백테스트(P7-PRED-62) — 실DB 를 읽기 전용으로 열어 메모리에 복제한 뒤, 전력 대회마다 D-0/D-28 시점
calculator(hr_profile·heat_model·darp)를 돌려 대회 당일 외기 기온으로 환원한 예측과 실제 기록을 비교한다.
기본 r3(`darp`, runpulse:formula_v1)와 r4 섀도 두 변형(`darp_r4`)을 같은 대회·시점으로 나란히 낸다.
결과는 in-sample 회고(retro)다 — 전향 평가(P7-PRED-63 스냅샷)와 섞지 않는다.

사용: python3 scripts/pred_backtest.py --db data/users/<id>/running.db [--since 2025-04-01] [--out retro.json]
합격(기본 r3 기준): D-0 MAE ≤ 2.5% 이고 최대 ≤ 4.5% (대회 n ≥ 5). 실DB 에는 아무것도 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_setup import create_tables  # noqa: E402
from src.metrics.base import CalcContext  # noqa: E402
from src.metrics.darp import DARPCalculator  # noqa: E402
from src.metrics.darp_r4 import DARPShadowAsymCalculator, DARPShadowCalculator  # noqa: E402
from src.metrics.heat_model import HeatModelCalculator  # noqa: E402
from src.metrics.hr_profile import HRProfileCalculator  # noqa: E402
from src.metrics.prediction.core import temp_factor  # noqa: E402
from src.metrics.prediction.effort import auto_effort  # noqa: E402
from src.utils.db_helpers import upsert_metric  # noqa: E402

NAME = {5000.0: "race_pred_5k_sec", 10000.0: "race_pred_10k_sec", 21097.5: "race_pred_half_sec"}
MAX_MAE, MAX_ABS, MIN_N = 2.5, 4.5, 5
MODELS = {"r3": DARPCalculator, "r4": DARPShadowCalculator, "r4_asym": DARPShadowAsymCalculator}


def _run(conn, calc, day):
    res = calc.compute(CalcContext(conn=conn, scope_type="daily", scope_id=day))
    for r in res:
        upsert_metric(conn, "daily", day, r.metric_name, calc.provider, numeric_value=r.numeric_value,
                      json_value=json.loads(r.json_value) if r.json_value else None)
    return {r.metric_name: r for r in res}


def backtest(conn: sqlite3.Connection, since: str, today: str, calc_cls=DARPCalculator) -> dict:
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today)
    prof = _run(conn, HRProfileCalculator(), today)
    prof_self = json.loads(prof["hr_profile"].json_value)["self"] if prof else {}
    hmax = prof_self.get("hrmax")
    confirmed = ctx.get_race_results()          # 사용자 확인 effort 가 HR 임계보다 우선(allout 만 평가 대상)
    allruns = ctx.get_runs((date.fromisoformat(today) - date.fromisoformat(since)).days + 365)
    races = [r for r in allruns if r["date"] >= since
             and r["is_race"] and r["nominal_m"] in NAME and (
                 confirmed[r["id"]]["effort"] == "allout" if r["id"] in confirmed
                 else auto_effort(r, allruns, hmax) == "allout")]
    out = {}
    for hd in (0, 28):
        errs = []
        for r in races:
            d = (date.fromisoformat(r["date"]) - timedelta(days=hd)).isoformat()
            _run(conn, HRProfileCalculator(), d)
            hm = json.loads(_run(conn, HeatModelCalculator(), d)["heat_model"].json_value)
            p = _run(conn, calc_cls(), d)
            if NAME[r["nominal_m"]] not in p:
                continue
            t = ctx.get_activity_metric(r["id"], "weather_temp_c")
            pred = p[NAME[r["nominal_m"]]].numeric_value / temp_factor(t, hm["heat"], hm["cold"])
            errs.append(round((pred / r["perf_time_s"] - 1) * 100, 1))
        out[f"D-{hd}"] = {"n": len(errs), "mae": round(mean(abs(e) for e in errs), 2) if errs else None,
                          "max": max((abs(e) for e in errs), default=None), "errors": errs,
                          "bias": round(mean(errs), 2) if errs else None}
    return out


def backtest_all(conn: sqlite3.Connection, since: str, today: str) -> dict:
    """모델별 결과 {"r3": {...}, "r4": {...}, "r4_asym": {...}} — 같은 메모리 사본을 순서대로 쓴다."""
    return {k: backtest(conn, since, today, cls) for k, cls in MODELS.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--since", default="2025-04-01")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--out", default=None, help="결과 JSON 저장 경로(선택)")
    a = ap.parse_args()
    src = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    src.backup(mem)
    src.close()
    create_tables(mem)          # 메모리 사본에만 v20 컬럼 보장(실DB 무변경)
    allres = backtest_all(mem, a.since, a.today)
    print(json.dumps(allres, ensure_ascii=False, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps({"mode": "retro", "today": a.today, **allres}, ensure_ascii=False, indent=1))
    d0 = allres["r3"]["D-0"]
    ok = d0["n"] >= MIN_N and d0["mae"] is not None and d0["mae"] <= MAX_MAE and d0["max"] <= MAX_ABS
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
````

**`tests/test_pred_backtest.py`** — 신규, 전문 그대로(19줄)

````python
"""P7-PRED-62: 수용 백테스트 스크립트 — 대회 없음이면 n=0."""
import importlib.util
from pathlib import Path

from tests.helpers_pred import mem_conn, seed_run

_spec = importlib.util.spec_from_file_location("pred_backtest", Path(__file__).parent.parent / "scripts" / "pred_backtest.py")
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)


def test_no_races():
    c = mem_conn()
    seed_run(c, sid="a", date="2026-09-01", max_hr=190)
    seed_run(c, sid="b", date="2026-09-02", max_hr=192)
    r = pb.backtest(c, "2026-01-01", "2026-09-26")
    assert r["D-0"] == {"n": 0, "mae": None, "max": None, "errors": [], "bias": None}
    allr = pb.backtest_all(c, "2026-01-01", "2026-09-26")
    assert set(allr) == {"r3", "r4", "r4_asym"} and all(v["D-28"]["n"] == 0 for v in allr.values())
````

검증:
```
python3 -m pytest tests/test_pred_backtest.py -q
python3 scripts/check_docs.py
```

## P7-PRED-63 — 예측 스냅샷(`prediction_snapshots`, 스키마 v21) + 대회 전향 평가 — **사용자 승인(2026-09-26)**

- 의존: P7-PRED-11, P7-PRED-51, P7-PRED-53 · UI 노출: 없음(데이터). 평가 요약 화면은 후속 · 실DB: 앱 기동 시 테이블 생성(멱등). 이후 동기화마다 오늘 스냅샷 기록.
- 파일: `src/db_schema_v21.py`(신규), `src/db_setup.py`, `src/services/prediction_snapshot_service.py`(신규), `src/services/race_result_service.py`, `src/web/bg_sync.py`, `tests/test_prediction_snapshot.py`(신규), `tests/test_db_setup.py`, `tests/test_phase1_schema.py`
- 왜(REVIEW-07 §R4-8(4)): r4는 후보다. 기본(r3)·기기(b)·섀도(r4 2종)·Garmin 예측을 **그날 값 그대로** 보존해야 대회 뒤 전향 비교가 가능하다. metric_store는 재계산 때 덮어쓰이므로 스냅샷이 따로 필요하다.
- 규칙:
  - live 스냅샷: 동기화 직후(`bg_sync`) **오늘** 예측만 쓴다. 과거 날짜 재계산값은 전향이 아니라서 쓰지 않는다. 값이 같으면 7일마다 1행이다. Garmin 값은 14일 이내 최신값만 쓴다.
  - 전향 평가: 대회 확인(`race_result_service.confirm`, effort=allout)에서 거리가 같은 live 스냅샷을 horizon 0·7·28일(허용 7일)마다 provider별 1행씩 고른다. 그 행에 실제 기록, 잔차(예측/실제−1, %), 대회일 공변량(수면·HRV·BB·RHR·전날 TSB·외기)을 채운다.
  - 요약: `summary()`는 provider·horizon별 n·MAE·편향·80% 적중을 낸다.
  - retro(회고): P7-PRED-62 JSON 출력. 이 테이블의 mode='retro'는 예약만 하고 쓰지 않는다.
  - 판정 규칙(제안): 전향 대회 ≥4건에서 r4 MAE < r3이고 80% 적중 ≥60%면 전환을 **제안**한다. 결정은 사용자가 한다.

**`src/db_schema_v21.py`** — 신규, 전문 그대로(37줄)

````python
"""스키마 v21 — 예측 스냅샷(P7-PRED-63): 모델별 예측을 그날 값 그대로 보존해 대회 후 전향 평가한다.

mode 'live' = 동기화 직후 그날 예측(전향), 'retro' = 과거 시점 재계산(회고, in-sample). 평가·요약은 live 만 쓴다.
"""
from __future__ import annotations

import sqlite3

DDL_PREDICTION_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS prediction_snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT DEFAULT (datetime('now')),
    as_of            TEXT NOT NULL,
    mode             TEXT NOT NULL DEFAULT 'live' CHECK(mode IN ('live', 'retro')),
    provider         TEXT NOT NULL,
    variant          TEXT,
    model_version    TEXT,
    distance_m       REAL NOT NULL,
    pred_s           REAL NOT NULL,
    low_s            REAL,
    high_s           REAL,
    confidence       REAL,
    inputs_json      TEXT,
    race_activity_id INTEGER,
    horizon_days     INTEGER,
    actual_s         REAL,
    residual_pct     REAL,
    covariates_json  TEXT,
    UNIQUE(as_of, mode, provider, distance_m)
);
CREATE INDEX IF NOT EXISTS idx_pred_snap_dist_asof ON prediction_snapshots(distance_m, as_of);
"""


def ensure_v21(conn: sqlite3.Connection) -> None:
    """v21 테이블을 멱등적으로 보장한다."""
    conn.executescript(DDL_PREDICTION_SNAPSHOTS)
````

**`src/db_setup.py`** — 수정, 아래 diff 그대로 — v21 보장 호출

````diff
--- a/src/db_setup.py
+++ b/src/db_setup.py
@@ -29,7 +29,7 @@
 
 _PROJECT_ROOT = Path(__file__).resolve().parent.parent
 DEFAULT_USER = "default"
-SCHEMA_VERSION = 20  # v0.3.10: 예측 리뉴얼 컬럼·race_results (db_schema_v20)
+SCHEMA_VERSION = 21  # v0.3.11: 예측 스냅샷 (db_schema_v21) — v20: 예측 리뉴얼 컬럼·race_results
 
 
 # ─────────────────────────────────────────────────────────────────────────────
@@ -716,6 +716,9 @@
     # v20: 예측 리뉴얼 컬럼·race_results (멱등)
     from src.db_schema_v20 import ensure_v20
     ensure_v20(conn)
+    # v21: 예측 스냅샷(P7-PRED-63)
+    from src.db_schema_v21 import ensure_v21
+    ensure_v21(conn)
 
     conn.commit()
 
````

**`src/services/prediction_snapshot_service.py`** — 신규, 전문 그대로(115줄)

````python
"""예측 스냅샷·전향 평가(P7-PRED-63) — 모델별(r3 기본·기기·r4 섀도·Garmin) 예측을 그날 값 그대로 보존하고,
대회 확인 시 대회 전 예측(D-0·D-7·D-28)과 실제 기록을 비교해 채운다. 기본 표시 전환 판단의 근거(REVIEW-07 §R4-8(4)).

live 스냅샷은 동기화 직후 '오늘' 예측만 쓴다(과거 날짜 재계산값은 전향이 아니다). 재계산이 metric_store 를 덮어도
스냅샷은 바뀌지 않는다. 값이 그대로면 7일마다 1행만 쓴다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

PROVIDERS = ("runpulse:formula_v1", "runpulse:ref_garmin", "runpulse:shadow_r4", "runpulse:shadow_r4_asym", "garmin")
DISTANCES = {"race_pred_5k_sec": 5000.0, "race_pred_10k_sec": 10000.0, "race_pred_half_sec": 21097.5,
             "race_pred_marathon_sec": 42195.0}
HORIZONS = (0, 7, 28)        # 대회일 기준 며칠 전 예측을 평가하나
TOLERANCE_DAYS = 7           # 그 시점 스냅샷이 없으면 이만큼 더 이전까지 허용(주 1회 기록)
REPEAT_DAYS = 7              # 값이 같으면 이 간격으로만 다시 기록
GARMIN_STALE_DAYS = 14       # Garmin 예측은 동기화가 드물다 — 이보다 오래된 값은 스냅샷하지 않음


def _latest(conn, metric: str, provider: str, day: str, max_age: int | None):
    row = conn.execute(
        "SELECT scope_id, numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
        "AND provider=? AND scope_id<=? ORDER BY scope_id DESC LIMIT 1", (metric, provider, day)).fetchone()
    if not row or row[1] is None:
        return None
    if max_age is not None and (date.fromisoformat(day) - date.fromisoformat(row[0][:10])).days > max_age:
        return None
    return row


def record_snapshots(conn: sqlite3.Connection, day: str, mode: str = "live") -> int:
    """day 의 모델별·거리별 예측을 스냅샷한다. 쓴 행 수 반환. runpulse 경로는 그날 값만, Garmin 은 14일 이내 최신값."""
    n = 0
    for provider in PROVIDERS:
        for metric, dist in DISTANCES.items():
            row = _latest(conn, metric, provider, day, GARMIN_STALE_DAYS if provider == "garmin" else 0)
            if row is None:
                continue
            js = json.loads(row[2]) if row[2] else {}
            last = conn.execute(
                "SELECT as_of, pred_s FROM prediction_snapshots WHERE mode=? AND provider=? AND distance_m=? "
                "ORDER BY as_of DESC LIMIT 1", (mode, provider, dist)).fetchone()
            if last and round(last[1]) == round(row[1]) and \
                    (date.fromisoformat(day) - date.fromisoformat(last[0])).days < REPEAT_DAYS:
                continue
            inputs = {k: js[k] for k in ("contributions", "signals_s", "reasons", "tanda_s", "daniels_s") if k in js}
            cur = conn.execute(
                "INSERT OR IGNORE INTO prediction_snapshots (as_of, mode, provider, variant, model_version, distance_m, "
                "pred_s, low_s, high_s, confidence, inputs_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (day, mode, provider, js.get("variant") or js.get("path"), js.get("model_version"), dist, row[1],
                 js.get("low_s"), js.get("high_s"), js.get("confidence"), json.dumps(inputs, ensure_ascii=False)))
            n += cur.rowcount
    conn.commit()
    return n


def _covariates(conn, race_date: str, activity_id: int) -> dict:
    w = conn.execute("SELECT sleep_score, hrv_last_night, body_battery_high, resting_hr FROM daily_wellness "
                     "WHERE date=?", (race_date,)).fetchone()
    prev = (date.fromisoformat(race_date) - timedelta(days=1)).isoformat()
    tsb = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name='tsb' "
                       "AND provider='runpulse:formula_v1' AND scope_id=?", (prev,)).fetchone()
    t = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='activity' AND scope_id=? "
                     "AND metric_name='weather_temp_c' AND is_primary=1", (str(activity_id),)).fetchone()
    keys = ("sleep_score", "hrv_last_night", "body_battery_high", "resting_hr")
    out = dict(zip(keys, w)) if w else {}
    out.update(tsb_prev=tsb[0] if tsb else None, temp_c=t[0] if t else None)
    return out


def evaluate_race(conn: sqlite3.Connection, activity_id: int) -> int:
    """확인된 대회(race_results)에 대해 거리가 같은 live 스냅샷을 horizon 별로 1행씩 골라 실제 기록·잔차·공변량을 채운다.
    잔차 = 예측/실제 − 1 (%, 양수 = 실제가 더 빠름). 반환: 채운 행 수. 전력(allout)이 아니면 평가하지 않는다."""
    row = conn.execute(
        "SELECT substr(a.start_time,1,10), r.distance_m, COALESCE(r.official_time_sec, a.elapsed_time_sec, "
        "a.moving_time_sec), r.effort FROM race_results r JOIN activity_summaries a ON a.id=r.activity_id "
        "WHERE r.activity_id=?", (activity_id,)).fetchone()
    if not row or row[3] != "allout" or not row[2]:
        return 0
    race_date, dist_m, actual, _ = row
    dist = min(DISTANCES.values(), key=lambda d: abs(d - dist_m))
    if abs(dist - dist_m) / dist > 0.03:
        return 0
    cov = json.dumps(_covariates(conn, race_date, activity_id), ensure_ascii=False)
    n = 0
    for provider in PROVIDERS:
        for h in HORIZONS:
            hi = (date.fromisoformat(race_date) - timedelta(days=h)).isoformat()
            lo = (date.fromisoformat(race_date) - timedelta(days=h + TOLERANCE_DAYS)).isoformat()
            snap = conn.execute(
                "SELECT id, pred_s FROM prediction_snapshots WHERE mode='live' AND provider=? AND distance_m=? "
                "AND as_of<=? AND as_of>=? AND race_activity_id IS NULL ORDER BY as_of DESC LIMIT 1",
                (provider, dist, hi, lo)).fetchone()
            if not snap:
                continue
            conn.execute("UPDATE prediction_snapshots SET race_activity_id=?, horizon_days=?, actual_s=?, "
                         "residual_pct=?, covariates_json=? WHERE id=?",
                         (activity_id, h, actual, round((snap[1] / actual - 1) * 100, 2), cov, snap[0]))
            n += 1
    conn.commit()
    return n


def summary(conn: sqlite3.Connection) -> list[dict]:
    """provider·horizon 별 전향 평가 요약: n, MAE%, 편향%, 80% 범위 적중 수."""
    rows = conn.execute(
        "SELECT provider, horizon_days, count(*), avg(abs(residual_pct)), avg(residual_pct), "
        "sum(CASE WHEN low_s <= actual_s AND actual_s <= high_s THEN 1 ELSE 0 END), "
        "sum(CASE WHEN low_s IS NOT NULL THEN 1 ELSE 0 END) FROM prediction_snapshots "
        "WHERE mode='live' AND actual_s IS NOT NULL GROUP BY provider, horizon_days ORDER BY provider, horizon_days"
    ).fetchall()
    return [{"provider": p, "horizon_days": h, "n": n, "mae_pct": round(m, 2), "bias_pct": round(b, 2),
             "hit80": hit, "n_range": nr} for p, h, n, m, b, hit, nr in rows]
````

**`src/services/race_result_service.py`** — 수정, 아래 diff 그대로 — 확인 직후 전향 평가

````diff
--- a/src/services/race_result_service.py
+++ b/src/services/race_result_service.py
@@ -30,6 +30,8 @@
         "note=excluded.note, confirmed_at=excluded.confirmed_at",
         (activity_id, race_name, distance_m, official_time_sec, effort, note))
     conn.commit()
+    from src.services.prediction_snapshot_service import evaluate_race   # 대회 전 스냅샷 전향 평가(P7-PRED-63)
+    evaluate_race(conn, activity_id)
     return get(conn, activity_id)
 
 
````

**`src/web/bg_sync.py`** — 수정, 아래 diff 그대로 — 동기화 후 오늘 스냅샷(실패해도 계속)

````diff
--- a/src/web/bg_sync.py
+++ b/src/web/bg_sync.py
@@ -201,6 +201,12 @@
                 # 오늘 날짜를 항상 포함하여 메트릭 계산
                 end = max(job.to_date, _date.today().isoformat())
                 metrics_engine.run_for_date_range(conn, job.from_date, end)
+                # 오늘 예측 스냅샷(전향 평가용, P7-PRED-63) — 실패해도 동기화는 계속
+                try:
+                    from src.services.prediction_snapshot_service import record_snapshots
+                    record_snapshots(conn, _date.today().isoformat())
+                except Exception as snap_exc:  # noqa: BLE001
+                    update_job(self.job_id, last_error=f"예측 스냅샷 실패: {str(snap_exc)[:150]}")
                 # 스키마 마이그레이션 후 재동기화 플래그 해제
                 from src.db_setup import clear_needs_resync
                 clear_needs_resync(conn)
````

**`tests/test_prediction_snapshot.py`** — 신규, 전문 그대로(64줄)

````python
"""P7-PRED-63: 예측 스냅샷 기록·중복 억제·대회 전향 평가·요약."""
import json

from src.services import prediction_snapshot_service as ps
from src.services.race_result_service import confirm
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_run


def _pred(c, day, provider, sec, variant=None):
    js = {"low_s": sec - 60, "high_s": sec + 60, "confidence": 0.8, "contributions": {"race": 1.0}}
    if variant:
        js["variant"] = variant
    upsert_metric(c, "daily", day, "race_pred_10k_sec", provider, numeric_value=sec, json_value=js)


def test_record_only_today_and_dedupe():
    c = mem_conn()
    _pred(c, "2026-09-20", "runpulse:formula_v1", 2700)
    assert ps.record_snapshots(c, "2026-09-21") == 0          # 그날 값 없음(과거 값 재사용 안 함)
    _pred(c, "2026-09-21", "runpulse:formula_v1", 2700)
    _pred(c, "2026-09-21", "runpulse:shadow_r4", 2760, "base")
    assert ps.record_snapshots(c, "2026-09-21") == 2
    _pred(c, "2026-09-22", "runpulse:formula_v1", 2700)
    assert ps.record_snapshots(c, "2026-09-22") == 0          # 값 같고 7일 안 → 생략
    _pred(c, "2026-09-23", "runpulse:formula_v1", 2690)
    assert ps.record_snapshots(c, "2026-09-23") == 1
    row = c.execute("SELECT variant, low_s, inputs_json FROM prediction_snapshots WHERE provider='runpulse:shadow_r4'").fetchone()
    assert row[0] == "base" and row[1] == 2700 and json.loads(row[2])["contributions"] == {"race": 1.0}


def test_garmin_uses_recent_value_only():
    c = mem_conn()
    _pred(c, "2026-09-01", "garmin", 2600)
    assert ps.record_snapshots(c, "2026-09-10") == 1
    c2 = mem_conn()
    _pred(c2, "2026-08-01", "garmin", 2600)
    assert ps.record_snapshots(c2, "2026-09-10") == 0          # 14일 넘은 Garmin 값은 스냅샷하지 않음


def test_evaluate_on_confirm():
    c = mem_conn()
    for d, sec in (("2026-08-29", 2760), ("2026-09-20", 2730), ("2026-09-27", 2720)):
        _pred(c, d, "runpulse:formula_v1", sec)
        ps.record_snapshots(c, d)
    c.execute("INSERT INTO daily_wellness (date, sleep_score, hrv_last_night) VALUES ('2026-09-27', 70, 60)")
    rid = seed_run(c, sid="r", date="2026-09-27", name="가을 10K 대회", dist=10000.0, moving=2700, elapsed=2705)
    confirm(c, rid, "allout", official_time_sec=2700)
    rows = c.execute("SELECT horizon_days, pred_s, actual_s, residual_pct, covariates_json FROM prediction_snapshots "
                     "WHERE race_activity_id=? ORDER BY horizon_days", (rid,)).fetchall()
    assert [r[0] for r in rows] == [0, 7, 28] and [r[1] for r in rows] == [2720, 2730, 2760]
    assert rows[0][2] == 2700 and abs(rows[0][3] - (2720 / 2700 - 1) * 100) < 0.01
    assert json.loads(rows[0][4])["sleep_score"] == 70
    s = ps.summary(c)
    assert [x["horizon_days"] for x in s] == [0, 7, 28] and s[0]["hit80"] == 1 and s[0]["n"] == 1


def test_not_allout_not_evaluated():
    c = mem_conn()
    _pred(c, "2026-09-27", "runpulse:formula_v1", 2720)
    ps.record_snapshots(c, "2026-09-27")
    rid = seed_run(c, sid="r", date="2026-09-27", name="펀런 10K 대회", dist=10000.0, moving=3000)
    confirm(c, rid, "fun")
    assert c.execute("SELECT count(*) FROM prediction_snapshots WHERE actual_s IS NOT NULL").fetchone()[0] == 0
````

**`tests/test_db_setup.py`** — 수정, 아래 diff 그대로 — user_version 21

````diff
--- a/tests/test_db_setup.py
+++ b/tests/test_db_setup.py
@@ -90,7 +90,7 @@
         """v20: 예측 리뉴얼 컬럼·race_results (db_schema_v20)"""
         ver = self.conn.execute("PRAGMA user_version").fetchone()[0]
         assert ver == SCHEMA_VERSION
-        assert ver == 20
+        assert ver == 21
 
     def test_pipeline_tables_count(self):
         """조건 3: pipeline 테이블 (daily_fitness 제거됨, ADR-005)"""
@@ -160,7 +160,7 @@
 
     cols_after = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
     assert "evidence_json" in cols_after
-    assert conn.execute("PRAGMA user_version").fetchone()[0] == 20
+    assert conn.execute("PRAGMA user_version").fetchone()[0] == 21
     conn.close()
 
 
````

**`tests/test_phase1_schema.py`** — 수정, 아래 diff 그대로 — 스키마 버전 21

````diff
--- a/tests/test_phase1_schema.py
+++ b/tests/test_phase1_schema.py
@@ -96,7 +96,7 @@
     def test_schema_version(self, db_conn):
         ver = _get_user_version(db_conn)
         assert ver == SCHEMA_VERSION
-        assert ver == 20  # v0.3.10: 예측 v2 (laps GAP·race_results 등, P7-PRED-11)
+        assert ver == 21  # v0.3.11: 예측 스냅샷(P7-PRED-63) — v20: laps GAP·race_results 등(P7-PRED-11)
 
     def test_activity_summaries_column_count(self, db_conn):
         cols = db_conn.execute("PRAGMA table_info(activity_summaries)").fetchall()
````

검증:
```
python3 -m pytest tests/test_prediction_snapshot.py tests/test_db_setup.py tests/test_phase1_schema.py tests/test_race_result_service.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```

