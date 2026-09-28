# UX 리뷰 로드맵 구현 진행 (체크포인트)

세션 한도·재시작 대비 재개용. 로드맵 원본: `99-summary.md §7`, 결정: `../DECISIONS.md [P7-UX-REVIEW-0928]`.

## 작업 규칙
- 작업 위치: worktree `/home/ubuntu/projects/RunPulse-p0` (브랜치 `claude/project-thread-vgunp6`).
  메인 폴더 `/home/ubuntu/projects/RunPulse`는 운영 컨테이너가 `--reload`로 마운트 → 직접 편집 금지.
- 운영 반영: 메인 폴더 `renew/data-architecture`에 ff 병합 → `frontend`에서 `npm run build` → (Dockerfile 변경 시) `docker compose build && up -d`.
- 테스트: `$V -m pytest tests/`(venv: 스크래치 `venv`, 없으면 `python3 -m venv` + `pip install -r requirements.txt pytest`), `cd frontend && npm run test:unit && npm run check`.
  기존 실패(무시): `test_plan_service` 2건, worktree에서 `test_autopilot_run_unit` 3건.
- 실 DB 변경 전 백업: `data/users/pansongit@gmail.com/running.db` → `running.db.bak-<날짜>-<사유>`.
- 한도(429) 걸리면 해제 시각 직후로 재개.

## 상태
| 단계 | 상태 | 커밋/메모 |
|---|---|---|
| Phase 0 핫픽스 | 완료·운영 반영(2026-09-28 08:40) | d31511b |
| 1-1 부하 모델 재기준화(PMC α=1/τ, TRIMP 계수, 재계산) | 완료·운영 반영(2026-09-28 12:45, 백업 `running.db.bak-20260928-pre-pmc-v2`) | d43dedf. 남음: Today 1회성 변경 알림(10 S0 명세) — 2-1 공통 규격 때 함께 |
| 1-2 등급 SSOT | 완료·운영 반영(2026-09-28 13:30, bbb66de) | `src/metrics/bands.py`, API status·status_label, 프론트 등급표 4벌 제거, consistency 검사 17. 남음: formChart 레이스 최적 음영 [5,25] 상수(시각 밴드) |
| 1-5 이행 재정의 | 완료·운영 반영 | `src/training/week_compliance.py`(R1 유효 계획·R2 분모·R3 세 수치·R5 라벨, 읽기 시점 계산), API `compliance`·`week.days`, 계획 화면·NextSessionCard. 보류: R4 매칭 게이트(재매칭 = 실 DB 변경), R9 CTL 궤적, R5 강도 판정은 평균 페이스 근사(스트림·HR존 미사용) |
| 1-6 동기화 원장 | 완료·운영 반영 | `sync_state_service`·`GET /api/v1/data/sync-state`, `get_last_sync_at` 원장 파생. 보류: sync_jobs 열 확장(error_code 등)·4경로 오류 기록(Strava 403이 completed로 남는 문제 = SYNC-ERROR-SURFACE), 프론트 표면(4-1) |
| 1-3 활동 파생 수치 | 완료·운영 반영(2026-09-28 18:07, 백업 `running.db.bak-20260928-pre-group-once`, 전체 재계산 426초) | 68e7635 | RE 선수 최대심박+스트림 존(conf 0.85/폴백 0.6 숨김), Friel 디커플링(백엔드 단일), TE Garmin 구간, 이동시간 스플릿·⏸, 활동 VDOT 대회·템포만 표시, 소스 비교 캐노니컬·comparable·항목별 임계·케이던스 정규화. 보류: 날씨 category 백필·형제 고유 메트릭 병합·PB 공식 기록(S1 나머지), providers `unit` 세부 |
| 1-4 그룹당 1회 계산 | 완료·운영 반영(같은 재계산) | edd2d52. 운영: 사본 RunPulse 행 0, RE 폴백 341→2, 17414 RE 302→27.7 | `src/utils/canonical.py`, CalcContext `get_group_metric`·`get_group_streams`, 엔진 캐노니컬만 계산·`prune_noncanonical_runpulse`, 상세·소스 비교 캐노니컬 RunPulse 값, consistency 18·19. 남음: 재매칭 시 그룹 재계산 트리거(현재는 다음 재계산 창에서 정리), C4 매트릭스 쌍 비교(3-8) |
| 1-7 GAP v2 | 완료·운영 반영(같은 재계산) | 8d2b9ad. Garmin GAP 대비 중앙 오차 평지 0.6초/km·언덕 4초/km(n=258) → Minetti 유지 | 고도 30m 창 경사, 곱셈 보정, 정지 제외, 경사 없으면 미산출. **설계 예시 4:25(5%)는 Minetti가 아니라 경험 모델 값** — Garmin GAP 대비 오차로 모델 판단 필요. 남음: Garmin gap_speed_ms 소스 GAP 저장(④) |
| 2-1 공통 규격(1차) | 진행 중·브랜치에만 있음(운영 미반영) | 아래 "2-1 세부" 참조. D1a~D1e 중 D1b(델타 토큰)·D1c(거리 소수 2자리 예외)·D1e(★ 아이콘) 반영, D1d(활동 scope `@a{id}`)는 §C3.3 드릴다운 URL 작업(2-5)과 함께 할 예정이라 보류 |
| 2-5 분해 v2 API(백엔드만) | 진행 중·브랜치에만 있음(운영 미반영) | 사용자 확인(2026-09-28 "오케이") — 아래 "2-5 세부" 참조. 프론트 DrillPanel/BreakdownView 재작성은 별도 라운드 |

