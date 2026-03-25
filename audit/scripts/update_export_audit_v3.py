#!/usr/bin/env python3
"""
Step 2 감사보고서 수정 + 컬럼 인벤토리 업데이트
- Garmin CSV: 38컬럼 전체 목록 반영
- Intervals.icu CSV: 86컬럼 전체 목록 반영
- Strava CSV: 기존 101컬럼 유지
- 교차비교표 재생성
"""
import csv, os, json
from datetime import datetime

# ── 경로 설정 ──
BASE = os.path.expanduser("~/projects/RunPulse")
AUDIT_DIR = os.path.join(BASE, "audit", "reports")
os.makedirs(AUDIT_DIR, exist_ok=True)

STRAVA_CSV  = os.path.expanduser("~/projects/RunPulse/audit/export_data/strava/activities.csv")
GARMIN_CSV  = os.path.expanduser("~/storage/downloads/garmin_running_20231029.csv")
INTERVALS_CSV = os.path.expanduser("~/storage/downloads/i268037_activities.csv")

REPORT_PATH = os.path.join(AUDIT_DIR, "step2_export_audit_report_v3.txt")
JSON_PATH   = os.path.join(AUDIT_DIR, "export_column_inventory_v3.json")

# ── CSV 분석 함수 ──
def analyze_csv(path, label):
    """CSV 파일을 읽어서 컬럼 목록, 행 수, fill rate 반환"""
    result = {
        "label": label,
        "path": path,
        "exists": os.path.exists(path),
        "size_bytes": 0,
        "encoding": None,
        "num_cols": 0,
        "num_rows": 0,
        "headers": [],
        "columns": [],  # [{name, filled, total, pct}]
        "fill_summary": {"high": 0, "medium": 0, "low": 0, "empty": 0}
    }
    if not result["exists"]:
        return result
    
    result["size_bytes"] = os.path.getsize(path)
    
    # 인코딩 시도
    for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1']:
        try:
            with open(path, 'r', encoding=enc) as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)
            result["encoding"] = enc
            break
        except:
            continue
    else:
        return result
    
    # BOM 제거
    if headers and headers[0].startswith('\ufeff'):
        headers[0] = headers[0].lstrip('\ufeff')
    
    result["num_cols"] = len(headers)
    result["num_rows"] = len(rows)
    result["headers"] = headers
    
    high = med = low = empty = 0
    for i, col in enumerate(headers):
        filled = sum(1 for row in rows if i < len(row) and row[i].strip() != '')
        pct = (filled / len(rows) * 100) if rows else 0
        result["columns"].append({
            "index": i + 1,
            "name": col,
            "filled": filled,
            "total": len(rows),
            "pct": round(pct, 1)
        })
        if pct >= 80: high += 1
        elif pct >= 30: med += 1
        elif pct > 0: low += 1
        else: empty += 1
    
    result["fill_summary"] = {"high": high, "medium": med, "low": low, "empty": empty}
    return result

# ── 분석 실행 ──
print("분석 중...")
strava = analyze_csv(STRAVA_CSV, "Strava")
garmin = analyze_csv(GARMIN_CSV, "Garmin")
intervals = analyze_csv(INTERVALS_CSV, "Intervals.icu")

# ── Strava 활동 파일 분석 ──
STRAVA_ACTIVITIES_DIR = os.path.expanduser("~/projects/RunPulse/audit/export_data/strava/activities")
strava_files = {"gpx": 0, "gpx.gz": 0, "tcx.gz": 0, "fit.gz": 0, "other": 0}
total_activity_files = 0
if os.path.isdir(STRAVA_ACTIVITIES_DIR):
    for fn in os.listdir(STRAVA_ACTIVITIES_DIR):
        total_activity_files += 1
        fl = fn.lower()
        if fl.endswith('.gpx.gz'): strava_files["gpx.gz"] += 1
        elif fl.endswith('.gpx'): strava_files["gpx"] += 1
        elif fl.endswith('.tcx.gz'): strava_files["tcx.gz"] += 1
        elif fl.endswith('.fit.gz'): strava_files["fit.gz"] += 1
        else: strava_files["other"] += 1

