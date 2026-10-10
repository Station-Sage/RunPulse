# v2 미구현 영역 — 통합 개선 설계 (data·ui·ux)

**작성일**: 2026-09-27 · **입력**: `40-v2-unimplemented/data.md`(F-DATA-01~13) · `ui.md`(F-UI-01~09) · `ux.md`(F-UX-01~12) · `00-vision-criteria.md` · `02-information-architecture.md` · `03f-data.md` · 실데이터 GET(`/library/providers/status`, `/bg-sync/status`)
**대상**: 전역 셸(☰·동기화 상태·as-of) · ☰ Data(`/v2/data/*`: 개요·동기화·소스·내보내기·가져오기·설정·기준값·재계산) · 계획 비교(참조만) · Story(`/v2/library/story/*`) · 웰니스 일자(`/v2/library/wellness/:date`) · 첫 사용자 온보딩(`/v2/welcome`) · 빈/오류 4상태 · v2 기본 진입 전환 게이트 G0~G6 · v1 → v2 계승 목록
**공통 규격**: 차트·칩·D2 시트·값 포맷·스켈레톤·출처 배지·의미색·토큰은 `10-today/design.md §C1~C8`을 **참조**하고 재정의하지 않는다. 계획 비교의 결정은 `31-coach-plan/design.md`(§2.6, §3, §4.1 R10, §7.2, S2·S6)를 따른다. Library 섹션 탭은 `20-library-activities/design.md §2-1`을 따른다.
**성격**: 설계만 다룬다(코드 수정 없음). 스키마·원장 결정은 `DECISIONS.md` 기록 대상이며 구현 착수 전 사용자 확인이 필요하다.

---

## 1. 요약

**설계 목표**
1. **동기화 사실을 한 곳에서 정한다.** "마지막 동기화" 값이 세 저장소(`sync_state.json`, `sync_jobs.updated_at`, `MAX(source_payloads.fetched_at)`)에서 모두 다르다. 이를 **작업 원장(`sync_jobs` 확장) 하나와 거기서 파생한 `SyncState` 계약 하나**로 바꾼다. 셸·Today·Library·Data가 모두 이 계약만 읽는다.
2. **v2 안에서 "넣고 → 확인하고 → 고치는" 루프를 닫는다.** ☰를 활성화하고, 헤더 `SyncStatusPill` → 동기화 시트 → [지금 동기화]를 2동작 안에 끝낸다. 소스 실패는 분류 코드와 행동 버튼이 붙은 문장으로 보여 주고, 결손 기간이 부하 지표에 주는 영향도 함께 알린다.
3. **막다른 화면을 없앤다.** 빈 상태 3종과 오류 1종(4분류)을 전역 컴포넌트로 정의하고 `+error.svelte`를 둔다. 첫 사용자에게는 온보딩을 준다. Story와 웰니스 일자에는 URL을 준다.
4. **v2 기본 진입 전환을 되돌릴 수 있게 만든다.** 계정 설정 `ui_default`와 전역 기본값 1줄로 롤백한다. 게이트 G0~G6은 흐름 기준(과업 T1~T13의 동작 수)으로 통과 여부를 판정한다.

**범위 밖**: 계획 상세·마법사·비교 화면의 설계 본문(31 소관, 여기서는 진입과 전역 오류만 다룬다), Today 본문(10 소관, SyncState 계약만 제공), 메트릭 계산식 수정(10·21 소관).

**세 평가 간 상충과 판단**

| 쟁점 | 의견 | 채택 · 이유 |
|---|---|---|
| 원장 저장소 | data: `sync_jobs`를 원장으로 승격 / ui: `SyncState` 계약만 요구 | **`sync_jobs` 확장**(새 테이블 대신 열 추가). 이미 `job_type`·`last_error`·`retry_after`가 있다. 재계산·내보내기·가져오기도 `job_type`으로 같은 원장에 넣어 "작업 진행" UI를 하나로 만든다. `sync_state.json`은 쓰기를 중단하고 원장에서 파생한다 |
| SyncState 필드명 | data: `attempted_at/succeeded_at/last_new_data_at` / ui: `last_success_at/last_attempt_at/latest_data_date` | **ui 명명 + data 의미**: `last_attempt_at`, `last_success_at`, `last_new_data_at`, `last_error{code}`, 전역 `latest_data_date`. "동기화 시각"과 "데이터 기준일"을 분리한다는 ui 원칙을 이름에 반영했다 |
| 지연 판정 기준 | data: as-of 6h·배지 24h / ui: 24h / ux: 12h | **12h 한 기준.** 자동 동기화가 1시간 주기라 12h는 연속 실패 10회 이상을 뜻한다. 밤 9시 성공 → 아침 9시 확인 경계와도 맞는다. 오류는 시간과 상관없이 즉시 red |
| Pill 탭 결과 | ui: `/data` 이동(데스크톱 팝오버) / ux: `?sheet=sync` 시트 | **모바일 시트, 데스크톱 팝오버. 둘 다 같은 `SyncPanel` 내용**(소스 4행 + [지금 동기화] + `Data에서 관리 →`). 매일 하는 과업(T1·T2)을 페이지 이동 없이 끝낸다 |
| ☰ 위치 | IA 문서 좌/우 혼재, 구현은 우 | **좌측 ☰, 우측 Pill**(ui F-UI-08). 모바일 좌측 드로어와 방향이 일치한다. DECISIONS 기록 |
| 드로어 구성 | ui: 항목 나열 / ux: 빈도순 + 상단 동기화 요약 | **ux 빈도순**을 ui 시각 규격으로 그린다. 드로어 최상단에 동기화 요약과 [지금 동기화]를 둔다 |
| 재계산 노출 | ui: 동기화 고급 / data·ux: 독립 버튼 숨김, 제안형 | **제안형이 기본**(기준값 변경·가져오기 뒤). 수동 실행은 `설정 › 시스템` 한 곳에만 둔다. v1의 중복 배치는 계승하지 않는다 |
| 설정 저장 방식 | ui: 필드 자동 저장 / ux: 저장 → 영향 미리보기 → 재계산 | **값의 성격으로 나눈다.** 기준값(HRmax·LTHR·역치)은 [적용] + 영향 미리보기다. 존·이행률·예측이 바뀌기 때문이다. 표시·AI 전송 범위·자동 동기화는 자동 저장한다 |
| 기준값 입력 | ui: 단일 입력 / data: `자체 추정 \| 기기 \| 직접 입력` 3열 | **data 3열 + "사용 중" 선택.** 값이 세 벌인 현실을 숨기지 않는 것이 P3다 |
| 내보내기 형태 | ui: DB 사본 백업 / data: 테이블 CSV + 원본 JSON + manifest zip | **data zip.** 공식 버전·계산 시각이 담긴 재현 가능한 형식이다. DB 사본은 내부 스키마 의존이 커서 보류한다 |
| Story 단위 | ui·ux: 월 페이지 / data: 주·블록·월 토글 | **라우트는 세 단위 모두 정의하고, 구현은 월 → 주 → 블록 순서로 한다.** 블록 경계는 활성 계획 phase를 쓴다 |
| 온보딩 단계 | Today 설계: 3단계 / ux: 4단계(+기준값) | **4단계, 4단계는 선택.** 기준값을 첫 선택으로 받으면 초기 존 판정 오류(9.5bpm 차)를 막는다. 건너뛰면 자체 추정값을 쓴다 |
| 계획 비교 | data: 목표 축 3안 / ui: 1건 모드 / ux: "지금 계획" 열 | **31 설계를 그대로 따른다**(시나리오 3안, 무파라미터 307 → `/new`, 확인 시트). ux의 "지금 계획" 열은 31 S6에 **추가 제안**으로만 남긴다(§2.9) |

---

## 2. 정보 구조·배치

### 2.1 전역 셸 — 블록과 근거
| 위치 | 요소 | 근거 |
|---|---|---|
| 헤더 좌 | ☰(44×44) + 화면 제목(데스크톱) / 브랜드(모바일) | P4: 관리 기능은 ☰. 좌측 드로어 방향과 일치 |
| 헤더 우 | `SyncStatusPill`: 데이터 기준일 + 마지막 성공 상대 시각 + 상태 점(모양 병기) | P8: 마지막 동기화 상시 표시 |
| 사이드바(≥1024) | Today·Library·Coach / 구분선 / Data / `SidebarSyncBlock`(소스별 1줄) | 데스크톱은 빈 폭이 있으므로 소스별 상태를 상시 노출 |
| 하단 탭(<1024) | Today·Library·Coach(56px + safe-area) | 기존 유지. Data는 탭이 아니다(IA) |
| 셸 상단 2px | 진행바(`$navigating`, §C5) | U9 |

```
데스크톱 1280                                                      모바일 390
┌────────────┬──────────────────────────────────────────────┐   ┌──────────────────────────────┐
│◉ RunPulse  │ ☰  Today              ● 9월 27일 · 3분 전 동기화│   │☰ RunPulse    ● 9/27 · 3분 전 │ 48px
│────────────│──────────────────────────────────────────────│   ├──────────────────────────────┤
│ Today      │                                              │   │                              │
│ Library    │  (본문 max-w-6xl)                             │   │  (본문)                       │
│ Coach      │                                              │   │                              │
│ ────────── │                                              │   ├──────────────────────────────┤
│ Data     • │ ← 오류가 있으면 점 배지                        │   │ Today   Library   Coach      │ 56+safe
│ ┌────────┐ │                                              │   └──────────────────────────────┘
│ │Garmin ● 3분 전 │                                        │
│ │Intervals ● 4시간│                                        │   Pill 4상태(색 + 모양 + 문구)
│ │Strava ○ 꺼짐   │                                        │   ● 9/27 · 3분 전            (teal)
│ └────────┘ │                                              │   ● 9/26 기준 · 14시간 전      (amber)
└────────────┴──────────────────────────────────────────────┘   ▲ Strava 연결 만료           (red)
                                                                  ⟳ 동기화 중 1/2              (fg)
```

