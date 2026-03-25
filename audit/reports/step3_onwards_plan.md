# RunPulse — Step 2 이후 작업 계획

작성일: 2026-03-24

## 진행 상태

| Step | 내용 | 상태 |
|------|------|------|
| 2 | API 필드 실측 검증 | ✅ 완료 (93개 엔드포인트, 1,708키) |
| 3 | 슈퍼셋 스키마 정의 | 🔜 다음 |
| 4 | ALTER TABLE 및 백필 | ⏳ 대기 |
| 1 | CSV/GPX/TCX/FIT 파싱·로드 | ⏳ 대기 |

---

## Step 3: 슈퍼셋 스키마 정의

### 목표
Step 2에서 확인한 3개 서비스(Strava/Garmin/Intervals.icu)의 전체 API 필드를
하나의 통합 DB 스키마로 설계한다.

### 선행 작업
1. 현재 DB 스키마 확인 (테이블, 컬럼, 행 수)
2. 현재 DB 컬럼 vs Step 2 감사 필드 갭 분석

### 설계할 테이블
1. **activities** — 활동 요약 (슈퍼셋)
   - 공통: id, source, date, type, distance, duration, calories, HR, speed, power, cadence, elevation, gear
   - Strava 고유: suffer_score, kudos, comments, segment_efforts, polyline
   - Garmin 고유: training_effect, vo2max, running_dynamics, training_load
   - Intervals 고유: icu_training_load, trimp, hrss, gap, decoupling, efficiency_factor, zone_times

2. **activity_laps** — 랩/스플릿/인터벌
   - source, activity_id, lap_index, distance, duration, HR, speed, power, cadence, elevation

3. **activity_streams** — 시계열 데이터
   - activity_id, elapsed_sec, lat, lon, altitude, heartrate, cadence, power, speed, grade, temperature

4. **activity_best_efforts** — 베스트 노력
   - activity_id, name, distance, elapsed_time, pr_rank

5. **wellness_daily** — 일별 건강 데이터
   - date, sleep, hrv, resting_hr, body_battery, stress, spo2, training_readiness, weight, steps, atl, ctl, tsb

6. **gear** — 장비
   - id, source, brand, model, name, distance, retired

7. **athlete_profile** — 프로필/설정
   - source, ftp, lthr, max_hr, weight, zones

8. **activity_weather** — 활동별 날씨
   - activity_id, temperature, humidity, wind, conditions, uv, pressure

### 산출물
- `docs/step3_superset_schema.sql` — CREATE TABLE 문
- `docs/step3_schema_design.md` — 설계 근거 문서
- 컬럼 매핑 테이블 (서비스별 필드 → 스키마 컬럼)

---

## Step 4: ALTER TABLE 및 백필

### 목표
기존 DB에 Step 3 스키마를 적용하고, 이미 수집된 데이터를 재매핑한다.

### 작업 내용
1. 기존 테이블 vs 신규 스키마 diff 생성
2. ALTER TABLE / CREATE TABLE 마이그레이션 스크립트 작성
3. 기존 데이터 백필 (컬럼 매핑 적용)
4. 데이터 무결성 검증

### 선행 작업
- Step 3 완료
- 기존 DB 백업

### 산출물
- `migrations/001_superset_schema.sql` — 마이그레이션 SQL
- `src/migrate.py` — 마이그레이션 실행 스크립트

---

## Step 1: CSV/GPX/TCX/FIT 파싱·로드

### 목표
Export 파일과 API 데이터를 신규 스키마에 맞춰 파싱하고 로드한다.

### 작업 내용
1. Export 파일 수집 (기기로 가져오기)
   - Strava: activities.csv + activities/ 폴더 (GPX/TCX)
   - Garmin: CSV export
   - Intervals: CSV export + FIT files
2. CSV 파서 구현/수정 (101/38/86 컬럼 전체 임포트)
3. GPX/TCX 파서 → activity_streams 테이블
4. FIT 파서 (fitparse) → activities + activity_laps + activity_streams
5. API 데이터 재수집
   - Strava API detail: 나머지 488건
   - Garmin API summary/detail: 나머지 468건
   - Intervals API: ~526건 (API 키 재발급 필요)
   - Garmin wellness: 전체 재수집
6. 교차 검증 (같은 활동의 서비스간 데이터 비교)

### 선행 작업
- Step 4 완료 (스키마 적용됨)
- Export 파일 기기 배치
- Intervals.icu API 키 재발급

### 산출물
- `src/import_export/` 파서 모듈들
- `src/sync/` 수정된 동기화 모듈들
- 데이터 로드 완료 보고서

---

## 알려진 이슈 (해결 필요)

| # | 이슈 | 해결 시점 | 방법 |
|---|------|-----------|------|
| 1 | Intervals.icu API 키 만료 (403) | Step 1 전 | Settings > Developer Settings 재발급 |
| 2 | Export 파일 미존재 | Step 1 전 | 각 서비스에서 export 다운로드 |
| 3 | Strava zones 402 (Premium) | - | Intervals zones로 대체 |
| 4 | Garmin 일부 메서드 파라미터 불일치 | Step 1 | garminconnect 업데이트 또는 수동 보정 |
| 5 | Garmin tokenstore 경로 (Windows→Termux) | ✅ 해결 | .garmin_tokens로 수정됨 |
