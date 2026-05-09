# MIGRATION-01-03: B안 개요 — SSH 역방향 터널

작성일: 2026-04-25 | 브랜치: renew/data-architecture
연관: MIGRATION-01-01-IP-BLOCK-RESEARCH.md
상태: **보류** — A안(MIGRATION-01-02) 충분할 때까지 구현 대기

---

## 1. 개요

A안의 근본 한계(전체기간 sync 불가, 백그라운드 자동 sync 불가)를 해결하는 방안.
로컬 기기에서 SOCKS5 프록시 서버를 실행하고 SSH 역방향 터널로 VPS에 노출하여,
VPS의 `diauth.garmin.com` 인증 트래픽을 로컬 IP 경유로 라우팅한다.

---

## 2. 아키텍처

```
[로컬 기기 — 주거용 IP]              [VPS — AWS IP]
microsocks :1080 실행
ssh -R 1080:localhost:1080 ubuntu@vps
                             ←─────── VPS:1080 = 로컬 SOCKS5 프록시
                                       HTTPS_PROXY=socks5h://127.0.0.1:1080
                                       diauth.garmin.com → 로컬 IP 경유 ✅
                                       connectapi.garmin.com → 직접 연결 ✅
```

### 2.1 포트 라우팅 상세

- VPS `127.0.0.1:1080` → SSH 터널 → 로컬 `localhost:1080` → SOCKS5 서버 → `diauth.garmin.com`
- `connectapi.garmin.com` 은 HTTPS_PROXY를 우회해도 되고 경유해도 됨 (차단 없음)
- 로컬 기기에서 나가는 IP = 주거용 IP → Garmin 차단 없음

---

## 3. 필요 컴포넌트

### 3.1 로컬 기기 (Windows/macOS/Linux/Termux)

| 컴포넌트 | 역할 | 설치 |
|----------|------|------|
| microsocks | 경량 SOCKS5 서버 | apt/brew/termux-pkg |
| OpenSSH client | SSH 역방향 터널 | 대부분 기본 설치 |
| cloudflared | CF Zero Trust SSH ProxyCommand | 별도 설치 필요 |

**microsocks 대안**: Dante (`sockd`), PySocks 기반 Python 서버, 또는 SSH -D 로컬 SOCKS.

### 3.2 VPS

- SSH 서버 (기존 사용 중)
- CF Zero Trust (기존 사용 중)
- `GatewayPorts no` (기본값) — `127.0.0.1:1080`만 바인딩, 외부 노출 없음

---

## 4. CF Zero Trust SSH 설정

VPS가 CF Zero Trust 뒤에 있어 직접 SSH 불가. 터널 접속 시 ProxyCommand 필요.

### 4.1 ~/.ssh/config (로컬 기기)

```
Host vps.example.com
  ProxyCommand cloudflared access ssh --hostname %h
  User ubuntu
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

### 4.2 터널 실행 명령

```bash
# 터미널 1: SOCKS5 서버 실행
microsocks -p 1080

# 터미널 2: SSH 역방향 터널
ssh -N -R 1080:localhost:1080 ubuntu@vps.example.com
# CF Zero Trust ProxyCommand가 ~/.ssh/config에서 자동 적용됨
```

### 4.3 VPS에서 프록시 적용

```bash
# 단일 명령 실행
HTTPS_PROXY=socks5h://127.0.0.1:1080 python3 src/sync.py --source garmin --days 365

# 또는 환경변수로 전체 세션에 적용
export HTTPS_PROXY=socks5h://127.0.0.1:1080
python3 src/sync.py --source garmin --days 365
unset HTTPS_PROXY
```

---

## 5. 장단점

### 장점

- 전체기간 sync 가능 (터널 유지 중)
- 백그라운드 자동 sync 가능 (터널 유지 중, systemd 타이머/cron 연계)
- A안보다 자동화 수준 높음
- 토큰 파일 업로드 불필요 (VPS가 직접 login 처리)

### 단점

- 로컬 기기 상시 가동 필요 (터널 유지)
- microsocks 데몬 별도 실행 필요
- CF Zero Trust ProxyCommand 설정 필요
- 터널 단절 시 자동 재연결 스크립트 필요 (autossh 또는 systemd 재시작 정책)
- Windows에서 microsocks 대안 필요 (wsl2 또는 Python SOCKS 서버)

---

## 6. autossh 자동 재연결 (선택적)

```bash
# autossh로 터널 단절 시 자동 재연결
autossh -M 0 -N -R 1080:localhost:1080 ubuntu@vps.example.com \
  -o "ServerAliveInterval 30" \
  -o "ServerAliveCountMax 3"
```

---

## 7. 구현 우선순위 및 트리거

**보류 조건**: A안으로 개인 용도 증분 sync가 충분한 동안 구현 대기.

**구현 트리거** (다음 중 하나 해당 시 NEXT로 승격):
1. 전체기간 sync가 필요해질 때 (신규 장치 연동, 데이터 초기화 등)
2. 자동 야간 sync 루틴이 필요해질 때
3. A안 토큰 만료 문제가 빈번해질 때

---

## 8. 구현 필요 항목 (구현 시 참고)

| 항목 | 파일 | 비고 |
|------|------|------|
| HTTPS_PROXY 환경변수 인식 | `src/sync/garmin_auth.py` | garminconnect 0.3.x는 환경변수 자동 인식 여부 확인 필요 |
| 로컬 터널 실행 가이드 문서 | `scripts/garmin_tunnel_setup.md` | OS별 단계별 설명 |
| VPS sync 트리거 스크립트 | `scripts/vps_garmin_sync.sh` | 터널 ON → sync → 터널 OFF |
| microsocks Windows 대안 | — | WSL2 또는 Python PySocks 서버 검토 |
