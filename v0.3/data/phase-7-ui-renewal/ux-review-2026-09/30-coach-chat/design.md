# Coach 홈·대화 — 개선 설계서 (data·ui·ux 통합)

**작성일**: 2026-09-27 · **대상**: `/v2/coach`(Coach 홈), `/v2/coach/:threadId`(대화), `/v2/coach/new?ctx=`(맥락 첨부 새 대화, 신규), Coach 홈 컨디션 입력, Today·활동·계획·드릴 패널에서 Coach로 들어오는 경로, Coach가 쓰는 API(`/coach/threads*`, 신규 `/coach/engine`·SSE 스트림)
**입력**: `30-coach-chat/{data,ui,ux}.md`(발견 33건), `00-vision-criteria.md`, `03e-coach.md` 5-A·5-B, 실 API GET(`/coach/threads`, `/coach/threads/4`), 코드(`src/services/coach_service.py`, `src/ai/chat_engine*.py`, `src/ai/chat_context*.py`, `src/analysis/recovery.py`, `frontend/src/routes/coach/**`)
**참조 규격(재정의하지 않음)**: `10-today/design.md` §C1 ChartScrub · §C2 근거 칩 2종 · §C3 드릴 패널 D2(골격·스택·URL) · §C4 값 포맷 · §C5 스켈레톤·오류 · §C6 출처 배지 · §C7 의미색 · §C8 타이포·아이콘, 같은 문서 §2.4 히어로 상태 기계와 §4 권고 문장 규칙(`readiness_decision`). P7 판정은 `31-coach-plan/design.md` §4.1 **R8(Today CRS 게이트 단일화)**와 §7.2 `plan_adjustments`를 따른다.

---

## 1. 요약

**설계 목표**
1. **틀린 조언을 먼저 멈춘다.** 회복 등급 코드 불일치(`A/B/C` vs `excellent/good/moderate/poor`)는 S0 핫픽스로 고치고 회귀 테스트로 막는다. 이어서 Coach의 "오늘 어떻게 할까" 판정을 Today·계획과 같은 `readiness_decision(date)`(Today CRS 게이트 + 체크인 + 계획 세션 + 상태 기계)로 바꾼다. Coach 전용 판정 규칙은 두지 않는다.
2. **어떤 엔진이 답했는지 항상 보인다.** 외부 LLM이 실패하면 조용히 규칙 답변으로 바꾸지 않는다. 메시지마다 `엔진 · 기준 시점 · 근거 수`를 표시하고, 폴백이 일어나면 이유(`Gemini 404`)와 [AI로 다시 생성]을 함께 보여 준다. 외부로 무엇이 전송되는지는 첫 전송 전 동의와 입력창 위 한 줄로 고지한다(P8).
3. **근거 칩은 그 답변이 실제로 쓴 입력만 쓴다.** 저장 시점의 값·계산 시각·버전을 스냅샷으로 고정한다(as-of). 드릴 패널은 "답변 당시 값 → 현재 재계산 값"을 함께 보여 준다. Today 브리핑 근거를 복사하는 `build_evidence`는 폐기한다.
4. **맥락을 가지고 들어오고, 기다림과 실패를 보여 준다.** Today·활동·세션·드릴 패널의 `Coach에게 묻기`는 맥락 카드와 맥락별 추천 질문 3개가 있는 새 대화로 연결한다. 전송하면 즉시 내 말풍선이 뜨고, 응답은 SSE로 단계 표시(`데이터 확인 중` → 스트리밍)와 함께 받는다. 실패한 메시지는 내용을 보존하고 재시도할 수 있다.

**범위**: Coach 홈·대화·새 대화(맥락), 컨디션 입력의 Coach 배치, 답변 안의 계획 조정 카드(P7 연결부만. 조정 모델 자체는 31 설계 소관), 엔진 상태·전송 고지. 계획 화면(`/coach/plan/**`)은 31 설계, AI 제공자 설정 화면 자체는 40 설계(☰ → 설정 → AI 코치)의 자리를 쓰고 여기서는 Coach 쪽 계약만 정한다.

**평가 간 상충과 판단**

| 쟁점 | 의견 | 채택 | 이유 |
|---|---|---|---|
| 규칙 엔진의 역할 | DATA: 추천 질문마다 전용 핸들러 / UX: 규칙은 질문 이해를 흉내 내지 말고 "오늘 상태 요약"만 | **둘 다, 범위를 나눈다.** 앱이 제안한 질문(`chip_id`)은 전용 핸들러로 답한다(유한 집합, 테스트로 고정). 자유 텍스트는 키워드 분기를 폐지하고 "AI 미연결 안내 + 오늘 상태 요약 + 답할 수 있는 질문 칩"으로 답한다 | 앱이 먼저 제안한 질문에 답하지 못하는 것이 가장 나쁜 경험이다(F-DATA-05). 반면 자유 텍스트의 키워드 추측은 "목표 기록 가능할까?"를 오늘 훈련으로 보내는 식의 오답을 만든다 |
| 오늘 판정 규칙 | DATA F-DATA-07: Coach용 우선순위 5단(통증→완료→ACWR>1.5→웰니스+TSB→유지) / Today·31 설계: CRS 게이트 5종 + 체크인, 레벨 녹·황·주황·적 | **Today `readiness_decision(date)` 그대로 사용.** DATA의 "완료 여부"는 Today 상태 기계(`done`→대상 날짜 내일), "국면별 TSB 해석"은 Today §4 국면 의존 밴드가 이미 담당한다 | 판정 함수가 둘이면 모순이 다시 생긴다(현재 Today "핵심 세션" vs Coach "휴식"). 체크인 임계값은 Today 기준 **피로 ≥7 또는 통증 ≥중간**(DATA의 ≥8 대신) |
| 등급 버그 수정 시점 | DATA: 상수 통일 + 테스트 / UX: 판정 함수 재사용으로 대체 | **S0에서 enum·매핑·테스트로 즉시 수정, S3에서 `readiness_decision`으로 교체** | 판정 공용화는 Today S3 의존이라 몇 주가 걸린다. 그동안 "항상 쉬어라"를 계속 내보낼 수 없다 |
| 근거 패널 형태 | UI: 데스크톱 우측 360px 컨텍스트 패널, 모바일 50/90% 스냅 시트 / UX·Today: C3 | **Today §C3**(≥1024px 우측 420px 밀어내기, 모바일 풀스크린, `?drill=` 스택) | 공통 규격을 재정의하지 않는다. 03e 5-B의 컨텍스트 패널은 D2가 닫혀 있을 때 같은 420px 자리에 둔다(§2.3) |
| 숫자 자릿수 | UI: 본문·칩 모두 소수 1자리 / DATA·C4: TSB 정수 | **§C4**: 본문·칩은 부호 정수(`−11`), D2 공식 블록만 소수 1자리 | 규칙은 한 곳에서만 정한다. 서버 답변 본문도 같은 포맷터를 쓴다 |
| "당시 기준" 표시 기준 | DATA: 1일 / UI: 24시간 / UX: 기준일이 오늘이 아니면 | **답변 as-of 날짜(Asia/Seoul) ≠ 오늘** | 러닝 판정은 날짜 단위(아침 폼)다. 24시간 기준은 밤 11시 답변을 다음 날 아침에도 "현재"로 보이게 한다 |
| 컨디션 입력 형태 | UI: 모바일 하단 시트 / Today §3 B2: 인라인 1줄, 피로 1탭 저장 | **Today B2 그대로**(같은 `QuickInput`), Coach 홈 상단으로 올린다 | 시트가 필요했던 이유(폼이 페이지 맨 아래라 저장 버튼이 화면 밖)는 위치를 올리고 1탭 저장으로 바꾸면 사라진다 |
| 맥락 진입 URL | Today: `/v2/coach/{thread}?from=today` / Library: `/coach/new?activity={id}` / UX: `/coach/new?ctx=today:…` / 31: `context:{type:"plan_session"}` | **수신 라우트 `/v2/coach/new?ctx={kind}:{ref}&from={origin}` 하나.** 스레드는 첫 전송 때 만들고 URL을 `/v2/coach/{id}?from=`로 replace한다. `?activity=`는 `ctx=activity:`의 별칭, `plan_session`은 `session`의 별칭으로 받는다 | 칩을 보기만 하고 나가도 빈 스레드가 생기지 않는다. 전송 후의 최종 URL은 Today 설계와 같다 |
| 모바일 대화 크롬 | UI: 대화 라우트에서 전역 헤더·탭바 숨김 / P4 탭 상시 노출 | **숨김 채택**(대화 라우트만). `←`가 진입 출처로 돌아간다 | 입력 중 대화가 보이는 높이가 300px 안팎까지 줄어드는 문제가 더 크다. 메신저 표준 패턴이다 |
| 홈 데스크톱 레이아웃 | UI: 목록 320 + 대화 마스터-디테일 / UX: 최근 3개 + `전체 대화 ›` | **UX안 + 우측 레일 360px**(계획·컨디션·엔진 상태) | 스레드가 4개인 현재 규모에 마스터-디테일은 과하다. 스레드가 30개를 넘으면 재검토한다(보류 조건) |
| 엔진 상태 위치 | UX: 홈 상단·입력창 위 상시 배지 / DATA: 연속 실패 시 배너 | **입력창 위 엔진 줄은 상시**(정상이면 중립 1줄), **홈 상단 배너는 최근 3회 연속 실패일 때만** | 정상일 때 경고색을 쓰면 무시하는 습관이 생긴다. 전송 고지(P8)가 같은 줄에 있어야 하므로 상시 표시가 필요하다 |

