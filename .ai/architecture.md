# RunPulse - 아키텍처

## 데이터 흐름

    [Garmin Watch]
         |
         v
    [Garmin Connect] ---> [Strava] ---> [Intervals.icu]
         |                    |                |
         v                    v                v
    [garmin.py]          [strava.py]     [intervals.py]     [runalyze.py]
         |                    |                |                  |
         +--------------------+----------------+------------------+
                              |
                              v
                     [dedup.py - 중복 매칭]
                              |
                              v
                     [running.db (SQLite)]
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
           [analyze.py]  [plan.py]   [serve.py]
                 |            |            |
                 v            v            v
           [마크다운       [훈련 계획]  [웹 대시보드
            리포트]                     localhost:8080]
                 |            |
                 v            v
           [클립보드 복사 -> Genspark AI Chat]

## DB 스키마 (SQLite: running.db)

### activities 테이블
주요 필드: id, source(garmin|strava|intervals|runalyze), source_id,
activity_type, start_time, distance_km, duration_sec, avg_pace_sec_km,
avg_hr, max_hr, avg_cadence, elevation_gain, calories,
description, matched_group_id, created_at

### source_metrics 테이블
활동 ID별 각 소스 고유 지표 저장.
주요 필드: id, activity_id, source, metric_name, metric_value, metric_json

예시:
- garmin: training_effect=3.2, training_load=156, vo2max=48.5
- strava: suffer_score=87, segment_prs=3, stream_file=streams/12345.json
- intervals: ctl=42.3, atl=55.1, tsb=-12.8, hrss=95
- runalyze: effective_vo2max=47.8, vdot=44.2, trimp=120

### daily_wellness 테이블
주요 필드: id, date, source, sleep_score, sleep_hours, hrv_value,
resting_hr, body_battery, stress_avg, readiness_score

### planned_workouts 테이블
주요 필드: id, date, workout_type(easy|tempo|interval|long|rest),
distance_km, target_pace_min, target_pace_max, target_hr_zone,
description, rationale, completed(0|1), matched_activity_id

### goals 테이블
주요 필드: id, name, race_date, distance_km, target_time_sec,
target_pace_sec_km, status(active|completed|cancelled), created_at

## 중복 매칭 규칙
동일 활동 판별: start_time 차이 5분 이내 AND distance_km 차이 3퍼센트 이내.
매칭된 활동들은 같은 matched_group_id를 공유한다.
리포트 생성 시 그룹 내 모든 소스의 고유 지표를 병합하여 표시한다.

## 설정 파일
config.json (gitignore 대상):
- garmin: email, password
- strava: client_id, client_secret, refresh_token, access_token, expires_at
- intervals: athlete_id, api_key
- runalyze: token
