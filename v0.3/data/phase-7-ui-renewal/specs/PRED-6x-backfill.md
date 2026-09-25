# PRED-6x — 실DB 백필과 수용 검증 (예측 리뉴얼 r3)

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
| 5 메트릭 재계산 | `RUNPULSE_DB=<db> python3 -m src.metrics.cli recompute --days 1100` (**`RUNPULSE_DB`를 꼭 지정** — 기본값은 작업 폴더의 `runpulse.db`) (**`recompute-all` 쓰지 말 것** — runpulse 메트릭을 전부 지우고 90일만 다시 계산한다) | 없음 | 400일 기준 약 160초. `race_pred_vdot`·`hr_profile`·`heat_model`·`training_response` 일별 행 생성, `marathon_shape`·`rri`·`vdot_adj`·`sapi`가 0행 → 수백 행 |
| 6 매칭 소급 | 계획이 있는 주마다 `match_week_activities(conn, <월요일>)` 또는 앱의 기존 재매칭 경로 | 없음 | `session_outcomes` 행 생성(현재 0) |
| 7 수용 백테스트 | `python3 scripts/pred_backtest.py --db <db>` | 없음(읽기 전용, 메모리 사본) | D-0 MAE ≈ 1.3%, 최대 ≈ 3.0%, n=8 → `PASS`. FAIL 이면 병합 되돌림 검토 |
| 8 확인 | Today 레이스 허브: 예측 ± 범위·신뢰도·3경로 비교 표시(P7-PRED-72 이후) | – | (c) 10K ≈ 45:40, 하프 ≈ 1:41, 풀 ≈ 3:40 (15℃) |

되돌리기: 1~4·6은 백업 복원으로 완전 복구된다. 2는 활동 id를 바꾸지 않으므로 참조 테이블 손상이 없다.

## P7-PRED-62 — 수용 백테스트 스크립트

- 의존: P7-PRED-24, P7-PRED-33, P7-PRED-51 · UI 노출: 없음 · 실DB: **읽기 전용**(`mode=ro`로 열어 메모리에 복제, 원본 무변경)
- 파일: `scripts/pred_backtest.py`(신규), `tests/test_pred_backtest.py`(신규)
- 합격 기준: D-0 MAE ≤ 2.5%, 최대 ≤ 4.5%, 전력 대회 n ≥ 5. 사본 DB 결과: D-0 n=8 MAE 1.26% 최대 3.0%, D-28 MAE 2.11% 최대 3.9% → PASS.

**`scripts/pred_backtest.py`** — 신규, 전문 그대로(83줄)

````python
"""예측 v2 수용 백테스트(P7-PRED-62) — 실DB 를 읽기 전용으로 열어 메모리에 복제한 뒤, 전력 대회마다 D-0/D-28 시점
calculator(hr_profile·heat_model·darp)를 돌려 대회 당일 외기 기온으로 환원한 예측과 실제 기록을 비교한다.

사용: python3 scripts/pred_backtest.py --db data/users/<id>/running.db [--since 2025-04-01]
합격: D-0 MAE ≤ 2.5% 이고 최대 ≤ 4.5% (대회 n ≥ 5). 실DB 에는 아무것도 쓰지 않는다.
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
from src.metrics.heat_model import HeatModelCalculator  # noqa: E402
from src.metrics.hr_profile import HRProfileCalculator  # noqa: E402
from src.metrics.prediction.core import temp_factor  # noqa: E402
from src.utils.db_helpers import upsert_metric  # noqa: E402

NAME = {5000.0: "race_pred_5k_sec", 10000.0: "race_pred_10k_sec", 21097.5: "race_pred_half_sec"}
MAX_MAE, MAX_ABS, MIN_N = 2.5, 4.5, 5


def _run(conn, calc, day):
    res = calc.compute(CalcContext(conn=conn, scope_type="daily", scope_id=day))
    for r in res:
        upsert_metric(conn, "daily", day, r.metric_name, calc.provider, numeric_value=r.numeric_value,
                      json_value=json.loads(r.json_value) if r.json_value else None)
    return {r.metric_name: r for r in res}


def backtest(conn: sqlite3.Connection, since: str, today: str) -> dict:
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=today)
    prof = _run(conn, HRProfileCalculator(), today)
    hmax = json.loads(prof["hr_profile"].json_value)["self"]["hrmax"] if prof else None
    races = [r for r in ctx.get_runs((date.fromisoformat(today) - date.fromisoformat(since)).days)
             if r["is_race"] and r["nominal_m"] in NAME and hmax and r["avg_hr"] and r["avg_hr"] >= 0.84 * hmax]
    out = {}
    for hd in (0, 28):
        errs = []
        for r in races:
            d = (date.fromisoformat(r["date"]) - timedelta(days=hd)).isoformat()
            _run(conn, HRProfileCalculator(), d)
            hm = json.loads(_run(conn, HeatModelCalculator(), d)["heat_model"].json_value)
            p = _run(conn, DARPCalculator(), d)
            if NAME[r["nominal_m"]] not in p:
                continue
            t = ctx.get_activity_metric(r["id"], "weather_temp_c")
            pred = p[NAME[r["nominal_m"]]].numeric_value / temp_factor(t, hm["heat"], hm["cold"])
            errs.append(round((pred / r["perf_time_s"] - 1) * 100, 1))
        out[f"D-{hd}"] = {"n": len(errs), "mae": round(mean(abs(e) for e in errs), 2) if errs else None,
                          "max": max((abs(e) for e in errs), default=None), "errors": errs}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--since", default="2025-04-01")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    src = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    src.backup(mem)
    src.close()
    create_tables(mem)          # 메모리 사본에만 v20 컬럼 보장(실DB 무변경)
    res = backtest(mem, a.since, a.today)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    d0 = res["D-0"]
    ok = d0["n"] >= MIN_N and d0["mae"] is not None and d0["mae"] <= MAX_MAE and d0["max"] <= MAX_ABS
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
````

**`tests/test_pred_backtest.py`** — 신규, 전문 그대로(17줄)

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
    assert r["D-0"] == {"n": 0, "mae": None, "max": None, "errors": []}
````

검증:
```
python3 -m pytest tests/test_pred_backtest.py -q
python3 scripts/check_docs.py
```

