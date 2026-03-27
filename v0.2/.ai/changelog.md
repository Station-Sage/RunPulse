# Changelog

> 이전 이력은 `changelog_history.md` 참조

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

