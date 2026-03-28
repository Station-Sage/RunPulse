# CLAUDE.md - RunPulse

## 필수 읽기 (세션 시작 시 — 토큰 절약 규칙)

### 반드시 읽을 것
1. `v0.2/.ai/todo.md` — **`## ▶ 다음 세션 시작 시 여기부터` 섹션만** (상단 ~55줄)
   - ⚠️ 그 아래 `## 현재 미완료 작업` 섹션(100줄+)은 **읽지 말 것** — 완료 이력, 토큰 낭비

### 작업 유형별 참조 (필요할 때만)

| 작업 | 참조 파일 | 읽을 부분 |
|------|----------|----------|
| 새 모듈/파일 작성 | `v0.2/.ai/architecture.md` | 전체 (짧음) |
| 메트릭 계산식 수정 | `v0.2/.ai/metrics.md` | 해당 메트릭 섹션만 |
| 설계 결정 확인 | `v0.2/.ai/decisions.md` | 관련 D-V2-XX만 grep |
| 훈련 엔진 설계 | `v0.2/.ai/training_engine_v2_design.md` | 해당 섹션 번호만 |
| changelog 확인 | `v0.2/.ai/changelog.md` | 최신 2~3개 항목만 |
| 버전 목표/의존성 | `v0.2/.ai/roadmap.md` | 해당 버전 섹션만 |

### 읽지 말 것 (세션 시작 시)
- `v0.2/.ai/todo.md` 전체 (→ 위 `▶ 다음 세션` 섹션만)
- `v0.2/.ai/changelog_history.md` (→ 과거 이력, 거의 불필요)
- `v0.2/.ai/metrics_by_claude.md` (→ 연구용 초안, metrics.md 우선)
- `v0.2/.ai/index.md`, `v0.2/.ai/files_index.md` (→ 파일 탐색은 Grep/Glob 사용)
- v0.1 히스토리 일체 (`v0.1/.ai/` 폴더) — 완료된 버전, 참고 불필요

---

## 프로젝트 개요
- 이름: RunPulse — 개인 러닝 코치 에이전트
- 목적: Garmin, Strava, Intervals.icu, Runalyze 4개 소스의 러닝/건강 데이터를 통합 분석하고, AI 코치가 훈련 계획을 추천하며, 가민 워치에 자동 등록
- 저장소: https://github.com/Station-Sage/RunPulse
- 실행 환경: Android Termux, Python 3.11+, SQLite3, 파일 기반 저장
- AI 분석: Genspark AI Chat (무료) 기본, 다른 AI(ChatGPT, Claude, DeepSeek) 교체 가능
- 비용: 전액 무료

---

## 버전 현황

### v0.1 (완료, `main` 브랜치)
- Phase 1-2: DB 스키마 + 4소스 동기화 (Garmin/Strava/Intervals/Runalyze)
- Phase 3: 분석 10개 모듈 (compare, trends, recovery, weekly_score, efficiency, zones, activity_deep, race_readiness, report, CLI)
- Phase 4/4-1: 목표 관리 + AI 코치(브리핑/추천칩/응답 파싱)
- Phase 5: 웹 대시보드 (홈/활동/웰니스/설정, Flask)
- 테스트: 652개 통과

### v0.2 (진행 중, `fix/metrics-everythings` 브랜치)
- 2차 메트릭 계산 엔진 (UTRS, CIRS, FEARP, DI, DARP, RMR, TIDS, RTTI, WLEI, TPDI 등)
- 고도화된 통합 대시보드 UI (PMC 차트, 레이더 차트, 게이지)
- 레이스 예측, 분석 레포트, 웰니스 UI
- 활동 상세: 7그룹 접이식 + 서비스 탭 lazy load
- AI 코치 v2: Gemini Function Calling (10도구) + 의도 감지 + AJAX 실시간 채팅
- MCP 서버 (Claude Desktop/CLI용)
- VDOT 전문 추정 (가중 평균 + HR 검증 + 이상치 제거)
- **훈련 엔진 v2 (논문 기반)**: Gate 5종(CRS) + Seiler 80/20 + Daniels 페이스 + session_outcomes ML 기반 — DB v3
- **훈련탭 UX**: 체크인 AJAX + 재조정 diff 인라인 + 동기화 후 자동 매칭
- **DB SCHEMA_VERSION = 3** (최신)
- 테스트: **1047개** 통과 (2026-03-28)
- 자세한 내용: `v0.2/.ai/todo.md` 상단 섹션