---

## 2. 정보 구조·배치

### 2.1 Coach 홈 블록 순서

| # | 블록 | 내용 | 근거 |
|---|---|---|---|
| H0 | 엔진 배너(조건부) | 최근 3회 연속 폴백일 때만: `AI 코치 연결 실패 — 최근 3회 기본 규칙 답변 · 원인 보기 ›` | F-UX-01, F-DATA-04 |
| H1 | **오늘 코치 노트** | `readiness_decision` 헤드라인(Today 히어로와 **같은 문장**) + 근거 칩 2~3(§C2) + `이어서 묻기 ›`. 조정 제안이 있으면 31 `AdjustmentCard` 축약형(같은 adjustment id) | F-UX-07, F-DATA-01·07, P7 |
| H2 | 컨디션 1줄 | Today B2와 같은 `QuickInput`(피로 1탭 저장, `✕ 나중에`) | F-UX-08, F-UI-08, F-DATA-06 |
| H3 | 질문 제안 | 국면·맥락 기반 칩 3~4개, **탭 = 즉시 전송**, 칩 끝 `✎` = 입력창에 채우기 | F-UX-07, F-UI-09, F-DATA-05 |
| H4 | 최근 대화 3개 + `전체 대화 ›` | 행 = 제목 · 날짜 / `Q: 질문` · 결론 1구절 / 근거 미니 칩 2 | F-UI-07, F-UX-06 |
| H5 | 계획 카드 | `42km 목표 · 1/9주 · 세션 2/6 · 다음: 월 이지 8km ›`(31 API 값) | F-UX-07 ⑤ |
| C | 상시 컴포저 | 하단 고정 `무엇이든 물어보세요` + 엔진 줄(§4.2) | F-UI-09, F-UX-07, F-UX-12 |

### 2.2 Coach 홈 — 데스크톱 1280

```
사이드바 208 │ 헤더: ☰ Coach                                   ● 9월 27일 · 3분 전 동기화
             │ 메인 720 (가운데 정렬)                          │ 우측 레일 360
             │ H1 오늘 코치 노트 · 9월 27일 아침 기준          │ H5 진행 중 계획
             │   오늘 완료 ✓ 9.3km · 내일 월 이지 8km 계획대로 │   42km 목표 · 1/9주 · D-56
             │   [게이트 녹 5/5 ›] [폼 −9 ›] [수면 52 ›]      │   세션 2/6 · 볼륨 60%   ›
             │   이어서 묻기 ›                                 │   + 다른 대회 준비
             │ H2 오늘 컨디션  피로 [1][2]…[10]  1 가뿐함–10 탈진│ 엔진 상태
             │ H3 질문 제안                                    │   Gemini 2.5 Flash · 정상
             │   (목표 기록 가능할까?) (이번 주 뭘 하면 돼?)    │   마지막 응답 09:12
             │   (테이퍼는 언제부터?) (부상 위험 확인)          │   전송 범위 보기 ›
             │ H4 최근 대화                         전체 대화 › │
             │   9/25 오늘 훈련              9/25(목) 10:51    │
             │   Q: 오늘 훈련 조언 · 회복 6.9km 권고           │
             │   9/24 훈련 분석              9/24(수) 23:59    │
             │ ┌───────────────────────────────────────────┐  │
             │ │ 무엇이든 물어보세요                     (↑)│  │
             │ └───────────────────────────────────────────┘  │
             │ Gemini로 전송: 질문 + 최근 30일 요약 · 범위 ›    │
```

### 2.3 대화 — 데스크톱 1280 (D2 닫힘 / 열림)

```
사이드바 │ ← Coach   9/25 오늘 훈련                    ⋯ │ 컨텍스트 패널 420 (D2 닫힘일 때)
         │ 대화 열 720                                    │ 이 대화의 맥락
         │ ──────── 9월 25일 (목) ────────                │   Today · 9/25 아침
         │                     [나] 오늘 훈련 조언 10:51  │   진행 중 계획 1/9주 · 세션 2/6
         │ ◎ Coach                                        │ 이 대화가 쓴 데이터
         │ ▍기본 규칙 답변 · Gemini 연결 실패(404)         │   폼(TSB) 9/25 · 수면 9/25
         │ ▍[AI로 다시 생성]  [원인 보기 ›]               │   계획 9/25 회복 6.9km
         │ 오늘은 계획대로 회복 달리기 6.9km를 권해요.     │   전송 없음(규칙 답변)
         │ • 폼 −11: 생산적 부하 구간, 강도 제한은 없음   │
         │ • 수면 87·HRV 평소 범위: 회복 신호 양호         │
         │ [폼 −11 ›] [수면 87 ›] [계획 회복 6.9km ›]     │
         │ 반대 신호: (ACWR 1.10 적정)                     │
         │ 규칙 답변 · 9/25(목) 10:51 기준 · 근거 3 [당시 기준]│
         │ 이어서 묻기: (이 폼이면 이번 주엔?) (내일은?)   │
         │ ┌──────────────────────────────────────┐       │
         │ │ 메시지 입력                       (↑)│       │
         │ └──────────────────────────────────────┘       │
         │ 규칙 답변 모드 · 외부 전송 없음 · 범위 ›        │
```
- 근거 칩을 누르면 오른쪽 420px 자리가 D2(§C3)로 바뀐다. 헤더 `폼(TSB) · 9월 25일 기준`, ① 블록 맨 위에 **스냅샷 줄**(§4.4)이 들어간다. 닫으면 컨텍스트 패널로 돌아간다.
- 1024px 미만에서는 컨텍스트 패널을 숨기고 스레드 헤더 `⋯ → 이 대화의 맥락`으로 연다.
- 와이어프레임의 답변 문장·수치는 설계 예시다. 레거시 메시지 14의 실제 본문은 §7.4 이관 규칙대로 그대로 두고 표시만 바꾼다.

### 2.4 대화 — 모바일 390 (스트리밍 중)

```
←  9/25 오늘 훈련               ⋯     48   (전역 헤더·탭바 숨김)
──────── 9월 27일 (일) ────────
               [나] 목표 기록 가능할까?  09:12
◎ Coach
  ◌ 데이터 확인 중: 예측 추이 · 최근 롱런 4회
  ▂▂▂▂▂▂▂▂▂  (본문 스켈레톤 3줄)
  [중단]
                                          (메시지 영역 ≈ 844−48−72 = 724px)
┌──────────────────────────────────┐
│ 다음 질문을 미리 쓸 수 있어요       (↑)│ 16px, 1~5줄 auto-grow
└──────────────────────────────────┘
 Gemini로 전송 중 · 범위 ›               24   + safe-area-inset-bottom
```
- 근거 칩 줄은 가로 스크롤 1줄(`snap-x`, 오른쪽 끝 페이드)이다. 칩 4개가 세로로 약 270px를 쓰던 문제를 없앤다.
- 키보드가 열리면 `interactive-widget=resizes-content`와 `visualViewport` 보정으로 컴포저가 키보드 위에 붙는다.

### 2.5 새 대화(맥락 첨부) — `/v2/coach/new?ctx=activity:17414&from=activity`

```
←  Coach에게 묻기                        48
┌ 맥락 카드 ──────────────────────────────┐
│ 9/27(일) 러닝 9.3km · 55:18 · 5:57/km    │  탭 → 원래 화면(from)
│ 계획: 장거리 22.4km 대체 · 평균 HR 137   │
└─────────────────────────────────────────┘
이 러닝에 대해 물어보기
 (페이스 배분 괜찮았어?)   ← 탭 = 즉시 전송
 (심박이 왜 높았지?)
 (다음 세션에 반영할 점은?)
이 활동으로 나눈 대화 1개 · 9/27 이어서 묻기 ›   (같은 ctx 스레드가 있을 때)
┌──────────────────────────────────┐
│ 직접 질문하기                    (↑)│
└──────────────────────────────────┘
 Gemini로 전송: 질문 + 이 활동 요약·랩 · 범위 ›
```

맥락 종류(`ctx` kind)와 맥락 카드·추천 질문은 다음과 같다.

| kind:ref | 진입점 | 맥락 카드 | 추천 질문 3개 |
|---|---|---|---|
| `today:2026-09-27` | Today 히어로 `Coach에게 묻기`, Coach 홈 H1 `이어서 묻기` | Today 헤드라인 + 근거 칩(같은 스냅샷) | 왜 이렇게 판단했어? / 강도를 올려도 될까? / 내일은? |
| `activity:17414` | 활동 상세 `코치에게 묻기`(20 설계 §3) | 날짜·거리·시간·페이스·계획 매칭 라벨 | 페이스 배분 괜찮았어? / 심박이 왜 높았지? / 다음 세션에 반영할 점은? (유형별로 바뀜: 인터벌이면 "세트 편차 괜찮았어?") |
| `metric:tsb@2026-09-27` | D2 푸터 `Coach에게 묻기`(§C3.2 ④) | 지표 이름·값·상태·기준일 | 이 값이면 뭘 하면 돼? / 왜 이렇게 바뀌었어? / 목표 범위는? |
| `session:2026-09-28?w=152` | 세션 상세·행 액션 `Coach에게 묻기`(31 §3) | 처방·유효 계획·조정 상태 | 이 세션 줄여야 할까? / 페이스 범위는 왜 이래? / 다른 날로 옮겨도 돼? |
| `plan:1` | 계획 상세 `⋯` | 계획 요약·이행 3수치 | 이 계획 현실적이야? / 이번 주 어땠어? / 남은 기간 어떻게 준비할까? |

