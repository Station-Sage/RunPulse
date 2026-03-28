# v0.2 작업 목록

최종 업데이트: 2026-03-28 (훈련탭 UX 재설계 Phase C 완료 — Wizard 4단계)

---

## ▶ 다음 세션 시작 시 여기부터 (2026-03-28 기준)

### 최근 완료 요약 (상세: `changelog.md` 참조)
- **Phase C 완료**: 4단계 AJAX Wizard (`/training/wizard`)
  - `views_training_wizard.py` 신규 (Blueprint + 3 라우트)
  - `views_training_wizard_render.py` 신규 (Step 1~4 HTML 렌더러, JS)
  - Step 1: 목표 이름/종목/날짜/시간·페이스 입력
  - Step 2: 환경 설정(휴식·롱런 요일, 인터벌 거리, 훈련 기간)
  - Step 3: `readiness.analyze_readiness()` 호출 — 달성률·예상 기록·경고 표시 (DB 없으면 graceful)
  - Step 4: 플랜 요약 + 생성 버튼 → `POST /training/wizard/complete`
  - `wizard_bp` app.py 등록
  - 목표 없을 때 "🗓️ 훈련 계획 시작하기" 버튼 (`views_training_cards.py`)
  - `tests/test_training_wizard.py` 18개 통과
- **현재 상태: SCHEMA_VERSION=3.1(내부4), 1097 테스트 통과 (2026-03-28)**

### 다음 우선 작업 — Phase D부터 시작

**Phase D: 워크아웃 편집 메뉴**
- [ ] 각 워크아웃 카드 `⚙️` 편집 버튼 + inline 패널 (AJAX)
- [ ] `PATCH /training/workout/<id>` 편집 라우트
- [ ] 인터벌 타입: `interval_calc.py` 재계산 연동

**Phase E: 전체 계획 뷰**
- [ ] `planner.py` — 전체 기간(N주) 계획 생성 함수 추가
- [ ] `src/web/views_training_fullplan.py` 신규 (표/캘린더 뷰, Collapsible)

**Phase F: 비교 차트 + 훈련 분석 카드**
- [ ] 계획 vs 실제 km 비교 바 차트 (ECharts)
- [ ] 달성도·가능률·예상 기록 카드 (`readiness.analyze_readiness()` 연동)
- [ ] Q-day 달성률, 페이스 준수율 뱃지

**Phase G: 목표 관리 개선**
- [ ] 이전 목표 Collapsible 섹션 + [불러오기] 버튼

---

## 현재 미완료 작업 (이 섹션만 읽을 것)

### UI 재설계 (v0.2/UI_redesign.md 기준, §9.2 순서)

- [x] **UI-R1**: 활동 상세 재설계 — 7개 목적별 그룹 + 서비스 접이식
  - 신규 파일 10개 (g1~g7, cards_common, map, loaders_v2)
  - 신규 차트: G4 멀티라인(ACWR/Monotony/Strain/LSI), G5 RMR 레이더, G2 EF/Dec 스파크라인, G6 TIDS 주간
  - 승격: VO2Max/GCT/수직진동/보폭 (서비스탭→메인), Training Readiness
  - 884 테스트 통과 (2026-03-25)
- [x] **UI-R2**: 대시보드 재설계 — 웰니스 미니, RTTI, 주간 요약, EF 스파크라인, Monotony/Strain
- [x] **UI-R3**: 레포트 재설계 — 시계열 차트 6종, 비교 델타, 폼 섹션, 웰니스 기간
- [x] **UI-R4**: 웰니스 보강 — 기준선 밴드, 패턴 인사이트, 주간 비교, 수면/HRV 미니차트
- [x] **UI-R5**: 레이스 예측 보강 — DARP/VDOT/DI 추세, 목표 갭, MarathonShape, 메트릭 해설
  - 신규: views_race_enhanced.py (로더 2 + 렌더러 5)
  - 추가 섹션: 목표 갭 계산기, 예측 추세 차트, 준비 요소 차트, DI 해석, 메트릭 해설
  - 884 테스트 통과 (2026-03-25)
- [x] **UI-GAP**: 스펙 갭 해소 8건 (UI_redesign.md 대비 누락 항목)
  - 웰니스: 메트릭 해설 접이식, 수면 시간대 패턴, 이상치 빨간 점, BB/수면/스트레스 기준선 배지, 패턴→회복 권장 연동
  - 레포트: TRIMP 이전 기간 비교선 (회색 점선)
  - 레이스: 목표 갭 기반 구체적 훈련 권장 (VDOT/DI 연동)
  - 활동 상세: ADTI 데이터 연결 버그 수정
  - 스펙 충족률 88% → 98%, 884 테스트 통과 (2026-03-25)

