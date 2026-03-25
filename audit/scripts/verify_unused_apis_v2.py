#!/usr/bin/env python3
"""verify_unused_apis_v2.py — 미구현 API 전수 호출 (에러 핸들링 보강)"""
import json, os, time, traceback
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
        results.append((prefix, f"[max_depth]", str(obj)[:80]))
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

def safe_call(func, name, *args, **kwargs):
    try:
        data = func(*args, **kwargs)
        print(f"  [OK] {name}", flush=True)
        return data
    except Exception as e:
        print(f"  [FAIL] {name}: {e}", flush=True)
        return {"_error": str(e)}

def is_error(data):
    return isinstance(data, dict) and "_error" in data

# ═══════════════ GARMIN (이전에 실패/누락 수정) ═══════════════
def verify_garmin(config):
    from garminconnect import Garmin
    print("\n[GARMIN] 미사용 API 검증", flush=True)
    garmin_cfg = config["garmin"]
    client = Garmin()
    client.login(tokenstore=garmin_cfg.get("tokenstore", ""))
    print("[garmin] 로그인 성공", flush=True)

    results = {}
    report = []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    summaries = client.get_activities(0, 1)
    aid = summaries[0]["activityId"] if summaries else None
    print(f"[garmin] activity_id: {aid}", flush=True)

    calls = [
        # 활동 관련
        ("activity_details", lambda: client.get_activity_details(aid)),
        ("activity_exercise_sets", lambda: client.get_activity_exercise_sets(aid)),
        ("activity_gear", lambda: client.get_activity_gear(aid)),
        ("activity_power_zones", lambda: client.get_activity_power_in_timezones(aid)),
        ("activity_split_summaries", lambda: client.get_activity_split_summaries(aid)),
        ("activity_typed_splits", lambda: client.get_activity_typed_splits(aid)),
        ("activity_types", lambda: client.get_activity_types()),
        # 퍼포먼스
        ("race_predictions", lambda: client.get_race_predictions()),
        ("training_status", lambda: client.get_training_status(yesterday)),
        ("endurance_score", lambda: client.get_endurance_score(yesterday)),
        ("hill_score", lambda: client.get_hill_score(yesterday)),
        ("running_tolerance", lambda: client.get_running_tolerance(yesterday, today)),
        ("lactate_threshold", lambda: client.get_lactate_threshold()),
        ("cycling_ftp", lambda: client.get_cycling_ftp()),
        ("fitnessage", lambda: client.get_fitnessage_data(yesterday)),
        ("personal_records", lambda: client.get_personal_record()),
        # 일일
        ("heart_rates", lambda: client.get_heart_rates(yesterday)),
        ("steps_data", lambda: client.get_steps_data(yesterday)),
        ("floors", lambda: client.get_floors(yesterday)),
        ("all_day_stress", lambda: client.get_all_day_stress(yesterday)),
        ("hydration", lambda: client.get_hydration_data(yesterday)),
        ("intensity_minutes", lambda: client.get_intensity_minutes_data(yesterday)),
        ("body_battery_events", lambda: client.get_body_battery_events(yesterday)),
        ("blood_pressure", lambda: client.get_blood_pressure(yesterday)),
        ("daily_weigh_ins", lambda: client.get_daily_weigh_ins(yesterday)),
        ("user_summary", lambda: client.get_user_summary(yesterday)),
        ("stats", lambda: client.get_stats(yesterday)),
        ("stats_and_body", lambda: client.get_stats_and_body(yesterday)),
        # 디바이스/프로필
        ("devices", lambda: client.get_devices()),
        ("device_last_used", lambda: client.get_device_last_used()),
        ("user_profile", lambda: client.get_user_profile()),
        ("primary_training_device", lambda: client.get_primary_training_device()),
        ("unit_system", lambda: client.get_unit_system()),
        # 주간
        ("weekly_stress", lambda: client.get_weekly_stress(yesterday)),
        ("weekly_steps", lambda: client.get_weekly_steps(yesterday)),
        ("weekly_intensity_mins", lambda: client.get_weekly_intensity_minutes(week_ago, today)),
        # 기간
        ("progress_summary", lambda: client.get_progress_summary_between_dates(week_ago, today)),
        ("activities_by_date", lambda: client.get_activities_by_date(week_ago, today)),
        ("weigh_ins", lambda: client.get_weigh_ins(week_ago, today)),
    ]

    for name, func in calls:
        data = safe_call(func, name)
        results[name] = data
        if not is_error(data):
            report.append(fmt(dump_structure(data, name), f"Garmin > {name}"))
        time.sleep(1)

    return results, report

