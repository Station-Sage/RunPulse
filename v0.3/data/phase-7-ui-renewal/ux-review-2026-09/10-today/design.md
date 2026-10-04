# Today — 개선 설계서 (data·ui·ux 통합)

**작성일**: 2026-09-27 · **대상**: `/v2/today`, Today에서 여는 드릴다운(D2)·레이스 허브, Today가 부르는 API
**입력**: `10-today/{data,ui,ux}.md`(발견 47건), `00-vision-criteria.md`, `03a-today.md`, `03g-common-patterns.md` §7, 교차 탭 데이터 발견(`21-library-metrics/data.md` F-DATA-01·02·06·07·08·10·12, `20-library-activities/data.md` F-DATA-04, `30-coach-chat/data.md` F-DATA-01, `31-coach-plan/data.md` F-DATA-01, `40-v2-unimplemented/{data,ui}.md` F-DATA-01·02, F-UI-03·04)
**공통 규격**: 이 문서 끝의 **§C 공통 규격(C1~C8)**은 Today가 첫 탭이라 여기서 정의한다. 다른 탭의 design.md는 이 규격을 `10-today/design.md §C3`처럼 참조하고 재정의하지 않는다.

---

## 1. 요약

**설계 목표**
1. 모바일 첫 화면(탭바 제외 780px)에서 "오늘 무엇을 할까 + 근거"를 3초 안에 전달한다. 히어로는 **오늘 세션 상태 기계**(pre/done/rest…)이고, 레이스 허브는 한 줄 요약으로 내린다.
2. 보이는 모든 숫자·칩·행·차트 포인트는 1탭으로 **D2(의미 → 공식·기여 → 원천)**, 2탭으로 D3(활동·날짜·Library)에 닿는다. 빈 시트·가짜 칩을 없애고, 스택은 URL에 두어 뒤로가기 = 한 단계 pop.
3. **숫자를 먼저 바로잡는다.** PMC α·TRIMP 계수를 원문으로 복구해 재계산하고, 결정용 TSB는 하루 동안 고정되는 "아침 폼"으로, 등급은 서버 한 곳에서 내린다. 틀린 숫자를 보기 좋게 만드는 개선은 하지 않는다.
4. 차트·칩·시트·포맷·로딩·출처 배지를 공통 규격(§C)으로 고정한다.

**범위**: Today 본문 전체, 드릴 패널, 레이스 허브 상세(`/v2/today/race`), Today가 쓰는 API(`/today`, `/today/narrative`, `/today/race-hub`, `/library/metrics/:slug`, `/coach/plan/active`). 셸(사이드바·☰·동기화 필)은 `40-v2-unimplemented/ui.md` §2.1 설계를 따르고, Today는 그 as-of 계약만 사용한다.

**평가 간 상충과 판단**

| 쟁점 | 의견 | 채택 · 이유 |
|---|---|---|
| 첫 화면 순서 | UI: 권고+링+세션 → 레이스 1줄 / UX: 세션 → 입력 → 링 → 허브 1줄 | **히어로 → 컨디션 1줄 → 상태 게이지 → 레이스 1줄.** 둘 다 "행동 먼저"다. 입력은 권고의 입력값이라 게이지보다 위(03a 2026-09-24 갱신과 일치) |
| D2 형태 | UI: 모바일 하단 시트 50/90% / UX·03g: 모바일 풀스크린 | **데스크톱 ≥1024 우측 420px 밀어내기, 모바일 풀스크린.** 3단 스택·브레드크럼은 반높이 시트에서 읽기 어렵다 |
| 허브 확장 | UI: 전용 화면 / UX: 예측 D2 시트 | **역할 분리.** 레이스 1줄 → `/v2/today/race`, 예측 숫자 → D2. 허브 내용은 420px에 들어가지 않고, 숫자 설명은 D2 문법으로 통일 |
| 테이퍼 차트 | UI: 제거 / UX: 칩 → 시나리오 시트 | **88px 차트 제거, 칩 → D2 `x.taper`**(폼 차트 미래 구간 재사용) |
| 권고 입력 | UX: 완료 상태 기계 / DATA: 게이트+계획+체크인, 아침 TSB | **결합.** 상태 기계가 대상 날짜를, 게이트가 판정을 정한다(축이 다름) |
| PMC α | Today DATA: `1/N` 또는 `1−e^(−1/N)` / Library DATA: `1−e^(−1/τ)` | **원문 `1/τ` 기본, DECISIONS에서 확정(판단 필요).** 원문(`v0.2/.ai/metrics.md:176`)이 `/42`, `/7`이다 |

---

## 2. 정보 구조·배치

### 2.1 블록 순서(모든 폭 공통 우선순위)

| # | 블록 | 관여 층 |
|---|---|---|
| B1 | **Today Hero**: 상태 헤드라인 + 세션 칩 + 근거 칩 2~3 | L0 |
| B2 | 컨디션 입력 1줄(QuickInput compact) | L0 |
| B3 | 상태: 훈련 준비도·부상 위험·폼(각 델타 vs 어제) | L1 |
| B4 | 레이스 1줄 `D-56 · 예측 3:40 (3:26–4:03) · 목표 3:19 ›` | L1 |
| B5 | 이번 주: 거리·핵심 세션 이행 + 7칸 요일 스트립 | L1 |
| B6 | 최근 활동 3행(링크) + `활동 전체 →` | L1 |
| B7 | 흐름: 폼 차트(ChartScrub) + 월간 이야기 요약 | L2 |
| B8 | 마일스톤(거리 돌파·PB·레이스만) | L2 |
| B9 | 푸터: `Library에서 전체 탐색 →` | L3 |

as-of와 동기화 상태는 셸 헤더의 `SyncStatusPill`(40 ui §2.1)이 맡는다. Today 본문에는 B3 헤더의 `아침 기준 · 9월 27일 (일)` 한 줄만 둔다.

### 2.2 데스크톱 1280 — 첫 화면(pre 상태)

```
사이드바 208 │ 헤더: ☰ Today                          ● 9월 27일 · 3분 전 동기화
             │ 좌열(행동) 560                      │ 우열(추세) 440
             │ B1 오늘 · 계획대로                  │ B6 최근 활동
             │   이지런 4.6km 6:21–6:45/km · Z2    │   오늘 이지 9.3km 55:18   G ›
             │   [세션 상세 ›]                     │   9/26 이지 7.1km         G ›
             │   [게이트 5/5 ›][폼 −9 ›][수면 52 ›]│   활동 전체 →
             │   Coach에게 묻기 →                  │ B7 폼 차트  부하 | 폼  (C1)
             │ B2 오늘 컨디션 1탭 →                │   CTL 72.6 · ATL 81.4 · TSB −9
             │ B3 아침 기준 · 9월 27일   RunPulse 계산│   100┤  ╱‾╲_╱‾      ┊
             │   ◔60↑1   ◐33↓3   ─◆─ −9↑5          │   +15┤▒▒ 최적 ▒▒▒▒▒┊▒
             │   준비도   부상 위험  폼             │   −30┤ 7월 8월 9월 오늘 11월
             │ B4 D-56 · 예측 3:40 (3:26–4:03)     │   ━체력 ┄피로 ▆폼 ┅계획대로
             │    목표 3:19 · 21분 차이 ▓▓▓░░ ›    │ 9월 이야기 · 러닝 171.0km [전체 ›]
             │ B5 이번 주 34.7/70.6km · 핵심 0/2   │ B8 마일스톤 9/20 누적 3,800km ›
             │    월 화 수 목 금 토 일 ○○○●◐⟳◉     │
```
수치는 설계 예시다. 재계산(S0) 뒤 값은 달라진다.