### v0.2 잔여

- [x] **6.4**: Settings 보완 — sync 상태 허브, 시스템 정보 카드
- [x] **6.5**: Race Prediction 잔여 — 예측 이력 테이블
- [x] **6.6**: AI Coach 잔여 — 최근 훈련 요약, 리스크 요약 카드
- [x] **6.7**: Training Plan UI 재설계
  - 7열 그리드 캘린더 + 주 네비게이션 (?week= 파라미터)
  - UTRS/CIRS 통합 (목표 카드 + 주간 요약 + AI 추천)
  - AI 훈련 추천 카드 (규칙 기반, UTRS/CIRS 연동)
  - 데이터 연동 상태 (Garmin/Strava/Intervals/Runalyze)
  - 헤더 액션 (공유 + 플랜 생성 버튼)
  - 파일 분리: loaders.py + cards.py + 메인 라우트
  - 875 테스트 통과 (2026-03-25)
- [x] **6.8**: Wellness 보완 — 7일 트렌드 차트, 회복 권장 카드
- [x] **S5-C2**: 대폭 확장된 데이터 반영 UI 노출
- [x] **V2-5-3**: Report AI 인사이트 실체화
- [x] **V2-5-4**: Report 기간 선택기 7개 확장
- [x] **V2-6-1a~f**: 레이스 예측 UI 보강
- [x] **V2-7-1a~e**: AI 코칭 UI 보강
- [x] **V2-9-12~14, B-4**: 문서/참고디자인 수정

### v0.3 예정 (메트릭)

- [x] **V3-1-3**: eFTP — Intervals FTP 우선 + 고강도 활동 페이스 기반 자체 추정
- [x] **V3-1-4**: CP/W' — 2파라미터 선형 회귀 (파워 데이터 있을 때)
- [x] **V3-2-1**: REC — EF×Decoupling×폼 종합 효율성 (0~100)
- [x] **V3-2-2**: RRI — VDOT진행률×CTL충족률×DI×안전계수 (0~100)
- [x] **V3-2-3**: SAPI — 기온 구간별 FEARP 비교 (기준 10~15°C 대비)
- [x] **V3-2-4**: TEROI — CTL 변화/TRIMP 투입 ROI (28일 단위)
- [x] **V3-2-5**: VDOT_ADJ — HR-페이스 회귀 + EF 추세 기반 VDOT 보정

### v0.3 예정 (인프라)

