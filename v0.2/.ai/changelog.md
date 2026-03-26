# Changelog

> 이전 이력은 `changelog_history.md` 참조

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

## [v0.4-ai-providers] 2026-03-26

### AI 제공자 확장

- **Google Gemini**: 무료 API (1,500 RPD, gemini-2.0-flash)
- **Groq**: 무료 API (14,400 RPD, llama-3.3-70b-versatile)
- **Genspark iframe**: AI 코치 탭에 내장
- **Genspark B방식**: 프롬프트 복사 + 응답 붙여넣기
- **Genspark A방식**: Cloudflare 403으로 보류
- 설정 UI: 6개 provider 선택 + API 키 입력 + 발급 링크
- `start.sh`: proot bind mount 서버 시작 스크립트

지원: rule / gemini / groq / genspark / claude / openai

---

## [v0.4-calendar-ai] 2026-03-26

### Garmin Connect 워크아웃 전송
- `garmin_push.py`: upload_running_workout → schedule_workout → DB에 garmin_workout_id 저장
- 타입별 워크아웃 구조: easy/tempo/threshold(워밍업+메인+쿨다운), interval(3분×5 반복)
- 훈련탭 "⌚ Garmin" 버튼

### CalDAV 캘린더 연동
- `caldav_push.py`: iCal 이벤트 생성 → CalDAV 서버 등록 (Google/네이버/Apple/Synology)
- 설정: URL + 사용자명 + 앱 비밀번호 + 연결 테스트
- 훈련탭 "📅 캘린더" 버튼

### Genspark AI 연동
- **B방식 (수동)**: 프롬프트 복사 → Genspark/ChatGPT/Claude에 붙여넣기 → 응답 저장
  - /ai-coach/prompt (프롬프트 생성 API), /ai-coach/paste-response (응답 저장)
  - 외부 AI 연동 접이식 섹션 (링크 + 복사 + 붙여넣기)
- **A방식 (자동)**: proot + Selenium headless Chromium으로 Genspark DOM 자동화
  - `genspark_driver.py`: send_and_receive(), 다중 셀렉터, 응답 polling

### 훈련 계획 개선
- 4주치 플랜 한 번에 생성 + 빈 주 자동 생성
- 전체 훈련 계획 개요 카드 (base/build/peak/taper 타임라인)

### 성능
- WorkoutType N+1 → 배치 로드
- Garmin per_request_sleep 1.5→0.8초

---

## [v0.3-training-fixes] 2026-03-26

### 훈련탭 + AI코치 + 데이터 버그 수정

**ACWR 공식 수정:**
- 기존: sum(7일) / mean(28일 중 >0인 날만) → 비정상 고값 (5.29)
- 수정: (sum(7일)/7) / (sum(28일)/28) = 표준 공식

**DI 스케일 변환:**
- 비율값(0.8~1.2) → 0~100 스케일 (1.0 → 70점, 0.80 → 20점)

**DARP 표시 수정:**
- 예측 카드/이력: metric_value(페이스) → metric_json.time_sec(완주 시간)
- 대시보드 DARP 미니: VDOT/DI 배지 상단 표시

**AI 코치:**
- 브리핑: 숫자 나열 → 코치 톤 종합 판단 + 조언
- 채팅: 8개 키워드 분기 (강도/레이스/회복/페이스/부상/주간/피트니스/일반)
- 설정: AI provider 선택 (규칙/Claude/ChatGPT) + API 키 입력

**훈련탭:**
- 컨디션 카드: CIRS/UTRS 경고 반영 + 피로도 한국어
- 목표 관리: 활성 목표 없으면 폼 자동 펼침
- CLI 안내 제거 → 웹 UI 안내

**설정:**
- 프로필 추정값 표시 (최대HR/역치/주간거리) + '적용' 버튼
- 마지막 동기화 시간: sync_jobs.db에서 조회

**대시보드:**
- 동기화 버튼 → POST /trigger-sync (설정 이동 대신 바로 시작)
- 툴팁 모바일 넘침 방지 (fixed 중앙)

**GPS 경로:**
- 그룹 내 다른 소스에서 latlng 자동 탐색 (Garmin 대표 + Strava GPS)

**Garmin aerobic TE:**
- 추가 키 fallback (act/trainingEffectAerobic)

**설정:**
- 프로필 RunPulse 추정값 표시 (최대HR/역치/주간거리) + '적용' 버튼
- 마지막 동기화: sync_jobs.db에서 조회 (별도 DB)