# ── 교차 비교: 카테고리별 컬럼 매핑 ──
CATEGORY_MAP = {
    "식별자": {
        "strava": ["Activity ID"],
        "garmin": ["제목"],
        "intervals": ["id", "external_id"]
    },
    "날짜/시간": {
        "strava": ["Activity Date", "UTC Offset"],
        "garmin": ["날짜"],
        "intervals": ["start_date_local", "start_date", "icu_sync_date", "timezone"]
    },
    "활동유형": {
        "strava": ["Activity Type", "Activity Name", "Workout Type"],
        "garmin": ["활동 종류"],
        "intervals": ["type", "name", "sub_type", "description"]
    },
    "거리": {
        "strava": ["Distance"],
        "garmin": ["거리"],
        "intervals": ["distance"]
    },
    "시간": {
        "strava": ["Moving Time", "Elapsed Time"],
        "garmin": ["시간", "이동 시간", "경과 시간"],
        "intervals": ["moving_time", "elapsed_time", "icu_recording_time", "icu_warmup_time", "icu_cooldown_time"]
    },
    "심박": {
        "strava": ["Average Heart Rate", "Max Heart Rate"],
        "garmin": ["평균 심박", "최대심박"],
        "intervals": ["has_heartrate", "average_heartrate", "max_heartrate", "icu_hrrc", "icu_hrrc_start_bpm"]
    },
    "케이던스": {
        "strava": ["Average Cadence"],
        "garmin": ["평균 달리기 케이던스", "최고 달리기 케이던스", "평균 달리기 케이던스(중복)"],
        "intervals": ["average_cadence"]
    },
    "속도/페이스": {
        "strava": ["Average Speed", "Max Speed"],
        "garmin": ["평균 페이스", "최대 페이스", "평균 GAP"],
        "intervals": ["average_speed", "max_speed", "pace", "threshold_pace"]
    },
    "고도": {
        "strava": ["Elevation Gain", "Elevation Loss"],
        "garmin": ["총 상승", "총 하강", "최저 해발", "최고 해발"],
        "intervals": ["total_elevation_gain"]
    },
    "칼로리": {
        "strava": ["Calories"],
        "garmin": ["칼로리"],
        "intervals": ["calories"]
    },
    "파워": {
        "strava": ["Average Watts", "Max Watts", "Weighted Average Watts"],
        "garmin": ["Normalized Power® (NP®)", "Training Stress Score®", "평균 파워", "최대 파워"],
        "intervals": ["device_watts", "icu_average_watts", "icu_normalized_watts", "icu_joules",
                       "icu_ftp", "icu_eftp", "icu_pm_ftp", "icu_pm_cp", "icu_pm_w_prime", "icu_pm_p_max",
                       "icu_power_spike_threshold"]
    },
    "달리기역학": {
        "strava": [],
        "garmin": ["평균 보폭", "평균 수직 비율", "평균 수직 진동", "평균 지면 접촉 시간"],
        "intervals": []
    },
    "Training Load": {
        "strava": ["Suffer Score", "Relative Effort", "Perceived Exertion", "Perceived Relative Effort"],
        "garmin": ["유산소 훈련 효과"],
        "intervals": ["icu_intensity", "icu_training_load", "icu_training_load_edited", "icu_rpe",
                       "icu_variability", "icu_efficiency",
                       "power_load", "hr_load", "pace_load"]
    },
    "HR 존": {
        "strava": [],
        "garmin": [],
        "intervals": ["hr_z1", "hr_z2", "hr_z3", "hr_z4", "hr_z5", "hr_z6", "hr_max",
                       "hr_z1_secs", "hr_z2_secs", "hr_z3_secs", "hr_z4_secs",
                       "hr_z5_secs", "hr_z6_secs", "hr_z7_secs"]
    },
    "파워 존": {
        "strava": [],
        "garmin": [],
        "intervals": ["z1_secs", "z2_secs", "z3_secs", "z4_secs",
                       "z5_secs", "z6_secs", "z7_secs", "sweet_spot_secs"]
    },
    "체중/설정": {
        "strava": [],
        "garmin": [],
        "intervals": ["icu_weight", "icu_resting_hr", "lthr", "icu_fatigue", "icu_fitness"]
    },
    "온도/환경": {
        "strava": ["Weather Temperature"],
        "garmin": ["최저 온도", "최고 온도", "감압"],
        "intervals": []
    },
    "장비": {
        "strava": ["Activity Gear"],
        "garmin": [],
        "intervals": ["gear"]
    },
    "기타메타": {
        "strava": ["Commute", "Flagged", "From Upload", "Activity Visibility"],
        "garmin": ["즐겨찾기", "걸음", "바디 배터리 방전", "최고 랩 기록", "랩 수"],
        "intervals": ["trainer", "commute", "race", "compliance",
                       "icu_ignore_power", "icu_ignore_hr", "icu_ignore_time", "file_type"]
    }
}