### 2.3 모바일 390 — 첫 뷰포트(탭바 제외 780px)

```
☰ RunPulse                ● 9/27 · 3분 전      48
B1 오늘 · 계획대로                              ≈260  헤드라인 20px semibold
   이지런 4.6km · 6:21–6:45/km · Z2 · 약 30분
   [세션 상세 ›]
   [게이트 5/5 ›] [폼 −9 ›] [수면 52 평소 −14 ›]
B2 오늘 컨디션 1탭 →                        ✕   48
B3 아침 기준 · 9월 27일 (일)                    ≈150  게이지 56px
   ◔60↑1  준비도 보통 · ◐33↓3 부상 위험 낮음 · ─◆─ −9↑5 폼
B4 D-56 · 예측 3:40 · 목표 3:19 · 21분 차이  ›   56
B5 이번 주 34.7/70.6km · 핵심 0/2 ○○○●◐⟳◉   ›   ≈64 (경계 약 700px)
 ↓ B6 최근 활동 → B7 폼 차트·월간 → B8 → B9
```
현재 모바일에서 다음 세션은 약 4,500px 위치에 있다. 이 배치에서는 약 100px 위치다.

### 2.4 히어로 상태 기계(B1)

| 상태 | 조건(서버 판정 `briefing.state`) | 헤드라인 | 보조 |
|---|---|---|---|
| `pre` | 오늘 계획 세션 있음, 미완료 | `오늘 · {조정}` + 세션 이름·거리·페이스 범위·존 | [세션 상세 ›], 조정 시 `⚠ 수면 52·HRV −8% → 템포를 이지로 [수락][원래대로]`(P7) |
| `done` | 오늘 활동이 계획에 매칭됨(`completed=1`) | `오늘 완료 ✓ 9.3km · {계획 대비 라벨}` | 활동 행 링크, 해석 1줄, **내일** 세션 예고 칩. 권고 판정 입력은 "오늘 반영 후 예상 내일 아침 폼" |
| `extra` | 계획 없는 날에 활동 있음 | `오늘 9.3km 달렸어요` | 내일 세션 예고 |
| `rest` | 계획상 휴식 | `오늘은 휴식` | 회복 행동 1개(예: 수면 목표) |
| `no_plan` | 활성 계획 없음 | 게이트 기반 권고 1문장 | [계획 만들기 ›](프리필 `/v2/coach/plan/new`) |
| `race_week`·`race_day` | D−7 이내, D−0 | 레이스 주간 문장 | 레이스 페이스·기온 예측 |
| `stale` | 셸 동기화 상태가 amber/red | 위 상태 + 한정 문구 `Strava 미수신 3일 — 부하가 낮게 잡힐 수 있어요 ›` | 40 F-DATA-02 |

`done` 상태 B1(모바일, 오늘 9/27 실제 상황):
```
오늘 완료 ✓ 9.3km · 55:18                       ›  → /v2/library/17414
쉬운 날치고 길었어요 — 내일은 짧게
내일: 이지런 4.6km · 6:21–6:45/km        [세션 상세 ›]
[게이트 5/5 ›] [내일 아침 폼 예상 ›] [수면 52 ›]
```

`done`의 비율: 현재 매칭 92.3%는 대체된 롱런 22.4km가 아니라 Garmin 일정(거리 null) 기준이다. 31의 날짜별 유효 계획 정의가 들어오기 전에는 비율 없이 `오늘 완료 ✓ 9.3km`만 쓴다.

### 2.6 레이스 허브 `/v2/today/race` (L1, B4에서 진입)

위에서 아래로: ① 예측 요약 `3:40 (3:26–4:03) · 신뢰도 낮음` + **목표 실현성** `필요 향상 9.7%/8주 · 90일 추세 −7분 · 도전적` + 대안 목표 2개(예측 중앙·범위 하한)와 목표별 레이스 페이스 + 실제 직전 마라톤 `2025-10 3:42:13` 참조 줄(F-DATA-08) ② 예측 추이(§5) ③ **예측 분해** `대회·품질세트 기반 3:30 · 주간 볼륨 기반 3:51 → 결합 3:40`, 볼륨 입력(8주 주평균 43.1km, 28km+ 롱런 0회)과 `주 +10km 시 약 −n분` 민감도(F-DATA-07) ④ 3경로 비교(Garmin은 `기기 원값`, RunPulse 행만 `15℃ 기준`, F-DATA-10) + `레이스 당일 예상 기온 → 환산 예측` ⑤ 레이스 아침 폼(계획 기반 투영, `TSB +n · 체력 −n%`) ⑥ `예측에 쓰는 대회 8/13 · 수정 ›`. 근거 문장은 입력에서 자동 생성한다(`5월 10K 44:13(20주 전) 60% · 품질 세트 20% · 심박-속도 20%`, F-DATA-14). 범위 라벨은 보정 전까지 `모델 범위`로 쓴다. 데스크톱은 2열(①②③ | ④⑤⑥)이다.

### 2.5 D2 열림

데스크톱은 본문 grid가 `1fr | 420px`로 바뀌고 본문은 1열로 재흐름한다(오버레이·스크림 없음). 패널 헤더는 `← 훈련 준비도 · UTRS › 폼 · ✕`, 본문은 §C3.2의 ①의미 ②공식·기여 ③원천 ④푸터다. 모바일은 풀스크린 슬라이드업(200ms)이고 헤더를 고정한다.

---

## 3. 클릭별 동작 명세

URL 표기는 §C3.3(`?drill=` 토큰 스택). "Today 복원" = 스크롤·펼침·D2 스택 복원.