# ═══════════════ STRAVA ═══════════════
def verify_strava(config):
    import httpx
    print("\n[STRAVA] 미사용 API 검증", flush=True)
    strava = config["strava"]

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

    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{base}/athlete/activities", headers=headers, params={"per_page": 1})
        resp.raise_for_status()
        acts = resp.json()
    aid = acts[0]["id"] if acts else None
    gear_id = acts[0].get("gear_id") if acts else None
    print(f"[strava] activity_id: {aid}, gear_id: {gear_id}", flush=True)

    results = {}
    report = []

    endpoints = [
        ("athlete_profile", f"{base}/athlete", {}),
        ("athlete_zones", f"{base}/athlete/zones", {}),
        ("athlete_stats", f"{base}/athletes/{acts[0]['athlete']['id']}/stats" if acts else None, {}),
        ("activity_laps", f"{base}/activities/{aid}/laps", {}),
        ("activity_comments", f"{base}/activities/{aid}/comments", {}),
        ("activity_kudos", f"{base}/activities/{aid}/kudos", {}),
    ]
    if gear_id:
        endpoints.append(("gear_detail", f"{base}/gear/{gear_id}", {}))

    for name, url, params in endpoints:
        if url is None:
            continue
        print(f"  호출: {name}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Strava > {name}"))
            print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {e}", flush=True)
        time.sleep(1)

    return results, report

# ═══════════════ INTERVALS.ICU ═══════════════
def verify_intervals(config):
    import httpx
    print("\n[INTERVALS] 미사용 API 검증", flush=True)
    intervals = config["intervals"]
    athlete_id = intervals["athlete_id"]
    api_key = intervals["api_key"]
    auth = ("API_KEY", api_key)
    base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"

    today = datetime.now().strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{base}/activities", auth=auth,
                     params={"oldest": f"{month_ago}T00:00:00", "newest": f"{today}T23:59:59"})
        resp.raise_for_status()
        acts = resp.json()
    act_id = acts[0]["id"] if acts else None
    print(f"[intervals] activity_id: {act_id}, 총 {len(acts)}건", flush=True)

    results = {}
    report = []

    endpoints = [
        ("athlete_profile", f"https://intervals.icu/api/v1/athlete/{athlete_id}", {}),
        ("sport_info", f"{base}/sport-info", {}),
        ("zones", f"{base}/zones", {}),
        ("gear", f"{base}/gear", {}),
        ("fitness_chart", f"{base}/fitness/{month_ago}/{today}", {}),
        ("events", f"{base}/events", {"oldest": month_ago, "newest": today}),
        ("calendars", f"{base}/calendars", {}),
    ]
    if act_id:
        endpoints.extend([
            ("activity_intervals", f"{base}/activities/{act_id}/intervals", {}),
            ("activity_laps", f"{base}/activities/{act_id}/laps", {}),
            ("activity_map", f"{base}/activities/{act_id}/map", {}),
            ("activity_pace_curve", f"{base}/activities/{act_id}/pace-curve", {}),
            ("activity_hr_curve", f"{base}/activities/{act_id}/hr-curve", {}),
            ("activity_power_curve", f"{base}/activities/{act_id}/power-curve", {}),
        ])

    for name, url, params in endpoints:
        print(f"  호출: {name}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, auth=auth, params=params)
                resp.raise_for_status()
                data = resp.json()
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Intervals > {name}"))
            print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {e}", flush=True)
        time.sleep(0.5)

    return results, report

# ═══════════════ MAIN ═══════════════
def main():
    config = load_config()
    all_results = {}
    all_report = []

    for svc, func in [("garmin", verify_garmin), ("strava", verify_strava), ("intervals", verify_intervals)]:
        try:
            r, rp = func(config)
            all_results[svc] = r
            all_report.extend(rp)
        except Exception as e:
            print(f"[{svc}] 전체 실패: {e}", flush=True)
            traceback.print_exc()
            all_results[svc] = {"_error": str(e)}

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
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(all_report))

    print(f"\n[완료] JSON: {OUTPUT_PATH}", flush=True)
    print(f"[완료] 리포트: {REPORT_PATH}", flush=True)

    print("\n" + "="*70, flush=True)
    print("  미사용 API 호출 요약", flush=True)
    print("="*70, flush=True)
    for svc, data in all_results.items():
        if isinstance(data, dict) and "_error" not in data:
            ok = sum(1 for v in data.values() if not is_error(v))
            fail = sum(1 for v in data.values() if is_error(v))
            print(f"  {svc:<15} 성공: {ok}, 실패: {fail}", flush=True)

if __name__ == "__main__":
    main()
