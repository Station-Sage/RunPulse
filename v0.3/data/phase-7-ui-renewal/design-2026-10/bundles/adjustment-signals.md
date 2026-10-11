# 조정 제안 근거 신호 확장 (adjustment-signals)

> 작성 2026-10-11 · 상태: 설계 확정(ADJ-1~18·NEW-1~3·NEW-38·V1-1·V1-2·V1-13·PLN-23 결정 반영, 구현 전) · 관련: [ADJUSTMENT-SOURCE-CRS-LABEL], [CRS-EVALUATE-MISSING], FRS-12~21(`patterns/data-freshness.md` §2.6·§2.7), ADR-035, `bundles/adjustment-new-signals.md`, `bundles/race-calendar.md`
> 전제(결정됨): `crs.evaluate()` 복원(저장 CRS·신선도 읽기 전용), CRS stale/게이트 불명 시 BOOST만 보류(FRS-12 c', `adjuster_v2`), 보류 범위 A1+A2(FRS-15), 해제 = BB·HRV 당일 확보+CRS fresh(FRS-17), `plan_service.todays_adjustment_with_hold` 래퍼(FRS-18), Hero `as_planned`+`hold_reason` 중립 회색 한 줄(FRS-19·21), 사유 한 줄·Coach 근거 한 줄(FRS-16·20).
> 변경 이력: 2026-10-11 초안 · 2026-10-11 ADJ-1·2·4 결정 반영(신호 목록 (c)+대회 계획·추가 신호 후보, 트리거 확장 (c) `adjuster_v3`, source=주 트리거 종류 재적재) · 2026-10-11 설계서 동기화(ADJ-3~16, NEW-1~3 확정 반영) · 2026-10-11 설계서 동기화(ADJ-13 readiness 표 추가 결정, ADJ-15 표 순서 일치 확인, RC-4b/RC-6 정합으로 §3.4 수집·unplanned 정의 보정, TZ-1 '오늘' 헬퍼, NEW-10 익명화 행·NEW-12 일반화 반영, §7 축약·§9 모호점 정리) · 2026-10-11 2차 동기화(ADJ-17 race 주 트리거 위치 — §3.8·§3.10·§5·§7·§9 갱신, 유니크 인덱스 충돌 사실 확인 1줄) · 2026-10-11 4차 동기화(V1-1 v1 화면·경로 일몰 — §5 호환 항목의 v1 서술 제거, `adjuster_v1`·`pain_v1` 규칙 버전명은 유지) · 2026-10-11 5차 동기화(ADJ-18 '미판정' = 주 트리거 후보 동률만 — §3.8·§5·§9, V1-2 정정 — v1 일몰은 UI·라우트, 공유 `adjust_todays_plan` 호환 서술 복원·v1 로더 이관 대상 명시) · 2026-10-11 7차 동기화(PLN-23 기존 `planned_workouts` 삭제 시 `plan_adjustments` 참조 사실 정리·삭제 범위 열린 질문 — §3.14 신설·§9, V1-13 v1 보호 서술 제거 — §5 호환·§8, NEW-38 복귀 context 기점은 `adjustment-new-signals.md` §2.2·§2.7 참조)
> 결정 번호: 본문 D1~D18 = decisions-table ADJ-1~18, 신규 신호 저장·트리거는 NEW-1~3(`adjustment-new-signals.md`).

## 1. 근본 원인
- `plan_adjustments.source='crs'`는 "누가 만들었나(시스템 자동)"와 "무엇이 근거인가"를 한 라벨에 섞었다. 실제 생성 경로는 `plan_pain.proposal`(통증, `pain_v1`) 또는 `adjust_todays_plan`→`readiness_decision`(BB·수면·스트레스·TSB, `adjuster_v1`)이며 CRS는 한 번도 읽히지 않는다(`plan_adjustment_service.py:98`).
- 근거는 `reasons_json` 칩(`{key:"summary"|"readiness"|"pain", label}`)으로만 남아 값·출처·신선도가 없다. `reasons_json`은 이미 `plan_advisory`의 발급 원장(`{key:"advisory",code}`)으로도 쓰여 의미가 과적재돼 있다.
- CRS를 읽어야 할 두 곳(`replanner.py:142`, `matcher_context.py:84`)은 없는 `crs.evaluate` import로 항상 빈 값 → 시스템 전체에서 CRS가 행동 경로에 0회 반영.

## 2. 현황 — 신호 × 소비처 (코드 확인분, 2026-10-11)
소비처: **P**=`ensure_proposal`(조정 제안 저장) · **H**=`today_hero` verdict down/up · **R**=`replanner` 경고 · **M**=`matcher_context` 스냅샷 · **A**=`plan_advisory` A1~A6 · **E**=`coach_evidence` plan 근거

| 신호 | P | H | R | M | A | E | 비고 |
|---|---|---|---|---|---|---|---|
| TSB | ○(fatigue) | ○ down(<-15/-25)·up(>10) | | ○ | | ○ | `get_latest_tsb` 날짜 이전 최신값 폴백(신선도 미표시) |
| Body Battery | ○ | ○ down(<50/30)·up(>70) | | ○ | | ○ | `daily_wellness.body_battery_high` |
| 수면 점수 | ○ | ○ down | | | | ○ | |
| 스트레스 | ○ | ○ down(>75) | | | | ○ | 근거 칩(`_reason_parts`)에는 안 나옴 |
| HRV | ✕ | ✕ | | ○ | | | `get_todays_wellness`가 `hrv_value` 로드하나 `fatigue_level` 미사용 |
| ACWR | | | | ○ | ○ ACWR_LOW(`load_delta.acwr_after`) | | |
| CRS(level·score·gates) | ✕(이름만) | ✕ | ✕(import 실패) | ✕(import 실패) | | | 복원 후 R·M 동작 변화 |
| UTRS | | | | | | | `/today` 게이지 표시만(`today_readiness`) |
| 통증(조정 행 `key:pain`) | ○ 우선(D+1~2) | (P 경유 아님) | | | ○ 집계 제외·REPLAN 억제 | | `plan_pain._pain_rows` |
| 체크인(`user_inputs` fatigue·pain) | | | | | | | AI 컨텍스트(`chat_context_checkin`)만 |
| 폭염 예보 | | | | | | | `weekly_adapt_job`(`heat_forecast`)만, 외부 API |
| 대회 임박 | | state race_week/day | ○ taper(≤2주) | | ○ LONG 집계 | | move `TAPER_LOCK`(ADR-035) |
| 세션 결과 피드백 | | | ○ 볼륨·페이스 경고 | | | | `session_outcomes.crs_at_session` 포함(현재 항상 NULL) |

→ "조정 제안"이 실제로 보는 신호는 웰니스 3종+TSB(+통증)뿐이고, 저장 행에는 그 값·신선도가 남지 않는다.

## 3. 설계안
**3.1 개념 분리(D4).** `source` = **주 트리거 신호 종류**(`pain`/`illness`/`checkin`/`crs`/`acwr`/`readiness`/`race`, 사용자 작성은 `user`, 코치는 `coach`). 생성 주체(auto/user/coach)는 source 값 집합으로 유도(`user`·`coach` 이외 = 자동). 역할 분담: **source = "왜 이 제안이 나왔나"의 한 단어(필터·집계·UI 분기용)**, **signals_json = 판정에 쓰인/참고한 신호 전부(값·신선도·role)**. 불변식: 자동 행이면 `signals_json` 안 `role:"trigger"` 중 하나가 source 와 같은 종류(예외: 레거시 행 §3.9, 질병 에피소드 삭제로 익명화된 행 — `adjustment-new-signals.md` §2.6 NEW-10: 질병 항목 제거·`source='illness'`→`'readiness'`, 나머지 유지).

**3.2 저장(D5 확정: B `signals_json` 컬럼).** `signals_json TEXT NOT NULL DEFAULT '[]'`을 **v37 재생성에 합류**(재생성+CHECK 확장+컬럼 추가 1회, §3.9). 항목:
```json
{"signal":"crs","role":"trigger|support|counter|hold|context","value":2,"detail":{"level_label":"…","gates":["hrv"]},
 "as_of":"2026-10-11","freshness":"fresh|stale|partial|missing","provider":"runpulse:formula_v1"}
```
`role`: trigger=제안 방향을 만든 신호, support=같은 방향, counter=반대 방향, hold=BOOST 보류 사유(FRS-16 재사용), context=판정 미사용 참고값. `reasons_json`은 UI 칩·advisory 원장으로 유지(무수정).

**3.3 신호 목록(D1·D10 확정).** 판정 입력: BB·수면·스트레스·TSB·통증 기록 / 추가 기록: CRS(level·score·gates)·UTRS·ACWR·HRV(`hrv_last_night`/`hrv_weekly_avg`)·체크인(`user_inputs` fatigue·pain) / 외부·일정: 폭염(`weather_cache` 캐시만)·**대회 계획**(§3.4) / 가용 추가 신호 6종(§3.5, 표의 쓰임대로) / 신규 수집 4종(질병·여행·시간대·고도·B/C 우선순위 — 수집·UI는 `adjustment-new-signals.md`, 대회는 `race-calendar.md`).

**3.4 대회 계획 신호 `race_plan`(D1·D11·D12 확정).** 대회 사실의 원천은 **`race_calendar`**(v38, 우선순위 `A|B|C` 필수 — NEW-4/RC-2), 목표는 v39 `goals.race_id`로 참조(`race-calendar.md`). `planned_workouts.workout_type='race'` 행은 계획상 위치(조정 제외 대상)로만 쓴다. `training/constraints.b_race_week()`는 현재 호출자 0(정리는 RC 번들).
- 수집: 오늘(`reference_today`, TZ-1 추가 결정 — `patterns/timezone-display.md` §2.4) 기준 −14~+21일 `race_calendar` 행 중 `status IN ('planned','done')`이고 `adapt_choice != 'no_adapt'`인 것 전부(A = 활성 목표의 `race_id`). recovery 창은 대회 날짜가 지나 자동 done(RC-8)된 뒤라 `done`을 포함해야 하고, `no_adapt`·`cancelled`는 대회 신호를 전혀 만들지 않는다(RC-4b, `race-calendar.md` §2.4). 계획 중간에 있거나 새로 추가된 대회 포함. `detail.unplanned=true`는 `adapt_choice IN ('unasked','later')`인 대회에만(RC-4b 우선·RC-6 정합). v38 이전 DB에서는 `goals`+race 행으로 수집하고 priority=`unknown`.
- 정규화: `{"signal":"race_plan","value":<d_day>,"detail":{"race_id","race_date","distance_km","priority":"A|B|C","phase":"pre_taper|taper|race_day|recovery","unplanned"}}`. 가장 가까운 미래 1건을 주, 나머지는 `detail.others`.
- 보호 기간(D12, RC-5): 기본값 taper `≤10K 3일 / 하프 7일 / 풀 14일`, recovery `2/4/7일`, B/C는 절반 **올림**(RC-16) + **대회별 덮어쓰기**(race_calendar 필드, 덮어쓰면 절반 미적용).
- 역할: taper·recovery 창 안에서 **상향 금지 hold** + 하향 support. race_day·race 행은 조정 대상 제외. 계획에 반영된 대회는 하향 trigger를 만들지 않는다(이중 감량 방지). **계획에 반영하지 않은 대회(unplanned = 질문 대기·나중에)의 recovery 창 Q-day만 하향 trigger**(source=`race`, RC-6). '조정 안 함' 대회는 hold·support·trigger 어느 것도 만들지 않는다(RC-4b). 대회 등록·수정 시 리플랜 질문·일괄 적용은 RC-7 흐름(본 번들 범위 밖).

**3.5 추가 신호(가용분, D10 확정 — 표의 쓰임대로 채택).**
| 신호 | 원천(코드 확인) | 쓰임 |
|---|---|---|
| 직전 고강도 간격·연속 Q-day | `plan_move.HARD/Q_TYPES` + `activity_summaries`·`planned_workouts` | 48h 내 Q 2회 → support |
| 최근 7일 수면 부채 | `daily_wellness.sleep_duration_sec`(28일 평균 대비 누적 부족) | support, 단독 trigger 아님 |
| 안정시 심박 상승 | `daily_wellness.resting_hr`(7일 기준선 +5bpm 등) | support |
| 통증 추세(재발) | `plan_adjustments` pain 행 + `user_inputs.pain` 14일 횟수 | context |
| 놓침/미이행 추세 | `week_compliance.outcome_label`='missed' | context |
| 폭염 | `weather_cache`/`weekly_adapt.heat_forecast` | support·context, 외부 호출 금지 |
신규 수집 신호(NEW-3): **질병 = 단독 OR trigger**(+BOOST hold), 여행·시간대·고도 = support/context.

**3.6 수집 모듈 `src/services/adjustment_signals.py`(신규, 서비스 계층).** `collect(conn, day, *, readiness=None, crs=None, hold=None) -> list[dict]` — 수집기별 try/except, 실패 신호만 `freshness:"missing"`. 외부 호출 금지(캐시만). 대회 수집기 `adjustment_signals_race.py`, 질병·여행·고도 수집기 `adjustment_signals_context.py`(new-signals 번들)로 분리(300줄). `classify(signals, proposal)` 순수 함수로 role 부여. `primary_trigger(signals) -> str`(§3.8) 순수 함수.

**3.7 트리거 확장(D2·D9·D13, `adjuster_v3`).** 판정 규칙(임계값은 **제안 값** — 빈도 관찰(§3.13) 후 조정):
- **단독 OR(하나만으로 하향)**: 통증 기록(`plan_pain`, D+1~2) · 체크인 통증(`pain` 비어있지 않음, 통증 경로와 동일 처리) · 질병(확인된 `illness` 에피소드, NEW-3).
- **2개 합의 AND**: CRS `level ≤ 1` · ACWR `≥ 1.5` · 체크인 피로 당일/전일 `fatigue ≥ 4`(1~5 척도 가정, 구현 시 확인) 중 **2개 이상**이 같은 날 성립하면 하향. 1개만 성립하면 role=support로 기록만. 강도: CRS level 0 포함 시 rest/skip 후보, ACWR `≥ 1.8` 포함 시 Q-day → easy replace, 그 외 reduce. ACWR 1.3~1.5는 support.
- 기존 `readiness_decision`(BB·수면·스트레스·TSB) 하향은 **AND 합의의 1표로 세지 않고 현행 단독 경로 그대로 유지**(source=`readiness`, ADJ-13 추가 결정). 이 규칙은 추후 데이터 분석·ML/백테스트로 재검토해 결정한다(`LATER.md` 'ADJ-READINESS-VOTE').
- stale 허용(D9): stale·partial 신호도 trigger 가능, 대신 `freshness`·`as_of`를 signals에 기록하고 상세에 표시.
- 제안 강도는 `readiness_decision`의 `adjusted_type` 체계 재사용(새 op 없음). race 행·rest 행 제외.
- 버전: v3 배포 후 자동 행은 모두 `rule_version='adjuster_v3'`(버전 = 배포된 규칙 세트), `pain_v1` 불변. Calculator 아님 → `algo_changelog` 대신 ADR-035 개정에 기록.

**3.8 주 트리거 선정(D15·D17·D18 확정 + NEW-3).** trigger가 복수면 고정 순서 **`pain > illness > checkin > race > crs > acwr > readiness`**로 source를 고른다(안전 우선·결정적). `race`(RC-6 미반영 대회 recovery 창 Q-day 하향)는 **checkin 바로 뒤, crs 앞**(ADJ-17 a). 동률·미판정은 `readiness`(decisions-table ADJ-15·ADJ-3 문구와 일치). **'미판정' = 주 트리거 후보가 2개 이상 동률인 경우만**(ADJ-18 b) — OR trigger 없이 AND 합의만 성립한 경우는 '미판정'이 아니다. 이때 AND 구성원(체크인 피로=`checkin`(ADJ-15 'checkin(통증·피로)'), `crs`, `acwr`)이 trigger 후보이고 위 고정 순서로 source를 고른다(이 문서의 적용 해석). 고정 순서 아래에서 '동률'이 실제로 생기는 경로는 §9 확인 항목. 표시 순서(D3)도 동일. 이 순서는 확정값이지만 **추후 데이터 백테스트·ML로 재검토할 대상이며 `LATER.md`에 기록돼 있다**(ADJ-17).

| 순위 | source | 트리거 종류(§3.7) |
|---|---|---|
| 1 | `pain` | OR 단독(통증 기록) |
| 2 | `illness` | OR 단독(confirmed 질병, NEW-3) |
| 3 | `checkin` | OR 단독(체크인 통증) |
| 4 | `race` | 미반영 대회 recovery 창 Q-day(RC-6, §3.4) |
| 5 | `crs` | AND 합의 구성원 |
| 6 | `acwr` | AND 합의 구성원 |
| 7 | `readiness` | 현행 단독 경로(투표 안 함)·동률(=미판정, ADJ-18) 기본값 | readiness는 AND 합의에 투표하지 않는다(§3.7, `LATER.md` 'ADJ-READINESS-VOTE').

**3.9 스키마·마이그레이션(v37 → v38 → v39).**
- **v37 `plan_adjustments` 재생성(본 번들)**: ① `running.db.bak-v36-<ts>` 파일 백업 + `PRAGMA integrity_check` ② 한 트랜잭션에서 v33 패턴 재사용 — `plan_adjustments_new`(CHECK `source IN ('pain','illness','checkin','crs','acwr','readiness','race','travel','altitude','user','coach')`(NEW-2), `signals_json` 추가) → `INSERT … SELECT` + 재분류 → 인덱스 재생성(유니크 동일) → 행 수·id 일치 검증 후 RENAME ③ 멱등: CHECK에 `'illness'`가 있으면 skip.
- 재분류(기존 `source='crs'` 행): `rule_version='pain_v1'` 또는 reasons 키 `pain` → `pain`; reasons 키 `readiness` → `readiness`; **판별 불가(summary만·빈 배열) → `readiness`로 UPDATE**(D16). 마이그레이션 후 `source='crs'` 레거시 행 0건.
- dry-run: `scripts/plan_adjustments_resource.py --dry-run`(쓰기 없음) — `crs→readiness n, crs→pain n, 판별불가→readiness n` 분포·샘플 id. 마이그레이션 함수도 `dry_run=True`로 같은 로직 공유. 운영 DB **사본**에서 먼저 실행.
- 기존 행 signals(D6): `proposed` 행은 다음 조회 때 `collect` 결과로 **전체 재기록**. `accepted`/`reverted` 행은 현재 값을 덧씌우지 않고 `[]` 유지(불변식 예외). **제안**: 이 과거 행에 reasons 키 기반 trigger 1건(`detail.backfilled=true`, 값·신선도 없음)을 v37 재분류와 같은 판정으로 병행 백필 — 비용 거의 0, 필요 시 채택.
- **v38 `context_episodes`·`race_calendar` 생성(가산, NEW-1)**: 스키마는 `adjustment-new-signals.md`·`race-calendar.md`. **v39 `goals.race_id` + 백필**(`race-calendar.md`, `race_backfill_dry_run.py`). 각 단계 사본 dry-run·멱등·`integrity_check`.
- 롤백: 실패 시 트랜잭션 롤백(원 테이블 유지). v37은 새 source 값이 v36 CHECK 위반이므로 **역마이그레이션 = 백업 파일 복원 + `SCHEMA_VERSION` 36 코드만**. v38은 v39 전이면 DROP 가능, v39 이후는 전진 전용(race-calendar.md). 운영상 롤백은 우선 §3.13 플래그(v3→v2)로 하고 스키마는 되돌리지 않는다.
- 소비처 수정(`source='crs'` 판정, 2026-10-11 grep): `plan_adjustment_service.py:84`(오늘 자동 제안 조회), `:229`(워크아웃별 자동 조정 after), `:278`(`source=? OR source='crs'` 중복 방지), `ensure_proposal` INSERT의 source 인자, `frontend/src/lib/rowActionView.ts:185`(자동 제안 판정), `PlanAdjustment.source` 타입(`index.ts`). 공통 헬퍼 `AUTO_SOURCES`(백엔드)·`isAutoSource()`(프론트)로 치환 — 구현 시 `grep -rn "'crs'" src frontend/src` 재확인.
- ADR-035 개정: source 의미(actor→주 트리거)·값 집합, `signals_json`, `adjuster_v3` 규칙(OR/AND), 주 트리거 순서, 레거시 재분류, 자동 롤백 플래그. 오버레이(`after_json`)·유니크·decision 상태기계 불변.

**3.10 생성 흐름·표시(D3·D7).** 생성: `plan_pain.proposal` → 질병 → 체크인 통증 → 대회 recovery(unplanned, §3.4) → v3 AND 판정(CRS·ACWR·체크인 피로) → readiness → 래퍼 hold(상향만 차단). 하향·상향 동시 → 하향. 대회 taper/recovery 창 → 상향 hold. 표시: 신호 순서는 §3.8과 동일. **카드 = 주 트리거 칩 1개**, **상세 = 전체 신호**(counter는 상세에서만, 통증 제안에서도 다른 신호는 접어서 유지, stale 신호는 freshness 표기), **Coach 근거 = trigger 신호**(문구 FRS-4 체계).

**3.11 rev·갱신(D8).** 제안 상태에서 **trigger 집합이 바뀔 때만 rev+1**, 값만 바뀌면 rev 유지 UPDATE, accepted 이후 동결. 예외: 질병 에피소드 단건 삭제 시 익명화(NEW-10 — `signals_json`의 해당 질병 항목 제거, `source='illness'`→`'readiness'`, `after_json`·decision·rev 등 나머지 유지)는 상태와 무관하게 적용(`adjustment-new-signals.md` §2.6). 주 트리거가 바뀌어 source가 달라져도 같은 행 갱신(현 유니크 키가 source를 포함하므로 §9 확인 필요).

**3.12 읽기·소비처.** `_to_dict`에 `signals` 추가, 프론트 `PlanAdjustment.signals?`, `AdjustmentCard` 표시(§3.10). `coach_evidence`는 source + trigger label. 단 AI 코치로 나가는 경로에서는 질병 별도 동의(NEW-12)가 없으면 `illness` 신호·`source='illness'`를 '컨디션 신호'로 일반화해 보낸다(규칙·위치는 `adjustment-new-signals.md` §2.6). 앱 안 "왜?" 표시는 로컬이라 그대로. R·M은 `crs.evaluate` 복원으로 CRS 채워짐.

**3.13 빈도 관찰·자동 롤백(D14).** ① 배포 전 백테스트 — DB 사본 최근 90일을 v2·v3로 dry 판정, 일별 제안 수·주 트리거 분포 비교(`scripts/adjuster_backtest.py`, 쓰기 없음). ② 배포 후 주간 집계 — `GROUP BY rule_version, source, decision` 로그 1줄(`adjuster_v3 weekly: proposed=…, accepted=…, by_source={…}`). ③ **자동 롤백 플래그** 설정 `adjuster_version`(v3|v2): 기준(제안 값) **자동 제안 주 3회 초과 2주 연속** 또는 **수락률 급락(v2 백테스트 기준 대비 절반 이하, 제안 값)** 시 `v2`로 전환 → v3 트리거(CRS·ACWR·체크인 피로 AND, 질병·체크인 통증 OR) 정지, 기존 행·스키마 유지. 오작동 방지(제안): 판정 최소 표본 주 2회 이상, 대회 recovery·질병 에피소드 주간 제외. 사용자 설명(제안): 전환 시 Coach/설정에 중립 한 줄("최근 제안이 많아 이전 기준으로 돌아갔어요"), 재활성은 수동.

## 4. 변경 파일 표
| 파일 | 구분 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v37.py` | 신규 | 재생성(CHECK 11값)+`signals_json`+재분류(판별불가→readiness), 백업 확인, dry_run, 멱등 | ~95 |
| `src/db_schema_v38.py` / `v39.py` | 신규(타 번들) | context_episodes·race_calendar / goals.race_id | new-signals·race-calendar 참조 |
| `src/db_setup.py` | 수정 | `SCHEMA_VERSION` 37→39(번들 순차), ensure 호출 | +3(v37분) |
| `scripts/plan_adjustments_resource.py` | 신규 | 재분류 dry-run 리포트 | ~50 |
| `src/services/adjustment_signals.py` / `_race.py` | 신규 | collect·classify·primary_trigger / race_calendar 기반 대회 수집 | ~180 / ~100 |
| `src/services/adjustment_triggers_v3.py` | 신규 | OR(통증·체크인 통증·질병)/AND(CRS·ACWR·피로) 판정(순수) | ~110 |
| `src/services/adjuster_frequency.py` | 신규 | 주간 집계 로그·롤백 기준 판정·`adjuster_version` 전환 | ~80 |
| `src/services/plan_adjustment_proposal.py` | 신규(분리) | `ensure_proposal` 이동(원 파일 301줄) + source=primary, proposed 재기록·rev 규칙 | ~120 |
| `src/services/plan_adjustment_service.py` | 수정 | `'crs'` 판정 3곳→`AUTO_SOURCES`, signals 노출 | −70/+15 |
| `src/metrics/crs.py` | 수정(선행) | `evaluate()` 복원 | +30 |
| `src/services/coach_evidence.py` | 수정 | source·trigger label | +15 |
| `frontend/src/lib/rowActionView.ts`, `lib/types/index.ts`, `AdjustmentCard.svelte` | 수정 | `isAutoSource`, 타입, 칩 1개/상세 전체 | +5/+15/+30 |
| `scripts/adjuster_backtest.py` | 신규 | v2 vs v3 빈도 비교(읽기 전용) | ~80 |
| tests: `test_adjustment_signals*.py`, `test_adjustment_triggers_v3.py`, `test_adjuster_frequency.py`, `test_db_schema_v37.py`, `test_plan_adjustment_service.py` | 신규/수정 | §5 | ~35개 |
| `v0.3/data/decisions.md` | 수정(구현 시) | ADR-035 개정 | +25 |

## 5. 단계·검증·롤아웃
0. 선행: `crs.evaluate` 복원 → FRS `boost_hold`·래퍼(FRS-12~21).
1. `adjustment_signals`(+race·context) 추가(호출자 없음) + 단위 테스트(수집기별 정상·결측·stale, race 창·대회별 덮어쓰기, unplanned 포착 — `unasked`·`later`만, `no_adapt` 무신호, done 대회 recovery 창 수집, '오늘'=`reference_today` 주입, 외부 호출 없음). 선행: `reference_day.py`(timezone-display.md 단계 5-1).
2. v37: 사본 dry-run 분포 확인 → 백업·재생성·재분류 + `ensure_proposal` 분리(동작 불변 커밋 별도). 회귀: 같은 픽스처에서 `after`·`reasons`·rev 동일, source만 `readiness`/`pain`, `crs` 0건.
3. 소비처 6곳 `AUTO_SOURCES` 치환 → Hero·row action·중복 방지 동일 동작.
4. v38 → v39(타 번들 일정, 각 사본 dry-run·백업). race_plan priority가 race_calendar로 채워지는지 회귀.
5. 백테스트 v2/v3 비교 후 사용자 확인 → `adjuster_version=v3` 활성화 + 주간 로그·자동 롤백 감시.
6. API·프론트·coach_evidence. `pytest tests/`, `npm run check`, 픽스처 DB 브라우저 확인(운영 DB 미사용).
- 검증 체크: v37 전후 행 수·id·decision 일치, `integrity_check` ok, 재실행 멱등, CHECK 위반 INSERT 거부, `plan_overlay` 불변, OR 단독 하향(통증·체크인 통증·질병)·AND 1개=support/2개=하향 테스트, readiness 하향 + AND 1개 → AND 미성립(readiness 미투표)·readiness 단독 경로는 기존과 동일, stale trigger 시 freshness 기록, 주 트리거 순서 테스트(§3.8 표 7단계, race가 checkin 뒤·crs 앞 — 예: checkin+race → `checkin`, race+crs+acwr → `race`), '미판정'(ADJ-18): AND 합의만 성립(crs+acwr, 다른 trigger 없음) → `crs`, 체크인 피로+acwr → `checkin`(둘 다 readiness 아님), 동률 후보 직접 주입 → `readiness`(§9), trigger 집합 변화만 rev+1·accepted 동결, proposed 재기록·과거 행 불변, 롤백 기준 초과 시 v2 전환 테스트, race 행 조정 제외, taper 창 BOOST hold, 신규 파일 300줄 이하, `check_docs.py` 통과.
- 호환: v1 일몰은 UI·라우트 일몰이며 공유 파일·함수는 유지한다(V1-1 정정·V1-2). 공유 함수 `src/training/adjuster.adjust_todays_plan`(v2 `plan_adjustment_service.py:98`·`plan_service.py:145`·`ai/chat_readiness.py:22`·`ai/coach_rule_handlers.py:49`도 호출)은 유지·시그니처 불변. 직접 호출자 CLI `plan.py`와 v1 로더 `src/web/views_training_loaders.load_adjustment`(`:45`)는 `adjust_todays_plan`만 부르고 `src/web`에서 `plan_adjustments` 조회는 없음(grep 2026-10-11) → v37·v3 영향 없음. `views_training_loaders.py`처럼 v2도 필요한 로직을 가진 v1 파일은 재설계 대상이며 view 밖 모듈로 이관 설계(V1-2) — 가드 테스트에서 v1 파일을 제외하는 방식은 쓰지 않는다. v1 화면·라우트 자체는 고려하지 않는다.

## 6. 대안(기각)
- **A. `reasons_json`에 신호 내장** — 칩·원장·근거 혼재, rev 필터 필요. D5에서 B 채택.
- **source `'crs'` 유지 + API 별칭 / `'auto'` 치환** — D4에서 "주 트리거 종류" 채택.
- **v3 전부 OR / 전부 AND** — D13 혼합 채택(안전 신호는 단독, 측정·피로는 합의).

## 7. 결정 필요
- 결정 완료(표 참조: `decisions-table.md` ADJ-1~18·NEW-1~3·V1-1·V1-2, 본문 D번호 = ADJ번호). ADJ-17 주 트리거 순서는 확정, 재검토는 백테스트·ML 후(`LATER.md`). ADJ-13 readiness 투표 여부는 추가 결정으로 현행 유지, 재결정은 `LATER.md` 'ADJ-READINESS-VOTE'. 제안 상태로 남은 것: §3.9 과거 행 trigger 1건 백필(ADJ-6 단서).

## 8. 범위 밖 메모
- `session_outcomes.crs_at_session`·replanner CRS 경고 문구, 폭염 보정의 일일 조정 연결(본 설계는 support/context 기록까지), R8 거리 비율 규칙, 신규 수집 신호 입력 UI(new-signals·product), race_calendar 관리 화면·리플랜 질문(race-calendar), `b_race_week` 죽은 경로 정리. v1 로더 `views_training_loaders.py`의 view 밖 이관(V1-2) — 본 번들은 공유 함수 `adjust_todays_plan`을 바꾸지 않으므로 이관 일정과 독립.

## 9. 동기화 중 발견한 모호점
- 해소(ADJ-17): race는 checkin 바로 뒤(§3.8 표).
- 해소(ADJ-18): '미판정' = 주 트리거 후보 동률만, AND만 성립은 미판정 아님(§3.8).
- **확인 항목(ADJ-18):** 고정 순서는 source 종류마다 순위가 달라 종류 간 동률이 없다. 같은 종류 후보가 여럿(예: 통증 기록 2건)인 경우는 source가 같아 결과가 같다. 그러면 '동률 → readiness' 규칙이 적용되는 실제 입력이 무엇인지(사실상 도달 불가 방어 분기인지) 결정 문구로 정해지지 않았다 — 구현은 방어 분기로 두고 테스트는 `primary_trigger` 에 동률을 직접 주입해 검증하는 것을 제안.
- NEW-10 익명화는 `accepted`/`reverted` 행도 고친다 — "수락 후 동결"(ADJ-8)·"과거 행 덧씌움 금지"(ADJ-6)의 예외로 적었으나 표에 명시는 없다.
- ADJ-14 수락률 "급락" 수치와 `adjuster_version` 저장 위치(설정 저장소)는 결정에 없어 제안 값으로 적었다.
- `plan_adjustments` 유니크 인덱스는 `(workout_id, date, source) WHERE decision IN ('proposed','accepted')`(`db_schema_v31.py:30`)로 source를 포함한다. 자동 source가 여러 값으로 나뉘면 같은 워크아웃·날짜에 자동 제안 행이 source별로 공존할 수 있고, §3.11 "같은 행 갱신"은 인덱스가 막지 않는다. v37 재생성 시 유니크 키 조정(자동 source 묶음) 여부 확인이 필요하다. NEW-10 익명화(`illness`→`readiness`)도 같은 워크아웃·날짜의 `readiness` 행과 이 인덱스에서 충돌할 수 있다. 코드 확인(2026-10-11 grep): 인덱스는 partial이라 reverted 행은 충돌 대상이 아니고, 현재 `ensure_proposal`은 `_live`(날짜·`source='crs'`)로 날짜당 live 자동 행을 1개만 두며 새 제안 전 기존 proposed를 reverted 처리한다(`plan_adjustment_service.py:83-121`) — 지금 코드에서는 충돌이 생기지 않고, v37 이후 같은 workout·date에 live `illness`·live `readiness` 행이 공존할 수 있을 때만 UPDATE가 유니크 위반이 된다(`adjustment-new-signals.md` §4 S0 확인 항목, 해결안 미결정).