| 요소 | 제스처 | 결과 | 뒤로가기 | URL 상태 |
|---|---|---|---|---|
| 히어로 세션(pre) | 탭 | `/v2/coach/plan/{id}/session/{date}` | Today 복원 | 경로 |
| 조정 배지 [수락]/[원래대로] | 탭 | 조정 저장, 헤드라인 즉시 갱신, 토스트 [되돌리기] | — | 없음 |
| DrillChip(메트릭) | 탭 | D2 열기 | D2 닫힘 | `?drill=m.tsb` |
| 칩 `42km 목표 D-56` | 탭 | `/v2/today/race` | Today 복원 | 경로 |
| 칩 `레이스 아침 폼` | 탭 | D2 `x.taper`(시나리오 3종·가정 문구) | 닫힘 | `?drill=x.taper` |
| 칩 `이번 달 171km` | 탭 | `/v2/library/activities?from=2026-09-01&to=2026-09-30&type=running` | Today 복원 | 경로 |
| 칩 `수면 52` | 탭 | D2 `m.sleep_score`(원천 → `/v2/library/wellness?date=`) | 닫힘 | `?drill=m.sleep_score` |
| `Coach에게 묻기 →` | 탭 | 새 스레드 + 권고·근거 맥락 첨부 + 추천 질문 3개(30 설계 계약) | Today 복원 | `/v2/coach/{thread}?from=today` |
| B2 컨디션 1줄 | 탭 | 인라인 펼침. 피로 숫자 탭 = 즉시 저장, 통증·메모는 `+ 더하기` | — | 없음 |
| B2 `✕ 나중에` | 탭 | 접기(오늘은 다시 올리지 않음) | — | 없음 |
| B3 게이지 | 탭 / Enter | D2 `m.utrs`·`m.cirs`·`m.tsb` | 닫힘 | `?drill=m.utrs` |
| D2 구성요소 행 `›` | 탭 | 스택 push | 1단 pop | `?drill=m.utrs,m.tsb` |
| D2 `←` / `✕`·Esc | 탭 / 키 | 1단 pop / 전체 닫기, 포커스는 원 트리거로 | — | 토큰 제거 |
| D2 원천 행 · `추세·과거 보기 →` | 탭 | `/v2/library/{id}?from=today` · `/v2/library/metrics/{slug}?date=&from=today` (D3) | Today 복원 | 경로 |
| B4 레이스 1줄 | 탭 | `/v2/today/race` | Today 복원 | 경로 |
| B5 요약 / 요일 칸 | 탭 | `/v2/coach/plan/{id}` / `…/session/{date}` | Today 복원 | 경로 |
| B6 활동 행(전체, ≥48px) | 호버 배경 / 탭 | `/v2/library/{id}?from=today` | Today 복원 | 경로 |
| B7 폼 차트 | 호버 / 클릭·탭 | 미리보기 / 날짜 고정(§C1), 판독줄 `그날 보기 ›` | × 또는 밖 탭으로 해제 | `?pin=`(replaceState) |
| B7 `그날 보기 ›` | 탭 | D2 `m.tsb@2026-09-12`(원천 = 그날 ±3일 활동) | 닫힘 | `?drill=m.tsb@…` |
| B7 시나리오 토글 | 탭 | 계획대로 / 유지 / 테이퍼 | — | `?scn=`(replaceState) |
| 월간 이야기 `전체 ›` | 탭 | D2 `x.month@2026-09`(40의 Story 라우트가 생기면 그 경로) | 닫힘 | `?drill=x.month@2026-09` |
| B8 마일스톤 행 | 탭 | `/v2/library/{activity_id}`(누적 돌파는 돌파 활동) | Today 복원 | 경로 |
| 허브 예측 숫자 | 탭 | D2 `m.race_pred_marathon_sec` | 닫힘 | `?drill=…` |
| 허브 `예측에 쓰는 대회 8/13 · 수정 ›` | 탭 | `/v2/today/race/races`(명시적 저장·실패 표시·예측 변화 토스트·되돌리기) | 허브 | 경로 |

---

## 4. 지표 표기·설명 규격 (Today 적용)

포맷·배지·칩·색의 공통 규칙은 §C4·§C6·§C2·§C7이다. 아래는 Today에만 해당하는 결정이다.

| 지표 | 표시 이름(약어는 작게) | 값 포맷 | 기준 시점 | 좋은 방향·밴드 출처 |
|---|---|---|---|---|
| UTRS | 훈련 준비도 `UTRS` | 정수 `60` + 델타 `↑1` | 아침 스냅샷(수면 종료 기준) | 높을수록 좋음, registry `utrs.bands` |
| CIRS | 부상 위험 `CIRS` | 정수 `33` | 아침 스냅샷 | 낮을수록 좋음, registry `cirs.bands` |
| TSB | 폼 `TSB` | 부호 정수 `−9`(분해 안에서는 소수 1자리) | **아침 폼 = 전날 종료 CTL−ATL** | 국면 의존 밴드(아래), 서버 status |
| CTL/ATL | 체력 `CTL` / 피로 `ATL` | 소수 1자리 | 차트: 일 종료값, 오늘 점은 "잠정" | 단위는 정의 블록에 `TRIMP 기반 AU` |
| 램프 | 체력 증가 `/주` | 부호 소수 1자리 `+4.2/주` | `CTL_t − CTL_{t−7}` | 안전 3~8/주(관행) |
| 마라톤 예측 | 예측 | 신뢰도 <0.5면 **분 단위 + 범위** `3:40 (3:26–4:03)`, ≥0.5면 `3:40:23` | 일 1회 | 낮을수록 좋음 |
| 목표 격차 | `21분 차이` | 분 단위, 색 없이 진행 게이지로 | — | — |
| 이행 | `34.7/70.6km (49%) · 핵심 0/2` | km 1자리, % 정수 | 주(월~일) | 백엔드 `week_compliance` |

**TSB 밴드(재계산 후 기준, registry 단일 정의)**: `< −30 과부하(red)` · `−30~−10 생산적 부하(teal)` · `−10~+5 유지(neutral)` · `+5~+25 신선(green; D−21 이내면 "레이스 최적")` · `> +25 휴식 과다(amber)`. 테이퍼·레이스 주간 국면에서는 서버가 `−30~−10`을 `amber 피로 누적`으로 판정한다. 프론트는 `status`와 `label`만 렌더한다(`status.ts`·`metricMeaning.ts`·`raceHub.formBand` 제거).

**설명(U5)**: 별도 ⓘ 없이 게이지 탭 → D2 ① 블록(무엇 / 밴드 바·내 위치 / 7일 평균·어제 대비 해석 / 그래서, §C3.2)이 맡는다. 예: UTRS ① `오늘 훈련을 받아들일 준비 정도 · 0–100, 70↑ 준비됨 · 7일 평균 64보다 4 낮음 — 수면이 가장 크게 끌어내림 · 계획대로 가되 강도는 Z2 상한`.

**게이지 형태(F-UI-12)**: UTRS = 채움 링(중립은 회색이 아닌 등급 중간색), CIRS = 저·중·고 3구간 트랙 + 마커, TSB = 0 중심 양방향 반원(음수 왼쪽, 밴드 틱). 아래에 어제 대비 델타. 출처 배지는 B3 헤더에 `RunPulse 계산` 1회(§C6).

**권고 문장 규칙(F-DATA-06)**: 형식은 `{계획대로|하향 조정|상향 가능}: {세션} · {결정 근거 신호 1~2개}`이다. 입력은 CRS 게이트 5종(ACWR·HRV·BB·TSB·CIRS) + 체크인(피로 ≥7 또는 통증 ≥중간이면 1순위) + 계획 세션이다. Today·Coach·Plan 조정은 **같은 판정 함수** `readiness_decision(date)`를 쓴다(30 F-DATA-01의 "Today는 핵심 세션, Coach는 항상 휴식" 모순 제거). 근거 칩은 판정에 영향을 준 신호 2~3개만 쓴다. 투영값(레이스 아침 폼)은 조건부 문장으로만 쓴다(`계획대로 가면 약 +18 예상`).

