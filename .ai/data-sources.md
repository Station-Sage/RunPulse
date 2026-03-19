# RunPulse - 데이터 소스 상세

## 1. Garmin Connect
라이브러리: python-garminconnect (pip install garminconnect)
인증: 이메일/비밀번호 로그인 (세션 토큰 자동 관리)
가져올 데이터:
- 활동 목록: get_activities(start, limit) -> 날짜/거리/시간/HR/칼로리 등
- 활동 상세: get_activity(activity_id) -> Training Effect, Training Load, VO2Max
- 수면: get_sleep_data(date) -> Sleep Score, 수면 시간, 수면 단계
- HRV: get_hrv_data(date) -> HRV Status, HRV 값
- Body Battery: get_body_battery(date) -> 충전/소모 그래프
- 스트레스: get_stress_data(date) -> 평균 스트레스
API 제한: 비공식이므로 명확한 제한 없음. 요청 간 2초 딜레이 권장

## 2. Strava
인증: OAuth2 (client_id, client_secret, refresh_token)
토큰 갱신: POST https://www.strava.com/oauth/token
가져올 데이터:
- 활동 목록: GET /api/v3/athlete/activities?after=epoch&per_page=30
- 활동 상세: GET /api/v3/activities/{id} -> Suffer Score, 칼로리, Segment Efforts
- 스트림: GET /api/v3/activities/{id}/streams?keys=time,distance,heartrate,velocity_smooth,cadence,altitude
  -> 1초 단위 데이터 배열
- 세그먼트 PR: 활동 상세 내 segment_efforts 배열에서 pr_rank 확인
API 제한: 200 요청/15분, 2000 요청/일

## 3. Intervals.icu
인증: Basic Auth (athlete_id, api_key). Settings -> Developer Settings에서 API key 생성
Base URL: https://intervals.icu/api/v1/athlete/{athlete_id}
가져올 데이터:
- 활동 목록: GET /activities?oldest=YYYY-MM-DD&newest=YYYY-MM-DD
- 활동 상세: GET /activities/{id} -> icu_training_load, icu_intensity 등
- 웰니스(피트니스): GET /wellness?oldest=YYYY-MM-DD&newest=YYYY-MM-DD
  -> ctl, atl, rampRate, eftp 등
- 웰니스 cols 파라미터: ?cols=ctl,atl,rampRate,ctlLoad,atlLoad,eftp
API 제한: 명시된 제한 없음. 합리적 사용 권장

## 4. Runalyze
인증: Personal API Token. Settings -> Personal API에서 생성 (만료일 설정 필요)
헤더: token: YOUR_TOKEN
Base URL: https://runalyze.com/api/v1
가져올 데이터:
- 활동 목록: GET /activities -> 기본 활동 정보
- 활동 상세: GET /activities/{id} -> Effective VO2Max, VDOT, TRIMP
- 비공식 내부 URL (웹 스크래핑):
  https://runalyze.com/_internal/data/athlete/history/vo2max -> VO2Max 이력 JSON
  (로그인 세션 쿠키 필요)
- Race Prediction: 활동 상세 내 계산값 또는 웹 도구
  https://runalyze.com/tools/effective-vo2max
MCP Server: https://github.com/floriankimmel/runalyze-mcp-server (참고용)
API 제한: 공식 제한 없음. Fair use 기대

## 과거 데이터 일괄 가져오기
- Garmin: https://www.garmin.com/en-US/account/datamanagement/exportdata/
  -> 전체 데이터 ZIP 다운로드 (FIT 파일 포함)
- Strava: https://www.strava.com/athlete/delete_your_account
  -> "Request your archive" -> 전체 GPX/FIT ZIP 다운로드
  (계정 삭제가 아님. 데이터 다운로드 페이지)
- 다운로드한 ZIP을 data/history/ 에 풀고 import_history.py 실행

## 5. Garmin Connect 워크아웃 API (쓰기)
라이브러리: python-garminconnect[workout] (pip install garminconnect[workout])
Typed Models: RunningWorkout, create_warmup_step, create_interval_step, create_recovery_step 등

### 워크아웃 생성 예시 (Typed Model)
from garminconnect import RunningWorkout
workout = RunningWorkout("Tuesday Intervals")
workout.add_step(create_warmup_step(duration_minutes=10, target_hr_zone=2))
workout.add_step(create_interval_step(repeat=6, work_pace="4:30", rest_pace="6:00", work_minutes=3, rest_minutes=2))
workout.add_step(create_cooldown_step(duration_minutes=10, target_hr_zone=1))

### 주요 API 메서드
- upload_running_workout(workout) -> workout_id
- schedule_workout(workout_id, date_str) -> 캘린더 등록
- delete_workout(workout_id) -> 워크아웃 삭제 (캘린더 이벤트는 유지됨)
- get_workouts() -> 현재 저장된 워크아웃 목록

### 슬롯 제한 우회 흐름
1. upload_running_workout(workout) -> id 획득
2. schedule_workout(id, "2026-03-24") -> 캘린더에 등록
3. delete_workout(id) -> 워크아웃 삭제 (슬롯 해제, 캘린더 유지)
4. 워치 싱크 시 해당 날짜에 워크아웃 자동 로드

## 6. Strava Stream 상세 (분석용)
엔드포인트: GET /api/v3/activities/{id}/streams?keys=time,distance,heartrate,velocity_smooth,cadence,altitude,grade_smooth
응답: 각 key별 1초 단위 데이터 배열
저장: data/sources/strava/{activity_id}.json

### 분석 활용
- heartrate + velocity_smooth: Aerobic EF 계산 (pace / hr ratio)
- heartrate 전반/후반 비교: Cardiac Decoupling (디커플링 %)
- altitude + grade_smooth: GAP (Grade Adjusted Pace) 보정
- cadence: 케이던스 패턴 분석
- distance + time: km별 스플릿 계산