같은 `ctx`의 스레드가 이미 있으면 새로 만들지 않고 `이어서 묻기`를 1순위로 보여 준다. "오늘 훈련 조언" 같은 일일 질문은 `today:{date}` 스레드 하나로 모은다(스레드 증식 방지).

### 2.6 주요 상태

```
[폴백 답변 — 메시지 상단 띠, amber 좌측 3px]
▍기본 규칙 답변 · Gemini·Groq 연결 실패(404) · 09:12
▍[AI로 다시 생성]   [원인 보기 ›]

[AI 미설정 — 중립, 띠 없이 메타 줄만]
규칙 답변 (AI 미설정) · 9/27(일) 09:12 기준 · 근거 3 · AI 설정 ›

[전송 실패 — 사용자 말풍선]
                       [나] 이번 주 롱런 줄여도 돼?  ⚠
                       전송 실패 · 다시 보내기 · 수정

[답변 생성 실패 — 어시스턴트 자리]
◎ 답변을 만들지 못했어요 (시간 초과 45초) · ↻ 다시 생성

[재계산 드리프트 — 메시지 하단]
ⓘ 이 답변의 근거 수치가 이후 재계산으로 바뀌었어요 (폼 −11 → −3) · 지금 상태로 다시 묻기 ↻

[첫 LLM 전송 동의 시트 — §4.3]
```

---

## 3. 클릭별 동작 명세

URL 상태 문법은 §C3.3(`?drill=` 토큰)을 따른다.

| 요소 | 제스처 | 결과 | 뒤로가기 | URL 상태 |
|---|---|---|---|---|
| H0 배너 `원인 보기 ›` | 탭 | 엔진 시트: provider별 마지막 시도(모델·HTTP 상태·시각), `AI 코치 설정 ›`(☰ 설정 → AI 코치, 40 설계) | 시트 닫힘 | `?sheet=engine` |
| H1 근거 칩(DrillChip) | 탭 | D2(해당 토큰, 기준일 = 오늘) | D2 닫힘 | `?drill=m.tsb@2026-09-27` |
| H1 `이어서 묻기 ›` | 탭 | `today:{오늘}` 스레드가 있으면 그 스레드, 없으면 `/v2/coach/new?ctx=today:{오늘}&from=coach` | Coach 홈 | 경로 |
| H1 조정 `[조정 적용]`/`[원래대로]` | 탭 | 31 `POST /coach/plan/adjustments/:id/accept|revert`, 토스트 `[되돌리기]` 8초. Today·계획 카드와 같은 id라 세 화면이 같은 상태를 보인다 | — | 없음 |
| H2 피로 숫자 | 탭 | 즉시 저장(낙관적), `피로 6 · 09:12 입력`. 저장 후 `컨디션을 반영해 오늘 조언을 다시 받을까요? [받기]` | — | 없음 |
| H2 `[받기]` | 탭 | `today:{오늘}` 스레드에 `chip_id=today_advice` 전송 | 홈 | 경로 |
| H3 질문 칩 | 탭 | **즉시 전송**: `/v2/coach/new`를 거치지 않고 스레드 생성(`chip_id`) → 대화 화면으로 이동, 내 말풍선 즉시 표시 | Coach 홈 | `/v2/coach/{id}?from=coach` |
| H3 칩 `✎` | 탭 | 컴포저에 문구 채우고 포커스 | — | 없음 |
| H4 행(전체 영역, ≥56px) | 탭 | 대화 화면, 마지막 메시지로 스크롤 | Coach 홈(스크롤 복원) | `/v2/coach/{id}` |
| H4 행 `⋯` / 길게 누르기 500ms | 탭 / 길게 | 행 메뉴: 이름 변경 · 고정 · 삭제(토스트 `[되돌리기]` 5초) | 메뉴 닫힘 | `?sheet=thread-{id}` |
| `전체 대화 ›` | 탭 | `/v2/coach/threads`(날짜 그룹 `오늘/이번 주/이전`, 10개 초과 시 검색창) | Coach 홈 | 경로 |
| H5 계획 카드 | 탭 | `/v2/coach/plan/{id}?week={이번 주}` | Coach 홈 | 경로 |
| 컴포저 전송 `(↑)` / Enter | 탭 / 키 | 데스크톱: Enter 전송, Shift+Enter 줄바꿈, **`isComposing`·keyCode 229면 무시**. `pointer: coarse`: Enter = 줄바꿈, 전송은 버튼만 | — | 홈에서는 스레드 생성 후 이동 |
| 엔진 줄 `범위 ›` | 탭 | 전송 범위 시트(§4.3) | 닫힘 | `?sheet=scope` |
| 대화 헤더 `←` (44px) | 탭 | 같은 앱 히스토리가 있으면 `history.back()`, 없으면 `from`에 맞는 경로(`today`→Today, `activity`→활동 상세, 없으면 Coach 홈) | — | — |
| 대화 헤더 `⋯` | 탭 | 이름 변경 · 이 대화의 맥락(모바일) · 삭제 · 외부 AI로 가져가기(40 설계 계승 항목 11, 복사 전 범위 미리보기) | 닫힘 | `?sheet=thread` |
| 답변 근거 칩(DrillChip) | 탭 | D2 + 스냅샷 줄(§4.4). 데스크톱은 우측 420px, 모바일 풀스크린 | 1단계 pop | `?drill=m.tsb@2026-09-25&msg=14` |
| 답변 근거 `+n 근거` | 탭 | 컨텍스트 패널의 "이 답변이 쓴 데이터" 목록(모바일은 시트) | 닫힘 | `?sheet=inputs-14` |
| 반대 신호 칩(caveat) | 탭 | D2(칩 앞 `반대 신호` 라벨, 의미색 점 없이 테두리 점선) | pop | `?drill=…` |
| 원천 활동 칩 `어제 인터벌 12km ›` | 탭 | `/v2/library/{id}?from=coach` (D3) | 대화 + D2 복원 | 경로 |
| D2 푸터 `Coach에게 묻기` (대화 안에서) | 탭 | 현재 스레드 컴포저에 프리필 `폼이 −11에서 −3으로 바뀐 이유?`(스냅샷과 현재가 다를 때) 또는 `이 지표 설명해줘` | D2 닫힘 | 없음 |
| 폴백 띠 `[AI로 다시 생성]` | 탭 | `POST …/messages/{mid}/regenerate` → 같은 자리에서 스트리밍. 새 답변이 오면 기존 규칙 답변은 `이전 답변 보기 ▾`로 접힘 | — | 없음 |
| 폴백 띠 `[원인 보기 ›]` | 탭 | 엔진 시트(이 메시지의 시도 기록) | 닫힘 | `?sheet=engine-14` |
| 메타 줄 `당시 기준` 태그 / `지금 상태로 다시 묻기 ↻` | 탭 | 같은 질문을 현재 기준으로 전송(같은 스레드, 새 메시지) | — | 없음 |
| 후속 질문 칩(이어서 묻기) | 탭 | 즉시 전송(서버가 준 `suggested_followups`만, 이미 물은 질문 제외) | — | 없음 |
| 스트리밍 `[중단]` | 탭 | `POST …/messages/{mid}/cancel`, 받은 부분까지 `중단됨` 표시 + `↻ 다시 생성` | — | 없음 |
| 20초 무응답 안내 `[기본 답변 받기]` | 탭 | 진행 중 LLM 요청을 취소하고 규칙 답변(판정 요약) 생성, 폴백 이유 `사용자 선택(지연)` | — | 없음 |
| 실패 말풍선 `다시 보내기` / `수정` | 탭 | 같은 `client_msg_id`로 재전송(서버 멱등) / 내용을 컴포저로 되돌림 | — | 없음 |
| 답변 안 조정 카드 `[조정 적용]`/`[원래대로]` | 탭 | 31 `adjustments/:id/accept|revert`(CRS 발 제안) 또는 `workouts/:id/action`(source=coach). 카드가 `적용됨 · 계획 보기 ›`로 바뀜 | — | 없음 |
| `↓ 새 답변` 플로팅 버튼 | 탭 | 맨 아래로 스크롤(위로 스크롤한 상태에서 답변이 오면 표시) | — | 없음 |
| 맥락 카드(새 대화) | 탭 | `from` 화면으로 복귀 | — | — |
| 맥락 추천 질문 | 탭 | 즉시 전송 → 스레드 생성, URL `replaceState` `/v2/coach/{id}?from={origin}` | 진입 원래 화면(새 대화 화면은 히스토리에 남기지 않음) | 경로(replace) |

---

## 4. 지표 표기·설명 규격

값 포맷은 §C4, 출처 배지는 §C6, 의미색은 §C7이다. 아래는 Coach에만 해당하는 결정이다.

### 4.1 메시지 메타 줄과 엔진 라벨

답변 블록 하단 12px `fg-secondary` 한 줄: `{엔진 라벨} · {as-of} · 근거 {n}` + 조건부 태그.