### v0.3 (계획)
- 인증/로그인 시스템, PWA, REST API (`/api/v1/*`)
- DB 정규화, 멀티유저 지원
- GPX/FIT/TCX Import, CSV/JSON Export
- 메트릭 추가: eFTP(완료), Critical Power(완료), REC/RRI/SAPI/TEROI(완료)

### v0.4 (계획)
- React Native 모바일 앱
- ML 기반 개인화: session_outcomes 누적 → CRS 가중치 자동 도출 (기반 완료, 데이터 축적 중)
- TQI (훈련 품질 지수), PLTD (개인화 역치 자동 탐지)

---

## 기술 스택
- Python 3.11+, SQLite3 (running.db)
- garminconnect[workout] (비공식, Typed Workout 모델 포함)
- httpx (Strava/Intervals/Runalyze API)
- gpxpy, fitparse (GPX/FIT 파싱)
- Flask 3.x (웹 대시보드)
- ECharts (CDN, 차트), SVG (게이지/레이더)
- Mapbox GL JS (지도, 선택, 무료 플랜)
- Open-Meteo API (날씨, 무료, 키 없음)

---

## 브랜치 전략
- `main`: 안정 릴리스 전용, 보호됨
- `dev`: 개발 기본 브랜치, 모든 PR은 dev로
- `claude/*`: Claude Code 작업 브랜치 (dev에서 분기)

---

## 빌드 및 실행 명령어

    python src/db_setup.py                         # DB 초기화/마이그레이션
    python src/sync.py --source all --days 7       # 데이터 동기화
    python src/analyze.py today                    # 오늘 리포트
    python src/analyze.py compare --period week    # 주간 비교
    python src/analyze.py deep --activity-id 123   # 단일 활동 심층 분석
    python src/analyze.py race                     # 레이스 준비도
    python src/analyze.py full --clipboard         # 전체 리포트 클립보드
    python src/plan.py week                        # 이번 주 훈련 계획
    source .venv/Scripts/activate && python src/serve.py   # 웹 대시보드 localhost:18080
    python -m pytest tests/                        # 테스트 (1047개 기준, 2026-03-28)

---

## 핵심 규칙
1. 파일 300줄 이하 유지. 초과 시 모듈 분리
2. 모든 외부 API 호출은 `src/utils/api.py`의 래퍼 함수 사용
3. 비밀 정보(토큰, 비밀번호)는 `config.json`에 저장. 절대 커밋 금지
4. 숫자 계산은 Python에서 수행. LLM은 해석/서술/계획 생성에만 활용
5. 4개 소스의 중복 활동은 timestamp ±5분 AND distance ±3%로 매칭
6. CLI 출력은 마크다운 형식. `--clipboard` 옵션으로 termux-clipboard-set 연동
7. 커밋 메시지: conventional commits (`feat:` `fix:` `docs:` `refactor:` `test:`)
8. 한국어 주석 허용, 코드와 변수명은 영어
9. 프롬프트 템플릿은 `src/ai/prompt_templates/*.txt`에 분리 관리
10. AI 응답 파싱 실패 시 항상 graceful fallback (규칙 기반 등)
11. v0.2 새 기능: 메트릭 데이터 없을 때 에러 대신 "데이터 수집 중" graceful UI
12. 하단 네비게이션 7+1탭: 홈 | 활동 | 레포트 | 훈련 | AI코치 | 동기화 | 설정 (+개발자)

---

## 폴더 구조
```
v0.1/.ai/     — v0.1 히스토리 (완료된 작업 기록, 참고용)
v0.2/.ai/     — v0.2 작업 문서 (todo, roadmap, architecture, metrics 등)
v0.2/         — v0.2 설계 참고 자료 (PDF, HTML 목업, gitignore 대상)
```

---

## Who Is Claude Code
시니어 Python 엔지니어로서 깔끔하고 테스트 가능한 코드를 작성한다.
작업 전 반드시 plan을 세우고 승인을 요청한다.
불필요한 칭찬이나 장황한 설명 없이 핵심만 전달한다.
파일 생성과 수정은 확인 없이 진행하되, 설계 변경은 반드시 확인한다.