### 2-1 세부 (커밋 예정)
- **폰트 self-host**: `static/fonts/{inter-variable,jetbrains-mono}.woff2`(jsdelivr fontsource 라틴 서브셋 — 한글 글리프 없음, 시스템 폰트 폴백), `layout.css`에 `@font-face`+`--font-sans`, `body`에 적용.
- **토큰**(`layout.css`): `--color-status-{danger,caution,neutral,good,great}`(기존 semantic-* 재매핑, 프론트 경계값 없음), `--color-delta-{better,worse}`(D1b), `--color-series-{1,2,3}`, `.num{ tabular-nums }`.
- **format.ts §C4**: `formatDistance`에 `decimals` 옵션(D1c, 기본 1·활동 랩 표는 2) + <1km는 `n m`(기존엔 항상 km였음 — 버그 수정), 신규 `formatLoad`·`formatForm`/`formatFormDetail`·`formatRatio`·`formatPercent`·`formatPercentile`·`formatScore`·`formatHeartRate`·`formatChange`·`formatTimeDiff`·`formatPrediction`·`formatDateLong`·`formatDateShort`, `MINUS`(U+2212) 상수. 테스트 `tests/format-c4.test.mjs`(11건).
- **Icon.svelte §C8**: 아이콘 3종(today/library/coach) → 20종으로 확장(`metric,activity,note,target,trophy,refresh,warning,close,menu,chevron,check,arrow-up,arrow-down,more,info,search,source-primary`). 타입은 `lib/icon.ts`의 `IconName`으로 분리(다른 모듈과 공유).
- **이모지·문자 아이콘 전면 제거**(§C8 "이모지·✕☰⚠ 금지" — RC6/F-UI-06): `EvidenceQuote.svelte`(⋯🏃📝📊 → Icon), `MilestonesPanel`/`MonthNarrative`/`Today` 마일스톤 아이콘(🎯🏃🔄🔖 → `lib/milestoneIcon.ts` 공유 매핑 + Icon), 상단 `☰`(`+layout.svelte`), 닫기 `✕` 4곳, 경고 `⚠` 5곳(`NextSessionCard`·계획 상세·`ProviderComparison`×3·활동 목록 플래그), 대표 소스 `★`→`Icon name="source-primary"`(D1e, `ProviderComparison.svelte`).
- **EvidenceQuote.svelte → §C2 DrillChip/InfoTag 패턴**: 기존 컴포넌트가 이미 C1(구 번호) 근거 칩 역할을 하고 있어 신규 컴포넌트를 병렬로 만들지 않고 그 자리에서 규격 반영 — `onOpen` 있으면 DrillChip 스타일(44px 히트, `fg-secondary/40` 테두리, 값 `.num` semibold, 끝에 `›` 아이콘, `active:scale-[.97]`, focus ring), 없으면 InfoTag(테두리·`›` 없음). Props(`EvidenceQuoteProps`) 불변이라 4개 소비처(Today/MonthNarrative/Coach thread/RecommendationCard) 수정 불필요.
- **검증**: `npm run test:unit`(206 pass, 신규 11건 포함) · `npm run check`(0 errors, 기존 경고 15건 그대로) · `npm run build`(성공, 폰트 파일 `build/fonts/`에 포함 확인) · `npm run preview`로 실제 서빙 확인(`/v2/today` HTML에 이모지 0건, 폰트 `Content-Type: font/woff2` 정상).
- **§C5 진행바·스켈레톤**(2차 커밋): `ProgressBar.svelte`(`$app/state`의 `navigating`, 150ms 지연 후 표시, `+layout.svelte`에 배선) + `Skeleton.svelte`(text/circle/chart/chip 4종 프리미티브, shimmer 1.2s, `prefers-reduced-motion` 정지). 아직 화면에 실제로 붙이진 않음(로딩 상태를 스켈레톤으로 바꾸는 작업은 각 라우트 손대는 범위라 3-x 재구성 때 자연스럽게 적용 — 지금은 컴포넌트만 준비).
- **§C6 출처 배지**(2차 커밋): `SourceBadge.svelte` 신규(`계산`/`직접 입력` 중립 배지). **provider(기기) 배지는 그대로 둠** — 기존 `providerBadgeClass`(14개 소비처)가 배경 채움+흰 글자라 §C6·F-UI-05가 지적한 대비 문제(예: `runpulse` 회색 위 흰 글자 ~3.9:1, 4.5:1 미달)가 실재하지만, 색을 바꾸려면 dataviz 팔레트 검증(대비·색각 시뮬레이션)이 먼저 필요해서 이번엔 손대지 않음 — 별도 항목으로 남김.
- **남음(2-1 나머지)**: D1d 활동 scope 토큰(§C3.3, 2-5와 함께), provider 배지 대비 재검토(dataviz 팔레트 검증 필요), Stylelint(`value-no-unknown-custom-properties`) — 이 리포에 Stylelint 자체가 아직 없어 신규 도입 필요.

