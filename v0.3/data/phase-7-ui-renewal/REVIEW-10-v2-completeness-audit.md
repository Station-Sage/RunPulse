# REVIEW-10 — UI Renewal v2 완성도 감사 (2026-11-17)

사용자 체감: "UX 가 중간에 끊기고, UI 가 아쉽고, 적재 누락, 분석·인사이트 부족, 코치·플랜 부족, 스트림/Lap 이 가민과 불일치".
방법: 읽기 전용 감사 에이전트 3개(데이터·UX/UI·분석/코치/플랜) 순차 실행. 결론: **v3 로 바로 가지 않고 A→B→C 정비 후 D 를 v3 범위로**.

## 1. 데이터 적재 · Lap/스트림 (축 A)

| ID | 결함 | 근거 | 해결 방향 |
|----|------|------|-----------|
| A-1 | 스트림 `maxchart` 미지정 → 기본 2000 다운샘플 | `src/sync/garmin_activity_sync.py:264` | `maxchart` 명시(상한값) + 기존 활동 재수집 |
| A-2 | `elapsed_sec` 반올림 + `UNIQUE(activity_id,source,elapsed_sec)` + `INSERT OR IGNORE` → 같은 초 샘플 유실 | `garmin_extractor.py:341`, `db_setup.py:230`, `db_helpers.py:674` | 유일성 키를 `(elapsed_sec, sample_idx)` 또는 REAL 로 변경, 유실 카운트 메타 |
| A-3 | 요약 해시 동일 시 기존 활동 영구 스킵 → 스트림/Lap 백필 불가 | `garmin_activity_sync.py:163-173` | 스킵 조건에 스트림 payload 존재 포함 |
| A-4 | HR존·날씨를 응답 최상위에서 찾음(실제는 `summaryDTO` 중첩), `/hrTimeInZones` 미호출, 픽스처가 합성 구조 | `garmin_extractor.py:179,198,217` | 실구조 파싱 + 엔드포인트 호출 + 실구조 픽스처 |
| A-5 | Lap 의미: `lap_index` 덮어쓰기, `lap_trigger` NULL(오토/수동), Lap 시각 GMT vs 활동 로컬(9h), 옛 Lap 잔존, `duration_sec` 절삭 | `garmin_extractor.py:257,262,275,611-620`, `db_helpers.py:591-632` | `lap_kind` 컬럼 분리, 가민 lapIndex 보존, 로컬화, ingest 전 삭제 |
| A-6 | 동기화 구간이 UTC 날짜 기준 → KST 경계일 새벽 활동 누락 가능 | `garmin_activity_sync.py:62-73` | 1일 여유 |
| A-7 | 소스 병합: Strava 행을 열면 가민 Lap/스트림이 안 보임 | `activity_detail_service.py:105,132` | **사용자 결정**: Lap/스트림 canonical 소스 규칙 |
| A-8 | HRV 가 평균만 저장(전체 야간 readings 미수집) — 사용자 지적 | 소스 감사(§5)에서 확정 | 별도 항목, §5 참조 |

테스트 공백: `maxchart` 검증 없음, 실구조(`summaryDTO`) 가민 픽스처 없음, lap 시각·인덱스·트리거 테스트 없음, 기존 활동 스트림 백필 테스트 없음.

## 2. UX/UI (축 B)

원인은 구조: 공용 내비/CTA 레이어(`PageHeader`·`Button`·`SubTabs`·`EmptyState`)가 없어 화면마다 다음 행동·뒤로가기가 따로 결정됨. BACKLOG `[V2-AUDIT-INDIV]` 161건의 공통 원인.

| ID | 문제 | 근거 | 수준 |
|----|------|------|------|
| B-1 | 온보딩 일방통행: Step1 소스 연결·Step3 플랜 생성에서 welcome 복귀 없음, Step4 저장/완료 분리(입력 소실) | `Step1Connect.svelte:40,58`, `Step3Goal.svelte:9`, `Step4Baseline.svelte:53`, `welcome/+page.svelte:65` | 부분 수정 |
| B-2 | 같은 의도 CTA 가 다른 목적지(소스 연결·세션 상세·플랜 만들기) | `library/+page.svelte:50` vs `states.ts:38`; `TodayHero.svelte:48` vs `NextSessionCard.svelte:110` | 부분 수정 |
| B-3 | 뒤로가기 규칙·글리프 제각각(`from=`/context/고정 `← 코치`/breadcrumb/`‹`) | `library/[id]/+layout.svelte:35-47`, `coach/plan/[id]/+page.svelte:119` 등 | 구조 |
| B-4 | 플랜·데이터가 탭 밖(드로어)에만 있음, 서브탭 3구현 | `navTabs.ts:13-17`, `menuLinks.ts`, `library/+layout.svelte:8`, `data/+layout.svelte:16` | 구조 + **사용자 결정(탭 구성)** |
| B-5 | 빈/오류 상태 3패턴, 일부 다음 행동 없음 | `library/activities/+page.svelte:231`, `coach/plan/+page.svelte:65-73` | 부분 수정 |
| B-6 | 디자인 시스템 컴포넌트 층 부재(버튼 class 101종, h1 10종, 모서리 혼재) | `lib/components/ui/` | 구조 |
| B-7 | 체크인 QuickInput 3곳 중복, "코치에게 묻기" 이중 렌더 | `today/+page.svelte:142`, `library/[id]/+page.svelte:226,234` | 부분 수정 |

