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

## 다음
Phase 1 완료. 2026-09-28 "오케이 이어서 진행" 지시로 Phase 2 착수. 2-1 대부분 완료, 2-2(셸 기반) 완료(위 세부의 스코프 판단 1건 확인 필요) — 2-3(전환 스위치 G0)으로 이동 전에 사용자 확인 대기.
