# UX 리뷰 2026-09 — 01. 사이트맵 (실서비스 전수)

**측정일**: 2026-09-27 · **방법**: Playwright(Chromium headless)로 `localhost:80`에 pansongit 계정 헤더를 붙여 방문, 화면별 링크·버튼·클릭 가능해 보이는 요소를 수집(원자료: 스크래치 `tour.json`).
**스크린샷**: `screenshots/<키>-desktop.png`(1280×800, 전체 페이지) · `screenshots/<키>-mobile.png`(390×844 @2x)
**주의**: 헤드리스 환경에 컬러 이모지 폰트가 없어 이모지 아이콘(📊🏃📝 등)이 스크린샷에서 □로 보인다. 실제 기기에서는 이모지로 보이지만, 이모지를 아이콘 체계로 쓰는 것 자체는 UI 리뷰 대상이다.

---

## 0. 진입 구조 — 두 개의 앱이 공존

```
/  ──302──▶ /dashboard  (v1: Flask 서버 렌더, 하단 7탭 + 개발자)
/v2/ ─────▶ /v2/today   (v2: SvelteKit SPA, 좌측 사이드바/하단 3탭)
```

- 루트 진입은 **여전히 v1**. v1 어디에도 v2로 가는 링크가 없고, v2에도 v1으로 가는 링크가 없다.
- v2의 ☰ 메뉴 버튼은 `disabled`("메뉴 (준비 중)") — 동기화·소스 연결·설정·내보내기는 **v1에만** 존재한다.
- 따라서 실사용자는 "리뉴얼 화면(v2)을 보려면 URL을 직접 쳐야 하고, 동기화·설정을 하려면 v1으로 돌아가야" 한다.

## 1. v2 (리뉴얼) — 하단 3탭

### 1.1 Today — `/v2/today` (스크린샷 키 `today`)

| 블록 | 내용 | 상호작용(실측) |
|------|------|---------------|
| 레이스 허브 | D-56, 42km 목표(2026-11-22), 예측 3:40:23 vs 목표 3:19:00, "목표보다 21분 23초 느림", 80% 범위, Garmin/RunPulse 3종 예측 비교 | 예측 숫자 클릭 → **무반응**. `<details>` 3개: "자체 추정 근거·불확실성", "검토 중 알고리즘 2건", "예측 추이·근거·레이스 아침 폼 보기"(펼침 → `today-prediction-expanded`) |
| 오늘 권고 | "레이스까지 56일 — 빌드 구간…" + 근거 칩 4개 | 칩 중 `TSB`·`UTRS`만 버튼(패널 열림), `42km 목표 D-56`·`레이스 아침 TSB +24`는 비대화형 span. "Coach에게 더 묻기 →" 링크 |
| 컨디션 입력 | "오늘 컨디션 입력 →" | 폼 펼침(`today-checkin-open`) |
| 다음 세션 | 내일 쉬운 달리기 4.6km, 이번 주 준수율 3/7 | "세션 상세 →"(→`/v2/coach/plan/1/session/2026-09-28`), "계획 수립·수정은 Coach에서 →" |
| 점수 링 | UTRS 59 · CIRS 37 · TSB -15 (RunPulse 배지) | 링 클릭 → 인페이지 분해 패널(`today-utrs-click`) |
| 최근 활동 | 오늘/어제/2일 전 3행(거리·시간·Garmin 배지) | **행 클릭 무반응 — 링크 아님** (사용자 지적 재현) |
| 흐름·훈련·성장 | 월간 한 문단 + 칩 3개(CTL만 버튼) | "이번 달 전체 이야기 보기"(`today-month-story`), "전체 마일스톤"(`today-milestones`) — 인페이지 펼침 |
| 폼 차트 | 체력·피로·폼 3개월 + 레이스 예측 투영 | 호버 시 값 표시(데스크톱만 DOM 변화 확인), 클릭 이동 없음 |
| 마일스톤 | 누적 3800km 등 | 행 클릭 무반응 |
| 원본 데이터 | "Library에서 전체 탐색 →" | Library 이동 |

### 1.2 Library — `/v2/library` 및 하위