**용어(F-DATA-15)**: 화면 전체에서 `체력(CTL)`, `피로(ATL)`, `폼(TSB)`로 통일한다. 사전은 `src/utils/metric_labels.py`(`name_ko`+선택 `abbr`, API 필드명 동일)에 둔다. 분해 라벨의 `(parent: utrs)` 같은 내부 표기는 API 단계에서 제거한다.

---

## 5. 차트 규격 (Today 적용)

공통 동작·축·툴팁은 §C1 ChartScrub이다. Today 차트별 설정만 적는다.

| 차트 | 위치 | 설정 |
|---|---|---|
| 폼 차트 | B7 | 패널 `부하` 140px / `폼` 100px, 간격 8px. y: 부하 nice ticks, 폼 −30/−15/0/+15/+30. 오늘 라벨은 세로선에 붙임(`left:{todayPct}%`). 오늘 점 = 잠정(속 빈 원). 미래는 `계획대로` 1개만 점선, 나머지는 토글. 최적 밴드 라벨은 오른쪽 거터. 체력 `--series-1` 2.5px, 피로 `--series-2` 1.25px·70%, 폼 선 fg-primary 1.5px(의미는 밴드 배경으로만, §C7) |
| 예측 추이(허브 페이지·D2) | `/v2/today/race`, D2 | `invert` 켬(빨라짐 = 위), 축 캡션 `빠름 ↑`. y 눈금 5분 단위(3:35/3:40/3:45/3:50). 목표 3:19 수평 점선 라벨, 범위 밴드(fill .12), 오른쪽 끝 현재값 라벨 + `90일 −7분` 배지. 높이 ≥160px. 기준 대회 교체 시점 세로 마커(21 F-DATA-06) |
| 월간 체력 스파크라인 | 월간 이야기 D2 | 높이 48, 시작·끝·피크 값 라벨(`68.3 → 80.0 피크 → 72.6`), 스크럽 가능, 색 `--series-1`(미정의 `--color-accent` 제거) |
| 레이스 아침 폼 | D2 `x.taper` | 폼 차트 미래 구간을 확대 재사용(오늘~레이스일). 시나리오 3개 비교표(레이스 아침 폼 · 체력 변화율 `−6%`) + 가정 문구 |

**빈 데이터**: 폼 차트는 부하 이력이 28일 미만이면 차트 대신 `체력 계산에 28일 기록이 필요해요 (지금 12일) · 활동 가져오기 ›`를 보여 준다. 예측 추이는 점 2개 미만이면 숨기고 현재값만 둔다.

---

## 6. 로딩·빈·오류 상태

공통 문법은 §C5. `+page.ts`는 `/today`(95ms)만 await하고 나머지(narrative 413ms 등)는 streamed promise로 넘긴다. trend 3회는 `/today/form-chart` 1회로 합친다(§7.3). 재방문은 SWR 캐시로 즉시 그린다.

| 블록 | 스켈레톤(높이 예약) | 빈 상태 · 행동 | 오류 |
|---|---|---|---|
| B1 | 헤드라인 2줄 + 칩 3개(260px) | `no_plan`: `목표 레이스를 정하면 매일 세션을 제안해요 [계획 만들기]` | `오늘 권고를 불러오지 못했어요 · [다시 시도]` |
| B2 | 1줄 | — | 저장 실패: 폼 유지 + `저장 실패 · 다시 시도` |
| B3 | 원 3개 | 웰니스 없음: `수면·HRV 데이터 수집 중 · 기기 연결 확인 ›` | 블록 재시도 |
| B4 | 1줄 | 목표 없음: `목표 레이스 등록 ›` | `예측을 불러오지 못했어요 · 다시 시도`(숨기지 않음) |
| B5 | 7칸 | 계획 없음: 숨김(B1이 안내) | 블록 재시도 |
| B6 | 3행 | `아직 활동이 없어요 · 소스 연결 ›` | 블록 재시도 |
| B7 | 차트 영역(240px) | 부하 이력 <28일: `체력 계산에 28일 기록이 필요해요 (지금 12일)` | 블록 재시도 |
| 페이지 | 셸 + B1 | **데이터 없음**: 온보딩 `소스 연결 → 첫 동기화 → 목표 레이스` | **조회 실패**: `불러오지 못했어요 ({message}) · [다시 시도]`. 모든 예외를 "데이터 없음"으로 처리하지 않는다 |

D2: 트리거 pointerdown에서 분해를 선요청하고, 열리는 즉시 ①~④ 골격 스켈레톤을 보인다.

---

## 7. 변경 컴포넌트·API

### 7.1 프론트엔드 (`frontend/src/`)

| 파일 | 변경 |
|---|---|
| `routes/today/+page.ts` | `/today`만 await, 나머지 streamed. `empty`/`error` 구분 |
| `routes/today/+page.svelte` | B1~B9 재배치(`order-*` 제거), 활동 행 `<a>`, `DrillHost` 사용, `snapshot` 복원, 약속 문구 정정 |
| 신규 `TodayHero.svelte` (← `RecommendationCard`) | 상태 기계, 조정 배지, 세션 칩, 기존 스켈레톤 재사용 |
| 신규 `ReadinessGauge.svelte` (← `ScoreRing`) | ring / risk / bipolar 3형, 델타, 서버 status |
| 신규 `RaceSummaryLine.svelte`, `routes/today/race/+page.svelte`, `routes/today/race/races/+page.svelte` | 허브 분리. `RaceHub`·`PredictionCompare`·`PredictionBasis`·`RaceConfirmList`를 허브로 이동, 테이퍼 88px 차트 제거, 존은 신규 `ZoneBar.svelte`, 실험 알고리즘은 설정 토글 뒤, `RaceConfirmList`에 catch·되돌리기 |
| 신규 `WeekStrip.svelte` (← `NextSessionCard` 점) | 요일 7칸, §C7 상태 기호, 칸 링크 |
| `QuickInput.svelte` | 1탭 저장, `✕ 나중에`, 저장 후 `invalidate('api:today')` |
| `FormChart`·`TrendChart`·`Sparkline` + `formChart.ts`·`trendChart.ts` | `ChartScrub` 코어로 통합(§C1) |
| 신규 `DrillPanel.svelte`·`BreakdownView.svelte` (← `MetricBreakdown`) | §C3 |
| 신규 `DrillChip.svelte`·`InfoTag.svelte` (← `EvidenceQuote`) | §C2 |
| `MonthNarrative.svelte` | `--color-accent` 제거, 러닝 거리만 |
| `lib/format.ts` | §C4 함수(`formatSigned`, `formatPrediction`, `formatDateKo`, `formatByUnit`) |
| `lib/status.ts`·`metricMeaning.ts`·`raceHub.ts formBand` | 삭제(서버 status 렌더) |
| `routes/layout.css`·`+layout.svelte` | §C8 토큰·폰트, `$navigating` 진행바. 셸은 40 §2.1 |

### 7.2 백엔드·데이터 (교차 탭 문제 중 Today 표시에 영향을 주는 것 포함)

