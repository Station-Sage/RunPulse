# MIGRATION-01-02: A안 상세 설계 — 로컬 토큰 발급 + VPS 동기화

작성일: 2026-04-25 | 브랜치: renew/data-architecture
연관: MIGRATION-01-01-IP-BLOCK-RESEARCH.md | 결정: ADR-010

---

## 1. 구현 범위

| 항목 | 파일 | 상태 |
|------|------|------|
| CF Zero Trust 서비스 토큰 바이패스 | `src/web/auth_cf.py` | 변경 |
| 로컬 토큰 수신 + sync 트리거 API | `src/web/app.py` | 변경 (엔드포인트 추가) |
| 로컬 토큰 발급 스크립트 | `scripts/garmin_local_sync.py` | 신규 |
| UI 2탭 (로컬 동기화 / 서버 직접) | `src/web/views_settings_garmin.py` | 변경 |
| 설정 추가 | `config.json.example` | 변경 |

> **주의**: 새 Blueprint 파일 생성하지 않음. sync 관련 API는 기존 패턴대로 `app.py`에 직접 추가.

---

## 2. 동작 흐름

```
[로컬 기기 — 주거용 IP]
python scripts/garmin_local_sync.py
  └── garminconnect.login()               ← diauth.garmin.com ✅ (주거용 IP)
  └── 토큰 JSON 읽기
  └── POST /api/garmin/local-sync
        Headers:
          CF-Access-Client-Id: <service_client_id>      ← CF Zero Trust 바이패스
          CF-Access-Client-Secret: <service_client_secret>
        Body: { "token": {...}, "days": 30 }

[CF Zero Trust Edge]
  └── CF-Access-Client-Id/Secret 검증 → 통과 (서비스 토큰)
  └── 요청을 VPS에 그대로 전달

[VPS — AWS IP]
POST /api/garmin/local-sync
  └── auth_cf.py: 서비스 토큰 헤더 확인 → 통과
  └── 토큰 JSON 유효성 검사
  └── garmin_tokens.json 저장 → tokenstore 경로
  └── bg_sync.start_job("garmin", from_date, to_date, config, user_id)
  └── 202 Accepted + job_id 반환

[VPS — 백그라운드]
  └── src/sync.py --source garmin --days N  ← connectapi.garmin.com ✅ (데이터 전용)
```

---

## 3. scripts/garmin_local_sync.py 설계

### 3.1 CLI 인터페이스

```
python scripts/garmin_local_sync.py [옵션]
  --email     Garmin 계정 이메일 (없으면 프롬프트)
  --password  패스워드 (없으면 프롬프트 — 화면 미출력)
  --vps       VPS URL (예: https://run.example.com)
  --days      동기화 기간 (기본 30, 최대 90)
  --token-only  토큰 발급만 수행, 업로드 없이 파일로 저장
```

API 키 (`--api-key`) 제거됨 — CF Service Token으로 대체. 키 값은 `.env`에서만 관리.

### 3.2 처리 순서

```python
1. 인증 정보 수집 (CLI 인수 우선 → .env 파일 → 인터랙티브 프롬프트)
2. garminconnect.Garmin(email, password, return_on_mfa=True).login()
   → needs_mfa: input("MFA 코드: ")로 resume_login()
3. client.client.dump('.') → garmin_tokens.json 생성
4. --token-only 시: 파일 저장 후 종료
5. POST {vps}/api/garmin/local-sync
   Headers:
     CF-Access-Client-Id: {CF_SERVICE_CLIENT_ID}
     CF-Access-Client-Secret: {CF_SERVICE_CLIENT_SECRET}
   Body: { "token": <garmin_tokens.json 내용>, "days": N }
6. 응답 처리:
   202 → "동기화 시작됨. job_id={...}" 출력 + 웹 UI URL 안내
   401 → "CF 서비스 토큰 인증 실패" 출력
   400 → "토큰 JSON 형식 오류: {detail}" 출력
   기타 → 응답 본문 출력
```

### 3.3 환경변수 지원 (.env 파일)

```
GARMIN_EMAIL=foo@bar.com
GARMIN_VPS_URL=https://run.example.com
CF_SERVICE_CLIENT_ID=xxxxxxxx.access
CF_SERVICE_CLIENT_SECRET=yyyyyyyy...
```

`GARMIN_SYNC_API_KEY` 불필요 (구 설계 잔재 — 사용하지 않음).

### 3.4 플랫폼 지원