| 2-2 셸 기반(40:S0) | 진행 중·브랜치에만 있음(운영 미반영) | 아래 "2-2 세부" 참조. S1(전환 스위치 `ui_default`)은 범위 밖(D6 계정 설정 필요, 별도) |

### 2-2 세부
- `app.html`: `lang="ko"`, `viewport-fit=cover`.
- `+layout.svelte`: safe-area(헤더 top, 하단 탭바 bottom), ☰를 좌측으로 이동해 활성화(기존엔 우측·disabled) — 40 design §2.1 "좌측 ☰·우측 Pill" 결정 반영(Pill 자체는 SyncState 프론트 배선이 있는 Phase 4-1 몫이라 아직 없음).
- `MenuDrawer.svelte` 신규 — **과도기 드로어(스코프 판단)**: 40 design 최종안(①동기화 요약 ②소스 연결 ③내 데이터 ④설정 ⑤가이드 ⑥로그아웃)은 SyncState 프론트 연동이 있어야 하는 Phase 4-1 몫이라, 지금은 "과도기(G1 전)" 문구가 명시한 v1 링크만 담음 — 대시보드·활동·웰니스·훈련·레이스·AI 코치·신발(빠른 이동) + 동기화·설정·가이드·CSV 내보내기(데이터·설정) + 계정 전환. v1 경로는 `data-sveltekit-reload`로 전체 새로고침. **이 스코프 좁히기는 설계 문서가 명시적으로 결정한 사항이 아니라 이번 세션의 판단** — 사용자가 과도기 드로어에 동기화 요약까지 지금 넣길 원하면 후속 지시 필요.
- `+error.svelte` 신규(§6.3) — 셸(헤더·탭) 유지, 404는 상위 경로로, 그 외는 다시 시도 + Today 링크.
- `ErrorState.svelte`/`EmptyState.svelte`/`Toast.svelte`/`SubTabs.svelte` 신규(§C5·§7.1) — 전부 프레젠테이션 컴포넌트만, 아직 소비처 없음(다음 단계에서 각 화면에 배치). `lib/states.ts`(4분류 판정)는 SyncState 의존이라 이번엔 미작성.
- 검증: `npm run check`(0 errors) · `npm run build`(성공) · `npm run test:unit`(206 pass, 회귀 없음).
- 남음: `ui_default` 전환 스위치(S1, 계정 설정 스키마 필요 → D6과 함께), MenuDrawer를 실제 SyncStatusPill로 교체(Phase 4-1), ErrorState/EmptyState를 각 라우트 로딩 실패 지점에 실제로 배선.

