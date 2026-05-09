# MIGRATION-01-01: VPS IP 차단 근본 원인 분석 및 방안 검토

작성일: 2026-04-25 | 브랜치: renew/data-architecture
연관: MIGRATION-01-AUTH.md | 결정: ADR-010

---

## 1. 문제 정의

garminconnect 0.3.x 마이그레이션 완료 후 VPS(AWS)에서 Garmin 동기화 시 429 에러 발생.
토큰 파일이 정상 존재함에도 불구하고 sync 실패.

---

## 2. 근본 원인 분석

### 2.1 garminconnect 0.3.x DI OAuth 흐름

```
login(tokenstore)
  └── 토큰 파일 로드
  └── _token_expires_soon() 체크 (만료 900초 전이면 True)
        └── True → _refresh_session() 호출
              └── _refresh_di_token()
                    └── POST diauth.garmin.com/di-oauth2-service/oauth/token
                          └── ❌ AWS 데이터센터 IP → Garmin/Cloudflare 차단 → 429
```

### 2.2 silent fail 메커니즘

`_refresh_session()`은 내부적으로 모든 예외를 삼킨다:

```python
# garminconnect 0.3.x 소스 (upstream)
def _refresh_session(self):
    try:
        self._refresh_di_token()
    except Exception:
        pass  # silent fail
```

결과: `login()` 자체는 성공처럼 보임 → 이후 API 호출에서 401 →
`connectapi()` 내부에서 `GarminConnectAuthenticationError` → `GarminConnectConnectionError` 발생.

### 2.3 차단 대상 식별

| 엔드포인트 | 상태 | 비고 |
|-----------|------|------|
| `diauth.garmin.com` | ❌ 차단 | 인증/토큰 갱신 전용 |
| `connectapi.garmin.com` | ✅ 동작 추정 | 실제 데이터 조회 |

→ 데이터 조회 자체가 막힌 것이 아니라 **토큰 갱신 엔드포인트만 차단**.

### 2.4 왜 개인 개발자들은 문제가 없는가

garth, garminconnect 모두 **로컬(주거용 IP) 실행 전제**로 설계됨.
서버 배포 케이스는 공식 Garmin Developer API 또는 별도 프록시 구성이 필요.
VPS에서 쓰는 개인은 거의 없으므로 이 문제가 표면화되지 않음.

---

## 3. 검토 방안

### 3.1 방안 A: 로컬 토큰 발급 + VPS 데이터 sync (채택)

**원리**: 로컬 기기(주거용 IP)에서 fresh 토큰 발급 → VPS에 업로드 → VPS는 데이터 API만 호출.

```
[로컬 기기 — 주거용 IP]              [VPS — AWS IP]
garminconnect.login()
→ fresh access_token (~3600s 유효)
→ POST /api/garmin/local-sync ──────> 토큰 저장
                                       garmin sync 실행
                                       connectapi.garmin.com ✅
                                       DB 저장
```

**동작 조건**: 토큰 발급 후 2700초 이내 sync 완료 (900초 전 갱신 임박 임계값 때문).

**한계**:
- 전체기간 sync 불가 (45분 초과 시 토큰 만료)
- 백그라운드 자동 sync 불가
- 매 sync마다 로컬 스크립트 수동 실행 필요

**채택 이유**: 현재 단계(개인 용도, 수동 트리거)에서 가장 단순하고 즉시 구현 가능.
상세 설계: MIGRATION-01-02

---

### 3.2 방안 B: SSH 역방향 터널 (보류 — BACKLOG NEXT)

**원리**: 로컬 기기에서 SOCKS5 서버 실행 → SSH 역방향 터널로 VPS에 노출 →
VPS의 `diauth.garmin.com` 트래픽을 로컬 IP로 라우팅.

```
[로컬 기기]                           [VPS]
SOCKS5 서버 실행 (예: microsocks)
ssh -R 1080:localhost:1080 ubuntu@vps
                              ←─────── VPS:1080 = 로컬 SOCKS 프록시
                                        HTTPS_PROXY=socks5h://127.0.0.1:1080
                                        diauth.garmin.com → 로컬 IP 경유 ✅
                                        connectapi.garmin.com → 직접 ✅
```

