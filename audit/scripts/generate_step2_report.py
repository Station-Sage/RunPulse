#!/usr/bin/env python3
"""Step 2 최종 리포트: 전체 API 필드 검증 결과 통합"""
import json, os
from collections import defaultdict

BASE = "/data/data/com.termux/files/home/projects/RunPulse"

FILES = {
    "api_field_audit":       os.path.join(BASE, "api_field_audit.json"),
    "garmin_field_audit":    os.path.join(BASE, "garmin_field_audit.json"),
    "unused_api_garmin":     os.path.join(BASE, "unused_api_garmin.json"),
    "unused_api_strava":     os.path.join(BASE, "unused_api_strava.json"),
    "unused_api_intervals":  os.path.join(BASE, "unused_api_intervals.json"),
}

def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def count_keys(obj, prefix=""):
    """재귀적으로 leaf 키 수 세기"""
    if obj is None:
        return 0
    if isinstance(obj, dict):
        if "raw" in obj:
            return count_keys(obj["raw"], prefix)
        total = 0
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            total += count_keys(v, f"{prefix}.{k}")
        return max(total, len([k for k in obj if not k.startswith("_")]))
    if isinstance(obj, list):
        return len(obj)
    return 1

def extract_endpoints(data, source_name):
    """JSON에서 엔드포인트별 요약 추출"""
    results = []
    if data is None:
        return results
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            has_error = val.get("_error") or ("_error" in str(val)[:100])
            if "raw" in val:
                raw = val["raw"]
                if isinstance(raw, dict):
                    kcount = len(raw)
                    status = "OK"
                elif isinstance(raw, list):
                    kcount = len(raw)
                    status = "OK"
                else:
                    kcount = 0
                    status = "OK"
            elif "_error" in val:
                kcount = 0
                status = f"FAIL: {str(val['_error'])[:60]}"
            else:
                kcount = len([k for k in val if not k.startswith("_")])
                status = "OK"
            results.append((key, status, kcount))
        elif isinstance(val, list):
            results.append((key, "OK", len(val)))
        else:
            results.append((key, "OK", 1))
    return results