| 상태(`engine.status`) | 엔진 라벨 | 추가 표시 |
|---|---|---|
| `ok` | `Gemini 2.5 Flash · 조회 3회` (provider·모델·도구 호출 수) | 없음 |
| `fallback` | `기본 규칙 답변` | 메시지 상단 amber 띠 `Gemini·Groq 연결 실패(404) · [AI로 다시 생성] [원인 보기 ›]` |
| `rule_only` | `규칙 답변 (AI 미설정)` | `AI 설정 ›` 링크, 띠 없음 |
| `rule_by_choice` | `규칙 답변 (AI 끔)` | 없음(사용자가 전송 범위 시트에서 끈 경우) |
| `error` | — | 어시스턴트 자리에 `답변을 만들지 못했어요 ({이유}) · ↻ 다시 생성` |
| `cancelled` | `중단됨` | 받은 부분 + `↻ 다시 생성` |

- 폴백 이유 코드: `http_404 · http_401 · http_429 · timeout · no_key · parse_error · user_skip`. 화면 문구는 `연결 실패(404)`, `인증 실패(401)`, `사용량 한도(429)`, `시간 초과`, `키 없음`, `응답 해석 실패`, `사용자 선택`이다. 404는 "모델 ID 확인 필요"를 원인 시트에 덧붙인다(현재 기본값 `gemini-2.0-flash`가 폐기되었을 가능성, 추정).
- **규칙 답변 문구는 "AI 코치"를 자칭하지 않는다.** 없는 목적지 안내(`훈련 탭`, `설정 > AI에서 Claude 또는 ChatGPT API 키`)는 v2 경로(`Coach › 계획`, `☰ 설정 → AI 코치`) 링크로 바꾼다.

### 4.2 as-of 표기

- as-of는 **답변이 쓴 데이터의 기준 시점**이다. `readiness_decision`을 쓰면 `9/25(목) 아침 기준`(Today 아침 폼 기준과 같음), 자유 질문이면 `9/25(목) 10:51 기준`(생성 시각, KST). DB `created_at`은 UTC 문자열(`2026-09-25 01:51:08`)이므로 API가 `+09:00` 오프셋을 붙인 ISO로 내려준다.
- as-of 날짜(Asia/Seoul) ≠ 오늘이면 메타 줄 끝에 amber 태그 `당시 기준`과 `지금 상태로 다시 묻기 ↻`를 붙인다. 답변 본문의 상대 표현(`오늘 계획`, `D-58`)은 그대로 두되, 태그가 붙은 메시지에서 서버가 `오늘`을 `9/25`로 바꾼 표시용 사본(`content_display`)을 함께 내려준다(원문은 보존).
- 날짜가 바뀌는 지점에 `──── 9월 25일 (목) ────` 구분선, 사용자 말풍선 옆에 `10:51`을 둔다.
- 목록 행 날짜는 7일 이내 `어제 21:14`·`9/25(목) 10:51`, 그 이상 `9/12`. 상대 표기 `2일 전`만 쓰지 않는다.

### 4.3 외부 전송 범위 고지(P8)

**엔진 줄(컴포저 바로 위, 12px, 상시)**: 정상 `Gemini로 전송: 질문 + 최근 30일 요약 · 범위 ›` / 전송 중 `Gemini로 전송 중` / 규칙 모드 `규칙 답변 모드 · 외부 전송 없음 · 범위 ›`.

**첫 LLM 전송 동의 시트(계정당 1회, provider가 바뀌면 다시)**:
```
이 질문은 Google(Gemini)로 전송됩니다
보내는 것            기간        끄기
 질문과 이 대화 최근 6개 메시지      —
 훈련 요약(거리·부하·CTL/ATL/TSB)  최근 30일
 웰니스(수면·HRV·바디배터리)       최근 30일
 컨디션 입력: 피로·통증            최근 3일
 컨디션 메모(자유 텍스트)          최근 3일    [ ] 제외
 필요할 때 추가 조회(15종 ▾)       요청 범위   [ ] 끄기
 연결 실패 시 대신 사용: Groq                   [ ] 끄기
보내지 않는 것: 원본 GPS 경로, 계정·토큰, 다른 사용자 데이터
[규칙 답변만 쓰기]                        [동의하고 보내기]
```
- 추가 조회 15종은 묶어서 보여 준다: 활동·랩·스플릿(`get_activity*`, `compare_workout_sets`), 기간 요약(`get_training_summary`, `compare_periods`), 메트릭(`get_metrics*`, `get_fitness`), 웰니스, 대회 이력, 계획, 러너 프로필, 날씨. 날씨 조회가 위치를 보내는지는 구현 확인 후 문구를 확정한다(추정).
- **폴백 체인은 동의한 provider만 포함한다.** 지금 체인은 선택 provider → gemini → groq 순으로 사용자가 모르는 두 번째 업체에 같은 데이터를 보낸다. 동의 시트에서 `대신 사용`을 끄면 체인에서 뺀다.
- 메시지별 전송 기록: 컨텍스트 패널 "이 대화가 쓴 데이터"에 `09:12 Gemini · 요약 30일 · 도구: get_activity_laps(17414), get_wellness(9/21–27)`를 남긴다. 규칙 답변은 `전송 없음`.

### 4.4 근거 칩(답변 단위)

- 칩 형태는 §C2(DrillChip/InfoTag)다. Coach는 `role`만 추가한다: `supports`(결론을 만든 신호) / `caveat`(결론과 방향이 반대인 신호). caveat 칩은 앞에 `반대 신호` 라벨을 붙이고 테두리를 점선으로 하며, supports 뒤에 둔다.
- **칩 = 이 답변이 실제로 쓴 입력.** 규칙 경로는 분기 판단에 쓴 값(`readiness_decision.reasons/caveats`, 계획 세션, 체크인)만 칩으로 만든다. LLM 경로는 보낸 컨텍스트 항목과 도구 결과 가운데 **본문에 인용된 값**(숫자 일치 ±반올림)만 칩으로 만들고, 인용되지 않은 입력은 "이 답변이 쓴 데이터" 목록에만 둔다(판단: LLM이 무엇을 "사용했는지"는 알 수 없으므로 보낸 것과 인용한 것을 구분한다).
- 보이는 칩은 2~3개(§C2), 나머지는 `+n 근거`. 체크인이 판정에 들어갔으면 `피로 7 (직접 입력, 07:40)` 칩은 항상 보인다. 소스 간 값이 다르면(Garmin HRV 평소 vs Intervals ATL 높음) caveat 칩으로 설명한다(U7 차별점).
- 투영값(`레이스 아침 폼 +25`)은 칩 라벨에 단정하지 않고 `계획대로 가면 레이스 아침 폼 약 +25`로 쓰며, 목적지는 D2 `x.taper`(Today §3)다.
- **스냅샷 줄(D2 ① 블록 맨 위, 답변 칩에서 열었을 때만)**: `답변 당시 −10.7 (9/25 10:51 계산 · pmc_v1)` → `현재 −3.3 (9/27 11:57 재계산 · pmc_v1)`. 값이 같으면 한 줄만 둔다. 차이가 있으면 amber 점과 `이후 데이터 동기화·재계산으로 값이 바뀌었어요`를 붙인다. D2 ② 이하는 현재 값 기준이다(§C3 그대로). 이 줄은 §C3.2 ① 블록의 확장으로, Today에서 열 때는 나오지 않는다(10 설계에 역반영 요청).
- **드리프트 판정**: `|현재 − 당시| ≥ max(5, |당시|×0.25)` 또는 부호 반전 또는 `status` 변화면 메시지 하단 배너(§2.6). 9/23 TSB −16.5 → +15.8, 9/24 −28.4 → +2.6은 모두 해당한다.

### 4.5 답변 본문 포맷

- 규칙 답변은 서버 포맷터(§C4를 옮긴 `src/utils/format_ko.py`)만 쓴다: 거리 `10.03km`, 페이스 `5:45/km`, 폼 부호 정수 `−11`, 등급·운동 유형은 한국어 라벨(`excellent`→`매우 좋음`, `recovery`→`회복 달리기`). 원시 부동소수(`10.027959999999998km`)·`초/km`·영문 내부 키는 0건이어야 한다(§8 검사).
- LLM 답변은 시스템 프롬프트에 같은 포맷 규칙을 넣고, 후처리로 `\d+\.\d{3,}`(소수 3자리 이상)와 `\d+(\.\d+)?초/km` 패턴만 교정한다. 문장은 고치지 않는다.
- 렌더: 답변은 말풍선이 아닌 전폭 문서 블록(좌측 Coach 아바타 20px, 본문 15/24 = 1.6, 헤딩 16px semibold, `<ul>` 4px 불릿). 사용자 말풍선은 `surface-3` + `fg-primary`, 최대 폭 75%. 이모지(📋📊)는 §C8 SVG로 바꾼다. 한글에는 mono를 쓰지 않는다.

### 4.6 컨디션 입력 척도(U5)

- 라벨: `피로도` + 양 끝 앵커 `1 가뿐함 … 10 탈진`(12px fg-secondary), 선택 뒤 해석 1줄(`6 · 다소 피곤`). 통증은 `통증` 제목 + `없음/경미/중간/심함` + 선택 시 부위(선택 항목).
- 선택색: 중립 강조(fg-primary 2px 테두리 + surface-3). 등급색을 쓰지 않는다(피로 10이 teal, 통증 없음이 amber인 현재 역전 제거).
- 저장 값은 LLM·규칙 모두 `피로도 N/10 (1 가뿐함–10 탈진)`으로 전달한다. 척도 정의를 컨텍스트에 함께 넣어 방향 오독을 막는다.
- "자동 반영" 문구는 반영이 코드로 보장되는 S3 이후에만 쓴다. 그 전에는 `오늘 조언에 반영돼요(AI 연결 시)`로 사실만 적는다. S0에서 먼저 고친다.

