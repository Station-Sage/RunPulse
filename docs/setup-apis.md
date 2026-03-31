# RunPulse API 설정 및 서비스 연동 가이드

## 연동 방식 요약

| 서비스 | 사이트 로그인 | 구글 로그인 | API 접근 방식 | 필요한 값 |
|--------|-------------|-----------|-------------|----------|
| Garmin Connect | 이메일+비번 | 구글 SSO 지원 | garth 세션 토큰 | email, password |
| Strava | OAuth2 | 구글 로그인 가능 | access_token + refresh_token | client_id, client_secret, refresh_token |
| Intervals.icu | Strava/자체 | Strava 경유 가능 | API Key (Basic Auth) | athlete_id, api_key |
| Runalyze | 이메일+비번 | 구글/페이스북 SSO | API Token | token |

## RunPulse 연동 방식 (2단계)

### CLI 모드 (Phase 2, 현재)
config.json에 인증 정보를 직접 입력하여 사용합니다.
각 서비스의 키/토큰을 아래 안내에 따라 발급받아 입력합니다.

### 웹 UI 모드 (Phase 5, 예정)
설정 페이지에서 "연동하기" 버튼을 누르면 해당 서비스의 로그인 페이지가 팝업으로 열립니다.
구글 계정 등 소셜 로그인으로 인증하면 토큰이 자동으로 획득됩니다.
HealthSync 앱과 동일한 WebView 방식입니다.

| 서비스 | 웹 UI 연동 방식 | 구글 로그인 |
|--------|---------------|-----------|
| Garmin | 팝업으로 sso.garmin.com 열기 → 세션 토큰 캡처 | 가능 (가민 SSO가 구글 지원) |
| Strava | OAuth2 플로우 자동화 → 토큰 자동 획득 | 가능 (Strava가 구글 로그인 지원) |
| Intervals.icu | 팝업으로 intervals.icu 설정 페이지 열기 → API Key 복사 안내 | 간접 가능 (Strava 경유 로그인) |
| Runalyze | 팝업으로 runalyze.com 설정 페이지 열기 → API Token 복사 안내 | 가능 (Runalyze가 구글 SSO 지원) |

---

## 1. Garmin Connect

### 인증 방식
python-garminconnect 라이브러리는 내부적으로 garth를 사용합니다.
garth는 가민 SSO(sso.garmin.com) 인증을 이메일+비밀번호로 처리하며,
OAuth1 토큰을 받아 약 1년간 유효한 세션을 유지합니다.

### 구글 계정으로 가민을 사용하는 경우
가민에 구글 SSO로 가입한 경우, 가민 전용 비밀번호가 없을 수 있습니다.
이 경우 CLI 모드에서는 아래 절차로 비밀번호를 설정해야 합니다.
(Phase 5 웹 UI에서는 구글 로그인이 직접 가능하므로 이 절차가 불필요합니다.)

1. https://sso.garmin.com/sso/forgot-password 접속
2. 가민에 연결된 이메일(구글 이메일) 입력
3. 이메일로 비밀번호 재설정 링크 수신
4. 새 비밀번호 설정
5. 이제 이메일+비밀번호로 garminconnect 로그인 가능

### config.json 설정

    "garmin": {
      "email": "your@gmail.com",
      "password": "설정한_비밀번호"
    }

### 주의사항
- 2단계 인증(MFA) 활성화 시 garth의 MFA 핸들러로 처리 가능
- garth 세션 토큰은 ~/.garth/ 에 캐시되어 매번 로그인하지 않음
- 로그인 빈도를 최소화할 것 (잦은 로그인 시 일시 차단 가능)

---

## 2. Strava (OAuth2)

### 앱 등록
1. Strava에 로그인 (구글 계정 로그인 가능)
2. https://www.strava.com/settings/api 접속
3. 앱 생성:
   - Application Name: RunPulse
   - Category: Data Importer
   - Website: https://runpulse.stationsage.dev
   - Authorization Callback Domain: runpulse.stationsage.dev
4. 생성 완료 후 확인:
   - Client ID (숫자)
   - Client Secret (영문+숫자 문자열)

