#!/usr/bin/env python3
"""verify_api_fields.py — 각 서비스 API 실측 필드 검증
Strava, Garmin, Intervals.icu API를 1건씩 호출하여
전체 응답 JSON 구조를 재귀적으로 덤프합니다.
"""
import json, os, sys, time
from datetime import datetime, timedelta
from collections import OrderedDict

CONFIG_PATH = os.path.expanduser("/data/data/com.termux/files/home/projects/RunPulse/config.json")
OUTPUT_PATH = os.path.expanduser("/data/data/com.termux/files/home/projects/RunPulse/api_field_audit.json")
REPORT_PATH = os.path.expanduser("/data/data/com.termux/files/home/projects/RunPulse/api_field_audit.txt")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def dump_structure(obj, prefix="", max_depth=5, depth=0):
    """재귀적으로 JSON 구조를 (path, type, sample) 리스트로 반환."""
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
    return results

def format_structure(structure, title):
    lines = [f"\n{'='*70}", f"  {title}", f"{'='*70}"]
    for path, typ, sample in structure:
        sample_str = f"  ex: {sample}" if sample else ""
        lines.append(f"  {path:<60} {typ:<15}{sample_str}")
    return "\n".join(lines)

# ─── STRAVA ─────────────────────────────────────────────
def verify_strava(config):
    import httpx
    print("[strava] 시작...", flush=True)
    strava = config["strava"]

    # 토큰 갱신
    if strava.get("expires_at", 0) < time.time():
        print("[strava] 토큰 갱신 중...", flush=True)
        with httpx.Client(timeout=30) as client:
            resp = client.post("https://www.strava.com/oauth/token", data={
                "client_id": strava["client_id"],
                "client_secret": strava["client_secret"],
                "refresh_token": strava["refresh_token"],
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            token_data = resp.json()
            strava["access_token"] = token_data["access_token"]
            strava["refresh_token"] = token_data["refresh_token"]
            strava["expires_at"] = token_data["expires_at"]
            # config.json 업데이트
            config["strava"] = strava
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print("[strava] 토큰 갱신 완료", flush=True)

    headers = {"Authorization": f"Bearer {strava['access_token']}"}
    base = "https://www.strava.com/api/v3"
    results = {}

    # 1) activity summary (최근 1건)
    print("[strava] summary 호출...", flush=True)
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{base}/athlete/activities", headers=headers, params={"per_page": 1})
        resp.raise_for_status()
        summaries = resp.json()

    if summaries:
        summary = summaries[0]
        activity_id = summary["id"]
        results["activity_summary"] = {
            "raw": summary,
            "structure": dump_structure(summary, "summary")
        }
        print(f"[strava] summary OK — id={activity_id}, keys={len(summary)}", flush=True)

        # 2) activity detail
        print("[strava] detail 호출...", flush=True)
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{base}/activities/{activity_id}", headers=headers)
            resp.raise_for_status()
            detail = resp.json()
        results["activity_detail"] = {
            "raw": detail,
            "structure": dump_structure(detail, "detail")
        }
        print(f"[strava] detail OK — keys={len(detail)}", flush=True)

        # 3) streams
        print("[strava] streams 호출...", flush=True)
        stream_keys = "time,distance,latlng,altitude,heartrate,cadence,watts,temp,moving,grade_smooth,velocity_smooth"
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{base}/activities/{activity_id}/streams",
                            headers=headers,
                            params={"keys": stream_keys, "key_type": "time"})
            resp.raise_for_status()
            streams = resp.json()
        results["streams"] = {
            "raw_keys": [s.get("type") for s in streams] if isinstance(streams, list) else "N/A",
            "structure": dump_structure(streams, "streams")
        }
        print(f"[strava] streams OK — types={results['streams']['raw_keys']}", flush=True)

        # 4) zones
        print("[strava] zones 호출...", flush=True)
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{base}/activities/{activity_id}/zones", headers=headers)
                resp.raise_for_status()
                zones = resp.json()
            results["zones"] = {
                "raw": zones,
                "structure": dump_structure(zones, "zones")
            }
            print(f"[strava] zones OK", flush=True)
        except Exception as e:
            results["zones"] = {"error": str(e)}
            print(f"[strava] zones 실패: {e}", flush=True)

    return results

# ─── GARMIN ─────────────────────────────────────────────
def verify_garmin(config):
    from garminconnect import Garmin
    print("[garmin] 시작...", flush=True)
    garmin_cfg = config["garmin"]

    # 로그인
    tokenstore = os.path.expanduser(garmin_cfg.get("tokenstore", "~/.garth"))
    try:
        client = Garmin()
        client.login(tokenstore=tokenstore)
        print("[garmin] 토큰 로그인 성공", flush=True)
    except Exception as e:
        print(f"[garmin] 토큰 실패, 이메일 로그인: {e}", flush=True)
        client = Garmin(garmin_cfg["email"], garmin_cfg["password"])
        client.login()
        os.makedirs(tokenstore, exist_ok=True)
        client.garth.dump(tokenstore)

    results = {}

    # 1) activity summary
    print("[garmin] activity summary 호출...", flush=True)
    summaries = client.get_activities(0, 1)
    if summaries:
        summary = summaries[0]
        activity_id = summary.get("activityId")
        results["activity_summary"] = {
            "raw": summary,
            "structure": dump_structure(summary, "garmin_summary")
        }
        print(f"[garmin] summary OK — id={activity_id}, keys={len(summary)}", flush=True)

        # 2) activity detail
        print("[garmin] activity detail 호출...", flush=True)
        detail = client.get_activity(activity_id)
        results["activity_detail"] = {
            "raw": detail,
            "structure": dump_structure(detail, "garmin_detail")
        }
        print(f"[garmin] detail OK — keys={len(detail)}", flush=True)

        # 3) splits
        print("[garmin] splits 호출...", flush=True)
        try:
            splits = client.get_activity_splits(activity_id)
            results["activity_splits"] = {
                "raw": splits,
                "structure": dump_structure(splits, "garmin_splits")
            }
            print(f"[garmin] splits OK", flush=True)
        except Exception as e:
            results["activity_splits"] = {"error": str(e)}
            print(f"[garmin] splits 실패: {e}", flush=True)

        # 4) HR zones
        print("[garmin] HR zones 호출...", flush=True)
        try:
            hr_zones = client.get_activity_hr_in_timezones(activity_id)
            results["hr_zones"] = {
                "raw": hr_zones,
                "structure": dump_structure(hr_zones, "garmin_hr_zones")
            }
            print(f"[garmin] HR zones OK", flush=True)
        except Exception as e:
            results["hr_zones"] = {"error": str(e)}
            print(f"[garmin] HR zones 실패: {e}", flush=True)

        # 5) weather
        print("[garmin] weather 호출...", flush=True)
        try:
            weather = client.get_activity_weather(activity_id)
            results["activity_weather"] = {
                "raw": weather,
                "structure": dump_structure(weather, "garmin_weather")
            }
            print(f"[garmin] weather OK", flush=True)
        except Exception as e:
            results["activity_weather"] = {"error": str(e)}
            print(f"[garmin] weather 실패: {e}", flush=True)

    # 6) wellness (오늘 기준)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    wellness_methods = {
        "sleep": ("get_sleep_data", yesterday),
        "hrv": ("get_hrv_data", yesterday),
        "body_battery": ("get_body_battery", yesterday),
        "stress": ("get_stress_data", yesterday),
        "respiration": ("get_respiration_data", yesterday),
        "spo2": ("get_spo2_data", yesterday),
        "training_readiness": ("get_training_readiness", yesterday),
        "body_composition": ("get_body_composition", yesterday),
        "rhr": ("get_rhr_day", yesterday),
        "max_metrics": ("get_max_metrics", yesterday),
    }
    for name, (method_name, date_arg) in wellness_methods.items():
        print(f"[garmin] {name} 호출...", flush=True)
        try:
            method = getattr(client, method_name)
            data = method(date_arg)
            results[f"wellness_{name}"] = {
                "raw": data,
                "structure": dump_structure(data, f"garmin_{name}")
            }
            print(f"[garmin] {name} OK", flush=True)
        except Exception as e:
            results[f"wellness_{name}"] = {"error": str(e)}
            print(f"[garmin] {name} 실패: {e}", flush=True)
        time.sleep(1)  # rate limit 방지

    return results

