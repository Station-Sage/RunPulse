# API 설정 가이드

## 1. Garmin Connect
별도 API 설정 불필요. config.json에 Garmin Connect 로그인 이메일과 비밀번호 입력.
python-garminconnect 라이브러리가 자동으로 세션 관리.
주의: 2단계 인증(2FA) 활성화 시 첫 로그인에서 추가 처리 필요할 수 있음.

## 2. Strava OAuth2

### 앱 생성
1. https://www.strava.com/settings/api 접속
2. Application Name: RunPulse (아무 이름)
3. Authorization Callback Domain: localhost
4. Client ID와 Client Secret을 config.json에 입력

### 최초 토큰 발급
브라우저에서 아래 URL 접속 (CLIENT_ID를 실제 값으로 교체):

    https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&scope=activity:read_all&approval_prompt=auto

승인 후 리다이렉트되는 URL에서 code 파라미터 복사.
그 다음 Termux에서:

    curl -X POST https://www.strava.com/oauth/token \
      -d client_id=CLIENT_ID \
      -d client_secret=CLIENT_SECRET \
      -d code=위에서_복사한_CODE \
      -d grant_type=authorization_code

응답의 refresh_token, access_token, expires_at을 config.json에 입력.
이후 src/sync/strava.py가 자동으로 토큰을 갱신.

## 3. Intervals.icu
1. https://intervals.icu 로그인
2. Settings -> Developer Settings
3. API Key 생성
4. Athlete ID: Settings 페이지 URL에서 확인 (예: i12345)
5. config.json에 athlete_id와 api_key 입력

## 4. Runalyze
1. https://runalyze.com 로그인
2. Settings -> Personal API (https://runalyze.com/settings/personal-api)
3. 토큰 생성 (만료일 설정 필요)
4. config.json에 token 입력
참고: 일부 고급 API는 Premium(2.99유로/월) 필요

## 5. 과거 데이터 다운로드

### Garmin 전체 데이터
https://www.garmin.com/en-US/account/datamanagement/exportdata/
-> 데이터 내보내기 요청 -> 이메일로 ZIP 링크 수신 -> 다운로드

### Strava 전체 데이터
https://www.strava.com/athlete/delete_your_account
-> "Request your archive" 클릭 (계정 삭제가 아님)
-> 이메일로 ZIP 링크 수신 -> 다운로드

### 임포트

    # ZIP 파일을 data/history/ 에 풀기
    unzip garmin_export.zip -d data/history/
    python src/import_history.py