---

## 5. 차트 규격

Coach 본문에는 새 차트를 두지 않는다. 차트는 모두 D2와 컨텍스트 패널 안에서 §C1 ChartScrub으로 그린다.

| 위치 | 차트 | 설정 |
|---|---|---|
| D2 ①(답변 칩에서 열림) | 14일 미니 추이 | §C1 스파크라인(48px, 스크럽 가능) + **답변 시점 세로 마커** `답변 9/25` + 그날 **당시 값 점**(속 빈 원, 현재 선과 다르면 amber)과 현재 선. 최적 밴드는 서버 `bands` |
| 컨텍스트 패널 | 맥락별 1개 | `today`·`metric`: 해당 지표 28일 스파크라인. `activity`: 그 활동 km 스플릿 페이스(invert, `빠름 ↑`). `session`/`plan`: 31 `PlanTimeline` 축소형(9주, 높이 64). 모두 §C1 |
| 목표 기록 핸들러 답변 | 예측 추이 | 본문에 넣지 않고 칩 `예측 3:40 (3:26–4:03) ›` → D2 `m.race_pred_marathon_sec`(Today §5 예측 추이, invert) |

빈 데이터는 §C1 규칙(`데이터 수집 중 (n/필요 일수)`)을 따른다. 레거시 메시지(스냅샷 계산 시각 없음)는 당시 값 점만 찍고 마커 라벨을 `답변 9/25 (계산 시각 기록 없음)`으로 둔다.

---

## 6. 로딩·빈·오류 상태

문법은 §C5다. Coach 고유 상태만 적는다.

### 6.1 블록

| 블록 | 스켈레톤 | 빈 상태 | 오류 |
|---|---|---|---|
| H1 코치 노트 | 헤드라인 2줄 + 칩 3 윤곽(≈140px) | 웰니스·계획 없음: `오늘 판단에 쓸 데이터가 부족해요 (수면·HRV 없음) · 기기 연결 ›` + 부하 기반 문장 | `오늘 판단을 불러오지 못했어요 · [다시 시도]` |
| H3 질문 제안 | 칩 4개 윤곽 | 목표 없음: 일반 3개 + `목표 레이스 등록 ›` | 칩은 클라이언트 기본값으로 표시(오류 숨김) |
| H4 최근 대화 | 행 3개 바 | `아직 대화가 없어요 · 아래 질문 제안을 눌러 시작하세요` | `대화 목록을 불러오지 못했어요 · [다시 시도]`(현재 재시도 없음) |
| H5 계획 | 1줄 바 | `목표 레이스를 정하면 주차별 계획을 만들어요 [계획 만들기]` | 재시도 |
| 대화 화면 | 메시지 3개 윤곽, 진입 즉시 **마지막 메시지로 스크롤** | — | 없는 스레드: `대화를 찾을 수 없어요 · ← Coach` |
| 새 대화 맥락 카드 | 카드 윤곽(72px) | 참조 대상 없음(삭제된 활동): 카드 대신 `이 활동을 찾을 수 없어요` + 일반 질문 | 카드 없이 진행(질문은 가능) |

### 6.2 전송·응답 상태 기계

| 상태 | 화면 | 전이 |
|---|---|---|
| `sending` | 내 말풍선 즉시 표시(≤100ms, 흐림 70%), 컴포저는 **활성 유지**(다음 질문 작성 가능, 전송 버튼만 대기) | 201 → `pending`, 실패 → `send_failed` |
| `send_failed` | 말풍선 `⚠ 전송 실패 · 다시 보내기 · 수정`, 내용 보존 | 다시 보내기(같은 `client_msg_id`) |
| `pending` | 어시스턴트 자리 점 3개(`prefers-reduced-motion`이면 정지) | SSE `stage` → `working` |
| `working` | `◌ 데이터 확인 중: {도구를 사람 말로}` 단계 목록 + 본문 스켈레톤 + `[중단]` | `delta` → `streaming` |
| `streaming` | 토큰이 이어서 그려짐, 칩 자리 윤곽 예약 | `done` → `done`, 끊김 → `reconnecting` |
| `slow` | 20초 동안 `delta` 없음: `평소보다 오래 걸려요 · [계속 기다리기] [기본 답변 받기]` | 선택에 따름. 45초면 서버가 `timeout`으로 폴백 |
| `reconnecting` | 상단 1줄 `연결을 다시 잇는 중…`. `Last-Event-ID`로 재개, 3회 실패 시 `GET …/messages/{mid}` 폴링(2초) | `done`/`error` |
| `done` | 본문 + 칩 + 메타 줄 + 후속 질문 | — |
| `fallback` | `done`과 같고 상단 amber 띠(§4.1) | `[AI로 다시 생성]` → `pending` |
| `error` | `답변을 만들지 못했어요 ({이유}) · ↻ 다시 생성`. 사용자 메시지는 성공 표시 유지 | 다시 생성 |
| `cancelled` | 받은 부분 + `중단됨 · ↻ 다시 생성` | 다시 생성 |

- 대기 시간 상한: provider별 연결 10초 + 응답 30초, 체인 전체 45초(현재 60초 × 2 + 30초 가능성 제거). 45초를 넘으면 남은 provider를 건너뛰고 규칙 폴백으로 끝낸다.
- 새 대화(홈·맥락)는 **먼저 이동, 나중에 응답**: `POST /coach/threads`는 스레드와 사용자 메시지, pending 어시스턴트 id를 즉시 돌려주고(목표 ≤200ms) 화면은 바로 대화로 이동한다.
- Cloudflare Access 경유 SSE: `Cache-Control: no-cache`, `X-Accel-Buffering: no`, 15초마다 `: ping` 주석 전송(프록시 유휴 타임아웃 방지).

---

## 7. 변경 컴포넌트·API

### 7.1 프론트엔드 (`frontend/src`, 파일당 300줄 이하)

| 파일 | 변경 |
|---|---|
| `routes/coach/+page.svelte` | 재작성: H0~H5 + 상시 컴포저, `{#if !isCreating}` 토글 제거, 우측 레일(≥1024). 조립만(≤150줄) |
| `routes/coach/+page.ts` | `/coach/threads?limit=3`·`/coach/engine`·`/today`(briefing 재사용)만 await 없이 streamed. 목록 오류/빈 구분 |
| `routes/coach/new/+page.svelte`·`+page.ts` | 신규: `ctx`·`from`(및 별칭 `activity`) 파싱, `GET /coach/context-preview` 로드, 맥락 카드·추천 질문·같은 맥락 스레드 안내 |
| `routes/coach/threads/+page.svelte` | 신규: 전체 대화(날짜 그룹, 검색, 페이지네이션 20) |
| `routes/coach/[threadId]/+page.svelte` | 재작성: 메시지 목록·날짜 구분선·진입 시 하단 스크롤·`↓ 새 답변`, `DrillHost`(§C3) 연결, 컨텍스트 패널 슬롯, 전역 헤더·탭바 숨김 플래그 |
| `routes/+layout.svelte`·`app.html` | 라우트 메타 `chrome: 'immersive'`면 헤더·탭바 숨김. viewport에 `viewport-fit=cover, interactive-widget=resizes-content`. 탭바 `pb-[env(safe-area-inset-bottom)]` |
| `lib/components/coach/ChatComposer.svelte` | 신규(홈·대화·새 대화 공용): 16px, `field-sizing: content`(폴백 auto-grow 1~5줄), IME 가드, coarse 포인터 Enter 규칙, 44px 원형 전송, 엔진 줄 포함 |
| `lib/components/coach/MessageBlock.svelte` | 신규: 어시스턴트 문서 블록/사용자 말풍선, 폴백 띠, 메타 줄, 드리프트 배너, 실패 액션, `이전 답변 보기 ▾` |
| `lib/components/coach/EvidenceRow.svelte` | 신규: `DrillChip`/`InfoTag`(§C2) 가로 스크롤 행 + `role` 처리 + `+n 근거` |
| `lib/components/coach/StreamStatus.svelte` | 신규: 단계 목록·점 3개·`[중단]`·`slow` 안내 |
| `lib/components/coach/EngineLine.svelte`·`EngineSheet.svelte`·`ScopeSheet.svelte` | 신규: 엔진 줄, 원인 시트, 전송 범위·동의 시트(토글 3개) |
| `lib/components/coach/ContextPanel.svelte`·`ContextCard.svelte` | 신규: 03e 5-B 컨텍스트 패널(맥락·쓴 데이터·전송 기록), 새 대화 맥락 카드 |
| `lib/components/coach/CoachNote.svelte` | 신규: H1(Today `TodayHero`의 compact 변형 재사용 가능 여부는 구현 시 판단) |
| `lib/components/coach/QuestionChip.svelte` | 신규: 질문 칩(말풍선 아이콘 + 텍스트, surface-3 배경, 테두리 없음, `✎` 보조). 근거 칩(§C2)과 모양이 달라야 한다 |
| `lib/components/coach/ThreadRow.svelte` | 신규: 제목·절대 날짜·`Q:` 질문·결론 1구절·미니 칩 2, `⋯` 메뉴 |
| `lib/components/plan/AdjustmentCard.svelte` | 31 신규 컴포넌트를 `compact` prop으로 재사용(H1·답변 안) |
| `lib/components/QuickInput.svelte` | Today 설계 변경 + 척도 앵커·중립 선택색·통증 제목(§4.6) |
| `lib/components/EvidenceQuote.svelte`·`MetricBreakdown.svelte` | 삭제(§C2 `DrillChip`/`InfoTag`, §C3 `DrillPanel`로 대체). D2에 `snapshot` prop 추가 |
| `lib/coachSuggestions.ts` | `homeTopics()`는 서버 `suggested_questions`의 오프라인 기본값으로만 남김. `followUps()` 삭제(서버 생성) |
| `lib/threadAge.ts` | `staleLabel` 7일 기준 삭제 → as-of 날짜 ≠ 오늘. `threadTitles` 접미사 삭제(서버 제목에 날짜 포함) |
| `lib/markdownLite.ts` | `localizeSource` 삭제(서버 `engine.label` 렌더) |
| `lib/api/coach.ts` | `createThread({message, chip_id?, context?, client_msg_id})`, `postMessage`, `streamMessage(mid)`(EventSource + 재연결 + 폴링 폴백), `cancel`, `regenerate`, `renameThread`, `deleteThread`, `getEngine`, `putConsent`, `getContextPreview` |
| 진입점 | `routes/today/+page.svelte:116` href → `/v2/coach/new?ctx=today:{date}&from=today`. 활동 상세(20 설계 `코치에게 묻기`)는 `ctx=activity:{id}`. D2 푸터(§C3.2 ④)·세션 상세(31)도 같은 형식 |