**미해결:**
- Strava detail 수집 누락 (best_efforts/zones 미저장)
- Garmin aerobic TE 실제 API 키 확인 필요
- 웰니스 3/13~3/18 데이터 빈 값 원인 조사

**테스트:** 904개 통과

---

## [v0.3-metrics] 2026-03-26

### v0.3 신규 메트릭 7개

**신규 파일:**
- `src/metrics/eftp.py`: eFTP — Intervals FTP 우선, 없으면 40~70분 고강도 활동 페이스 추정
- `src/metrics/rec.py`: REC — EF × (1-Dec%) × 폼팩터, 7일 평균 기반 (0~100)
- `src/metrics/teroi.py`: TEROI — CTL 변화 / 총 TRIMP × 1000 (28일 단위 ROI)
- `src/metrics/rri.py`: RRI — VDOT진행률 × CTL충족률 × DI × (100-CIRS)/100 (0~100)
- `src/metrics/sapi.py`: SAPI — 기온 구간별 FEARP 비교 (기준 10~15°C 대비 비율)
- `src/metrics/vdot_adj.py`: VDOT_ADJ — HR-페이스 선형 회귀 + EF 28일 추세 보정
- `src/metrics/critical_power.py`: CP/W' — P×t=W'+CP×t 2파라미터 선형 회귀

**수정:**
- `engine.py`: 13~19번 신규 메트릭 등록 (TPDI 다음, 일별 계산)
- `helpers.py`: METRIC_DESCRIPTIONS에 7개 메트릭 설명 추가

**테스트:** 904개 통과

---

## [v0.3-ui-fix] 2026-03-26

### UI 버그 수정 10건

**D1**: 대시보드 접속 시 오늘 메트릭 자동 재계산 (`_ensure_today_metrics`)
**D2/R11**: VDOT 조회 개선 — computed_metrics 우선 + Garmin VO2Max fallback
**D4**: 게이지 arc large-arc-flag 수정 (50% 이상 정상 렌더링) + 다크 테마 트랙 색상
**D6**: RTTI 자체 추정 fallback — ATL/(CTL×wellness_factor) 공식
**R3/R4**: 주별 차트 X축 YYYY-WW → M/D 형식 (주 시작일)
**R5**: Decoupling% 별도 Y축 분리 (EF/VO2Max/Dec 3축)
**R7/R9**: 리스크·컨디션 추세 범례-실선 색상 일치 (itemStyle+symbol)

### 메트릭 설명 툴팁 5건

- `helpers.py`: `tooltip()` 함수 + `METRIC_DESCRIPTIONS` 17개 메트릭 설명 사전
- CSS `.rp-tip`: 호버/터치 팝업 (다크 테마, 280px, 모바일 클릭 토글)
- **D5**: 대시보드 UTRS/CIRS/ACWR/RTTI 게이지 툴팁
- **D8**: 리스크 pill에 적정 범위 + 상태 배지 (적정/주의/위험)
- **R2**: 레포트 평균 UTRS/CIRS 툴팁
- **R6**: TIDS 모델명 설명 (폴라리제드/피라미드/건강유지) + 편차 점수 해석
- **R8**: 위험 지표 개요에 적정 기준값 + 상태 표시

### 활동탭 리뉴얼 4건

- **A1**: 동기화 카드 → 접이식으로 하단 이동 (기본 접힘)
- **A2**: 필터 전체 접이식 전환 — 검색바만 항상 노출, 나머지 '상세 필터' 토글
- **A3**: 모바일 날짜 축약 (640px 이하에서 연도+시간 숨김, 날짜 컬럼 축소), uncategorized 등 불필요 태그 숨김
- **A4**: 소스비교 차이 강조 임계값 0.5% → 5% (의미 있는 차이만 강조)

### UX 개선 5건

- **D3**: 최근활동에 훈련 이름(name) 표시 (활동 제목 우선, 없으면 '러닝')
- **D7**: RMR 기간 기준 표시 (최근 28일 날짜 범위) + 툴팁
- **D9**: 대시보드 상단에 마지막 동기화 시간 + 동기화 버튼
- **R10**: 레이스 예측 VDOT 공통 상단 표시 + DI 내구성 지수 추가
- **R12**: 최근활동 메트릭에 효과 컬럼 (고강도 자극/적정 부하/유산소 양호 등)

### 기타

