# UX 리뷰 로드맵 구현 진행 (체크포인트)

세션 한도·재시작 대비 재개용. 로드맵 원본: `99-summary.md §7`, 결정: `../DECISIONS.md [P7-UX-REVIEW-0928]`.

## 작업 규칙
- 작업 위치: worktree `/home/ubuntu/projects/RunPulse-p0` (브랜치 `claude/project-thread-vgunp6`).
- 운영 반영 이력: 2026-09-30 06:50 — 6982aa6까지(Phase 2·3-1·Coach 판정 통합) ff 병합·프론트 빌드. 2026-09-30 12:11 — 266ebee까지(3-2·3-3) ff 병합·`npm run build`·`docker restart`(스키마 v23 자동 마이그레이션). 이후 커밋은 다시 "운영 반영" 지시 시에만. 2026-10-01 23:42 — 98123e3까지(Groq 404 수정·format_ko·3-4·3-5) ff 병합·`npm run build`(gunicorn --reload로 코드 반영, 스키마 v24 자동 마이그레이션·백업 `running.db.bak-20261001-pre-v24`, 컨테이너 내부 서비스 스모크 통과). 2026-10-03 — fd49825까지(3-6·3-7 S1a·표시명 SSOT·wellness 버그 수정) ff 병합·`npm run build`.
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
| 2-1 공통 규격(1차) | 진행 중·운영 반영(2026-09-30 06:50, 6982aa6) | 아래 "2-1 세부" 참조. D1a~D1e 중 D1b(델타 토큰)·D1c(거리 소수 2자리 예외)·D1e(★ 아이콘) 반영, D1d(활동 scope `@a{id}`)는 §C3.3 드릴다운 URL 작업(2-5)과 함께 할 예정이라 보류 |
| 2-5 분해 v2(API+프론트) | 진행 중·운영 반영(2026-09-30 06:50, 6982aa6) | 사용자 확인(2026-09-28 "오케이" 반복) — 아래 "2-5 세부" 참조. `library/metrics`·Today에 통합, Coach 등 나머지 진입점은 별도 |

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

| 2-2 셸 기반(40:S0) | 진행 중·운영 반영(2026-09-30 06:50, 6982aa6) | 아래 "2-2 세부" 참조. S1(전환 스위치 `ui_default`)은 범위 밖(D6 계정 설정 필요, 별도) |

### 2-2 세부
- `app.html`: `lang="ko"`, `viewport-fit=cover`.
- `+layout.svelte`: safe-area(헤더 top, 하단 탭바 bottom), ☰를 좌측으로 이동해 활성화(기존엔 우측·disabled) — 40 design §2.1 "좌측 ☰·우측 Pill" 결정 반영(Pill 자체는 SyncState 프론트 배선이 있는 Phase 4-1 몫이라 아직 없음).
- `MenuDrawer.svelte` 신규 — **과도기 드로어(스코프 판단)**: 40 design 최종안(①동기화 요약 ②소스 연결 ③내 데이터 ④설정 ⑤가이드 ⑥로그아웃)은 SyncState 프론트 연동이 있어야 하는 Phase 4-1 몫이라, 지금은 "과도기(G1 전)" 문구가 명시한 v1 링크만 담음 — 대시보드·활동·웰니스·훈련·레이스·AI 코치·신발(빠른 이동) + 동기화·설정·가이드·CSV 내보내기(데이터·설정) + 계정 전환. v1 경로는 `data-sveltekit-reload`로 전체 새로고침. **이 스코프 좁히기는 설계 문서가 명시적으로 결정한 사항이 아니라 이번 세션의 판단** — 사용자가 과도기 드로어에 동기화 요약까지 지금 넣길 원하면 후속 지시 필요.
- `+error.svelte` 신규(§6.3) — 셸(헤더·탭) 유지, 404는 상위 경로로, 그 외는 다시 시도 + Today 링크.
- `ErrorState.svelte`/`EmptyState.svelte`/`Toast.svelte`/`SubTabs.svelte` 신규(§C5·§7.1) — 전부 프레젠테이션 컴포넌트만, 아직 소비처 없음(다음 단계에서 각 화면에 배치). `lib/states.ts`(4분류 판정)는 SyncState 의존이라 이번엔 미작성.
- 검증: `npm run check`(0 errors) · `npm run build`(성공) · `npm run test:unit`(206 pass, 회귀 없음).
- 남음: `ui_default` 전환 스위치(S1, 계정 설정 스키마 필요 → D6과 함께), MenuDrawer를 실제 SyncStatusPill로 교체(Phase 4-1), ErrorState/EmptyState를 각 라우트 로딩 실패 지점에 실제로 배선.

| 2-4 ChartScrub 코어(1차) | 진행 중·운영 반영(2026-09-30 06:50, 6982aa6) | 사용자 확인(2026-09-28 "권장안으로 하고") — 2-3(계정 설정 스키마 필요)은 보류, 스키마 안 건드리는 2-4부터 진행 |

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

### 2-5 세부 (4차 — 프론트 DrillPanel·BreakdownView, "오케이"로 이어서 진행)
- 사용자가 백엔드 확장 계속/프론트 전환 질문에 "오케이"로 응답 — 프론트 소비 쪽으로 진행(§C3 스펙 그대로 구현, `10-today/design.md` C3.1~C3.3).
- **신규 컴포넌트**: `BreakdownView.svelte`(§C3.2 본문 4블록 — ①의미: what·밴드 바(5색+핀)·7일평균/어제대비·so_what, ②공식·기여: mono 공식 텍스트+항목별 막대(±는 `--color-delta-better/worse`, RRI 같은 factor는 비율 막대), `loss` 있으면 1위에 "가장 크게 끌어내림" 태그, `drill` 필드 있는 항만 `›`로 스택 push 가능, ③원천 Top3, ④푸터: provider 배지 줄+추세 링크) / `DrillPanel.svelte`(§C3.1 컨테이너 — 데스크톱 ≥1024px는 `grid-cols-[1fr_420px]` 비모달 사이드 패널, 모바일은 풀스크린 슬라이드업+백드롭, 헤더 back·breadcrumb·✕, Esc=한 단계 pop, 포커스를 제목으로).
- **URL 스택(§C3.3) 구현 중 SvelteKit 함정 발견**: `pushState`는 브라우저 주소창의 URL은 바꾸지만 `$app/state`의 `page.url`은 갱신하지 않는다(shallow routing 설계상 `page.state`만 갱신) — 처음엔 `page.url`만 보고 만들어서 클릭해도 패널이 전혀 안 열리는 버그가 났다. `app.d.ts`에 `PageState.drill: string[]`을 추가하고 `currentDrillStack() = page.state.drill ?? parseDrillStack(page.url)`로 고쳐 해결(딥링크·새로고침 직후엔 `page.state`가 없어 URL 폴백, push 이후엔 `page.state`가 진짜 값 — `history.back()`은 SvelteKit이 popstate에서 저장된 state를 자동 복원해줘서 그대로 동작). 브라우저에서 실제로 클릭해보지 않았으면 놓쳤을 버그.
- **스코프**: `library/metrics/[slug]` 페이지 한 곳에만 통합(explain 지원 6개 슬러그는 DrillPanel, 그 외는 기존 `MetricBreakdown` 바텀시트 유지 — 백엔드의 v1 폴백과 같은 패턴). Today/Coach 등 나머지 진입점 배선은 이후 라운드(5·6차)에서 이어감. `@a{id}` 활동 scope 토큰(D1d)은 여전히 범위 밖(아래 6차 참조). 끌어 닫기 제스처(모바일)도 이번엔 구현 안 함(탭/✕/Esc/뒤로가기로는 닫힘) — 별도 판단 필요 항목.
- **로직 분리**: `drillStackCore.ts`(순수 함수 `parseDrillStack`·`tokenSlug`, SvelteKit 의존 없음 — 테스트용) / `drillStack.ts`(`pushState`·`page` 등 SvelteKit API, `pushDrill`·`popDrill`·`closeDrill`). `statusColor.ts`(서버 status 어휘 poor/caution/neutral/good/excellent → `--color-status-*` 토큰 매핑, 이번이 그 토큰의 첫 실제 소비처).
- **실제 브라우저 확인**: 워크트리 로컬(`data/users/default/running.db`, 커밋 안 함)에 90일 합성 데이터 시드 → Flask(`src/serve.py`)+`vite dev` 기동 → Playwright(임시 설치, headless Chromium)로 실제 클릭 스모크: 데스크톱 패널 열기/CTL로 드릴다운(브레드크럼 "TSB › CTL")/뒤로가기(URL이 `?drill=m.tsb,m.ctl` → `?drill=m.tsb`로 정확히 줄어듦)/모바일 슬라이드업/RRI(곱셈형) 화면까지 스크린샷 확인, 콘솔·페이지 에러 0건. 시드 스크립트·DB는 확인 후 삭제(커밋 안 함).
- **검증**: `npm run check`(0 errors) · `npm run test:unit`(217 pass, 드릴스택 순수 함수 6건 신규) · `npm run build`(성공) · 위 브라우저 스모크.
- **남음**: Coach 등 나머지 화면에 DrillPanel 연결(진입점마다 트리거 배선 필요, 이번 범위 밖), 모바일 끌어 닫기 제스처, `@a{id}` 활동 scope, VDOT 등 나머지 메트릭 확장 시의 카피 작성 부담은 여전.