### 7.2 백엔드

| 파일 | 변경 |
|---|---|
| `src/analysis/recovery.py` | `RecoveryGrade(str, Enum)` = `EXCELLENT/GOOD/MODERATE/POOR`, `_recovery_grade()`는 enum 반환. 한국어 라벨 맵 |
| `src/ai/chat_engine_rules.py` | **S0**: `grade in ("A","B")` → `grade in (EXCELLENT, GOOD)`, `MODERATE` → 중강도, `POOR` → 회복, `None` → `회복 데이터 없음 — 부하 지표로만 판단`. 없는 목적지 문구 교체, 포맷터 적용. **S3**: 자유 텍스트 키워드 분기 폐지, `chip_id` 핸들러 레지스트리(`coach_rule_handlers.py`, 신규)로 이동. 파일 300줄 규칙 유지 |
| `src/ai/coach_rule_handlers.py` | 신규: 핸들러 = `(ctx) -> RuleAnswer{text, evidence[], followups[]}`. 목록 §7.3 |
| `src/ai/chat_engine.py` | `chat()` 반환을 `ChatResult{text, engine{status, provider, model, attempts[], fallback_reason}, evidence[], followups[], as_of, sent_scope}`로 변경(튜플 반환은 v1 `/ai-coach` 호환 래퍼로 유지). 체인은 동의한 provider만, 전체 45초 예산. 스트리밍 콜백 `on_event(stage|delta)` |
| `src/ai/chat_engine_providers.py` | provider별 연결 10초·응답 30초 타임아웃, `attempt` 기록(HTTP 상태·지연), 스트리밍 지원 provider는 `stream=True`, 모델 ID는 config에서만(하드코딩 `claude-sonnet-4-20250514` 등 제거) |
| `src/services/coach_evidence.py` | 신규: 규칙 경로 evidence = `readiness_decision.reasons/caveats` + 계획 세션 + 체크인. LLM 경로 evidence = 도구 결과·컨텍스트 항목 중 본문 인용값. 항목마다 스냅샷(`value, computed_at, version, as_of`) 기록. `build_evidence`(Today 복사) 삭제 |
| `src/services/coach_service.py` | 스레드 생성 즉시 반환 + 비동기 생성(작업 스레드), `client_msg_id` 멱등, 실패 시 `status=error` 어시스턴트 레코드, 제목 규칙(`9/27 오늘 훈련`, 맥락 있으면 `9/27 이지 9.3km`), 목록 `limit/offset`·미리보기 = 마지막 **사용자** 질문 + 결론 1구절, 드리프트 계산(GET 시 evidence별 현재값 조회) |
| `src/services/coach_engine_health.py` | 신규: 최근 20개 메시지의 `engine` 집계(연속 실패 수, 마지막 오류). 외부 호출로 상태를 탐지하지 않는다(설정 화면의 `연결 테스트`만 호출) |
| `src/services/readiness_decision.py` | Today S3 소관(공용). Coach는 `readiness_decision(date, include_checkin=True)`만 호출한다 |
| `src/ai/chat_context*.py` | 컨텍스트 빌더가 보낸 항목 목록(`sent_scope`)을 반환. 체크인 척도 정의 포함, `exclude_notes`면 메모 제외. 최근 7일 세션 회고 포함(31 §7.2) |
| `src/api/routes_coach.py` | 엔드포인트 §7.3 |
| `src/db_setup.py` | 마이그레이션 v20(아래). `/check-data-consistency` 대상 |

**DDL(v20, 추가 컬럼만)**
```
chat_messages + status TEXT DEFAULT 'done'   -- sending|pending|done|fallback|error|cancelled
              + client_msg_id TEXT           -- UNIQUE(thread_id, client_msg_id)
              + engine_json TEXT             -- {status, provider, model, attempts[], fallback_reason}
              + as_of TEXT                   -- 2026-09-25 (KST 날짜) 또는 ISO 시각
              + sent_scope_json TEXT         -- 외부 전송 기록(규칙 답변은 NULL)
              + followups_json TEXT
              + parent_message_id INTEGER    -- 재생성 시 이전 답변
chat_threads  + context_kind TEXT, context_ref TEXT, title_source TEXT, pinned INTEGER DEFAULT 0, deleted_at TEXT
user_settings: coach_consent {provider, accepted_at, exclude_notes, tools_enabled, fallback_enabled}  (저장소는 40 설정 설계와 공유)
```

### 7.3 API 계약

**`POST /api/v1/coach/threads`** (변경: 즉시 반환)
```json
요청 {"message":"목표 기록 가능할까?","chip_id":"goal_feasibility","client_msg_id":"c-7f3a",
      "context":{"kind":"today","ref":"2026-09-27"}}
201  {"thread":{"id":5,"title":"9/27 목표 기록","context":{"kind":"today","ref":"2026-09-27"}},
      "user_message":{"id":15,"status":"done","created_at":"2026-09-27T09:12:03+09:00"},
      "assistant_message":{"id":16,"status":"pending","stream_url":"/api/v1/coach/messages/16/stream"}}
```
- 같은 `client_msg_id` 재요청은 같은 응답(200)을 돌려준다. `context.kind` 별칭: `plan_session`→`session`.

**`POST /api/v1/coach/threads/:id/messages`**: 요청 `{message|chip_id, client_msg_id}` → 201 `{user_message, assistant_message{status:"pending", stream_url}}`.

**`GET /api/v1/coach/messages/:mid/stream`** (신규, `text/event-stream`)
```
event: stage   data: {"key":"tools","label":"데이터 확인 중: 예측 추이 · 최근 롱런 4회","tool":"get_metrics_trend"}
event: delta   data: {"text":"현재 예측은 3:40(3:26–4:03)으로 "}
event: evidence data: [{"kind":"drill","role":"supports","label":"예측 3:40","metric":"race_pred_marathon_sec",
                        "value":13223,"display":"3:40","target":"m.race_pred_marathon_sec@2026-09-27",
                        "snapshot":{"computed_at":"2026-09-27T06:10:00+09:00","version":"pred_v3","as_of":"2026-09-27"},
                        "cited":true}]
event: done    data: {"status":"ok","engine":{"provider":"gemini","model":"gemini-2.5-flash","tool_calls":3},
                      "as_of":{"basis":"generated","at":"2026-09-27T09:12:09+09:00"},"followups":["…"]}
event: error   data: {"status":"fallback","reason":"http_404","attempts":[{"provider":"gemini","model":"gemini-2.0-flash","status":"http_404","ms":180},{"provider":"groq","status":"http_404","ms":150}]}
```
`Last-Event-ID` 재개 지원, 15초 ping. 폴백이면 `error`(fallback) 뒤에 규칙 답변 `delta`·`evidence`·`done`이 이어진다.

**`GET /api/v1/coach/threads/:id`** (확장): 메시지마다 `status, engine{status,label,provider,model,reason}, as_of, content_display?, evidence[]{…, role, snapshot, current{value,display,computed_at}|null, drifted}, followups[], sent_scope|null`.

**`GET /api/v1/coach/threads?limit=20&offset=0&q=`**: 행 `{id, title, context, pinned, last_question, last_conclusion, last_at(+09:00), evidence_mini[2]}`.