| 항목 | 변경 | 연관 |
|---|---|---|
| `src/metrics/pmc.py` | α = 원문 `1/τ`(DECISIONS 확정), 전일 값 이어받는 연속 재귀(창 절단 제거), `pmc_v2`로 전 기간 재계산. ACWR은 EWMA `2/(N+1)` 유지 | T·DATA-01, 21·DATA-01, 20·DATA-04 |
| `src/metrics/trimp.py` | 남 `0.64·e^(1.92x)`, 여 `0.86·e^(1.67x)`, 성별은 프로필 | T·DATA-02 |
| 아침 폼 | `tsb_morning`(D−1 종료)을 판정·게이지·UTRS 입력으로. 당일 `frac` 감쇠값은 `tsb_live`로 차트 잠정 점에만 | T·DATA-03, 21·DATA-07 |
| 등급 SSOT | `bands.py`(등급)·`metric_display.py`(`higher_is_better`·`unit`·`decimal_places`)·`metric_labels.py`(`name_ko`·`abbr`). API 값마다 `status`·`status_label`·`unit`. `check_data_consistency.py`에 "프론트 등급표 존재 시 실패" | T·DATA-04·15, 21·DATA-02·10·13 |
| `readiness_decision()` | `today_service`·`race_hub_service`·`chat_engine_rules`·계획 조정이 공용 사용, 등급 키 enum | T·DATA-06, 30·DATA-01 |
| UTRS v2 / CIRS v2 | HRV·RHR 개인 60일 기준선, BB 제외 또는 대체 입력 / ACWR 비대칭 위험, 피로 항 ATL/CTL, 연속일은 러닝만 | T·DATA-11·12, 21·DATA-07·08 |
| 주간 이행 | `week_compliance`(날짜별 유효 계획 기준, 31 설계와 한 함수) | T·DATA-05, 31·DATA-01 |
| 월간·마일스톤 | 러닝(트레일 포함)만 집계, 추세 문구는 주별 기울기+피크, `metric_recompute` 제외, 누적 돌파에 `activity_id` | T·DATA-13, T·UX-13 |
| 레이스 투영 | `planned_workouts` 일별 거리 × 개인 TRIMP/km. 계획이 없을 때만 균일 부하(라벨 표기). `ctl_change_pct` 추가 | T·DATA-09 |
| 예측 분해 | `race_pred_marathon_sec` 분해에 json_value 구조화(모델·신호·가중·원천 활동·기온별), 범위 `range_kind` | T·DATA-07·14, 21·DATA-06 |
| 동기화 원장 | 40의 `SyncState` 사용, 소스 결손 시 `briefing.caveats[]` | 40·DATA-01·02 |
| Intervals CTL 인제스트 복구 | TSB D2 ④에 `Intervals 폼 −6 (척도 다름)` 비교 줄(P3). 복구 전에는 숨김 | 21·DATA-12 |

### 7.3 API 계약

**`GET /api/v1/today`** 확장(기존 필드 유지, 추가분만):
```
as_of          {basis:"morning", date, computed_at(+09:00)}
briefing       {state: pre|done|extra|rest|no_plan|race_week|race_day,
                target_date, verdict: as_planned|down|up, headline,
                today_result{activity_id, distance_m, outcome_label, plan_ratio_pct|null},
                session{id, date, title, distance_m, pace_min, pace_max, zone},
                adjustment{reason, from, to}|null,
                evidence[{kind: drill|route|info, label, metric?, value?, status?, status_label?, target?|href?}],
                caveats[{code:"source_missing", provider, days}]}
readiness      {utrs|cirs|tsb: {value, delta_1d, status, status_label, bands?, provider, version}
                 + tsb.live(당일 잠정)}
week_compliance{done_km, plan_km, key_done, key_total,
                days[{date, state: done|partial|missed|rest|substituted|upcoming, session_id, activity_id}]}
race_summary   {days_left, pred_sec, low_sec, high_sec, range_kind: model_envelope|calibrated80, confidence, target_sec}
recent_activities[] + provider, plan_label
```

**`GET /api/v1/library/metrics/{slug}?scope_type=daily&scope_id=YYYY-MM-DD&explain=1`** 분해 v2(§C3 렌더 계약):
```
slug, name_ko, abbr, scope{type, id, basis}, value, display, unit, status, status_label, higher_is_better
meaning  {what, bands[{max, status, label}], baseline{avg_7d, delta_1d}, so_what}
formula  {text:"폼 = 체력(CTL) − 피로(ATL)", version, computed_at,
          terms[{slug, label, raw?, normalized?, weight?, contribution?, loss?, sign?, drill?}]}
sources  [{type: activity|wellness_day, id|date, label, value, unit, effect:"피로 +10.6"}]
provider {kind, version, computed_at};  compare[{provider, value, note, as_of}];  links{trend}
```
`terms`와 `sources`가 모두 빈 응답은 계약 위반이다(API 테스트). TSB·CTL·ATL은 공식 항을, UTRS는 원시 입력·가중치·손실을 채운다.

**`GET /api/v1/today/form-chart?period=3m`** 신규(trend 3회 통합): `{days[{date, ctl, atl, tsb, provisional}], future{plan[], keep[], taper[]}, bands[], race_date}`.

---

## 8. 수용 기준

**데이터**
- [ ] `pmc.py` 고정 테스트(부하 0일 CTL 감소 = CTL/42, ATL = ATL/7; 원문 α 채택 시). 재계산 전후 비교표(90일 TSB 범위, −30 미만 일수)가 DECISIONS에 있다.
- [ ] TRIMP 고정 테스트: x=0.5 → 0.836/분, x=0.9 → 3.243/분(남).
- [ ] 같은 날 06:00·22:00 조회에서 게이지·칩·D2의 TSB가 같다. 차트 오늘 점만 `provisional`.
- [ ] 같은 메트릭·같은 날의 `status_label`이 Today·Library·Coach에서 같다. 프론트 등급 경계 상수 0개(grep).
- [ ] 이번 주 `done_km/plan_km`가 31 이행 API와 같고, 대체된 롱런은 `●`로 나오지 않는다.
- [ ] 월간 거리에 러닝만 포함(수영 추가 시 불변). 마일스톤에 `metric_recompute` 0건.

**상호작용·흐름**
- [ ] 누를 것처럼 보이는 요소 전수의 `NO_VISIBLE_REACTION` 0건(`raw/interact.mjs` 재측정). 목적지 없는 근거는 `InfoTag`로만 렌더.
- [ ] 모든 D2에 ①·④ 블록. 빈 시트 0건.
- [ ] D2 2단에서 뒤로가기 1회 = 1단 pop, 2회 = 닫힘. `?drill=m.utrs,m.tsb` 새로고침 시 스택 복원.
- [ ] 모바일 폼 차트: 탭 후 손을 떼도 판독 유지(Playwright touch). y 눈금 ≥3개, 모두 nice 값.
- [ ] 예측 추이: 기록이 빨라지면 선이 올라간다(`invert` 단위 테스트).
- [ ] 활동 상세 → 뒤로가기 시 Today 스크롤 오차 ≤ 50px.
- [ ] 컨디션 2탭 저장, 저장 후 ≤ 1s 안에 권고 근거에 입력 칩.