| 플랫폼 | 설치 | 실행 |
|--------|------|------|
| Windows | `pip install garminconnect>=0.3.1 curl_cffi ua-generator` | `python garmin_local_sync.py` |
| macOS/Linux | `pip3 install garminconnect>=0.3.1 curl_cffi ua-generator` | `python3 garmin_local_sync.py` |
| Android (Termux) | `pkg install python` → `pip install garminconnect>=0.3.1 curl_cffi ua-generator` | `python garmin_local_sync.py` |

Termux 특이사항: `scripts/` 경로 없이 직접 실행. curl_cffi wheel이 없을 경우 `pkg install clang` 후 소스 빌드 필요 (ARM64).

### 3.5 CF 토큰 관리 방법 (두 경로)

| 방법 | 설명 | 권장 대상 |
|------|------|-----------|
| **웹 UI 설정** | `/connect/garmin` Tab 1 → CF Service Token 카드 → 저장 → `.env 다운로드` | 처음 설정 시 |
| **.env 직접 편집** | 스크립트와 같은 디렉터리에 `.env` 파일 생성 | 고급 사용자 |

두 경로 모두 동일한 CF 대시보드 서비스 토큰 값을 사용.

### 3.6 Q4 분석 — 웹 UI에서 PC/폰 스크립트 직접 실행 가능 여부

**결론: 현재 아키텍처에서 불가**

이유:
1. **단방향 연결**: 사용자 로컬 기기는 NAT/방화벽 뒤. VPS→로컬 outbound TCP 불가.
2. **로컬 IP 미인지**: VPS는 사용자 기기 IP를 알 수 없음 (CF Zero Trust 경유 → 실제 IP 비노출).
3. **대안 (Polling)**: 로컬 기기가 VPS 명령 queue를 poll 후 실행 — 별도 상시 실행 daemon 필요, 복잡도 과도.

**채택 전략**: 스크립트+.env 파일을 웹 UI에서 다운로드 후 사용자가 로컬에서 직접 실행. 이것이 A안의 설계 의도.

---

## 4. CF Zero Trust 바이패스: auth_cf.py 수정

### 4.1 현행 동작

`APP_ENV=production` 시 모든 요청에서 `CF-Access-Authenticated-User-Email` 헤더를 검사.
헤더 없으면 → 401 반환. 로컬 스크립트의 HTTP POST는 이 헤더가 없으므로 차단됨.

### 4.2 서비스 토큰 체크 추가

`before_request` 핸들러 내 기존 user-email 검사 **앞에** 서비스 토큰 확인 로직 삽입:

```python
# auth_cf.py — before_request 핸들러 내 추가 (기존 user-email 검사 앞에)

client_id = request.headers.get("CF-Access-Client-Id", "")
client_secret = request.headers.get("CF-Access-Client-Secret", "")

svc_id = config.get("cf", {}).get("service_client_id", "")
svc_secret = config.get("cf", {}).get("service_client_secret", "")

if svc_id and client_id == svc_id and client_secret == svc_secret:
    # 서비스 토큰 인증 성공 → config.garmin.email을 user_id로 사용
    g.user_id = config.get("garmin", {}).get("email", "service")
    return None  # 이후 user-email 검사 스킵
```

- `svc_id` 미설정(`""`) 시 서비스 토큰 바이패스 비활성화 (보안 기본값)
- `g.user_id`에 `config.garmin.email` 주입 → 이후 sync 로직에서 user_id 일관 사용

### 4.3 보안 고려사항

- CF Service Token은 CF 대시보드에서 발급, TLS로만 전송 (HTTPS 강제 — CF가 보장)
- `service_client_id`, `service_client_secret`은 `config.json`에 저장 (gitignore됨)
- 서비스 토큰 없는 일반 요청: 기존 CF user-email 검사 그대로 유지
- 서비스 토큰 바이패스는 `/api/garmin/local-sync` 전용이 아님 — CF가 이미 토큰 유효성 검증하므로 특정 라우트 제한 불필요

---

## 5. VPS API 엔드포인트: POST /api/garmin/local-sync

### 5.1 위치

`src/web/app.py`에 직접 추가 (기존 `/trigger-sync`, `/bg-sync/*` 패턴과 동일).
새 Blueprint 파일 생성 불필요.

### 5.2 엔드포인트 설계