### 최초 토큰 발급
브라우저에서 아래 URL 접속 (YOUR_CLIENT_ID를 실제 값으로 교체):

RunPulse 웹 설정 → Strava 연동 → "Strava로 로그인" 버튼을 클릭하면 자동으로 OAuth 인증이 시작됩니다.
콜백 URL: `https://runpulse.stationsage.dev/connect/strava/callback`

code= 뒤의 값(abc123def456)을 복사합니다.

토큰 교환 (Termux 또는 터미널에서):

    curl -X POST https://www.strava.com/oauth/token \
      -d client_id=YOUR_CLIENT_ID \
      -d client_secret=YOUR_CLIENT_SECRET \
      -d code=abc123def456 \
      -d grant_type=authorization_code

응답 예시:

    {
      "token_type": "Bearer",
      "expires_at": 1562908002,
      "expires_in": 21600,
      "refresh_token": "YOUR_REFRESH_TOKEN",
      "access_token": "YOUR_ACCESS_TOKEN",
      "athlete": { "id": 12345, ... }
    }

### config.json 설정

    "strava": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET",
      "refresh_token": "YOUR_REFRESH_TOKEN",
      "access_token": "YOUR_ACCESS_TOKEN",
      "expires_at": 1562908002
    }

### 주의사항
- access_token은 6시간마다 만료됨. RunPulse(strava.py)가 자동 갱신
- refresh_token은 갱신 시 새 값이 발급됨. config.json에 자동 저장
- API 제한: 200 요청/15분, 2000 요청/일
- scope에 read_all,activity:read_all 필수 (Stream 데이터 접근용)

### Phase 5 웹 UI에서의 연동 (예정)
설정 페이지에서 "Strava 연동" 버튼 클릭
-> Strava OAuth2 인증 페이지로 리다이렉트 (구글 로그인 가능)
-> 승인 후 RunPulse로 자동 리다이렉트
-> authorization code 자동 교환
-> config.json에 토큰 자동 저장
위의 수동 절차가 모두 자동화됩니다.

---

## 3. Intervals.icu (API Key)

### API Key 발급
1. https://intervals.icu 로그인
   - Strava 계정으로 로그인 가능 (Strava가 구글 로그인 지원)
   - 또는 자체 이메일+비밀번호 계정
2. 우측 상단 프로필 아이콘 → Settings
3. 좌측 메뉴에서 Developer 클릭
4. "API Key" 섹션에서 Generate 클릭 → 키 복사
5. Athlete ID 확인: 같은 페이지 상단 또는 URL에서 확인
   - 예: https://intervals.icu/athlete/i12345 → athlete_id는 "i12345"

### config.json 설정

    "intervals": {
      "athlete_id": "i12345",
      "api_key": "발급받은_API_KEY"
    }

### 주의사항
- API Key는 Basic Auth로 사용 (username: "API_KEY", password: 발급받은 키)
- 명시적 요청 제한 없음. 합리적 사용 권장
- Intervals.icu OAuth2도 지원하지만, 개인 사용에는 API Key가 더 간편
- 무료 계정에서도 전체 API 접근 가능

### Phase 5 웹 UI에서의 연동 (예정)
설정 페이지에서 "Intervals.icu 연동" 버튼 클릭
-> Intervals.icu OAuth2 플로우로 인증 (Strava/구글 로그인 가능)
-> 또는 설정 페이지 직접 링크로 API Key 복사 안내

---

## 4. Runalyze (API Token)

### API Token 발급
1. https://runalyze.com 로그인
   - "Sign in with Google" 버튼 지원 (구글 계정으로 직접 로그인 가능)
   - "Sign in with Facebook" 버튼도 지원
   - 또는 자체 이메일+비밀번호 계정
2. 우측 상단 톱니바퀴 → Settings
   또는 직접 접속: https://runalyze.com/settings
3. Personal API 탭 클릭
   또는 직접 접속: https://runalyze.com/settings/personal-api
4. 만료일 설정 (권장: 1년)
5. Generate 클릭 → 토큰 복사

### config.json 설정

    "runalyze": {
      "token": "발급받은_API_TOKEN"
    }

