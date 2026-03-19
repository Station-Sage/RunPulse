# RunPulse - 아키텍처

## 전체 데이터 흐름

    [Garmin Watch]
         |
         v
    [Garmin Connect] ---> [Strava] ---> [Intervals.icu]
         |                    |                |
         v                    v                v             [Runalyze]
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
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    [분석 레이어]        [AI 코치 레이어]     [웹 레이어]
    (Phase 3)            (Phase 4-1)          (Phase 5)
          |                   |                   |
          v                   v                   v
    [마크다운 리포트]   [Genspark/AI Chat]   [웹 대시보드]
                              |
                              v
                     [AI 훈련 계획 JSON]
                              |
                              v
                     [워크아웃 레이어]
                     (Phase 4-2)
                              |
                              v
                     [Garmin 워크아웃 캘린더]
                              |
                              v
                     [Garmin Watch 자동 로드]

## 분석 레이어 상세 (Phase 3)

    [running.db] + [Strava Stream JSON 파일]
            |
     +------+------+------+------+------+------+
     |      |      |      |      |      |      |
     v      v      v      v      v      v      v
  compare trends recov- weekly effi-  zones  activity
  .py     .py   ery.py score  ciency _analy _deep
                        .py   .py    sis.py .py
     |      |      |      |      |      |      |
     +------+------+------+------+------+------+
                        |
              +---------+---------+
              |                   |
              v                   v
        race_readiness.py    report.py
              |                   |
              v                   v
        [레이스 준비도]    [마크다운 리포트]
                                  |
                          +-------+-------+
                          |               |
                          v               v
                   [사용자 읽기]    [AI 컨텍스트]
                   [클립보드]      [briefing.py]

### 분석 모듈 역할
- compare.py: 두 기간 비교 (거리/시간/페이스/HR + 4개 소스 고유 지표 변화량)
- trends.py: N주 롤링 추세, ACWR 부상 위험도 (4개 부하 지표 교차 검증)
- recovery.py: Garmin Body Battery/HRV/Sleep/Stress 기반 회복 점수
- weekly_score.py: 볼륨/강도/ACWR/회복/EF/일관성 종합 0-100 점수
- efficiency.py: Strava Stream으로 Aerobic EF 및 Cardiac Decoupling 계산
- zones_analysis.py: HR/Pace Zone 분포, 80/20 법칙 준수 판정
- activity_deep.py: 단일 활동 심층 (스플릿/디커플링/4소스 평가 병합)
- race_readiness.py: VO2Max추세 + VDOT + Marathon Shape + TSB 종합 레이스 준비도
- report.py: 인간용 마크다운 + AI 컨텍스트용 구조화 텍스트 이중 출력
- analyze.py: CLI 진입점 (argparse 서브커맨드)

## AI 코치 레이어 상세 (Phase 4-1)

### AI 코치 탭 진입 플로우

    [사용자: AI 코치 탭 클릭]
              |
              v (즉시)
    [briefing.py: 데이터 수집]
    - DB에서 오늘 활동 조회 (유무 분기)
    - 이번 주 누적 데이터
    - weekly_score, ACWR, recovery 등 분석 실행
              |
       +------+------+
       |             |
       v (즉시)      v (비동기)
    [suggestions.py] [브리핑 프롬프트 조립]
    규칙 기반 칩 5개   briefing.txt 템플릿 + 데이터
       |                    |
       v                    v
    [UI: 칩 즉시 표시] [프롬프트 → AI 전송]
                            |
                            v
                     [AI 응답 수신]
                            |
                     +------+------+
                     |             |
                     v             v
              [브리핑 메시지  [응답 끝 JSON 파싱]
               채팅에 표시]   {"suggestions":[...]}
                                   |
                            성공 → 칩 교체
                            실패 → 규칙 기반 유지

### 추천 칩 클릭 플로우

    [사용자: 칩 클릭 "오늘 훈련 상세 분석"]
              |
              v
    [칩 ID → 프롬프트 템플릿 매핑]
    today_deep → deep_analysis.txt
              |
              v
    [해당 분석 데이터 수집]
    activity_deep + Strava Stream
              |
              v
    [템플릿 + 데이터 → 완성 프롬프트]
              |
              v
    [프롬프트 → AI 전송]
              |
              v
    [AI 응답 → 채팅 표시 + 새 칩 갱신]

### AI 훈련 계획 수신 플로우

    [사용자: "다음 주 훈련 스케줄 만들어줘" 칩 또는 직접 요청]
              |
              v
    [ai_context.py: plan_request.txt + 4주 추세/ACWR/목표 데이터]
              |
              v
    [프롬프트 → AI 전송]
              |
              v
    [AI 응답: 훈련 계획 JSON 포함]
              |
              v
    [ai_parser.py: JSON 추출 및 ai_schema.py로 검증]
              |
         유효 → [승인 UI 표시] → 사용자 확인
              |
              v
    [workout_builder.py: Garmin Typed Workout 변환]
              |
              v
    [garmin_calendar.py: 업로드 → 스케줄 → 삭제]
              |
              v
    [Garmin Watch 싱크 시 워크아웃 자동 로드]

## 가민 워크아웃 슬롯 우회 전략 (Phase 4-2)

    워치 워크아웃 슬롯: 최대 25개
    우회: upload_running_workout() → schedule_workout(id, date) → delete_workout(id)
    캘린더 이벤트는 워크아웃 삭제 후에도 유지됨
    워치 싱크 시 해당 날짜 워크아웃 자동 로드

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
- garmin: training_effect_aerobic, training_effect_anaerobic, training_load, vo2max
- strava: relative_effort, segment_prs, best_efforts, stream_file 경로
- intervals: ctl, atl, tsb, hrss, ramp_rate, hr_zone_distribution, pace_zone_distribution
- runalyze: effective_vo2max, vdot, trimp, marathon_shape, race_pred_5k/10k/half/full

### daily_wellness 테이블
주요 필드: id, date, source, sleep_score, sleep_hours, hrv_value,
resting_hr, body_battery, stress_avg, readiness_score

### planned_workouts 테이블
주요 필드: id, date, workout_type(easy|tempo|interval|long|rest),
distance_km, target_pace_min, target_pace_max, target_hr_zone,
description, rationale, source(manual|ai), ai_model,
completed(0|1), matched_activity_id, garmin_workout_id

### goals 테이블
주요 필드: id, name, race_date, distance_km, target_time_sec,
target_pace_sec_km, status(active|completed|cancelled), created_at

## 중복 매칭 규칙
동일 활동 판별: start_time 차이 5분 이내 AND distance_km 차이 3퍼센트 이내.
매칭된 활동들은 같은 matched_group_id를 공유한다.
분석 시 그룹 내 모든 소스의 고유 지표를 병합하여 하나의 통합 뷰 생성.

## 설정 파일
config.json (gitignore 대상):
- garmin: email, password
- strava: client_id, client_secret, refresh_token, access_token, expires_at
- intervals: athlete_id, api_key
- runalyze: token
- user: max_hr, threshold_pace, weekly_distance_target, race_targets
- ai: default_provider, prompt_language
