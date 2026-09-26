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
