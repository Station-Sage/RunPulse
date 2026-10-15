# S4 계획 — FRS(ADR-050) · NRA(ADR-051) · TZ

상태: **승인 대기** (사용자가 "S4 진행" 하기 전에는 코드 수정 없음). 작성 2026-10-14.
상세 변경 파일 표·단계는 각 설계서(`patterns/data-freshness.md` §3·§4, `patterns/non-running-activities.md` §3·§4, `patterns/timezone-display.md` §3·§4)가 원본이다. 이 문서는 실행 순서·검증·롤백·선행 조건을 한곳에 모은 것.

범위 밖: 레거시 삭제 7종, 스키마 v37~v40 (사용자가 DB에서 직접 삭제 후 별도 진행). NRA-8(매처 HIIT 처리), README §5 정책 질문 1~3.

## 0. 진행 원칙
- 스트림 단위로 계획 → 승인 → 구현 → 보고 → 확인, 단계마다 push. PR 은 요청 시에만.
- 구현 중 정한 세부 사항은 decisions-table.md 에 `S4-n` 행(사용자 확인 필요)으로 기록.
- 스키마 변경 없음(SCHEMA_VERSION 36 유지). 운영 DB·외부 서비스 접근 없음.

## 1. 권장 스트림 순서와 근거
| 순서 | 스트림 | 이유 |
|---|---|---|
| 1 | NRA | 스키마·Calculator 변경 없음, 위험 최소. `family_clause` SSOT 가 HSR-12(`activity_counts`)의 선행 |
| 2 | TZ | 시간 표기 유틸이 FRS 의 '오늘 기준일' 판정(`reference_day`)에 쓰임. 기존 행 보정은 안 함(TZ-19 c) |
| 3 | FRS | Calculator 버전 상향 + 전체 재계산(운영 작업) 포함, 가장 위험. 앞 두 스트림이 안정된 뒤 |
순서 자체는 에이전트 제안이며 사용자 확인 필요(S4-1).

## 2. NRA (ADR-051) 단계
| # | 내용 | 주요 파일 | 테스트 |
|---|---|---|---|
| N1 | SSOT: `sport_family`·`family_raw_types`·`family_clause`·`SPORT_LABELS` | `src/utils/activity_types.py`(현재 85줄, 신규 함수) | 매핑 표 전수, HIIT=비러닝(NRA-7) |
| N2 | `run_totals.py` 신설, 주간·월간 러닝 합계 단일화 | `src/services/run_totals.py`, `week_digest.py`, `story_stats.py` | 비러닝 혼입 시 합계 불변 |
| N3 | `activity_display.py` 스포츠별 표시 계약, 상세·요약 | `activity_display.py`, `activity_summary_extras.py`, `activity_detail_service.py`, `activity_impact_service.py` | 스포츠별 필드 스냅샷 |
| N4 | `today_narrative.py` 분리(today_service 324줄→300 이하), 서사 | `today_service.py`, `today_narrative.py`, `_narrative.py` | 기존 오늘 화면 테스트 회귀 |
| N5 | 프론트 표시 | `activityDisplay.ts` 등 | vitest, `npm run check/build` |
- 롤백: 단계별 커밋 revert. 데이터 변경이 없어 안전.
- 사용자 선행 조건: 없음. 단 비러닝 라벨 문구(`SPORT_LABELS`)는 사용자 확인(TXT-1 과 함께 가능).

## 3. TZ 단계
| # | 내용 | 주요 파일 | 테스트 |
|---|---|---|---|
| T1 | `src/utils/timefmt.py` 신설 (`to_iso_instant`, `to_local_wallclock`) | timefmt.py, extractors | 경계값·DST·오프셋 없는 입력 |
| T2 | Strava CSV 활동별 타임존 체인 `strava_tz.py` (오프라인 임포트 전용, 피어 5a/폴백 5b) + `tz_peers.py`(60초 허용) | strava_tz.py, tz_peers.py, `strava_csv.py`(488줄, 분리 필요) | 피어 일치/불일치/폴백 |
| T3 | `strava_csv.py:384-387` 의 start_time 무조건 덮어쓰기 제거·보호(`tz_pinned`) | strava_csv.py, import_service.py | 재임포트가 보정값을 덮지 않음(활동 1327 유형) |
| T4 | `tz_backfill.py`(`tz_history`, `--revert-run`) 도구 — 기본 dry-run | tz_backfill.py, normalize_start_time.py | dry-run 무변경, revert 복원 |
| T5 | `reference_day.py` '오늘' 기준일 (TZ-1/17/18/21) | reference_day.py, today_service | 자정 경계 |
| T6 | 프론트 `format.ts`, 'time zone estimated'(TZ-8) | format.ts 외 | vitest |
- 롤백: 코드 revert. T4 는 실행 시 `tz_history` 로 `--revert-run`. 기존 행 자동 보정은 하지 않음(TZ-19 c).
- 사용자 선행 조건: **활동 1327 은 사용자가 백업 후 수동 SQL**(TZ-23). 백필 실제 실행(비 dry-run)은 사용자 승인·백업 후에만.