| 2-4 ChartScrub 코어(1차) | 진행 중·브랜치에만 있음(운영 미반영) | 사용자 확인(2026-09-28 "권장안으로 하고") — 2-3(계정 설정 스키마 필요)은 보류, 스키마 안 건드리는 2-4부터 진행 |

### 2-4 세부 (1차 — 순수 함수만)
- `lib/chart/scrub.ts` 신규: `niceTicks`(§C1 "1·2·2.5·5×10ⁿ", 3~5개), `clamp01`, `nearestIndexByFraction`, `axisDateLabel`(기간별 x축 라벨 규칙). 테스트 `tests/chart-scrub.test.mjs`(5건).
- 검증: `npm run test:unit`(211 pass) · `npm run check`(0 errors) · `npm run build`(성공).

### 2-4 세부 (2차 — ChartScrub.svelte + Sparkline 첫 적용)
- 사용자 확인(2026-09-28 "오케이"): 목록형 화면(`library/metrics`)의 스파크라인은 지금은 비인터랙티브로 유지, 상세 화면 5곳만 인터랙티브로 전환. 그 목록 화면 재구성(로드맵 3-7)에서 재검토.
- `ChartScrub.svelte` 신규: 포인터(hover 미리보기/click 고정/같은 점 재탭 해제/drag 스크럽 — pointerup에서 해제하지 않아 "손을 떼도 유지" 충족), 키보드(←/→ 1점, Shift+←/→ 7점, Home/End, Esc). 렌더링은 호출부 snippet에 위임(`children(index, pinned)`).
- `Sparkline.svelte`에 `interactive`·`dates`·`formatValue` prop 추가(기본 `interactive=false`로 기존 동작 100% 보존) — true면 ChartScrub로 감싸고 세로선+작은 툴팁(값+선택 시 날짜)을 그린다.
- 적용 5곳: 웰니스 30일 트렌드(수면 점수·HRV·UTRS, `library/wellness/+page.svelte`), 활동 상세 페이스·심박(`library/[id]/+page.svelte`, `formatPace`/`formatHeartRate`로 툴팁 포맷), Today L2 월간 CTL·ATL(`MonthNarrative.svelte`, `formatLoad`로 포맷 + 날짜 추가 수집). 색상도 이 김에 미정의 CSS 변수(`var(--color-accent)`, `var(--color-semantic-yellow, ...)`  — §C8이 금지하는 미정의 토큰)를 `--color-series-1`/`--color-semantic-amber`로 교체.
- **의도적으로 안 한 것**: (1) FormChart·TrendChart(날짜 기반 다계열)는 `formChart.ts`/`trendChart.ts`의 기존 xFrac·nearest 로직을 걷어내는 게 이 코어 마이그레이션의 본 목표인데, 축이 다계열·날짜형이라 Sparkline보다 복잡해 별도 단계로 분리. (2) 판독줄 `aria-live` 낭독(§C1)은 `aria-valuenow`로 근사만 함 — 스크린리더 실기기 확인 못 함.

### 2-4 세부 (3차 — 스트림 탭 마이그레이션 + 사용자 피드백 2건 기록)
- `library/[id]/streams/+page.svelte`: 자체 구현이던 스크럽(포인터 기반, 5개 스택 차트 동기화)을 `ChartScrub`로 교체. 기존 버그였던 "`pointerleave`에서 해제 → 모바일에서 손 떼면(=leave) 사라짐"이 해소됨(이제 pinned면 유지) + 키보드 내비게이션이 새로 생김(이전엔 전혀 없었음). 판독줄·커서 라인 렌더링은 그대로, `scrubIndex`/`scrubFrac` 로컬 상태와 `onPointerMove`/`onPointerLeave` 핸들러는 전부 제거(→ `streamAxis.ts`의 `indexAtFraction` import도 제거, 이 파일의 마지막 사용처였음).
- **사용자 피드백 2026-09-28 09:50** — "목록 화면이 의미 없는 나열이 되지 않을지" 지적(`library/metrics`, 스파크라인을 목록에서만 비활성화하기로 한 직후 나온 질문). 검토 결과: 이미 "핵심 지표" 히어로 섹션(예측 4종+CTL/TSB/UTRS/CIRS)과 카테고리 접기가 있어 완전한 무차별 나열은 아니지만, 히어로 밖 ~40여 개 카드는 정렬이 registry 순서 고정이라 그날 의미 있게 움직인 지표가 위치상 묻힐 수 있음 — 타당한 지적. **지금 구현하지 않고 사용자 지시대로 설계 보완 항목으로 기록**: `99-summary.md §8.5`(보류 항목 표에 신규 행) + `21-library-metrics/design.md §11`(해당 절에 3b 항목 추가, 3-7 착수 시 여기서 정렬 알고리즘 설계). 21-library-metrics §11 항목 3(카드 스크럽 충돌)도 이번 사용자 확인으로 "해소"로 갱신.
- 검증: `npm run check`(0 errors) · `npm run build`(성공) · `npm run test:unit`(211 pass, 회귀 없음).