**기타**
- `POST /coach/messages/:mid/cancel` → `{status:"cancelled"}` · `POST /coach/messages/:mid/regenerate` 요청 `{mode:"ai"|"rule"}` → 새 pending id(`parent_message_id` 연결)
- `PATCH /coach/threads/:id` `{title?, pinned?}` · `DELETE /coach/threads/:id`(소프트 삭제) · `POST /coach/threads/:id/restore`
- `GET /coach/engine` → `{mode:"llm|rule_only|rule_by_choice", selected:{provider,model}, chain:[…동의한 것만], health:{consecutive_failures:3, last_ok_at, last_error:{provider,model,status,at}}, consent:{provider, accepted_at, exclude_notes, tools_enabled, fallback_enabled}|null, scope:[{item,period,optional}]}`
- `PUT /coach/consent` `{provider, exclude_notes, tools_enabled, fallback_enabled}`
- `GET /coach/context-preview?ctx=activity:17414` → `{card{title, lines[], href}, suggested_questions[{chip_id, text}], existing_thread_id|null, scope_extra:"이 활동 요약·랩"}`
- `GET /coach/suggestions?at=home` → `[{chip_id, text}]`(국면·목표·오늘 상태 기반, 핸들러가 있는 칩만)

**규칙 핸들러 목록(`chip_id` → 최소 응답)**

| chip_id | 질문 | 규칙 응답(모두 §4.5 포맷, 근거 칩 포함) |
|---|---|---|
| `today_advice` | 오늘 훈련 조언 | `readiness_decision` 헤드라인·세션·reasons/caveats, 조정 제안 있으면 같은 adjustment 카드. 오늘 완료면 결과 요약 + 내일 세션 |
| `goal_feasibility` | 목표 기록 가능할까? | 예측(Today 허브와 같은 값·범위) vs 목표, 차이(분·초/km), 최근 4주 예측 추이 방향, 차이를 줄이는 조건 1~2개(31 R6 MP 간극 문장 재사용) |
| `race_build` | 레이스까지 어떻게 쌓을까? | 계획 단계·남은 주·피크 주 km·대회일 예상 CTL/TSB(31 `load_projection`) + `계획 보기 ›`. 계획 없으면 `계획 만들기 ›` |
| `week_plan` | 이 폼이면 이번 주엔? | 이번 주 남은 세션 목록 + 오늘 판정 레벨에 따른 31 R8 매핑 결과 |
| `taper_when` | 테이퍼 언제부터? | 계획의 테이퍼 시작일·감량률, `x.taper` 칩 |
| `injury_check` | 부상 위험 확인 | CIRS·ACWR 상태(서버 status), 통증 입력, 가장 큰 기여 항목 |
| `explain_{slug}` | 왜 테이퍼하면 폼이 올라가? 등 | registry `meaning.what/so_what` 설명 + 내 현재 값 |
| (자유 텍스트) | — | `지금은 AI가 연결되지 않아 이 질문에 답할 수 없어요.` + 오늘 상태 요약 1줄 + 답할 수 있는 질문 칩 3개 + `[AI로 다시 시도]` |

### 7.4 P7 일관성 계약(31 설계와 연결)

1. Coach의 오늘 판단은 `readiness_decision(date)`만 쓴다. 판정의 원천은 31 R8의 **Today CRS 게이트**(ACWR·HRV·BB·TSB·CIRS + 체크인, 레벨 녹·황·주황·적)이며, Coach 문장은 Today 히어로 헤드라인과 같은 문자열을 재사용한다(스냅샷 테스트).
2. 오늘 CRS 발 조정(`plan_adjustments.source='crs'`, `decision='proposed'`)이 있으면 Coach는 **같은 id**의 카드를 보여 준다. Coach가 따로 제안을 만들지 않는다.
3. Coach 발 제안(`source='coach'`)은 사용자가 변경을 요청했을 때만 만든다("이번 주 너무 힘들어"). 제안은 `readiness_decision.intensity_cap`을 넘을 수 없다. 레벨이 적이면 상향 제안이 불가하고, 주황이면 품질 세션 유지 제안이 불가하다.
4. 미래 날짜 질문("내일 인터벌 해도 돼?")에는 31 R8처럼 `당일 아침 컨디션으로 판단해요 · 지금 추세 {양호}`로 답하고 단정하지 않는다.
5. 적용 결과는 31 R1(유효 계획)·R3(이행률)에 반영되고, 답변 카드는 `적용됨 · 9:12 · 계획 보기 ›`로 바뀐다. Today·계획·Coach 세 화면에서 같은 결정 상태가 보여야 한다.

**레거시 메시지 이관(1회)**: 기존 어시스턴트 메시지 6건은 본문을 바꾸지 않는다. `as_of` = `created_at`의 KST 날짜, `engine.status` = `rule`이면 `fallback`인지 알 수 없으므로 `legacy_rule`(라벨 `규칙 답변(이전 방식)`)로 둔다. evidence에는 `role:"legacy"`를 붙여 칩 행 앞에 `당시 Today 근거 — 이 답변의 입력과 다를 수 있어요`를 표시한다. `drill:null` 항목은 InfoTag로 렌더한다.

---

## 8. 수용 기준

**데이터·판정**
- [ ] `_respond_training_recommendation` 파라미터 테스트: 등급 `excellent/good/moderate/poor/None` 5종의 첫 문장이 각각 고강도 가능/고강도 가능/중강도/회복/`회복 데이터 없음`으로 나온다. `A/B/C` 문자열이 코드에 0건이다(grep).
- [ ] 같은 날 같은 시각에 Today 히어로 헤드라인과 Coach `today_advice` 첫 문장이 같다(API 스냅샷 테스트). 9/24 픽스처(BB 100·수면 91·HRV 97, 재계산 TSB +2.6)에서 "휴식 권장"이 나오지 않는다.
- [ ] 체크인 피로 8 저장 → 같은 날 `today_advice` 답변에 `피로 8 (직접 입력)` 칩이 있고 판정 레벨이 한 단계 이상 내려간다.
- [ ] 모든 어시스턴트 메시지의 evidence 항목이 `snapshot.computed_at`과 `as_of`를 가진다(레거시 제외). `build_evidence` 호출은 0건이다.
- [ ] 규칙 답변의 근거 칩 값이 본문 숫자와 §C4 포맷 기준으로 같다(`TSB −11` 본문 = 칩). 본문에 원시 부동소수(소수 3자리 이상)·`초/km`·영문 등급/유형 키가 0건이다(규칙 핸들러 전수 스냅샷).
- [ ] 스레드 4 메시지 14의 TSB 칩 → D2 스냅샷 줄에 `답변 당시 −10.7` / `현재 −3.3`이 둘 다 보이고 드리프트 배너가 뜬다.
- [ ] 홈·후속 질문 칩 전부가 `chip_id` 핸들러를 가진다(칩 목록 ↔ 핸들러 레지스트리 대조 테스트). "목표 기록 가능할까?"의 답에 예측·목표·차이가 들어 있다.

**엔진 투명성·P8**
- [ ] provider 404를 모킹하면 메시지 `engine.status = fallback`, `reason = http_404`이고, 화면에 amber 띠·`[AI로 다시 생성]`이 보인다. 폴백인데 띠가 없는 메시지는 0건이다.
- [ ] 연속 3회 폴백이면 홈 H0 배너가 뜨고, 1회 성공하면 사라진다.
- [ ] 동의 전에는 외부 호출이 0건이다(provider 모킹 호출 수 검사). `fallback_enabled=false`면 체인에 두 번째 provider가 없다. `exclude_notes=true`면 프롬프트에 메모 문자열이 없다(컨텍스트 스냅샷 테스트).
- [ ] 입력창 위 엔진 줄이 홈·대화·새 대화 세 화면에 항상 있다.

**흐름·상호작용**
- [ ] Today `Coach에게 묻기` → 추천 질문 1탭 = 답변 스트리밍 시작까지 2탭. 활동 상세 → Coach도 2탭. 맥락 카드가 보인다.
- [ ] 같은 `ctx`로 다시 들어오면 `이어서 묻기`가 1순위로 나오고, 칩을 보기만 하고 나가면 스레드가 생기지 않는다.
- [ ] 홈 질문 칩 1탭 = 전송(현재 2탭 → 1탭).
- [ ] 대화 진입 시 마지막 메시지가 뷰포트 안에 있다. 근거 칩 → D2 → 뒤로가기 1회 = D2 닫힘, 2회 = 이전 화면(§C3.3).
- [ ] 한글 조합 중 Enter로 잘린 전송이 0건이다(`isComposing` 단위 테스트 + Playwright IME 시뮬레이션).
- [ ] 전송 실패 모킹 → 말풍선에 `다시 보내기`가 있고, 재전송 후 DB에 같은 사용자 메시지가 1건이다(`client_msg_id` 멱등).
- [ ] 스레드 삭제 → 5초 안에 `되돌리기`로 복원된다.

**성능(U9)**
- [ ] 전송 클릭 → 내 말풍선 표시 ≤100ms. `POST /coach/threads` 응답 ≤200ms(생성 대기 없음).
- [ ] LLM 경로 첫 `stage` 이벤트 ≤1s, 첫 `delta` ≤3s(p50 측정 기록). 체인 전체 상한 45초, 20초 무응답이면 `slow` 안내가 뜬다.
- [ ] 규칙 폴백 답변 완료 ≤1.5s(404 즉시 실패 기준).
- [ ] 홈 첫 의미 있는 콘텐츠(H1) ≤1.0s, 대화 전환 ≤300ms(현재 152~170ms 유지).