**성능·시각**
- [ ] 탭 하이라이트 ≤ 100ms. 진행바는 150ms 지연 후. B1 헤드라인 ≤ 1.0s(현재 1,252ms), 스켈레톤 ≤ 300ms, 재방문 캐시 표시 ≤ 300ms.
- [ ] D2 열림 피드백 ≤ 100ms, 내용 ≤ 400ms, CLS ≤ 0.05.
- [ ] 12px 미만 텍스트 0개(축 11px 예외), 보조 텍스트 대비 ≥ 4.5:1, 터치 타깃 ≥ 44px, 미정의 CSS 변수 0건.
- [ ] `document.fonts`에 Inter·JetBrains Mono 로드, 한글에 mono 미적용.
- [ ] 모바일 첫 뷰포트(780px) 안에 B1~B4.

---

## 9. 구현 순서

| 단계 | 묶음 | 의존 | 규모 |
|---|---|---|---|
| **S0 데이터 기반** | PMC α·연속 재귀·재계산, TRIMP 계수, 아침 폼 분리, 등급 SSOT(registry + API status), 월간 러닝 필터, 마일스톤 필터 | DECISIONS(α 확정) | L |
| **S1 공통 규격** | §C4 포맷, §C8 토큰·폰트·아이콘, §C2 칩, §C6 배지, §C5 스켈레톤·진행바 | — | M |
| **S2 드릴다운** | 분해 v2 API(`explain=1`, TSB/CTL/ATL 공식 terms, 원천 활동), `DrillPanel` + URL 스택 + 패널 레이아웃 | S0(값), S1 | L |
| **S3 Today IA** | Hero 상태 기계(`briefing.state`, `readiness_decision` 공용화), 게이지 3형, 레이스 1줄, 이번 주 스트립(`week_compliance`, 31과 공동), 활동 행 링크, 스트리밍 load, 오류/빈 분리 | S1, S2, 31 이행 정의 | L |
| **S4 차트** | `ChartScrub` 코어, FormChart·TrendChart 이관, `/today/form-chart`, 예측 추이 invert | S1 | M |
| **S5 레이스 허브** | `/v2/today/race`, 예측 분해·실현성·기온 환산, 계획 기반 투영, 대회 편집 화면 | S2, S4 | L |
| **S6 맥락 연결** | Coach 프리필(30 설계), Library 딥링크(`?date=&from=`), snapshot 복원, 셸 SyncStatusPill 연동(40) | 30·40·21 설계 | M |
| **S7 신호 품질** | UTRS v2·CIRS v2, 델타·개인 기준선 브리핑, Intervals CTL 비교 | S0, 21 F-DATA-12 | M |

S0이 먼저다. S1·S4는 병행 가능하다. S0 배포 시 Today에 1회성 알림 `부하 계산 방식을 바로잡았어요 — 체력·폼 수치가 바뀌었습니다 ›`(→ Library CTL 상세 변경 마커)을 띄운다.

---

## 10. 발견 → 설계 추적표

| 발견 | 설계 위치 | 상태 |
|---|---|---|
| F-DATA-01 | §7.2 pmc, §8, S0 | 반영(α 식은 판단 필요) |
| F-DATA-02 | §7.2 trimp, §8, S0 | 반영 |
| F-DATA-03 | §4 아침 폼, §2.4 done, §7.2 | 반영 |
| F-DATA-04 | §4 밴드, §7.2 SSOT, §C7 | 반영 |
| F-DATA-05 | §2.1 B5, §7.2 week_compliance, §8 | 반영(31과 공동) |
| F-DATA-06 | §4 권고 규칙, readiness_decision | 반영 |
| F-DATA-07 | §4 예측 포맷, §7.2 예측 분해, S5 | 반영(보정 구간은 백테스트 뒤 전환, 그 전 라벨 "모델 범위") |
| F-DATA-08 | S5 허브 실현성·대안 목표 | 반영 |
| F-DATA-09 | §7.2 레이스 투영, §5 x.taper | 반영 |
| F-DATA-10 | S5 허브 행별 기준 표기·당일 기온 환산 | 반영 |
| F-DATA-11 | §7.2 UTRS v2, S7 | 반영(가중치 재설계는 S7) |
| F-DATA-12 | §7.2 CIRS v2, S7 | 반영 |
| F-DATA-13 | §7.2 월간·마일스톤, §8 | 반영 |
| F-DATA-14 | S5 입력 기반 자동 문장 | 반영 |
| F-DATA-15 | §4 표·용어, §C4 | 반영 |
| F-UI-01 | §C1, §5, §8 | 반영 |
| F-UI-02 | §C1 invert, §5, §8 | 반영 |
| F-UI-03 | §C3.2 ②, §7.3 분해 v2 | 반영 |
| F-UI-04 | §2.1~2.3 | 반영 |
| F-UI-05 | §C8, §8 | 반영 |
| F-UI-06 | §C8, §C2 | 반영 |
| F-UI-07 | §C2, §3, §8 | 반영 |
| F-UI-08 | §5 폼 차트, §C7 시리즈색 | 반영 |
| F-UI-09 | §5 스파크라인, §C8 lint | 반영 |
| F-UI-10 | §3 허브 페이지 분리, `ZoneBar`, 대회 편집 화면 | 반영 |
| F-UI-11 | §2.1 공통 우선순위 | 반영 |
| F-UI-12 | §4 게이지 형태 | 반영 |
| F-UI-13 | §C8 아이콘 | 반영(🏁 등 예시 기호는 SVG로 대체) |
| F-UI-14 | 40 §2.1 참조, §2.1 | 보류(셸은 40 설계 소관, Today는 계약만 사용) |
| F-UI-15 | §C8 Card·SectionHeader | 반영 |
| F-UI-16 | §1 상충표, §5 x.taper, B5 WeekStrip | 반영 |
| F-UX-01 | §C3, §3, §8 | 반영 |
| F-UX-02 | §3 B6, §8 | 반영 |
| F-UX-03 | §C2, §3 칩 목적지 | 반영 |
| F-UX-04 | §2.4 상태 기계, §2.3 | 반영 |
| F-UX-05 | §3 허브·D2, §5 | 반영 |
| F-UX-06 | §C3, §1 상충표 | 반영 |
| F-UX-07 | §6, §C5, §8 | 반영 |
| F-UX-08 | §3 B2, §7.1 QuickInput | 반영 |
| F-UX-09 | §3 대회 편집 화면 | 반영 |
| F-UX-10 | §C1, §3 `그날 보기` | 반영 |
| F-UX-11 | §3 Coach·Library 딥링크, S6 | 반영(Coach 수신 측은 30 설계 의존) |
| F-UX-12 | §6 빈/오류 분리, 40 §2.1 | 부분 반영(Data 영역은 40 소관) |
| F-UX-13 | §3 B5·B8, §7.2 activity_id | 반영 |
| F-UX-14 | §2.1 B4 1줄, 실험 알고리즘 토글 | 반영 |
| F-UX-15 | §4 이름·① 블록, §C3.2 | 반영 |
| F-UX-16 | §4 델타, S7 기준선 브리핑 | 부분 반영(목표 진행 막대는 B4 게이지로, 주간 예측 변화 설명은 S7 뒤 검토) |

---

## C. 공통 규격 (전 탭 참조용 — 다른 탭은 재정의하지 않고 참조한다)

### C1. ChartScrub — 차트 상호작용·축 규격