### 2.2 동기화 패널(`SyncPanel`) — 모바일 시트 `?sheet=sync` / 데스크톱 팝오버 360px
```
┌ 동기화 ───────────────────────────── ✕ ┐
│ 9월 27일 데이터까지 · 마지막 성공 3분 전  │
│ ▌Garmin     ● 20:56 · 활동 1 · 웰니스 1 │  ← 소스 행 = 상태 기계(§3.2) 1행
│ ▌Intervals  ● 16:52 · 새 데이터 없음     │
│ ▌Strava     ▲ 접근 차단(403)             │
│   Garmin 데이터로 계속됩니다              │
│   [동기화에서 제외] [자세히]              │
│ ▌Runalyze   ○ 미연결            [연결 ›] │
│ ─────────────────────────────────────── │
│ [ 지금 동기화 ⟳ ]  (전폭 44px, primary)  │
│ 기간 지정 · 과거 데이터 가져오기 ›         │
│ Data에서 관리 →                          │
└─────────────────────────────────────────┘
실행 중: 버튼 → "동기화 중 1/2 · 중지", 소스 행에 진행 막대 + "2026-09-20 가져오는 중"
```

### 2.3 ☰ 드로어(모바일 좌측 min(320px,85vw), surface-4, 스크림 60%) / 데스크톱 ☰ 팝오버 280px
빈도순(ux F-UX-11): ① 동기화 요약 1행(소스 점 4개 + 마지막 성공 + [⟳]) ② 소스 연결 `3/4 연결` ③ 내 데이터(내보내기·가져오기) ④ 설정(러너 기준값 / AI 코치 / 표시·화면 전환) ⑤ 지표 가이드·버전 ⑥ 로그아웃. 과도기(G1 전)에는 ③④ 아래에 `기존 화면에서 관리(v1) ↗`를 둔다.

### 2.4 Data 영역 `/v2/data/*` — SubTabs `개요 | 동기화 | 소스 | 내보내기 | 설정`
공통: `data/+layout.svelte`에 `SubTabs`(44px, 가로 스크롤, `aria-current`, ui F-UI-09)를 한 번만 둔다. 가져오기(`/data/import`)와 기준값(`/data/settings/profile`)은 하위 페이지다.

**개요 `/data`** — ui.md §2.3 와이어프레임을 채택하고, 변경점만 적는다.
- StatTile 4개: `통합 활동 N건`(중복 제거 수, 소스 합 1,429 아님) · `웰니스 N일` · `기간 2019-03~` · `저장 788MB`.
- SourceCard 4장: 연결 상태와 동기화 포함 여부를 **별개 축**으로 표시한다(data F-DATA-04). 끈 소스는 `○ 동기화 꺼짐 · 과거 202건 보존`(회색, 경고 아님).
- `최근 작업` 5행: 원장의 동기화·재계산·내보내기를 한 목록으로 보여 준다. 오류 행은 red 아이콘과 문장 한 줄, 탭하면 펼친다.
- 데이터 공백 알림(있을 때만): `2024-03~05 전 소스 0건 · 가져오기 ›`(커버리지 → 임포트 딥링크, data F-DATA-08).

**동기화 `/data/sync`** — ui.md §2.4 와이어프레임 채택. 변경점:
- 범위 라디오 `새 데이터만 | 기간 지정`. 기간 지정 시 **예상 요청 수와 레이트리밋 잔량**을 표시한다(`약 32요청 · Garmin 15분 잔량 50/50`, data F-DATA-13).
- 결과는 종류별 카운트다: `활동 신규 0 · 갱신 2 · 웰니스 15일 · 랩 보강 1`.
- 자동 동기화 행: `켜짐 · 1시간마다 · 최근 14일 · 마지막 12:40 · 다음 13:40`. 자동 실행 실패도 로그와 배지에 남긴다.
- 재계산 버튼은 두지 않는다(§1 판단).

**소스 상세 `/data/sources/:provider`**
```
┌ ← 소스  Garmin ──────────────────────────────┐
│ ● 연결됨 · 계정 확인됨 · 마지막 성공 3분 전(20:56) │
│ [지금 동기화] [재연결]          [연결 해제…]   │  ← 해제는 우측 분리 + 확인 시트
│ 동기화에 포함  [● 켜짐]                        │  ← 토글. 끄면 대기 잡 cancelled
│ 이 소스가 준 데이터                             │
│  활동 589 · 웰니스 890일 · 스트림 571 · 랩 540  │
│  12개월 커버리지 ▁▂▃▅▆▇▇▆▇█ (월 셀, 탭 → 그 달 활동) │
│ 대표값으로 쓰이는 지표  심박·케이던스·VO2max ›   │  ← Library 소스(Provider 비교)로
│ 최근 작업 (이 소스만) 5행                       │
└──────────────────────────────────────────────┘
키 방식(Intervals·Runalyze) 미연결: [API 키 ____] [연결 확인] → 즉시 검증 결과 한 줄
```

**내보내기 `/data/export`** — ui.md §2.6 카드 배치를 쓰되 카드 구성을 바꾼다: ① 빠른 CSV(활동 통합 + 소스별 원값 열 / 일별 웰니스 / 일별 부하), 사람용 열(`h:mm:ss`, `m:ss/km`)과 기계용 열(초)을 함께 넣는다 ② 전체 아카이브 zip(작업) ③ 계획 캘린더 `.ics`(기존 `/training/export.ics`) + 구독 URL ④ `외부 AI로 전송되는 범위` 고지 줄 → 설정 AI. 아카이브는 담기는 파일 목록을 미리 보여 주고, 완료되면 토스트와 ☰ 배지를 띄운다. 링크는 7일 뒤 만료되고 `내보내기 기록`에서 다시 받는다.

**가져오기 `/data/import`** — 4단계: ① 파일 선택(Strava zip·FIT/GPX·Garmin bulk) ② **미리보기**(인식 N건 · 기간 · 중복 M건[시작 ±60초, 거리 ±3%] · 신규 K · 스트림/랩 보강 L) ③ 실행(원장 작업, 상태 기계 재사용) ④ 결과(신규·보강·건너뜀·오류 행) + `최근 기간 재계산 제안`.

**설정 `/data/settings`** — 섹션: 러너 기준값(§2.5 페이지로 이동) · AI 코치 · 표시 · 화면(`ui_default`) · 시스템 정보(버전·공식 버전·DB 크기·행 수, 경로 비노출) · 고급(전체 재계산 1곳).
- **AI 코치**(data F-DATA-12): 제공자 라디오(`Gemini | Groq | 규칙 기반`), 키 상태(마스킹 + [연결 테스트]), **전송 범위 체크리스트**(최근 N일 활동 요약 ☑ / 웰니스 ☑ / 체크인 메모 ☐ / 원본 GPS ☒ 항상 제외), 최근 7일 사용량. 하단에 외부 AI 연동(프롬프트 복사·MCP 연결 상태·마지막 접근 시각).

### 2.5 러너 기준값 `/data/settings/profile`
```
데스크톱                                                   모바일: 행마다 카드, 3값을 세로 라디오
┌ 러너 기준값 ────────────────────────────────────────────────────────┐
│ 존·처방·이행 판정·예측이 이 값을 씁니다.                                 │
│            자체 추정            기기(Garmin)      직접 입력        사용 중 │
│ 최대 심박   192 bpm ⓘ           —                [190] bpm        (●자체) │
│            대회 2건 · 9/20 추정 · 신뢰 중간 ›                              │
│ 젖산역치 HR 177.5→178 bpm ⓘ     168 bpm · 9/12    [   ]            (●자체) │
│ 역치 페이스 4:23/km ⓘ           4:31/km          [ :  ]/km        (●기기) │
│ 안정 심박   —                   41 bpm · 오늘     [   ]            (●기기) │
│ 주간 목표   —                   —                [45] km          (●직접) │
│ ────────────────────────────────────────────────────────────────── │
│ 변경 1건: 최대 심박 190 → 192                                          │
│ 영향 미리보기: HR 존 5개 경계 +1~2bpm · 최근 90일 메트릭 약 312건 재계산     │
│ [적용하고 재계산] [적용만] [취소]                                        │
└─────────────────────────────────────────────────────────────────────┘
```
- ⓘ는 §4.2 문안을 쓴다. 자체 추정 행의 `›`는 근거(대회 활동 링크·추정 시각·신뢰도) 시트를 연다.
- 저장 키는 `profile.overrides`와 `profile.source_choice` 한 곳으로 모은다. `threshold_pace` / `threshold_pace_sec_km` 불일치는 이관 스크립트로 정리한다(data F-DATA-06).

### 2.6 재계산 결과(원장 작업 완료 시트/토스트 → 상세)
```
재계산 완료 · 최근 90일 · 41초 · 사유: 최대 심박 변경
            전       후       변화
체력 CTL    72.6     72.6     —
폼 TSB      −9       −8       +1
VDOT        44.5     44.3     −0.2
마라톤 예측  3:40:23  3:41:02  +0:39   ← 시간은 늦어짐=amber
준비도 UTRS  59       61       +2
바뀐 날짜 88일 · 공식 버전 hrzones_v1 → v2
```
메트릭 상세(21 소관)에는 `9/27 재계산됨(사유)` 이력 표식을 남긴다.