```
/v2/library                    Library 홈 (상단 서브탭: 활동 | 메트릭 | 웰니스 | Provider 비교)
 ├ 아카이브 히어로(누적 거리) · 월별 막대(→ 활동 목록 월 필터) · 53주 히트맵(셀 클릭 무반응)
 ├ PB(1K/1마일/5K/10K/하프/풀 → 해당 활동) · 가장 멀리 달린 날
 ├ 최근 활동 5 → /v2/library/:id · 메트릭 카테고리 칩 8개 → /v2/library/metrics?category=
 ├ /v2/library/activities       활동 목록 (종목 칩 전체/러닝/수영/근력, 거리 칩, 검색, 20건 + 더 불러오기)
 ├ /v2/library/:id              활동 상세 (서브탭: 요약 | 스트림 | 랩 | 메트릭 | 소스 비교)
 │   요약: 거리 히어로, 시간/페이스/심박, "이 러닝의 이야기"(전후반·디커플링), 경로 SVG(페이스/심박 토글),
 │         KM 스플릿 바, 고도 프로필, "이 러닝의 의미", 핵심 메트릭 카드 5(클릭 → 인페이지 분해), 페이스·심박 흐름
 │   ├ /streams   스트림 차트(체크박스 5종)
 │   ├ /laps      랩 표
 │   ├ /metrics   카테고리별 <details> + 메트릭 행 버튼(클릭 → 분해 펼침), "미매핑(개발용)" 그룹 노출
 │   └ /providers 소스별 값 비교
 ├ /v2/library/metrics          메트릭 브라우저 (카테고리 칩 9, Provider 필터 3, 대표 지표 행 + "세부 지표" <details>)
 │   └ /v2/library/metrics/:slug 메트릭 상세 (기간 4주/3개월/6개월/1년, 추세 차트, "계산 분해 보기", Provider 비교 링크)
 ├ /v2/library/wellness         웰니스 (수치 클릭 무반응)
 └ /v2/library/providers        Provider 매트릭스 (4주/8주/12주)
```
- 서브탭(활동/메트릭/웰니스/Provider 비교)은 Library 홈·웰니스에만 있고, 활동 목록·메트릭 브라우저·Provider 비교에서는 "←" 뒤로만 있다(서브탭 소실).
- 설계(02 IA)의 `/library/activities/:id` 대신 실제 URL은 `/v2/library/:id`. `/library/wellness/:date`, `/library/story/*`는 미구현.

### 1.3 Coach — `/v2/coach` 및 하위

```
/v2/coach                      Coach 홈: 스레드 4개, "+ 새 대화 시작", 추천 질문 4개, 진행 중 계획 카드, "오늘 컨디션 입력 →"
 ├ /v2/coach/:threadId          대화 (근거 칩 버튼 → 패널, 후속 질문 3개, 입력+전송)
 └ /v2/coach/plan               → /v2/coach/plan/1 로 리다이렉트(활성 계획)
     ├ /v2/coach/plan/:id        주간 세션 목록(계획 vs 실제 매칭 라벨), ACWR 칩(→ 분해)
     │   └ /session/:date        세션 상세(계획·실제·메모 입력, 저장 비활성)
     ├ /v2/coach/plan/new        새 프로그램: 거리 4종, 날짜·목표·요일 입력, "프로그램 생성 →"(입력 전 비활성)
     └ /v2/coach/plan/compare    프로그램 비교 — 진입 경로 없음(링크 0), 빈 화면
```

## 2. v1 (구 UI) — 루트 기본 진입

| 탭 | 경로 | 주요 하위 |
|----|------|----------|
| 홈 | `/dashboard` | 점수 카드(→ `/guide#UTRS` 등 가이드 앵커), 최근 활동(→ `/activity/deep?id=`), "AI 분석 업데이트" |
| 활동 | `/activities` | 필터·정렬 표, 페이지네이션, 동일 활동 묶기, 운동 분류 기준 |
| 레포트 | `/report` | 기간(오늘~최근 1년), `/race` 레이스 예측, `/wellness` 웰니스, 요약 복사 |
| 훈련 | `/training` | 주간/월간/전체, 목표 관리·수정 위저드, 세션 완료/건너뜀, 내보내기, 재생성, 훈련 환경 설정 |
| AI코치 | `/ai-coach` | 채팅, 추천 질문 5, 외부 AI 연동(프롬프트 복사), ngrok/MCP |
| 동기화 | `/sync` | 소스별 연결/재연동/해제, 기본·기간 동기화, 자동 주기, 아카이브 임포트, 재계산 |
| 설정 | `/settings` | 프로필, AI 제공자, 프롬프트, 메일, 재계산 |
| 개발자 | `/dev` | (방문 안 함) |

v1은 폐기 대상(사용자 확정). 평가하지 않고 v2가 **계승·참고할 기능**만 `40-v2-unimplemented/`에서 추출한다.

## 3. 리뷰 분할

| 폴더 | 범위 | 스크린샷 키 |
|------|------|------------|
| `10-today/` | Today 전체 | today, today-* |
| `20-library-activities/` | Library 홈, 활동 목록, 활동 상세 5개 서브탭 | library, library-activities*, library-month-filter, activity*, activity-910, activity-15302 |
| `21-library-metrics/` | 메트릭 브라우저·상세, 웰니스, Provider 비교 | library-metrics*, metric-*, library-wellness, library-providers |
| `30-coach-chat/` | Coach 홈, 대화 | coach, coach-thread*, coach-checkin-open |
| `31-coach-plan/` | 계획 상세, 세션, 새 계획, 비교 | coach-plan*, coach-plan-new*, coach-plan-compare |
| `40-v2-unimplemented/` | v2 미구현(☰ Data·동기화·소스·내보내기·설정, 계획 비교, Story/웰니스 일자, 기본 진입 전환 등) 평가·설계 + v1 계승 목록 | v1-*(참고) |

각 탭 폴더에는 `data.md`·`ui.md`·`ux.md`(평가) 다음에 `design.md`(통합 개선 설계)를 둔다.