- RTTI 자체 추정: `ATL / (CTL × wellness_factor) × 100` (Garmin 데이터 없을 때)
- VDOT: `src/metrics/vdot.py` (기존) Jack Daniels 정확 공식 + best_efforts + 고강도 활동 추정
- MarathonShape: `_get_vdot` Garmin VO2Max fallback + 자체 추정 연결
- bg_sync: 동기화 후 오늘까지 메트릭 계산 보장
- todo: V3-2-5 VDOT HR-페이스 회귀 보정 추가

**테스트:** 904개 통과

---

## [v0.3-ai-chat-training] 2026-03-26

### AI 대화형 코칭

**신규 파일:**
- `src/ai/chat_engine.py` (175줄): 교체 가능 AI 엔진
  - `chat()`: 메시지 → 컨텍스트 빌드 → AI 응답 생성
  - 4개 provider: `rule` (기본, 규칙 기반), `claude`, `openai`, `genspark`
  - `_rule_based_response()`: API 없이 메트릭 기반 응답 생성
  - `_call_claude()`, `_call_openai()`: httpx 기반 API 호출

**수정:**
- `src/db_setup.py`: `chat_messages` 테이블 추가 (role, content, chip_id, ai_model)
- `views_ai_coach.py`: `POST /ai-coach/chat` 라우트, `_load_chat_history()`, 칩→채팅 연동
- `views_ai_coach_cards.py`:
  - `render_chat_section()`: disabled 스텁 → 활성 채팅 UI (히스토리, 입력, 빠른 질문)
  - `render_chips()`: 칩 클릭 → POST /ai-coach/chat 폼 제출

### Training Plan 풀 구현

**신규 파일:**
- `views_training_crud.py` (277줄): CRUD + 목표 + ICS 분리
  - `POST /training/workout`: 워크아웃 생성
  - `POST /training/workout/<id>/update`: 수정
  - `POST /training/workout/<id>/delete`: 삭제
  - `POST /training/workout/<id>/toggle`: 완료 토글
  - `POST /training/goal`: 목표 추가
  - `POST /training/goal/<id>/complete|cancel`: 목표 상태 변경
  - `GET /training/export.ics`: iCal 내보내기

**수정:**
- `views_training.py`: 목표 폼 + 워크아웃 폼 UI (접이식)
- `views_training_cards.py`: 캘린더 그리드에 완료 토글 ✓ / 삭제 ✕ 버튼 + ICS 내보내기 링크
- `app.py`: `training_crud_bp` Blueprint 등록

**테스트:** 904개 통과

---

## [v0.3-perf] 2026-03-25

### DB 쿼리 성능 최적화

**신규 파일:**
- `src/web/views_perf.py`: 배치 로더 4개 + TTL 캐시 (30초)
  - `load_metrics_batch()`: 여러 일별 메트릭 1쿼리 로드 (기존 개별 6~9회 → 1회)
  - `load_metrics_json_batch()`: 여러 JSON 메트릭 1쿼리 로드 (기존 3회 → 1회)
  - `load_activity_metrics_batch()`: N+1 제거 — 활동 ID 리스트로 IN절 1쿼리
  - `load_darp_batch()`: DARP 4거리 1쿼리 로드 (기존 루프 4회 → 1회)
  - `cached_page()`: 페이지별 TTL 캐시, `invalidate_cache()` 무효화

**대시보드 최적화** (`views_dashboard.py`):
- `_load_metric()` 7회 + `_load_metric_json()` 4회 → `load_metrics_batch` 2회
- `_load_recent_activities()` N+1 (5×2=10쿼리) → `load_activity_metrics_batch` 1회
- `_load_darp_data()` 루프 4회 → `load_darp_batch` 1회
- 페이지 TTL 캐시 적용 (30초)
- **예상: 25~30쿼리 → 8~10쿼리 (70% 감소)**

**레포트 최적화** (`views_report.py`):
- `_load_activity_metrics()` N+1 (15×1=15쿼리) → `load_activity_metrics_batch` 1회
- **예상: 15쿼리 → 1쿼리**

**테스트:** 904개 통과 (신규 14개: 배치 로더 10 + 캐시 4)

---

## [v0.3-pwa] 2026-03-25

### PWA 인프라 구현