**시각·접근성**
- [ ] 모바일 대화 화면 고정 크롬 합계 ≤130px(현재 약 220px). 입력 글꼴 16px(iOS 확대 없음). safe-area 적용 확인(iPhone 프레임 스크린샷).
- [ ] 근거 칩·질문 칩·컨디션 버튼·전송·`←` 히트 영역 ≥44×44px. 컨디션 피로 버튼 모바일 폭 ≥44px(2행 5열).
- [ ] 이모지·문자 아이콘 0건(§C8). 한글 텍스트에 mono 폰트 0건. 목록 미리보기 대비 ≥4.5:1.
- [ ] 데스크톱 대화 열 ≤720px, D2는 대화를 가리지 않고 밀어낸다.

---

## 9. 구현 순서

| 단계 | 묶음 | 의존 | 규모 |
|---|---|---|---|
| **S0 핫픽스** | 등급 enum·매핑·파라미터 테스트, 규칙 본문 포맷터·한국어 라벨, 없는 목적지 문구, "자동 반영" 문구 정정, `staleLabel` → as-of 날짜 기준, IME 가드, 컨디션 척도 앵커 라벨 | 없음. BACKLOG 등록 후 Hotfix로 진행 가능 | S |
| **S1 엔진 투명성·P8** | `ChatResult`·`attempts`·`engine_json` 저장, 타임아웃 예산 45초, 모델 ID config 일원화, 엔진 라벨 4상태·폴백 띠·원인 시트·H0 배너, `/coach/engine`, 동의 시트·범위 시트·체인 동의 필터, `sent_scope` 기록, `[AI로 다시 생성]`(동기) | S0. 모델 ID 404 원인 확인(운영 설정, 추정) | M |
| **S2 답변 근거 v2** | `coach_evidence.py`(사용 입력·인용 판정·스냅샷), `role`, 레거시 이관, 드리프트 계산, D2 스냅샷 줄, `DrillChip`/`InfoTag` 교체 | Today S1(§C2)·S2(§C3 `DrillPanel`) | M |
| **S3 판정 단일화·핸들러·체크인** | `readiness_decision` 호출로 `today_advice` 교체, `chip_id` 핸들러 7종, 자유 텍스트 정직 응답, `/coach/suggestions`, 서버 후속 질문, 체크인 입력 연결·칩 | Today S3(`readiness_decision`), 31 S1(이행·예측 값) | M |
| **S4 비동기·스트리밍·오류** | 즉시 반환 API, 작업 스레드 생성, SSE(`stage/delta/evidence/done/error`, 재개·ping), 폴링 폴백, 취소·재생성, `client_msg_id` 멱등, 상태 기계 UI | S1 | L |
| **S5 셸·레이아웃** | immersive 크롬·safe-area·viewport, `ChatComposer`, `MessageBlock` 타이포, 날짜 구분선·시각, 홈 재배치(H0~H5, 우측 레일), `ThreadRow`, 스레드 관리(이름·고정·삭제·검색·전체 대화) | S1(엔진 줄), Today S1(§C8 토큰·아이콘) | M |
| **S6 맥락 진입** | `/coach/new`, `context-preview`, `context_kind/ref`, 같은 맥락 스레드 재사용, 컨텍스트 패널, 진입점 4곳(Today·활동·D2·세션) | S4, Today S6, 20 S7, 31 S8 | M |
| **S7 계획 연결(P7)** | 답변 안 `AdjustmentCard`(CRS id 공유)·Coach 발 제안(`intensity_cap` 제한), 미래 날짜 답변 규칙 | 31 S5(`plan_adjustments`), S3 | M |

S0은 다른 모든 단계보다 먼저 배포한다. S1과 S5는 병행할 수 있다. 저장된 스레드 6개 답변은 S2 레거시 이관 전까지 결론이 틀린 상태로 남는다. 그래서 S0 배포 때 해당 메시지 3건(msg 8·12·14)에 `이 답변은 판정 오류(9/27 수정)로 틀렸을 수 있어요 · 지금 다시 묻기 ↻` 배너를 한 번 붙인다(메시지 id 목록 기반, 본문 불변).

---

## 10. 발견 → 설계 추적표

| 발견 | 설계 위치 | 상태 |
|---|---|---|
| F-DATA-01 등급 비교 버그 | §1 상충표, §7.2 recovery·rules(S0), §8 | 반영 |
| F-DATA-02 칩 = Today 근거 복사 | §4.4, §7.2 `coach_evidence`, §7.4 레거시 | 반영 |
| F-DATA-03 본문·칩·드릴 값 불일치, as-of 없음 | §4.2, §4.4 스냅샷 줄·드리프트, §7.3 evidence 스키마 | 반영 |
| F-DATA-04 LLM 404 조용한 폴백, 전송 범위 미고지 | §4.1, §4.3, §7.3 `/coach/engine`, S1 | 반영. 404 원인(모델 ID) 확정은 운영 확인 필요(추정) |
| F-DATA-05 추천 질문 오라우팅 | §1 상충표, §7.3 핸들러 목록, §8 | 반영 |
| F-DATA-06 체크인 미반영·척도 방향 | §4.6, §3 H2, §7.2 chat_context, S0·S3 | 반영(임계값은 Today 기준 ≥7) |
| F-DATA-07 판정이 TSB·버그 등급에 의존 | §1 상충표, §7.4 P7 계약(`readiness_decision` 공용) | 반영. Coach 전용 우선순위표는 채택하지 않고 Today·31 판정에 위임 |
| F-DATA-08 단위·포맷·용어, 원천 선택 | §4.5, §7.2 포맷터 | 반영. 오늘 활동을 `v_canonical_activities`에서 읽는 변경은 S3 `readiness_decision` 입력으로 흡수 |
| F-DATA-09 레이스 아침 TSB 가정 불명 | §4.4 투영 문구, D2 `x.taper`(Today §3·§5) | 반영(Today 설계 참조) |
| F-UI-01 칩→패널 값 불일치, 기준일 없음 | §4.4 스냅샷 줄, §5 D2 마커, §C3 헤더 기준일 | 반영 |
| F-UI-02 칩 2종 구분 없음, mono·tofu | §C2 참조, §4.4 role, §2.4 가로 스크롤 | 반영 |
| F-UI-03 모바일 크롬·키보드·safe-area·iOS 확대 | §1 상충표, §2.4, §7.1 layout·ChatComposer, §8 | 반영 |
| F-UI-04 IME Enter | §3 컴포저 행, §7.1 ChatComposer, §8, S0 | 반영 |
| F-UI-05 말풍선 위계·메타·폭 | §4.5 렌더, §4.2 날짜·시각, §2.3 720px | 반영 |
| F-UI-06 근거 시트 형태 | §1 상충표(§C3 채택) | 반영(UI안의 50/90 스냅 시트는 채택하지 않음, 이유: §C3 일관성) |
| F-UI-07 스레드 목록 구분 불가 | §2.1 H4, §7.1 ThreadRow, §7.3 목록 응답 | 반영(마스터-디테일은 보류: 스레드 30개 초과 시 재검토) |
| F-UI-08 컨디션 폼 척도·색·타깃 | §4.6, §1 상충표(Today B2), §8 | 반영(모바일 시트 대신 Today B2 인라인) |
| F-UI-09 주 행동 약함, 칩 3종 동형 | §2.1 C·H3, §7.1 QuestionChip | 반영 |
| F-UI-10 로딩·전송 상태 | §6.2, §3 `↓ 새 답변` | 반영 |
| F-UI-11 아이콘·셸 일관성, v1 문구 | §C8 참조, §4.1 문구 교체, S0 | 반영 |
| F-UX-01 규칙 템플릿인데 알리지 않음 | §4.1, §2.6, §7.3 핸들러·자유 텍스트 응답, S0·S1 | 반영 |
| F-UX-02 칩이 답변 근거 아님·드릴 막다름 | §4.4, §3 원천 활동 칩·D2 푸터, §C3 4블록 | 반영 |
| F-UX-03 맥락 가지고 Coach 진입 불가 | §2.5, §1 상충표(URL), §7.3 `context`·`context-preview`, S6 | 반영 |
| F-UX-04 대기 피드백·스트리밍·취소 | §6.2, §7.3 SSE, §8 성능, S4 | 반영 |
| F-UX-05 실패 메시지 방치·재시도 없음 | §6.2 `send_failed`·`error`, §7.3 멱등·regenerate | 반영 |
| F-UX-06 스레드 관리·시간 없음 | §3 행 메뉴·전체 대화, §4.2, §7.2 제목 규칙, §2.5 일일 스레드 | 반영 |
| F-UX-07 홈 구조(묻기가 토글 뒤) | §2.1~2.2, §3 H3 즉시 전송 | 반영 |
| F-UX-08 컨디션 "자동 반영" 약속 불이행 | §4.6, §3 H2 `[받기]`, §8, S0·S3 | 반영 |
| F-UX-09 드릴 시트가 대화 덮음·뒤로가기 | §C3 참조, §2.3 | 반영 |
| F-UX-10 본문 포맷·용어 | §4.5 | 반영 |
| F-UX-11 후속 질문이 근거 slug로 결정 | §7.3 `followups`, 핸들러 한정 | 반영 |
| F-UX-12 외부 LLM 전송 고지 없음 | §4.3, §8 P8 | 반영 |
| F-UX-13 행동 연결 없음(경쟁 대비) | §7.4 P7 계약·조정 카드(S7), §4.4 소스 간 caveat | 부분 반영. 활동 상세 하단 "이 활동으로 나눈 대화" 아카이브는 보류(20 설계 S7 이후 활동 상세 IA와 함께 결정). 선제 알림(Coach가 먼저 말 걸기)은 H1 코치 노트로 대체 |