## 3. 분석 · 코치 · 플랜 (축 C/D)

원인은 계산 부족이 아니라 **해석·노출 결손**. 엔진은 Runalyze/TrainingPeaks 수준 이상.

| ID | 격차 | 근거 | 수준 |
|----|------|------|------|
| C-1 | 행동 힌트(action_hint) 지표 87개 중 6개 | `metric_label_texts.py:1`, `metric_display.py:32` | 보강 |
| C-2 | Coach LLM 컨텍스트에 Lap·스트림·플랜 이행 없음, 칩 질문은 도구 호출 꺼짐 | `chat_context_builders.py:17`, `chat_engine.py:92` | 보강 |
| C-3 | 계산만 되고 미노출 지표(teroi·tpdi·sapi·rtti·critical_power·training_strain) | `metric_browse_groups.py` | 보강 |
| C-4 | 플랜 HR존이 유형별 고정 매핑(`lthr_self` 미연결), 세션 rationale 없음 | `planner.py:211`, `planner_rules.py:64-68` | 보강 |
| C-5 | 코치 근거 칩이 "본문 인용 숫자"에만 의존 | `coach_evidence.py:1-6` | 보강 |
| D-1 | 능동 인사이트 경로 없음(`briefing.py` dead code, 적응은 조회 시 지연 평가) | `briefing.py`, `weekly_adapt_job.py` | **새 설계(v3 범위)** |

데이터 결함(A-1~A-5)이 디커플링·정지 제외·RE(confidence<0.8 숨김)·FEARP/WLEI 결측으로 분석 품질을 직접 떨어뜨림 → A 를 먼저.

## 4. 권고 순서와 사용자 결정

1. A 데이터 정비 → 2. B UI 뼈대(공용 컴포넌트+내비 규칙) → 3. C 해석 계층 보강 → 4. D 능동 인사이트(v3).
사용자 결정 필요: ① 순서·범위, ② A-7 Lap/스트림 canonical 소스, ③ B-4 하단 탭 구성.

## 5. 소스 수집 전수 감사 (HRV 포함)

사용자 지적: HRV 를 전체 데이터가 아니라 평균만 받음 → 확정. 다른 항목도 전수 확인(읽기 전용, 코드 근거). 상태: 미호출 / raw만(source_payloads) / 요약 반영.

**운영 경로 전제**: 웹 bg_sync(`src/sync/bg_sync.py:332-360`)는 Garmin `sync_activities` + `sync_wellness`(6개 엔드포인트) + `sync_vo2max_range` 만 호출. `sync_daily_extensions`/`sync_athlete_extensions`(training_status·endurance·hill·fitness age·LT·race_predictions·HR 타임라인·all-day stress·BB events·hydration·weigh-in·running tolerance·PR·stats)는 **CLI `src/sync.py --source garmin` 에서만** 실행(`src/sync/garmin.py:221-250`). 웹 사용자에게는 전부 "미호출". Intervals wellness 도 bg_sync 에서 미호출(`bg_sync.py:375` 활동만).