```
POST /api/garmin/local-sync

인증: auth_cf.py에서 처리 (CF Service Token 또는 CF user-email 둘 다 통과)

요청 Body (JSON):
{
  "token": { ... garmin_tokens.json 내용 ... },
  "days": 30          (선택, 기본 30, 최대 90)
}

처리:
1. token 유효성 확인 (access_token 또는 di_access_token 키 존재)
2. tokenstore 경로 결정: config.garmin.tokenstore / {user_id} / garmin_tokens.json
3. garmin_tokens.json 저장
4. from_date = today - days, to_date = today
5. bg_sync.start_job("garmin", from_date, to_date, config, g.user_id)
6. 202 반환

응답:
202 { "status": "sync_started", "days": 30, "job_id": "...", "message": "동기화 시작됨" }
400 { "error": "token 필드 없음" | "access_token/di_access_token 누락" }
```

### 5.3 subprocess 패턴 준수

bg_sync.start_job → BgSyncThread._run_batches() → subprocess.run([sys.executable, "src/sync.py", ...])
직접 스레드에서 `sync_garmin()` 함수 호출 금지 (ADR-009, 기존 패턴 불일치).

### 5.4 config 미설정 처리

`config.cf.service_client_id` 미설정 시에도 엔드포인트는 활성화 상태 유지.
엔드포인트 자체는 auth_cf.py 인증을 통과한 요청만 도달하므로 별도 비활성화 로직 불필요.

---

## 6. UI 2탭 설계: /connect/garmin

### 6.1 탭 구조

```
탭 1: 로컬 동기화 (권장)          탭 2: 서버 직접 로그인
─────────────────────────          ──────────────────────
[CF Service Token 설정 카드]       서버 IP가 차단되어 동작하지
  Client ID + Secret 입력폼        않을 수 있습니다.
  .env 다운로드 버튼
[스크립트 다운로드 + 실행 안내]    이메일 + 패스워드 입력
  PC/Mac/Linux 명령어              (서버에서 직접 login)
  Android Termux 명령어
📁 파일 업로드
📋 JSON 붙여넣기
```

### 6.2 탭 1 콘텐츠 (로컬 동기화) — 구현 완료

**CF Service Token 카드** (최상단):
- 현재 저장 상태 배지 (설정됨 ✓ / 미설정)
- `POST /connect/garmin/cf-settings` 폼
- CF 설정 후 `.env 다운로드` 버튼 노출 (`GET /connect/garmin/download-env`)

**스크립트 다운로드 + 실행 안내**:
- `GET /connect/garmin/download-script` → `garmin_local_sync.py` 첨부파일
- PC/Mac/Linux 명령어 예시
- Android Termux 설치+실행 명령어 포함

**수동 업로드 폼** (스크립트 없이 직접 업로드 가능):
- 파일 업로드: `POST /connect/garmin/upload-token`
- JSON 붙여넣기: `POST /connect/garmin/paste-token`
- trigger_sync 체크박스 (ON 시 토큰 저장 후 즉시 bg_sync 시작)

### 6.3 탭 2 콘텐츠 (서버 직접)

기존 로그인 폼 + 차단 경고 배너. 내용 동일.

