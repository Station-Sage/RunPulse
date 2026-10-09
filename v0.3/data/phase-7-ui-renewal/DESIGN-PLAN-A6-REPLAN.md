# DESIGN — A6 REPLAN 시트 상단 고정 표시와 링크 대상

상태: 초안(승인 대기) · 2026-10-09 · 상위: DESIGN-PLAN-ROW-ACTION-COACHING.md §3, ADR-035 부록 "경고 A1~A6" 후속 2건
범위: (1) 행 액션 시트를 열 때 "지금 REPLAN 조건인가" 표시, (2) `[계획 다시 맞추기 ›]` 링크 대상. 새 재계획 엔진은 범위 밖.

## 0. 현재 저장소 조사 결과

| 항목 | 확인 내용 |
|---|---|
| 재계획 전용 라우트/화면 | 없음. `frontend/src/routes/coach/plan*`에 `/coach/plan`, `/new`, `/compare`, `/[id]`, `/[id]/session/[date]`만 있음. `src/api`·`src/services`에 replan/regenerate(플랜) 없음(`regenerate`는 코치 메시지용) |
| 기존 재생성 진입점 | `/coach/plan` 화면의 "남은 N주 로드맵 만들기 →" = `planNewHref(goal)` → `/coach/plan/new?distance_km&race_date&target_time_sec` → `/compare` → `POST /coach/plan` |
| `/new`가 받는 선택 입력 | `recent_weekly_km`, `recent_long_km` 쿼리(`parseReportedLoad`)를 이미 읽고 폼에 채운다 |
| `POST /coach/plan` 동작 | `add_goal`로 **새 goal 행** 생성(기존 goal은 active로 남고, `get_active_goal`은 최신 created_at을 고른다). 대회 주에서 거슬러 이번 주 월요일부터 `save_weekly_plan` → 해당 날짜 `source='planner'` 행 삭제 후 재삽입 |
| 경고 계산 | `plan_advisory.compute(conn, today, delta)`는 읽기 전용, 발급 기록은 `issue()`만 남김. 현재 호출처는 액션 POST의 `_advisories()` 하나 |
| 시트 | `RowActionSheet.svelte`(198줄), 열릴 때 첫 `button, a`에 포커스. 사용처: `plan/[id]`, `session/[date]` (`RowActionButton` 경유) |

## 1. 결정 ① 상태 조회 API

**추천: `GET /api/v1/coach/plan/advisories?date=YYYY-MM-DD` — 전체 반환, 읽기 전용, 발급 기록 없음.**

- 서버: `plan_advisory.compute(conn, date, delta=None)` 그대로. delta가 없으니 A4·A5는 자연히 빠지고 A1/A6/A2/A3만 나온다. `issue()`·`_issued()` 호출 금지(조회만으로 "이번 주 발급됨"이 기록되면 실제 액션 시 토스트 안내가 사라짐).
- `date` 생략 시 서버 오늘. 시트의 `today` prop을 넘긴다.
- 통증 억제: 최근 72시간 안에 accepted pain 조정이 있으면 빈 리스트(§4 "통증일 때 A1~A6 없음", pain_v1 72시간 창과 동일).
- REPLAN 항목에만 링크용 값을 붙인다: `link: {distance_km, race_date, target_time_sec, recent_weekly_km}`. `recent_weekly_km` = 직전 2 ISO 주 실제 km 평균(`week_compliance` 재사용, 0.1 반올림, 데이터 없으면 생략).
- 응답 예: `{"advisories":[{"code":"REPLAN","severity":"info","text":"최근 2주 세션 8개 중 3개를 했어요. …","link":{…}}]}`
- 이유(전체 반환): 계산 비용이 같고, 프론트가 `code==='REPLAN'`만 고정 표시하면 된다. 나머지는 지금 쓰지 않지만 플랜 화면 상단 등 후속 재사용 시 API를 다시 바꿀 필요가 없다. REPLAN만 반환하는 대안은 이름이 좁아져 재사용 때 두 번째 엔드포인트가 생긴다.
- 실패/503/빈 응답: 배너를 그리지 않는다(시트 동작에 영향 없음, 재시도 없음).

## 2. 결정 ② 고정 배너 UI

**추천: 시트 제목 줄 바로 아래, 작업 버튼들 위에 info 띠 하나. 새 컴포넌트 `ReplanBanner.svelte`로 분리.**