### 2.7 웰니스 일자 `/v2/library/wellness/:date`
ui.md §2.10 와이어프레임을 채택하고 data·ux를 합친다.
```
┌ Library [홈][활동][메트릭][웰니스][이야기][소스] ────────────────────────┐
│ ‹  9월 20일 (일)  ›  [오늘] [📅]      Garmin 04:53 갱신 · 최종            │ ← 당일이면 "진행 중 · 14:10 기준"
│ 월 화 수 목 금 토 일  (7일 스트립, 수면점수 농도, 선택일 링, 각 44px)       │
│ 준비도 UTRS 59 보통 · 부상위험 CIRS 37 주의                    RunPulse 계산│
│ ┌수면 점수──┬수면 시간─┬HRV 야간──┬안정 심박─┐                   Garmin    │
│ │ 90        │ 8:03     │ 97 ms    │ 41 bpm   │                            │
│ │ 28일 평균 72│ 평균 +1:10│ 균형 범위 75–111│ 평균 −3 │ ← 개인 기준선 대비     │
│ └───────────┴──────────┴──────────┴──────────┘                            │
│ 수면 단계 막대(깊은·얕은·REM·깬) · 취침 23:12 → 기상 07:15                    │
│ 이날의 훈련: 전날 인터벌 10.2km › · 당일 롱런 24.2km › · 체크인 RPE 6 ›       │
│ 상세 지표(카테고리 접이식)  ▸ 몸  ▸ 심박  ▸ 수면  ▸ 스트레스·BB              │
│ 30일 추세 [수면][HRV][안정심박][UTRS]  TrendChart 1개, 선택일 세로선          │
└──────────────────────────────────────────────────────────────────────┘
```
- 모바일: 카드 2열, 추세 칩 가로 스크롤, 날짜 스테퍼는 상단 sticky다.
- Library 섹션 탭은 20 설계의 5탭에 **`이야기`를 추가해 6탭**으로 한다(`홈|활동|메트릭|웰니스|이야기|소스`). 모바일은 가로 스크롤이라 비용이 작다. 20 설계에 대한 **추가**이며 재정의가 아니다.

### 2.8 Story `/v2/library/story/:period`
`:period` = `2026-09`(월) · `2026-W39`(주) · `b-<planId>-<phase>`(블록). 기본 `/library/story` → 이번 달로 리다이렉트한다.
```
데스크톱                                                          모바일: 한 열 스택, 기간 이동 sticky
┌ ‹ 8월   2026년 9월   10월 ›        [주 | 블록 | 월●]   [텍스트로 복사] ┐
├──────────────────────────────────────┬──────────────────────────────┤
│ ① 한 문단(규칙 기반) + DrillChip 2~3  │ ② 이전 같은 단위 대비          │
│ "9월 171.0km, 17회. 체력(CTL) 68→74…" │ 거리 171.0km  +11%  (8월 154.1)│
│ [CTL 73.8 ›] [9월 171.0km ›] [롱런 24.2km ›] │ 시간 16:40  +9%            │
│ ⑤ 체력·피로 추이 (C1 ChartScrub 160px)│ 부하 합 …   품질 세션 5 (+1)   │
│ 주별 거리 막대(탭 → 활동 목록 주 필터)  │ ③ 강도 분포 Z1-2 78% · Z3 9% · Z4-5 13% (목표 80/20) │
│                                      │ ④ 대표 세션 3: 최장·품질 최고·레이스 › │
│                                      │ ⑥ 위험 최고: ACWR 1.42 (9/14) ›     │
│                                      │ ⑦ 예측 변화 3:43 → 3:40 · 원인 칩    │
│                                      │ 마일스톤 ◆ 9/20 누적 3,800km ›       │
├──────────────────────────────────────┴──────────────────────────────┤
│ 규칙 기반 요약 · 9월 27일 기준                            Coach에게 묻기 → │
└──────────────────────────────────────────────────────────────────────┘
```
- 블록 순서 근거: 결론(①) → 성장 비교(②) → 균형(③) → 증거(④⑤) → 위험·예측(⑥⑦). data F-DATA-10의 6요소를 ui 레이아웃에 배치했다.
- Today B7 "월간 이야기 `전체 ›`"는 이 라우트가 생기면 `x.month` D2 대신 `/library/story/2026-09`로 간다(10 설계 §3이 예고한 전환).
- 블록 단위는 활성 계획 phase 경계를 쓰고, 계획이 없으면 토글에서 숨긴다.
- 강도 분포가 전부 0%인 경우(v1 결함)는 `존 데이터 부족`으로 표시하고 0%를 그리지 않는다.