### 2-5 세부 (5차 — Today 연결, "오케이"로 이어서 진행 + 실제 클릭으로 발견한 버그 수정)
- Today `+page.svelte`의 L1 ScoreRing 3개(UTRS·CIRS·TSB — `04-component-catalog.md` 1-A' L1)가 정확히 explain 지원 6개 슬러그 중 3개와 일치해 자연스러운 다음 연결점이었음. `<DrillPanel scopeType="daily" scopeId={todayDate}>`로 전체를 감싸고, `handleDrill`을 슬러그가 지원 목록에 있으면 새 패널로, 아니면(EvidenceQuote 칩·`onDrillInput` 캐스케이드처럼 scope가 다르거나 임의 슬러그인 경우) 기존 `drillStack`/`MetricBreakdown`으로 분기.
- **실제 클릭에서만 드러난 버그 2건**(둘 다 헤드리스 브라우저로 직접 눌러보다가 발견 — 코드만 봤으면 못 잡았을 것들):
  1. **워크트리 오염 위험**: 서버 기동 명령을 여러 줄로 나눠 쓰면서 `cd frontend`가 이전 줄의 `cd .../RunPulse-p0 &&`와 분리된 백그라운드 job 안에서만 유효해, 실제로는 툴이 리셋한 기본 디렉터리(`/home/ubuntu/projects/RunPulse`, **운영 컨테이너가 마운트하는 메인 폴더**)에서 `vite dev`가 떴다. 그 상태로 스모크를 돌렸더니 내 변경 사항이 전혀 없는 코드가 렌더링돼 "패널이 안 열린다"는 잘못된 결론을 낼 뻔했다. 파일은 안 건드렸지만(읽기 전용 `vite dev` 프로세스) 즉시 process 확인(`readlink /proc/<pid>/cwd`)으로 잡아 죽이고, 이후로는 서버 기동을 `cd <절대경로> && nohup ... &` 한 줄짜리 자기완결 명령으로만 실행. 여러 줄 백그라운드 명령에서 `cd`를 분리하면 안 된다는 교훈.
  2. **스택 대체 vs 쌓기 혼동**: UTRS 패널이 열려 있을 때 TSB ScoreRing을 누르면 `pushDrill`이 그대로 append돼 `?drill=m.utrs,m.tsb`(브레드크럼 "UTRS › TSB")가 됐다 — 완전히 다른 독립 진입점을 누른 건데 TSB가 UTRS "안"에 있는 것처럼 보이는 오표시. `drillStack.ts`에 `openDrill(slug)`(스택을 이 슬러그 하나로 교체 — 패널 밖 독립 진입점용)을 추가하고 `pushDrill`(패널 안 `drill` 탭 전용, 기존 스택 위에 쌓기)과 분리해서 고침. `library/metrics` 페이지의 "계산 분해 보기" 버튼도 같은 이유로 `openDrill`로 교체(그 페이지는 항상 닫힌 상태에서 열어서 동작은 그대로지만 의도가 더 명확해짐).
- **검증**: `npm run check`(0 errors) · `npm run test:unit`(217 pass, 회귀 없음) · `npm run build`(성공) · 브라우저 스모크 재실행 — UTRS 클릭 → `?drill=m.utrs`, 이어서 TSB 클릭 → `?drill=m.tsb`(스택 교체 확인, 이전엔 `m.utrs,m.tsb`였음), 콘솔 에러는 무관한 기존 404(`/coach/plan/active`, 활성 계획 없을 때 정상) 1건만.

### 2-5 세부 (6차 — Coach 연결 + §C3.3 날짜 scope 토큰, "진행"으로 이어서)
- Coach 스레드(`coach/[threadId]/+page.svelte`)의 EvidenceQuote 근거 칩은 대화에서 인용한 **과거 날짜**를 가리킬 수 있어(Today의 evidence·ScoreRing과 달리 scope가 화면 기준일 하나로 고정되지 않음), 이번에 처음으로 `?drill=` 토큰에 scope를 실어야 했다. §C3.3이 원래 정의한 문법(`m.{slug}@{scope}`, scope는 `YYYY-MM-DD` 또는 `YYYY-MM`, 생략하면 화면 기준일)을 지금 구현: `drillStackCore.ts`에 `parseDrillToken`/`formatDrillToken` 추가, `openDrill`/`pushDrill`이 선택적 `scope` 인자를 받고, `DrillPanel`이 스택 맨 위 토큰의 scope(없으면 페이지 기본 `scopeId` prop)로 API를 호출·소제목에 표시. 패널 안에서 더 드릴다운할 때도 **현재 보고 있는 scope를 그대로 물려받는다**(페이지 기본으로 되돌아가지 않게 — 안 그러면 과거 날짜 TSB를 보다가 CTL로 들어갔는데 갑자기 오늘 CTL이 뜨는 오류가 났을 것).
  - **주의(과다 주장 방지)**: 이건 `99-summary.md` D1d(활동 scope `@a{id}`, 예: `m.trimp@a17414`)와는 다른 항목이다. D1d는 "특정 활동 하나"를 가리키는 토큰이고, 이번에 구현한 건 "다른 날짜"를 가리키는 날짜 scope 토큰(§C3.3 기본 문법에 이미 있던 것)이다. explain 지원 6개 슬러그가 전부 daily scope라 활동 scope가 필요한 상황 자체가 아직 없음 — D1d는 여전히 미구현으로 남겨둔다.
  - Coach `openEvidence`도 Today와 같은 패턴(지원 슬러그+`scopeType==='daily'`면 새 패널, 아니면 기존 `drillStack`/`MetricBreakdown`)으로 분기.
- **적용 안 한 곳**: `MonthNarrative.svelte`(Today L2, `이번 달 이야기` 오버레이)도 자체 evidence 드릴다운이 있지만, 그 컴포넌트 자체가 이미 `fixed inset-0` 오버레이라 Today의 `DrillPanel`(마찬가지로 `fixed inset-0` 모바일 오버레이)과 동시에 열리면 두 레이어가 겹치는 문제가 생길 수 있어 이번엔 손대지 않음 — 레이어링을 실제로 확인 못 한 채 고치는 게 더 위험 판단, 별도 검증 필요 항목으로 기록.
- **실제 브라우저 확인**: 합성 DB에 `chat_threads`/`chat_messages`(스키마는 `evidence_json` 컬럼 — 처음엔 `evidence`로 잘못 짐작해서 Explore 에이전트로 실제 DDL 확인 후 수정) 1건 + 과거 날짜(생성일 기준 +10일) 근거를 단 메시지 시드 → Coach 스레드에서 칩 클릭 → `?drill=m.tsb@2026-07-11`로 정확히 열림, 소제목 "2026-07-11 아침 기준", 그 시점의 실제 CTL/ATL/소스 활동 표시 확인 → CTL 행 눌러 중첩 드릴 → `?drill=m.tsb@2026-07-11,m.ctl@2026-07-11`로 scope 유지 확인. 콘솔 에러 0건. 서버는 이번엔 절대경로 한 줄짜리 자기완결 명령으로만 기동(5차에서 겪은 실수 재발 방지), `readlink /proc/<pid>/cwd`로 매번 worktree 확인.
- 테스트 6건 추가(`parseDrillToken`/`formatDrillToken` 파싱·포맷·왕복).
- **검증**: `npm run check`(0 errors) · `npm run test:unit`(223 pass) · `npm run build`(성공) · 위 브라우저 스모크.
- **남음**: D1d 활동 scope(`@a{id}`) — explain 지원 슬러그가 daily뿐이라 지금은 필요 상황이 없어 보류. `MonthNarrative` 레이어링 검증. 모바일 끌어 닫기 제스처. VDOT 등 나머지 메트릭 확장의 카피 작성 부담.

### 2-6 세부 (1차 — `/library/metrics` N+1 쿼리 제거, "진행"으로 착수)
- `02-performance.md`(P-3)가 측정한 `/library/metrics` 776ms의 원인을 코드에서 확인: `get_metrics_browser()`가 daily-scope 84개 메트릭마다 각각 `get_primary_metric`(값 1개) + 무제한 `get_metric_history`(전체 히스토리)를 개별 쿼리해 최대 ~168회 왕복이 발생하고 있었음.
- **수정**: `src/services/metrics_browser_service.py` — 값 조회를 `get_primary_metrics`(복수형, 기존 `db_helpers`에 이미 있던 배치 헬퍼) 1회 `IN (...)` 쿼리로 교체. 히스토리도 메트릭별 개별 쿼리 대신, 값이 있는 메트릭들에 대해 `scope_id BETWEEN`+`metric_name IN (...)` 1회 쿼리로 배치하고 Python에서 `metric_name`별로 그룹핑. 무제한 히스토리 대신 "최근 14개 스파크라인"에 필요한 만큼만 `_SPARKLINE_LOOKBACK_DAYS = 90`일 창으로 제한(그보다 드물게 기록되는 메트릭은 스파크라인이 14개보다 짧아질 수 있음 — 에러 대신 짧은 리스트, 코딩 규칙 그대로). 결과: 요청당 쿼리 수 최대 ~168회 → 정확히 2회.
- **사소한 버그**: 함수 매개변수 `date: str | None`이 모듈 상단의 `from datetime import date` 클래스 임포트를 가려서, 배치 히스토리 창 계산에 `date.fromisoformat(...)`을 그대로 쓰면 문제가 됨 — 함수 내부에서 `from datetime import date as _date_cls`로 로컬 임포트해 회피.
- **동치성 테스트 추가**(`tests/test_metrics_browser_service.py::test_sparkline_matches_batched_history_over_multiple_days`): 19일치 활동을 추가로 시드하고, 배치로 만든 스파크라인이 메트릭별 개별 raw SQL 히스토리 쿼리 결과의 마지막 14개와 정확히 일치하는지 검증.
- **벤치마크**(스크래치 스크립트, 커밋 안 함): 365일 합성 데이터셋에서 `get_metrics_browser()` 5회 평균 4.7ms(카테고리 5개·메트릭 25개) — 원래 측정치 776ms 대비 대폭 개선. 이 환경엔 원래 운영 규모(84개 daily 메트릭 전부)의 데이터가 없어 776ms 자체를 재현하지는 못했으나, 쿼리 횟수가 168회→2회로 줄어든 구조적 개선이라 규모가 커질수록 효과가 더 뚜렷할 것으로 판단.
- **무관 실패 확인**: 이 변경 적용 중 `tests/test_plan_creation.py::test_created_plan_follows_periodization_and_ends_on_race`가 `assert 9 == 10`로 실패하는 걸 발견 — `git stash`로 변경분을 빼고 동일 테스트를 단독 실행해도 **동일하게 실패**함을 확인(오늘 날짜 2026-09-29 기준 주차 계산이 달라지는 날짜 의존 테스트로 추정, 이번 변경과 무관). `git stash pop`으로 복원 후 계속 진행.
- **검증**: `pytest tests/test_metrics_browser_service.py tests/test_today_service.py -v` 50 pass. 전체 `pytest tests/ -q` 1871 pass·247 skip·무관 기존 실패 4건(`test_autopilot_run_unit.py` 3건 + 위 `test_plan_creation.py` 1건, 모두 이번 변경과 무관 확인됨)만 그대로.
- **남음**: P-3 나머지 절반인 `/today/narrative`(413ms)는 초기 조사 결과 DB 비효율이 아니라 캐시 미스 시 LLM 추론 지연으로 보임(`get_narrative_cache`/`set_narrative_cache`가 성공한 AI 결과만 캐시) — 백그라운드 사전 생성 등 캐시 워밍 전략이 필요한 더 큰 설계 결정이라 임의로 진행하지 않고 사용자 확인 필요. P-4(활동 상세 650KB 스트림 페이로드 서브탭 간 공유)·P-5(탭 재방문 stale-while-revalidate 캐싱)는 미착수. P-1(gunicorn 워커/스레드, `--reload` 제거)·P-6(루트 라우팅)은 운영 컨테이너 인프라 변경이라 범위 밖으로 명시 제외.
- **실제 브라우저 확인(뒤늦게, 사용자 피드백 "성능작업 때도 브라우징 해봐야지" 반영)**: 120일 합성 데이터로 워크트리 로컬 DB 시드 → Flask+vite 실제 기동 → Playwright로 `/v2/library/metrics` 페이지 로드. 프론트가 실제로 부르는 `/api/v1/library/metrics` 200, 콘솔·페이지 에러 0건, CTL·TSB·UTRS·CIRS 정상 렌더 확인(스크린샷). curl 반복 호출로 서버 왕복시간 10~12ms(22개 메트릭·14일 스파크라인 포함) 확인. 확인 후 서버 종료·시드 DB 삭제.

### 2-6 세부 (2차 — 활동 상세 서브탭 간 데이터 공유, "계속 진행해줘"로 착수)
- P-4("활동 상세 API에서 스트림 분리, 서브탭 간 데이터 공유(레이아웃 load)") 중 **후자만** 이번에 진행 — 전자(요약 탭 자체의 스트림 다운샘플)는 RouteMap·ElevationProfile·페이스/HR 미니차트가 전부 풀해상도 `streams`를 쓰고 있어(`library/[id]/+page.svelte`) 다운샘플하면 차트 충실도가 실제로 떨어지는 시각적 트레이드오프 판단이 필요해 별도 확인 없이 진행 안 함(코드에 주석으로 남김).
- **원인**: `library/[id]/(요약|laps|metrics|streams)/+page.ts` 4개가 각각 독립적으로 `getActivity(id)`(650KB, streams 포함)를 호출 — 서브탭 전환마다(같은 활동 안에서도) 매번 재요청됐다(streams 탭은 여기에 더해 자체 630KB `getActivityStreams`까지 병렬 호출해 한 번에 1.28MB).
- **수정**: `library/[id]/+layout.ts` 신규 — `getActivity(id)`를 여기서 1회만 호출해 `{ activity, errorMessage }`를 서브탭에 공유. 4개 `+page.ts`는 자체 `getActivity` 호출을 제거하고 `parent()`로 레이아웃 데이터를 받아 각자 필요한 모양(`laps`/`metricsByCategory`/`totalSec`)으로 재구성만 함 — `+page.svelte` 쪽은 변경 없음(반환 타입·필드명 그대로 유지). `streams/+page.ts`는 `getActivityStreams`(고유 630KB, 유지)와 레이아웃의 `activity.core.duration_sec`만 함께 사용.
- **실제 브라우저로 전후 비교**: 120일 합성 데이터로 활동 1건 시드 → Playwright로 요약→랩→메트릭→스트림→요약 5단계 이동. **수정 전**(git stash로 되돌려 같은 시나리오 재현): `/api/v1/library/activities/1` 3회 재요청. **수정 후**: 정확히 1회. `git stash`/`git stash pop`으로 원복 확인 후 계속 진행(이번 세션에 확립한 "전후 비교로 직접 증명" 패턴 — [[feedback_browser_verify_perf]]).
- **검증**: `npm run check`(0 errors, 기존 경고 15건 그대로) · `npm run test:unit`(223 pass) · `npm run build`(성공) · 위 브라우저 전후 비교. 서버·시드 DB는 확인 후 정리.
- **남음**: 요약 탭 자체의 스트림 다운샘플(위 이유로 보류), P-5(탭 재방문 stale-while-revalidate 캐싱) 미착수.

### 2-6 세부 (3차 — 탭 재방문 stale-while-revalidate 캐싱, "계속 진행"으로 착수)
- P-5 대응: Today·Library 홈을 재방문할 때마다(`$navigating`이 실제로 매번 전량 재요청, 02-performance.md 측정 1.2~1.3초 무반응) `+page.ts`의 `load()`가 매번 처음부터 다시 fetch하던 것을 캐시로 대체.
- **구현**: `frontend/src/lib/loadCache.ts` 신규 — `swrLoad(key, fetcher, invalidateFn, staleMs=30_000)`. 캐시 없으면 기존과 동일하게 기다림(최초 방문 성능 불변). 캐시 있고 `SWR_STALE_MS`(30초) 이내면 네트워크 없이 즉시 반환. 30초 지났으면 **캐시를 먼저 즉시 반환하면서** 백그라운드로 `fetcher()`를 다시 부르고, 성공하면 캐시 교체 후 `invalidateFn(key)` 호출 — 실패하면 조용히 무시(이전 캐시 유지, 코딩 규칙의 "데이터 없음 대신 이전 상태 유지"와 같은 정신).
- **SvelteKit과의 연결**: `$app/navigation`의 `invalidate`는 SvelteKit 런타임에서만 동작해 순수 함수 노드 테스트가 안 되므로, `drillStackCore.ts`/`drillStack.ts`(이전 세션)와 같은 순수-로직/프레임워크-연동 분리 패턴을 그대로 적용 — `loadCache.ts`는 `invalidate`를 주입받기만 하고, 호출부(`today/+page.ts`·`library/+page.ts`)에서 `depends(key)`(등록) + `invalidate` 임포트해서 넘김. `invalidate(key)`가 호출되면 SvelteKit이 현재 페이지가 그 key에 `depends`했을 때만 `load()`를 조용히 다시 돌려 화면을 갱신(사용자에게 로딩 표시 없이) — 페이지 컴포넌트(`+page.svelte`)는 전혀 손대지 않음, `$derived(data....)` 패턴이 이미 반응형이라 자동으로 새 값을 반영.
- **버그 하나 잡음**: 최초 구현은 `Date.now() - hit.ts > staleMs` 였는데, `staleMs=0`으로 테스트하면 같은 밀리초 안에 두 호출이 일어날 때 `0 > 0`이 거짓이라 백그라운드 갱신이 영영 트리거 안 되는 경계 버그 — `>=`로 고침(운영값 30_000에선 사실상 안 보이는 문제였지만 테스트가 바로 잡아냄).
- 테스트 4건 추가(`tests/loadCache.test.mjs`): 콜드 캐시 fetch, 30초 이내 캐시 히트(네트워크 0회), 30초 이후 캐시 즉시 반환+백그라운드 갱신+invalidate 호출, 백그라운드 실패 시 이전 캐시 유지.
- **실제 브라우저로 전후 동작 확인**(Playwright): Today→Library→Today(30초 이내) 재방문 43ms·API 추가 호출 0회. 31초 대기 후 Today 재방문 28ms(여전히 캐시로 즉시 렌더)인데 이번엔 백그라운드 갱신 1회 발생(API 누적 호출 1→2) — 설계한 SWR 동작이 실측으로도 정확히 재현됨. 콘솔 404는 무관한 기존 이슈(`/coach/plan/active`, 활성 플랜 없을 때 정상, 이전 세션에도 확인된 것과 동일).
- **검증**: `npm run check`(0 errors) · `npm run test:unit`(227 pass, 신규 4건 포함) · `npm run build`(성공) · 위 브라우저 확인.
- **남음**: Coach·활동 상세 등 다른 라우트는 재방문 비용이 낮게 측정돼(02-performance.md 표 참조) 이번엔 손 안 댐. 요약 탭 스트림 다운샘플은 여전히 보류(차트 충실도 트레이드오프).

### 2-6 세부 (4차 — `/today/narrative` 지연 로드, "2-6 이어서" 확인 후 프론트 전용으로 재판단)
- P-3 나머지 절반(`/today/narrative` 413ms)은 이전 라운드에서 "백엔드 캐시 워밍은 설계 결정 필요"로 보류했었는데, **백엔드를 안 건드리고 프론트에서만** 체감 속도를 해결할 수 있다는 걸 재검토 중 발견 — narrative를 핵심 데이터와 분리해 지연 로드하면 캐시 전략 결정 없이도 무반응 시간을 없앨 수 있어 진행.
- **원인**: `today/+page.ts`의 `load()`가 `today`·`narrative`·`plan`·`trend`류·`race-hub`를 전부 `Promise.all`로 묶어 기다린 뒤 화면을 그려서, narrative가 느리면(캐시 미스 시 LLM 추론) 페이지 전체가 그만큼 늦게 떴다. 덤으로 발견한 기존 버그: FormChart(피트니스·폼 차트)는 `ctlTrend`/`tsbTrend`에만 의존하는데 `{#if narrative}` 블록 안에 있어서 narrative가 없으면 같이 안 뜨고 있었음(서로 무관한 데이터인데 우연히 묶여 있었음).
- **수정**: `today/+page.ts` — narrative를 `await` 없이 `Promise<NarrativeResponse|null>`로 `TodayPageData`에 그대로 넘김(핵심 배치와 동시에 시작만 하고 기다리지 않음). `today/+page.svelte` — FormChart를 `{#if narrative}` 밖으로 꺼내 narrative와 무관하게 먼저 렌더, narrative 표시 블록은 `{#await data.narrative}로딩 스켈레톤{:then narrative}기존 내용{/await}`로 감쌈. 페이지의 다른 부분(L0/L1, 스코어링 등)은 원래도 narrative와 무관했으니 무변경.
- **SWR과의 상호작용**: `loadCache.ts`의 `swrLoad`는 `fetchToday()`가 반환하는 객체를 캐시할 뿐이라, 그 안의 `narrative` 필드가 Promise든 아니든 상관없이 그대로 동작 — 재방문 시 캐시된 (이미 settled된) narrative Promise가 그대로 재사용되고, 백그라운드 갱신 시엔 새 Promise가 생겨 `{#await}`가 다시 자연스럽게 로딩→완료를 보여줌. 재확인 결과 회귀 없음.
- **실제 브라우저 확인**(Playwright `page.route()`로 narrative 응답에 인위적 2초 지연 주입 — 캐시 미스 상황 재현): 핵심 화면(스코어링·최근 활동·다음 세션 등)은 지연과 무관하게 ~900ms에 렌더 완료(지연 없을 때 baseline 868ms와 거의 동일), "흐름·훈련·성장" 섹션만 로딩 스켈레톤 표시 후 narrative 도착 시(~2.5초) 자연스럽게 교체. 요청 타이밍 로그로 `today`/`race-hub`/`narrative` 세 요청이 거의 동시에 시작되고(narrative를 Promise.all 뒤에 순차 호출하던 첫 구현을 동시 시작으로 한 번 더 고침) 핵심 응답이 narrative 완료보다 훨씬 먼저 화면에 반영됨을 확인. SWR 재방문(30초 이내/이후)도 이 변경 이후 재검증해 회귀 없음 확인.
- **검증**: `npm run check`(0 errors) · `npm run test:unit`(227 pass, 회귀 없음) · `npm run build`(성공) · 위 브라우저 확인 2종.
- **남음**: 백엔드 캐시 워밍(narrative를 애초에 빠르게 만드는 것) 자체는 여전히 안 함 — 이번 수정은 "느려도 화면을 막지 않는다"까지만이고, LLM 추론 자체를 빠르게 하려면 여전히 사용자 확인이 필요한 설계 결정(사전 생성 등)이 남아 있음. 요약 탭 스트림 다운샘플만 이제 2-6의 마지막 보류 항목.

### 2-6 세부 (5차 — 요약 탭 스트림 다운샘플, 사용자 "설계 방식대로 해"로 진행)
- P-4 나머지 절반("활동 상세 API에서 스트림 분리(요약용 다운샘플 폴리라인만)"): 이전 라운드에서 RouteMap·ElevationProfile·페이스/HR 미니차트의 시각적 충실도 트레이드오프를 이유로 보류했으나, 설계 문서(02-performance.md P-4)가 이미 "요약용 다운샘플 폴리라인만"이라고 방향을 정해뒀다는 사용자 지적으로 그 방식대로 구현.
- **수정**: `src/services/activity_service.py`의 `get_activity_detail()`이 반환하던 `streams`(전체 해상도, 활동에 따라 수천 포인트·650KB~1MB+)를 `_downsample_streams()`(신규, 균등 인덱스 선택, 최대 500포인트)로 다운샘플. `_route_previews`(목록 썸네일용, lat/lng만 32점)와 같은 균등 샘플링 원리이지만, 이번엔 고도·속도·심박 등 행 전체를 유지 — 요약 화면의 여러 차트(경로·고도·페이스·HR)가 전부 같은 `elapsed_sec` 축을 공유하므로 필드마다 다르게 샘플링하면 차트끼리 시간축이 어긋나기 때문. 원본 개수는 `stream_point_count`로 별도 반환해 화면에 실제 기록 밀도를 보여줄 수 있게 함. 전체 해상도가 필요한 스트림 탭(`get_activity_streams`)은 무변경.
- **파일 300줄 규칙**: `activity_service.py`가 이미(다운샘플 추가 전부터) 338줄로 기존 위반 상태였던 걸 발견 — `get_activity_detail`과 그 전용 헬퍼(`_downsample_streams`·`_build_metrics_by_category`·`_build_semantic_groups`)를 신규 `activity_detail_service.py`(187줄)로 분리하고 `activity_service.py`(182줄)에서 re-export(이 세션의 `metrics_explain.py`/`activity_service.py`(unified_activities 등) 분리와 같은 기존 관례 — check_docs.py의 "re-export shim 확인" 검사가 이 패턴을 전제하고 있음). 8개 파일이 `from src.services.activity_service import get_activity_detail`로 임포트 중이라 시그니처는 그대로 두고 내부만 옮김.
- 프론트: `ActivityDetail` 타입에 `stream_point_count: number` 추가. `library/[id]/+page.svelte`의 포인트 수 표시를 다운샘플 후 개수 대신 `stream_point_count`(원본)로 바꾸고, 다운샘플됐을 때만 "(차트는 N개로 다운샘플)" 문구를 덧붙임 — 실제 기록 밀도를 숨기지 않으면서 차트가 왜 부드럽게 안 보일 수 있는지 단서를 남김.
- 테스트 1건 추가(`test_get_activity_detail_streams_downsampled_over_500_points`): 1200포인트 시드 후 `streams`는 500개·`stream_point_count`는 1200 그대로, 처음·끝 `elapsed_sec` 보존, 정렬 유지 확인.
- **실제 브라우저 확인**: 3,600포인트짜리 합성 롱런(3시간) 시드 → 활동 상세 페이로드 실측 **1.1MB(전체 해상도 가정 시) → 159KB**(약 86% 감소, curl 직접 확인). Playwright로 요약 탭 로드 — 콘솔·페이지 에러 0건, "3,600개 포인트 (차트는 500개로 다운샘플)" 문구 정확히 표시, RouteMap·구간 차트·고도 프로필·페이스/HR 흐름 전부 정상 렌더(스크린샷 확인). 차트 선이 다소 들쭉날쭉해 보인 건 합성 데이터 자체가 정확히 200틱 주기로 반복되게 만들어서 다운샘플 간격과 우연히 겹쳐 생긴 앨리어싱(테스트 데이터의 인위적 한계) — 실제 GPS/HR 기록은 이런 정밀 주기성이 없어 해당 안 됨.
- **검증**: `pytest tests/ -q` 1872 pass·247 skip·무관 기존 실패 4건만 그대로(이번 세션 내내 확인해온 것과 동일 4건). `npm run check`(0 errors) · `npm run test:unit`(227 pass) · `npm run build`(성공) · `python3 scripts/check_docs.py`(신규 파일 미등록 에러 1건 발견 → `gen_files_index.py` 재생성으로 해소, Errors 0) · 위 브라우저 확인.
- 이걸로 P-3·P-4·P-5 전부 완료 — **2-6(성능) 로드맵 전 항목 종료**. 남은 건 narrative를 애초에 빠르게 만드는 백엔드 캐시 워밍(설계 결정 필요, 4차에서 이미 "느려도 안 막음"까지는 해결)뿐.

### 2-6 세부 (6차 — 활동 상세·스트림 ETag 조건부 GET, 사용자 "사용자 늘어날 것 감안하면 캐시 방식이 맞는" 지적으로 추가)
- 사용자가 5차(스트림 다운샘플) 완료 보고에 "지도 곡선 같은 걸 매번 다시 그릴 필요가 있나 / 원본 스트림을 매번 보낼 필요가 없을 것 같다"고 지적 — 다운샘플은 페이로드 크기만 줄였을 뿐, 안 바뀐 활동을 재조회할 때마다 서버가 매번 새로 계산해서 매번 통째로 다시 보내는 근본 낭비는 그대로였음. 사용자가 늘어날수록 이 비용이 누적된다는 지적에 동의해 진행.
- **왜 `updated_at` 컬럼으로 버전 판단을 안 했는지**: `activity_summaries.updated_at`은 INSERT 시 기본값만 있고 실제 UPDATE 경로(dedup 병합, 재동기화 등)에서 갱신되는 코드가 없어 신뢰 불가(조사로 확인) — 대신 **응답 본문 자체의 해시를 ETag로 쓰는 방식**을 선택. 내용이 조금이라도 바뀌면 해시가 달라져 자동으로 다시 내려가므로 별도 무효화 로직·버전 컬럼이 필요 없고, `updated_at` 신뢰성 문제에서 자유로움.
- **구현**: `src/api/__init__.py`에 `api_ok_cacheable()` 추가 — `jsonify` 응답에 `response.add_etag()`(Werkzeug 표준, 본문 해시) + `response.make_conditional(request)`(요청에 `If-None-Match`가 같으면 자동으로 본문 없는 304 반환)를 적용. `routes_library.py`의 활동 상세(`GET .../activities/<id>`)·스트림(`GET .../activities/<id>/streams`) 두 엔드포인트만 `api_ok` 대신 `api_ok_cacheable`로 교체 — 이 둘이 이번 2-6 작업 내내 다룬 무거운 페이로드였고, Today·메트릭 브라우저 등 매번 값이 실제로 바뀌는 엔드포인트는 캐싱해도 이득이 없어 그대로 둠.
- **프론트 변경 없음**: 브라우저의 `fetch()`가 HTTP 캐시·조건부 요청(`If-None-Match`)을 기본으로 처리해줘서 `apiFetch()` 클라이언트 코드를 손댈 필요가 없었음 — 304를 받아도 브라우저가 캐시에서 body를 복원해 호출 코드엔 평소처럼 200+정상 데이터로 보임.
- 테스트 2건 추가(`test_get_activity_detail_etag_304_on_revalidate`, `test_get_activity_streams_etag_304_on_revalidate`): 첫 요청의 `ETag`를 `If-None-Match`로 재요청하면 304·빈 본문 확인.
- **실제 브라우저로 확인**: curl로 ETag 재검증 → 실제 304 응답 확인. Playwright로 활동 상세 페이지 첫 방문→다른 페이지 이동→재방문 후 `request.sizes()`(실제 네트워크 전송 바이트, JS에 보이는 논리적 body 크기와 다름)로 확인한 결과 **첫 방문 `responseBodySize: 159458` → 재방문 `responseBodySize: 0`**(실제로는 304로 응답, 브라우저가 캐시에서 복원해 페이지엔 정상 데이터로 보임) — 설계한 대로 재방문 시 실제 전송량이 0에 가까워짐을 확인.
- **검증**: `pytest tests/test_api_library.py -v` 29 pass. 전체 `pytest tests/ -q` 1874 pass·247 skip·무관 기존 실패 4건만 그대로. `python3 scripts/check_docs.py` Errors 0.

### 3-1 세부 (1차 — 판정 함수 통합 `readiness_decision()`, 사용자 "진단 및 설계에 따른 우선순위에 따라 해야지"로 자체 판단해 착수)
- 2-6(성능) 완료 후 2-3(전환 스위치)은 백로그 확정됐으므로, 로드맵 우선순위(`99-summary.md` §7 순서 원칙)상 다음은 **3-1 Today IA**(`10-today/design.md` §9 S3, size L). 구현 순서를 4단계(①판정 함수 통합 ②`TodayHero`/`ReadinessGauge` ③레이스 허브 분리 ④`WeekStrip`+스트리밍 확장)로 쪼개 가장 위험이 적은 ①부터 진행.
- **문제 진단**: 같은 날 컨디션 판정이 코드 3곳에서 독립적으로 이뤄지고 있었음 — (a) `today_service.get_today_briefing()`은 TSB 등급(`bands.py`)만 봄, (b) `chat_engine_rules._respond_training_recommendation()`은 CRS 등급 + TSB를 별도 하드코딩 임계값(`bands.py`와 불일치)으로 봄, (c) `adjuster._fatigue_level()`은 wellness(BB/수면/스트레스)+TSB를 결합한 스코어링으로 판정하고 실제 당일 계획 다운그레이드에 씀. design.md §4가 지적한 "Today는 핵심 세션 권함, Coach는 항상 휴식 권함" 모순의 근본 원인.
- **구현**: `adjuster.py`의 wellness/TSB 조회 + 피로도 스코어링(`_get_todays_wellness`/`_get_latest_tsb`/`_fatigue_level`)을 신규 `src/training/fatigue.py`로 그대로 이관(로직 변경 없음, `adjuster.py`는 이 모듈을 import해서 씀 — `adjust_todays_plan()` 동작 100% 동일). 그 위에 `readiness_decision(conn, date=None, tsb=None)` 신규 — wellness+TSB 결합 피로도(`fatigue_level`)가 moderate/high면 그 헤드라인이 TSB 단독 등급보다 우선하고, low일 때만 기존 TSB 등급 헤드라인(`_TSB_HEADLINES`, `today_service.py`에서 이관)으로 폴백. `tsb` 인자를 옵션으로 받아 호출부가 이미 조회해둔 값(Today의 대시보드 서비스 exact-date 값)을 그대로 쓸 수 있게 해 TSB 조회 시맨틱 차이(adjuster는 날짜 이전 최신값 폴백, 대시보드는 정확히 그 날짜만) 충돌을 피함.
- **적용 범위(의도적으로 좁힘)**: `today_service.get_today_briefing()`만 이 함수로 교체(가장 낮은 위험 — 읽기 전용 표시 경로). `chat_engine_rules.py`(Coach 실시간 채팅 응답 문구)와 `adjuster.py`의 실제 계획 다운그레이드 결정 로직은 이번 라운드에서 건드리지 않음 — 각각 별도 검증이 필요한 더 위험한 후속 작업으로 남김(라이브 채팅 문구·실제 DB 변경 동작에 영향).
- 테스트 신규 `tests/test_fatigue.py` 4건: 데이터 없음→"수집 중" 폴백, 웰니스 나쁨+TSB 좋음(예: "신선")에도 피로 헤드라인이 우선됨(모순 재현 케이스), 피로 낮을 때 TSB 헤드라인 폴백, 호출부가 tsb를 직접 넘기면 재조회 안 함.
- **검증**: `pytest tests/ -q` 1878 pass·247 skip·무관 기존 실패 4건만 그대로(`test_autopilot_run_unit.py` 워크트리 경로 3건 + `test_plan_creation.py` 날짜 의존 1건 — base 브랜치에서도 동일하게 실패함을 `git stash`로 재확인). `python3 scripts/check_docs.py`(신규 파일 미등록 에러 2건 → `gen_files_index.py` 재생성으로 해소, Errors 0).
- **남음**: 화면(프론트) 변경 없음 — 이번 1차는 백엔드 판정 통합까지. 다음은 ②`TodayHero.svelte`/`ReadinessGauge.svelte`(design.md §7.1 신규 컴포넌트, `RecommendationCard`/`ScoreRing` 대체).

### 3-1 세부 (2차 — ② 히어로·게이지·Today 재구성, 설계서 있는 항목은 바로 구현하라는 지시로 진행)
- **백엔드**(efc8ff4): `today_readiness.py`(UTRS/CIRS/TSB 값·`delta_1d`·서버 등급 `status`/`status_label`·provider, 값 없으면 None), `today_hero.py`(`build_week`·`build_briefing_state`·`build_today_extras`). `/api/v1/today` 응답에 `as_of{basis,date,computed_at}`·`readiness`·`week_compliance`가 추가되고 `briefing`에 `state`(pre/done/extra/rest/no_plan/race_week/race_day)·`target_date`·`verdict`·`today_result`·`session`·`adjustment`·`caveats[{code,provider,days}]`가 붙음. 등급은 `metrics.bands.grade()` SSOT만 사용 — 프론트에 임계값 없음. 신규 판정 로직 없음(`readiness_decision`/`adjust_todays_plan` 조합만).
- **설계 편차**: `week_compliance.days[].state`에 `substituted`를 별도 상태로 두지 않고 원래 상태(done/partial…)를 유지한 채 `substituted: true` 플래그를 추가 — 대체 수행이어도 이행 여부 판정을 잃지 않게 하기 위함. `race_summary`·`today_result.outcome_label`은 ③(레이스 허브 분리)로 이월(현재 null).
- **프론트**: `TodayHero.svelte`(상태별 카피·세션·조정 배지·caveat 문구는 프론트가 code로 생성)·`ReadinessGauge.svelte`(UTRS=링, CIRS=3구간 트랙+마커, TSB=양극 반원, 빈 게이지 "수면·HRV 데이터 수집 중")·`TodayRecent.svelte`·`TodayNarrative.svelte`·`lib/todayHero.ts`(순수 헬퍼, 노드 테스트 7건). B3 헤더에 "아침 기준 · 9월 29일 (화)" + "RunPulse 계산" 배지 1회. `today/+page.ts`는 실패를 throw해 캐시에 남기지 않고 `errorKind`('empty' 온보딩 / 'failed' 재시도)로 분리(design §6.1), `+page.svelte`를 히어로+레이스허브+빠른입력 / 게이지·최근활동 / 폼차트+내러티브 2열로 재구성.
- **실제 브라우저 확인**(Playwright, Flask synth DB + 빌드 산출물, 데스크톱 1280·모바일 390): pre 상태 히어로·게이지 3종·최근 활동·FormChart·내러티브, 게이지 클릭 → `?drill=m.cirs` 드릴 패널, 빈 DB(no_plan 히어로 + 게이지 "수집 중" + 온보딩 카피). `page.route()`로 `/today` 응답을 변형해 done(오늘 완료·계획의 101%·다음 세션)/extra/rest/race_week/race_day/다운그레이드 배지+caveat 6종 렌더 확인, 500 응답 → "오늘 권고를 불러오지 못했어요" + "다시 시도" 클릭 시 정상 복구 확인. 페이지 에러 0건.
- **검증**: `pytest tests/ -q` 1887 pass·247 skip·기존 실패 4건만 동일(`test_autopilot_run_unit` 3 + 날짜 의존 `test_plan_creation` 1). `npm run test:unit` 234 pass · `npm run check` 0 errors · `npm run build` 성공 · `check_docs.py` Errors 0.
- **남음**: 히어로 260px 스켈레톤(B1)은 아직 없음(페이지 단위 로드라 체감 영향 작음, ④ 스트리밍 확장 때 함께). `RecommendationCard`/`ScoreRing`은 Today에서 미사용이 됐으나 다른 곳 사용 여부 확인 후 삭제 예정.

### 3-1 세부 (3차 — ③ 레이스 허브 분리, 설계서 있는 항목은 바로 구현하라는 지시로 진행)
- **백엔드**(c5de529): `today_hero.build_race_summary(conn, day, hub=None)` → `/today`의 `race_summary`{days_left,name,distance_km,pred_sec,low_sec,high_sec,range_kind,confidence,target_sec} (목표 없으면 None). 범위는 자체 추정 행의 모델 범위라 `range_kind='model_envelope'`(보정된 80% 구간 전에는 "확률 구간"이라 부르지 않음, design §2.6).
- **프론트**: Today의 `RaceHub` 카드를 삭제하고 B4 한 줄 `RaceSummaryLine`("D-70 · 예측 1:46 · 목표 1:45 ›")으로 축소. 상세는 신규 라우트 `/v2/today/race`(`RacePredictionSummary` 예측 기록·목표 격차·90일 추이 + `PredictionBasis`, `PredictionCompare`, `RaceMorningForm` 시나리오·TSB 추이 링크). "검토 중 알고리즘" 후보는 기본 접힘 → 허브의 토글(localStorage `runpulse:showCandidates`)로만 노출. 대회 확인은 `/v2/today/race/races`로 분리하고 저장 시 "대회 표시를 저장했어요 · 예측에 반영됩니다 [되돌리기]" 토스트 + undo, 로드/저장 실패는 `role=alert`(재시도). 무목표 = 등록 유도 카드, 조회 실패 = `ErrorState` 재시도(design §6 두 상태 분리).
- **실제 브라우저 확인**(Playwright, 합성 DB 3종: 예측 시드/목표 없음/기본): B4 한 줄 3상태(예측 있음·없음·조회 실패+재시도), 허브 데스크톱 1280(2열)·모바일 390(scrollWidth 390, 가로 스크롤 없음), 허브 실패(alert+재시도)·무목표, 후보 토글 localStorage 유지, 허브→대회 목록 이동, 대회 칩 "전력" 클릭 → aria-pressed·토스트·되돌리기 → 원복 확인, 콘솔·페이지 에러 0건(중단 라우트로 유도한 ERR_FAILED 제외).
- **검증**: `pytest tests/ -q` 1891 pass·247 skip·기존 실패 4건만 동일. `npm run test:unit` 237 pass · `npm run check` 0 errors · `npm run build` 성공 · `check_docs.py` Errors 0.
- **이월(설계서 P2 이하)**: 목표 달성 가능성(필요 개선 %)·대안 목표, 볼륨 민감도("주 +10km 시 약 −n분"), 레이스 당일 예상 기온 환산, 직전 마라톤 대비 기준선, explain API의 `race_pred_marathon_sec`·`x.taper` 드릴(현재 허브는 라이브러리 TSB 추이로 링크), B1 히어로 260px 스켈레톤·히어로 내부 오류 상태, Today 로더의 `getRaceHub()` 중복 호출 제거(④에서 `GET /today/form-chart` 통합과 함께).

### 3-1 세부 (4차 — ④ 주간 스트립·스트리밍 확장·빠른 입력, 설계서 있는 항목은 바로 구현하라는 지시로 진행)
- **스트리밍**(5bfd792): `today/+page.ts`는 `getToday()`만 await, `narrative`·`nextSession`·`formChart`·`raceHub`는 Promise로 넘겨 `{#await}` 블록 단위 스켈레톤/`ErrorState compact`+재시도. `WeekStrip`(월~일 7칸·핵심 n/m), `TodayNextSession`, `TodayFormChart`, `swrEvict`(실패 시 캐시 제거) 추가, `NextSessionCard`의 주간 점 삭제.
- **B2 빠른 입력**: 피로 숫자 탭 = 즉시 저장(`pickFatigue`), 통증·메모는 `+ 더하기` 뒤, `✕ 나중에`는 날짜별로 `localStorage`(`rp:checkin-later:<date>`, `lib/checkinDismiss.ts`, 노드 테스트 3건)에 기억해 오늘은 다시 띄우지 않음. `QuickInput`의 `dismissDate`는 opt-in이라 Coach 페이지에서는 접히지 않음(1탭 저장은 Coach에도 적용). 저장 성공 시 `swrEvict('app:today')` + `invalidate('app:today')`(design §3 B2 "저장 후 invalidate") — 피로 값이 히어로 판정에 반영됨. `retry`도 캐시를 먼저 비워야 "다시 시도"가 실제로 재요청함(브라우저 검증 중 발견·수정).
- **B1 히어로**: 최소 높이 260px, 브리핑 `state`·`headline`이 모두 없으면 "오늘 권고를 불러오지 못했어요 · [다시 시도]". 별도 히어로 스켈레톤은 만들지 않음 — `today`를 `load`에서 await하므로 렌더될 일이 없는 죽은 코드가 되기 때문(design §6 B1의 스켈레톤 항목은 페이지 단위 로드로 충족).
- **빈 DB 수정**: 메트릭 추이 404(데이터 없음)가 "차트를 불러오지 못했어요"로 뜨던 것을 빈 추이로 처리해 블록 숨김(design §6 두 상태 분리).
- **실제 브라우저 확인**(Playwright, 합성 DB): 모바일 390 접힘 카드→펼침→`✕ 나중에`→새로고침 후에도 숨김, 데스크톱 1280 피로 4 탭 → POST `{"fatigue":4}` 즉시 저장·요약 접힘, `+ 더하기`로 통증·메모 저장(`{"fatigue":4,"pain":"mild","note":...}`), `/today` 응답 변형으로 히어로 오류 상태 + 260px + 재시도 복구, 빈 DB 오류 카드 없음. 콘솔·페이지 에러 0건.
- **검증**: `npm run test:unit` 247 pass · `npm run check` 0 errors · `npm run build` 성공 · `check_docs.py` Errors 0.

### 3-1 세부 (5차 — Coach 채팅·계획 조정 판정 통합, 라이브 영향 항목)
- **adjuster**: `adjust_todays_plan`이 `_fatigue_level`/`_get_latest_tsb`/`_get_todays_wellness` 3회 개별 호출 대신 `readiness_decision()` 1회로 피로도·TSB·웰니스를 얻는다 — 판정 소스가 Today·Coach와 하나.
- **`src/ai/chat_readiness.py` 신규**: `attach_readiness`(컨텍스트에 판정+조정 계획 부착, 실패 시 None), `decision_lines`(headline+근거), `plan_line`(원 계획 → 조정 유형·사유). `ai_context.build_context`/`format_context_text`와 `chat_engine_rules`(훈련 추천·회복 응답·`recovery_advice` 칩)가 이를 사용 → 채팅 문구가 Today 히어로와 동일 headline·근거.
- **제거**: `chat_engine_rules`의 회복 등급 임계값 기반 문구(Today와 모순되던 별도 판정). 판정 데이터 없으면 "회복·부하 데이터가 없어 판정할 수 없습니다" 안내.
- **검증**: `pytest tests/` 1894 passed · 4 failed(기존 `test_autopilot_run_unit` 3 + 날짜 의존 `test_plan_creation` 1, 이번 변경 무관) · `check_docs.py` Errors 0. 합성 DB 복사본에서 정상(BB 높음: 채팅 "컨디션이 좋습니다", 인터벌 9.0km 유지)·고피로(BB 20, 수면 30: Today verdict=down 인터벌→휴식, 채팅 "피로가 과도합니다… → 조정: rest")가 일치함을 확인. 실 DB는 건드리지 않음(읽기 전용 판정).

### 3-2 세부 (Coach 엔진 투명성·P8, `30-coach-chat/design.md` S1 — 설계서 있는 항목은 바로 구현하라는 지시로 진행)
- **백엔드**(8b4fe1b·b84ce66·7fe38af·b9d9e3e): `ChatResult`/`EngineInfo`/`Attempt`(`chat_engine_result.py`), 체인은 동의한 provider만(+`fallback_enabled` 시 폴백), 전체 예산 45초, 모델 ID를 config로 일원화(기본 `gemini-2.5-flash` — 운영 404 원인이던 `gemini-2.0-flash` 폐기), `engine_json` 저장, `GET /coach/engine`·`PUT /coach/consent`·`POST /coach/threads/<tid>/messages/<mid>/regenerate`. 동의 없으면 `rule_only`(reason `no_consent`). v1 `provider="rule"`은 더 이상 gemini/groq를 부르지 않음(`rule_by_choice`).
- **프론트**: `lib/coachEngine.ts`(reasonText·needsConsent·engineLineText·bannerFor·visibleScope, 단위 테스트 5), `components/coach/`(EngineLine·DegradedBanner·ScopeSheet·EngineSheet·MessageBlock). 홈·스레드·새 채팅 입력창 위 엔진 한 줄, 첫 LLM 전송 전 동의 시트(provider 변경 시 재동의), 범위 시트 토글 3종(메모 제외·도구·폴백), 폴백 메시지 앰버 배너 + `[AI로 다시 생성]`·`[원인 보기 ›]`, 연속 3회 폴백 시 H0 배너.
- **검증**: 백엔드 `pytest tests/` 1939 passed · 247 skipped · 4 failed(기존). 프론트 unit 252 · `npm run check` 0 errors · build OK · `check_docs.py` 통과. 합성 DB 서버 + Playwright로 홈 플로우 5·스레드 플로우 11 항목 통과(동의 시트→동의 PUT→전송 재개, 폴백 라벨·배너·원인 시트·재생성, degraded 배너, `rule_by_choice`/`rule_only` 라인, 스레드 전송 동의 게이트 0 send).
- **운영 반영 완료**(2026-10-01 23:42, 98123e3): 모델 404 수정 포함.

### 3-3 세부 (Coach 답변 근거 v2·S2, `30-coach-chat/design.md` §4.4·§7.1~7.4·§9)
- **백엔드**(e984458): `services/coach_evidence.py` — 규칙 경로는 판정 근거+오늘 계획+체크인, LLM 경로는 본문이 인용한 값(지표 키워드+반올림 오차 내 숫자 일치)만 남기고 체크인은 항상(`pinned`). 항목마다 `role`(supports|caveat, 판정 방향과 비교)·`snapshot{value,computed_at,version,as_of}`·`drill`. 조회 시 같은 as_of의 현재값을 다시 읽어 `current`·`drifted`(|Δ| ≥ max(5, |then|×0.25) / 부호 반전 / 등급 변화). 스냅샷 없는 옛 메시지는 `role:"legacy"`·`drill:null`·`evidence_legacy:true`.
- **프론트**: `lib/answerEvidence.ts`(순수 헬퍼, 노드 테스트 5건), `EvidenceRow.svelte`(칩 2~3개 + "+n 근거"/접기, 체크인 칩은 항상 노출, caveat는 "반대 신호" 라벨+점선 테두리로 뒤에 배치, legacy 안내 "당시 Today 근거 — 이 답변의 입력과 다를 수 있어요"), `MessageBlock`의 drift 배너("답변 이후 데이터가 바뀌었어요 · TSB −10.7 → +6.2"), `DrillPanel`의 답변 칩 스냅샷 줄("답변 당시 −10.7 (9/25 10:51 계산 · formula_v1) → 현재 +6.2 (…재계산 · …)" + 값이 다르면 앰버 점과 "이후 데이터 동기화·재계산으로 값이 바뀌었어요"; 답변 칩에서 연 단일 slug·scope 일치 때만). 투영 칩(`race_form_projection`)은 "계획대로 가면 레이스 아침 폼 약 +N" 완곡 문구, 접힘 상태에서는 숨김.
- **설계 편차**: 투영 칩의 도착지 D2 `x.taper` 패널이 아직 없어 `/v2/today/race`(레이스 허브의 "레이스 아침 폼" 시나리오)로 연결. `x.taper` 드릴 신설 시 `chipTarget`만 바꾸면 된다.
- **실제 브라우저 확인**(Playwright, 합성 DB Flask + 빌드 산출물, 모바일 390, Coach API는 `page.route()`로 근거 시나리오 주입): 근거 행 2개, 체크인 pinned 노출·"반대 신호" 라벨, "+n 근거" 토글, 접힘 시 투영 칩 숨김/펼침 시 완곡 문구, legacy 안내, drift 배너, 칩 클릭 → `?drill=m.tsb@…` + 스냅샷 줄·변경 안내, 투영 칩 → `/today/race`, 페이지 에러 0건(11/11 통과). 스크린샷 3장(접힘·펼침·드릴)은 스크래치패드에만 두고 커밋하지 않음.
- **검증**: `pytest tests/` 1953 passed · 247 skipped · 4 failed(기존: `test_autopilot_run_unit` 3 + `test_compliance_pct_ignores_prior_goal_leftovers` 1) · 프론트 unit 257 · `npm run check` 0 errors · build OK.
- **운영 반영 완료**(2026-09-30 12:11, 266ebee): 저장 형식이 바뀌어(스냅샷 추가) 기존 메시지는 legacy로 표시. **정정**: 3-2의 스키마 v23(`chat_messages` 4컬럼 + `coach_consent`)이 이번 배포에서 처음 적용됐다(추가형·멱등). 사전 백업 `data/users/<user>/running.db.bak-20260930-pre-v23`(integrity ok). 배포 후 pansongit DB v23·컬럼 확인, 컨테이너 기동·트레이스백 0.
- **알려진 경고(기존)**: `pansong.us@gmail.com` DB는 테이블 없는 빈 파일(root 소유, user_version 0)이라 기동 시 "no such table: activity_summaries" 경고가 9/28부터 매번 뜬다. 이번 배포와 무관, 데이터 영향 없음.
- **Groq 404 원인·수정**: Groq `/models` 목록에서 기본 모델 `llama-3.3-70b-versatile`이 사라져 404. 기본값을 `openai/gpt-oss-120b`로 교체(`provider_common.DEFAULT_MODELS`, 테스트 추가). 운영 반영은 다음 "운영 반영" 지시 때.

### 3-4 세부 (Coach 규칙 핸들러·칩 플로우·S3, `30-coach-chat/design.md` §7.2~7.3·H3)
- **백엔드**(3cf3ab1·334abe8): `ai/coach_rule_handlers.py`(chip_id → 핸들러 12종 레지스트리, 데이터 있는 칩만 노출 `answerable_chips`), `coach_rule_plan_handlers.py`(목표 가능성·레이스 준비·이번 주 계획·테이퍼), `coach_rule_grade.py`(회복 등급 → 강도 5단계 + 체크인 하향), `coach_rule_types.py`(`CHIP_TEXT`·`RuleAnswer`). 오늘 판정은 `readiness_decision` 헤드라인을 첫 문장으로 써 Today와 어긋나지 않음. 자유 텍스트는 "AI가 연결되지 않아 답할 수 없어요" + 칩 3개(`free_text_answer`). 규칙 답변은 "AI 코치"라 부르지 않음.
- **API**: `GET /coach/suggestions`(최대 6), `POST /coach/threads`·`/messages`가 `chip_id` 입력 지원(미지 id·빈 본문 400), 어시스턴트 메시지에 `followups:[{chip_id,text}]`(최대 3, 스레드에서 이미 물은 칩 제외).
- **프론트**: 하드코딩 주제·후속 질문 제거. `lib/coachSuggestions.ts`(`CoachInput = string | CoachChip`, `messageBody`), Coach 홈 "바로 물어보기" 칩 = 즉시 전송(H3, 동의 게이트 통과 후 재개), 스레드 끝 followup 칩(마지막이 어시스턴트 메시지일 때만).
- **실제 브라우저 확인**(Playwright, 합성 DB 사본 + Flask + 빌드 산출물): 홈 칩 탭 → 스레드 생성·답변·근거 칩·후속 칩 3개, 후속 칩 탭 시 이미 물은 칩 제외, 자유 텍스트 폴백 안내, 9/9 통과.
- **검증**: `pytest tests/` 1982 passed · 247 skipped · 4 failed(기존 동일 4건) · 프론트 unit·`npm run check` 0 errors·build OK.
- **남음**: 체크인 입력 연결은 홈의 빠른 입력(QuickInput)이 이미 있어 별도 링크 미추가. LLM 성공 답변은 followups가 비어 있음(수용). `?from=coach`는 URL에만 붙고 스레드 페이지 전용 처리 없음.
- **운영 반영 완료**(2026-10-01 23:42, 98123e3): Groq 404 수정(9e858f7) + 3-4 전체.

### 3-5 세부 (Coach 비동기·스트리밍·오류 상태 기계·S4, `30-coach-chat/design.md` §6.2·§7.1~7.3)
- **스키마 v24**(bb5d593): `chat_messages`에 status·client_msg_id·스트림 이벤트 저장 컬럼 추가(중복 전송 멱등, DB 재생).
- **백엔드**(6c84641·75fc3a3·aee960e·968e967): `services/coach_async.py`(`_RUNS`·데몬 워커·`INLINE` 테스트 플래그·DB 재생), 전송 API가 pending 행을 즉시 반환(201, 중복 `client_msg_id`는 200), `GET /coach/messages/:id`(폴링)·`/stream`(SSE, `Last-Event-ID`/`?last_event_id=`, 15초 `: ping`, `X-Accel-Buffering: no`)·`POST /cancel`·`/regenerate {mode: ai|rule}`. 이벤트 `stage`·`delta`(40자 청크)·`evidence`·`done`·`error{fallback|error}`, 공급자 체인 45초 예산.
- **프론트**(62c6ee0·8648485): `coachStream.ts`(순수 리듀서: sending→pending→working→streaming→done + send_failed·slow·reconnecting·fallback·error·cancelled), `coachLive.svelte.ts`(메시지별 스트림 핸들·1초 슬로우 체크), `api/coachSse.ts`(EventSource, 연결 3회 실패 시 2초 `getMessage` 폴링), `StreamStatus.svelte`(단계 줄·[중단]·20초 침묵 시 "계속 기다리기 / 기본 답변 받기"·재연결 안내), `MessageBlock`(폴백 띠·[AI로 다시 생성]·취소 표시), `ChatComposer`(전송 실패 → 같은 `client_msg_id`로 재시도).
- **실제 브라우저 확인**(Playwright, 합성 DB 사본 + Flask + 빌드 산출물): 실서버 e2e(홈 → 스레드 생성·답변, 후속 질문) 2/2, 모킹 상태별 화면(단계 줄·재연결 안내·폴링 정착·스트리밍 정착·20초 슬로우 → 규칙 재생성·폴백·오류·취소·취소 POST·전송 실패/재시도) 17/17, 페이지 오류 0. 이 과정에서 결함 발견·수정: `'error'`가 서버 이벤트명이자 EventSource 연결 오류 이벤트라 연결이 끊길 때마다 실패 횟수가 0으로 초기화돼 폴링으로 내려가지 않았음 → MessageEvent만 이벤트로 취급(8648485).
- **알려진 한계**: 공급자가 비스트리밍이라 `delta`는 완성 답변의 청크 재생(실제 `stream=True`는 후속). SSE 연결이 gunicorn 스레드(8개)를 점유. LLM 성공 답변의 followups는 비어 있음. `?from=coach`는 스레드 페이지 전용 처리 없음. `engine_label("legacy_rule", …)`은 아직 "규칙 답변".
- **운영 반영 완료**(2026-10-01 23:42, 98123e3): Groq 404 수정(9e858f7)·`format_ko`(496981a)·3-4·3-5 전체. 스키마 v24(`pansongit` DB) 적용 확인, `pansong.us` 빈 DB(v0)의 마이그레이션 경고는 기존부터 있던 것.

## 3-10(일부) 코치에게 묻기 — 활동 컨텍스트 Coach (2026-10-02)
- **백엔드**(3618ff1 외): `coach_activity_context.py`(근거 카드 값 + 훈련 유형별 추천 질문 3개), `GET /coach/activity-context?activity=`, `chat_engine`이 활동 스레드의 자유 입력 프롬프트 앞에 활동 요약을 붙임(칩 프롬프트·규칙 폴백은 제외), `get_thread`가 `context` 반환.
- **프론트**: `/coach/new?activity={id}`(근거 칩 카드·추천 질문 3개·자유 입력·동의 게이트), 스레드 생성 시 `context={kind:'activity', ref}`, 활동 스레드의 ← 는 `/library/{id}`. 활동 요약 페이지는 모바일 하단 고정 56px CTA(탭바 위), md 이상은 인라인 링크. 순수 로직 `lib/activityEvidence.ts`(단위 테스트).
- **검증**: Playwright(합성 DB, 390px) — CTA → 근거 카드 → 추천 질문 탭 → 스레드 생성·`?from=activity`, 뒤로가기 `/v2/library/100`. 백엔드 2029 pass, 프론트 unit 268 pass·check 0 errors·build 성공.
- **남음**: 3-10의 RPE 입력(⑦ ADR·사용자 승인 필요)·`⋯` 메뉴. 활동 scope drill(`@a{id}`)은 이월.

## 다음 (2026-09-29 인수인계)

### 현재 위치
- 브랜치 `claude/project-thread-vgunp6`(OCI 워크트리 `/home/ubuntu/projects/RunPulse-p0`), 최신 커밋 f760456(Coach·계획 조정 판정 통합) + 이 문서 커밋. 푸시 완료, **운영 반영 완료(2026-09-30 06:50, 6982aa6 ff 병합 + `npm run build`, Dockerfile·의존성·DB 값 변경 없음 → 백업·재계산 불필요, 컨테이너 내부 스모크 통과)**. Phase 2 + 3-1 + Coach 판정 통합이 운영에 들어감.
- Phase 1·2 완료(2-3 전환 스위치는 백로그 유지). **3-1 Today IA 완료** — ①`readiness_decision()` ②TodayHero·ReadinessGauge ③레이스 허브 `/v2/today/race`(=3-17) ④주간 스트립·스트리밍·빠른 입력 ⑤Coach 채팅·adjuster 판정 통합. 상세는 위 "3-1 세부" 1~5차.
- 알려진 기존 실패(무관): `test_autopilot_run_unit` 3건, 날짜 의존 `test_plan_creation` 1건.

### 다음 착수 순서(99-summary §7, 설계서 있는 항목은 바로 구현·재확인 금지)
1. (3-2~3-5 완료) 3-6~3-10(Library) → 3-11~3-16(Plan) → 3-18(UTRS/CIRS v2). **3-16은 (판단 필요)** — D4 사용자 지시 없이 진행 금지.

### 이월(설계서 P2 이하 / 후속 정리)
- narrative 백엔드 캐시 워밍(설계 결정 필요), `MonthNarrative` 레이어링 검증, D1d 활동 scope, RRI 등급 SSOT 미등재.
- 미사용 후보 삭제 전 grep 확인: `lib/status.ts`·`metricMeaning.ts`·`raceHub.ts formBand`, `RecommendationCard`/`ScoreRing`.
- `today_result.outcome_label`(현재 None), `/today/form-chart` 통합(S4)과 Today 로더 `getRaceHub()` 중복 호출 제거, `emptyTrend` 단위 테스트(+page.ts), B1 히어로 260px 스켈레톤·내부 오류 상태.
- 목표 달성 가능성(필요 개선 %)·대안 목표, 볼륨 민감도, 당일 예상 기온 환산, 직전 마라톤 기준선, explain API `race_pred_marathon_sec`·`x.taper` 드릴.
- 3-1 ① 이후 `ai_context.py`는 300줄 초과 상태(기존) — 손댈 때 분리.
- P-1(gunicorn)·P-6(루트 라우팅)은 운영 인프라 변경이라 범위 밖으로 계속 제외.

### 세션 시작 절차·도구
- 워크트리에서 `git log --oneline -8`로 상태 확인 후 이 섹션부터 진행. `/home/ubuntu/projects/RunPulse`(운영 마운트)에는 쓰지 않는다.
- pytest: `<scratchpad>/venv/bin/python -m pytest tests/`(워크트리에서) · 프론트: `frontend/`에서 `npm run test:unit && npm run check && npm run build` · 문서: `python3 scripts/check_docs.py`, `python3 scripts/gen_files_index.py`.
- 화면 작업은 합성 DB 복사본으로 Flask+vite를 띄워 Playwright로 클릭 검증. 실 DB 수치 변경은 백업+복사본 검증 후에만.
- 커밋에 넣지 말 것: `config.json*`(`.bak-*` 포함), `.mcp.json`, `running.db`, 실데이터, `screenshots/`. 파일 이름으로 스테이징.
- 이번 세션 MCP 상태: Google Drive·Notion·Strava·Tredict는 claude.ai 커넥터 설정에서 인증해야 사용 가능, `pytest` MCP는 CONNECTION_CLOSED(작업에 영향 없음).

## 3-6 세부 (활동 상세 요약) — 프론트 완료 (2026-10-02)
- 완료: 공통 레이아웃·탭, 판정(ActivityVerdict), 타임라인, SplitBars(발산형)·RouteMap(구간색·km 마커·커서) 연동, 요약 페이지 재작성(서버 splits/series/hr_zones/environment/source_diffs 사용). 클라이언트 splits.ts·runStory 계산 삭제.
- 브라우저 검증(합성 DB): 지도·스플릿 클릭 선택/해제, 데스크톱·모바일 가로 넘침 없음. HR 존은 합성 시드에 데이터 없어 미확인.
- 판정 근거 칩 drill은 explain v2가 daily 범위만 지원해 기존 MetricBreakdown 유지(D1d 이월).
- 백엔드(2026-10-02): impact를 설계 형태로 재구성 — `{load(TRIMP), ctl_contribution(구 ctl_delta), tsb, tsb_as_of, similar{basis,n,pace_rank,…}, race}`. `streams`는 기본 응답에서 제외(`?include=streams`일 때만 500포인트), 프론트는 `detail.streams`를 쓰지 않아 영향 없음. 서브탭 parent()(g)는 이미 충족.
- 남음: `similar.basis`는 현재 `distance`만(설계의 `same_class`는 후보별 훈련 유형 조회 필요), ⑦ 피드백 저장(ADR·승인 필요), S1b 보류.

## 3-7 메트릭 목록 재구성 (진행 중)
- S1a 완료: `/library/metrics` 항목에 `name_ko`·`confidence_label`·`last_value_date`·`change{abs,pct,days}` 추가, `/trend`에 `best`/`worst`(higher_is_better 반영)·`baseline{mean,p25,p75,days}` 추가(peak 유지). 프론트 타입 반영.
- 표시명 SSOT 완료(ADR-018): `src/utils/metric_labels.py`(daily 84개 name_ko·abbr), explain API도 동일 SSOT 사용. 이름은 노출 필터가 아님(없어도 폴백으로 표시) — 목록 누락의 실제 원인은 기준일=MAX(scope_id)와 wellness 저장 12개 미노출.
- BUG 2건 수정 완료: ① 목록이 지표별 최신값(90일 창)+`last_value_date` 사용, 카드에 "MM-DD 기준" 표시 ② daily_wellness 저장 숫자 11개(취침 시각 제외) 목록·추세에 노출.
- S2 1차 완료: `/trend`에 `bands`(bands.band_ranges), TrendChart에 등급 밴드·기준선(p25~p75·평균)·7일 이동평균·결측 끊김·동적 aria-label(`trendChart.ts` movingAverage/splitOnGaps/spanRange). Playwright(`pw/s2_trend.mjs`) 검증. 좌측 y축 거터(최대·중간·최소)·주 경계 x틱(≤35일)·마지막 점 추가(`weekTicks`, 브라우저 검증). 남음(S2 나머지): 이벤트 마커(▲대회·◆버전)·Sparkline min_span(`spanRange`)·`?date=` selectedDate(S3와 함께).
- 남음: S1b PMC decay·GAP(보류), S3 설명·분해 인라인, S4 서브탭·검색·정렬("오늘 주목할 지표"), 운영 반영 2026-10-03 기록.
- S3 진행(2026-10-04): `?date=` 선택일 인라인 분해 패널(`BreakdownPanel`)·입력 지표 행 drillTerm(같은 기간·날짜로 이동)·데스크톱 8/4 열 + `MetricAbout`("이 지표는", 모바일 접힘) 완료, Playwright(`pw/s3_breakdown|s3_drillterm|s3_layout.mjs`) 검증. 남음: 요약 카드 문법 통일(현재/피크/3개월 변화), 예측계열 `ContributionBars`·`PredictionEvidence`, `#3b82f6` 토큰 교체.
- S3 추가(2026-10-04): 요약 카드 문법 통일(현재/선택 기간 변화(%·절대값·의미색)/피크(M월 D일)) + 하드코딩 #3b82f6→series 토큰. 남음: ContributionBars·PredictionEvidence(예측군), Today 시트 링크.
- S3 추가(2026-10-04): 예측군 `race_pred_*_sec` explain(`metrics_explain_prediction.py`: 신호별 환산·가중·범위·신뢰·제한 요인·다니엘스/탄다·기온별) + `PredictionEvidence.svelte`(BreakdownView에서 evidence 있을 때 표시). 커밋 351988a, 운영 반영 2026-10-04(ff-only·frontend build·컨테이너 재시작; Dockerfile 변경 없음). 남음: Today 시트 링크·`x.taper`·목표 달성 가능성, 브라우저 스모크(PredictionEvidence).