### Garmin
| ID | 데이터 | 상태 | 근거 | 가치 |
|----|--------|------|------|------|
| S-1 | HRV 야간 5분 readings(`hrvReadings[]`) | raw만 — `hrvSummary` 의 weeklyAvg/lastNightAvg/5MinHigh/baseline 만 | `garmin_extractor.py:447-451,577-597` | 상 |
| S-2 | HRV 7일 범위(`get_hrv_data_range`) | 미호출 | garminconnect:2366 | 중 |
| S-3 | 수면 단계 시계열(`sleepLevels`)·수면 중 HR/스트레스/BB/SpO2·호흡 epoch·`sleepScores` 세부 | raw만 — dailySleepDTO 합계/평균 11개만 | `garmin_extractor.py:435-445,524-560` | 상 |
| S-4 | Body Battery 시계열·charged/drained | raw만 — max/min 만 | `garmin_extractor.py:454-457,687-699` | 중 |
| S-5 | 하루 스트레스·HR 시계열, 일 min/max HR | raw만 / CLI 전용 | `garmin_extractor.py:460-462`, `garmin_daily_extensions.py:225-321` | 중 |
| S-6 | 안정시 HR 추이(`get_rhr_day/daily`) | 미호출 / user_summary raw만 | garminconnect:2275,2288 | 상 |
| S-7 | user_summary 94키 중 SpO2 평균·호흡·강도분·BB charged/drained·max stress | raw만. CLI 보완 UPDATE 가 `WHERE source='garmin'` 인데 `daily_wellness` 에 `source` 컬럼 없음 → OperationalError 삼킴 → **항상 미반영(버그)** | `garmin_daily_extensions.py:175-191`, `db_setup.py:156-190` | 중 |
| S-8 | 훈련 준비도 세부(feedback·recoveryTime·acwrFactor 등) | 5개만 추출. 라이브러리는 `list[dict]` 반환(garminconnect:2379), sync 가 `{"data":[...]}` 로 감싸고 extractor 는 `tr.get("score")` → **운영 0건 추출 의심(버그, 테스트는 dict 픽스처)** | `garmin_wellness_sync.py:118`, `garmin_extractor.py:544-560` | 상 |
| S-9 | 훈련상태·ATL/CTL/ACWR·VO2max 일별·레이스 예측·LT·지구력/힐 점수·피트니스 나이·running tolerance | CLI 전용(웹 미호출). VO2max 만 웹 반영 | `garmin.py:106-189`, `bg_sync.py:358` | 상 |
| S-10 | 일별 steps/intensity/spo2/respiration API, body_composition, 4주 로드 밸런스, 아침 준비도, HR/파워 존 설정 | 미호출 | garminconnect:2445,2434,2387,1270,2059,2041,2033,1472,3441 | 중 |
| S-11 | 활동 HR/파워 존(`hrTimeInZone_*`, `/hrTimeInZones`)·날씨(`/weather`) | 미호출 + 구조 오파싱 (= A-4) | garminconnect:3409,3417 | 상 |
| S-12 | **러닝 다이내믹스 스트림**(GCT·수직진동·보폭·수직비·케이던스), `directBodyBattery`/`directRespirationRate` | raw만 — `_KEY_MAP` 12키 제한 | `garmin_extractor.py:313-327` | 상 |
| S-13 | 랩 러닝 다이내믹스·`maxRunCadence` 등 | raw만 — 13+7 컬럼 외 미추출 | `garmin_extractor.py:244-272`, `garmin_lap_fields.py:12-24` | 중 |
| S-14 | 장비 상세(`get_gear/gear_stats`), 기온 min/max·날씨DTO, 운동 세트 | 미호출/미반영 | `garmin_activity_sync.py:155-158`, `garmin_api_extensions.py:97` | 중~하 |

요약 반영 정상: 활동 러닝 다이내믹스 평균, 파워(요약·랩·스트림), GPS(2000 다운샘플은 A-1).

### Intervals.icu
| ID | 데이터 | 상태 | 근거 | 가치 |
|----|--------|------|------|------|
| S-15 | 활동 intervals/laps(`/activities/{id}/intervals`) | 미호출 → **Intervals 랩 0건** | `intervals_activity_sync.py:81`, `base.py:63` | 상 |
| S-16 | 스트림 | 미호출(`include_streams` 무시) | `intervals_activity_sync.py:22-96` | 중 |
| S-17 | wellness: `hrvSDNN`·`avgSleepingHR`·`readiness`·soreness/fatigue/mood/motivation·`ctlLoad/atlLoad` | raw만 — `extract_wellness_metrics` 미구현. `sleepQuality`(1~4)를 `sleep_score` 로 저장(스케일 오류) | `intervals_extractor.py:157-176`, `base.py:81`, `intervals_wellness_sync.py:67-70` | 상 |
| S-18 | 존 시간·`icu_intensity`·활동 시점 atl/ctl, 날씨 키 | raw만 / 키 불일치 가능 | `intervals_extractor.py:84-152` | 중~하 |