**신규 파일:**
- `static/manifest.json`: PWA 매니페스트 (standalone, theme #1a1a2e, 아이콘 4종)
- `static/sw.js`: Service Worker — Cache First (CDN/정적), Network First (HTML→offline fallback, API)
- `static/offline.html`: 오프라인 폴백 페이지 (다크 테마, 재시도 버튼)
- `static/icons/`: icon-192.png, icon-512.png, icon-192-maskable.png, icon-512-maskable.png (플레이스홀더)
- `tests/test_pwa.py`: 15개 테스트 (정적 파일, 메타 태그, 매니페스트 무결성)

**수정:**
- `src/web/app.py`: Flask static_folder를 프로젝트 루트 `static/`으로 설정
- `src/web/helpers.py`: html_page()에 PWA 메타 태그 (theme-color, manifest, apple-touch-icon) + SW 등록 스크립트
- `templates/base.html`: 동일 PWA 메타 태그 + SW 등록 (Jinja2 경로)

**SW 캐시 전략:**
- `cacheFirst`: CDN (ECharts, Google Fonts), 정적 파일
- `networkFirstHtml`: HTML 페이지 → 캐시 → offline.html 폴백
- `networkFirst`: API/기타

**테스트:** 890개 수집 (PWA 15개 추가)

---

## [v0.2-training-ui] 2026-03-25

### 6.7 Training Plan UI 재설계

**신규 파일:**
- `views_training_loaders.py`: DB 로더 5개 (goal, workouts, adjustment, metrics, sync_status)
- `views_training_cards.py`: 카드 렌더러 7개 (S1~S7)
- `test_web_training.py`: 통합 + 단위 테스트 40개

**views_training.py 리팩터:**
- 기존 300줄 → 100줄 (로더/카드 분리)
- `?week=` 쿼리 파라미터로 주 네비게이션 지원

**UI 변경:**
- S1: 헤더 액션 — 공유 + 플랜 생성 버튼 (기존 하단 폼 → 헤더 이동)
- S2: 목표 카드 — UTRS 미니 배지 통합
- S3: 주간 요약 — 4칸 그리드 (완료/km/시간/UTRS), 프로토타입 디자인 적용
- S4: 컨디션 조정 — 웰니스 상세 (BB/Sleep/HRV/TSB) 인라인 표시 추가
- S5: 주간 캘린더 — 리스트형 → 7열 그리드, ←→ 주 네비게이션, 타입별 배경색
- S6: AI 훈련 추천 — UTRS/CIRS 기반 규칙 기반 추천 카드 (🤖 아바타)
- S7: 데이터 연동 — Garmin/Strava/Intervals/Runalyze 동기화 상태 표시

**테스트:** 875개 통과 (기존 835 + 신규 40)

---

## [v0.2-ui-gap-fix] 2026-03-25

### UI 스펙 갭 해소 — 8건 구현

**웰니스 (#1~#5):**
- `views_wellness_enhanced.py`: `render_wellness_glossary` (HRV/BB/SDNN/Training Readiness 접이식 해설), `render_sleep_time_pattern` (평균 취침/기상 시각), `build_outlier_mark_points` (이상치 빨간 점 markPoint), `build_pattern_recovery_tips` (패턴→회복 권장 연동), `load_sleep_times` (취침/기상 timestamp 로더), `_baseline_badge` 확장 (BB/수면/스트레스/RHR 14일 평균 기준 배지)
- `views_wellness.py`: 신규 import 통합, `_render_sleep_card`에 시간대 패턴 추가, 라우트에서 sleep_times/outlier_points/pattern_tips 로드, `_render_recovery_recommendation`에 패턴 권장 연동, `render_wellness_glossary` 최하단 삽입

**레포트 (#6):**
- `views_report_sections.py`: `render_trimp_weekly_chart`에 이전 기간 비교선 (회색 점선) 오버레이 추가
- `views_report.py`: 이전 기간 TRIMP 로드 후 차트에 전달

**레이스 (#7):**
- `views_race_enhanced.py`: `render_goal_gap`에 목표 갭 기반 구체적 훈련 권장 (VDOT 향상 필요량/DI 연동) JS 추가
- `views_race.py`: vdot/di_val을 goal_gap에 전달

**활동 상세 (#8):**
- `views_activity_g2_performance.py`: ADTI 스텁 버그 수정 — `day_metrics`에서 ADTI 값 로드
- `views_activity.py`: `render_group2_performance`에 `day_metrics_data` 전달

**테스트:** 884개 통과

---

## [v0.2-ui-redesign] 2026-03-25

### UI-R5: 레이스 예측 보강 — 6개 섹션 추가

**신규 파일:**
- `views_race_enhanced.py` (293줄): 로더 2개 (DARP/VDOT 12주 추세, DI/MarathonShape/EF 12주 추세) + 렌더러 5개 (목표 갭 계산기, 예측 추세 ECharts, 준비 요소 ECharts, DI 해석 배지, 메트릭 해설 접이식)

**수정:**
- `views_race.py`: 신규 import 통합, 라우트 body에 6개 섹션 삽입 — 목표 갭(예측 카드 아래), 예측 추세 차트, 준비 요소 차트, DI 해석(DI 카드 아래), 메트릭 해설(최하단)

**6개 섹션:** 예측+목표갭 → 예측추세차트(신규) → 준비요소차트(신규) → 페이스전략+DI+DI해석(신규) → HTW+훈련조정+이력 → 메트릭해설(신규)

**테스트:** 884개 통과

---

### UI-R4: 웰니스 보강 — 9개 섹션 구조

**신규 파일:**
- `views_wellness_enhanced.py` (283줄): 로더 3개 (14일 웰니스, HRV 기준선, 주간 비교) + 렌더러 6개 (핵심 지표 대시, 7일 차트+기준선 밴드, 수면 미니 바, HRV 미니 차트+해석, 패턴 인사이트, 주간 비교 테이블)

**수정:**
- `views_wellness.py`: 신규 import 통합, `_render_sleep_card`/`_render_hrv_card`에 미니차트 추가, `_render_wellness_body` 9섹션 재구성 (핵심대시+패턴+주간비교 삽입), 라우트에서 신규 로더 호출

**9개 섹션:** 오늘상태 → 핵심지표대시(신규) → 수면+HRV상세(미니차트 보강) → 패턴인사이트(신규) → 주간비교(신규) → 기타+활동 → 7일차트(기준선밴드) → 회복권장 → 14일추세

**테스트:** 884개 통과

---

### UI-R3: 레포트 재설계 — 8개 섹션 구조

**신규 파일:**
- `views_report_loaders.py` (155줄): 이전 기간 통계, 훈련 질(EF/Dec/VO2Max) 시리즈, 리스크(ACWR/Mono/Strain) 시리즈, 폼(RMR/GCT/수직비율/보폭) 시리즈, 웰니스(HRV/수면/BB/스트레스/안정심박) 시리즈, 주간 TIDS
- `views_report_charts.py` (285줄): 6개 신규 렌더러 — `render_summary_delta` (이전 기간 대비 델타 행), `render_training_quality_chart` (EF/Dec/VO2Max 3라인 ECharts), `render_tids_weekly_chart` (주간 z12/z3/z45 스택 바), `render_risk_trend_chart` (ACWR+Mono+Strain 차트 + sweet spot 밴드), `render_form_trend` (RMR 레이더 시작/끝 비교 + GCT/수직비율/보폭 라인), `render_wellness_trend_chart` (HRV/수면/BB/스트레스/안정심박 + 기간 평균)

**수정:**
- `views_report.py` (265줄): 8섹션 순서 재작성 — 기간요약+델타 → 볼륨 → 훈련질(신규) → 분포+주간TIDS(신규) → 리스크차트(신규)+테이블 → 폼(신규) → 컨디션(신규) → 피트니스&레이스 → 메트릭테이블 → AI인사이트

**테스트:** 884개 통과

---

### UI-R2: 대시보드 재설계 — 7개 섹션 구조

**신규 파일:**
- `views_dashboard_loaders.py` (119줄): 웰니스 미니, 주간 요약, Monotony/Strain/EF 추세, 리스크 7일 추세 로더

**수정:**
- `views_dashboard_cards.py`: 4개 신규 렌더러 추가 — `render_daily_status_strip` (UTRS/CIRS 미니게이지 + ACWR/RTTI/BB/수면/HRV 아이콘), `render_weekly_summary` (주간 거리 진행률 바 + TIDS 도넛), `render_fitness_trends_chart` (PMC + Monotony/Strain 오버레이 + EF 스파크라인 ECharts), `render_risk_pills_v2` (Strain 추가 + 7일 추세 화살표)
- `views_dashboard.py` (210줄): 7섹션 오케스트레이션 재작성 — body 단일 변수로 조립
- `dashboard.html`: 개별 변수 → `{{ body | safe }}` 단일 렌더

**7개 섹션:** 상태스트립 → 훈련권장 → 주간요약(신규) → 피트니스추세(확장) → 레이스&피트니스 → 리스크상세(확장) → 최근활동

**테스트:** 884개 통과

---

### UI-R1: 활동 상세 재설계 — 7개 목적별 그룹 구조

**신규 파일 10개:**
- `views_activity_cards_common.py` (294줄): 공통 헬퍼 추출 — 포매터, METRIC_META, gauge_bar, rp_row, source_badge, no_data_msg, group_header, summary/nav/scroll/badge/splits
- `views_activity_map.py` (52줄): Mapbox GPS 경로 지도 (activity_streams 연동)
- `views_activity_loaders_v2.py` (104줄): 신규 데이터 로더 — EF/Decoupling 30일 시리즈, ACWR/Monotony/Strain/LSI 60일 시리즈, TIDS 8주 추세, DARP 값
- `views_activity_g1_status.py` (142줄): 그룹1 일일상태 스트립 — UTRS/CIRS/ACWR/RTTI/Training Readiness 미니게이지
- `views_activity_g2_performance.py` (206줄): 그룹2 퍼포먼스 — FEARP/GAP/EF+스파크라인/Decoupling+스파크라인/ADTI/VO2Max 승격
- `views_activity_g3_load.py` (119줄): 그룹3 부하 — TRIMP+WLEI 메인, RE/TL/SS/TE 서브행 + 소스 배지
- `views_activity_g4_risk.py` (87줄): 그룹4 과훈련 위험 — ACWR+Monotony+Strain+LSI ECharts 멀티라인
- `views_activity_g5_biomechanics.py` (104줄): 그룹5 바이오메카닉스 — RMR 5축 레이더, GCT/수직진동/수직비율/보폭/케이던스
- `views_activity_g6_distribution.py` (161줄): 그룹6 훈련분포 — HR존 막대, TIDS 8주 스택 차트, MarathonShape, TPDI
- `views_activity_g7_fitness.py` (170줄): 그룹7 피트니스 — PMC 차트, DI, DARP 요약, CTL/ATL/TSB

**수정:**
- `views_activity.py` (200줄): 오케스트레이션 7그룹 순서 재작성
- `views_activity_source_cards.py`: `<details>` 접이식 래핑, import 경로 수정
- `views_activity_loaders.py`: 신규 loaders → loaders_v2.py로 분리
- `activity_deep.py`: garmin_data에 `avg_vertical_oscillation` 추가

**폐기:** `views_activity_cards.py`, `views_activity_s5_cards.py` → 내용 10개 파일로 분배 완료

**테스트:** 884개 통과

---

## [v0.2-ui-minor-revision] 2026-03-25

### S5-C2: Sprint 5 데이터 UI 노출
- `views_activity_s5_cards.py` (신규 277줄): RTTI/WLEI/TPDI/Running Tolerance/HR존 차트 렌더링 카드
  - RTTI: 게이지 바 + 부하/권장최대 상세 + 과부하 판정
  - WLEI: TRIMP 대비 보정 비율 + 기온/습도 스트레스 계수
  - TPDI: 실내/실외 FEARP 격차 + 양방향 해석
  - Running Tolerance: Garmin 원시 데이터 (load/optimal_max/score) + 사용률 게이지
  - HR Zone: 존 1~5 수평 막대 차트 (색상 + 시간 + 비율)
- `views_activity_loaders.py`: `_load_running_tolerance()`, `_load_hr_zone_times()` 추가
- `views_activity.py`: S5 카드 통합 (WLEI/RTTI → TPDI/RunTolerance → HR존 → DI 순서 배치)

---

## [v0.2-ui-minor] 2026-03-25

### 6.4 Settings 보완
- `views_settings_hub.py` (신규): sync 상태 요약 카드 (연결 수, 최근 동기화, 서비스별 도트) + 시스템 정보 카드 (버전, DB 크기, 공식 버전, AI 모델)
- `views_settings.py`: 상단에 sync 개요, 하단에 시스템 정보 배치

### 6.5 Race Prediction 잔여
- `views_race.py`: 예측 이력 섹션 추가 (`_load_prediction_history`, `_render_prediction_history`) — 최근 10회 DARP 값 테이블

### 6.6 AI Coach 잔여
- `views_ai_coach_cards.py` (신규): 렌더링 카드 분리 (300줄 규칙)
- `views_ai_coach.py`: 최근 훈련 3건 요약 카드 + 리스크 요약 카드 (CIRS/ACWR/LSI) 추가
- 코치 프로필/브리핑/칩/채팅 렌더링 → cards 모듈로 분리

### 6.8 Wellness 보완
- `views_wellness.py`: 7일 웰니스 트렌드 ECharts 라인 차트 (수면/HRV/바디배터리/스트레스/안정심박)
- 회복 권장 카드 — 바디배터리/수면/스트레스/HRV 기반 규칙 조언

---

## [v0.2-sprint7] 2026-03-25

### 추가/변경

**V2-5-3: Report AI 인사이트 실체화**
- `views_report_sections.py`: `render_ai_insight()` — 기간별 규칙 기반 메트릭 분석 (UTRS 추세, CIRS 경고, Monotony, TIDS 편향, ACWR 상태)
- placeholder 제거, 실 데이터 연동

**V2-5-4: Report 기간 선택기 7개 확장**
- `views_report.py`: `_PERIODS` 7개 (today/week/month/quarter/year/1year/custom)
- custom 기간: 날짜 입력 UI + 쿼리 파라미터 파싱
- `3month` → `quarter` 하위 호환 리다이렉트
- 탭 UI 모바일 대응 (overflow-x:auto)

**V2-6-1a~f: 레이스 예측 UI 보강**
- 거리 선택기 카드 래핑 + "목표 레이스 선택" 타이틀
- 스플릿 그리드 색상 코딩 (전반=green, 후반=yellow/orange)
- VDOT/예상 순위(percentile) 표시 (DARP JSON에서)
- DI 게이지 3단계(부족/양호/우수) + 세션 수/등급 설명 자동 생성

**V2-7-1a~e: AI 코칭 UI 보강**
- 코치 프로필: 80px 아바타 + 펄스 애니메이션 상태 표시등
- 브리핑 카드: 타임스탬프 + 재생성/공유 액션 버튼
- 채팅 UI: 샘플 AI 메시지 + 입력 필드 + 전송 버튼 + 빠른 질문 칩 (v0.3 대비 레이아웃)

**V2-9-12: decisions.md Settings Platform Roadmap**
- D-V2-17 항목 추가 (v0.2→v0.3→v0.4 3단계 진화 로드맵)

**V2-9-13: DI/CIRS 비전-코드 공식 불일치 주석**
- `di.py`, `cirs.py` docstring에 PDF vs Claude 연구 버전 차이 상세 기술

**V2-9-14 / B-4: RMR 6축→5축 수정**
- `app-UI/dashboard.html` SVG: 정육각형→정오각형, "경제성" 라벨 제거

### 리팩터링
- `views_report.py` → `views_report_sections.py`: `render_summary_cards`, `render_weekly_chart`, `render_metrics_table` 이동 (300줄 제한 준수)

### 마이그레이션
- V2-9-4a (GPX/FIT/TCX Import), V2-9-4b (CSV/JSON Export) → v0.4로 이동

### 테스트
- 884 passed (6개 신규 테스트: period_today, period_year, period_1year, period_custom, custom_invalid, period_quarter)

## [v0.2-sprint6-final] 2026-03-25

### 추가

**V2-9-6: 웹 뷰 통합 테스트 37개**
- `tests/test_web_dashboard.py` (12개): 기본 렌더링, DB 미존재, 활동/메트릭 시드, PMC/RMR 카드, resync 배너, /analyze/* 리다이렉트
- `tests/test_web_report.py` (11개): 기간 파라미터(week/month/3month), 폴백, 요약 카드, 주별 차트, 메트릭 테이블, 탭
- `tests/test_web_race.py` (14개): 거리 선택기(5K/10K/하프/풀), DARP/DI/페이스전략/HTW 카드, no-data 처리

**V2-9-7: /analyze/* 레거시 경로 리다이렉트**
- `src/web/app.py`: `/analyze/today` → `/dashboard`, `/analyze/full` → `/report`, `/analyze/race` → `/race`
- `src/web/helpers.py`: 네비게이션 메뉴 링크 신규 경로로 업데이트

**V2-9-9: Mapbox 토큰 설정**
- `src/web/views_settings.py`: 설정 페이지에 Mapbox 토큰 입력/저장 섹션 추가
- `config.json.example`: `mapbox.token` 키 추가
- `src/web/views_activity_cards.py`: 토큰 존재 시 Mapbox GL JS 지도 렌더링

### 테스트
- 전체 829개 통과 (기존 792 + 신규 37)

---

## [v0.2-sprint5-audit] 2026-03-25

### API 데이터 감사 후 수정

**Bug #1: Garmin athlete_profile 컬럼명 오류**
- `garmin_athlete_extensions.py`: `first_name`→`firstname`, `last_name`→`lastname`, `username`/`profile_medium` 제거, `source_athlete_id` 추가
- `activity_best_efforts` INSERT: `effort_name` → `name` (실제 컬럼명 일치)

**Bug #2: Garmin ZIP zone time 루프 데드코드**
- `garmin_v2_mappings.py`: `extract_summary_fields_from_zip`에서 `hrTimeInZone_N`/`powerTimeInZone_N` 루프가 key 변수만 만들고 버림 → 실제 리스트 빌드 후 `_hr_zone_times`/`_power_zone_times`로 반환
- `garmin_backfill.py`: 특수 키 pop 후 `activity_detail_metrics`에 zone time 저장

**Bug #3: Strava elevation_loss 미저장**
- `strava_activity_sync.py`: `total_elevation_loss` → `elevation_loss` 컬럼에 INSERT/UPDATE 추가

**Bug #4: Intervals avg_power = normalized_power 동일값**
- `intervals_activity_sync.py`: `avg_power` = `icu_average_watts`(평균), `normalized_power` = `icu_weighted_avg_watts`(가중평균 NP)로 분리

**Bug #5: Intervals wellness stress_avg/body_battery 미저장**
- `intervals_wellness_sync.py`: `avgStress`→`stress_avg`, `bodyBattery`→`body_battery` INSERT 추가

**Check #6: Garmin extract_detail_fields 인자 순서 역전**
- `garmin_activity_sync.py`: `extract_detail_fields(act, detail)` → `extract_detail_fields(detail, act)` 수정
- Running Dynamics 필드들이 실제로 저장되지 않던 근본 원인 수정

**Check #7: Garmin ZIP avgVerticalOscillation 단위 mm→cm**
- `garmin_v2_mappings.py`: ZIP export는 mm 단위 → `/10`으로 cm 변환

**신규 필드 추가**
- `db_setup.py`: `activity_summaries`에 `session_rpe`, `strain_score`, `polarization_index`, `perceived_exertion` 컬럼 추가 + 마이그레이션
- `intervals_activity_sync.py`: `lap_count(icu_lap_count)`, `session_rpe`, `strain_score`, `polarization_index` → `activity_summaries` INSERT/UPDATE
- `strava_activity_sync.py`: `perceived_exertion` → detail UPDATE

---

## [v0.2-sprint5-bugfix] 2026-03-25

### 버그 수정

**활동 목록 — matched_group_id hex 오분류**
- `unified_activities.py` Step2 쿼리에 `is_group` 플래그 추가
- `'66588299'` 같이 숫자처럼 보이는 8자리 hex group ID가 `solo_id`로 오분류되어 활동 미표시되는 버그 수정

**활동 상세 — 서비스별 1차 메트릭 누락**
- `_load_service_metrics`: 대표(Garmin) row 1개만 조회 → 그룹 전체 소스별 row 각각 조회
- Strava `suffer_score`, Intervals `icu_atl/ctl/tsb/intensity` 전부 "—"으로 표시되던 버그 수정
- `activity_summaries`에 `icu_intensity` 컬럼 추가 + intervals sync에서 저장

**활동 상세 — no such column 오류**
- `training_load_acute/chronic` (Garmin API에서 제공 안 함) → `training_load` 단일 컬럼으로 교체
- `icu_intensity` 컬럼 DB 추가 및 마이그레이션

**대시보드 활동 링크 → Not Found**
- `views_dashboard_cards.py`: `/activity?id=` → `/activity/deep?id=` 수정

**API 로그 정리**
- `api.py`: 4xx 응답은 `[API]` 로그 출력 안 함 (caller가 처리)
- `intervals_activity_sync.py`: intervals/streams/power_curve 404 로그 억제
- `strava_activity_sync.py`: zones 402/404, streams 404 로그 억제

**병렬 동기화 req_count 추정치 수정**
- strava: `count * 3 + 1` → `count * 4 + 1` (zones 추가 반영)
- intervals: `count + 1` → `count * 3 + 1` (intervals + streams + power_curve 반영)
- runalyze: `count + 1` → `count * 2 + 1` (detail 반영)
