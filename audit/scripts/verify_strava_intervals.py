#!/usr/bin/env python3
"""Strava + Intervals 미사용 API 검증 (개별 실행)"""
import json, os, time, traceback
from datetime import datetime, timedelta

CONFIG_PATH = "/data/data/com.termux/files/home/projects/RunPulse/config.json"
OUT_DIR = "/data/data/com.termux/files/home/projects/RunPulse"

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

def save_partial(name, data, report_lines):
    jp = os.path.join(OUT_DIR, f"unused_api_{name}.json")
    rp = os.path.join(OUT_DIR, f"unused_api_{name}.txt")
    with open(jp, "w") as f:
        json.dump(sanitize(data), f, indent=2, ensure_ascii=False, default=str)
    with open(rp, "w") as f:
        f.write("\n".join(report_lines))
    print(f"  [저장] {jp}", flush=True)

# ═══════════════ STRAVA ═══════════════
def do_strava():
    import httpx
    print("\n[STRAVA] 미사용 API 검증", flush=True)
    config = load_config()
    strava = config["strava"]

    if strava.get("expires_at", 0) < time.time():
        print("[strava] 토큰 갱신...", flush=True)
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
        print("[strava] 토큰 갱신 완료", flush=True)

    headers = {"Authorization": f"Bearer {strava['access_token']}"}
    base = "https://www.strava.com/api/v3"

    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{base}/athlete/activities", headers=headers, params={"per_page": 1})
        resp.raise_for_status()
        acts = resp.json()

    aid = acts[0]["id"] if acts else None
    gear_id = acts[0].get("gear_id") if acts else None
    athlete_id = acts[0]["athlete"]["id"] if acts else None
    print(f"[strava] aid={aid}, gear={gear_id}, athlete={athlete_id}", flush=True)

    results = {}
    report = []

    endpoints = [
        ("athlete_profile", f"{base}/athlete"),
        ("athlete_stats", f"{base}/athletes/{athlete_id}/stats"),
        ("activity_laps", f"{base}/activities/{aid}/laps"),
        ("activity_comments", f"{base}/activities/{aid}/comments"),
        ("activity_kudos", f"{base}/activities/{aid}/kudos"),
    ]
    if gear_id:
        endpoints.append(("gear_detail", f"{base}/gear/{gear_id}"))

    for name, url in endpoints:
        print(f"  호출: {name}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Strava > {name}"))
            print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {e}", flush=True)
        time.sleep(1)

    save_partial("strava", results, report)
    return results, report

# ═══════════════ INTERVALS ═══════════════
def do_intervals():
    import httpx
    print("\n[INTERVALS] 미사용 API 검증", flush=True)
    config = load_config()
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
    print(f"[intervals] act_id={act_id}, 총 {len(acts)}건", flush=True)

    results = {}
    report = []

    endpoints = [
        ("athlete_profile", f"https://intervals.icu/api/v1/athlete/{athlete_id}"),
        ("sport_info", f"{base}/sport-info"),
        ("zones", f"{base}/zones"),
        ("gear", f"{base}/gear"),
        ("fitness_chart", f"{base}/fitness/{month_ago}/{today}"),
        ("events", f"{base}/events?oldest={month_ago}&newest={today}"),
        ("calendars", f"{base}/calendars"),
    ]
    if act_id:
        endpoints.extend([
            ("activity_intervals", f"{base}/activities/{act_id}/intervals"),
            ("activity_laps", f"{base}/activities/{act_id}/laps"),
            ("activity_map", f"{base}/activities/{act_id}/map"),
            ("activity_pace_curve", f"{base}/activities/{act_id}/pace-curve"),
            ("activity_hr_curve", f"{base}/activities/{act_id}/hr-curve"),
            ("activity_power_curve", f"{base}/activities/{act_id}/power-curve"),
        ])

    for name, url in endpoints:
        print(f"  호출: {name}...", flush=True)
        try:
            with httpx.Client(timeout=30) as c:
                resp = c.get(url, auth=auth)
                resp.raise_for_status()
                data = resp.json()
            results[name] = data
            report.append(fmt(dump_structure(data, name), f"Intervals > {name}"))
            print(f"  [OK] {name}", flush=True)
        except Exception as e:
            results[name] = {"_error": str(e)}
            print(f"  [FAIL] {name}: {e}", flush=True)
        time.sleep(0.5)

    save_partial("intervals", results, report)
    return results, report

# ═══════════════ MAIN ═══════════════
def main():
    print("Garmin은 이미 완료 — Strava + Intervals만 실행\n", flush=True)

    try:
        do_strava()
    except Exception as e:
        print(f"[strava] 전체 실패: {e}", flush=True)
        traceback.print_exc()

    try:
        do_intervals()
    except Exception as e:
        print(f"[intervals] 전체 실패: {e}", flush=True)
        traceback.print_exc()

    print("\n[완료] 모든 검증 종료", flush=True)

if __name__ == "__main__":
    main()