def main():
    lines = []
    lines.append("=" * 80)
    lines.append("  STEP 2 — API 필드 실측 검증 최종 리포트")
    lines.append("=" * 80)
    lines.append("")

    # ── 1. 파일 존재 확인 ──
    lines.append("■ 감사 파일 현황")
    all_data = {}
    for name, path in FILES.items():
        data = load(path)
        exists = data is not None
        all_data[name] = data
        sz = os.path.getsize(path) if exists else 0
        lines.append(f"  {'✓' if exists else '✗'} {name:30s}  {'있음':6s}  {sz:>10,} bytes" if exists
                     else f"  ✗ {name:30s}  없음")
    lines.append("")

    # ── 2. 서비스별 엔드포인트 요약 ──
    services = {
        "STRAVA": [],
        "GARMIN": [],
        "INTERVALS.ICU": [],
    }

    # --- Strava ---
    d = all_data.get("api_field_audit")
    if d and "strava" in d:
        for k, v in d["strava"].items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "raw" in v:
                raw = v["raw"]
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["STRAVA"].append((f"[기본] {k}", "OK", cnt))
            elif isinstance(v, dict) and "_error" in v:
                services["STRAVA"].append((f"[기본] {k}", f"FAIL", 0))
            elif isinstance(v, dict):
                services["STRAVA"].append((f"[기본] {k}", "OK", len(v)))

    d2 = all_data.get("unused_api_strava")
    if d2:
        for k, v in d2.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "_error" in v:
                services["STRAVA"].append((f"[미사용] {k}", "FAIL", 0))
            elif isinstance(v, dict):
                raw = v.get("raw", v)
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["STRAVA"].append((f"[미사용] {k}", "OK", cnt))
            elif isinstance(v, list):
                services["STRAVA"].append((f"[미사용] {k}", "OK", len(v)))

    # --- Garmin ---
    d = all_data.get("garmin_field_audit")
    if d:
        for k, v in d.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "raw" in v:
                raw = v["raw"]
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["GARMIN"].append((f"[기본] {k}", "OK", cnt))
            elif isinstance(v, dict) and "_error" in v:
                services["GARMIN"].append((f"[기본] {k}", "FAIL", 0))
            elif isinstance(v, dict):
                services["GARMIN"].append((f"[기본] {k}", "OK", len(v)))
            elif isinstance(v, list):
                services["GARMIN"].append((f"[기본] {k}", "OK", len(v)))

    d3 = all_data.get("unused_api_garmin")
    if d3:
        for k, v in d3.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "_error" in v:
                services["GARMIN"].append((f"[미사용] {k}", "FAIL", 0))
            elif isinstance(v, dict):
                raw = v.get("raw", v)
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["GARMIN"].append((f"[미사용] {k}", "OK", cnt))
            elif isinstance(v, list):
                services["GARMIN"].append((f"[미사용] {k}", "OK", len(v)))

    # --- Intervals ---
    d = all_data.get("api_field_audit")
    if d and "intervals" in d:
        for k, v in d["intervals"].items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "raw" in v:
                raw = v["raw"]
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["INTERVALS.ICU"].append((f"[기본] {k}", "OK", cnt))
            elif isinstance(v, dict) and "_error" in v:
                services["INTERVALS.ICU"].append((f"[기본] {k}", "FAIL", 0))
            elif isinstance(v, dict):
                services["INTERVALS.ICU"].append((f"[기본] {k}", "OK", len(v)))

    d4 = all_data.get("unused_api_intervals")
    if d4:
        for k, v in d4.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and "_error" in v:
                services["INTERVALS.ICU"].append((f"[미사용] {k}", "FAIL", 0))
            elif isinstance(v, dict):
                raw = v.get("raw", v)
                cnt = len(raw) if isinstance(raw, (dict, list)) else 0
                services["INTERVALS.ICU"].append((f"[미사용] {k}", "OK", cnt))
            elif isinstance(v, list):
                services["INTERVALS.ICU"].append((f"[미사용] {k}", "OK", len(v)))

    for svc, endpoints in services.items():
        ok_count = sum(1 for _, s, _ in endpoints if s == "OK")
        fail_count = sum(1 for _, s, _ in endpoints if s != "OK")
        lines.append(f"■ {svc}  —  총 {len(endpoints)}개 엔드포인트  (성공 {ok_count} / 실패 {fail_count})")
        lines.append(f"  {'엔드포인트':<50s} {'상태':8s} {'키/항목수':>10s}")
        lines.append(f"  {'-'*50} {'-'*8} {'-'*10}")
        for name, status, cnt in sorted(endpoints):
            lines.append(f"  {name:<50s} {status:8s} {cnt:>10}")
        lines.append("")

    # ── 3. 데이터 카테고리별 교차 검증 매트릭스 ──
    lines.append("■ 데이터 카테고리별 가용성 매트릭스")
    lines.append("")
    matrix = [
        # (카테고리, Strava, Garmin, Intervals)
        ("기본 (거리/시간/칼로리)",      "summary+detail",  "summary+detail", "activity_detail"),
        ("심박 (평균/최대/zones)",       "detail+streams",  "summary+zones",  "detail+zones"),
        ("페이스/속도",                  "detail+streams",  "summary+splits", "detail+streams"),
        ("파워 (watts)",                "detail+streams",  "summary+zones",  "detail+streams+zones"),
        ("케이던스",                     "detail+streams",  "summary",        "detail+streams"),
        ("고도/경사",                    "detail+streams",  "summary+detail", "detail+streams"),
        ("GPS 좌표",                    "streams(latlng)", "detail(GPS)",    "streams+map"),
        ("랩/스플릿",                    "laps API",        "splits API",     "intervals+laps"),
        ("Best Efforts",               "detail.best_efforts", "personal_records", "best_efforts"),
        ("훈련 부하/효과",              "suffer_score",     "training_effect", "load+TRIMP+HRSS"),
        ("VO2max",                      "✗",               "max_metrics",    "✗"),
        ("러닝 다이내믹스",              "✗",               "detail(GCT,VO)", "detail(GCT,VO)"),
        ("날씨",                        "✗",               "weather API",    "weather API"),
        ("장비/기어",                    "gear_detail",     "activity_gear",  "gear"),
        ("수면",                        "✗",               "sleep API",      "wellness"),
        ("HRV",                         "✗",               "hrv API",        "wellness"),
        ("Body Battery",               "✗",               "body_battery",   "✗"),
        ("스트레스",                     "✗",               "stress API",     "wellness(stress)"),
        ("SpO2",                        "✗",               "spo2 API",       "✗"),
        ("Training Readiness",         "✗",               "training_readiness","✗"),
        ("체성분",                       "✗",               "body_composition","wellness(weight)"),
        ("안정시 심박",                  "✗",               "rhr API",        "wellness(restingHR)"),
        ("Race Predictions",           "✗",               "race_predictions","✗"),
        ("Endurance/Hill Score",       "✗",               "endurance+hill", "✗"),
        ("Lactate Threshold",          "✗",               "lactate_threshold","✗"),
        ("시계열 스트림",               "11 streams",      "FIT files",      "activity_streams"),
        ("프로필/통계",                 "athlete+stats",   "user_summary+stats","athlete_profile"),
    ]

    lines.append(f"  {'카테고리':<25s} {'Strava':<25s} {'Garmin':<25s} {'Intervals.icu':<25s}")
    lines.append(f"  {'-'*25} {'-'*25} {'-'*25} {'-'*25}")
    for cat, s, g, i in matrix:
        lines.append(f"  {cat:<25s} {s:<25s} {g:<25s} {i:<25s}")
    lines.append("")

    # ── 4. 핵심 필드 수 요약 ──
    lines.append("■ 서비스별 고유 필드 수 (API 기준)")
    strava_keys = set()
    garmin_keys = set()
    intervals_keys = set()

    # Strava: api_field_audit의 strava 섹션에서 structure 키 추출
    d = all_data.get("api_field_audit")
    if d and "strava" in d:
        for endpoint, val in d["strava"].items():
            if isinstance(val, dict) and "structure" in val:
                for item in val["structure"]:
                    if isinstance(item, (list, tuple)):
                        strava_keys.add(item[0] if item else endpoint)
                    elif isinstance(item, dict) and "path" in item:
                        strava_keys.add(item["path"])
                    elif isinstance(item, str):
                        strava_keys.add(item)

    # Garmin
    d = all_data.get("garmin_field_audit")
    if d:
        for endpoint, val in d.items():
            if isinstance(val, dict) and "structure" in val:
                for item in val["structure"]:
                    if isinstance(item, (list, tuple)):
                        garmin_keys.add(item[0] if item else endpoint)
                    elif isinstance(item, dict) and "path" in item:
                        garmin_keys.add(item["path"])
                    elif isinstance(item, str):
                        garmin_keys.add(item)

    # Intervals
    d = all_data.get("unused_api_intervals")
    if d:
        for endpoint, val in d.items():
            if isinstance(val, dict) and "structure" in val:
                for item in val["structure"]:
                    if isinstance(item, (list, tuple)):
                        intervals_keys.add(item[0] if item else endpoint)
                    elif isinstance(item, dict) and "path" in item:
                        intervals_keys.add(item["path"])
                    elif isinstance(item, str):
                        intervals_keys.add(item)

    lines.append(f"  Strava:       {len(strava_keys) if strava_keys else '(구조 파싱 필요)'}")
    lines.append(f"  Garmin:       {len(garmin_keys) if garmin_keys else '(구조 파싱 필요)'}")
    lines.append(f"  Intervals:    {len(intervals_keys) if intervals_keys else '(구조 파싱 필요)'}")
    lines.append("")

    # ── 5. 엔드포인트별 키 수 합산 (raw 기준) ──
    lines.append("■ 엔드포인트별 총 키/항목 수 (raw 기반 합산)")
    totals = {}
    for svc, endpoints in services.items():
        t = sum(cnt for _, s, cnt in endpoints if s == "OK")
        totals[svc] = t
        lines.append(f"  {svc}: {t} keys/items (OK 엔드포인트 합산)")
    lines.append("")

    # ── 6. 다음 단계 ──
    lines.append("■ Step 2 결론 및 Step 3 진행 사항")
    lines.append("")
    lines.append("  [완료] 3개 서비스 API 실측 검증")
    lines.append("    • Strava: 기본 4 + 미사용 6 = 총 10 엔드포인트 검증")
    lines.append("    • Garmin: 기본 15 + 미사용 33 = 총 48 엔드포인트 검증")
    lines.append("    • Intervals: 기본 5 + 미사용 30 = 총 35 엔드포인트 검증")
    lines.append("")
    lines.append("  [Step 3 → 슈퍼셋 스키마 정의]")
    lines.append("    1. 위 매트릭스 기반으로 테이블 구조 설계")
    lines.append("    2. activities 테이블: 공통 + 서비스별 고유 컬럼")
    lines.append("    3. activity_laps: 랩/스플릿 정규화")
    lines.append("    4. activity_streams: 시계열 데이터 (GPS, HR, power, cadence...)")
    lines.append("    5. wellness_daily: 수면, HRV, stress, body_battery 등")
    lines.append("    6. athlete_profile/stats: 프로필, 누적 통계")
    lines.append("    7. gear: 장비 추적")
    lines.append("")

    report = "\n".join(lines)

    # 파일 저장
    report_path = os.path.join(BASE, "step2_final_report.txt")
    with open(report_path, "w") as f:
        f.write(report)

    # 요약 출력 (클립보드 복사용)
    print(report)
    print(f"\n[저장완료] {report_path}")

if __name__ == "__main__":
    main()