### 2-4 세부 (4차 — FormChart·TrendChart 마이그레이션, 2-4 사실상 완료)
- `FormChart.svelte`(피트니스·폼 시그니처 차트): 자체 포인터 핸들러 제거, `ChartScrub` 도입. t0~t1 사이 일수를 `pointCount`로 근사해 키보드 ←/→가 하루씩 움직이게 함 — 값 조회(`nearestByFrac`)는 그대로 frac 기반이라 `formChart.ts`는 안 건드림. 모바일에서 손 떼면 판독줄이 "오늘"로 되돌아가던 문제 해소(이제 pinned 유지).
- `TrendChart.svelte`: 동일 패턴(day-count → pointCount). 기존 `interactive` prop은 유지하되(내부적으로 `interactive=false`면 ChartScrub 자체를 안 씌움 — 완전 정적 렌더가 필요할 상황 대비), **실사용처의 `interactive={false}` 2건은 제거**(`RaceHub.svelte`의 예측 추이·레이스 아침 폼 미니 차트 — §C1 "interactive={false} 금지" 위반이었음, `<details>` 안 평범한 div라 탭-내비게이션 충돌 없음 확인 후 반영). 커서 위치는 기존처럼 최근접 데이터 포인트 날짜에 스냅(원래 동작 보존).
- 이것으로 2-4(ChartScrub 코어+마이그레이션)는 Sparkline·스트림 탭·FormChart·TrendChart 전부 완료. 남은 건 y축 nice tick 실제 렌더(지금은 `scrub.ts`의 `niceTicks`가 어디서도 호출 안 됨 — 각 차트의 기존 "min/max 텍스트만" 방식을 §C1의 "3~5개 nice tick" 방식으로 바꾸는 건 레이아웃 변경 폭이 커서 별도 판단 필요) + `axisDateLabel` 실사용(현재 x축은 t0/t1 두 끝만 표시, §C1 "≤14일 요일/일, ≤6개월 월경계, >6개월 분기" 세분화 눈금 미적용).
- 검증: `npm run check`(0 errors, 기존 경고 15건 그대로) · `npm run build`(성공) · `npm run test:unit`(211 pass, 회귀 없음). **주의**: 이 컴포넌트는 포인터/드래그 제스처가 핵심인데 이 환경엔 헤드리스 빌드 검증만 있고 실제 터치 기기 확인은 못 했음 — 다음에 화면을 열어볼 때 스크럽이 실제로 부드럽게 동작하는지 확인 필요.