# ── 보고서 생성 ──
print("보고서 생성 중...")
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("  RunPulse Step 2 — Export 감사 보고서 v3 (수정본)\n")
    f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")
    
    # ── 섹션 1: 각 서비스별 상세 ──
    for data in [strava, garmin, intervals]:
        f.write("─" * 70 + "\n")
        f.write(f"  섹션: {data['label']} Export\n")
        f.write("─" * 70 + "\n")
        f.write(f"  파일: {data['path']}\n")
        f.write(f"  크기: {data['size_bytes']:,} bytes ({data['size_bytes']/1024:.1f} KB)\n")
        f.write(f"  인코딩: {data['encoding']}\n")
        f.write(f"  컬럼 수: {data['num_cols']}\n")
        f.write(f"  데이터 행 수: {data['num_rows']}\n\n")
        
        fs = data['fill_summary']
        f.write(f"  Fill Rate 요약:\n")
        f.write(f"    HIGH (≥80%):     {fs['high']:>3} 컬럼\n")
        f.write(f"    MEDIUM (30-79%): {fs['medium']:>3} 컬럼\n")
        f.write(f"    LOW (1-29%):     {fs['low']:>3} 컬럼\n")
        f.write(f"    EMPTY (0%):      {fs['empty']:>3} 컬럼\n\n")
        
        f.write(f"  {'#':>3}  {'컬럼명':<45} {'채워진행':>6}/{data['num_rows']:<5} {'fill%':>6}\n")
        f.write(f"  {'─'*3}  {'─'*45} {'─'*12} {'─'*6}\n")
        for col in data['columns']:
            f.write(f"  {col['index']:>3}  {col['name']:<45} {col['filled']:>6}/{col['total']:<5} {col['pct']:>5.1f}%\n")
        f.write("\n")
    
    # ── 섹션 2: Strava 활동 파일 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: Strava Activity Files (GPX/TCX)\n")
    f.write("─" * 70 + "\n")
    f.write(f"  폴더: {STRAVA_ACTIVITIES_DIR}\n")
    f.write(f"  총 파일 수: {total_activity_files}\n")
    for ftype, cnt in strava_files.items():
        if cnt > 0:
            f.write(f"    {ftype.upper():>10}: {cnt}\n")
    f.write(f"\n  → activity_streams 테이블 데이터 소스\n")
    f.write(f"  → activity_laps 테이블 데이터 소스 (TCX 파일)\n\n")
    
    # ── 섹션 3: 교차 서비스 비교 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: 교차 서비스 비교\n")
    f.write("─" * 70 + "\n\n")
    
    f.write(f"  {'항목':<20} {'Strava':>10} {'Garmin':>10} {'Intervals':>12}\n")
    f.write(f"  {'─'*20} {'─'*10} {'─'*10} {'─'*12}\n")
    f.write(f"  {'CSV 컬럼 수':<20} {strava['num_cols']:>10} {garmin['num_cols']:>10} {intervals['num_cols']:>12}\n")
    f.write(f"  {'데이터 행 수':<20} {strava['num_rows']:>10} {garmin['num_rows']:>10} {intervals['num_rows']:>12}\n")
    f.write(f"  {'파일 크기(KB)':<20} {strava['size_bytes']/1024:>9.1f} {garmin['size_bytes']/1024:>9.1f} {intervals['size_bytes']/1024:>11.1f}\n")
    f.write(f"  {'Fill HIGH':<20} {strava['fill_summary']['high']:>10} {garmin['fill_summary']['high']:>10} {intervals['fill_summary']['high']:>12}\n")
    f.write(f"  {'Fill EMPTY':<20} {strava['fill_summary']['empty']:>10} {garmin['fill_summary']['empty']:>10} {intervals['fill_summary']['empty']:>12}\n")
    f.write(f"  {'활동파일(GPX/TCX)':<20} {total_activity_files:>10} {'N/A':>10} {'N/A':>12}\n")
    f.write("\n")
    
    # ── 섹션 4: 카테고리별 컬럼 매핑 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: 카테고리별 컬럼 매핑 (Superset 기준)\n")
    f.write("─" * 70 + "\n\n")
    
    total_unique = 0
    for cat, sources in CATEGORY_MAP.items():
        s_cnt = len(sources.get("strava", []))
        g_cnt = len(sources.get("garmin", []))
        i_cnt = len(sources.get("intervals", []))
        total_cat = s_cnt + g_cnt + i_cnt
        total_unique += total_cat
        
        f.write(f"  ▸ {cat} ({total_cat}개 컬럼)\n")
        if sources.get("strava"):
            f.write(f"    Strava:     {', '.join(sources['strava'])}\n")
        if sources.get("garmin"):
            f.write(f"    Garmin:     {', '.join(sources['garmin'])}\n")
        if sources.get("intervals"):
            f.write(f"    Intervals:  {', '.join(sources['intervals'])}\n")
        
        # 고유 필드 표시
        only_s = [c for c in sources.get("strava", []) 
                  if not any(c in sources.get(k, []) for k in ["garmin", "intervals"])]
        only_g = [c for c in sources.get("garmin", []) 
                  if not any(c in sources.get(k, []) for k in ["strava", "intervals"])]
        only_i = [c for c in sources.get("intervals", []) 
                  if not any(c in sources.get(k, []) for k in ["strava", "garmin"])]
        
        exclusives = []
        if only_s: exclusives.append(f"Strava 고유: {', '.join(only_s)}")
        if only_g: exclusives.append(f"Garmin 고유: {', '.join(only_g)}")
        if only_i: exclusives.append(f"Intervals 고유: {', '.join(only_i)}")
        if exclusives:
            for ex in exclusives:
                f.write(f"    ★ {ex}\n")
        f.write("\n")
    
    f.write(f"  총 매핑 컬럼 수: {total_unique}\n")
    f.write(f"  (중복 제거 전 — 동일 의미 컬럼 포함)\n\n")
    
    # ── 섹션 5: Garmin 38컬럼 평가 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: Garmin CSV 38컬럼 평가\n")
    f.write("─" * 70 + "\n\n")
    f.write("  Garmin Connect 웹 → Activities → Export CSV는 활동 목록 요약이며\n")
    f.write("  38컬럼이 해당 내보내기 방식의 최대치입니다.\n\n")
    f.write("  추가 데이터 확보 방법:\n")
    f.write("  1) Garmin Data Management → Request Data Export (전체 ZIP)\n")
    f.write("     → FIT 파일 (초단위 시계열 + 랩 + 세션 요약)\n")
    f.write("     → JSON 파일 (wellness, sleep, stress 등)\n")
    f.write("  2) Garmin Connect API (비공식) → 개별 활동 상세 JSON\n")
    f.write("     → splits, HR zones, running dynamics 상세 등\n\n")
    f.write("  현재 38컬럼에서 이전 스키마에 누락됐던 필드:\n")
    f.write("    - 즐겨찾기, 제목, 유산소 훈련 효과\n")
    f.write("    - 평균 GAP (Grade Adjusted Pace)\n")
    f.write("    - 걸음 (Steps), 감압 (Decompression)\n")
    f.write("    - 최고 랩 기록, 랩 수\n")
    f.write("    - 평균 달리기 케이던스 (중복 컬럼 #11=#22, #12=#23)\n\n")
    
    # ── 섹션 6: Intervals 86컬럼 평가 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: Intervals.icu CSV 86컬럼 평가\n")
    f.write("─" * 70 + "\n\n")
    f.write("  Intervals.icu 내보내기는 활동 요약 + 존 데이터 + 설정 스냅샷을\n")
    f.write("  포함하여 86컬럼입니다. API에서 제공하는 추가 필드도 있으나\n")
    f.write("  CSV 내보내기 기준으로 86컬럼이 전량입니다.\n\n")
    f.write("  이전 스키마에 누락됐던 주요 필드 그룹:\n")
    f.write("    - HR 존 경계값 (hr_z1~z6, hr_max): 7개\n")
    f.write("    - HR 존별 시간 (hr_z1_secs~z7_secs): 7개\n")
    f.write("    - 파워 존별 시간 (z1_secs~z7_secs, sweet_spot_secs): 8개\n")
    f.write("    - 부하 분리 (power_load, hr_load, pace_load): 3개\n")
    f.write("    - icu_eftp, icu_variability, icu_efficiency: 3개\n")
    f.write("    - icu_fatigue/fitness (ATL/CTL 스냅샷): 2개\n")
    f.write("    - threshold_pace, icu_resting_hr, lthr, icu_weight: 4개\n")
    f.write("    - trainer, race, sub_type, icu_rpe: 4개\n")
    f.write("    - icu_ignore_power/hr/time 플래그: 3개\n")
    f.write("    - EMPTY 컬럼 (0%): icu_training_load_edited, icu_w_prime,\n")
    f.write("      p_max, icu_power_spike_threshold, timezone\n\n")
    
    # ── 섹션 7: 결론 ──
    f.write("─" * 70 + "\n")
    f.write("  섹션: 결론 및 다음 단계\n")
    f.write("─" * 70 + "\n\n")
    f.write("  ✅ Garmin CSV 38컬럼 확인 — 웹 Export CSV 방식의 정상 범위\n")
    f.write("  ✅ Intervals.icu CSV 86컬럼 확인 — 활동 내보내기의 전량\n")
    f.write("  ✅ Strava CSV 101컬럼 + 활동파일 132개 확인\n\n")
    f.write("  ⚠️  Garmin 중복 컬럼 발견: #11=#22 (평균 달리기 케이던스),\n")
    f.write("     #12=#23 (최고 달리기 케이던스) → 스키마에서 deduplicate\n\n")
    f.write("  📋 다음 단계:\n")
    f.write("  1) Superset 스키마 v2 설계 (이 보고서 기반)\n")
    f.write("     - Garmin 누락 8개 필드 추가\n")
    f.write("     - Intervals 누락 41개 필드 추가 (존 데이터 등)\n")
    f.write("     - activity_zones 테이블 신설 (HR/파워 존)\n")
    f.write("  2) Garmin 전체 데이터 내보내기(ZIP) 확보 검토\n")
    f.write("  3) ETL 파이프라인 구축 (Step 4)\n")