**장점**: 전체기간 sync 가능, 백그라운드 sync 가능 (터널 유지 중).
**단점**: 로컬에 SOCKS5 데몬 별도 필요, 터널 상시 유지 필요.
**CF Zero Trust 고려**: SSH 접속에 `cloudflared access ssh --hostname %h` ProxyCommand 필요.

보류 이유: 현 단계(수동 트리거 충분)에서 구현 복잡도 대비 효용 낮음.
상세 설계: MIGRATION-01-03

---

### 3.3 방안 C: 공식 Garmin Developer API (LATER)

**원리**: Garmin이 제공하는 공식 Push/Webhook 기반 API 사용 → IP 무관.

**특징**:
- IP 차단 문제 근본 해결
- 멀티유저 지원 가능
- 웹훅 기반이므로 백그라운드 sync 자연스럽게 지원

**보류 이유**: Enterprise 신청 필요, 현 단계(개인 용도)에서 불가.
LATER.md 등록됨.

---

## 4. Drop된 방안 (검토 후 탈락)

### 4.1 공용 SOCKS 프록시 서비스

무료 공용 SOCKS5 프록시를 사용해 VPS 인증 트래픽을 우회.

**탈락 이유**:
- 보안 위험: Garmin 인증 토큰이 제3자 프록시를 경유
- 안정성 불가: 무료 프록시는 언제든 차단/오프라인 가능
- 속도 저하: 지연시간 증가로 rate limit 재발 가능성

### 4.2 Oracle Cloud 무료 인스턴스 (프록시 서버용)

Oracle Cloud Always Free 티어에 별도 인스턴스를 만들어 SOCKS 프록시로 사용.

**탈락 이유**:
- 현재 Oracle Cloud 리소스 부족으로 신규 인스턴스 생성 불가
- 별도 인프라 유지 부담

### 4.3 Cloudflare Worker 프록시

CF Worker를 proxy로 사용해 `diauth.garmin.com` 요청을 중계.

**탈락 이유**:
- VPS 자체가 CF Zero Trust 뒤에 있어, CF에서 나가는 IP도 CF IP → 동일 문제
- CORS: 브라우저에서 `diauth.garmin.com`을 직접 호출 불가
- CF Worker는 요청을 실제로 전달해야 하는데 Garmin 측 CORS 정책 충돌

### 4.4 SSH -D 순방향 터널 (방향 오류)

`ssh -D 1080 ubuntu@vps "HTTPS_PROXY=socks5h://localhost:1080 python3 sync.py"` 방식.

**탈락 이유**:
- `-D 1080`은 **로컬 기기**에 SOCKS 프록시를 생성하고 **VPS IP**로 트래픽을 내보냄
  (로컬 → VPS 방향)
- 실제 필요한 것은 반대: VPS → 로컬 방향 (역방향 터널)
- 명령어의 `HTTPS_PROXY=socks5h://localhost:1080`은 VPS 쪽 `localhost:1080`을 가리키므로,
  거기에 아무것도 없어 연결 실패

---

## 5. 결정 요약

| 방안 | 결정 | 이유 |
|------|------|------|
| A: 로컬 토큰 발급 | **채택** | 즉시 구현, 현 단계 요구사항 충족 |
| B: SSH 역방향 터널 | **보류** | 복잡도 높음, 전체기간 sync 필요 시 구현 |
| C: 공식 Garmin API | **LATER** | Enterprise 신청 필요 |
| 공용 SOCKS | **탈락** | 보안/안정성 문제 |
| Oracle Cloud | **탈락** | 리소스 부족 |
| CF Worker | **탈락** | CF IP 동일 문제 |
| SSH -D 순방향 | **탈락** | 방향 오류 |

---

## 6. 미결 확인 사항

| 항목 | 우선순위 |
|------|---------|
| `connectapi.garmin.com`이 AWS IP에서 실제로 동작하는지 실측 | 높음 |
| 토큰 발급 직후 `_token_expires_soon()` false 확인 (exp - now > 900 보장) | 중간 |