### 2-5 세부 (백엔드 — `explain=1` API, 프론트는 다음 라운드)
- 사용자 확인(2026-09-28 "그래" → 구체 계획 제시 후 "오케이"): 설계 문서(`10-today/design.md §7`)가 값 채우기를 명시한 4개 메트릭(TSB·CTL·ATL·UTRS)만 지원, 나머지는 v1 폴백, DB 스키마 변경 없음, 이번 라운드는 백엔드+테스트만(프론트 `DrillPanel`/`BreakdownView` 재작성은 별도 판단 필요한 규모라 분리).
- `src/services/metrics_explain.py` 신규(235줄): `get_metric_explain(conn, scope_type, scope_id, slug)` — TSB(`ctl−atl` 부호 있는 항), CTL/ATL(전일값×(1−α) + 오늘 부하×α, `pmc.py` EMA 그대로), UTRS(`utrs.py` `WEIGHTS`로 가용 항목만 재정규화, 항목별 `loss`=100점 대비 손실 기여로 정렬) 4종 explainer. `bands.py` `BANDS`를 API 계약 `bands[{max,status,label}]`(마지막 구간 `max=null`)로 변환하는 `_bands_v2`, 최근 7일 평균/전일 대비 `_baseline` 공통 헬퍼. `sources`(원천 활동)는 최근 14일 내 TRIMP 상위 3개 활동으로 근사 — CTL은 252일 창 EMA라 정확한 기여 배분은 의도적으로 안 함(과설계 방지, 코드 주석에 명시).
- `metrics_service.py`의 `_metric_label`/`_metric_unit`을 그대로 import해 재사용(ADR-009는 Calculator 클래스 대상이라 서비스 레이어 raw SQL은 기존 관례대로 허용).
- `src/api/routes_library.py`: `GET /library/metrics/<slug>?explain=1` 쿼리 파라미터로 분기 — explainer가 `None`(미지원 슬러그 또는 해당 scope 데이터 없음) 반환 시 기존 v1(`metrics_service.get_metric_breakdown`)로 자동 폴백, 계약 깨짐 없음.
- `tests/test_metrics_explain.py` 신규(9건) — 인메모리 sqlite + `run_activity_metrics`/`run_daily_metrics`로 실제 엔진 계산 후 4개 슬러그 각각 검증: 미지원 슬러그·데이터 없음 → `None`, TSB 항 부호(CTL `+`/ATL `-`), CTL/ATL 항에 전일값·오늘 부하 포함(ATL α=1/7 가중치 확인), UTRS 항에 `contribution`·`loss` 필드 및 기여 합계가 총점에 근사, `sources`가 웰니스 소스로 채워짐. API 계약의 "terms·sources 둘 다 비면 위반" 요건을 4개 슬러그 모두에서 명시적으로 검증.
- **검증**: `pytest tests/test_metrics_explain.py tests/test_metrics_service.py -v` 17 pass. 전체 `pytest tests/` 1865 pass·247 skip·기존에도 실패하던 무관 3건(`test_autopilot_run_unit.py` — 이 환경에 없는 worktree 경로 참조, 이번 변경과 무관)만 남음, 회귀 없음. `python3 -c "import ast; ast.parse(...)"`로 두 파일 구문 확인, `wc -l`로 300줄 이하 확인(290·235).
- **남음**: 프론트 `DrillPanel.svelte`/`BreakdownView.svelte`(§C3.1~C3.3 4블록 레이아웃, `?drill=` URL 스택)가 신규 API를 실제로 소비하도록 재작성 — 자체로 규모가 커서 별도 라운드로 분리, 사용자 확인 필요.

### 2-5 세부 (2차 — CIRS 추가, 사용자 피드백 "다른 지표들도"·"너무 최소한만 하는데" 반영)
- 사용자 확인 없이 즉시 확장(2026-09-28 "너무 최소한만 하는데" — 판단 가능한 범위는 바로 진행): CIRS는 UTRS와 동일한 가중 합성 구조(`parent_metric_id` 자식 행 + `WEIGHTS` dict)라 기계적으로 확장 가능해 바로 추가. `_explain_cirs`는 UTRS 패턴을 재사용하되 위험 점수 특성상 `loss` 없이 `contribution` 자체가 위험 기여분(내림차순 정렬 = 가장 큰 위험 요인이 먼저).
- **다른 메트릭은 왜 이번에 안 넣었는지(기계적 확장이 아니라 판단이 필요한 이유, 코드에도 주석으로 남김)**: RRI·VDOT 등은 곱셈형 공식(요인들이 `metric_store` 자식 행이 아니라 `json_value`에만 있음)이라 UTRS/CIRS식 가중치 분해 코드가 그대로 안 맞음 — 별도 표현 방식 설계가 필요. 또한 모든 신규 메트릭의 "meaning.what/so_what" 카피는 `metric_registry.py`에 영문 약어 설명만 있고 사용자向 문구가 없어 매번 직접 작성해야 함(TSB/UTRS/CIRS도 이번 세션에서 새로 씀) — 이건 등록부에 없는 순수 UX 카피 작성이라 값 추출과 달리 계속 판단이 필요한 부분. 이 두 가지가 "왜 4개 → 5개까지만 기계적으로 늘었는지"의 근거.
- CIRS는 S7에서 개인 기준선 기반으로 재설계될 예정(`10-today/design.md` F-DATA-12) — 이 explainer는 현재 v1 공식 기준이며 S7 착수 시 갱신 필요(코드 주석에 명시).
- 테스트 3건 추가(`TestCIRSExplain`) — contribution 필드 존재·loss 없음, `higher_is_better=False`, 위험 기여도 내림차순 정렬.
- **검증**: `pytest tests/test_metrics_explain.py -v` 12 pass. 전체 `pytest tests/` 1868 pass·247 skip·무관 기존 실패 3건만 그대로. `wc -l` 288줄(300줄 이하 유지).