**코어**: `lib/chart/scrub.ts`(순수 함수: 스케일, nice ticks, 가장 가까운 인덱스) + `ChartScrub.svelte`(포인터·키보드·툴팁 레이어). FormChart·TrendChart·Sparkline·Library 스트림 차트가 모두 이 코어를 쓴다.

| 항목 | 규격 |
|---|---|
| 데스크톱 | hover = 미리보기(점 마커 + 툴팁), click = 고정. 고정 중 hover는 미리보기만 하고 고정은 유지 |
| 모바일 | 탭 = 고정, 드래그 = 스크럽. **손을 떼도 유지**(pointerleave·cancel로 해제 금지). 해제 = 판독줄 `×`·차트 밖 탭·같은 점 재탭. 가로 8px 이상 이동만 스크럽(`touch-action: pan-y`) |
| 키보드 | `tabindex=0`, ←/→ 한 점, Shift+←/→ 7점, Home/End, Esc 해제. `aria-live=polite` 판독 |
| 판독줄 | 차트 위 고정 높이 1줄(줄바꿈 금지). 모바일은 약어(`CTL 70.9 · ATL 70.1 · TSB +0.8`). 날짜 `9/12(금)`. 선택적 액션 `그날 보기 ›`(`onPick(date)`이 있을 때만) |
| 툴팁 | 시리즈별 4px 점 + surface-3 박스, 가장자리 좌우 반전, 차트 상단 12px 안쪽(손가락 가림 방지) |
| y 눈금 | nice ticks 3~5개(1·2·2.5·5×10ⁿ). 시간은 1/2/5/10/15/30분 단위, 페이스는 5/10/15/30초 단위. **패딩 경계값을 라벨로 쓰지 않는다**. 라벨 11px sans, fg-secondary, 오른쪽 정렬 |
| x 눈금 | 기간 ≤14일: 요일/일, ≤6개월: 월 경계 `7월`, >6개월: `25.10` 분기. ISO 전체 날짜 금지 |
| 방향 | `invert: true`는 낮을수록 좋은 값(시간·페이스·예측·RHR)에 쓴다. **빨라짐·좋아짐 = 위**. 축 캡션 `빠름 ↑` |
| 참조선 | 목표(수평 점선 + 라벨), 오늘(세로선 + 선에 붙은 라벨), 밴드(옅은 배경, 라벨은 오른쪽 거터 24px) |
| 미래·잠정 | 미래 = 점선, 잠정 점 = 속 빈 원. 범례에 반드시 포함 |
| 범례 | 차트 아래 1줄, 선 모양(━ ┄ ┅ ▆ ▭)과 이름 |
| 결측 | null이 2일 넘게 이어지면 선을 끊는다. 결측 구간 툴팁은 `기록 없음` |
| 빈 데이터 | 점 <2개면 차트 대신 `데이터 수집 중 (n/필요 일수)` + 행동 링크 |
| 최소 크기 | 대화형 차트 높이 ≥ 120px, 스파크라인 48px(스크럽 가능). `interactive={false}` 금지 |

### C2. 근거 칩 2종

| 종류 | 컴포넌트 | 모양 | 사용 조건 |
|---|---|---|---|
| **DrillChip**(대화형) | `DrillChip.svelte` (`<button>` 또는 `<a>`) | 높이 32px(히트 44px), radius full, 테두리 1px `fg-secondary/40`, 배경 surface-2, 라벨 13px sans + 값 `.num` semibold + 끝에 `›`. 눌림 `active:scale-[.97]`, 포커스 링. 상태가 있으면 앞에 의미색 점(모양 병기 ●▲) | `target`(D2 토큰) 또는 `href`가 있을 때만 |
| **InfoTag**(정보형) | `InfoTag.svelte` (`<span>`) | 테두리·배경 없음, 13px fg-secondary, `›` 없음 | 목적지가 없을 때. 원천이 없으면 `(데이터 부족)` |

- 서버 evidence 항목 `kind`는 `drill`·`route`·`info` 중 하나다. `drill`과 `route`는 목적지가 필수다(API 테스트).
- 칩 아이콘은 SVG 12px fg-muted(§C8)다. 이모지는 쓰지 않는다. 한글 라벨에는 mono를 쓰지 않는다.
- 결론(권고·Coach 답변·내러티브) 하나에 칩은 2~3개로 하고, 결론에 영향을 준 입력만 쓴다.

### C3. 드릴다운 시트 D2 — 골격·스택·URL

**C3.1 컨테이너**(`DrillHost` + `DrillPanel.svelte`)
- ≥1024px: 우측 패널 420px, 비모달, 본문 grid를 `1fr 420px`로 밀어낸다(스크림 없음). 본문의 선택 요소에 선택 테두리. 진입·전환 200ms, `prefers-reduced-motion`이면 0.
- <1024px: 풀스크린 슬라이드업, 헤더 고정, safe-area 반영. 최상위에서만 아래로 끌어 닫기.
- 헤더: `← {이전 제목}`(스택 깊이 ≥2일 때) · 브레드크럼 `UTRS › 폼` · `✕`. 제목은 한국어 이름 + 약어(작게). 부제에 기준 시점(`9월 27일 아침 기준`).
- 포커스: 열 때 제목으로, 닫을 때 원 트리거로. 포커스 트랩(모바일), Esc = pop.
- 스택 최대 3단. 더 깊은 이동은 D3(경로 이동)다.

**C3.2 본문 4블록**(순서 고정, `BreakdownView.svelte`)
1. **의미**: 무엇(1문장) · 밴드 바(등급 5색, 현재 위치 핀, 경계 라벨) · 내 값 해석(7일 평균·어제 대비) · 그래서(행동 1문장).
2. **공식·기여**: 공식 1줄(mono 12px, 버전·계산 시각). 행 = `사람 말 라벨 · 원시 입력 · 정규화 · 가중치 · 기여 막대(±)`. 감점이 큰 순으로 정렬하고 1위에 `가장 크게 끌어내림` 태그. 하위 메트릭 행은 `›`(스택 push). 가중치가 없는 산식(TSB = CTL − ATL)은 항을 행으로 둔다.
3. **원천**: 이 값을 만든 활동·웰니스 일자 Top 3(날짜 · 이름 · 기여값 · 효과 `피로 +10.6`). 행 탭 = D3.
4. **푸터**: `추세·과거 보기 →`(Library 메트릭 상세 `?date=&from=`), `Coach에게 묻기 →`(맥락 첨부), provider 비교 줄(있을 때), 출처 배지(§C6).
- 빈 상태: ①과 ④는 항상 나온다. ②·③이 모두 비면 `이 지표는 {원천}에서 직접 받은 값이에요` + 원천 링크를 둔다. 빈 시트는 금지한다.
- 모든 값은 §C4 포맷을 통과한다.

**C3.3 URL·히스토리**
- 쿼리 `drill` = 쉼표로 이은 토큰 스택. 토큰 = `{kind}.{id}[@{scope}]`. `m.` 메트릭 slug, `x.` 특수 시트(`x.taper`, `x.gates`, `x.month`). scope는 `YYYY-MM-DD` 또는 `YYYY-MM`. 생략하면 화면 기준일.
  예: `/v2/today?drill=m.utrs,m.tsb@2026-09-12`
