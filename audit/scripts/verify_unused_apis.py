#!/usr/bin/env python3
"""verify_unused_apis.py — 미구현 API 전수 호출 검증
러닝 분석에 관련된 미사용 API를 호출하여 필드 구조를 덤프합니다.
"""
import json, os, time
from datetime import datetime, timedelta

CONFIG_PATH = "/data/data/com.termux/files/home/projects/RunPulse/config.json"
OUTPUT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_audit.json"
REPORT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_audit.txt"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def dump_structure(obj, prefix="", max_depth=5, depth=0):
    results = []
    if depth >= max_depth:
        results.append((prefix, f"[max_depth] {type(obj).__name__}", str(obj)[:80]))
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

def call_safe(func, name, *args, **kwargs):
    """안전하게 호출, 결과 반환. 실패 시 에러 dict."""
    try:
        data = func(*args, **kwargs)
        print(f"  [OK] {name}", flush=True)
        return data
    except Exception as e:
        print(f"  [FAIL] {name}: {e}", flush=True)
        return {"_error": str(e)}

# ═══════════════════════════════════════════════════════
#  GARMIN — 미사용 API (러닝 관련)
# ═══════════════════════════════════════════════════════
def verify_garmin_unused(config):
    from garminconnect import Garmin
    print("\n[GARMIN] 미사용 API 검증 시작", flush=True)

    garmin_cfg = config["garmin"]
    tokenstore = garmin_cfg.get("tokenstore", "")
    client = Garmin()
    client.login(tokenstore=tokenstore)
    print("[garmin] 로그인 성공", flush=True)

    results = {}
    report = []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 최근 활동 ID 가져오기
    summaries = client.get_activities(0, 1)
    aid = summaries[0]["activityId"] if summaries else None
    print(f"[garmin] 기준 activity_id: {aid}", flush=True)

    # ── 활동 관련 미사용 메서드 ──
    activity_methods = {
        "activity_details":       ("get_activity_details", (aid,)),
        "activity_exercise_sets": ("get_activity_exercise_sets", (aid,)),
        "activity_gear":          ("get_activity_gear", (aid,)),
        "activity_power_zones":   ("get_activity_power_in_timezones", (aid,)),
        "activity_split_summaries": ("get_activity_split_summaries", (aid,)),
        "activity_typed_splits":  ("get_activity_typed_splits", (aid,)),
        "activity_types":         ("get_activity_types", ()),
    }

    print("\n── 활동 관련 ──", flush=True)
    for key, (method, args) in activity_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    # ── 퍼포먼스/피트니스 관련 미사용 메서드 ──
    perf_methods = {
        "race_predictions":     ("get_race_predictions", ()),
        "training_status":      ("get_training_status", (yesterday,)),
        "endurance_score":      ("get_endurance_score", (yesterday,)),
        "hill_score":           ("get_hill_score", (yesterday,)),
        "running_tolerance":    ("get_running_tolerance", (yesterday,)),
        "lactate_threshold":    ("get_lactate_threshold", ()),
        "cycling_ftp":          ("get_cycling_ftp", ()),
        "fitnessage":           ("get_fitnessage_data", (yesterday,)),
        "personal_records":     ("get_personal_record", ("running",)),
    }

    print("\n── 퍼포먼스/피트니스 ──", flush=True)
    for key, (method, args) in perf_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    # ── 일일 데이터 미사용 메서드 ──
    daily_methods = {
        "heart_rates":          ("get_heart_rates", (yesterday,)),
        "daily_steps":          ("get_daily_steps", (yesterday, 1)),
        "steps_data":           ("get_steps_data", (yesterday,)),
        "floors":               ("get_floors", (yesterday,)),
        "all_day_stress":       ("get_all_day_stress", (yesterday,)),
        "hydration":            ("get_hydration_data", (yesterday,)),
        "intensity_minutes":    ("get_intensity_minutes_data", (yesterday,)),
        "body_battery_events":  ("get_body_battery_events", (yesterday,)),
        "blood_pressure":       ("get_blood_pressure", (yesterday,)),
        "daily_weigh_ins":      ("get_daily_weigh_ins", (yesterday,)),
        "user_summary":         ("get_user_summary", (yesterday,)),
        "stats":                ("get_stats", (yesterday,)),
        "stats_and_body":       ("get_stats_and_body", (yesterday,)),
    }

    print("\n── 일일 데이터 ──", flush=True)
    for key, (method, args) in daily_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    # ── 디바이스/프로필 ──
    profile_methods = {
        "devices":              ("get_devices", ()),
        "device_last_used":     ("get_device_last_used", ()),
        "user_profile":         ("get_user_profile", ()),
        "primary_training_device": ("get_primary_training_device", ()),
        "unit_system":          ("get_unit_system", ()),
        "gear_defaults":        ("get_gear_defaults", ()),
        "gear_stats":           ("get_gear_stats", (aid,)),
    }

    print("\n── 디바이스/프로필 ──", flush=True)
    for key, (method, args) in profile_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    # ── 주간 데이터 ──
    weekly_methods = {
        "weekly_stress":         ("get_weekly_stress", (yesterday,)),
        "weekly_steps":          ("get_weekly_steps", (yesterday,)),
        "weekly_intensity_mins": ("get_weekly_intensity_minutes", (yesterday,)),
    }

    print("\n── 주간 데이터 ──", flush=True)
    for key, (method, args) in weekly_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    # ── 기간 데이터 ──
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    period_methods = {
        "progress_summary":     ("get_progress_summary_between_dates", (week_ago, today)),
        "activities_by_date":   ("get_activities_by_date", (week_ago, today)),
        "weigh_ins":            ("get_weigh_ins", (week_ago, today)),
    }

    print("\n── 기간 데이터 ──", flush=True)
    for key, (method, args) in period_methods.items():
        data = call_safe(getattr(client, method), key, *args)
        results[key] = data
        if not isinstance(data, dict) or "_error" not in data:
            report.append(fmt(dump_structure(data, key), f"Garmin > {key}"))
        time.sleep(1)

    return results, report

