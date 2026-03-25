#!/usr/bin/env python3
"""Intervals.icu 미사용 API 재검증 — 정확한 엔드포인트 경로"""
import json, os, time
from datetime import datetime, timedelta

CONFIG_PATH = "/data/data/com.termux/files/home/projects/RunPulse/config.json"
OUTPUT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_intervals.json"
REPORT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_intervals.txt"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def dump_structure(obj, prefix="", max_depth=5, depth=0):
    results = []
    if depth >= max_depth:
        return results
    if isinstance(obj, dict):
        for k, v in sorted(obj.items()):
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                results.append((path, "dict", f"{{{len(v)} keys}}"))
                results.extend(dump_structure(v, path, max_depth, depth+1))
            elif isinstance(v, list):
                results.append((path, f"list[{len(v)}]", ""))
                if v and isinstance(v[0], dict):
                    results.append((f"{path}[0]", "dict", f"{{{len(v[0])} keys}}"))
                    results.extend(dump_structure(v[0], f"{path}[0]", max_depth, depth+1))
                elif v:
                    results.append((f"{path}[0]", type(v[0]).__name__, str(v[0])[:80]))
            else:
                t = type(v).__name__ if v is not None else "null"
                results.append((path, t, str(v)[:80] if v is not None else "null"))
    elif isinstance(obj, list):
        results.append((prefix, f"list[{len(obj)}]", ""))
        if obj and isinstance(obj[0], dict):
            results.extend(dump_structure(obj[0], f"{prefix}[0]", max_depth, depth+1))
        elif obj:
            results.append((f"{prefix}[0]", type(obj[0]).__name__, str(obj[0])[:80]))
    return results

def fmt(structure, title):
    lines = [f"\n{'='*70}", f"  {title}", f"{'='*70}"]
    for path, typ, sample in structure:
        s = f"  ex: {sample}" if sample else ""
        lines.append(f"  {path:<60} {typ:<15}{s}")
    return "\n".join(lines)

def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj[:3]]
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)

def main():
    import httpx
    config = load_config()
    intervals = config["intervals"]
    athlete_id = intervals["athlete_id"]
    api_key = intervals["api_key"]
    auth = ("API_KEY", api_key)

    athlete_base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    activity_base = "https://intervals.icu/api/v1/activity"

    today = datetime.now().strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # 최근 활동 ID
    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{athlete_base}/activities",
                     auth=auth,
                     params={"oldest": f"{month_ago}T00:00:00", "newest": f"{today}T23:59:59"})
        resp.raise_for_status()
        acts = resp.json()
    act_id = acts[0]["id"] if acts else None
    print(f"[intervals] act_id={act_id}, 총 {len(acts)}건\n", flush=True)

    results = {}
    report = []

    # ── Activity 엔드포인트 (athlete 없이 /api/v1/activity/{id}/...) ──
    activity_endpoints = [
        ("activity_detail",      f"{activity_base}/{act_id}"),
        ("activity_intervals",   f"{activity_base}/{act_id}/intervals"),
        ("activity_streams",     f"{activity_base}/{act_id}/streams"),
        ("activity_map",         f"{activity_base}/{act_id}/map"),
        ("activity_best_efforts",f"{activity_base}/{act_id}/best-efforts"),
        ("activity_pace_curve",  f"{activity_base}/{act_id}/pace-curve"),
        ("activity_hr_curve",    f"{activity_base}/{act_id}/hr-curve"),
        ("activity_power_curve", f"{activity_base}/{act_id}/power-curve"),
        ("activity_segments",    f"{activity_base}/{act_id}/segments"),
        ("activity_hr_histogram",f"{activity_base}/{act_id}/hr-histogram"),
        ("activity_pace_histogram",f"{activity_base}/{act_id}/pace-histogram"),
        ("activity_power_histogram",f"{activity_base}/{act_id}/power-histogram"),
        ("activity_gap_histogram",f"{activity_base}/{act_id}/gap-histogram"),
        ("activity_weather",     f"{activity_base}/{act_id}/weather-summary"),
        ("activity_power_vs_hr", f"{activity_base}/{act_id}/power-vs-hr"),
        ("activity_time_at_hr",  f"{activity_base}/{act_id}/time-at-hr"),
        ("activity_hr_load_model",f"{activity_base}/{act_id}/hr-load-model"),
    ]

    # ── Athlete 엔드포인트 ──
    athlete_endpoints = [
        ("athlete_profile",      f"{athlete_base}"),
        ("athlete_sport_settings",f"{athlete_base}/sport-settings"),
        ("athlete_sport_run",    f"{athlete_base}/sport-settings/Run"),
        ("athlete_gear",         f"{athlete_base}/gear"),
        ("athlete_power_curves", f"{athlete_base}/power-curves"),
        ("athlete_pace_curves",  f"{athlete_base}/pace-curves"),
        ("athlete_hr_curves",    f"{athlete_base}/hr-curves"),
        ("athlete_power_hr_curve",f"{athlete_base}/power-hr-curve?oldest={month_ago}&newest={today}"),
        ("athlete_weather_forecast",f"{athlete_base}/weather-forecast"),
        ("athlete_weather_config",f"{athlete_base}/weather-config"),
        ("athlete_activity_tags", f"{athlete_base}/activity-tags"),
        ("athlete_routes",       f"{athlete_base}/routes"),
        ("wellness_yesterday",   f"{athlete_base}/wellness/{(datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')}"),
    ]

    all_endpoints = activity_endpoints + athlete_endpoints

    for name, url in all_endpoints:
        print(f"  호출: {name}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, auth=auth)
                resp.raise_for_status()
                # streams can be large, check content type
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                else:
                    data = {"_raw_type": ct, "_size": len(resp.content), "_sample": resp.text[:200]}
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Intervals > {name}"))
            # 간단 요약
            if isinstance(data, dict):
                print(f"  [OK] {name} — {len(data)} keys", flush=True)
            elif isinstance(data, list):
                print(f"  [OK] {name} — {len(data)} items", flush=True)
            else:
                print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {str(e)[:100]}", flush=True)
        time.sleep(0.5)

    # 저장
    with open(OUTPUT_PATH, "w") as f:
        json.dump(sanitize(results), f, indent=2, ensure_ascii=False, default=str)
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report))
    print(f"\n[완료] JSON: {OUTPUT_PATH}", flush=True)
    print(f"[완료] 리포트: {REPORT_PATH}", flush=True)

    # 요약
    ok = sum(1 for v in results.values() if not (isinstance(v, dict) and "_error" in v))
    fail = sum(1 for v in results.values() if isinstance(v, dict) and "_error" in v)
    print(f"\n총 {len(results)}개 호출: 성공 {ok}, 실패 {fail}", flush=True)

if __name__ == "__main__":
    main()
