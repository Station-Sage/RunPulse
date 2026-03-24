"""RunPulse 전체 데이터 파이프라인 감사 — 0단계: API 현황 파악"""
import sqlite3, json

conn = sqlite3.connect("running.db")

print("=" * 70)
print("0. 각 서비스별 API endpoint & 데이터 항목 현황")
print("=" * 70)

# ── Garmin: 사용 중인 API ──
print("""
[Garmin Connect — garminconnect 라이브러리]
사용 중 API:
  1. client.get_activities(start, limit) → 활동 목록
  2. client.get_activity(id) → 활동 상세 (summaryDTO, splitSummaries)
  3. client.get_sleep_data(date) → 수면
  4. client.get_hrv_data(date) → HRV
  5. client.get_body_battery(date) → Body Battery
  6. client.get_stress_data(date) → 스트레스
  7. client.get_respiration_data(date) → 호흡
  8. client.get_spo2_data(date) → SpO2
  9. client.get_training_readiness(date) → 훈련 준비도
  10. client.get_body_composition(date) → 체성분
  11. client.get_rhr_day(date) → 안정시 심박
  12. client.get_max_metrics(date) → VO2max 등 [추가 예정]

미사용 가능 API:
  - client.get_activity_splits(id) → 킬로미터별 스플릿
  - client.get_activity_hr_in_timezones(id) → HR 존별 시간
  - client.get_activity_weather(id) → 날씨
  - client.get_floors(date) → 층수
  - client.get_steps_data(date) → 걸음수 상세
  - client.get_heart_rates(date) → 심박수 타임라인
""")

# ── Strava: 사용 중인 API ──
print("""
[Strava API v3]
사용 중 API:
  1. GET /athlete/activities → 활동 목록
  2. GET /activities/{id} → 활동 상세 (laps, splits, best_efforts, segment_efforts)
  3. GET /activities/{id}/streams → 타임시리즈 (HR, pace, cadence, altitude)

미사용 가능 API:
  - GET /activities/{id}/laps → 별도 랩 endpoint (detail에 포함되긴 함)
  - GET /activities/{id}/zones → HR/Power 존 분석
  - GET /athlete → 프로필 (weight, ftp)
  - GET /athlete/zones → 개인 존 설정
  - GET /segments/{id} → 세그먼트 상세
""")

# ── Intervals.icu: 사용 중인 API ──
print("""
[Intervals.icu API v1]
사용 중 API:
  1. GET /athlete/{id}/activities → 활동 목록 (173개 필드!)
  2. GET /athlete/{id}/wellness → 웰니스 (수면, HRV, 체중, vo2max 등)
  3. GET /athlete/{id} → 프로필/연결 확인

미사용 가능 API:
  - GET /athlete/{id}/activities/{id}/streams → 타임시리즈
  - GET /athlete/{id}/activities/{id}/intervals → 인터벌 상세
  - GET /athlete/{id}/activities/{id}/laps → 랩 상세
  - GET /athlete/{id}/athlete-settings → FTP/LTHR/zones 설정
  - GET /athlete/{id}/events → 이벤트/레이스 계획
""")

# ── 실제 데이터: raw payload에서 각 서비스 키 전체 추출 ──
print("=" * 70)
print("0-1. 각 서비스 raw payload 키 분석 (실제 수신 데이터)")
print("=" * 70)

for source, etype in [("garmin","activity_summary"), ("strava","activity_summary"), ("intervals","activity")]:
    cur = conn.execute(
        "SELECT payload_json FROM raw_source_payloads WHERE source=? AND entity_type=? LIMIT 1",
        (source, etype)
    )
    row = cur.fetchone()
    if not row:
        print(f"\n  [{source}] {etype}: 없음")
        continue
    p = json.loads(row[0])
    if isinstance(p, list) and p:
        p = p[0]
    keys = sorted(p.keys())
    print(f"\n  [{source}] activity: {len(keys)}개 필드")
    
    # 카테고리별 분류
    categories = {
        "위치": [], "시간": [], "거리/페이스": [], "심박": [],
        "파워": [], "케이던스": [], "고도": [], "날씨": [],
        "훈련부하": [], "존분석": [], "FTP/VO2": [], "기타": []
    }
    for k in keys:
        kl = k.lower()
        if any(x in kl for x in ["lat", "lon", "location", "latlng", "position"]):
            categories["위치"].append(k)
        elif any(x in kl for x in ["time", "date", "duration", "elapsed", "moving"]):
            categories["시간"].append(k)
        elif any(x in kl for x in ["distance", "pace", "speed", "gap"]):
            categories["거리/페이스"].append(k)
        elif any(x in kl for x in ["hr", "heart", "pulse"]):
            categories["심박"].append(k)
        elif any(x in kl for x in ["power", "watt", "ftp", "joule"]):
            categories["파워"].append(k)
        elif any(x in kl for x in ["cadence", "stride", "step", "run_cadence"]):
            categories["케이던스"].append(k)
        elif any(x in kl for x in ["elev", "altitude", "climb", "grade"]):
            categories["고도"].append(k)
        elif any(x in kl for x in ["temp", "weather", "wind", "cloud", "rain", "snow", "humid", "uv"]):
            categories["날씨"].append(k)
        elif any(x in kl for x in ["load", "trimp", "stress", "strain", "intensity", "effect", "rpe"]):
            categories["훈련부하"].append(k)
        elif any(x in kl for x in ["zone", "tiz"]):
            categories["존분석"].append(k)
        elif any(x in kl for x in ["ftp", "vo2", "vdot", "eftp", "threshold"]):
            categories["FTP/VO2"].append(k)
        else:
            categories["기타"].append(k)
    
    for cat, cat_keys in categories.items():
        if cat_keys:
            print(f"    [{cat}] {', '.join(cat_keys)}")

# ── DB에 저장 중인 것 vs 안 하는 것 ──
print("\n" + "=" * 70)
print("0-2. 수신 데이터 vs DB 저장 매핑 GAP")
print("=" * 70)

# activity_summaries 컬럼
as_cols = set(c[1] for c in conn.execute("PRAGMA table_info(activity_summaries)").fetchall())
print(f"\n  activity_summaries 컬럼: {sorted(as_cols)}")

# 각 소스에서 매핑 안 되는 중요 필드
print("""
  [Garmin] 미저장 중요 필드:
    - splitSummaries (detail) → activity_laps에 안 넣음
    - get_activity_splits() → 호출 안 함
    - get_max_metrics() → VO2max 수집 안 함
    - endLatitude/endLongitude → 종료 위치 미저장

  [Strava] 미저장 중요 필드:
    - laps (detail) → activity_laps에 안 넣음 [Sprint5에서 추가]
    - splits_metric, splits_standard → 미저장 [Sprint5에서 추가]
    - segment_efforts → 미저장
    - average_cadence, average_watts → summary에서 미저장
    - weighted_average_watts, kilojoules → 미저장
    - gear → 미저장

  [Intervals] 미저장 중요 필드 (173개 중 ~30개만 저장):
    - icu_ftp, icu_rolling_ftp → 미저장
    - gap, threshold_pace → 미저장
    - 날씨 전체 (average_temp, wind 등) → 미저장
    - decoupling → 7건만 (1.3%)
    - polarization_index → 미저장
    - icu_efficiency_factor → 7건만 (1.3%)
""")

conn.close()
