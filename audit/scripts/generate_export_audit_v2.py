import csv, os, gzip, json, zipfile
from collections import Counter
from datetime import datetime

BASE = "/data/data/com.termux/files/home/projects/RunPulse"
STRAVA_DIR = f"{BASE}/audit/export_data/strava"
GARMIN_CSV = "/sdcard/Download/garmin_running_20231029.csv"
INTERVALS_CSV = "/sdcard/Download/i268037_activities.csv"
OUT = f"{BASE}/audit/reports/step2_export_audit_report.txt"

lines = []
def w(s=""): lines.append(s)

w("=" * 72)
w("RunPulse Step 2 — Export 데이터 실측 감사 보고서")
w(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("=" * 72)

# ───────────────────────────────────────────
# 1. STRAVA EXPORT
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("1. STRAVA EXPORT (export_127496686.zip)")
w("─" * 72)

# 1-1. ZIP 전체 구성
zip_path = "/sdcard/Download/export_127496686.zip"
zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
w(f"\n1-1. ZIP 파일 정보")
w(f"  경로: {zip_path}")
w(f"  크기: {zip_size:,} bytes ({zip_size/1024/1024:.1f} MB)")

# count files by extension from extracted dir
ext_count = Counter()
all_files = []
for root, dirs, fnames in os.walk(STRAVA_DIR):
    for fn in fnames:
        fp = os.path.join(root, fn)
        all_files.append(fp)
        ext = fn.split(".")[-1].lower() if "." in fn else "no_ext"
        if fn.endswith(".gpx.gz"):
            ext = "gpx.gz"
        elif fn.endswith(".tcx.gz"):
            ext = "tcx.gz"
        ext_count[ext] += 1

w(f"  총 파일 수: {len(all_files)}")
w(f"  파일 유형별:")
for ext, cnt in sorted(ext_count.items(), key=lambda x: -x[1]):
    w(f"    .{ext}: {cnt}")

# 1-2. Root-level CSVs
w(f"\n1-2. Root CSV 파일 상세")
root_csvs = sorted([f for f in os.listdir(STRAVA_DIR) if f.endswith(".csv")])
csv_details = {}
for fn in root_csvs:
    fp = os.path.join(STRAVA_DIR, fn)
    try:
        with open(fp, "r", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        csv_details[fn] = {"columns": len(header), "rows": rows, "header": header}
        w(f"  {fn}: {len(header)} columns, {rows} rows")
    except Exception as e:
        w(f"  {fn}: 읽기 실패 ({e})")

# 1-3. activities.csv 상세 분석
w(f"\n1-3. activities.csv 컬럼 상세 (Fill Rate 분석)")
act_fp = os.path.join(STRAVA_DIR, "activities.csv")
if os.path.exists(act_fp):
    with open(act_fp, "r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        fill_counts = {h: 0 for h in header}
        total_rows = 0
        sample_vals = {h: "" for h in header}
        for row in reader:
            total_rows += 1
            for h in header:
                v = row.get(h, "").strip()
                if v:
                    fill_counts[h] += 1
                    if not sample_vals[h]:
                        sample_vals[h] = v[:50]

    w(f"  총 행: {total_rows}, 총 컬럼: {len(header)}")
    w(f"  {'#':<4} {'컬럼명':<40} {'채움률':>8} {'샘플값'}")
    w(f"  {'─'*4} {'─'*40} {'─'*8} {'─'*40}")

    high, med, low, empty_cols = 0, 0, 0, 0
    for i, h in enumerate(header):
        rate = fill_counts[h] / total_rows * 100 if total_rows else 0
        tag = "■" if rate > 90 else ("◆" if rate > 50 else ("▲" if rate > 0 else "✗"))
        if rate > 90: high += 1
        elif rate > 50: med += 1
        elif rate > 0: low += 1
        else: empty_cols += 1
        w(f"  {i+1:<4} {h:<40} {rate:>6.1f}% {tag} {sample_vals[h]}")

    w(f"\n  채움률 요약: 높음(>90%) {high}, 중간(50-90%) {med}, 낮음(<50%) {low}, 비어있음 {empty_cols}")

# 1-4. Other CSV contents
w(f"\n1-4. 기타 Strava CSV 파일 상세")
for fn in root_csvs:
    if fn == "activities.csv":
        continue
    info = csv_details.get(fn, {})
    header = info.get("header", [])
    w(f"\n  [{fn}] ({info.get('columns',0)} cols, {info.get('rows',0)} rows)")
    if header:
        w(f"  컬럼: {', '.join(header)}")

# 1-5. Activities folder (GPX/TCX) 분석
w(f"\n1-5. Activities 폴더 (개별 활동 파일)")
act_dir = os.path.join(STRAVA_DIR, "activities")
gpx_files, gpx_gz, tcx_gz, other_act = [], [], [], []
if os.path.exists(act_dir):
    for fn in os.listdir(act_dir):
        if fn.endswith(".gpx.gz"): gpx_gz.append(fn)
        elif fn.endswith(".gpx"): gpx_files.append(fn)
        elif fn.endswith(".tcx.gz"): tcx_gz.append(fn)
        else: other_act.append(fn)

w(f"  GPX: {len(gpx_files)}, GPX.GZ: {len(gpx_gz)}, TCX.GZ: {len(tcx_gz)}, 기타: {len(other_act)}")
w(f"  총: {len(gpx_files)+len(gpx_gz)+len(tcx_gz)+len(other_act)}")

# Sample GPX fields
sample_gpx = None
if gpx_files:
    sample_gpx = os.path.join(act_dir, gpx_files[0])
elif gpx_gz:
    sample_gpx = os.path.join(act_dir, gpx_gz[0])

if sample_gpx:
    w(f"\n  샘플 GPX 분석: {os.path.basename(sample_gpx)}")
    try:
        if sample_gpx.endswith(".gz"):
            import gzip as gz
            content = gz.open(sample_gpx, "rt", encoding="utf-8").read(5000)
        else:
            content = open(sample_gpx, "r", encoding="utf-8").read(5000)
        # extract tag names
        import re
        tags = set(re.findall(r"<([a-zA-Z:]+)", content))
        w(f"  발견된 XML 태그: {', '.join(sorted(tags))}")
        # check for extensions
        has_hr = "hr" in content.lower() or "heartrate" in content.lower()
        has_cad = "cad" in content.lower() or "cadence" in content.lower()
        has_power = "power" in content.lower() or "watts" in content.lower()
        w(f"  HR: {'있음' if has_hr else '없음'}, Cadence: {'있음' if has_cad else '없음'}, Power: {'있음' if has_power else '없음'}")
    except Exception as e:
        w(f"  GPX 읽기 실패: {e}")

# Sample TCX fields
if tcx_gz:
    tcx_sample = os.path.join(act_dir, tcx_gz[0])
    w(f"\n  샘플 TCX 분석: {os.path.basename(tcx_sample)}")
    try:
        content = gzip.open(tcx_sample, "rt", encoding="utf-8").read(8000)
        import re
        tags = set(re.findall(r"<([a-zA-Z:]+)", content))
        w(f"  발견된 XML 태그: {', '.join(sorted(tags))}")
        has_hr = "HeartRateBpm" in content or "heartrate" in content.lower()
        has_cad = "Cadence" in content or "RunCadence" in content
        has_speed = "Speed" in content or "speed" in content
        has_power = "Watts" in content or "power" in content.lower()
        w(f"  HR: {'있음' if has_hr else '없음'}, Cadence: {'있음' if has_cad else '없음'}, Speed: {'있음' if has_speed else '없음'}, Power: {'있음' if has_power else '없음'}")
        # extract Lap-level fields
        lap_tags = re.findall(r"<(TotalTimeSeconds|DistanceMeters|MaximumSpeed|Calories|AverageHeartRateBpm|MaximumHeartRateBpm)", content)
        w(f"  Lap 수준 필드: {', '.join(sorted(set(lap_tags)))}")
    except Exception as e:
        w(f"  TCX 읽기 실패: {e}")

# ───────────────────────────────────────────
# 2. GARMIN EXPORT
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("2. GARMIN EXPORT (garmin_running_20231029.csv)")
w("─" * 72)
if os.path.exists(GARMIN_CSV):
    gsize = os.path.getsize(GARMIN_CSV)
    w(f"  경로: {GARMIN_CSV}")
    w(f"  크기: {gsize:,} bytes ({gsize/1024:.1f} KB)")
    with open(GARMIN_CSV, "r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        gheader = reader.fieldnames or []
        gfill = {h: 0 for h in gheader}
        gsample = {h: "" for h in gheader}
        gtotal = 0
        for row in reader:
            gtotal += 1
            for h in gheader:
                v = row.get(h, "").strip()
                if v:
                    gfill[h] += 1
                    if not gsample[h]:
                        gsample[h] = v[:50]

    w(f"  총 행: {gtotal}, 총 컬럼: {len(gheader)}")
    w(f"\n  {'#':<4} {'컬럼명':<35} {'채움률':>8} {'샘플값'}")
    w(f"  {'─'*4} {'─'*35} {'─'*8} {'─'*40}")

    gh, gm, gl, ge = 0, 0, 0, 0
    for i, h in enumerate(gheader):
        rate = gfill[h] / gtotal * 100 if gtotal else 0
        tag = "■" if rate > 90 else ("◆" if rate > 50 else ("▲" if rate > 0 else "✗"))
        if rate > 90: gh += 1
        elif rate > 50: gm += 1
        elif rate > 0: gl += 1
        else: ge += 1
        w(f"  {i+1:<4} {h:<35} {rate:>6.1f}% {tag} {gsample[h]}")

    w(f"\n  채움률 요약: 높음 {gh}, 중간 {gm}, 낮음 {gl}, 비어있음 {ge}")
else:
    w("  파일 없음")

# ───────────────────────────────────────────
# 3. INTERVALS.ICU EXPORT
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("3. INTERVALS.ICU EXPORT (i268037_activities.csv)")
w("─" * 72)
if os.path.exists(INTERVALS_CSV):
    isize = os.path.getsize(INTERVALS_CSV)
    w(f"  경로: {INTERVALS_CSV}")
    w(f"  크기: {isize:,} bytes ({isize/1024:.1f} KB)")
    with open(INTERVALS_CSV, "r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        iheader = reader.fieldnames or []
        ifill = {h: 0 for h in iheader}
        isample = {h: "" for h in iheader}
        itotal = 0
        for row in reader:
            itotal += 1
            for h in iheader:
                v = row.get(h, "").strip()
                if v:
                    ifill[h] += 1
                    if not isample[h]:
                        isample[h] = v[:50]

    w(f"  총 행: {itotal}, 총 컬럼: {len(iheader)}")
    w(f"\n  {'#':<4} {'컬럼명':<45} {'채움률':>8} {'샘플값'}")
    w(f"  {'─'*4} {'─'*45} {'─'*8} {'─'*40}")

    ih, im, il, ie = 0, 0, 0, 0
    for i, h in enumerate(iheader):
        rate = ifill[h] / itotal * 100 if itotal else 0
        tag = "■" if rate > 90 else ("◆" if rate > 50 else ("▲" if rate > 0 else "✗"))
        if rate > 90: ih += 1
        elif rate > 50: im += 1
        elif rate > 0: il += 1
        else: ie += 1
        w(f"  {i+1:<4} {h:<45} {rate:>6.1f}% {tag} {isample[h]}")

    w(f"\n  채움률 요약: 높음 {ih}, 중간 {im}, 낮음 {il}, 비어있음 {ie}")
else:
    w("  파일 없음")

# ───────────────────────────────────────────
# 4. CROSS-SERVICE COMPARISON
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("4. EXPORT 데이터 서비스간 비교")
w("─" * 72)

w(f"\n  {'항목':<25} {'Strava':<15} {'Garmin':<15} {'Intervals':<15}")
w(f"  {'─'*25} {'─'*15} {'─'*15} {'─'*15}")
w(f"  {'총 활동 수':<25} {'490':<15} {str(gtotal):<15} {str(itotal):<15}")
w(f"  {'CSV 컬럼 수':<25} {'101':<15} {str(len(gheader)):<15} {str(len(iheader)):<15}")
w(f"  {'활동 상세 파일':<25} {'487 (GPX/TCX)':<15} {'없음':<15} {'없음':<15}")
w(f"  {'기타 CSV':<25} {str(len(root_csvs)-1):<15} {'0':<15} {'0':<15}")

# field category mapping
categories = {
    "식별자": {"s": ["Activity ID"], "g": ["활동 종류"], "i": ["id", "type"]},
    "날짜/시간": {"s": ["Activity Date"], "g": ["날짜"], "i": ["start_date_local"]},
    "거리": {"s": ["Distance"], "g": ["거리"], "i": ["distance"]},
    "시간/Duration": {"s": ["Elapsed Time", "Moving Time"], "g": ["시간", "경과 시간"], "i": ["moving_time", "elapsed_time"]},
    "심박수": {"s": ["Average Heart Rate", "Max Heart Rate"], "g": ["평균 심박", "최고 심박"], "i": ["average_heartrate", "max_heartrate"]},
    "케이던스": {"s": ["Average Cadence"], "g": ["평균 달리기 케이던스", "최고 달리기 케이던스"], "i": ["average_cadence"]},
    "속도/페이스": {"s": ["Average Speed", "Max Speed"], "g": ["평균 페이스", "최고 페이스", "평균 속도", "최고 속도"], "i": ["average_speed", "max_speed", "pace"]},
    "칼로리": {"s": ["Calories"], "g": ["칼로리"], "i": ["calories"]},
    "고도": {"s": ["Elevation Gain", "Elevation Loss"], "g": ["총 상승 고도", "총 하강 고도"], "i": ["total_elevation_gain"]},
    "파워": {"s": ["Average Watts", "Max Watts"], "g": ["평균 파워", "최고 파워"], "i": ["average_watts", "max_watts", "weighted_average_watts"]},
    "훈련부하": {"s": ["Relative Effort"], "g": ["Training Effect (유산소)", "Training Effect (무산소)"], "i": ["icu_training_load", "icu_atl", "icu_ctl"]},
    "GPS": {"s": ["활동 파일 (GPX/TCX)"], "g": ["없음"], "i": ["없음"]},
    "날씨": {"s": ["Weather Temperature"], "g": ["없음 (API만)"], "i": ["없음"]},
    "장비": {"s": ["Gear"], "g": ["없음"], "i": ["gear_id"]},
}

w(f"\n  카테고리별 데이터 가용성:")
w(f"  {'카테고리':<20} {'Strava':<5} {'Garmin':<5} {'Intervals':<5}")
w(f"  {'─'*20} {'─'*5} {'─'*5} {'─'*5}")
for cat in categories:
    sc = "✓" if any(c in (csv_details.get("activities.csv",{}).get("header",[])) for c in categories[cat]["s"]) else "△"
    gc = "✓" if gheader and any(c in gheader for c in categories[cat]["g"]) else "✗"
    ic = "✓" if iheader and any(c in iheader for c in categories[cat]["i"]) else "✗"
    # override for non-csv fields
    if cat == "GPS": sc, gc, ic = "✓(파일)", "✗", "✗"
    if cat == "날씨": sc, gc, ic = ("✓" if "Weather Temperature" in (csv_details.get("activities.csv",{}).get("header",[])) else "✗"), "✗", "✗"
    if cat == "장비": sc = "✓" if "Gear" in (csv_details.get("activities.csv",{}).get("header",[])) else "✗"
    w(f"  {cat:<20} {sc:<5} {gc:<5} {ic:<5}")

# ───────────────────────────────────────────
# 5. EXPORT vs API 비교
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("5. EXPORT vs API 데이터 비교")
w("─" * 72)

w("""
  Strava:
    - CSV (101 cols) vs API (summary 57 + detail 73 + streams 11 types)
    - CSV 고유: 파일명, 미디어타입, Commute, From Upload, Perceived Exertion
    - API 고유: best_efforts, splits_metric, segment_efforts, map polyline,
                detailed streams (latlng, altitude, heartrate, cadence, watts, etc.)
    - GPX/TCX (487 files): lat/lon/ele/time/hr/cad/speed → API streams와 동등
    - 기타 CSV: bikes.csv(장비), global_challenges.csv(챌린지) 등

  Garmin:
    - CSV (38 cols, 한국어 헤더) vs API (102+ keys + wellness + body composition)
    - CSV 고유: 없음 (CSV는 API 서브셋)
    - API 고유: HR zones, splits, weather, GPS coordinates, device info,
                wellness (수면, 스트레스, 체중), body composition, training status

  Intervals.icu:
    - CSV (86 cols) vs API (173+ keys + streams + intervals)
    - CSV 고유: zone별 초(s1-s6 fields), CSV용 계산 필드
    - API 고유: streams (time-series), intervals/laps 상세, weather,
                power curve, HR curve, best efforts, fitness model
""")

# ───────────────────────────────────────────
# 6. Strava 기타 CSV 데이터 가치
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("6. STRAVA 기타 EXPORT 파일 데이터 가치 평가")
w("─" * 72)

strava_extras = {
    "bikes.csv": "장비(자전거/신발) 정보 → gear 테이블에 반영",
    "global_challenges.csv": "챌린지 참여 이력 → 선택적 (분석 가치 낮음)",
    "starred_routes.csv": "즐겨찾기 경로 → 선택적",
    "starred_segments.csv": "즐겨찾기 구간 → 선택적",
    "clubs.csv": "클럽 정보 → 스키마 불필요",
    "profile.csv": "프로필 → athlete_profile에 반영",
    "media/": "사진/동영상 → 별도 관리",
    "structured_details.csv": "활동 구조화 정보 → 확인 필요",
    "visibility_settings.csv": "공개설정 → 스키마 불필요",
}
for fn, desc in strava_extras.items():
    exists = "✓" if fn in root_csvs or os.path.isdir(os.path.join(STRAVA_DIR, fn.rstrip("/"))) else "?"
    w(f"  {exists} {fn:<30} {desc}")

# ───────────────────────────────────────────
# 7. 스키마 설계 권장사항
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("7. 스키마 설계 권장사항 (Export 기반)")
w("─" * 72)
w("""
  7-1. activities 테이블
    - Strava CSV 101 컬럼 전체 수용 (채움률 높은 ~40개 우선)
    - Garmin CSV 38 컬럼 매핑 (한국어→영문 변환)
    - Intervals CSV 86 컬럼 매핑
    - source_service 컬럼으로 출처 구분

  7-2. activity_streams 테이블 (시계열)
    - GPX/TCX 파싱: timestamp, lat, lon, elevation, hr, cadence, speed
    - API streams: + watts, temperature, grade_smooth, distance
    - FIT 파일: record 메시지 → 동일 스키마

  7-3. activity_laps 테이블
    - TCX Lap 데이터: total_time, distance, max_speed, calories, avg_hr, max_hr, cadence
    - API laps: + power, elevation, pace
    - Intervals API: 22 laps with detailed metrics

  7-4. gear 테이블
    - Strava bikes.csv: id, name, brand_name(?), distance
    - Intervals gear_id 연결
    - 신발/장비 구분 필드

  7-5. athlete_profile 테이블
    - Strava profile.csv 필드
    - API 보완

  7-6. wellness_daily 테이블
    - Garmin API만 (Export에 없음)

  7-7. activity_weather 테이블
    - Garmin API / Intervals API (Export에 없음)
""")

# ───────────────────────────────────────────
# 8. 결론
# ───────────────────────────────────────────
w("\n" + "─" * 72)
w("8. 결론")
w("─" * 72)
w(f"""
  Export 실측 감사 완료:
    - Strava: activities.csv (101 cols, 490 rows) + 기타 CSV 다수 + 활동파일 487개
    - Garmin: garmin_running_20231029.csv (38 cols, {gtotal} rows)
    - Intervals.icu: i268037_activities.csv (86 cols, {itotal} rows)
    - FIT 파일: 0개 (별도 다운로드 필요)

  핵심 발견:
    1. CSV는 API의 서브셋 — API 스키마를 기본으로 하되 CSV 고유 필드 추가
    2. GPX/TCX(487개)는 시계열 데이터의 주요 소스
    3. Strava bikes.csv에서 장비 정보 확보 가능
    4. Garmin CSV는 한국어 헤더 → 영문 매핑 테이블 필요
    5. Intervals CSV는 zone별 초 데이터 등 고유 필드 포함

  다음 단계: Step 3 (슈퍼셋 스키마 정의)
    - API 감사 + Export 감사 결과를 통합하여 최종 스키마 설계
""")

# Save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print(f"보고서 저장: {OUT}")
print(f"총 {len(lines)} 줄")

# Also save column inventory JSON
inventory = {
    "generated": datetime.now().isoformat(),
    "strava_csv": {
        "file": "activities.csv",
        "columns": csv_details.get("activities.csv", {}).get("header", []),
        "rows": 490,
        "other_csvs": {fn: {"columns": d["header"], "rows": d["rows"]} for fn, d in csv_details.items() if fn != "activities.csv"},
        "activity_files": {"gpx": len(gpx_files), "gpx_gz": len(gpx_gz), "tcx_gz": len(tcx_gz), "other": len(other_act)}
    },
    "garmin_csv": {
        "file": "garmin_running_20231029.csv",
        "columns": list(gheader) if 'gheader' in dir() else [],
        "rows": gtotal
    },
    "intervals_csv": {
        "file": "i268037_activities.csv",
        "columns": list(iheader) if 'iheader' in dir() else [],
        "rows": itotal
    }
}
inv_out = f"{BASE}/audit/reports/export_column_inventory.json"
with open(inv_out, "w", encoding="utf-8") as fh:
    json.dump(inventory, fh, ensure_ascii=False, indent=2)
print(f"컬럼 인벤토리 저장: {inv_out}")

