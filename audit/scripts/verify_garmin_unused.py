#!/usr/bin/env python3
"""Garmin 미사용 API만 재실행 — 파일 저장 보장"""
import json, os, time
from datetime import datetime, timedelta

CONFIG_PATH = "/data/data/com.termux/files/home/projects/RunPulse/config.json"
OUTPUT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_garmin.json"
REPORT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/unused_api_garmin.txt"

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
    from garminconnect import Garmin
    config = load_config()
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

    calls = [
        ("activity_details", lambda: client.get_activity_details(aid)),
        ("activity_exercise_sets", lambda: client.get_activity_exercise_sets(aid)),
        ("activity_gear", lambda: client.get_activity_gear(aid)),
        ("activity_power_zones", lambda: client.get_activity_power_in_timezones(aid)),
        ("activity_split_summaries", lambda: client.get_activity_split_summaries(aid)),
        ("activity_typed_splits", lambda: client.get_activity_typed_splits(aid)),
        ("activity_types", lambda: client.get_activity_types()),
        ("race_predictions", lambda: client.get_race_predictions()),
        ("training_status", lambda: client.get_training_status(yesterday)),
        ("endurance_score", lambda: client.get_endurance_score(yesterday)),
        ("hill_score", lambda: client.get_hill_score(yesterday)),
        ("running_tolerance", lambda: client.get_running_tolerance(yesterday, today)),
        ("lactate_threshold", lambda: client.get_lactate_threshold()),
        ("fitnessage", lambda: client.get_fitnessage_data(yesterday)),
        ("personal_records", lambda: client.get_personal_record()),
        ("heart_rates", lambda: client.get_heart_rates(yesterday)),
        ("steps_data", lambda: client.get_steps_data(yesterday)),
        ("all_day_stress", lambda: client.get_all_day_stress(yesterday)),
        ("intensity_minutes", lambda: client.get_intensity_minutes_data(yesterday)),
        ("body_battery_events", lambda: client.get_body_battery_events(yesterday)),
        ("daily_weigh_ins", lambda: client.get_daily_weigh_ins(yesterday)),
        ("user_summary", lambda: client.get_user_summary(yesterday)),
        ("stats", lambda: client.get_stats(yesterday)),
        ("stats_and_body", lambda: client.get_stats_and_body(yesterday)),
        ("devices", lambda: client.get_devices()),
        ("device_last_used", lambda: client.get_device_last_used()),
        ("user_profile", lambda: client.get_user_profile()),
        ("primary_training_device", lambda: client.get_primary_training_device()),
        ("weekly_stress", lambda: client.get_weekly_stress(yesterday)),
        ("weekly_steps", lambda: client.get_weekly_steps(yesterday)),
        ("weekly_intensity_mins", lambda: client.get_weekly_intensity_minutes(week_ago, today)),
        ("progress_summary", lambda: client.get_progress_summary_between_dates(week_ago, today)),
        ("activities_by_date", lambda: client.get_activities_by_date(week_ago, today)),
    ]

    for name, func in calls:
        try:
            data = func()
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Garmin > {name}"))
            if isinstance(data, dict):
                print(f"  [OK] {name} — {len(data)} keys", flush=True)
            elif isinstance(data, list):
                print(f"  [OK] {name} — {len(data)} items", flush=True)
            else:
                print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {str(e)[:80]}", flush=True)
        time.sleep(1)

    # 즉시 저장
    with open(OUTPUT_PATH, "w") as f:
        json.dump(sanitize(results), f, indent=2, ensure_ascii=False, default=str)
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report))

    ok = sum(1 for v in results.values() if not (isinstance(v, dict) and "_error" in v))
    fail = sum(1 for v in results.values() if isinstance(v, dict) and "_error" in v)
    print(f"\n[완료] 성공: {ok}, 실패: {fail}", flush=True)
    print(f"JSON: {OUTPUT_PATH}", flush=True)
    print(f"리포트: {REPORT_PATH}", flush=True)

if __name__ == "__main__":
    main()