배치(390px 기준):
```
┌ 이지 8km · 10-09 ──────────────────────┐
│ ▏최근 2주 세션 8개 중 3개를 했어요.          │  ← info 띠(semantic-blue 계열 옅은 배경, 좌측 3px 선)
│ ▏계획을 지금 흐름에 맞추면 남은 기간을        │
│ ▏더 잘 쓸 수 있어요.                        │
│ ▏계획 다시 맞추기 ›          이번 주 숨기기   │  ← 링크(왼쪽) · 텍스트 버튼(오른쪽, muted)
├────────────────────────────────────────┤
│ [줄이기] [이지로 바꾸기] [쉬기] …            │
```
- 정보 계층: L0 = 사실 한 문장 + 영향 한 문장(서버 `text`), L1 = 링크 한 개. 숫자는 문장 속 1개만. 아이콘·느낌표·빨강/노랑 금지(info는 파랑 계열, 경고색 아님).
- 톤: 서버 문구를 그대로 쓴다(주어=계획, "놓침·실패" 없음). 프론트가 문장을 덧붙이지 않는다.
- 숨김: "이번 주 숨기기" — `localStorage` 키 `rp.replanHidden=<ISO주 월요일>`. 판정 근거가 직전 2주라서 하루 단위로는 거의 안 바뀐다. 하루 숨김은 매일 같은 말을 다시 보게 하고, 영구 닫기는 다음 주 상태 변화를 놓친다. 다음 주에 조건이 계속되면 다시 보인다.
- 통증 선택 시: 시트에서 `reason='pain'`을 고르면 배너를 즉시 숨긴다(통증일 때 계획 압박 문구 금지).
- 토스트 중복 방지: 이 시트에서 배너를 보였다면, 액션 응답 `advisories`에서 REPLAN을 건너뛰고 다음 항목을 토스트에 붙인다(서버 발급 기록은 그대로).
- 높이: 최대 4줄, `max-h-[85vh]` 스크롤 안에 포함(고정 sticky 아님 — 390px에서 작업 버튼을 가리지 않게).
- 접근성
  - `role="note"` + `aria-label="계획 안내"`. `role="alert"`/`aria-live` 쓰지 않음(열 때마다 읽히면 소음).
  - 초기 포커스는 배너 링크가 아니라 첫 작업 버튼 유지 → 기존 `querySelector('button, a')` 순서가 배너 링크를 먼저 잡지 않게 시트 포커스 대상에 `data-autofocus` 지정 필요.
  - 링크 텍스트 단독으로 뜻이 통하게 "계획 다시 맞추기"(›는 `aria-hidden`). 터치 영역 44px 높이.
  - 대비: 본문 `fg-secondary` 이상, 배경 대비 4.5:1.

## 3. 결정 ③ 링크 대상

**추천: 기존 진입점 `/coach/plan/new`를 프리필로 연다. `planNewHref(goal)` + `recent_weekly_km`(직전 2주 실제 평균).**
`/coach/plan/new?distance_km=42.195&race_date=…&target_time_sec=…&recent_weekly_km=23`

이유
- 저장소에 재계획 전용 경로가 없고, 이 흐름이 이미 "남은 N주 로드맵 만들기"로 같은 목표를 이번 주부터 다시 짜는 유일한 길이다.
- `recent_weekly_km`을 실제 흐름(예 22~24km)으로 채우면 시작 볼륨이 계획 ~54km가 아니라 지금 상태에서 출발한다 — "지금 흐름에 맞춘다"는 문구와 결과가 일치한다. 사용자는 `/new` 폼에서 값을 보고 고칠 수 있다(투명성).
- 새 엔진·새 화면 없이 링크 1개 + 쿼리 1개로 끝난다.

알려진 부작용(시스템 설계 확인 필요, 이 문서는 결정하지 않음)
- K1: 같은 목표로 goal 행이 하나 더 생긴다(이전 goal도 active). 목록·이행률 집계에 중복이 보일 수 있다.
- K2: 이번 주 월요일부터 planner 행을 지우고 다시 넣는다 → 이번 주 지난 날짜 계획과 그 행을 가리키는 조정(바로 이 경고의 근거)이 끊길 수 있다.
- 대응 제안: K2가 실제로 기록을 깨면 링크를 켜기 전에 system-architect가 "재생성 시작 주 = 다음 주" 또는 "같은 목표면 goal 재사용" 중 최소 수정안을 정한다. 그 전까지의 대안은 **링크 없이 문구만** + "이번 주 숨기기"(정보는 주되 데이터를 건드리지 않음).

