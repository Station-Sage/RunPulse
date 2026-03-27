# Changelog

> 이전 이력은 `changelog_history.md` 참조

## [v0.4-stream-fix] 2026-03-27

### Stream 데이터 접근 버그 수정 + CTL/ATL 자체 계산

**Stream 접근 경로 수정 (핵심 버그):**
- 동기화: activity_streams 테이블에 저장
- 분석: activity_detail_metrics.stream_file 파일 경로 탐색 → 항상 None!
- 수정: activity_streams DB 테이블 우선 조회 (5곳 전부)
- 영향: EF, Decoupling, VDOT_ADJ(Stream 역치), maxHR(30초 peak), HR존 분석

**CTL/ATL/TSB 자체 계산 (ctl_atl.py 신규):**
- Intervals.icu API가 과거 CTL/ATL 미제공 (최근 ~30일만)
- DailyTRIMP 기반 EMA: CTL(42일), ATL(7일), TSB=CTL-ATL
- Intervals 값 있는 날짜는 스킵, 없는 날짜만 source='runpulse'로 채움

**레이스 분류기 수정:**
- 원본 event_type 태그 최우선 (Garmin "race" → 무조건 레이스)
- 풀마라톤 HR 75%+ 대응 (기존 90% → 거리별 차등)

**MarathonShape VDOT_ADJ 통일:**
- DARP/eFTP/MarathonShape 모두 VDOT_ADJ 사용 → Shape 카드 간 일관성

**DARP Shape 배지:**
- half → full → 10k → 5k 우선순위로 목표 거리 Shape 표시

---

## [v0.4-race-vdot] 2026-03-27

### 레이스 기반 VDOT + 예측 정밀화

**VDOT 소스 우선순위 변경:**
- ①최근 레이스(8주 이내) → ②고강도 가중 평균 → ③Runalyze/Garmin
- 레이스 검증: HR 82%+, 공식 거리 ±5%, FEARP 환경 보정
- 복수 레이스: 중앙값 + 교차 검증 ±20%

**레이스 예측: 잘못된 테이블 → Daniels 수학 공식:**
- Before: VDOT 44 → 하프 1:33 (테이블 오류)
- After:  VDOT 44 → 하프 1:42 (공식 정확)
- Round-trip 검증: 하프 1:42 → VDOT 44.1 → 예측 1:42:00 ✓

**VDOT_ADJ 보정 범위 축소 (Daniels/Pugh 기준):**
- 레이스 0~4주: ±3%, 4~8주: ±5%, 8주+: ±7%
- Before: ±15% (37.1) → After: ±3% (최소 42.8)

---

## [v0.4-metrics-precision] 2026-03-27

### 메트릭 정밀화 — 논문 기반 전면 재설계

**maxHR 추정:**
- Stream 30초 슬라이딩 윈도우 peak HR (ACSM/Beltz/Robergs 기준)
- 고강도 활동 IQR 이상치 제거 fallback
- 시계열 저장 (28일 캐시, 나이 변화 추적)

**VDOT_ADJ (현재 체력):**
- A. Strava stream 역치 HR 구간(Karvonen HRR 개인화) 페이스 추출
- B. 연속 역치런 평균 페이스 fallback
- C. HR-페이스 회귀 fallback
- Daniels T-pace 역보간 → VDOT
- HR 스파이크 ±30bpm 제거

**Karvonen HRR 역치 범위:**
- restingHR + HRR × 0.75~0.88 (Karvonen 1957, Daniels 2014)
- 안정심박 웰니스 7일 중앙값 사용
- 고정 %maxHR fallback

**Race Shape 논문 기반 가중치:**
- 10K (Midgley 2007): 페이스 40%, 일관성 27%, 볼륨 20%
- 하프 (Schmid 2012): 볼륨 28%, 페이스 25%, 최장 18%
- 마라톤 (Hagan 1981): 볼륨 34%, 최장 27%, 빈도 19%

**DI 보정 거리별 차등:**
- 5K 0%, 10K 최대 2%, 하프 최대 5%, 풀 최대 10%

**DARP Shape 페널티 축소:**
- Shape<70 → 5K 2%, 10K 4%, 하프 7%, 풀 10%

**계산 순서 수정:**
- VDOT_ADJ를 DARP/eFTP 앞으로 이동

**eFTP:**
- VDOT_ADJ Daniels T-pace 우선

---

## [v0.4-sync-tab] 2026-03-27

### 동기화 탭 분리 + AI 응답 품질