# ─── INTERVALS.ICU ──────────────────────────────────────
def verify_intervals(config):
    import httpx
    print("[intervals] 시작...", flush=True)
    intervals = config["intervals"]
    athlete_id = intervals["athlete_id"]
    api_key = intervals["api_key"]
    auth = ("API_KEY", api_key)
    base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    results = {}

    # 1) activities (최근 1건)
    print("[intervals] activities 호출...", flush=True)
    newest = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    oldest = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{base}/activities",
                         auth=auth,
                         params={"oldest": oldest, "newest": newest})
        resp.raise_for_status()
        activities = resp.json()

    if activities:
        act = activities[0]
        act_id = act.get("id")
        results["activity_list_item"] = {
            "raw": act,
            "structure": dump_structure(act, "intervals_activity")
        }
        print(f"[intervals] activity list OK — id={act_id}, keys={len(act)}", flush=True)

        # 2) single activity detail
        print("[intervals] activity detail 호출...", flush=True)
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{base}/activities/{act_id}",
                             auth=auth)
            resp.raise_for_status()
            detail = resp.json()
        results["activity_detail"] = {
            "raw": detail,
            "structure": dump_structure(detail, "intervals_detail")
        }
        print(f"[intervals] detail OK — keys={len(detail)}", flush=True)

        # 3) activity streams
        print("[intervals] streams 호출...", flush=True)
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{base}/activities/{act_id}/streams",
                                 auth=auth)
                resp.raise_for_status()
                streams = resp.json()
            if isinstance(streams, dict):
                results["streams"] = {
                    "available_keys": list(streams.keys()),
                    "structure": dump_structure(streams, "intervals_streams")
                }
            elif isinstance(streams, list):
                results["streams"] = {
                    "available_keys": [s.get("type","?") for s in streams[:20]],
                }
            print(f"[intervals] streams OK", flush=True)
        except Exception as e:
            results["streams"] = {"error": str(e)}
            print(f"[intervals] streams 실패: {e}", flush=True)

        # 4) activity power curve
        print("[intervals] power curve 호출...", flush=True)
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{base}/activities/{act_id}/power-curve",
                                 auth=auth)
                resp.raise_for_status()
                pc = resp.json()
            results["power_curve"] = {
                "structure": dump_structure(pc, "intervals_power_curve") if isinstance(pc, dict) else f"type={type(pc).__name__}, len={len(pc) if isinstance(pc,list) else 'N/A'}"
            }
            print(f"[intervals] power curve OK", flush=True)
        except Exception as e:
            results["power_curve"] = {"error": str(e)}
            print(f"[intervals] power curve 실패: {e}", flush=True)

    # 5) wellness (최근 7일)
    print("[intervals] wellness 호출...", flush=True)
    try:
        w_oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        w_newest = datetime.now().strftime("%Y-%m-%d")
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{base}/wellness",
                             auth=auth,
                             params={"oldest": w_oldest, "newest": w_newest})
            resp.raise_for_status()
            wellness = resp.json()
        if isinstance(wellness, list) and wellness:
            results["wellness"] = {
                "raw": wellness[0],
                "structure": dump_structure(wellness[0], "intervals_wellness"),
                "total_records": len(wellness)
            }
        print(f"[intervals] wellness OK — {len(wellness)} records", flush=True)
    except Exception as e:
        results["wellness"] = {"error": str(e)}
        print(f"[intervals] wellness 실패: {e}", flush=True)

    return results