### Strava / Runalyze
| ID | 데이터 | 상태 | 가치 |
|----|--------|------|------|
| S-19 | Strava laps·zones(HR/파워) | 미호출 → Strava 랩 0건 (`strava_activity_sync.py:96-104`) | 중 |
| S-20 | Strava splits_standard·photos·gear 상세 | 미반영 | 하 |
| S-21 | Runalyze 경로 이중화(`runalyze.py:/activity` vs `runalyze_activity_sync.py:/activities`, 후자 주석상 404), `marathon_shape` 키 불일치, `/metrics/*` 미호출 | 정합 불일치 | 중 |

## 6. 정비 설계 (제안 — 사용자 승인 전 착수 금지)

원칙: 테이블 재설계 없이 부분 수정 + 시계열 전용 저장소 1개 추가. 각 항목 ≥1 테스트, 실구조(실제 응답) 픽스처 사용, 단계별 커밋·BACKLOG 등록.

### 단계 A — 데이터 정비 (먼저)
- **A1 활동 상세 정확도**: A-1 `maxchart` 명시, A-2 유일성 키 `(elapsed_sec, sample_idx)`(마이그레이션 + 유실 카운트 메타), A-3 스킵 조건에 스트림 존재 포함, A-6 1일 여유. 기존 활동은 백필 잡(rate limit 고려, 일 N건 점증).
- **A2 Garmin 활동 파싱 정상화**: A-4/S-11 실구조 파싱 + `/hrTimeInZones`·`/weather` 호출, 실구조 픽스처로 교체. S-12 `_KEY_MAP` 확장(러닝 다이내믹스 5컬럼). S-13 랩 다이내믹스 컬럼 추가.
- **A3 Lap 의미 정리**: A-5 `lap_kind`(intensity)와 `lap_trigger` 분리, 가민 `lapIndex` 보존, 시각 로컬화, ingest 전 옛 Lap 삭제, `duration_sec` REAL.
- **A4 웹 경로 동기화 복원**: S-9 bg_sync 에 `sync_daily_extensions`(training_status·race_predictions·LT·RHR 우선) 포함. 요청 수·rate limit 예산 산정 후 점진 활성화.
- **A5 버그 2건**: S-8 훈련 준비도 list 응답 처리, S-7 `source` 컬럼 UPDATE 오류. 둘 다 실구조 응답 테스트 선행.
- **A6 일 단위 시계열 저장소 (HRV 포함)**: 신규 테이블 `wellness_series(date, source, kind, ts, value, meta)` — kind: `hrv_5min`·`sleep_stage`·`sleep_hr`·`body_battery`·`stress`·`hr_day`·`spo2`·`respiration`. 요약 컬럼에는 파생값만 추가(야간 HRV 최저/분포 p10·p90, 수면 중 최저 HR, 수면 단계 분 단위 합). S-1~S-6 소비. 저장량 추정 후(일 약 288×N 행) 보존 기간 결정 필요.
- **A7 Intervals/Strava**: S-15 `/intervals` → laps, S-17 wellness 주관 지표·SDNN·`sleepQuality` 스케일 교정, S-19 laps/zones. 우선순위는 낮음(가민 우선).
- 보류(후순위): S-10, S-14, S-16, S-18, S-20, S-21.

### 단계 B — UI 뼈대
`ui/PageHeader(back,title,actions)`·`ui/Button(variant)`·`ui/SubTabs`·`ui/EmptyState` 도입 → 뒤로가기 규칙·CTA 목적지 표 확정 → 온보딩 return_to(B-1) → 화면별 순차 적용(`V2-AUDIT-INDIV` 흡수).

### 단계 C — 해석 계층
action_hint 확대(87개 중 우선 20), Coach 컨텍스트에 Lap 요약·플랜 이행·HRV 분포 추가, 계획 HR존을 `lthr_self` 연동, 세션 rationale, 미노출 지표 노출. 단계 A 의 시계열(S-1~S-6)을 코치/지표가 소비.

### 단계 D — 능동 인사이트 (v3 범위)
이벤트 모델(`adjustment_triggers_v3.py` 신호 재사용) 별도 설계.

### 사용자 결정 필요
1. 단계 순서·범위(권고 A→B→C→D).
2. 소스 병합 시 Lap/스트림 canonical 소스(A-7). 권고: 가민 우선, 없으면 해당 행 소스.
3. 하단 탭 구성(B-4).
4. 시계열 보존 기간·백필 범위(A6): 권고 최근 400일 전체 + 이후 일 1회 증분.
5. 웹 bg_sync 확장 동기화의 Garmin 호출량 증가 허용 여부(rate limit/차단 위험).