# ═══════════════════════════════════════════════════════
#  STRAVA — 미사용 API
# ═══════════════════════════════════════════════════════
def verify_strava_unused(config):
    import httpx
    print("\n[STRAVA] 미사용 API 검증 시작", flush=True)

    strava = config["strava"]
    # 토큰 갱신
    if strava.get("expires_at", 0) < time.time():
        with httpx.Client(timeout=30) as c:
            resp = c.post("https://www.strava.com/oauth/token", data={
                "client_id": strava["client_id"],
                "client_secret": strava["client_secret"],
                "refresh_token": strava["refresh_token"],
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            td = resp.json()
            strava.update({k: td[k] for k in ["access_token","refresh_token","expires_at"]})
            config["strava"] = strava
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    headers = {"Authorization": f"Bearer {strava['access_token']}"}
    base = "https://www.strava.com/api/v3"
    results = {}
    report = []

    # 최근 활동 ID
    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{base}/athlete/activities", headers=headers, params={"per_page": 1})
        resp.raise_for_status()
        acts = resp.json()
    aid = acts[0]["id"] if acts else None
    gear_id = acts[0].get("gear_id") if acts else None
    print(f"[strava] 기준 activity_id: {aid}, gear_id: {gear_id}", flush=True)

    endpoints = {
        "athlete_profile": (f"{base}/athlete", {}),
        "athlete_zones": (f"{base}/athlete/zones", {}),
        "activity_laps": (f"{base}/activities/{aid}/laps", {}),
        "activity_comments": (f"{base}/activities/{aid}/comments", {}),
        "activity_kudos": (f"{base}/activities/{aid}/kudos", {}),
    }
    if gear_id:
        endpoints["gear_detail"] = (f"{base}/gear/{gear_id}", {})

    for key, (url, params) in endpoints.items():
        print(f"  호출: {key}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            results[key] = data
            report.append(fmt(dump_structure(data, key), f"Strava > {key}"))
            print(f"  [OK] {key}", flush=True)
        except Exception as e:
            results[key] = {"_error": str(e)}
            print(f"  [FAIL] {key}: {e}", flush=True)
        time.sleep(1)

    return results, report

# ═══════════════════════════════════════════════════════
#  INTERVALS.ICU — 미사용 API
# ═══════════════════════════════════════════════════════
def verify_intervals_unused(config):
    import httpx
    print("\n[INTERVALS] 미사용 API 검증 시작", flush=True)

    intervals = config["intervals"]
    athlete_id = intervals["athlete_id"]
    api_key = intervals["api_key"]
    auth = ("API_KEY", api_key)
    base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    results = {}
    report = []

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # 최근 활동 ID (Garmin external_id가 아닌 intervals 자체 ID)
    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{base}/activities",
                     auth=auth,
                     params={"oldest": f"{month_ago}T00:00:00", "newest": f"{today}T23:59:59"})
        resp.raise_for_status()
        acts = resp.json()
    act_id = acts[0]["id"] if acts else None
    print(f"[intervals] 기준 activity_id: {act_id}, 총 {len(acts)}건", flush=True)

    # 활동 관련
    activity_endpoints = {}
    if act_id:
        activity_endpoints = {
            "activity_intervals": (f"{base}/activities/{act_id}/intervals", {}),
            "activity_laps": (f"{base}/activities/{act_id}/laps", {}),
            "activity_map": (f"{base}/activities/{act_id}/map", {}),
            "activity_pace_curve": (f"{base}/activities/{act_id}/pace-curve", {}),
            "activity_hr_curve": (f"{base}/activities/{act_id}/hr-curve", {}),
        }

    # 선수 관련
    athlete_endpoints = {
        "athlete_profile": (f"https://intervals.icu/api/v1/athlete/{athlete_id}", {}),
        "athlete_sportinfo": (f"{base}/sport-info", {}),
        "athlete_zones": (f"{base}/zones", {}),
        "athlete_settings": (f"{base}/settings", {}),
        "athlete_gear": (f"{base}/gear", {}),
        "fitness_summary": (f"{base}/fitness/{month_ago}/{today}", {}),
    }

    all_endpoints = {**activity_endpoints, **athlete_endpoints}

    for key, (url, params) in all_endpoints.items():
        print(f"  호출: {key}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, auth=auth, params=params)
                resp.raise_for_status()
                data = resp.json()
            results[key] = data
            report.append(fmt(dump_structure(data, key), f"Intervals > {key}"))
            print(f"  [OK] {key}", flush=True)
        except Exception as e:
            results[key] = {"_error": str(e)}
            print(f"  [FAIL] {key}: {e}", flush=True)
        time.sleep(0.5)

    return results, report

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
def main():
    config = load_config()
    all_results = {}
    all_report = []

    # Garmin
    try:
        gr, grp = verify_garmin_unused(config)
        all_results["garmin"] = gr
        all_report.extend(grp)
    except Exception as e:
        print(f"[garmin] 전체 실패: {e}", flush=True)
        all_results["garmin"] = {"_error": str(e)}

    # Strava
    try:
        sr, srp = verify_strava_unused(config)
        all_results["strava"] = sr
        all_report.extend(srp)
    except Exception as e:
        print(f"[strava] 전체 실패: {e}", flush=True)
        all_results["strava"] = {"_error": str(e)}

    # Intervals
    try:
        ir, irp = verify_intervals_unused(config)
        all_results["intervals"] = ir
        all_report.extend(irp)
    except Exception as e:
        print(f"[intervals] 전체 실패: {e}", flush=True)
        all_results["intervals"] = {"_error": str(e)}

    # 저장
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj[:3]]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        return str(obj)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(sanitize(all_results), f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[완료] JSON: {OUTPUT_PATH}", flush=True)

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(all_report))
    print(f"[완료] 리포트: {REPORT_PATH}", flush=True)

    # 요약
    print("\n" + "="*70, flush=True)
    print("  미사용 API 호출 요약", flush=True)
    print("="*70, flush=True)
    for svc, data in all_results.items():
        if isinstance(data, dict):
            ok = sum(1 for v in data.values() if not (isinstance(v, dict) and "_error" in v))
            fail = sum(1 for v in data.values() if isinstance(v, dict) and "_error" in v)
            print(f"  {svc:<15} 성공: {ok}, 실패: {fail}", flush=True)

if __name__ == "__main__":
    main()
