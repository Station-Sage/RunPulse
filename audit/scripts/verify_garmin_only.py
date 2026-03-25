#!/usr/bin/env python3
"""Garmin API만 단독 검증 — 토큰 경로 수정 후 재시도"""
import json, os, sys, time
from datetime import datetime, timedelta

CONFIG_PATH = "/data/data/com.termux/files/home/projects/RunPulse/config.json"
OUTPUT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/garmin_field_audit.json"
REPORT_PATH = "/data/data/com.termux/files/home/projects/RunPulse/garmin_field_audit.txt"

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
    return results

def format_structure(structure, title):
    lines = [f"\n{'='*70}", f"  {title}", f"{'='*70}"]
    for path, typ, sample in structure:
        sample_str = f"  ex: {sample}" if sample else ""
        lines.append(f"  {path:<60} {typ:<15}{sample_str}")
    return "\n".join(lines)

def main():
    from garminconnect import Garmin

    config = load_config()
    garmin_cfg = config["garmin"]
    tokenstore = garmin_cfg.get("tokenstore", "")

    print(f"[garmin] tokenstore: {tokenstore}", flush=True)
    print(f"[garmin] 토큰 파일 존재: {os.path.exists(os.path.join(tokenstore, 'oauth1_token.json'))}", flush=True)

    # 토큰 로그인
    try:
        client = Garmin()
        client.login(tokenstore=tokenstore)
        print("[garmin] 토큰 로그인 성공", flush=True)
    except Exception as e:
        print(f"[garmin] 토큰 로그인 실패: {e}", flush=True)
        print("[garmin] 이메일/패스워드 로그인 시도...", flush=True)
        client = Garmin(garmin_cfg["email"], garmin_cfg["password"])
        client.login()
        os.makedirs(tokenstore, exist_ok=True)
        client.garth.dump(tokenstore)
        print("[garmin] 로그인 성공, 토큰 저장 완료", flush=True)

    results = {}
    report_lines = []

    # 1) activity summary
    print("[garmin] activity summary...", flush=True)
    summaries = client.get_activities(0, 1)
    if summaries:
        s = summaries[0]
        aid = s.get("activityId")
        results["activity_summary"] = {"raw": s, "structure": dump_structure(s, "garmin_summary")}
        report_lines.append(format_structure(results["activity_summary"]["structure"], "Garmin > activity_summary"))
        print(f"[garmin] summary OK — id={aid}, keys={len(s)}", flush=True)

        # 2) activity detail
        print("[garmin] activity detail...", flush=True)
        detail = client.get_activity(aid)
        results["activity_detail"] = {"raw": detail, "structure": dump_structure(detail, "garmin_detail")}
        report_lines.append(format_structure(results["activity_detail"]["structure"], "Garmin > activity_detail"))
        print(f"[garmin] detail OK — keys={len(detail)}", flush=True)

        # 3) splits
        print("[garmin] splits...", flush=True)
        try:
            splits = client.get_activity_splits(aid)
            results["splits"] = {"raw": splits, "structure": dump_structure(splits, "garmin_splits")}
            report_lines.append(format_structure(results["splits"]["structure"], "Garmin > splits"))
            print(f"[garmin] splits OK", flush=True)
        except Exception as e:
            print(f"[garmin] splits 실패: {e}", flush=True)

        # 4) HR zones
        print("[garmin] HR timezones...", flush=True)
        try:
            hrzones = client.get_activity_hr_in_timezones(aid)
            results["hr_zones"] = {"raw": hrzones, "structure": dump_structure(hrzones, "garmin_hr_zones")}
            report_lines.append(format_structure(results["hr_zones"]["structure"], "Garmin > hr_zones"))
            print(f"[garmin] HR zones OK", flush=True)
        except Exception as e:
            print(f"[garmin] HR zones 실패: {e}", flush=True)

        # 5) weather
        print("[garmin] weather...", flush=True)
        try:
            weather = client.get_activity_weather(aid)
            results["weather"] = {"raw": weather, "structure": dump_structure(weather, "garmin_weather")}
            report_lines.append(format_structure(results["weather"]["structure"], "Garmin > weather"))
            print(f"[garmin] weather OK", flush=True)
        except Exception as e:
            print(f"[garmin] weather 실패: {e}", flush=True)

        time.sleep(2)

    # 6) wellness — 어제 날짜
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    wellness_methods = [
        ("sleep", "get_sleep_data"),
        ("hrv", "get_hrv_data"),
        ("body_battery", "get_body_battery"),
        ("stress", "get_stress_data"),
        ("respiration", "get_respiration_data"),
        ("spo2", "get_spo2_data"),
        ("training_readiness", "get_training_readiness"),
        ("body_composition", "get_body_composition"),
        ("rhr", "get_rhr_day"),
        ("max_metrics", "get_max_metrics"),
    ]
    for name, method_name in wellness_methods:
        print(f"[garmin] wellness/{name}...", flush=True)
        try:
            data = getattr(client, method_name)(yesterday)
            results[f"wellness_{name}"] = {"raw": data, "structure": dump_structure(data, f"garmin_{name}")}
            report_lines.append(format_structure(results[f"wellness_{name}"]["structure"], f"Garmin > wellness_{name}"))
            print(f"[garmin] {name} OK — keys={len(data) if isinstance(data, dict) else 'list'}", flush=True)
        except Exception as e:
            print(f"[garmin] {name} 실패: {e}", flush=True)
        time.sleep(1)

    # 저장
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj[:5]]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        return str(obj)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(sanitize(results), f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[완료] JSON: {OUTPUT_PATH}", flush=True)

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report_lines))
    print(f"[완료] 리포트: {REPORT_PATH}", flush=True)

if __name__ == "__main__":
    main()