- [ ] 인증/로그인 시스템 (bcrypt, 세션, 리다이렉트)
- [x] PWA (오프라인, manifest, service worker) — manifest.json, sw.js, offline.html, 4 아이콘, 메타 태그, 15 테스트
- [x] DB 쿼리 성능 최적화 — 배치 로더 (N+1 제거), TTL 캐시, 대시보드 25→8쿼리, 레포트 N+1 제거
- [ ] REST API (`/api/v1/*`)
- [ ] DB 정규화, 멀티유저 강화
- [x] AI 채팅 (대화형 코칭) — chat_messages 테이블, POST /ai-coach/chat, 교체 가능 엔진 (rule/claude/openai), 칩 트리거, 히스토리 UI
- [x] Training Plan 풀 구현 — 워크아웃 CRUD, 완료 토글, 목표 웹 UI, ICS 내보내기
- [ ] (향후) 캘린더 API 연동 (Google Calendar / 네이버 캘린더 / Garmin Connect 선택)
- [x] Garmin Connect 워크아웃 전송 (캘린더 + 워치) + CalDAV 연동
- [x] Genspark AI 연동 B방식 (프롬프트 복사 + 응답 붙여넣기) + ~~A방식~~ Cloudflare 403 차단
- [x] Google Gemini API 연동 (무료 1,500 RPD) + Groq API 연동 (무료 14,400 RPD)
- [x] Genspark iframe 내장 (AI 코치 탭)
- [x] AI Everywhere v2: 탭별 1회 통합 호출 + DB 캐시 + 검증/재시도 + 13곳 AI + 전체화면 채팅 + AI 업데이트 버튼
- [x] AI 코치 v2: Gemini Function Calling (10도구) + 의도 감지 7종 + 날짜 추출 + Provider별 컨텍스트 전략 + 추천질문 칩 + UX 10건 개선
- [x] MCP 서버 (src/mcp_server.py) — Claude Desktop/CLI에서 RunPulse DB 직접 접근 (10개 도구)
- [x] Gemini 429→Groq 자동 fallback (RateLimitError) + chat() provider chain
- [x] AI 캐시 나이 표시 ("AI 3시간 전") + 서비스 탭 lazy load (AJAX)
- [x] 훈련탭 UX: 워크아웃 인라인 편집(✎) + 결과 메시지 표시 + 플랜 재생성 확인 + "오늘" 버튼
- [x] 활동탭: 7그룹 접이식 (G1-2 펼침, G3-7 접힘) + 서비스 탭 lazy load
- [x] VDOT 전문화: 가중 평균 + 이상치 제거 + HR 검증, 자체 추정 최우선, 소스 비교 UI
- [x] Daniels VDOT 룩업 테이블 (30~85, 페이스/레이스/볼륨) + 선형 보간
- [x] Race Shape v3: 5요소 (볼륨35%+최장20%+빈도20%+일관성15%+페이스품질10%) + Pfitzinger 기준
- [x] DARP v4: Daniels 테이블 + DI + Shape + EF 4요소 보정, 모든 UI 일관성
- [x] 최대심박 이상치 제거: estimate_max_hr() 상위 5개 중앙값 (8파일)
- [x] eFTP HR 역치 필터 (82%+) + GPS 이상치 제거 (3'00"/km)
- [x] 하단 네비 z-index 1000 + safe-area (갤럭시 폴드)
- [x] 동기화 탭 분리: 설정/활동에서 동기화 → /sync 독립 탭 (7+1탭)
- [x] AI 시스템 프롬프트 강화: 훈련 스케줄 상세 형식, 한국어 전용, 데이터 반올림
- [x] maxHR: Stream 30초 peak HR + IQR 이상치 제거 + 시계열 저장 (ACSM/Beltz 기준)
- [x] VDOT_ADJ: Stream 역치 HR 구간 페이스 추출 + Karvonen HRR 개인화
- [x] Race Shape 논문 기반 가중치 (Midgley/Schmid/Hagan)
- [x] DI 보정 거리별 차등 (5K 0%, 10K 2%, 하프 5%, 풀 10%)
- [x] 레이스 기반 VDOT 1순위 (8주 이내, HR/거리/FEARP 검증)
- [x] 레이스 예측: 잘못된 테이블 → Daniels 수학 공식 직접 계산
- [x] VDOT_ADJ 보정 범위: ±3~7% (레이스 경과 기간별, Daniels/Pugh 기준)
- [x] 메트릭 계산 순서 수정 (VDOT_ADJ → DARP/eFTP 앞으로)
- [x] Stream 접근 버그 수정: activity_streams 테이블 연결 (5곳)
- [x] CTL/ATL/TSB 자체 계산 (DailyTRIMP 기반 EMA, Intervals 미제공 구간)
- [x] 훈련 이행 추적 — 어제 체크인 카드, 계획 vs 실제 캘린더 비교, skip(-1)/confirm(1) 구분
- [x] 훈련 재조정 — 건너뜀 시 고강도→빈 날 이동, 연속 건너뜀 시 볼륨 10% 축소 (replanner.py)
- [x] 날짜 기반 계획↔활동 자동 매칭 (matcher.py)
- [x] DB 스키마 v2 마이그레이션 — planned_workouts에 skip_reason, updated_at 컬럼
- [x] AI 브리핑 이행 현황 연동 — ai_context/context_builders에 yesterday_plan + plan_compliance, briefing.txt 항목 4/5 업데이트
- [x] 재계산 365일 제한 제거 — days=0 시 전체 기간(DB 최초 활동부터), sync 탭 GET /recompute-metrics 라우트 추가
- [x] 레이스 분류기: 소스 태그 기반으로 전면 교체 (Garmin event_type / Strava workout_type / Intervals sub_type+race)
- [x] Intervals sync: sub_type='RACE' + race=True 필드 캡처 (category 대신)
- [x] VDOT_ADJ 버그 수정: source 키 누락 + T-pace 블렌딩 (easy run HR 오염 방지)
- [x] VDOT_ADJ 보정 범위 재정의: 4주이내 ±1%, 4~8주 ±3%, 8주+ ±7%
- [x] 대시보드 DARP 갱신: _ensure_today_metrics에 DARP_half 조건 포함
- [x] 레이스 탭: 오늘 DARP 없으면 자동 재계산
- [x] 훈련 권장 카드: ACWR/CIRS/DI 종합 보정 + 계획된 훈련 비교 블록
- [x] Shape 라벨 소스 일치: DARP 소스 거리로 라벨 결정 (값·라벨 불일치 버그)
- [x] 목표 거리 기반 Shape 우선 표시 (대시보드 DARP 카드 + 피트니스 카드)
- [x] MarathonShape/DARP/eFTP VDOT_ADJ 통일 → Shape 카드 일관성
- [x] AI 채팅 AJAX: 실시간 메시지 + "생성 중..." 로딩 + JSON 노출 방지 + 마크다운 확장
- [x] 프롬프트 복사 보강: 30일 풀 데이터 (Gemini 1M 대응)
- [x] 채팅 타임스탬프: 클라이언트 로컬 시간 (JS toLocaleString)
- [ ] (향후) ngrok 터널링 / VPS 배포 — 외부 AI 서비스에서 API 접근
- [x] Mapbox → Leaflet+OSM 전환 (완전 무료, API 키 불필요)
- [x] 운동 유형 자동 분류기 (HR존/페이스/거리 기반 7분류)
- [x] 용어집/가이드 페이지 (/guide) — 25개 메트릭 상세 + 분류 기준
- [x] UI 피드백 25건 수정 (버그 10 + 툴팁 5 + UX 5 + 활동탭 4 + 추가 버그)
- [x] ACWR 표준 공식 수정 + DI 0~100 스케일 변환 + DARP 완주 시간 표시
- [x] AI 채팅 키워드 매칭 8분기 + 브리핑 코치 톤
- [x] 기간 동기화 시 기존 활동 업데이트 (INSERT OR REPLACE)
- [x] GPS 경로 SVG 썸네일 (API 없이 자체 렌더링)
- [x] 설정: AI provider/API 키 + 프로필 추정값 + 적용 버튼

### 미해결 버그 (v0.3) — 수정 완료, 재동기화 후 확인 필요

- [x] Strava detail 수집 누락 — force_streams 시 detail 강제 재조회 (PR #36)
- [x] Garmin aerobic TE — 추가 키 fallback (PR #35, 재동기화 필요)
- [x] 웰니스 빈 값 — bg_sync에 웰니스 호출 + from_date 지원 (PR #37)

### v0.4 예정

- [ ] React Native 모바일 앱
- [ ] **V4-1-1**: TQI (훈련 품질 지수) — ML 기반
- [ ] **V4-1-2**: PLTD (개인화 역치 자동 탐지) — ML 기반
- [ ] **V2-9-4a**: GPX/FIT/TCX 개별 파일 Import (v0.2에서 이동)
- [ ] **V2-9-4b**: CSV/JSON Export (v0.2에서 이동)

---
---

## 아래는 완료 히스토리 (참고용)

---

## 메트릭 전체 현황

### 1차 메트릭 커버리지

| 메트릭 | 상태 |
|--------|------|
| ATL/CTL/TSB (PMC) | ✅ v0.2 |
| TRIMP / HRSS | ✅ v0.2 |
| rTSS | ✅ v0.2 |
| VDOT | ✅ v0.2 |
| Aerobic Decoupling | ✅ v0.2 |
| GAP / NGP | ✅ v0.2 |
| EF (효율 계수) | ✅ v0.2 |
| Monotony & Strain | ✅ v0.2 |
| Relative Effort | ✅ v0.2 |
| Marathon Shape | ✅ v0.2 |
| Running Dynamics | ✅ v0.2 |
| eFTP | ⏳ v0.3 |
| Critical Power | ⏳ v0.3 |

### 2차 메트릭 (RunPulse 고유)

| 코드 | 명칭 | 상태 |
|------|------|------|
| UTRS | 통합 훈련 준비도 | ✅ v0.2 |
| DI | 내구성 지수 | ✅ v0.2 |
| CIRS | 복합 부상 위험 | ✅ v0.2 |
| LSI | 부하 스파이크 | ✅ v0.2 |
| ACWR | 급성/만성 부하 비율 | ✅ v0.2 |
| FEARP | 환경 보정 페이스 | ✅ v0.2 |
| ADTI | 유산소 분리 추세 | ✅ v0.2 |
| TIDS | 훈련 강도 분배 | ✅ v0.2 |
| DARP | 내구성 보정 레이스 예측 | ✅ v0.2 |
| RMR | 러너 성숙도 레이더 | ✅ v0.2 |
| RTTI | 러닝 내성 훈련 지수 | ✅ v0.2 |
| WLEI | 날씨 가중 노력 지수 | ✅ v0.2 |
| TPDI | 실내/야외 퍼포먼스 격차 | ✅ v0.2 |
| REC | 통합 러닝 효율성 | ⏳ v0.3 |
| RRI | 레이스 준비도 지수 | ⏳ v0.3 |
| SAPI | 계절·날씨 성과 비교 | ⏳ v0.3 |
| TEROI | 훈련 효과 ROI | ⏳ v0.3 |
| TQI | 훈련 품질 지수 | ⏳ v0.4 (ML) |
| PLTD | 개인화 역치 탐지 | ⏳ v0.4 (ML) |

---

## Phase 0: 기반 준비 ✅ 완료

- [x] V2-0-1~3: DB 스키마 확장, Open-Meteo 날씨, 마이그레이션 테스트

## Phase 1: 2차 메트릭 계산 엔진 ✅ 완료

- [x] 그룹 A: GAP/NGP/LSI/FEARP/ADTI/TIDS/RelativeEffort/MarathonShape + store
- [x] 그룹 B: ACWR/TRIMP/Monotony/UTRS/CIRS/Decoupling/DI/DARP/RMR + engine

## Phase 2: 동기화 후 메트릭 자동 계산 ✅ 완료

- [x] sync 후 engine 호출, 재계산 엔드포인트

## Phase 3: 통합 대시보드 UI ✅ 완료

- [x] UTRS/CIRS 게이지, RMR 레이더, PMC 차트, 최근 활동

## Sprint 4-A/B/C: UI 기반 + Jinja2 + 화면 구현 ✅ 완료

- [x] ECharts, bottom_nav, 다크 테마, templates, 활동 상세 2차 메트릭, 레포트

## Phase UI-Gap: v0.2 UI 보완 ✅ 부분 완료

- [x] 6.1~6.3: Dashboard/Activity/Report 보완
- [x] 7.3: Strava Archive Import UI

## Phase API-Garmin/Strava/Intervals: 전체 API 수집 ✅ 완료

- [x] Garmin: 80컬럼 확장, streams/gear/exercise_sets, 일별 확장, 선수 데이터
- [x] Strava: 모듈 분리, 29컬럼, streams DB, best_efforts, athlete/stats/gear
- [x] Intervals: 모듈 분리, 31컬럼, intervals/streams, athlete/stats

## Phase PERF: 성능 개선 ✅ 완료

- [x] 복합 인덱스, 페이지네이션, TTL 캐시, 4소스 병렬 sync

## Sprint 5: 데이터 파이프라인 + 레이스 + AI 코칭 ✅ 완료

- [x] 5-A: 데이터 레이어 아키텍처 (4계층)
- [x] 5-B: 병렬 동기화, Garmin/Strava/Intervals 신규 API
- [x] 5-C: RTTI/WLEI/TPDI 메트릭, zone fallback
- [x] 5-E: 버그 수정 (hex 오분류, 서비스 메트릭 누락 등)
- [x] 5-F: API 데이터 감사 (Bug #1~#5, Check #6~#7)
- [x] /race 레이스 예측, /ai-coaching AI 코칭, /wellness 웰니스

## Sprint 5-D: 미완료 항목 처리 ✅ 부분 완료

- [x] S5-B1: 재계산 ETA 표시
- [x] S5-C1: 서비스 탭 UI 분리

## Phase 6-7: 레이스 예측 + AI 코칭 ✅ 기본 구현 완료

- [x] /race (DARP, DI, 페이스전략, HTW)
- [x] /ai-coach (브리핑, 추천칩, 웰니스 컨텍스트)

## Phase 8-9: 훈련 계획 + 설정 + 마무리 ✅ 기본 완료

- [x] V2-8-1a/b: /training 스캐폴딩 + 기본 구현
- [x] V2-9-3~V2-9-11: graceful fallback, Settings hub, 통합 테스트, 리다이렉트, DB 마이그레이션, Mapbox

## Multi-User ✅ 기본 완료

- [x] 사용자별 DB/config 분리, Flask 세션, CLI --user

## Priority B ✅ 부분 완료

- [x] B-1: 파일 크기 리팩토링 (helpers_svg, views_activity 분리 등)
- [x] B-2: graceful fallback 전면 보강
- [x] B-3: Settings hub 고도화

---

테스트: **945개** 통과 (2026-03-27 기준, fitparse 미설치 3파일 제외)