### 6.4 신규 엔드포인트 요약

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/connect/garmin/cf-settings` | POST | CF 서비스 토큰 저장 → config.json |
| `/connect/garmin/download-script` | GET | `garmin_local_sync.py` 첨부 다운로드 |
| `/connect/garmin/download-env` | GET | CF 토큰 pre-fill된 `.env` 생성 + 다운로드 |

### 6.5 현행 → 신규 UI 변환

| 현행 | 신규 |
|------|------|
| `<details>` 3개 (🔧 서버 직접, 📁 파일 업로드, 📋 붙여넣기) | 2탭 (로컬 동기화 권장, 서버 직접) |
| CF 토큰 설정 UI 없음 | CF Service Token 카드 (설정 + 상태 표시) |
| 스크립트 다운로드 없음 | 스크립트 + .env 다운로드 버튼 |
| Termux 안내 없음 | Android Termux 설치+실행 명령어 포함 |
| 업로드 후 자동 sync 없음 | 체크박스로 선택 가능 |

---

## 7. config.json.example 변경

```json
{
  "garmin": {
    "email": "your@email.com",
    "tokenstore": "~/.garminconnect"
  },
  "cf": {
    "service_client_id": "xxxxxxxx.access",
    "service_client_secret": "your_cf_service_token_secret_here"
  }
}
```

- `garmin.local_sync_api_key` 제거 (구 설계 잔재)
- `cf.service_client_id` / `cf.service_client_secret`: CF Zero Trust 대시보드 → Service Auth에서 발급한 값
- 미설정 시 서비스 토큰 바이패스 비활성화 (로컬 스크립트 사용 불가, 웹 UI만 가능)

---

## 8. 완료 조건

### 8.1 기능 완료 조건

- [x] `scripts/garmin_local_sync.py` 구현 완료 (PC/Mac/Linux/Termux)
- [x] CF Service Token 헤더로 `POST /api/garmin/local-sync` → 202 응답
- [x] VPS에서 bg_sync job 시작 확인 (job_id 반환)
- [ ] sync 완료 후 DB에 활동 데이터 저장 확인 (실환경 검증 필요)
- [x] UI: 2탭 렌더링 정상
- [x] UI: 파일 업로드 후 자동 sync 트리거 (체크박스 ON 시)
- [x] UI: CF Service Token 설정 카드 (저장 상태 배지)
- [x] UI: 스크립트 + .env 다운로드 버튼
- [x] UI: Termux 실행 명령어 안내
- [x] CF Service Token 미설정 시 서비스 토큰 바이패스 비활성화
- [x] 잘못된 CF Service Token → 401 처리 (auth_cf.py 통과 실패)
- [x] 토큰 JSON 형식 오류 → 400 처리

### 8.2 검증 조건

- [ ] `connectapi.garmin.com`이 VPS AWS IP에서 실제 동작 확인 (실측 필요)
- [ ] 토큰 발급 직후 `_token_expires_soon()` false 확인 (갱신 불필요)
- [ ] 30일 증분 sync가 45분 이내 완료 (토큰 만료 2700초 내)

---

## 9. 테스트 항목

### 9.1 유닛 테스트 (신규)

**test_garmin_local_sync_api.py**:

```python
class TestLocalSyncEndpoint:
    def test_cf_service_token_auth_passes(self, client, mocker):
    def test_missing_cf_headers_returns_401(self, client):
    def test_wrong_cf_secret_returns_401(self, client):
    def test_valid_token_returns_202_with_job_id(self, client, mocker):
    def test_missing_token_field_returns_400(self, client, mocker):
    def test_invalid_token_structure_returns_400(self, client, mocker):
    def test_bg_sync_started_after_token_save(self, client, mocker):
```

**test_garmin_local_sync_script.py**:

```python
class TestLocalSyncScript:
    def test_token_file_generated(self, mocker):
    def test_cf_headers_sent_in_request(self, mocker):
    def test_mfa_flow(self, mocker):
    def test_token_only_flag_skips_upload(self, mocker):
    def test_env_file_loaded(self, mocker, tmp_path):
```

### 9.2 수동 검증 체크리스트

```
□ 1. 로컬 기기에서 스크립트 실행
      python scripts/garmin_local_sync.py --email x --vps https://... --days 30
      → garmin_tokens.json 생성 확인
      → VPS 응답 202 + job_id 확인

□ 2. VPS에서 bg_sync job 시작 확인
      docker logs runpulse | grep "bg_sync"

□ 3. 웹 UI에서 sync 진행 확인
      /sync 페이지 → 백그라운드 동기화 상태 확인

□ 4. DB 데이터 확인
      SELECT COUNT(*) FROM activities WHERE source='garmin';

□ 5. CF Service Token 오류 케이스
      잘못된 CF-Access-Client-Secret → 401 확인

□ 6. UI 업로드 경로 수동 테스트
      /connect/garmin → 탭 1 → 파일 업로드 → 자동 sync 확인
```

---

## 10. 알려진 한계 및 우회책

| 한계 | 우회책 |
|------|--------|
| 전체기간 sync 불가 (토큰 45분 내 만료) | 30일 단위 분할 수동 실행 (`--days 30` 반복) |
| 백그라운드 자동 sync 불가 | B안(SSH 역방향 터널) 구현 시 해결. BACKLOG 등록됨 |
| 매 sync마다 로컬 기기 필요 | 수동 트리거 전제이므로 허용 |

---

## 11. 구현 순서

1. ✅ `config.json.example` — `cf.service_client_id/secret` 추가
2. ✅ `src/web/auth_cf.py` — CF Service Token 바이패스 로직 추가
3. ✅ `src/web/app.py` — `POST /api/garmin/local-sync` 엔드포인트 추가
4. ✅ `scripts/garmin_local_sync.py` — 로컬 실행 스크립트 (PC/Mac/Linux/Termux)
5. ✅ `src/web/views_settings_garmin.py` — 2탭 UI + CF 설정 카드 + 스크립트/.env 다운로드 + Termux 안내
6. ✅ 유닛 테스트 (`test_garmin_local_sync_api.py` 14개, `test_garmin_local_sync_script.py` 7개, 합계 21개)
7. ⬜ 수동 검증 (로컬 기기에서 스크립트 실행 → VPS sync 확인)