- 열기·push = SvelteKit `pushState`(shallow routing), pop = `history.back()`, 전체 닫기 = `history.go(−깊이)`. 딥링크로 진입해 히스토리가 없으면 pop은 `replaceState`로 토큰을 줄인다.
- 새로고침·공유 시 스택 전체를 복원한다. D3로 나갔다가 돌아오면 스택이 복원된다.
- 차트 고정(`pin`)·시나리오(`scn`) 같은 보기 상태는 `replaceState`로 히스토리를 쌓지 않는다.

### C4. 값 포맷 규칙 (`lib/format.ts`, registry `unit`·`decimal_places` 기반)

| 종류 | 규칙 | 예 |
|---|---|---|
| 시간(기록·소요) | ≥1h `h:mm:ss`, <1h `m:ss`. 원시 초 노출 금지 | `3:40:23`, `55:18` |
| 예측 기록 | 신뢰도 <0.5: `h:mm` + 범위 `(h:mm–h:mm)`. ≥0.5: `h:mm:ss` | `3:40 (3:26–4:03)` |
| 시간 차 | ≥1분이면 `n분`(±), 초 단위는 D2에서만 | `21분 차이`, `90일 −7분` |
| 페이스 | `m:ss/km`, 범위는 en dash `6:21–6:45/km` | `4:43/km` |
| 거리 | ≥1km `n.n km`, <1km `n m` | `9.3km`, `525m` |
| 심박 | 정수 `bpm` | `137 bpm` |
| 점수(0–100) | 정수 | `60` |
| 부하(CTL/ATL) | 소수 1자리, 단위는 정의 블록에(`AU`) | `72.6` |
| 폼(TSB) | 요약·칩·게이지: 부호 정수. 분해 공식: 소수 1자리 | `−9`, `+15` |
| 비율(ACWR 등) | 소수 2자리 | `1.12` |
| 백분율 | 정수 `%`, 백분위는 `p78` | `49%`, `p78` |
| 변화량 | 항상 부호, 화살표는 방향(좋고 나쁨은 색·라벨로) | `↑1`, `+4.2/주` |
| 음수 부호 | U+2212 `−`, 숫자는 `.num`(tabular-nums) | `−14` |
| 정수 물리량 | 층·W·걸음·bpm 반올림 | `22층` |
| 날짜 | 본문 `9월 27일 (일)`, 짧게 `9/27(일)`, 축 `9월`. ISO는 URL에만 | |
| 시각 | 상대 + 툴팁 절대(오프셋 포함 ISO 파싱) | `3분 전` |
| 단위 없음 | 레지스트리 unit 빈 문자열 금지(검사). 모르는 단위는 소수 1자리로 제한 | |

### C5. 스켈레톤·진행바·오류

- **진행바**: 셸 상단 2px(`$navigating`), 150ms 지연 후 표시, 완료 시 페이드. 탭 하이라이트는 클릭 즉시(≤100ms, optimistic).
- **블록 스켈레톤**: 최종 레이아웃과 같은 높이를 예약한다(CLS ≤0.05). surface-3 블록, shimmer 1.2s(`prefers-reduced-motion`이면 정지). 텍스트 줄 12px 높이, 원 게이지, 차트 영역, 칩 윤곽 4종 프리미티브(`Skeleton.svelte`).
- **로딩 원칙**: 라우트는 핵심 API 1개만 await하고 나머지는 streamed promise로 넘긴다. 재방문은 stale-while-revalidate(헤더 필 `업데이트 중` 점).
- **빈 상태**: `무엇이 없는지 + 왜 + 행동 버튼 1개`. "데이터 없음"과 "불러오기 실패"를 구분한다.
- **오류**: 블록 단위 `불러오지 못했어요 · [다시 시도]` + 접힌 상세(오류 코드). 쓰기 실패는 입력 자리 옆에 표시하고 입력값을 보존한다. 쓰기 성공은 토스트 + [되돌리기](5s).

### C6. 출처 배지

| 종류 | 표기 | 색 |
|---|---|---|
| 기기·서비스 | `Garmin` `Strava` `Intervals` `Runalyze`(글자 약어 G/S/I/R은 좁은 곳에서만) | provider 토큰. 작은 배지 대비 ≥4.5:1이 되도록 채움 대신 테두리+글자 사용(40 F-UI-05) |
| RunPulse 계산 | `RunPulse 계산` + D2 푸터에 `pmc_v2 · 06:10 계산` | neutral |
| 사용자 입력 | `직접 입력` | neutral |

- 한 블록의 값이 모두 같은 출처면 블록 헤더에 한 번만 표시한다. 섞이면 값마다 표시한다.
- 값의 기준일이 화면 기준일과 다르면 배지에 날짜를 붙인다(`Garmin · 9/26`). 30일 넘게 갱신이 없으면 회색 + `오래된 값`.
- 배지 탭 = D2 ④ 출처 줄 또는 소스 상세(`/v2/data/sources/:provider`, 40 설계).

### C7. 등급·의미색·시리즈색

- 등급은 서버 `status ∈ {danger, caution, neutral, good, great}` + `status_label`로만 렌더한다. 프론트에 경계값을 두지 않는다.
- 의미색: danger red · caution amber · neutral slate-400 · good teal · great green. 색만으로 구분하지 않고 라벨·모양(●▲)을 병기한다.
- **시리즈색은 의미색·provider색과 분리한다**: `--series-1` sky-300 계열(주 시리즈), `--series-2` slate-300(보조), `--series-3` 경계 대비용. amber·red·teal·green과 provider 색은 시리즈에 쓰지 않는다. 최종 값은 dataviz 팔레트 검증(대비 3:1, 색각 이상 시뮬레이션)으로 확정한다.
- 상태 기호(계획·이행): `●` 완료 · `◐` 부분 · `○` 미이행 · `⟳` 대체 · `◉` 오늘 · `┄` 휴식.

### C8. 타이포·토큰·아이콘

- 폰트: Inter Variable(sans), JetBrains Mono(숫자 전용 보조), self-host woff2, `font-display: swap`. 숫자는 `.num { font-variant-numeric: tabular-nums }`.
- 스케일: caption 12/16(최소), body-sm 13/18, body 15/22, title 18/24, headline 20/28, hero 32/36. 12px 미만 금지(축 눈금 11px 예외).
- 대비: `fg-muted`를 surface-2 위에서 ≥4.5:1이 되도록 상향하거나, 카드 위 보조 텍스트는 `fg-secondary`를 쓴다.
- 컴포넌트: `Card`(radius 12, surface-2, border subtle, padding 16), `SectionHeader`(13px semibold + 우측 액션 링크), 강조 변형은 좌측 3px 의미색 바.
- 아이콘: `Icon.svelte` 확장(metric, activity, note, target, trophy, refresh, warning, close, menu, chevron; 16/20px, stroke 1.8, currentColor). 이모지·문자 아이콘(✕ ☰ ⚠)은 쓰지 않는다. 이 문서 와이어프레임의 기호는 자리 표시다.
- 미정의 CSS 변수는 Stylelint(`value-no-unknown-custom-properties`)로 CI에서 실패시킨다.