검토한 대안
| 대안 | 판단 |
|---|---|
| `/coach/plan` 랜딩으로 이동 | 한 번 더 탭해야 하고 실제 km 프리필이 빠진다 |
| 코치 대화(`/coach/new`)로 질문 넘기기 | 대화가 계획을 바꾸지 못해 "맞추기" 약속과 어긋남 |
| 문구만(링크 없음) | 가장 안전, K2 미해결 시 기본값 |
| 새 replan 엔드포인트 | 범위 밖 |

목적지 쪽 최소 보완(같은 작업에 포함 권장): `/new`가 `recent_weekly_km`을 프리필로 받았을 때 입력 칸 옆에 "최근 2주 실제 평균" 출처 한 줄 표시.

## 4. 테스트 항목

서버(`tests/test_plan_advisory.py`, `tests/test_api_plan_adjustments.py`)
- [ ] GET advisories: REPLAN 조건(2주 세션 4개 이상·이행 < 50%)에서 REPLAN 포함, 경계(정확히 50%, total=3)에서 미포함
- [ ] GET 호출 후 `plan_adjustments.reasons_json`에 advisory 기록이 생기지 않음 → 이어서 액션 POST하면 REPLAN이 정상 발급
- [ ] 같은 주 이미 발급된 뒤에도 GET은 REPLAN을 계속 반환(상태 표시이므로)
- [ ] 72시간 안 pain 조정이 있으면 빈 리스트
- [ ] `link.recent_weekly_km` = 직전 2주 실제 평균, 활동 없으면 키 생략, goal 없으면 `link` 생략
- [ ] date 형식 오류 400, DB 없음 503

프론트(`frontend/tests/*.test.mjs`, 순수 함수)
- [ ] `replanBannerView(advisories, hiddenWeek, isoWeek, isPain)` → REPLAN 있고 숨김 아님·통증 아님일 때만 표시
- [ ] 링크 생성: `planNewHref` + `recent_weekly_km` 쿼리, `parseReportedLoad`로 되읽혀 같은 값
- [ ] 토스트 선택: 배너 표시 시 REPLAN 건너뛰고 다음 항목

브라우저 스모크(390px, 실제 페이지)
- [ ] 조건 충족 데이터에서 시트 열기 → 배너가 작업 버튼 위, 초기 포커스는 첫 작업 버튼
- [ ] "이번 주 숨기기" → 시트 닫고 다시 열어도 미표시, ISO 주 바뀌면 재표시
- [ ] 통증 선택 → 배너 사라짐
- [ ] 링크 → `/coach/plan/new` 폼에 거리·대회일·목표시간·최근 주간 km가 채워짐
- [ ] advisories API 실패 시 시트 정상 동작

## 5. 구현 순서 체크리스트

1. [ ] system-architect에 K1·K2 확인 요청(링크 활성 여부 결정 근거). 결과 나오기 전엔 링크를 플래그로 숨김
2. [ ] 서버: `GET /coach/plan/advisories` (compute 재사용, pain 72h 억제, REPLAN `link`) + 테스트
3. [ ] 프론트 API 함수 `getPlanAdvisories(date)` + 타입
4. [ ] `rowActionView`에 `replanBannerView`·토스트 항목 선택 순수 함수 + mjs 테스트
5. [ ] `ReplanBanner.svelte`(role=note, 이번 주 숨기기, 링크) → `RowActionSheet` 상단 삽입, `data-autofocus`로 초기 포커스 고정
6. [ ] `RowActionButton` 토스트: 배너 표시 시 REPLAN 제외
7. [ ] `/coach/plan/new`: 프리필 `recent_weekly_km` 출처 한 줄
8. [ ] K2 해소 확인 후 링크 플래그 켜기(미해소면 문구만으로 배포)
9. [ ] 390px 브라우저 스모크, `pytest`, `check_docs.py`
10. [ ] ADR-035 부록 "경고 A1~A6"의 후속 2건 상태 갱신, BACKLOG 반영