## 4. FRS (ADR-050) 단계
| # | 내용 | 주요 파일 | 테스트 |
|---|---|---|---|
| F1 | `metric_freshness_spec.py`/`metric_freshness.py` (`assess`/`assess_many`, fresh/partial/stale/missing, `min_version`, 상류 전파) | 신규 2개 | 레벨 전이, 상류 전파 |
| F2 | Calculator 신뢰도를 실제 입력에서 기록: rmr/rtti/crs 1.0→1.1, `algo_changelog.py`(`value_changed=False`), `signals.hrv_rolling_days`, changelog events | rmr.py, rtti.py, crs.py, algo_changelog.py, metrics_changelog_events.py | 버전·신뢰도, dictionary 재생성 |
| F3 | 소비처 연결 (읽기 시점 판정) | today_readiness, today_hero, coach_*, chat_readiness, metrics_browser_service, metric_display, race_hub_service, fatigue 등 | 서비스별 회귀 |
| F4 | BOOST 보류: `adjuster_v2` `boost_hold` 주입 + `plan_service.todays_adjustment_with_hold`, Hero `as_planned`+`hold_reason`, 해제 = BB·HRV 당일 + CRS fresh. `load_adjustment` 제거(V1-6) | adjuster.py, plan_service.py, plan_adjustment_service.py, views_training_loaders.py | 보류/해제/경계 |
| F5 (완료) | 서버 제공 `text`(배지·hold_headline·사유; FRS-23/27) + 프론트 | types/index.ts, todayHero.ts, freshness.ts, Svelte | vitest, build |
| F6 | 배포 후 전체 재계산 (사용자 작업) → 신선도 활성화 | `POST /api/v1/data/recompute {"scope":"all"}` | — |
- 롤백: 코드 revert + (재계산 후라면) 백업 DB 복원. 순서: 코드 배포 → 재계산 → 활성화. `scope:"90d"` 금지.
- 사용자 선행 조건: 재계산 전 DB 백업, 재계산 실행은 사용자가. FRS-28·FRS-26 확인.

## 5. S0 사실 확인 결과 (grep, 2026-10-14)
| 항목 | 결과 |
|---|---|
| `strava_csv.py:384-387` | 확인: start_time 을 COALESCE 없이 강제 UPDATE(docstring 에 UTC→KST 교정 목적). T3 대상 |
| 매처 `acts_by_date` | 확인: `src/training/matcher.py:76-83`, 날짜 키 리스트 구조 |
| `normalize_activity_type` | 확인: `race`·`treadmill`·`treadmill_running` → running. **HIIT 는 매핑 없음**(소문자 원문 `hiit` 그대로, strava_csv 는 "HIIT"→"hiit", unified_view 는 strength 군에 포함). NRA N1 은 `hiit` 를 비러닝으로 분류. 설계서 §9 "미확인" 해소 |
| `hrv_weekly_avg` 의미 | 확인: DB 컬럼 `daily_wellness.hrv_weekly_avg`, 라벨 "최근 7일 심박변이도 평균". utrs·adaptation 에서 소비. FRS-26 의미 확정은 raw payload 대조 필요 → **미확인**(S4-2) |
| Calculator confidence | `crs.py:209`, `rtti.py:77` 모두 `confidence=1.0` 하드코딩 → F2 필요성 확인. `rmr.py` 에는 confidence 문자열 없음 → 구조 별도 확인 **미확인** |
| `race_briefing` | 확인: `race_hub_service.py:146`, `today_service.py:118-119` 에서 호출. FRS-27 코드/텍스트 통일 대상 |
| 신규 모듈 | `timefmt.py`·`metric_freshness.py`·`run_totals.py` 모두 현재 없음(신규 생성 예정) |

## 6. 사용자 확인 필요 (S4-n)
- S4-1: 스트림 순서 NRA → TZ → FRS (또는 다른 순서).
- S4-2: `hrv_weekly_avg` 의미(FRS-26)를 raw payload 로 확인하는 시점 — 사용자가 운영 DB 값을 알려주거나 F2 착수 전에 결정.
- S4-3: HIIT 를 비러닝으로 처리하며 매처는 그대로(NRA-7/8) — 설계서 결정 재확인.
- S4-4: `strava_csv.py` 488줄 → 300줄 규칙 때문에 분리가 필요(T2/T3 와 함께 분할).

## 7. 공통 검증 (단계마다)
`.venv/bin/python -m pytest tests/ -q -p no:cacheprovider` (기준 3255 passed / 240 skipped), 프론트 `npm run check`·`test:unit`(기준 479)·`build`, `gen_files_index.py` → `check_docs.py`(기준 0 errors / 64 warnings), `ls data/users` 전후 비교.

승인 요청: "S4 진행" 과 함께 스트림 순서(S4-1)와 시작 스트림을 알려주시면 첫 스트림의 세부 plan 부터 제시합니다.