**동기화 탭 (/sync):**
- 설정탭에서 동기화/서비스 연결/임포트/재계산 분리 → 독립 `/sync` 탭
- 활동탭에서 동기화 카드 제거 → "동기화 관리 →" 링크
- 하단 네비 7+1탭: 홈|활동|레포트|훈련|AI코치|동기화|설정(+개발자)
- 설정탭에는 "동기화 탭" 바로가기 배너만 남김

**AI 응답 품질 개선:**
- 시스템 프롬프트 대폭 강화 (한국어 전용, 훈련 원칙, 데이터 해석 가이드)
- 훈련 스케줄 상세 형식: 날짜별 워밍업/메인/쿨다운 구간 + Daniels 페이스
- 대화 이력 3→6개 (맥락 유지)
- 데이터 반올림: "21.047509765625km" → "21.0km"
- get_runner_profile 도구에 Daniels 훈련 페이스 포함

**eFTP/VDOT_ADJ/DARP 정확도:**
- eFTP: Daniels T-pace 우선 (5'17" → 4'25")
- VDOT_ADJ: HR 88% 역치 기준, EF 제거 (순수 체력)
- DARP: VDOT_ADJ 우선 + EF ±3% 대칭 보정
- Daniels 레이스 테이블 1 VDOT 단위 (30~60)

---

## [v0.4-daniels-darp-v4] 2026-03-27

### Daniels VDOT 테이블 + Race Shape v3 + DARP v4 (PR #56)

**daniels_table.py (신규):**
- VDOT 30~85 훈련 페이스 (E/M/T/I/R) — Daniels Running Formula 3rd Ed
- VDOT 30~80 레이스 예측 시간 (5K/10K/하프/풀)
- VDOT 30~70 권장 볼륨 (Pfitzinger + Daniels 종합)
- 선형 보간, 거리별 자동 축소 (10K 55%, 하프 70%)

**Race Shape v3 (5요소 종합):**
- 주간 볼륨 35% + 최장 거리 20% + 장거리 빈도 20% + 일관성 15% + 페이스 품질 10%
- Daniels 테이블 기반 목표 (VDOT 50 마라톤: 주 77.5km, 장거리 34km, 25km+ 6회/12주)
- E-pace 품질: Daniels 테이블 정확 E-pace ±15% 범위 검증

**DARP v4 (4요소 보정):**
- 기본: Daniels 테이블 직접 룩업 (임의 근사 공식 제거)
- DI 보정: DI<70 → 최대 +8% (하프/풀)
- Shape 보정: Shape<80 → 최대 +15% (거리별 계수)
- EF 보정: EF≥1.0 → 최대 -3% 보너스, EF<1.0 → 최대 +3% (10K+)
- 모든 UI에 VDOT/DI/Shape/EF 4배지 일관 표시

**기타:**
- 최대심박 이상치 제거: estimate_max_hr() 상위 5개 중앙값 (8파일)
- eFTP HR 역치 필터 (82%+) + GPS 이상치 (3'00"/km) 제거
- 하단 네비: z-index 1000 + safe-area (갤럭시 폴드8)

---

## [v0.4-training-activity-vdot] 2026-03-27

### 훈련탭 UX 개선 (PR #52)
- 워크아웃 인라인 편집: ✎ 버튼 → 유형/거리 변경 폼
- Garmin/CalDAV/플랜 생성 결과 메시지 표시 (?msg= → 상단 배너)
- 플랜 재생성 confirm 대화상자 ("4주 계획을 재생성합니다")
- 주 네비게이션 "오늘" 버튼 (다른 주 볼 때만)
- Silent exception 3곳 → logging 추가

### 활동탭 개선 (PR #52)
- 7개 분석 그룹 `<details>` 접이식: G1-2 펼침, G3-7 접힘
- 빈 그룹 자동 숨김, 페이지 스크롤 대폭 감소

### VDOT 전문화 (PR #53)
- 추정 알고리즘: 베스트 1개 → **가중 평균** (최신 가중 + 장거리 가중)
- HR 검증: 최대심박 75%+ 노력 활동만 (이지런 제외)
- 이상치 제거: 중앙값 ±2SD 벗어난 값 제외
- 우선순위: RunPulse 자체 추정 > Runalyze > Garmin
- 대시보드/레포트 VDOT 소스 통일 (computed_metrics 우선)
- 피트니스 카드에 "Runalyze 43.7 · Garmin 48.0" 소스 비교 표시
- metric_json에 runalyze_vdot/garmin_vo2max 참고값 저장

### AI 채팅 버그 수정 6건 (PR #53)
- AJAX 실시간 채팅 (`/ai-coach/chat-async`):
  즉시 사용자 메시지 표시 + "생성 중..." 로딩 애니메이션 + 응답 (리로드 없음)
- JSON 노출 방지: 코드블록(```) 자동 제거 + `{"suggestions":[]}` 파싱 → 추천질문 칩
- 마크다운 변환 확장: ### 헤딩, - 리스트, 번호 리스트
- 타임스탬프: 클라이언트 로컬 시간 (JS toLocaleString)
- 전체화면: flex 레이아웃 안정화
- 텍스트 입력: AJAX sendChat() (빈 입력 검증)

### 429 Fallback + 캐시 나이 + Lazy Load (PR #49)
- Gemini 429 → Groq 자동 전환 (RateLimitError 예외)
- chat() provider chain fallback 패턴 적용
- AI 캐시 생성 시점 표시 ("AI 3시간 전")
- 활동 상세 서비스 원본 데이터 lazy load (AJAX)

### AI Everywhere 탭별 통합 호출 마이그레이션 (PR #48)
- AI Coach/Wellness/Race → get_tab_ai() 통합 호출 전환
- 개별 get_card_ai_message() 제거
- Report orphaned except 구문 오류 수정

---

## [v0.4-ai-coach-v2] 2026-03-26

### AI 코치 v2 — Function Calling + 의도 감지 + 풍부한 컨텍스트

**Function Calling (Gemini):**
- `tools.py`: 10개 도구 정의 (get_activity, compare_periods, get_race_history 등)
- AI가 사용자 질문에 필요한 데이터를 **직접 판단**하여 DB 조회
- Multi-turn: 최대 3라운드 도구 호출 → 최종 답변 생성
- Groq/Claude/OpenAI fallback: 기존 프롬프트 주입 방식 유지

**의도 감지 + 날짜 추출 (`chat_context.py`):**
- 7개 의도: today, lookup, race, compare, plan, recovery, general
- 한국어 날짜 파싱: "3월 15일", "어제", "지난주 수요일", "2026-03-20"
- Provider별 컨텍스트 전략:
  - Gemini (1M): 30일 풀 활동/메트릭/웰니스/피트니스
  - Claude/OpenAI (200K): 14일 + 의도별
  - Groq (128K): 의도 기반 선택적 수집
- 레이스 이력 + 동일 유형 과거 활동 자동 포함
- 러너 프로필 요약 (주간 평균, VO2Max, 목표 D-day)

**AI 코치탭 UX 개선:**
- 마크다운 볼드 파싱: 깨진 루프 → regex 정확 변환
- 추천질문 플로팅 칩: AI 응답 `[추천: Q1 | Q2 | Q3]` 파싱 → 클릭 가능 칩
- AI provider 배지: 채팅 메시지에 "via gemini" 표시
- 웰니스 카드: HRV/안정심박 상태색 + 수면시간 표시
- 빠른 질문 → 칩 시스템 연동
- 전체화면 토글: z-index 9999 + body overflow hidden + safe-area 패딩
- 채팅 전송 후 `#chatCard` 앵커 → 스크롤 유지
- Genspark iframe 제거 (100% 차단), 수동 연동 UX 개선
- Silent exception → logging 추가

**시스템 프롬프트:**
- 코치 역할 정의 + 응답 규칙 (간결성, 위험 경고, 데이터 근거)
- 추천질문 3개 자동 생성 규칙
- 최근 3개 대화 이력 포함 (맥락 유지)

---

## [v0.4-ai-everywhere] 2026-03-26

### AI Everywhere — 전체 UI AI 해석 통합

**기반 모듈:**
- `ai_message.py`: provider 체인 (선택→gemini→groq→규칙) + 카드별 자동 컨텍스트
- `context_builders.py`: 탭별 컨텍스트 빌더 6개 (시계열 포함)
- `prompt_config.py`: 프롬프트 템플릿 14종 + 사용자 커스텀 병합

**AI 적용 카드 (7곳):**
- 대시보드 훈련 권장, AI 코치 브리핑, 훈련탭 AI 추천
- 레포트 AI 인사이트 (기간별), 웰니스 회복 권장, 레이스 DI 해석

**설정 UI:**
- AI provider별 API 키 발급 링크 (Gemini/Groq 무료, Claude/OpenAI 유료)
- 무료/유료 명시 안내
- 🔧 프롬프트 관리 접이식: 14종 프롬프트 미리보기/수정 + 기본값 복원

---