### 2-5 세부 (3차 — RRI 추가 + 파일 분리, 사용자 "오케이"로 계속 확장)
- 사용자가 앞선 "다른 지표들도 넣을지/RRI 등도 새 표현으로 설계할지" 질문에 "오케이"로 응답 — 둘 다 진행: 곱셈형 공식(RRI)도 새 표현으로 추가.
- **RRI**: `RRICalculator`가 곱셈 인수(`vdot`, `vdot_target`, `ctl`, `target_ctl`, `di`, `cirs`)를 이미 `json_value`에 저장해두고 있어(재계산 없이) 그대로 읽어 표현만 바꿈. UTRS/CIRS의 `weight`+`contribution`(가중 합) 대신 `ratio`(0~1)+`role="factor"`(곱) 형태의 새 term 종류를 도입 — 공식 자체가 합이 아니라 곱이라 가중치 분해가 의미 없음. `sources`도 활동이 아니라 구성 메트릭(`race_pred_vdot`/`ctl`/`di`/`cirs`) 자체를 가리키도록(`type: "metric"`) 다르게 설계 — RRI는 특정 활동이 아니라 다른 지표들의 조합이라 활동 근사가 안 맞음.
- **RRI는 registry(`bands.py`)에 등급 구간이 없다는 것도 이번에 발견**: `RRICalculator.ranges`(insufficient/building/ready/peak)가 1-2 "등급 SSOT" 작업(`bands.py`) 이관 대상에서 빠져 있어, 지금 앱 전체에서 RRI는 status/label 없이 값만 보여주고 있음 — 이건 이번 explain 작업 범위 밖의 기존 갭이라 고치지 않고 기록만 함(SSOT 파일 변경은 check_docs.py 영향 범위가 커서 별도 판단 필요, `21-library-metrics/design.md` 등에 후속 항목으로 남길 만함).
- **파일 300줄 규칙 위반 해소**: `metrics_explain.py`가 CIRS+RRI 추가로 336줄이 되어 3개로 분리 — `metrics_explain.py`(TSB/CTL/ATL + 진입점 `get_metric_explain`, 186줄), `metrics_explain_composite.py`(UTRS/CIRS/RRI explainer, 131줄), `metrics_explain_shared.py`(양쪽이 쓰는 `top_activity_sources`/`daily_trimp_sum`, 순환 import 방지용, 44줄).
- 테스트 3건 추가(`TestRRIExplain`) — `role="factor"`·`ratio∈[0,1]`, `higher_is_better=True`, sources가 정확히 4개 구성 메트릭을 가리킴. seeding은 기존 `tests/test_rri.py` 패턴처럼 `upsert_metric`으로 `json_value` 직접 주입(RRI는 VDOT 등 선행 데이터가 많이 필요해 단일 활동 엔진 계산으로는 잘 안 나옴 — `test_metrics_service.py`의 기존 RRI 테스트도 데이터 없으면 skip하는 이유와 동일).
- **검증**: `pytest tests/test_metrics_explain.py -v` 15 pass. 전체 `pytest tests/` 1871 pass·247 skip·무관 기존 실패 3건만 그대로. `wc -l` 3개 파일 모두 300줄 이하. `python3 scripts/check_docs.py` 신규 파일 4개(`metrics_explain_composite.py`·`metrics_explain_shared.py`·`test_metrics_explain.py` 등) files_index.md 미등록 에러 발견 → `python3 scripts/gen_files_index.py` 재생성으로 해소(이 참에 이전 세션에서 남아있던 미등록 파일 7개도 같이 정리됨), 재실행 결과 Errors 0.

## 다음
Phase 1 완료. 2026-09-28 "오케이 이어서 진행"으로 Phase 2 착수, 2-1 대부분·2-2·2-4·2-5(백엔드, TSB/CTL/ATL/UTRS/CIRS/RRI) 완료. 다음 후보: 2-5 프론트(DrillPanel/BreakdownView 재작성), 2-6(성능). VDOT 등 더 있는 메트릭 확장 시엔 매번 "meaning.what/so_what" 카피를 직접 써야 하는 제약은 여전함. RRI 등급 SSOT 미등재(발견한 기존 갭)는 별도 판단 필요 항목으로 기록. 2-3(전환 스위치)은 계정 설정 스키마 필요해 보류 중.