# ─── MAIN ───────────────────────────────────────────────
def main():
    config = load_config()
    all_results = {}
    report_lines = []

    # Strava
    try:
        strava_results = verify_strava(config)
        all_results["strava"] = strava_results
        for endpoint, data in strava_results.items():
            if "structure" in data:
                report_lines.append(format_structure(data["structure"], f"Strava > {endpoint}"))
    except Exception as e:
        print(f"[strava] 전체 실패: {e}", flush=True)
        all_results["strava"] = {"error": str(e)}

    # Garmin
    try:
        garmin_results = verify_garmin(config)
        all_results["garmin"] = garmin_results
        for endpoint, data in garmin_results.items():
            if "structure" in data:
                report_lines.append(format_structure(data["structure"], f"Garmin > {endpoint}"))
    except Exception as e:
        print(f"[garmin] 전체 실패: {e}", flush=True)
        all_results["garmin"] = {"error": str(e)}

    # Intervals
    try:
        intervals_results = verify_intervals(config)
        all_results["intervals"] = intervals_results
        for endpoint, data in intervals_results.items():
            if "structure" in data:
                report_lines.append(format_structure(data["structure"], f"Intervals > {endpoint}"))
    except Exception as e:
        print(f"[intervals] 전체 실패: {e}", flush=True)
        all_results["intervals"] = {"error": str(e)}

    # JSON 저장 (raw 포함)
    def sanitize(obj):
        if isinstance(obj, (dict, OrderedDict)):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj[:5]]  # 리스트는 5건만
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        return str(obj)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(sanitize(all_results), f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[완료] JSON 저장: {OUTPUT_PATH}", flush=True)

    # 텍스트 리포트 저장
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report_lines))
    print(f"[완료] 리포트 저장: {REPORT_PATH}", flush=True)

if __name__ == "__main__":
    main()
