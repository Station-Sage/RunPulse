#!/usr/bin/env python3
"""audit_export_keys.py — Export 데이터 컬럼 전수 조사 (v3)"""
import sqlite3, json, os
from collections import Counter

DB_PATH = os.path.expanduser("~/projects/RunPulse/running.db")

def section(title):
    print(f"\n{'='*70}\n  {title}\n{'='*70}", flush=True)

def get_payloads(cur, source, entity_type):
    cur.execute("SELECT payload_json FROM raw_source_payloads WHERE source = ? AND entity_type = ?", (source, entity_type))
    results = []
    for (blob,) in cur.fetchall():
        try:
            results.append(json.loads(blob))
        except:
            pass
    return results

def analyze_keys(payloads):
    all_keys = set()
    key_non_null = Counter()
    key_samples = {}
    total = 0
    for p in payloads:
        items = [p] if isinstance(p, dict) else (p if isinstance(p, list) else [])
        for item in items:
            if not isinstance(item, dict):
                continue
            total += 1
            for k, v in item.items():
                all_keys.add(k)
                if v is not None and v != '' and str(v) != 'None':
                    key_non_null[k] += 1
                    if k not in key_samples:
                        key_samples[k] = str(v)[:60]
    print(f"\n  총 레코드: {total}, 고유 키: {len(all_keys)}", flush=True)
    print(f"  {'키':<50} {'비null':>6} {'%':>6}  샘플값", flush=True)
    print(f"  {'-'*50} {'-'*6} {'-'*6}  {'-'*40}", flush=True)
    for k in sorted(all_keys):
        cnt = key_non_null.get(k, 0)
        pct = cnt / total * 100 if total > 0 else 0
        print(f"  {k:<50} {cnt:>6} {pct:>5.1f}%  {key_samples.get(k, '')}", flush=True)
    return all_keys

def get_all_keys(cur, source, entity_type):
    payloads = get_payloads(cur, source, entity_type)
    keys = set()
    for p in payloads:
        if isinstance(p, dict):
            keys.update(p.keys())
    return keys

def compare_keys(export_keys, api_keys):
    only_export = export_keys - api_keys
    only_api = api_keys - export_keys
    common = export_keys & api_keys
    print(f"\n  공통: {len(common)}, Export전용: {len(only_export)}, API전용: {len(only_api)}", flush=True)
    if only_export:
        print(f"  Export에만 있는 키:", flush=True)
        for k in sorted(only_export):
            print(f"    + {k}", flush=True)
    if only_api:
        print(f"  API에만 있는 키:", flush=True)
        for k in sorted(only_api):
            print(f"    - {k}", flush=True)

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    section("0. raw_source_payloads 현황")
    cur.execute("SELECT source, entity_type, COUNT(*) FROM raw_source_payloads GROUP BY source, entity_type ORDER BY source, entity_type")
    for src, etype, cnt in cur.fetchall():
        print(f"  {src:<12} {etype:<30} {cnt:>5}건", flush=True)

    section("1. Strava CSV Export")
    strava_csv_keys = analyze_keys(get_payloads(cur, 'strava', 'csv_export'))

    section("1-1. Strava CSV vs API")
    strava_api_all = get_all_keys(cur, 'strava', 'activity_summary') | get_all_keys(cur, 'strava', 'activity_detail')
    if strava_csv_keys and strava_api_all:
        compare_keys(strava_csv_keys, strava_api_all)

    section("2. Intervals CSV Export")
    intervals_csv_keys = analyze_keys(get_payloads(cur, 'intervals', 'csv_export'))
    if not intervals_csv_keys:
        cur.execute("SELECT DISTINCT entity_type FROM raw_source_payloads WHERE source = 'intervals'")
        print(f"  Intervals entity types: {[r[0] for r in cur.fetchall()]}", flush=True)

    section("2-1. Intervals CSV vs API")
    intervals_api_keys = get_all_keys(cur, 'intervals', 'activity')
    if intervals_csv_keys and intervals_api_keys:
        compare_keys(intervals_csv_keys, intervals_api_keys)

    section("3. FIT Export 메타데이터 (샘플 3건)")
    fit_payloads = get_payloads(cur, 'intervals', 'fit_export')
    print(f"  총 {len(fit_payloads)}건", flush=True)
    for i, p in enumerate(fit_payloads[:3]):
        if isinstance(p, dict):
            print(f"  [{i}] keys: {sorted(p.keys())}", flush=True)
        else:
            print(f"  [{i}] type: {type(p).__name__}, len: {len(str(p)[:100])}", flush=True)

    section("4. Garmin 전체 entity_type별 키")
    cur.execute("SELECT DISTINCT entity_type FROM raw_source_payloads WHERE source = 'garmin'")
    for (etype,) in cur.fetchall():
        payloads = get_payloads(cur, 'garmin', etype)
        keys = set()
        for p in payloads:
            if isinstance(p, dict):
                keys.update(p.keys())
            elif isinstance(p, list) and p and isinstance(p[0], dict):
                keys.update(p[0].keys())
        print(f"\n  {etype} ({len(payloads)}건, {len(keys)}개 키):", flush=True)
        for k in sorted(keys):
            print(f"    {k}", flush=True)

    section("5. Strava API detail/summary 키")
    for etype in ['activity_summary', 'activity_detail']:
        keys = get_all_keys(cur, 'strava', etype)
        payloads = get_payloads(cur, 'strava', etype)
        print(f"\n  {etype} ({len(payloads)}건, {len(keys)}개 키):", flush=True)
        for k in sorted(keys):
            print(f"    {k}", flush=True)

    section("6. Intervals API activity 키")
    keys = get_all_keys(cur, 'intervals', 'activity')
    payloads = get_payloads(cur, 'intervals', 'activity')
    print(f"\n  activity ({len(payloads)}건, {len(keys)}개 키):", flush=True)
    for k in sorted(keys):
        print(f"    {k}", flush=True)

    section("끝")
    conn.close()

if __name__ == '__main__':
    main()