### 2.9 계획 비교 — 31 설계 참조
- 화면·계산·API는 `31-coach-plan/design.md` §2.6·§3·§4.1 R10·§7.2를 따른다. 목표 시나리오 3안, 예측은 Today 레이스 허브 값, 위험도는 규칙 최고 등급 + 근거 문장, 무파라미터 진입은 307 → `/coach/plan/new`, 생성 전 확인 시트.
- 40이 맡는 것은 두 가지다. ① 전역 `+error.svelte`(§6.3, 31 §6과 같은 규격, 한 파일) ② 활성 계획 사용자의 진입: 31 `⋯` 메뉴의 `계획 설정`(replan-preview)·`새 대회 계획` + Today B4 `계획 조정 보기 ›`.
- **31에 대한 추가 제안(보류, 31 S6 소관)**: 활성 계획에서 비교로 들어오면 `지금 계획` 열을 4번째 열로 고정한다(ux F-UX-04). `⋯` 메뉴에 `내보내기(ICS·Garmin 전송·캘린더)`를 추가한다(v1 계승 #19).

### 2.10 첫 사용자 온보딩 `/v2/welcome`
```
모바일(데스크톱은 가운데 560px 카드)
┌ ● ○ ○ ○  1/4 기기 연결              건너뛰기 ┐
│ 달리기 기록이 있는 곳을 연결하세요.            │
│ Garmin 하나면 충분해요 · 나머지는 나중에       │
│ ┌ Garmin    [연결 ›] ┐ ┌ Strava    [연결 ›] ┐ │
│ ┌ Intervals [연결 ›] ┐ ┌ Runalyze  [연결 ›] ┐ │
├──────────────────────────────────────────────┤
│ 2/4 과거 데이터 가져오기                        │
│ (● 최근 90일 권장) (○ 1년) (○ 전체)  [시작]     │
│ Garmin ████████░░ 2026-03까지 · 활동 212       │ ← 상태 기계 재사용. 진행 중에도 3단계 가능
├──────────────────────────────────────────────┤
│ 3/4 목표 레이스(선택)  거리·날짜·목표 시각        │ ← 31 마법사 ① 컴포넌트 재사용
│ 4/4 기준값 확인(선택)  기기 최대심박·역치 → 확인   │ ← §2.5 축약
└──────────────────────────────────────────────┘
완료 → Today 최상단 1회성 카드: "가져온 데이터: 활동 312건 · 2023-10~ · 가장 긴 달리기 24.2km [둘러보기]"
```
- 진행 상태는 서버에 저장한다(`/me/onboarding`). 중간에 떠나도 이어서 진행한다.
- 진입 조건: 연결 소스 0개 + 활동 0건이면 `/`·`/today`에서 리다이렉트한다. 건너뛰면 Today `empty-first`로 간다.

---

## 3. 클릭별 동작 명세

### 3.1 요소별 동작

| 요소 | 제스처 | 결과 | 뒤로가기 | URL 상태 |
|---|---|---|---|---|
| 헤더 ☰ | 탭 | 드로어(모바일) / 팝오버(데스크톱). 포커스 트랩, Esc 닫기, 닫으면 ☰로 포커스 | 드로어 닫힘 | `?menu=1`(모바일만, push) |
| SyncStatusPill | 탭 | 모바일 `SyncPanel` 시트 / 데스크톱 팝오버 | 시트 닫힘 | `?sheet=sync` |
| SyncStatusPill | 호버(데스크톱) | 툴팁: 소스별 절대 시각 `Garmin 2026-09-27 20:56 KST` | — | — |
| 사이드바 소스 행 | 클릭 | `/data/sources/:provider` | 이전 화면 | 경로 |
| 안내 문구 3곳(`providerHint`·`healthNotice`·Today 빈 상태) | 탭 | 문구 끝 `동기화 열기 ›` → `?sheet=sync` | 시트 닫힘 | `?sheet=sync` |
| 패널 [지금 동기화] | 탭 | ≤100ms pressed → `POST /data/sync`, 행이 `queued`/`running`으로 전이 | — | — |
| 패널 [중지] | 탭 | bg 작업 중지(재개 가능 표시) | — | — |
| 오류 행 [재연결] | 탭 | OAuth 창 또는 키 입력 인라인 → 복귀 후 실패 동기화 자동 재시도 | 소스 상세 | `?connected=1` |
| 오류 행 [동기화에서 제외] | 탭 | `PATCH sync_enabled=false`, 대기 작업 cancelled, 토스트 [되돌리기 5s] | — | — |
| 완료 토스트 [보기] | 탭 | 새 활동 1건이면 `/library/:id`, 여러 건이면 `/library/activities?from=` | 원래 화면 | 경로 |
| 드로어 `이전 화면으로(v1)` | 탭 | `PATCH /me/preferences {ui_default:"v1"}` → `/dashboard` | — | — |
| v1 헤더 `새 화면 사용해 보기` | 클릭 | `ui_default:"v2"` → `/v2/today` | — | — |
| Data SubTabs | 탭 | 해당 경로(스크롤 위치 유지) | 이전 탭 | 경로 |
| SourceCard | 탭 | `/data/sources/:provider` | `/data` | 경로 |
| SourceCard [연결] | 탭 | OAuth: `return_to=/v2/data/sources/:p?connected=1` / 키: 상세 인라인 입력 | 카드 | 경로 |
| 소스 상세 [연결 해제…] | 탭 | 확인 시트: `가져온 활동 202건 [유지 · 삭제]` → 삭제 선택 시 2차 확인 | 시트 닫힘 | `?sheet=disconnect` |
| 커버리지 월 셀 | 탭 | 데이터 있음: `/library/activities?month=` / 0건: `이 기간 가져오기` 시트(기간 동기화·파일 가져오기) | 원래 화면 | 경로 / `?sheet=gap&ym=` |
| 최근 작업 행 | 탭 | 펼침: 종류별 카운트·오류 원문·재시도 | — | `#run-<id>` |
| 기간 동기화 [시작] | 탭 | 예상 요청 수가 레이트리밋 잔량을 넘으면 확인 한 번 | — | — |
| 내보내기 카드 [받기] | 탭 | 빠른 CSV: 즉시 다운로드 / 아카이브: 작업 생성, 토스트 `준비되면 알려 드릴게요` | — | — |
| 기준값 라디오 | 탭 | 변경 목록·영향 미리보기 갱신(서버 preview) | — | — |
| 기준값 [적용하고 재계산] | 탭 | 저장 → 재계산 작업 → 완료 시 §2.6 요약 | — | — |
| 기준값 자체 추정 `›` | 탭 | 근거 시트(대회 활동 링크 → `/library/:id`) | 시트 닫힘 | `?sheet=basis-hrmax` |
| AI 전송 범위 체크 | 탭 | 자동 저장, 행 우측 `✓ 저장됨` 1.5s | — | — |
| Story 기간 ‹ › | 탭 | 이전/다음 기간(`goto`, push) | 직전 기간 | 경로 |
| Story 단위 토글 | 탭 | 같은 날짜를 포함하는 주/블록/월 | 이전 단위 | 경로 |
| Story 수치 칩·대표 세션·마일스톤 | 탭 | 칩: D2(§C3) / 세션·마일스톤: `/library/:id` / 월 거리: `/library/activities?from&to` | Story | 경로 / `?drill=` |
| Story [텍스트로 복사] | 탭 | 클립보드 + 토스트 `복사됨` | — | — |
| 웰니스 ‹ › / 7일 스트립 칸 | 탭 / 좌우 스와이프 | 날짜 이동(미래 비활성) | 이전 날짜 | `/wellness/:date`(push) |
| 웰니스 `[📅]` | 탭 | 달력 팝오버(데이터 있는 날 점) | 닫힘 | — |
| 웰니스 수치 카드 | 탭 | D2 `m.<slug>@<date>`(§C3) → `추세 보기` = Library 메트릭 | D2 닫힘 | `?drill=m.hrv@2026-09-20` |
| 웰니스 추세 차트 점 | 탭 / 판독줄 `그날 보기 ›` | 그 날짜로 이동(C1 `onPick`) | 이전 날짜 | 경로 |
| 활동 상세 `이날 컨디션 ›`(20 설계에 추가) | 탭 | `/library/wellness/:date` | 활동 | 경로 |
| Today 근거 칩 `수면 66 ›` | 탭 | D2 `m.sleep_score`(10 소관), D2 ④ `그날 웰니스 ›` | — | — |
| ErrorState [다시 시도] | 탭 | 해당 블록/페이지 load 재실행, 3회 실패 시 `상태 보기 → ?sheet=sync` | — | — |
| `+error.svelte` [이전 화면] / [Today] | 탭 | `history.back()`(히스토리 없으면 상위 경로) / `/today` | — | — |
| 온보딩 [건너뛰기] | 탭 | 다음 단계. 4단계 뒤 Today | 이전 단계(입력 보존) | `/welcome?step=N` |

### 3.2 동기화 상태 기계(소스 행 단위, ux F-UX-02 채택 + 원장 코드 연결)

| 상태 | 원장 조건 | 행 표시 | 행동 | Pill 영향 |
|---|---|---|---|---|
| `idle-ok` | `last_success_at` < 12h, 미해결 오류 없음 | `● 20:56` | [지금 동기화] | teal |
| `idle-stale` | ≥ 12h | amber `● 14시간 전` | [지금 동기화] | amber |
| `disabled` | `enabled=false` | `○ 동기화 꺼짐 · 과거 N건 보존` | [다시 포함] | 영향 없음 |
| `not_connected` | 자격증명 없음 | `○ 미연결` | [연결] | 영향 없음 |
| `queued` | 작업 `pending` | `대기 중` | [취소] | `⟳` |
| `running` | 작업 `running` | 진행 막대 + `2026-09-20 가져오는 중 · 3/12일` | [중지] | `⟳ 동기화 중 n/m` |
| `done-new` | 성공, 신규·갱신 > 0 | `✓ 활동 2 · 웰니스 1` | — | teal |
| `done-empty` | 성공, 카운트 0 | `✓ 새 데이터 없음`(성공, 경고 아님) | — | teal |
| `blocked` | `running`/`retry_after`/정책 가드 | 회색 `⏱ 18분 후 가능` + 사유 | 비활성 + 카운트다운 | 변화 없음 |
| `error-auth` | `auth_expired`/`auth_revoked` | red `▲ 다시 로그인 필요` | [재연결] | red |
| `error-access` | `subscription_required`(403) | red `▲ 접근 차단` + `Garmin 데이터로 계속됩니다` | [동기화에서 제외] [자세히] | red |
| `error-upstream` | `upstream_5xx`/`timeout`/`rate_limited` | amber `▲ 일시 오류 · 20:10` | [다시 시도] | amber |
| `interrupted` | 재시작으로 중단 | `⏸ 중단됨 · 이어서 가능` | [이어서] | amber |

- 전체 결과는 토스트 1개로 요약한다: `동기화 완료 · 활동 2 · Strava 실패 1 [보기]`. 성공하면 Today·Library 데이터를 무효화한다.
- **통합 순간(ux F-UX-12)**: 새 활동이 2개 이상 소스에서 합쳐졌으면 토스트 문구를 `아침 러닝 9.3km · Garmin + Intervals 합침 · 폼 −15 → −18 [보기]`로 바꾼다(판단 지표 1개 변화 포함).
- 미해결 오류는 해결 전까지 ☰ 점 배지와 사이드바 Data 점으로 남는다.
- 결손 한정 문구: 연결·포함 소스가 `error-*` 또는 `idle-stale`이고 결손 일수 ≥1이면 SyncState `caveats`에 `{code:"source_missing", provider, days}`를 싣는다. Today(10 §2.4 `stale`)와 부하 D2가 이 값을 쓴다.

---

## 4. 지표 표기·설명 규격

### 4.1 값 포맷 — §C4를 따르고, 이 영역에서 추가하는 것만
| 종류 | 규칙 | 예 |
|---|---|---|
| 동기화 시각 | 24h 이내: 상대(`3분 전`, `14시간 전`) + 툴팁 절대 KST. 그 이상: `9월 26일 20:56`. API는 오프셋 ISO만 보낸다 | `3분 전` |
| 데이터 기준일 | `9월 27일 데이터까지`(Pill은 `9/27`) | |
| 건수 | 천 단위 쉼표, 단위 명시 | `활동 1,203건`, `웰니스 890일` |
| 용량 | ≥1GB `n.n GB`, 그 외 `n MB` 정수 | `788 MB` |
| 진행 | 날짜 창 `3/12일`, 백분율 정수 | `42%` |
| 결과 카운트 | 종류별 `·` 구분, 0인 종류는 생략하되 모두 0이면 `새 데이터 없음` | `활동 1 · 웰니스 15일` |
| 기준값 | 심박 정수 `bpm`(LTHR 177.5 → `178`, 근거 시트에서만 소수), 역치 페이스 `m:ss/km` 단일 입력 마스크 | `4:23/km` |
| 재계산 전후 | 변화량 부호 필수, 시간은 `±m:ss`, 좋고 나쁨은 metric `higher_is_better`로 색(§C7) | `+0:39`(amber) |
| 웰니스 | 수면 시간 `h:mm`(`8:03`, `4h 14m` 금지), 걸음 쉼표, BB `100→13` | |
| 기준선 대비 | `28일 평균 72`, 편차 부호 `평균 −3`, Garmin 기준선이 있으면 `균형 범위 75–111` | |
| 오류 문장 | `무슨 일 · 영향 · 행동` 한 줄 + 코드는 펼침에만 | `Strava가 접근을 막았어요 · Garmin 데이터로 계속됩니다` |

### 4.2 ⓘ 설명(무엇 / 좋은 범위 / 내 값 / 행동) — 기준값 페이지
| 항목 | 무엇 | 좋은 범위·판단 | 내 값 해석(예) | 행동 |
|---|---|---|---|---|
| 최대 심박 | 도달 가능한 최고 심박. 존 경계의 기준 | 나이 공식보다 실측(대회 막판)이 정확 | 자체 추정 192(대회 2건) vs 입력 190 — 존 경계 1~2bpm 차 | 최근 5K~10K 레이스 막판 최고값이 더 높으면 갱신 |
| 젖산역치 HR | 1시간 지속 가능한 강도의 심박 | 최대 심박의 85~92% | 자체 178 vs Garmin 168: 9.5bpm 차 → Z2 상한이 달라짐 | 최근 대회·템포 기반 자체 추정 권장, 기기 값은 참고 |
| 역치 페이스 | 역치 강도의 페이스 | 10K 기록 페이스 + 5~10초/km 부근 | 4:23/km | 계획 처방 페이스(T)가 이 값을 쓴다 |
| 안정 심박 | 아침 휴식 심박 | 개인 60일 기준선 대비 +5bpm 이상 지속 시 피로 신호 | 41bpm, 기준선 −3 | 기기 값을 쓰고 직접 입력은 기기가 없을 때만 |

### 4.3 출처 배지·색
- 출처 배지는 §C6을 따른다. 기준값 3열 헤더가 곧 출처다(`RunPulse 계산`, `Garmin`, `직접 입력`). 오래된 기기 값(>30일)은 회색 + `오래된 값`이다.
- 상태색은 §C7 의미색만 쓴다: 정상 teal ●, 지연 amber ●, 오류 red ▲, 꺼짐/미연결 neutral ○, 진행 fg ⟳. **provider 색은 식별(카드 좌측 3px 막대·outline 배지)에만 쓰고 상태 표시에 쓰지 않는다**(ui F-UI-05). 작은 배지는 outline 변형(대비 ≥4.5:1)이다.
- 계획 비교의 위험도 색은 31 §4.2를 따른다. 미정의 토큰(`semantic-yellow`, `accent`)은 §C8의 Stylelint로 차단한다.

---

## 5. 차트 규격 — §C1 ChartScrub 준수, 영역별 적용

| 차트 | 위치 | 축·눈금 | 방향 | 상호작용 | 빈 데이터 |
|---|---|---|---|---|---|
| 커버리지 띠 | Data 개요·소스 상세 | 월 셀 12칸(높이 12px), 양끝 라벨 `25.10`·`26.09`(12px), 셀 농도 = 활동 수 5단 | 오른쪽 끝 = 이번 달 | 셀 탭 → 활동 월 필터 / 0건 셀 → 가져오기 시트. 셀 aria-label `2024년 4월 · 0건` | 소스 미연결: 띠 대신 `연결하면 표시돼요` |
| 웰니스 30일 추세 | 웰니스 일자 | 지표 칩으로 1개만 표시(개별 min–max 정규화 착시 제거). y nice ticks 3개, x 주 눈금 | RHR은 `invert`(낮을수록 좋음 = 위). HRV·수면 점수는 정방향 | C1 스크럽 + `그날 보기 ›`(`onPick`) + 선택일 세로선 | 점 <2개: `데이터 수집 중 (n/7일)` |
| 기준선 밴드 | 웰니스 추세(HRV·RHR) | Garmin 기준선 또는 개인 60일 밴드를 옅은 배경으로, 라벨은 우측 거터 | — | — | 기준선 없음: 밴드 생략 + 캡션 `기준선 계산 중` |
| 수면 단계 막대 | 웰니스 일자 | 가로 100% 누적, 구간 라벨 `h:mm`, 시각 축 취침→기상 | — | 구간 탭 → 툴팁 | 단계 없음: `수면 단계 없음(기기 미지원)` |
| 체력·피로 추이 | Story | 기간 + 앞 2주, §C1 그대로(폼 차트 컴포넌트 재사용) | 정방향 | 스크럽, 판독줄 | <28일: 10 §6 B7 문구 |
| 주별 거리 막대 | Story | y nice ticks(10/20/50km 단위), x `9/1주` | — | 막대 탭 → 활동 목록 주 필터 | 0주: 빈 막대 + `0` 라벨 |
| 강도 분포 막대 | Story | 가로 누적 Z1-2/Z3/Z4-5, 목표 80/20 표시선 | — | 구간 탭 → 해당 존 시간 목록 | 존 데이터 <50%: `존 데이터 부족`(0% 금지) |
| 진행 막대 | 동기화·작업 | 선형, 날짜 창 기준, 퍼센트 텍스트 병기 | — | — | 총량 모름: 불확정 막대 + 경과 시간 |

차트 색은 §C7 시리즈색만 쓴다. `Sparkline.svelte`의 하드코딩 hex(`#3b82f6`, `#10b981`)는 제거한다(ui F-UI-06).

---

## 6. 로딩·빈·오류 상태

### 6.1 전역 4분류(ux F-UX-05 채택) — 모든 v2 화면의 판정 규칙
공통 문법은 §C5(스켈레톤·진행바·블록 오류)를 따른다. 여기서는 **어떤 상태인지 판정하는 규칙**만 정한다. 판정 입력은 SyncState(`connected_count`, `first_sync_running`, `latest_data_date`)와 API 응답 코드다.

| 분류 | 판정 | 문구 형식 | 행동 |
|---|---|---|---|
| `empty-first` | 연결 소스 0 | `아직 연결된 기기가 없어요` | [기기 연결하기] → `/welcome` |
| `empty-syncing` | 연결 ≥1, 활동 0, 첫 동기화 진행 중 | `처음 가져오는 중 · 2026-03까지 · 활동 212` | 진행 막대, 완료 시 자동 갱신 |
| `empty-scope` | 데이터는 있으나 이 범위·필터에 없음 | `이 기간에 활동이 없어요` | [기간 넓히기] / [필터 해제] |
| `error` | API 실패(네트워크·5xx·타임아웃) | `불러오지 못했어요 · 서버 응답 없음` | [다시 시도], 3회 실패 시 `상태 보기 ›`(`?sheet=sync`) |

- `load`에서 예외를 삼켜 `null`로 두는 패턴(`today/+page.ts:32-36`, 보조 API `.catch(() => null)`)을 금지한다. 보조 블록 실패는 블록 자리에 `ErrorState compact`로 남기고 블록을 숨기지 않는다.
- 화면별 오류 문구 13종을 `ErrorState`/`EmptyState` 두 컴포넌트와 문구표 한 곳(`lib/states.ts`)으로 모은다.

### 6.2 블록별 상태(이 영역)
| 블록 | 스켈레톤 | 빈 상태 · 행동 | 오류 |
|---|---|---|---|
| SyncStatusPill | 회색 pill 폭 고정(레이아웃 점프 0) | 소스 0: `기기 연결 ›` | `상태 확인 실패 · 다시`(Pill 자체는 남김) |
| SyncPanel | 소스 4행 | 소스 0: 온보딩 카드 | 행 단위 오류(§3.2) |
| Data 개요 | StatTile 4 + 카드 4 | `empty-first` | 블록별 재시도 |
| 소스 상세 | 헤더 + 카운트 줄 | 미연결: 연결 폼 | 연결 확인 실패: 원인 문장 + [다시 확인] |
| 동기화 로그 | 5행 | `아직 동기화 기록이 없어요 · [지금 동기화]` | 재시도 |
| 내보내기 | 카드 4 | — | 작업 실패: 로그 행 red + [다시 만들기] |
| 가져오기 미리보기 | 표 스켈레톤 | 인식 0건: `인식한 활동이 없어요 · 지원 형식: zip, fit, gpx` | 파일 오류: 행 단위 사유 |
| 기준값 | 5행 | 자체 추정 없음: `대회 기록이 필요해요 · 대회 표시 ›` | 저장 실패: 입력 보존 + 인라인 |
| 웰니스 일자 | 카드 4 + 차트 240px | 그날 기록 없음: `9월 20일 웰니스 기록이 없어요` + 가까운 기록일 ‹ › | 재시도 |
| Story | 문단 3줄 + 타일 4 + 차트 | 그 기간 활동 0: `이 달은 기록이 없어요` + 이전/다음 유지 | 문단 실패 시 수치 블록만 표시 + 재시도 |
| 계획 비교 | 31 §6 | 31 §6 | 31 §6 |

### 6.3 전역 `routes/+error.svelte`(31 §6과 같은 파일)
셸 안(헤더·탭 유지)에 렌더한다. 아이콘 + 제목(`찾는 화면이 없어요` / `불러오지 못했어요`) + 설명 1줄 + 주 버튼(맥락별) + [Today]. HTTP 코드는 12px 각주로만 표시한다. 404는 가장 가까운 상위 경로 링크를 준다.

---

## 7. 변경 컴포넌트·API

### 7.1 프론트엔드(`frontend/src/`, 파일당 300줄 이하)
| 경로 | 구분 | 내용 |
|---|---|---|
| `app.html` | 변경 | `lang="ko"`, `viewport-fit=cover` |
| `routes/+layout.svelte` | 변경 | ☰ 좌측 활성화, Pill 우측, 사이드바 Data 항목·SyncBlock, safe-area, 진행바 |
| `routes/+error.svelte` | 신규 | §6.3(31과 공유) |
| `lib/stores/syncState.ts` | 신규 | `GET /data/sync-state` SWR(60s, 포커스 시 갱신), 실행 중엔 SSE 구독, 탭 복귀 시 폴링으로 복원 |
| `lib/components/shell/{SyncStatusPill,SidebarSyncBlock,MenuDrawer,SyncPanel}.svelte` | 신규 | §2.1~2.3, 상태 기계 §3.2 |
| `lib/components/{SubTabs,ErrorState,EmptyState,Toast,StatTile,DateStepper,WeekStrip}.svelte` | 신규 | SubTabs는 Library·Data 공용. Toast는 [되돌리기] 지원 |
| `lib/components/ProviderBadge.svelte` | 신규 | solid/outline(ui F-UI-05), §C6 |
| `lib/components/data/{SourceCard,SyncRunRow,SyncProgressRow,ExportCard,SettingRow,BaselineRow,RecomputeSummary,ImportPreview}.svelte` | 신규 | §2.4~2.6 |
| `lib/states.ts` | 신규 | 4분류 판정 + 문구표 |
| `lib/providerHint.ts`, `lib/healthNotice.ts`, `lib/asOf.ts` | 변경 | 문구 끝 `동기화 열기` 액션. `asOf`는 SyncState(`latest_data_date`)만 사용, 날짜만 비교 금지 |
| `routes/data/+layout.svelte`, `data/+page.svelte`, `data/sync`, `data/sources/[provider]`, `data/export`, `data/import`, `data/settings/{+page,profile,ai}` | 신규 | §2.4~2.5 |
| `routes/library/+layout.svelte` | 변경(20 설계) | 섹션 탭에 `이야기` 추가 |
| `routes/library/wellness/+page.ts` → `[date]/+page.{ts,svelte}` | 신규 | 무날짜 → 오늘로 redirect. `metrics_by_category` 렌더 |
| `routes/library/story/[period]/+page.{ts,svelte}` | 신규 | §2.8. `MonthNarrative.svelte`는 Today 요약 3줄 + `전체 보기`로 축소 |
| `lib/components/Sparkline.svelte` | 변경 | 하드코딩 hex 제거, C1 코어 사용 |
| `routes/welcome/+page.svelte` | 신규 | §2.10 |
| `lib/components/Icon.svelte` | 변경 | sync·source·export·import·settings·menu·chevron·check·alert·pause(§C8 목록에 추가) |

### 7.2 백엔드·데이터
| 항목 | 변경 |
|---|---|
| `sync_jobs` 확장(작업 원장) | 열 추가: `trigger`(auto/manual/range/onboarding/system), `started_at`, `finished_at`, `error_code`, `error_message_ko`, `counts_json`(`{activities_new, activities_updated, wellness_days, laps_backfilled, streams}`), `result_json`(재계산 전후 요약·내보내기 파일 목록), `params_json`. `job_type ∈ activity\|wellness\|range\|recompute\|export\|import`. **모든 동기화 경로**(수동 SSE `app.py:608-655`, `/trigger-sync-bg`, `auto_sync._trigger`, `sync.py`)가 원장에 쓴다. DDL은 `sync_jobs_schema.py`, 등록은 `/check-data-consistency` 대상 |
| `sync_state.json` | 쓰기 중단. 읽는 곳(`helpers.get_last_sync_at`)은 원장 파생 함수로 교체 |
| 오류 분류 | `src/sync/errors.py`(신규): HTTP·예외 → `auth_expired\|auth_revoked\|subscription_required\|rate_limited\|upstream_5xx\|timeout\|interrupted\|unknown`, 코드별 `message_ko`·`action`. 403이 `completed, count=0`으로 기록되는 경로를 제거한다(SYNC-ERROR-SURFACE) |
| 끈 소스 정리 | `sync_enabled=false`가 되면 해당 소스의 `pending`/`stopped` 작업을 `cancelled`로 전이한다(`bg_sync.py:460` 보완) |
| 상태 불일치 | `bg-sync/status`가 `status:completed`인데 `active:true`를 준다(garmin, 확인). SyncState는 원장 상태만 쓰고 `active`는 쓰지 않는다 |
| `data_service.py`(스텁 → 구현) | `sync_state()`, `sources()`, `summary()`. `check_*_connection` + 원장 + config `sync_sources` 조합 |
| `provider_status_service` | `last_synced_at` → `last_new_data_at`으로 개명(의미 교정), 오프셋 ISO |
| 기준값 | `profile_service.py`(신규): `overrides`·`source_choice`, 자체 추정(`/prediction/profile`)·기기 값 병합, 존·계획 엔진이 이 함수 하나만 읽는다(`planner_rules.py:195`, `zones_analysis.py:35` 교체). 키 이관 스크립트 |
| 재계산 | `GET /recompute-metrics`(부작용 GET) 폐기 → 원장 작업. 전후 대표 5지표 스냅샷 → `result_json` |
| 사용자 설정 | `ui_default`(v1/v2), `onboarding_step`를 사용자 config에 저장. 전역 `ui_default_global`(app config 1줄) |
| `/` 분기 | `app.py:305-307`: 사용자 `ui_default` → 없으면 전역값 → `/dashboard` 또는 `/v2/today`. 구 v1 URL 301은 G5에서 대응 화면이 있는 것만 적용 |
| OAuth 복귀 | `/connect/*` 콜백에 `return_to` 허용 목록(`/v2/data/sources/*`, `/v2/welcome`) |
| 내보내기 | `export_service.py`(신규): 빠른 CSV 3종(스트리밍), 아카이브 zip(테이블 CSV + `metric_store`(provider·formula_version·computed_at) + 원본 payload JSON + `manifest.json`), 7일 만료 |
| 가져오기 | 기존 `/import/*` 로직을 preview/commit 두 단계로 분리 |
| Story | `/today/narrative`를 `story_service`로 일반화: `scope=week\|block\|month`, 이전 동일 단위 Δ, 강도 분포, 대표 세션, 위험 최고, 예측 변화 |
| 웰니스 일자 | 응답에 `updated_at`(오프셋), `is_final`(다음날 04:00 이후), `baseline{avg_28d, garmin_range}`, `day_training[]` 추가 |

### 7.3 API 계약(신규 `/api/v1/data/*`, JSON, 쓰기는 POST/PATCH)

**`GET /api/v1/data/sync-state`** — 셸·Today·Library 공용 계약
```json
{"as_of":"2026-09-27T21:10:03+09:00",
 "latest_data_date":"2026-09-27",
 "overall":{"level":"ok|stale|error|running","label_ko":"3분 전 동기화","last_success_at":"2026-09-27T20:56:47+09:00"},
 "connected_count":3, "first_sync_running":false,
 "sources":[{"provider":"garmin","connection":"connected|expired|error|not_connected","enabled":true,
   "state":"idle-ok","last_attempt_at":"…+09:00","last_success_at":"…+09:00","last_new_data_at":"…+09:00",
   "last_error":null,"running":null},
  {"provider":"strava","connection":"connected","enabled":false,"state":"disabled",
   "last_success_at":"2026-06-23T23:13:16+09:00",
   "last_error":{"code":"subscription_required","message_ko":"Strava가 API 접근을 막았어요","action":"disable","at":"…"}}],
 "caveats":[{"code":"source_missing","provider":"intervals","days":2}],
 "open_errors":1}
```
- `POST /api/v1/data/sync` `{sources?:[…], mode:"incremental"|"range", from?, to?}` → `202 {runs:[{id, provider, state:"queued"}]}`. 이미 실행 중이면 `409 {code:"running"}`, 가드면 `429 {retry_after_sec, message_ko}`.
- `GET /api/v1/data/sync/stream`(SSE: `run_start`, `progress{provider, done_days, total_days, cursor_date}`, `run_done{provider, state, counts, error?}`) / `GET /api/v1/data/sync/status`(동일 내용 폴링).
- `POST /api/v1/data/sync/runs/:id/cancel` · `GET /api/v1/data/runs?type=&errors_only=&limit=`(원장 목록, 모든 작업 종류).
- `PATCH /api/v1/data/sync/auto` `{enabled, interval_h, window_days}` → 설정 + `next_run_at`.
- `GET /api/v1/data/sync/estimate?provider&from&to` → `{requests, rate_limit:{window_15m_left, daily_left}}`.
- `GET /api/v1/data/sources` · `GET /api/v1/data/sources/:p` → 위 source 항목 + `counts{activities, wellness_days, streams, laps}`, `coverage{first, last, months[]}`, `representative_metrics[]`.
- `PATCH /api/v1/data/sources/:p` `{sync_enabled}` · `POST /api/v1/data/sources/:p/connect` `{api_key?}` → 키 방식 `{ok, message_ko}`, OAuth `{redirect_url}` · `POST …/test` · `POST …/disconnect` `{keep_data:true}`.
- `GET /api/v1/data/profile` → `{rows:[{key:"hr_max", self:{value:192, basis:[activity_id…], at, confidence}, device:{value:null, provider, at}, manual:{value:190}, using:"self"}…]}` · `POST /api/v1/data/profile/preview` `{changes}` → `{zones_before, zones_after, affected_days, affected_metrics}` · `PATCH /api/v1/data/profile` `{changes, recompute:"none"|"90d"}` → `{job_id?}`.
- `POST /api/v1/data/recompute` `{scope:"90d"|"all"|"from", from?, reason}` → `202 {job_id}` · `GET /api/v1/data/jobs/:id` → `{state, progress, result:{before_after:[{slug, before, after, delta, status}], changed_days, formula_changes:[…]}}`.
- `POST /api/v1/data/export` `{kind:"quick_activities"|"quick_wellness"|"quick_load"|"archive", from?, to?}` → quick는 파일 스트림, archive는 `202 {job_id}` · `GET /api/v1/data/exports`(기록·만료).
- `POST /api/v1/data/import/preview`(multipart) → `{preview_id, recognized, period, duplicates, new, enrich}` · `POST /api/v1/data/import/:preview_id/commit` → `{job_id}`.
- `GET|PATCH /api/v1/data/settings/ai` → `{provider, key_state:"set|missing|invalid", scope:{activities_days:28, wellness:true, checkin_notes:false, gps:false}, usage_7d}`.
- `GET|PATCH /api/v1/me/preferences` `{ui_default:"v1"|"v2"}` · `GET|PATCH /api/v1/me/onboarding` `{step, done}`.
- `GET /api/v1/data/summary` → `{activities_unified, wellness_days, first_date, db_mb, formula_versions{}}`.

**확장**: `GET /api/v1/library/wellness?date=` + `updated_at, is_final, baseline, day_training[]`. `GET /api/v1/library/story?scope=month&id=2026-09` → `{period{start,end,prev}, paragraph, chips[], compare[{key, value, prev, delta_pct}], intensity{z12,z3,z45,coverage}, key_sessions[], risk_peak{slug,value,date}, prediction{start,end,drivers[]}, milestones[]}`. 계획 템플릿은 31 §7.2를 따른다.

---

## 8. 수용 기준

**셸·원장**
- [ ] 같은 시점에 Pill, 사이드바, Data 개요, v1 대시보드가 보이는 "마지막 성공" 값이 모두 원장 한 값과 같다. `sync_state.json` 쓰기 0회(grep).
- [ ] 수동·bg·자동·CLI 네 경로가 모두 원장 행을 남긴다(경로별 통합 테스트 4건).
- [ ] 403 응답을 주입하면 원장 `error_code=subscription_required`, 행 `error-access`, ☰ 배지가 뜬다. `completed, count=0`으로 기록되지 않는다.
- [ ] 모든 시각 필드는 오프셋 ISO다(API 스키마 테스트). 표시 상대 시각 오차 ≤1분.
- [ ] 소스를 끄면 그 소스의 대기 작업이 5초 안에 `cancelled`가 된다.
- [ ] Pill은 모든 v2 화면(390·1280)에 상시 표시되고, 탭 영역 ≥44×44, 대비 ≥4.5:1이다.

**흐름(과업 동작 수, 모바일 390, Today 출발)**
- [ ] T1 동기화 시점 확인 = 0동작, T2 지금 동기화 = 2, T3 기간 동기화 ≤5, T4 오류 인지·복구 ≤3, T5 새 소스 연결 ≤4 + OAuth(복귀 URL이 v2), T6 해제 = 3(보존/삭제 선택 포함), T7 내보내기 ≤3, T8 기준값 수정 ≤4(재계산 제안 포함), T9 다른 안 비교(활성 계획) ≤2(31), T10 지난달 이야기 = 2, T11 특정 날 웰니스 ≤3, T12 첫 사용자 첫 Today ≤8, T13 재시도 = 1.
- [ ] v2 안내 문구 3곳이 모두 `?sheet=sync`를 연다(비대화형 문구 0).
- [ ] 시트·드로어·Story 기간·웰니스 날짜 이동 후 뒤로가기는 한 단계씩 되돌린다. 새로고침하면 같은 상태가 복원된다.

**상태·반응**
- [ ] [지금 동기화] 누름 → pressed 피드백 ≤100ms, 행 `queued` 표시 ≤300ms.
- [ ] 인위 오류 3종(API 500, 네트워크 차단, 소스 401)에서 SvelteKit 기본 오류 화면 0, 버튼 없는 막다른 화면 0.
- [ ] `/today` 500일 때 "아직 데이터가 없습니다"가 아니라 `error` 분류가 표시된다.
- [ ] `sync-state` API ≤200ms, `data/sources` ≤300ms, 웰니스 일자 ≤300ms, Story 월 ≤800ms(현 narrative 520ms 기준).
- [ ] 스켈레톤 → 콘텐츠 전환의 CLS ≤0.05.

**데이터 정확성**
- [ ] 기준값 페이지에서 역치 페이스를 입력하면 계획 엔진이 그 값을 읽는다(`threshold_pace` 키 불일치 회귀 테스트).
- [ ] 재계산 완료 보고에 5지표 전후와 바뀐 날짜 수가 있다. 값이 바뀐 메트릭 상세에 재계산 이력 표식이 있다.
- [ ] 아카이브 zip의 `manifest.json` 행 수가 DB 행 수와 일치하고, 메트릭 CSV에 `formula_version`·`computed_at` 열이 있다.
- [ ] 웰니스 당일 화면은 `진행 중 · HH:MM 기준`, 과거 날은 `최종`을 표시한다.
- [ ] Story 월 수치가 `/library/activities?from&to` 합계와 같다(러닝만 집계, 10 설계의 규칙).
- [ ] 강도 분포 존 커버리지가 50% 미만이면 0% 막대 대신 `존 데이터 부족`을 표시한다.

**전환**
- [ ] `ui_default`를 바꾸면 새로고침과 다른 기기에서도 유지된다. 전역 롤백은 설정 1줄이고 재배포가 필요 없다.
- [ ] v1 헤더와 v2 드로어에 상대 UI로 가는 1탭 링크가 있다.

---

## 9. 구현 순서

| 단계 | 묶음 | 의존 | 규모 | 게이트 |
|---|---|---|---|---|
| **S0 셸 기반** | `lang="ko"`, safe-area, Icon 확장, `SubTabs`, `ErrorState`/`EmptyState`/`+error.svelte`(31 S2와 한 작업), Toast, ☰를 과도기 드로어(v1 링크 포함)로 활성화, v1 ↔ v2 상호 링크 | — | S | G0 일부 |
| **S1 전환 스위치** | `ui_default`(사용자) + `ui_default_global` + `/` 분기, 드로어 `이전 화면으로` | S0 | S | **G0** |
| **S2 작업 원장** | `sync_jobs` 확장 DDL, 네 동기화 경로 기록, 오류 분류, 끈 소스 정리, `sync_state.json` 파생화, `GET /data/sync-state`, `/data/runs`(ADR 선행) | — | M | G1 전제 |
| **S3 동기화 표면** | `syncState` 스토어, Pill·SidebarSyncBlock·SyncPanel, 상태 기계, `POST /data/sync`·SSE·status, 결과 토스트, 안내 3곳 연결, Today `caveats` 연동(10 S6) | S2 | M | **G1** |
| **S4 소스·동기화 페이지** | `/data`, `/data/sync`(기간·자동·로그·추정), `/data/sources/:p`(연결·재연결·제외·해제, OAuth `return_to`), `data_service` 구현 | S3 | M | G1 완성 |
| **S5 빈·오류·온보딩** | `states.ts` 4분류, `load`의 예외 삼키기 제거(Today·Library·Coach), 보조 블록 compact 오류, `/welcome` 4단계 | S3·S4 | M | **G2** |
| **S6 웰니스 일자** | 라우트·DateStepper·WeekStrip·기준선·`metrics_by_category`·추세 1차트, API 확장, 활동 상세 `이날 컨디션` | S0 | S | G4 일부 |
| **S7 Story 월** | `story_service` 월, `/library/story/:period`, Today 시트 축소, Library `이야기` 탭 | S0, 10 S(월간 집계 규칙) | M | **G4** |
| **S8 기준값·재계산** | `profile_service`, 키 이관, 기준값 페이지, preview, 재계산 원장 작업 + 전후 요약, 부작용 GET 폐기 | S2 | M | G2 권장 |
| **S9 내보내기·가져오기** | 빠른 CSV 3종, 아카이브 작업, 가져오기 preview/commit, 커버리지 공백 딥링크 | S2·S4 | L | G5 권장 |
| **S10 AI 설정·전송 고지** | `/data/settings/ai`, 전송 범위, Coach 라벨 사유(30 설계와 연결) | S0 | S | G5 권장 |
| **S11 Story 주·블록** | `scope=week\|block`, 블록 경계(31 phase) | S7, 31 S4 | M | — |
| 계획 비교 | 31 S2(리다이렉트·오류) · S6(시나리오·확인 시트·진입점) | 31 | — | **G3** |

### 9.1 v2 기본 진입 전환 게이트(ux F-UX-03 채택, 흐름 기준)

| 게이트 | 내용 | 통과 기준(검증 방법) | 롤백 |
|---|---|---|---|
| **G0 스위치** | 사용자 `ui_default`(기본 v1) + 전역 `ui_default_global` + 양방향 1탭 링크 | 두 방향 전환 1탭, 새로고침·다른 기기에서 유지 | 해당 없음 |
| **G1 데이터 루프** | S2~S4 | T1=0, T2=2, T4≤3, T5≤4+OAuth. 403·401 주입 시 배지·문장·행동 표시. 원장 경로 4종 기록 | 드로어 v1 링크 유지 |
| **G2 오류·빈** | S5(+S8 권장) | 인위 오류 3종에서 막다른 화면 0. 신규 계정 T12≤8 | — |
| **G3 계획 흐름** | 31 S2·S5·S6 | T9≤2, v1 `/training` 흐름 7종(완료/건너뜀 교정, 세션 편집, 목표 수정, 재생성, 전체 일정, 내보내기, 훈련 환경)에 v2 대응 경로가 있다 | — |
| **G4 되돌아보기** | S6·S7 | T10=2, T11≤3, URL 공유·뒤로가기 정상 | — |
| **G5 기본 전환** | `ui_default_global=v2`. 구 URL 301은 v2 대응이 있는 것만. 대응이 없는 v1 기능(`/dev` 등)은 v1 유지 + 드로어 `고급 도구` | 2주 운용: v1 복귀 클릭 수·사유(1문항) 로그 수집, 복귀율 <10%. 첫 진입 1회 안내 `새 화면으로 바뀌었어요 · 동기화·설정은 ☰ · 이전 화면으로 [↩]` | **전역값 1줄을 v1로**(재배포 없음). 개인은 드로어 1탭 |
| **G6 v1 제거** | v1 라우트 제거 | v1 복귀 0건이 2주 지속 + §11 계승 목록 P0·P1 전부 v2 제공 | 제거 전 태그 |

- 07 로드맵의 "쿠키 `use_v2`"는 계정 설정으로 바꾼다(여러 기기 일관, 코드에 쿠키 구현 0건). `DECISIONS.md` 기록 대상.

---

## 10. 발견 → 설계 추적표

| 발견 | 요지 | 설계 위치 | 상태 |
|---|---|---|---|
| F-DATA-01 | 마지막 동기화 3종 불일치, as-of 날짜만 비교 | §1 판단, §7.2 원장, §7.3 sync-state, §2.1 Pill, §8 셸·원장 | 반영(S2·S3) |
| F-DATA-02 | 소스 실패 비가시, 결손 = 휴식일 | §3.2 상태 기계·caveats, §7.2 오류 분류·끈 소스 정리 | 반영(S2·S3) |
| F-DATA-03 | 동기화 권유 문구가 막다름 | §2.2 SyncPanel, §3.1 안내 3곳, §8 | 반영(S3) |
| F-DATA-04 | 연결을 데이터 유무로 추정, Runalyze 소멸 | §2.4 SourceCard 두 축, §7.3 sources, 커버리지 띠 | 반영(S4) |
| F-DATA-05 | 내보내기가 활동 CSV 수준 | §2.4 내보내기, §7.2 export_service, §8 manifest | 반영(S9) |
| F-DATA-06 | 기준값 3벌, 역치 페이스 키 불일치 | §2.5, §4.2, §7.2 profile_service, §8 회귀 테스트 | 반영(S8) |
| F-DATA-07 | 재계산이 설명 없는 버튼, 부작용 GET | §2.6 요약, §7.3 recompute·jobs, §1 제안형 | 반영(S8) |
| F-DATA-08 | 아카이브 임포트 부재 | §2.4 가져오기 4단계, 커버리지 0건 셀 → 가져오기 | 반영(S9) |
| F-DATA-09 | 비교 1안·예측 15분 차·위험 모순 | §2.9 → 31 §4.1 R10·§2.6 | 반영(31 S2·S6) |
| F-DATA-10 | Story 주·블록 부재 | §2.8 단위 토글·6요소, §7.3 story | 반영(월 S7, 주·블록 S11) |
| F-DATA-11 | 웰니스 일자 라우트·측정 시각 없음 | §2.7 헤더 `갱신·최종/진행 중`, §7.2 `updated_at·is_final` | 반영(S6) |
| F-DATA-12 | AI 제공자·전송 범위 비가시 | §2.4 설정 AI, §7.3 settings/ai | 반영(S10). Coach 라벨 사유 문구는 30 설계와 연결 |
| F-DATA-13 | 범위·주기·종류별 카운트 없음 | §2.4 동기화(추정·자동 행), §4.1 결과 카운트, §7.2 `counts_json` | 반영(S2·S4) |
| F-UI-01 | ☰ 비활성인데 활성처럼 보임 | §2.1·2.3, S0 과도기 드로어 | 반영(S0) |
| F-UI-02 | 비교 400 원문·1장·미정의 토큰 | §6.3 +error, §2.9 → 31, §4.3 Stylelint | 반영(S0·31) |
| F-UI-03 | 동기화 출처 3종, 시간대 불명 | §7.3 SyncState(오프셋 ISO), `latest_data_date` 분리 | 반영(S2) |
| F-UI-04 | as-of가 Today 11px에만 | §2.1 Pill 전역, `asOf.ts` 변경, 날짜 포맷 §C4 | 반영(S3) |
| F-UI-05 | provider 색 대비 미달 | §4.3 상태 = 의미색, ProviderBadge outline, §C6 | 반영(S0·S4) |
| F-UI-06 | 웰니스 날짜 이동·차트 문법·hex | §2.7, §5 추세 1차트·C1, Sparkline 변경 | 반영(S6) |
| F-UI-07 | Story 시트·전폭·24px 버튼·빈 추세 | §2.8 라우트, 44px 이동, §5 추이 차트 | 반영(S7) |
| F-UI-08 | 사이드바 공백·☰ 위치·lang·safe-area·아이콘 | §1 좌측 ☰, §2.1, §7.1 app.html·Icon | 반영(S0). ☰ 위치는 DECISIONS 기록 |
| F-UI-09 | 서브탭 복제 | §7.1 SubTabs 공용, `+layout` 1회 | 반영(S0) |
| F-UX-01 | 데이터 루프 미완결, 상호 링크 0 | §2.2·2.3, §3.1, S0 상호 링크, G1 | 반영(S0·S3·S4) |
| F-UX-02 | 동기화 피드백 모델 없음 | §3.2 상태 기계 13상태, 토스트, SSE/폴링 복원 | 반영(S3) |
| F-UX-03 | 롤백 스위치 없음, 게이트 비검증 | §9.1 G0~G6, §7.2 `/` 분기, §8 전환 | 반영(S1) |
| F-UX-04 | 비교 진입 0·단계 누락·즉시 생성 | §2.9 → 31 §2.6·§3(⋯·확인 시트·3단계). "지금 계획" 열은 31 S6 추가 제안 | 반영(31) / "지금 계획" 열 보류(31 소관 결정) |
| F-UX-05 | 오류·빈 상태 혼재 | §6.1 4분류, §6.3, `states.ts`, `load` 예외 삼키기 금지 | 반영(S5) |
| F-UX-06 | 온보딩 없음 | §2.10 4단계, 1회성 요약 카드 | 반영(S5) |
| F-UX-07 | Story URL·재방문 없음 | §2.8 라우트·`goto` 이동·복사, Library `이야기` 탭 | 반영(S7) |
| F-UX-08 | 웰니스 오늘만, 들고 나는 경로 없음 | §2.7, §3.1 진입(활동 상세·Today 칩·Story)·이탈(D2·활동) | 반영(S6) |
| F-UX-09 | 연결·재연동·해제 흐름 미정의 | §2.4 소스 상세, §3.1 OAuth `return_to`·제외/해제 분리·보존 선택 | 반영(S4) |
| F-UX-10 | 내보내기·설정·재계산 결과 피드백 없음 | §2.4 파일 목록·기록, §2.5 영향 미리보기, §2.6 요약 | 반영(S8·S9) |
| F-UX-11 | 드로어 빈도 반영 | §2.3 빈도순, §1 판단 | 반영(S0·S3) |
| F-UX-12 | 동기화 signature moment | §3.2 통합 토스트 | 반영(S3). 판단 지표 변화 계산은 Today 폼 값 재사용 |

---

## 11. v1 → v2 계승 목록 (data §A · ui §3 · ux §C 통합)

우선순위: **P0** = G1~G2 전(데이터 루프 필수) · **P1** = G5 기본 전환 전 · **P2** = G6 v1 제거 전 · **P3** = 이후.

| # | 기능(v1 위치) | v2 위치 | 우선 | 재사용 API·로직 | 계승 시 바꿀 점 |
|---|---|---|---|---|---|
| 1 | 헤더 "마지막 동기화 + 🔄"(`/dashboard`) | 셸 Pill → SyncPanel | P0 | 원장 파생 `sync-state` | 헤더는 상태만, 실행은 패널에서. 값은 원장 한 곳 |
| 2 | 소스별 연결 카드(상태 pill·조치 문구·재연동·해제)(`/sync`) | `/data` SourceCard, `/data/sources/:p` | P0 | `check_*_connection`, `/connect/*` 콜백(`return_to`) | 토큰·파일 경로 비노출, 해제는 확인 + 보존/삭제 선택, 원인과 맞는 문구 |
| 3 | 요약 배너 "3/4 연결 · 소스별 점" | SidebarSyncBlock, 드로어 1행 | P0 | `sync-state` | 점에 모양 병기 |
| 4 | 동기화 대상 체크박스(29f82ef) | 소스 상세 토글, 패널 [동기화에서 제외] | P0 | config `sync_sources`, `POST /sync/sources` → `PATCH /data/sources/:p` | 끈 소스 대기 작업 cancelled. 경고색 없음 |
| 5 | 기본/기간 동기화 + 소스별 SSE 진행 | SyncPanel, `/data/sync` | P0 | `bg_sync`, `/trigger-sync-stream` 이벤트, `sync_policy` 가드 | 13상태 행 표시, 결과 토스트, Today 무효화, 가드 카운트다운 |
| 6 | 자동 동기화 주기·범위·마지막 실행 | `/data/sync` 자동 행 | P1 | `auto_sync`, `/sync/auto-sync-settings` → JSON PATCH | "다음 실행" 추가, 자동 실패도 원장·배지 |
| 7 | 프로필(최대심박·주간 목표·역치 페이스)(`/settings`) | `/data/settings/profile` | P1 | `/prediction/profile` + 신규 `profile_service` | 3열 기준값 + 사용 중 선택, 키 통일, `m:ss` 단일 입력, 영향 미리보기 |
| 8 | 메트릭 재계산 90일/전체(동기화·설정 중복) | 기준값·가져오기 뒤 제안, `설정 › 고급` 1곳 | P1 | 재계산 로직 → 원장 작업 | 부작용 GET 폐기, 전후 요약, 중복 배치 금지 |
| 9 | 활동 CSV(`/activities/export.csv`) | `/data/export` 빠른 CSV | P1 | 기존 엔드포인트(초기 링크) → `export_service` | 통합 대표값 + 소스별 열, 사람용·기계용 열 |
| 10 | 계획 ICS(`/training/export.ics`) | `/data/export` 카드 + 31 계획 `⋯`(추가 제안) | P1 | 기존 엔드포인트 | 구독 URL 복사 |
| 11 | 어제 훈련 확인 `[완료][건너뜀]`(`/training`) | Today done 상태·세션 상세(10·31) | P1 | 31 `workouts/:id/action` | 자동 매칭 결과 먼저, 교정만 받기, 건너뜀 사유 1탭 |
| 12 | 세션 ✓/↩ 토글·수정·삭제 | 31 계획 상세 행 `⋯` | P1 | 31 §7.2 | 삭제는 되돌리기 토스트 |
| 13 | 목표 수정 위저드·재생성·전체 일정 | 31 `⋯` 계획 설정(replan-preview)·타임라인 | P1 | `plan_template_service`(31 R10) | 적용 전 미리보기, 완료 기록 보존 고지 |
| 14 | 훈련 환경 설정(휴식·롱런 요일) | 31 마법사 ② + 계획 설정(같은 폼) | P1 | 기존 설정 저장소 | 설정 화면에서 떠넘기는 안내 금지 |
| 15 | AI 제공자·키 관리 | `/data/settings/ai` | P1 | `coach_service` provider 체인 | 전송 범위 체크리스트, 연결 테스트, 라벨 사유 |
| 16 | 레포트 기간 + "이전 동일 기간 대비" | Story ② 비교 | P1 | `/today/narrative` → `story_service` | 기준 기간 명시, 부호·의미색 |
| 17 | 레포트 TIDS·위험 지표 평균/최고·"적정 ≤1.30" 병기 | Story ③⑥, StatTile 보조줄 | P2 | 기존 계산 | 0.0% 결함 계승 금지, 좋은 범위 병기를 U5 표준으로 |
| 18 | 레포트 "요약 복사" | Story `텍스트로 복사` | P2 | story API 문단 | 복사 완료 토스트 |
| 19 | 계획 → Garmin 푸시·CalDAV(`📤 ▾`) | 31 계획 `⋯ 내보내기`(추가 제안) | P2 | `/training/push-garmin`, `/training/push-caldav` | 전송 결과(성공 N·실패 사유) |
| 20 | Strava zip·FIT/GPX 임포트 | `/data/import` | P2 | `/import/*` 로직 → preview/commit | 업로드 전 미리보기(중복·보강), 원장 진행 |
| 21 | 활동 "동일 활동 묶기"·셀별 소스 배지 | 활동 상세 소스 탭 [묶기/분리](20 설계) | P2 | `/activities/merge`·`ungroup` | 결과 미리보기 + 되돌리기 |
| 22 | 외부 AI 연동(프롬프트 복사) | Coach 대화 `⋯ 외부 AI로 가져가기`, 설정 AI | P2 | 기존 프롬프트 생성 | 복사 전 전송 범위 미리보기 |
| 23 | 고급 연동(MCP/ngrok) | 설정 AI › 고급 | P3 | MCP 도구 14종 | 연결 상태·마지막 접근 시각 |
| 24 | 시스템 정보(DB·공식 버전) | `/data` StatTile, 설정 › 시스템 | P2 | `data/summary` | 경로 비노출, 공식 버전은 §C6 배지와 연결 |

**계승하지 않을 것**: 토큰·DB 파일 경로 노출, 다른 화면으로 떠넘기는 안내("/settings에서 입력하세요", "훈련 탭으로 이동했습니다"), 같은 기능의 중복 배치(재계산), 원인과 다른 상태 문구("토큰 만료 — 자동 갱신"), 확인 없는 연동 해제, 실행 후 결과 요약 없는 화면 재로딩, 부작용이 있는 GET, 이모지 아이콘.
