# Coach 홈·대화·컨디션 입력 — UI(시각·인터페이스) 리뷰

**리뷰일**: 2026-09-27
**대상**: `/v2/coach`(Coach 홈), `/v2/coach/:threadId`(대화, 실측 스레드 4), Coach 홈의 컨디션 입력 폼(QuickInput compact)
**근거**: `screenshots/coach-{desktop,mobile}.png`, `coach-thread-{desktop,mobile}.png`, `coach-thread-evidence-{desktop,mobile}.png`, `coach-checkin-open-{desktop,mobile}.png`, `raw/coach.txt`, `raw/coach-thread.txt`, `raw/interact-mobile.json`, 실 API GET(`/api/v1/coach/threads`, `/coach/threads/4`, `/library/metrics/{tsb,utrs}`)
**코드**: `frontend/src/routes/coach/+page.svelte`, `routes/coach/[threadId]/+page.svelte`, `lib/components/{ChatBody,EvidenceQuote,MetricBreakdown,QuickInput}.svelte`, `lib/{evidence,markdownLite,threadAge,coachSuggestions}.ts`, `routes/+layout.svelte`

요약:
1. **근거 칩을 누르면 칩과 다른 숫자가 날짜 없이 나온다(확인).** 답변 본문은 `TSB -10.7`, 칩은 `TSB -11 (피로 누적)`인데, 칩을 누르면 패널에 `-3.3`만 크게 표시된다. 패널은 9/25 값을 **지금 다시 계산해서** 보여 준다. 패널에는 날짜·as-of·"답변 당시 값"이 없어서 사용자는 어느 숫자가 맞는지 판단할 수 없다. 근거 칩은 Coach의 핵심 약속(P1)인데, 이 칩이 신뢰를 오히려 깎는다.
2. **근거 칩 4개 중 2개는 버튼, 2개는 span인데 겉모습이 같다.** 칩은 모노 글꼴로 한글을 렌더해 자간이 벌어지고, 이모지 아이콘은 □로 깨진다. 후속 질문 칩과 주제 칩도 같은 알약 모양이어서 "근거 보기"와 "바로 전송"을 모양으로 구별할 수 없다.
3. **모바일 대화 화면은 크롬이 두껍고 입력창 설계가 모바일에 맞지 않는다.** 상단 헤더 2단(약 106px)과 하단 입력바+탭바(약 115px)가 고정되어 844px 중 약 26%를 차지한다. 입력창은 14px라 iOS에서 포커스 시 확대된다(추정). safe-area 처리도 없고, 키보드가 열려도 탭바가 남는다. Enter 전송 로직은 한글 IME 조합(`isComposing`)을 검사하지 않는다.
4. **대화 타이포와 메타 정보가 약하다.** 메시지에 시각이 없고, 2일 전 답변의 `D-58`(오늘은 D-56)이 "당시 기준" 표시 없이 현재 값처럼 보인다. 목록 미리보기 4개 중 3개가 같은 문장("오늘의 훈련 추천 피로 회복이 필요합니다…")으로 시작해 구별되지 않는다. 사용자 말풍선이 흰색(#f1f5f9)이라 화면에서 가장 밝은 요소가 질문이 되고, 정작 답변은 뒤로 밀린다.
5. **컨디션 입력 폼은 척도 의미가 보이지 않고 터치 타깃이 작다.** 피로 1~10에 양 끝 라벨이 없다. 모바일에서 버튼은 약 29px 폭, 통증·저장 버튼은 약 32px 높이다. 선택색도 의미와 어긋난다(피로 10 = teal "좋음"색, 통증 "없음" = amber "주의"색).

## 발견

### [치명] F-UI-01 근거 칩 → 패널 값 불일치, 패널에 기준일·당시값 없음
- 현상: 스레드 4의 답변은 본문 `TSB -10.7`, 칩 `TSB -11 (피로 누적)`이다. 칩을 누르면 하단 시트가 열리고 영어 제목 "Training Stress Balance" 아래에 `-3.3 RunPulse · formula_v1`만 표시된다. 날짜, 단위, 설명, 산식(CTL−ATL), 추이가 없다. 같은 화면에 −10.7 / −11 / −3.3 세 값이 공존한다. UTRS도 칩은 `75`, 패널은 `76.3`이다.
- 근거: `coach-thread-evidence-desktop.png`·`-mobile.png`. API `GET /coach/threads/4`의 evidence에는 `tsb value -10.7, drill {scope_type: daily, scope_id: 2026-09-25}`가 있다. `GET /library/metrics/tsb?scope_type=daily&scope_id=2026-09-25` → `value -3.3`, `children [] inputs []`. `utrs` 같은 날짜 → 76.3. 코드 `MetricBreakdown.svelte:55-57,73-81`(날짜·as-of 출력 없음, value 원시 출력), `evidence.ts:20-22`(스냅샷 value를 패널에 전달하지 않음). 반올림 불일치(본문 −10.7, 칩 −11)는 칩 label을 서버가 만들 때 생긴다.
- 왜 문제인가: P1(Evidence-First) 정면 위반이며 정보 정확성의 치명 사례다. 근거를 확인하려고 누르면 다른 숫자가 나와서, 답변 전체를 믿지 못하게 된다. 원인이 재계산(데이터 영역, data.md 참조)이더라도 **UI가 기준일과 스냅샷을 드러내지 않는 것**은 독립된 결함이다.
- 개선안(Evidence Sheet 사양, Today F-UI-03 Contribution Waterfall과 같은 컴포넌트로 통합):
  - 헤더: 한국어 이름 `폼(TSB)` + 한 줄 의미("체력−피로. 레이스 전 +5~+25 권장") + **기준일 칩 `9/25(목) 기준`**.
  - 값 행: `답변 당시 −10.7` → `현재 재계산 −3.3`을 나란히 두고, 다르면 amber 점과 "이후 데이터 동기화로 값이 바뀌었습니다(9/26 02:10)" 1줄을 붙인다. 같으면 한 값만 보인다. 이를 위해 칩 props에 snapshot value·computed_at을 넘긴다(`adaptEvidence`에서 `ev.value` 전달).
  - 본문: children이 없는 메트릭은 `CTL 73.8 − ATL 77.1 = −3.3` 산식 줄(mono 13px) + 14일 미니 추이(기준일 마커, 최적 밴드) + "Library에서 전체 보기 →".
  - 칩 라벨 숫자는 본문과 같은 정밀도(소수 1자리)로 통일한다. 반올림은 한 곳(`formatMetricValue`)에서만 한다.

### [치명] F-UI-02 근거 칩 2종(버튼/span)이 시각적으로 같고, 글꼴·아이콘이 깨짐
- 현상: 칩 4개 중 `42km 목표 D-58`, `레이스 아침 TSB +25 (테이퍼 시)`는 `drill: null`이라 span이고, `TSB -11`, `UTRS 75`만 버튼이다. 테두리, 배경, 글자색이 동일하다. 차이는 hover 배경뿐이라 모바일에서는 구별할 수 없다. 칩은 `font-mono text-xs`(12px)라 한글이 모노 폴백으로 렌더되어 "레이스  아침  TSB  +25"처럼 벌어진다. 아이콘 📊는 □(tofu)로 보인다. 칩 높이는 약 24~26px로 44px에 미달한다.
- 근거: `coach-thread-desktop.png`(y≈302), `coach-thread-mobile.png`, API evidence `drill` 값, 코드 `EvidenceQuote.svelte:10,26-43`(button/span 클래스 동일, `font-mono`, 이모지 아이콘).
- 왜 문제인가: U4(누를 것 같은 것이 반응하는가)와 P2 위반이다. 반은 눌리고 반은 무반응이라 사용자는 모든 칩을 의심하게 된다. Today F-UI-06·07과 같은 원인이다.
- 개선안:
  - **대화형 칩**: 테두리 `fg-secondary/40`, 끝에 `›`, 높이 32px + 투명 패딩으로 히트 영역 44px, `active:scale-[.97]`.
  - **정보형 칩**: 테두리 없이 `fg-secondary` 텍스트 + 앞에 점 구분자만 둔다. 가능하면 드릴 대상을 만들어 없앤다(`race_days_left`→Coach 계획 D-day, `race_form_projection`→Today 폼 차트 미래 구간).
  - 글꼴은 sans로 쓰고 숫자만 `.num`(tabular mono)으로 쓴다. 아이콘은 `Icon.svelte`의 SVG 12px로 교체한다.
  - 모바일에서는 칩 4개가 세로로 4줄(약 270px)을 차지하므로(`coach-thread-mobile.png`), 가로 스크롤 한 줄(`overflow-x-auto snap-x`, 오른쪽 끝 페이드)로 바꾼다.

### [중요] F-UI-03 모바일 대화 레이아웃 — 두꺼운 고정 크롬, 키보드·safe-area·iOS 확대 미대응
- 현상:
  - (a) 전역 헤더 `RunPulse ☰`(약 56px)와 스레드 헤더 `← 오늘 훈련 조언`(약 50px)이 이중으로 쌓인다. 하단에는 입력바(약 60px, `sticky bottom-14`)와 탭바(약 54px)가 겹쳐 쌓인다. 390×844 뷰포트에서 고정 크롬이 약 220px(26%)다. 키보드(약 300px)가 열리면 메시지 영역은 300px 안팎만 남는다(추정).
  - (b) 입력 textarea가 `text-sm`(14px)이다. iOS Safari는 16px 미만 입력에 포커스하면 화면을 확대한다(추정, 실기기 미확인). 홈의 새 대화 textarea와 컨디션 메모도 같다.
  - (c) `viewport`에 `viewport-fit=cover`와 `interactive-widget`이 없고 `env(safe-area-inset-bottom)`을 쓰는 곳이 0건이다. PWA/홈 화면 실행 시 탭바가 홈 인디케이터와 겹친다(추정).
  - (d) 입력바 위치가 `bottom-14`(탭바 높이 추정치)라는 매직 넘버에 의존한다. 메시지 영역 `min-h-[calc(100dvh-15.5rem)]`도 크롬 높이를 하드코딩했다.
  - (e) `rows={1}` + `max-height:8rem`인데 자동 높이 조절이 없어, 긴 메시지도 1줄 높이 안에서 스크롤된다.
- 근거: `coach-thread-mobile.png`, `app.html:5`, grep `safe-area|interactive-widget` 0건, `[threadId]/+page.svelte:119-120,187-199`, `+layout.svelte:26-38,44-47`.
- 왜 문제인가: 대화는 모바일에서 가장 오래 머무는 화면이다. 입력 중 볼 수 있는 대화 양이 적고, 확대·가림은 "모바일 깨짐"(중요 기준)에 해당한다.
- 개선안:
  - 대화 라우트에서는 **전역 헤더와 탭바를 숨기고** 스레드 헤더 하나(48px: `←` 44px 히트 영역, 제목, 우측 `⋯` 메뉴)만 둔다(메신저 앱의 표준 패턴). 탭 복귀는 `←`로 한다.
  - 입력바는 `position: sticky; bottom: 0` + `padding-bottom: max(12px, env(safe-area-inset-bottom))`로 두고, viewport에 `viewport-fit=cover, interactive-widget=resizes-content`를 추가한다. iOS는 `visualViewport` resize로 보정한다.
  - 입력 글꼴은 16px(`text-base`)로 올린다. `field-sizing: content`(폴백으로 스크립트 auto-grow)를 쓰고 1~5줄까지 늘어나게 한다.
  - 전송 버튼은 44×44 원형 아이콘 버튼(↑ 화살표)으로 바꾸고, 비어 있으면 숨기거나 `fg-muted` 윤곽만 둔다. 현재는 bg-fg-primary opacity-40 회색 블록이다.

### [중요] F-UI-04 Enter 전송이 한글 IME 조합을 검사하지 않음
- 현상: `handleKeydown`이 `e.key === 'Enter' && !e.shiftKey`면 바로 `send()`를 호출한다. `e.isComposing`(또는 keyCode 229)을 확인하지 않는다. 한글 입력 중 마지막 음절이 조합 상태일 때 Enter를 누르면 Chrome·Safari에서 조합 중 문자가 잘린 채 전송되거나, 마지막 글자가 입력창에 남아 중복된다(추정, 재현 미실시. 알려진 한국어 IME 동작). 저장소 전체에서 `isComposing` 사용은 0건이다.
- 근거: `[threadId]/+page.svelte:93-98`, `coach/+page.svelte:63-68`.
- 왜 문제인가: 주 사용자가 한국어로 입력하는 핵심 과업이다. 오입력이나 중복 전송이 생기면 대화 품질과 신뢰가 떨어진다.
- 개선안: `if (e.isComposing || e.keyCode === 229) return;`을 공통 `ChatComposer` 컴포넌트에 넣는다. 모바일(`pointer: coarse`)에서는 Enter를 줄바꿈으로 두고 전송은 버튼으로만 한다(모바일 메신저 관행).

### [중요] F-UI-05 메시지 타이포·위계 — 흰 사용자 말풍선이 답변을 압도, 메타 정보 없음
- 현상:
  - (a) 사용자 말풍선은 `bg-fg-primary`(#f1f5f9) + 어두운 글자라 다크 화면에서 가장 밝은 블록이다. Coach 답변은 surface-2 위 14px로 상대적으로 가라앉는다.
  - (b) 답변 본문은 14px/`leading-snug`(1.375)로, 한글 장문 가독 기준(1.5~1.6)보다 빽빽하다. 헤딩 "오늘의 훈련 추천"도 본문과 같은 14px semibold라 위계 차이가 약하다.
  - (c) 목록 항목이 `·`(fg-muted) 문자로 렌더되어, 본문 첫 줄 앞에 흩점처럼 보인다(`· TSB -10.7 — …`).
  - (d) 세션 유형 `recovery`가 영어로 굵게 강조된다. `📋`는 □로 보인다.
  - (e) 소스 라벨 "규칙 기반 답변"(11px)이 본문과 칩 사이에 끼어 있다. 메시지 시각이 없어 2일 전 답변의 `D-58`이 현재처럼 읽힌다(오늘 D-56). `staleLabel`은 7일 이상, 목록에서만 동작한다.
  - (f) 데스크톱 대화 폭에 제한이 없다. 사용자 말풍선은 x=1264, 답변은 x=224에서 시작해 시선이 1,040px를 오간다. 입력창은 973px 폭이다.
- 근거: `coach-thread-desktop.png`, `coach-thread-mobile.png`, `[threadId]/+page.svelte:128-151`, `ChatBody.svelte:13-25`, `markdownLite.ts:73-77`, `threadAge.ts:2-7`, API `created_at 2026-09-25 01:51:08`.
- 왜 문제인가: P5(Quiet Data) 위계 문제다. 답을 읽는 화면인데 질문이 가장 눈에 띈다. 시각 부재는 오래된 근거를 현재 상태로 오독하게 만든다(U8·P1).
- 개선안:
  - 사용자 말풍선은 `surface-3`(#334155) + fg-primary, 최대 폭 75%로 둔다. Coach 답변은 **말풍선 대신 전폭 문서 블록**으로 쓴다: 좌측 Coach 아바타 20px, 본문 15px/1.6, 헤딩 16px semibold(ChatGPT·Claude식 답변 레이아웃).
  - 목록은 실제 `<ul>` + 4px 원형 불릿으로 렌더한다. 세션 유형은 `sessionTypeLabel()`로 한국어화("회복 달리기")한다.
  - 메타 줄(답변 하단, 12px fg-secondary): `규칙 기반 · 9/25 10:51 기준 · 근거 4`. 24시간이 지난 답변에는 `당시 기준` amber 태그를 단다. 날짜가 바뀌는 지점에는 `── 9월 25일 (목) ──` 구분선을 둔다.
  - 데스크톱 대화 열은 `max-w-[720px] mx-auto`로 두고, 남는 오른쪽은 설계 5-B의 **컨텍스트 패널**(폭 360px) 자리로 쓴다. 근거 시트도 데스크톱에서는 이 패널에 연다(현재는 전폭 하단 시트가 사이드바까지 덮음, `MetricBreakdown.svelte:52`).

### [중요] F-UI-06 근거 시트 형태 — 데스크톱 전폭 하단 시트, 모바일 드래그·safe-area 없음, 영어 제목
- 현상: 데스크톱에서는 `inset-x-0` 하단 시트가 1280px 전체(사이드바 포함)를 덮는다. 값 `-3.3` 하나에 높이 약 160px, 폭 1,280px를 쓴다. 모바일에서는 탭바 위에 겹치고, 드래그 핸들이 없으며 `✕`는 문자 아이콘이다(히트 영역 약 28px). 제목은 서버 label 그대로 "Training Stress Balance"다. 로딩은 "불러오는 중…" 텍스트라 시트 높이가 튄다(interact-mobile settled 416ms).
- 근거: `coach-thread-evidence-*.png`, `MetricBreakdown.svelte:43-62,67-68`, `raw/interact-mobile.json`("근거 칩 TSB" settledMs 416).
- 왜 문제인가: 근거 보기는 Coach 대화의 주 인터랙션인데, 한 숫자를 위해 화면 전체를 가리고 대화 맥락을 끊는다.
- 개선안: F-UI-05의 컨텍스트 패널(데스크톱)과 하단 시트(모바일)를 같은 `EvidenceSheet` 컴포넌트로 만든다. 모바일 시트는 드래그 핸들, 스냅 50%/90%, `pb-[env(safe-area-inset-bottom)]`, 44px 닫기 버튼(SVG)을 갖춘다. 로딩은 값·산식·차트 자리 스켈레톤으로 높이를 고정한다. 제목은 한국어 메트릭 사전(`metricLabel(slug)`)을 따른다.

### [중요] F-UI-07 스레드 목록 — 미리보기가 구별되지 않고, 제목·시각 표기가 불일치
- 현상:
  - 4개 스레드 중 3개의 미리보기가 "오늘의 훈련 추천 피로 회복이 필요합니다. 가벼운 조깅이나…"로 시작한다. 구별 정보(TSB −10.7 / +2.6 / −28.4)는 모바일에서 2줄 말줄임에 걸려 뒤쪽이 잘린다.
  - 시각은 모두 `2일 전`(9/25, 9/24, 9/24)이라 순서 외 정보가 없다.
  - 제목은 목록에서 `오늘 훈련 조언 · 9/25`, 대화 헤더에서는 `오늘 훈련 조언`이라 서로 다르다(`threadTitles`는 목록에만 적용됨).
  - 데스크톱에서 제목과 시각 사이가 약 1,000px다. 섹션 라벨 "최근 대화"가 별도 테두리 바(`border-b`)로 한 줄을 차지하고, 한글에 `uppercase tracking-wide`가 무의미하게 걸려 있다.
  - 미리보기는 `text-xs text-fg-muted`(12px, 대비 3.75:1 on surface-1)로 AA 미달이다.
- 근거: `coach-desktop.png`, `coach-mobile.png`, API `/coach/threads`, `coach/+page.svelte:75-77,98-111`, `threadAge.ts:9-24`.
- 왜 문제인가: 목록의 역할은 "어느 대화였는지 알아보는 것"인데, 같은 문장이 반복되어 스캔할 수 없다.
- 개선안:
  - 행 구조: 1행 제목(15px medium) + 우측 절대 날짜 `9/25(목)`(7일 이내는 `어제 21:14`). 2행 **요약 핵심 1줄** — 헤딩을 빼고 첫 수치 문장을 우선한다(예: `TSB −10.7 · 회복 6.9km 권고`). 3행 근거 메트릭 미니 칩(최대 2개, 11px 대신 12px).
  - 대화 헤더도 `threadTitles` 결과를 쓴다. 섹션 라벨은 `SectionHeader`(13px semibold fg-secondary)로 통일하고 uppercase를 제거한다.
  - 데스크톱은 목록 폭 `max-w-[720px]`로 제한하거나, 2열(좌 목록 320px / 우 선택 대화) 마스터-디테일로 전환한다(메일·메신저 표준).
  - 대화가 많아지면 날짜 그룹 헤더(`이번 주`, `지난주`)를 쓴다.

### [중요] F-UI-08 컨디션 입력 폼 — 척도 의미 부재, 의미색 충돌, 터치 타깃 미달
- 현상:
  - 질문은 "어떻게 느껴지나요?" 하나뿐이고, 1~10 버튼 줄과 없음/경미/중간/심함 줄에 **어느 줄이 무엇인지 보이는 라벨이 없다**(aria-label에만 있음). 1과 10 중 어느 쪽이 피곤한지 표시가 없다.
  - 선택색: 피로 버튼은 선택 시 `bg-semantic-teal`이다. 피로 10(탈진)도 "좋음" 의미색 teal로 칠해진다. 통증은 선택 시 `bg-semantic-amber`라 "없음"을 골라도 주의색이 된다.
  - 모바일 390px에서 `grid-cols-10 gap-1` 버튼은 약 29px 폭(높이 44)이다. 통증 버튼과 저장 버튼은 `py-1.5`로 약 32px 높이다(`coach-checkin-open-desktop.png` 통증 52×32px).
  - 편집 모드에 취소/닫기가 없다. 아무것도 선택하지 않아도 저장이 활성화된다. 저장 후 요약 "피로 6 · 통증 없음 ✓"의 ✓는 문자다.
  - 데스크톱에서는 피로 버튼 하나가 약 97px 폭으로 과하게 늘어난다. 모바일에서는 폼이 페이지 맨 아래에서 펼쳐져 저장 버튼이 첫 화면 밖으로 나간다(`coach-checkin-open-mobile.png`).
- 근거: `QuickInput.svelte:65-114`, `coach/+page.svelte:210-229`, 스크린샷 2종.
- 왜 문제인가: P6(One Finger Reach)의 입력 품질 문제다. 척도 방향이 불명확하면 입력값이 잘못 기록되고, 그 값이 "Coach 답변에 자동 반영"되므로 오류가 코칭까지 전파된다. 의미색 오용은 P5 위반이다.
- 개선안:
  - 라벨 2줄: `피로도` + 양 끝 앵커 `1 가뿐함 … 10 탈진`(12px fg-secondary). 선택 버튼 아래에 현재 값 해석 1줄(`6 · 다소 피곤`)을 둔다.
  - 선택색은 **중립 강조**(fg-primary 테두리 2px + surface-3)로 한다. 굳이 색을 쓰려면 등급 스케일로 값에 비례시킨다(1~3 teal, 4~6 slate, 7~8 amber, 9~10 red). 통증도 없음=중립, 경미=amber, 중간·심함=red.
  - 모바일은 피로를 `1–5 / 6–10` 2행 5열(각 약 62×44px) 또는 가로 슬라이더(스냅 10단계, 썸 44px)로 둔다. 통증·저장·취소는 높이 44px로 한다.
  - 데스크톱 폼은 `max-w-[480px]`로 제한한다.
  - 모바일에서는 인라인 확장 대신 하단 시트로 연다(저장 버튼이 항상 보이게). 저장 버튼은 값이 1개 이상 선택되어야 활성화한다. 저장 후 요약에는 SVG 체크 + 시각(`오늘 08:12 입력`)을 표시한다.

### [개선] F-UI-09 Coach 홈 위계 — 주 행동(질문하기)이 보조 버튼, 칩 3종이 같은 모양
- 현상: 홈의 주 행동인 새 질문은 가운데 정렬 보조 스타일 버튼 `+ 새 대화 시작`이고, 누르면 3줄 textarea가 목록 아래에 펼쳐진다. 주제 칩(30px 높이, 누르면 입력창 prefill), 대화 내 후속 질문 칩(26px, **누르면 즉시 전송**), 근거 칩(26px, 패널 열림)이 모두 같은 `rounded-full border bg-surface-2` 알약이다. 동작이 셋으로 다른데 모양은 하나다.
- 근거: `coach/+page.svelte:155-182`, `[threadId]/+page.svelte:159-172`, `EvidenceQuote.svelte:30`.
- 왜 문제인가: U4다. 후속 질문 칩은 누르는 즉시 메시지가 전송되는 파괴적이지 않은 동작이지만, 근거 칩과 같은 모양이라 "내용 보기"로 오인하기 쉽다.
- 개선안:
  - 홈 하단에 대화와 동일한 **상시 컴포저**(`무엇이든 물어보세요` 16px, 전송 아이콘)를 두고, 주제 칩은 컴포저 바로 위에 `질문 제안` 가로 스크롤로 배치한다.
  - 칩 문법을 3종으로 고정한다. 근거 칩(데이터: 값 + `›`, 테두리), 질문 제안(말풍선 아이콘 + 텍스트, 배경 surface-3, 테두리 없음), 필터·상태(세그먼트). 후속 질문은 답변 블록 아래 "이어서 묻기" 라벨 아래에 둔다.

### [개선] F-UI-10 로딩·전송 상태 표현
- 현상: 전송 중 표시는 텍스트 "답변 생성 중…" 말풍선뿐이다. 전송 중 textarea는 `disabled opacity-50`으로 흐려져 다음 질문을 미리 쓸 수 없다. 오류는 12px 빨간 가운데 텍스트이고 재시도 버튼이 없다. 스레드에 들어올 때 스크롤 위치가 맨 위에 고정된다(`scrollToBottom`은 전송 후에만 호출). 긴 대화는 최신 메시지가 아닌 첫 메시지부터 보인다.
- 근거: `[threadId]/+page.svelte:56-58,69-89,175-186`.
- 개선안: 타이핑 인디케이터(점 3개 애니메이션, `prefers-reduced-motion` 시 정적), 입력은 계속 가능하게 하고 전송만 잠근다. 실패한 사용자 말풍선에는 빨간 `!` + `다시 보내기` 링크를 단다. 진입 시 `onMount`에서 마지막 메시지로 스크롤하고, 위로 스크롤했을 때 새 답변이 오면 `↓ 새 답변` 플로팅 버튼을 띄운다.

### [개선] F-UI-11 아이콘·셸 일관성
- 현상: `←`(스레드 헤더, 히트 영역 약 16×24px), `✕`, `›`, `☰`(disabled인데 활성처럼 보임), `📊📋`(tofu)가 모두 문자 글리프다. 탭바만 SVG다. 구 스레드 "안녕"의 미리보기는 v2에 없는 "훈련 탭에서 목표를 추가하세요"를 안내한다(문구 잔재).
- 근거: `[threadId]/+page.svelte:113`, `MetricBreakdown.svelte:62`, `+layout.svelte:29-36`, `coach-desktop.png`.
- 개선안: Today F-UI-13의 SVG 아이콘 세트(back/close/chevron/menu/metric/plan)를 공유하고, 모든 아이콘 버튼을 44×44 히트 영역으로 만든다. 규칙 기반 답변 템플릿의 탭 이름을 v2 IA(Coach › 계획)로 바꾼다(데이터 담당과 조율).

## 잘된 점 (유지)
- 근거 칩이 답변 버블 안에 인라인으로 붙고 일부는 실제 계산 시트로 드릴된다. 구조 자체는 P1 방향이 맞다. 드릴 대상이 없는 칩을 가짜 버튼으로 만들지 않은 판단(`EvidenceQuote.svelte:3-4`)도 옳다. 시각 구분만 추가하면 된다.
- 답변 렌더링이 `{@html}` 없이 토큰 파서(`ChatBody.svelte`)로 되어 있어 안전하다. 볼드, 헤딩, 목록을 처리하는 기본 틀이 있다.
- 답변 근거 메트릭에 따라 후속 질문을 바꾸는 `followUps()`와 목표 국면에 따라 주제 칩을 바꾸는 `homeTopics()`는 맥락형 안내의 좋은 씨앗이다.
- 낙관적 사용자 메시지 추가, 입력바 하단 도킹, 화면 전환 170ms·칩 반응 38ms(interact-mobile) 등 기본 반응성은 좋다.
- 컨디션 입력의 피로 버튼 높이 44px, `role=radiogroup`·`aria-pressed` 지정 등 접근성 기초가 들어가 있다.

## 채점 (0~10, 한 줄 근거)
- 비전 부합: 5 — 근거 칩과 컨디션→코칭 반영은 비전 방향이지만, 설계 5-B의 컨텍스트 패널이 없고 근거가 대화 맥락을 가린다.
- 정보 정확성: 3 — 칩 −11 / 본문 −10.7 / 패널 −3.3이 날짜 없이 공존하고, 2일 전 D-58이 현재처럼 보이며, 피로 척도 방향이 표시되지 않는다.
- 시각 품질: 4 — 흰 사용자 말풍선 과강조, 모노 한글 칩, tofu 이모지, 12px·대비 미달 미리보기, 데스크톱 무제한 폭.
- 상호작용 반응성: 6 — 전환·칩 반응은 빠르지만 칩의 절반이 무반응이고, 한글 IME Enter와 iOS 확대 위험이 있다.
- 흐름: 5 — 목록→대화→근거는 이어지지만 근거 시트가 막다른 숫자 하나이고, 진입 시 최신 메시지로 스크롤되지 않는다.
- 혁신성: 4 — 근거 기반 코칭은 차별점이지만 현재 시각적으로는 일반 챗 UI + 칩이며, WHOOP Coach·Runna 수준의 근거 시각화에 못 미친다.

## 최우선 개선 3개
1. **Evidence Sheet(F-UI-01/02/06)**: 칩에 스냅샷 값을 넘기고 시트에서 `답변 당시 값 vs 현재 값`, 기준일, 산식, 14일 추이를 보여 준다. 칩은 대화형/정보형 2종으로 시각 분리하고, sans 글꼴에 숫자만 tabular, SVG 아이콘, 44px 히트 영역으로 만든다. 데스크톱은 대화 옆 컨텍스트 패널, 모바일은 스냅 시트로 연다.
2. **모바일 대화 셸(F-UI-03/04/10)**: 대화 라우트에서 전역 헤더·탭바를 숨기고, safe-area·`interactive-widget` 대응, 16px auto-grow 컴포저, `isComposing` 가드, 진입 시 최신 메시지 스크롤을 적용한다. 공통 `ChatComposer`로 홈과 대화에서 공유한다.
3. **대화 타이포·목록·입력 폼 정리(F-UI-05/07/08)**: 답변을 전폭 문서 블록(15px/1.6)으로, 사용자 말풍선을 surface-3로 바꾼다. 메시지 시각·"당시 기준" 태그, 구별 가능한 목록 요약 줄을 넣는다. 컨디션 폼은 척도 앵커 라벨, 중립 선택색, 44px 타깃, 모바일 시트로 바꾼다.
