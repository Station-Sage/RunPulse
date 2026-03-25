#!/usr/bin/env python3
"""Intervals.icu 실패 3개 엔드포인트 파라미터 보정 재시도"""
import json, httpx, os
from datetime import datetime, timedelta

BASE = "/data/data/com.termux/files/home/projects/RunPulse"
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)

AID = cfg["intervals"]["athlete_id"]
KEY = cfg["intervals"]["api_key"]
AUTH = ("API_KEY", KEY)
API = "https://intervals.icu/api/v1"

# 최근 활동 ID 가져오기
newest = datetime.now().strftime("%Y-%m-%d")
oldest = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

with httpx.Client(timeout=30, auth=AUTH) as c:
    r = c.get(f"{API}/athlete/{AID}/activities", params={"oldest": oldest, "newest": newest})
    acts = r.json()
    act_id = acts[0]["id"] if acts else None
    print(f"활동 ID: {act_id}")

    results = {}

    # 1. best-efforts — stream 파라미터 필수
    print("\n=== 1. activity best-efforts ===")
    for stream in ["watts", "heartrate", "speed"]:
        try:
            r = c.get(f"{API}/activity/{act_id}/best-efforts",
                      params={"stream": stream, "count": 5})
            if r.status_code == 200:
                data = r.json()
                print(f"  stream={stream}: OK — {len(data) if isinstance(data, list) else type(data).__name__}")
                results[f"best_efforts_{stream}"] = {"status": "OK", "count": len(data) if isinstance(data, list) else 1}
            else:
                print(f"  stream={stream}: FAIL {r.status_code}")
                results[f"best_efforts_{stream}"] = {"status": f"FAIL {r.status_code}"}
        except Exception as e:
            print(f"  stream={stream}: ERROR {e}")
            results[f"best_efforts_{stream}"] = {"status": f"ERROR {e}"}

    # 2. athlete power-curves — type 파라미터 필수
    print("\n=== 2. athlete power-curves ===")
    try:
        r = c.get(f"{API}/athlete/{AID}/power-curves", params={"type": "Run"})
        if r.status_code == 200:
            data = r.json()
            cnt = len(data) if isinstance(data, list) else len(data) if isinstance(data, dict) else 0
            print(f"  type=Run: OK — {cnt} items")
            results["athlete_power_curves"] = {"status": "OK", "count": cnt}
            # 구조 샘플
            if isinstance(data, list) and data:
                sample = data[0]
                print(f"  샘플 키: {list(sample.keys()) if isinstance(sample, dict) else type(sample)}")
        else:
            print(f"  type=Run: FAIL {r.status_code} — {r.text[:200]}")
            results["athlete_power_curves"] = {"status": f"FAIL {r.status_code}"}
    except Exception as e:
        print(f"  ERROR: {e}")
        results["athlete_power_curves"] = {"status": f"ERROR {e}"}

    # 3. athlete power-vs-hr — type 파라미터 필수
    print("\n=== 3. athlete power-hr-curve ===")
    try:
        r = c.get(f"{API}/athlete/{AID}/power-hr-curve", params={"type": "Run"})
        if r.status_code == 200:
            data = r.json()
            cnt = len(data) if isinstance(data, list) else len(data) if isinstance(data, dict) else 0
            print(f"  type=Run: OK — {cnt} keys/items")
            results["athlete_power_hr_curve"] = {"status": "OK", "count": cnt}
            if isinstance(data, dict):
                print(f"  키: {list(data.keys())[:10]}")
        else:
            print(f"  type=Run: FAIL {r.status_code} — {r.text[:200]}")
            results["athlete_power_hr_curve"] = {"status": f"FAIL {r.status_code}"}
    except Exception as e:
        print(f"  ERROR: {e}")
        results["athlete_power_hr_curve"] = {"status": f"ERROR {e}"}

    # 결과 저장
    with open(os.path.join(BASE, "intervals_fixed_3.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[저장] {os.path.join(BASE, 'intervals_fixed_3.json')}")
    print(f"\n총 결과: {sum(1 for v in results.values() if v['status']=='OK')}/{len(results)} 성공")