### 주의사항
- 토큰 만료일 도래 시 재발급 필요 (만료 전 알림 예정 - Phase 6)
- 무료 계정: 기본 활동 데이터, VO2Max, TRIMP 접근 가능
- Premium(2.99유로/월): Effective VO2Max 상세 이력, Marathon Shape, 고급 Race Prediction
- 비공식 내부 URL(/_internal/data/)은 웹 세션 쿠키가 필요하므로 API Token으로 접근 불가

### Phase 5 웹 UI에서의 연동 (예정)
설정 페이지에서 "Runalyze 연동" 버튼 클릭
-> Runalyze 로그인 페이지 팝업 (구글/페이스북 로그인 가능)
-> 로그인 후 API 설정 페이지로 자동 이동
-> 토큰 복사 안내 또는 자동 캡처

---

## 5. 전체 config.json 예시

    {
      "garmin": {
        "email": "your@gmail.com",
        "password": "your_password"
      },
      "strava": {
        "client_id": "12345",
        "client_secret": "abcdef1234567890",
        "refresh_token": "your_refresh_token",
        "access_token": "",
        "expires_at": 0
      },
      "intervals": {
        "athlete_id": "i12345",
        "api_key": "your_api_key"
      },
      "runalyze": {
        "token": "your_api_token"
      },
      "user": {
        "max_hr": 190,
        "threshold_pace": 300,
        "weekly_distance_target": 50,
        "race_targets": []
      },
      "ai": {
        "default_provider": "genspark",
        "prompt_language": "ko"
      }
    }

### 연동 테스트
각 서비스별로 동기화를 개별 테스트할 수 있습니다:

    python src/sync.py --source garmin --days 1
    python src/sync.py --source strava --days 1
    python src/sync.py --source intervals --days 1
    python src/sync.py --source runalyze --days 1

성공하면 "N개 활동 동기화 완료" 메시지가 출력됩니다.
전체 동기화:

    python src/sync.py --source all --days 7

---

## 6. 과거 데이터 일괄 가져오기

### Garmin 전체 데이터 내보내기
1. https://www.garmin.com/en-US/account/datamanagement/exportdata/ 접속
2. "데이터 내보내기 요청" 클릭
3. 이메일로 ZIP 다운로드 링크 수신 (최대 수시간 소요)
4. ZIP 다운로드 → FIT 파일 포함

### Strava 전체 데이터 내보내기
1. https://www.strava.com/athlete/delete_your_account 접속
   (주의: 계정 삭제가 아닙니다. 데이터 다운로드 페이지입니다)
2. "Request Your Archive" 클릭
3. 이메일로 ZIP 다운로드 링크 수신
4. ZIP 다운로드 → GPX/FIT 파일 포함

### 임포트

    # ZIP 파일을 data/history/ 에 풀기
    mkdir -p data/history
    unzip garmin_export.zip -d data/history/
    unzip strava_export.zip -d data/history/

    # 일괄 임포트
    python src/import_history.py

---

## 7. 트러블슈팅

### Garmin 로그인 실패
- 구글 SSO 전용 계정 → 가민에서 비밀번호 별도 설정 필요 (위 안내 참조)
- 2FA 활성화 → garth MFA 핸들러 사용 또는 임시 비활성화
- 잦은 로그인 시도 → 일시 차단됨. 30분 후 재시도
- garth 세션 만료 → ~/.garth/ 폴더 삭제 후 재로그인

### Strava 토큰 오류
- "Authorization Error" → scope가 read_all,activity:read_all인지 확인
- code 만료 → authorization code는 수 분 내 사용해야 함. URL 재접속 후 재시도
- refresh_token 무효 → 앱을 Strava에서 제거 후 전체 과정 재시도
  (Strava → Settings → My Apps → RunPulse → Revoke Access)

### Intervals.icu 401 Unauthorized
- API Key가 정확한지 확인
- auth 형식: Basic Auth (username: "API_KEY", password: 발급받은 키)
- athlete_id 형식: "i" + 숫자 (예: "i12345")

### Runalyze 토큰 오류
- 토큰 만료일 확인 → 재발급 필요
- 헤더 형식: token: YOUR_TOKEN (Bearer가 아님)
