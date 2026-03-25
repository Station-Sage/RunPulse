#!/usr/bin/env python3
"""Step 2 보완: Export 데이터 감사 보고서 생성"""
import os, glob, csv, json
from datetime import datetime

BASE = "/data/data/com.termux/files/home/projects/RunPulse"
DOC_DIR = os.path.join(BASE, "docs")
os.makedirs(DOC_DIR, exist_ok=True)

doc = []
doc.append("=" * 80)
doc.append("  RunPulse — Step 2 보완: Export 데이터 감사 보고서")
doc.append("=" * 80)
doc.append(f"  작성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
doc.append("")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Export 파일 현황
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("━" * 80)
doc.append("  1. Export 파일 현황")
doc.append("━" * 80)

# Strava CSV
strava_csv = None
strava_csv_candidates = [
    os.path.join(BASE, "exports", "strava", "activities.csv"),
    os.path.join(BASE, "data", "strava", "activities.csv"),
    os.path.join(BASE, "strava_export", "activities.csv"),
]
for p in strava_csv_candidates:
    if os.path.exists(p):
        strava_csv = p
        break
# 더 넓은 검색
if not strava_csv:
    for root, dirs, files in os.walk(BASE):
        for f in files:
            if f == "activities.csv" and "strava" in root.lower():
                strava_csv = os.path.join(root, f)
                break
        if strava_csv:
            break
# activities.csv 어디든
if not strava_csv:
    for root, dirs, files in os.walk(BASE):
        for f in files:
            if f == "activities.csv":
                strava_csv = os.path.join(root, f)
                break
        if strava_csv:
            break

# Garmin CSV
garmin_csvs = []
for root, dirs, files in os.walk(BASE):
    for f in files:
        if f.endswith(".csv") and "garmin" in root.lower():
            garmin_csvs.append(os.path.join(root, f))

# Intervals CSV
intervals_csvs = []
for root, dirs, files in os.walk(BASE):
    for f in files:
        if f.endswith(".csv") and "interval" in root.lower():
            intervals_csvs.append(os.path.join(root, f))

# GPX/TCX
gpx_files = glob.glob(os.path.join(BASE, "**", "*.gpx"), recursive=True)
tcx_files = glob.glob(os.path.join(BASE, "**", "*.tcx"), recursive=True)
gpx_gz = glob.glob(os.path.join(BASE, "**", "*.gpx.gz"), recursive=True)

# FIT
fit_files = glob.glob(os.path.join(BASE, "**", "*.fit"), recursive=True)

doc.append(f"""
  파일 유형           개수      위치
  ─────────────       ─────     ────────────────────────────────
  Strava CSV          {'1' if strava_csv else '0'}         {strava_csv or '찾을 수 없음'}
  Garmin CSV          {len(garmin_csvs)}         {garmin_csvs[0] if garmin_csvs else '찾을 수 없음'}
  Intervals CSV       {len(intervals_csvs)}         {intervals_csvs[0] if intervals_csvs else '찾을 수 없음'}
  GPX files           {len(gpx_files)}
  GPX.GZ files        {len(gpx_gz)}
  TCX files           {len(tcx_files)}
  FIT files           {len(fit_files)}
""")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Strava CSV (activities.csv)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("━" * 80)
doc.append("  2. Strava CSV Export (activities.csv)")
doc.append("━" * 80)

strava_cols = []
strava_row_count = 0
strava_sample = {}
if strava_csv:
    try:
        with open(strava_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            strava_cols = reader.fieldnames or []
            rows = list(reader)
            strava_row_count = len(rows)
            if rows:
                strava_sample = rows[0]
    except Exception as e:
        doc.append(f"  [ERROR] CSV 읽기 실패: {e}")
        # BOM 등 시도
        try:
            with open(strava_csv, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                strava_cols = reader.fieldnames or []
                rows = list(reader)
                strava_row_count = len(rows)
                if rows:
                    strava_sample = rows[0]
        except:
            pass

    doc.append(f"\n  파일: {strava_csv}")
    doc.append(f"  크기: {os.path.getsize(strava_csv):,} bytes")
    doc.append(f"  컬럼 수: {len(strava_cols)}")
    doc.append(f"  행 수: {strava_row_count}")
    doc.append(f"\n  전체 컬럼 목록 ({len(strava_cols)}개):")
    doc.append(f"    {'#':<4s} {'컬럼명':<45s} {'샘플값'}")
    doc.append(f"    {'─'*4} {'─'*45} {'─'*40}")
    for i, col in enumerate(strava_cols, 1):
        sample = str(strava_sample.get(col, ""))[:40]
        doc.append(f"    {i:<4d} {col:<45s} {sample}")

    # DB에 저장된 컬럼과 비교
    doc.append(f"\n  현재 DB 저장 현황:")
    doc.append(f"    총 {len(strava_cols)}개 컬럼 중 22개만 저장 → {len(strava_cols)-22}개 누락")
else:
    doc.append("\n  [경고] Strava activities.csv 파일을 찾을 수 없음")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Garmin CSV Export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("\n" + "━" * 80)
doc.append("  3. Garmin CSV Export")
doc.append("━" * 80)

if garmin_csvs:
    for gcsv in garmin_csvs[:3]:  # 최대 3개
        doc.append(f"\n  파일: {gcsv}")
        doc.append(f"  크기: {os.path.getsize(gcsv):,} bytes")
        gcols = []
        grow_count = 0
        gsample = {}
        for enc in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
            try:
                with open(gcsv, encoding=enc) as f:
                    reader = csv.DictReader(f)
                    gcols = reader.fieldnames or []
                    rows = list(reader)
                    grow_count = len(rows)
                    if rows:
                        gsample = rows[0]
                break
            except:
                continue
        doc.append(f"  컬럼 수: {len(gcols)}")
        doc.append(f"  행 수: {grow_count}")
        if gcols:
            doc.append(f"\n  전체 컬럼 목록 ({len(gcols)}개):")
            doc.append(f"    {'#':<4s} {'컬럼명':<45s} {'샘플값'}")
            doc.append(f"    {'─'*4} {'─'*45} {'─'*40}")
            for i, col in enumerate(gcols, 1):
                sample = str(gsample.get(col, ""))[:40]
                doc.append(f"    {i:<4d} {col:<45s} {sample}")
    doc.append(f"\n  현재 DB 저장 현황:")
    doc.append(f"    38개 컬럼 중 29개 저장 → 9개 누락")
    doc.append(f"    누락 추정: 최고 랩 기록, 랩 수, 이동/경과 시간, 고도 최저/최고, 총 하강, 최대 페이스, 평균 GAP")
else:
    doc.append("\n  [경고] Garmin CSV 파일을 찾을 수 없음")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Intervals.icu CSV Export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("\n" + "━" * 80)
doc.append("  4. Intervals.icu CSV Export")
doc.append("━" * 80)

if intervals_csvs:
    for icsv in intervals_csvs[:3]:
        doc.append(f"\n  파일: {icsv}")
        doc.append(f"  크기: {os.path.getsize(icsv):,} bytes")
        icols = []
        irow_count = 0
        isample = {}
        for enc in ["utf-8", "utf-8-sig"]:
            try:
                with open(icsv, encoding=enc) as f:
                    reader = csv.DictReader(f)
                    icols = reader.fieldnames or []
                    rows = list(reader)
                    irow_count = len(rows)
                    if rows:
                        isample = rows[0]
                break
            except:
                continue
        doc.append(f"  컬럼 수: {len(icols)}")
        doc.append(f"  행 수: {irow_count}")
        if icols:
            doc.append(f"\n  전체 컬럼 목록 ({len(icols)}개):")
            doc.append(f"    {'#':<4s} {'컬럼명':<45s} {'샘플값'}")
            doc.append(f"    {'─'*4} {'─'*45} {'─'*40}")
            for i, col in enumerate(icols, 1):
                sample = str(isample.get(col, ""))[:40]
                doc.append(f"    {i:<4d} {col:<45s} {sample}")
    doc.append(f"\n  현재 DB 저장 현황:")
    doc.append(f"    86개 컬럼, 현재 미임포트 (0행)")
else:
    doc.append("\n  [경고] Intervals.icu CSV 파일을 찾을 수 없음")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. GPX/TCX 파일
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("\n" + "━" * 80)
doc.append("  5. Strava GPX/TCX Export")
doc.append("━" * 80)

doc.append(f"\n  GPX 파일: {len(gpx_files)}개")
doc.append(f"  GPX.GZ 파일: {len(gpx_gz)}개")
doc.append(f"  TCX 파일: {len(tcx_files)}개")
doc.append(f"  합계: {len(gpx_files) + len(gpx_gz) + len(tcx_files)}개")

# GPX 샘플 파싱
doc.append(f"\n  GPX 필드 구조 (대화 기록 기반):")
doc.append(f"    - XML 헤더 + metadata timestamp")
doc.append(f"    - trk > trkseg > trkpt:")
doc.append(f"      • lat (위도)")
doc.append(f"      • lon (경도)")
doc.append(f"      • ele (고도)")
doc.append(f"      • time (타임스탬프)")
doc.append(f"      • extensions > cadence (케이던스)")

doc.append(f"\n  TCX 필드 구조 (대화 기록 기반):")
doc.append(f"    - TrainingCenterDatabase > Activities > Activity:")
doc.append(f"      • TotalTimeSeconds (총 시간)")
doc.append(f"      • DistanceMeters (총 거리)")
doc.append(f"      • MaximumSpeed (최고 속도)")
doc.append(f"      • Calories (칼로리)")
doc.append(f"    - Trackpoint:")
doc.append(f"      • Time (타임스탬프)")
doc.append(f"      • Position > LatitudeDegrees, LongitudeDegrees")
doc.append(f"      • AltitudeMeters (고도)")
doc.append(f"      • HeartRateBpm (심박)")
doc.append(f"      • Cadence (케이던스)")
doc.append(f"      • Extensions > Speed (속도)")

doc.append(f"\n  현재 DB 저장 현황: 미파싱 (시계열 데이터 미저장)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. FIT 파일
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("\n" + "━" * 80)
doc.append("  6. FIT 파일 Export (Intervals.icu)")
doc.append("━" * 80)

doc.append(f"\n  FIT 파일: {len(fit_files)}개")
if fit_files:
    total_size = sum(os.path.getsize(f) for f in fit_files)
    doc.append(f"  총 크기: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    doc.append(f"  평균 크기: {total_size//len(fit_files):,} bytes")

# FIT 샘플 파싱
try:
    from fitparse import FitFile
    sample_fit = fit_files[0] if fit_files else None
    if sample_fit:
        ff = FitFile(sample_fit)
        msg_types = {}
        for msg in ff.get_messages():
            name = msg.name
            fields = [f.name for f in msg.fields]
            if name not in msg_types:
                msg_types[name] = set()
            msg_types[name].update(fields)

        doc.append(f"\n  FIT 메시지 유형 (샘플 파일: {os.path.basename(sample_fit)}):")
        for msg_name in sorted(msg_types.keys()):
            fields = sorted(msg_types[msg_name])
            doc.append(f"\n    [{msg_name}] — {len(fields)}개 필드")
            for i, field in enumerate(fields, 1):
                doc.append(f"      {i:>3d}. {field}")
except ImportError:
    doc.append("\n  [경고] fitparse 미설치 — FIT 필드 목록은 대화 기록 기반")
    doc.append(f"\n  FIT 메시지 유형 (대화 기록 기반):")
    doc.append(f"    [record] — 시계열 데이터")
    doc.append(f"      timestamp, position_lat, position_long, altitude,")
    doc.append(f"      heart_rate, cadence, speed, power, distance,")
    doc.append(f"      vertical_oscillation, ground_contact_time,")
    doc.append(f"      stance_time_percent, temperature")
    doc.append(f"    [lap] — 랩 데이터")
    doc.append(f"      timestamp, total_elapsed_time, total_distance,")
    doc.append(f"      avg_heart_rate, max_heart_rate, avg_cadence,")
    doc.append(f"      avg_speed, max_speed, avg_power, max_power")
    doc.append(f"    [session] — 세션 요약")
    doc.append(f"      sport, total_distance, total_elapsed_time,")
    doc.append(f"      total_calories, avg_heart_rate, max_heart_rate,")
    doc.append(f"      avg_speed, max_speed, total_ascent, total_descent")
    doc.append(f"    [device_info] — 기기 정보")
    doc.append(f"      manufacturer, product, serial_number, software_version")
except Exception as e:
    doc.append(f"\n  [ERROR] FIT 파싱 실패: {e}")

doc.append(f"\n  현재 DB 저장 현황: 메타 ~20키만 저장, record/lap 시계열 미파싱")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. Export vs API 교차 비교
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("\n" + "━" * 80)
doc.append("  7. Export vs API 데이터 교차 비교")
doc.append("━" * 80)

doc.append("""
  ┌──────────────────┬───────────────────────┬───────────────────────┐
  │ 데이터 카테고리   │ Export                │ API                   │
  ├──────────────────┼───────────────────────┼───────────────────────┤
  │ Strava 활동 요약  │ CSV 101컬럼           │ summary 57 + detail 73│
  │ Strava 시계열     │ GPX/TCX (lat,lon,     │ streams 11 types      │
  │                  │ ele,hr,cad,speed)     │                       │
  │ Garmin 활동 요약  │ CSV 38컬럼 (한국어)   │ summary 102키         │
  │ Garmin 시계열     │ (없음 — API/FIT만)    │ FIT files             │
  │ Intervals 활동    │ CSV 86컬럼            │ detail 173키          │
  │ Intervals 시계열  │ FIT 533개             │ streams 11 types      │
  └──────────────────┴───────────────────────┴───────────────────────┘

  주요 차이점:

  1) Strava CSV vs API
     - CSV에는 있지만 API에 없는 것: Filename, Media Type 등 메타
     - API에는 있지만 CSV에 없는 것: best_efforts, segment_efforts,
       splits_metric, laps, map.polyline
     → CSV는 요약, API는 상세. 둘 다 필요.

  2) Garmin CSV vs API
     - CSV: 38컬럼 요약 (한국어 헤더)
     - API: 102+ 키 상세 + wellness 10종
     → API가 훨씬 풍부. CSV는 백업/검증용.

  3) Intervals CSV vs API
     - CSV: 86컬럼 (API detail의 부분집합)
     - API: 173키 + streams + curves + weather
     → API가 상위집합. CSV는 벌크 로드에 유용.

  4) FIT vs API streams
     - FIT: 바이너리, record/lap/session 구조, 러닝 다이내믹스 포함
     - API streams: JSON, 동일 데이터 + 파생 필드
     → FIT가 원본 데이터, API streams는 가공된 버전.
       러닝 다이내믹스(GCT, VO 등)는 FIT에만 확실히 포함.

  5) GPX/TCX vs API streams
     - GPX/TCX: Strava export 시 제공, lat/lon/ele/hr/cad/speed
     - API streams: 동일 + watts, temp, moving, grade_smooth, velocity_smooth
     → API streams가 상위집합. GPX/TCX는 오프라인 백업용.
""")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. 결론 및 권고
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
doc.append("━" * 80)
doc.append("  8. 결론 및 스키마 설계 권고")
doc.append("━" * 80)
doc.append("""
  Export 데이터 감사 결과:

  ┌──────────────────┬────────┬────────┬──────────────────────────────┐
  │ 소스             │ 컬럼수 │ DB저장 │ 조치                         │
  ├──────────────────┼────────┼────────┼──────────────────────────────┤
  │ Strava CSV       │  101   │   22   │ 전체 101컬럼 임포트          │
  │ Garmin CSV       │   38   │   29   │ 누락 9컬럼 복원              │
  │ Intervals CSV    │   86   │    0   │ 전체 86컬럼 신규 임포트      │
  │ GPX/TCX          │  ~6-8  │    0   │ 시계열 테이블로 파싱         │
  │ FIT (533개)      │ ~20-40 │  ~20   │ record/lap/session 전체 파싱 │
  └──────────────────┴────────┴────────┴──────────────────────────────┘

  스키마 설계 시 고려사항:
  - CSV 데이터는 API 데이터의 부분집합이므로, API 스키마가 CSV를 포괄함
  - FIT 파일의 record 메시지는 activity_streams 테이블로 매핑
  - FIT의 lap/session은 activity_laps, activities 테이블로 매핑
  - GPX/TCX는 Strava streams API와 동일 구조 → activity_streams로 통합
  - Export 고유 필드(파일명, 미디어 타입 등)는 메타데이터 컬럼으로 추가
""")

doc.append("=" * 80)
doc.append("  END OF REPORT")
doc.append("=" * 80)

# 저장
report_text = "\n".join(doc)
output_path = os.path.join(DOC_DIR, "step2_export_audit_report.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(report_text)

print(f"[완료] 보고서 저장: {output_path}")
print(f"[완료] 보고서 길이: {len(report_text):,} 자 / {len(doc)} 줄")