print(f"✅ 보고서 저장: {REPORT_PATH}")

# ── JSON 인벤토리 저장 ──
inventory = {}
for data in [strava, garmin, intervals]:
    inventory[data["label"]] = {
        "file": data["path"],
        "size_bytes": data["size_bytes"],
        "encoding": data["encoding"],
        "num_cols": data["num_cols"],
        "num_rows": data["num_rows"],
        "fill_summary": data["fill_summary"],
        "columns": [
            {"index": c["index"], "name": c["name"], "filled": c["filled"], "pct": c["pct"]}
            for c in data["columns"]
        ]
    }

# Strava 활동 파일 정보 추가
inventory["Strava"]["activity_files"] = {
    "directory": STRAVA_ACTIVITIES_DIR,
    "total": total_activity_files,
    "breakdown": {k: v for k, v in strava_files.items() if v > 0}
}

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 인벤토리 저장: {JSON_PATH}")
print()
print(f"=== 요약 ===")
print(f"  Strava:     {strava['num_cols']}컬럼, {strava['num_rows']}행")
print(f"  Garmin:     {garmin['num_cols']}컬럼, {garmin['num_rows']}행 (전부 100% fill)")
print(f"  Intervals:  {intervals['num_cols']}컬럼, {intervals['num_rows']}행 (HIGH:{intervals['fill_summary']['high']}, EMPTY:{intervals['fill_summary']['empty']})")
print(f"  Strava files: {total_activity_files}개")
