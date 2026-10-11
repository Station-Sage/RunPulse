# 조정 제안 근거 신호 확장 (adjustment-signals)

> 작성 2026-10-11 · 상태: 설계 초안(ADJ-1·2·4 결정 반영, 나머지 미확정) · 관련: [ADJUSTMENT-SOURCE-CRS-LABEL], [CRS-EVALUATE-MISSING], FRS-12~19(`patterns/data-freshness.md` §2.6·§2.7), ADR-035
> 전제(결정됨): `crs.evaluate()` 복원(저장 CRS·신선도 읽기 전용), CRS stale/게이트 불명 시 BOOST만 보류(`adjuster_v2`), `plan_service.todays_adjustment_with_hold` 래퍼, Hero `as_planned`+`hold_reason`.
> 변경 이력: 2026-10-11 초안 · 2026-10-11 ADJ-1·2·4 결정 반영(신호 목록 (c)+대회 계획·추가 신호 후보, 트리거 확장 (c) `adjuster_v3`, source=주 트리거 종류 재적재)
> 결정 번호: 본문 D1~D9 = decisions-table ADJ-1~9, D10~ = 신규(미결정).

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
**3.1 개념 분리(ADJ-4 결정 반영).** `source` = **주 트리거 신호 종류**(`crs`/`readiness`/`pain`/…, 사용자 작성은 `user`, 코치는 `coach`). 생성 주체(auto/user/coach)는 source 값 집합으로 유도(`user`·`coach` 이외 = 자동). 전체 근거는 `signals_json`(§3.2). 역할 분담: **source = "왜 이 제안이 나왔나"의 한 단어(필터·집계·UI 분기용)**, **signals_json = 판정에 쓰인/참고한 신호 전부(값·신선도·role)**. 불변식: 자동 행이면 `signals_json` 안 `role:"trigger"` 중 하나가 source 와 같은 종류(레거시 백필 행은 예외, §3.9).

**3.2 저장(추천: 컬럼 추가, D5).** `signals_json TEXT NOT NULL DEFAULT '[]'`. ADJ-4로 테이블 재생성이 어차피 필요하므로 **v37 한 번에 재생성 + CHECK 확장 + 컬럼 추가**(§3.9). 항목:
```json
{"signal":"crs","role":"trigger|support|counter|hold|context","value":2,"detail":{"level_label":"…","gates":["hrv"]},
 "as_of":"2026-10-11","freshness":"fresh|stale|partial|missing","provider":"runpulse:formula_v1"}
```
`role`: trigger=제안 방향을 만든 신호, support=같은 방향, counter=반대 방향, hold=BOOST 보류 사유(FRS-16 재사용), context=판정 미사용 참고값. `reasons_json`은 UI 칩·advisory 원장으로 유지(무수정).

**3.3 신호 목록(ADJ-1 (c) 확정분).** 판정 입력: BB·수면·스트레스·TSB·통증 기록 / 추가 기록: CRS(level·score·gates)·UTRS·ACWR·HRV(`hrv_last_night`/`hrv_weekly_avg`)·체크인(`user_inputs` fatigue·pain) / 외부·일정: 폭염(`weather_cache` 캐시만)·**대회 계획**(§3.4). 추가 후보는 §3.5(D10).

**3.4 대회 계획 신호 `race_plan`(ADJ-1 사용자 요구).** 현황(grep 2026-10-11): 대회 정보 원천은 ① `goals.race_date·distance_km`(활성 목표 1개 유니크, v32) ② `planned_workouts.workout_type='race'` 행(계획 중간 레이스, `plan_move`·`plan_reduce`·`plan_pain`이 이미 race 를 이동/축소/통증 제안 제외) ③ `race_result_service.candidates`(과거 실적, 계획 아님). B/C 레이스 전용 저장소는 **없다** — `training/constraints.b_race_week()`는 호출자 0(죽은 경로).
- 수집: `goals` 활성 1건(A) + 오늘 기준 −14~+21일 `planned_workouts` race 행(A일 제외 = B/C 후보). 계획 도중 추가된 대회는 ②로 들어오면 자동 포착(`created_at` 비교로 `detail.added_mid_plan`). 우선순위(B/C) 표기 원천이 없으므로 D11.
- 정규화: `{"signal":"race_plan","value":<d_day>,"detail":{"race_date","distance_km","priority":"A|B|C|unknown","phase":"pre_taper|taper|race_day|recovery","source":"goal|planned"}}`. 하나의 날짜에 여러 대회면 가장 가까운 미래 1건을 주, 나머지는 `detail.others`.
- 단계 판정(제안 값, D12): taper 창 = 거리별 `≤10K 3일 / 하프 7일 / 풀 14일`(B/C는 절반), recovery 창 = 대회 후 `≤10K 2일 / 하프 4일 / 풀 7일`.
- 역할: taper·recovery 창 안에서 **상향 금지 hold**(BOOST 보류, role:hold) + 하향 support. race_day·race 행 자체는 조정 대상 제외(현행 `plan_pain` 규칙과 동일). race_plan 단독으로는 하향 trigger를 만들지 않는다(계획 자체가 이미 테이퍼를 반영 — 이중 감량 방지). 단 계획에 없는 추가 대회(added_mid_plan)의 recovery 창에 Q-day가 있으면 하향 trigger 후보(D12).

**3.5 추가 신호 후보(사용자 질문 "더 추가할 것은?", 포함 여부 D10).**
| 후보 | 가용성 | 원천(코드 확인) | 쓰임 제안 |
|---|---|---|---|
| 직전 고강도 간격·연속 Q-day | 가용 | `plan_move.HARD/Q_TYPES` + `activity_summaries`·`planned_workouts` | 48h 내 Q 2회 → support/하향 후보 |
| 최근 7일 수면 부채 | 가용 | `daily_wellness.sleep_duration_sec`(28일 평균 대비 누적 부족) | support, 단독 trigger 아님 |
| 안정시 심박 상승 | 가용 | `daily_wellness.resting_hr`(7일 기준선 +5bpm 등) | support |
| 통증 추세(재발) | 가용 | `plan_adjustments` pain 행 + `user_inputs.pain` 14일 횟수 | pain trigger 강화·context |
| 놓침/미이행 추세 | 가용 | `week_compliance.outcome_label`='missed' | context(하향 아님, 복귀 첫날 감량 근거 후보) |
| 테이퍼 단계 | 가용 | §3.4 race_plan.phase + `periodization` | hold/support |
| 폭염 | 가용(캐시) | `weather_cache`/`weekly_adapt.heat_forecast` | support·context, 외부 호출 금지 |
| 질병·메모 | 부분 | `user_inputs.note` 자유 텍스트 — 구조화 키 없음 | **신규 수집 필요**(체크인 `illness` 항목) |
| 여행·시간대 변화 | 없음 | 타임존 설계(PRED-1x) 미구현 | **신규 수집 필요** |
| 고도 | 없음 | 활동 고도 상승만 존재, 체류 고도 없음 | **신규 수집 필요** |
| B/C 레이스 우선순위 | 없음 | 저장소 없음(§3.4) | **신규 수집 필요**(D11) |

**3.6 수집 모듈 `src/services/adjustment_signals.py`(신규, 서비스 계층).** `collect(conn, day, *, readiness=None, crs=None, hold=None) -> list[dict]` — 수집기별 try/except, 실패 신호만 `freshness:"missing"`. 외부 호출 금지(캐시만). 대회 수집기는 `adjustment_signals_race.py`로 분리(300줄). `classify(signals, proposal)` 순수 함수로 role 부여. `primary_trigger(signals) -> str`(§3.8) 순수 함수.

**3.7 트리거 확장(ADJ-2 (c), `adjuster_v3`).** 하향 판정 규칙(임계값은 **제안 값**, 확정은 D13):
- CRS: `level ≤ 1`(fresh 또는 partial) → 하향. level 0 = rest/skip 후보, 1 = reduce.
- ACWR 과부하: `acwr ≥ 1.5` → reduce, `≥ 1.8` → Q-day를 easy 로 replace. 1.3~1.5 는 support만.
- 체크인 피로: 당일/전일 `fatigue ≥ 4`(1~5 척도 가정, 척도 확인 필요) → reduce. 체크인 통증: `pain` 비어있지 않음 → 통증 경로와 동일 처리(D+1~2).
- 결합: 단일 신호 1개로 하향(OR) vs 2개 이상 합의 필요(AND)는 D13. stale 신호 허용은 D9.
- 제안 강도는 기존 `readiness_decision` 의 `adjusted_type` 체계 재사용(새 op 없음). race 행·rest 행 제외.
- 버전: 새 하향 경로가 만든 행 = `rule_version='adjuster_v3'`, 기존 경로 동일 결과는 v3 배포 후 모두 `adjuster_v3`로 기록(버전 = 배포된 규칙 세트). `pain_v1` 불변. Calculator 아님 → `algo_changelog` 대신 ADR-035 개정에 기록.
- **제안 빈도 관찰**: ① 배포 전 백테스트 — 픽스처/운영 DB 사본에서 최근 90일을 v2·v3 로 각각 dry 판정해 일별 제안 수·주 트리거 분포 비교(`scripts/adjuster_backtest.py`, 쓰기 없음). ② 배포 후 — `plan_adjustments` 에서 `GROUP BY rule_version, source, decision` 주간 집계(제안/수락/되돌림 비율)를 로그 1줄(`adjuster_v3 weekly: proposed=…, accepted=…, by_source={…}`)로 남기고, 수락률이 v2 대비 급락하거나 주 3회 초과 제안이 2주 연속이면 임계값 재검토(기준은 D14).

**3.8 주 트리거 선정(ADJ-4, 우선순위는 D15).** trigger가 복수면 `primary_trigger`가 하나를 source로 고른다. 후보: (a) 안전 우선 고정 순서 `pain > checkin(pain/fatigue) > crs > acwr > readiness` — 결정적·설명 쉬움 / (b) 제안 강도 기여 최대 신호(rest를 만든 신호) — 정확하나 동률 규칙 필요 / (c) 사용자 입력 우선(`checkin`·`pain` > 측정치) — 주관 신호 존중. 동률·미판정 시 `readiness`. source 값 집합 후보: `pain, checkin, crs, acwr, readiness, race`(race 는 recovery-창 trigger 채택 시만) + `user, coach`.

**3.9 source 재적재·마이그레이션(v37, ADJ-4).**
- 절차: ① 시작 전 `running.db` 파일 복사 백업(`running.db.bak-v36-<ts>`) + `PRAGMA integrity_check` ② 트랜잭션 안에서 v33 패턴 재사용 — `plan_adjustments_new` 생성(CHECK `source IN ('pain','checkin','crs','acwr','readiness','race','user','coach')`, `signals_json` 추가) → `INSERT … SELECT` + 재분류 → 인덱스 재생성(유니크 인덱스 동일) → 행 수·id 일치 검증 후 RENAME ③ 멱등: CHECK에 `'readiness'`가 이미 있으면 skip.
- dry-run: `scripts/plan_adjustments_resource.py --dry-run`(신규, 쓰기 없음) — 재분류 결과 분포(`crs→readiness n, crs→pain n, 판별불가 n`)와 샘플 id 출력. 마이그레이션 함수도 `dry_run=True` 인자로 같은 로직 공유.
- 재분류 매핑(기존 `source='crs'` 행): `rule_version='pain_v1'` 또는 reasons 키 `pain` 존재 → `pain`; reasons 키 `readiness` 존재 → `readiness`; 둘 다 없음(summary만·빈 배열) → **판별 불가**: 후보 (a) `readiness`로 간주(기존 생성 경로상 pain 아니면 전부 adjuster — 사실상 정확) / (b) `crs` 그대로 두고 "레거시" 의미로 유지(D16). 기존 행은 CRS를 읽은 적이 없으므로 `crs`로 남는 행은 원칙적으로 0이어야 한다.
- 백필 행의 `signals_json`은 `[]`(ADJ-6 선택에 따름) — 불변식 예외로 `detail` 없이 source만 신뢰.
- 롤백: 마이그레이션 실패 시 트랜잭션 롤백(원 테이블 유지). 배포 후 문제 시 백업 파일 복원 + `SCHEMA_VERSION` 36 코드로 되돌림(v37 행의 새 source 값은 v36 CHECK 위반이므로 **역마이그레이션 = 백업 복원만** 지원, 명시).
- 소비처 수정(`source='crs'` 판정, 2026-10-11 grep): `plan_adjustment_service.py:84`(오늘 자동 제안 조회), `:229`(워크아웃별 자동 조정 after), `:278`(`source=? OR source='crs'` 중복 방지), `ensure_proposal` INSERT의 source 인자, `frontend/src/lib/rowActionView.ts:185`(자동 제안 판정), `PlanAdjustment.source` 타입(`index.ts`). 공통 헬퍼 `AUTO_SOURCES`(백엔드 상수)·`isAutoSource()`(프론트)로 치환 — 구현 시 `grep -rn "'crs'" src frontend/src` 재확인.
- ADR-035 개정 범위: source 의미(actor→주 트리거), 값 집합, `signals_json` 컬럼, `adjuster_v3` 트리거 규칙, 주 트리거 선정 규칙, 레거시 재분류 기록. 오버레이(`after_json`)·유니크·decision 상태기계는 불변.

**3.10 생성 흐름·우선순위(D3).** `plan_pain.proposal` → 체크인 통증 → v3 하향(CRS·ACWR·체크인 피로·readiness) → 래퍼 hold(상향만 차단) 순. 하향·상향 동시 → 하향. 대회 taper/recovery 창 → 상향 hold. D3 미결정 시 counter 는 저장만, 표시 보류.

**3.11 rev·갱신(D8).** 제안 상태에서 **trigger 집합 또는 source가 바뀔 때만 rev+1**, 값만 바뀌면 rev 유지 UPDATE, accepted 이후 동결. source 변경(예: readiness→crs) 시 행을 새로 만들지 않고 같은 행 갱신(유니크 키가 source 포함 여부 구현 시 확인).

**3.12 읽기·소비처.** `_to_dict`에 `signals` 추가, 프론트 `PlanAdjustment.signals?`, `AdjustmentCard` 표시(D7). `coach_evidence`는 source + trigger label. R·M은 `crs.evaluate` 복원으로 CRS 채워짐.

## 4. 변경 파일 표
| 파일 | 구분 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v37.py` | 신규 | 재생성(CHECK 확장)+`signals_json`+재분류, dry_run, 멱등 | ~90 |
| `src/db_setup.py` | 수정 | `SCHEMA_VERSION=37`, ensure 호출 | +3 |
| `scripts/plan_adjustments_resource.py` | 신규 | 재분류 dry-run 리포트 | ~50 |
| `src/services/adjustment_signals.py` / `_race.py` | 신규 | collect·classify·primary_trigger / 대회 계획 수집 | ~180 / ~90 |
| `src/services/adjustment_triggers_v3.py` | 신규 | CRS·ACWR·체크인 하향 판정(순수) | ~100 |
| `src/services/plan_adjustment_proposal.py` | 신규(분리) | `ensure_proposal` 이동(원 파일 301줄) + source=primary | ~110 |
| `src/services/plan_adjustment_service.py` | 수정 | `'crs'` 판정 3곳→`AUTO_SOURCES`, signals 노출 | −70/+15 |
| `src/metrics/crs.py` | 수정(선행) | `evaluate()` 복원 | +30 |
| `src/services/coach_evidence.py` | 수정 | source·trigger label | +15 |
| `frontend/src/lib/rowActionView.ts`, `lib/types/index.ts`, `AdjustmentCard.svelte` | 수정 | `isAutoSource`, 타입, 근거 표시 | +5/+15/+25 |
| `scripts/adjuster_backtest.py` | 신규 | v2 vs v3 빈도 비교(읽기 전용) | ~80 |
| tests: `test_adjustment_signals*.py`, `test_adjustment_triggers_v3.py`, `test_db_schema_v37.py`, `test_plan_adjustment_service.py` | 신규/수정 | 아래 §5 | ~30개 |
| `v0.3/data/decisions.md` | 수정(구현 시) | ADR-035 개정 | +20 |

## 5. 단계·검증
0. 선행: `crs.evaluate` 복원 → FRS `boost_hold`·래퍼.
1. `adjustment_signals`(+race) 추가(호출자 없음) + 단위 테스트(수집기별 정상·결측, race 창 판정, 추가 대회 포착, 외부 호출 없음).
2. dry-run 스크립트로 운영 DB **사본** 재분류 분포 확인 → v37 마이그레이션(백업·재생성·재분류) + `ensure_proposal` 분리(동작 불변 커밋 별도). 회귀: 같은 픽스처에서 `after`·`reasons`·rev 동일, source만 `readiness`/`pain`.
3. 소비처 6곳 `AUTO_SOURCES` 치환 → 레거시·신규 source 모두에서 Hero·row action·중복 방지 동일 동작.
4. 백테스트로 v2/v3 빈도 비교 후 사용자 확인 → `adjuster_v3` 트리거 활성화 + 주간 집계 로그.
5. API·프론트·coach_evidence. `pytest tests/`, `npm run check`, 픽스처 DB 브라우저 확인(운영 DB 미사용).
- 검증 체크: v37 전후 행 수·id·decision 일치, `PRAGMA integrity_check` ok, 재실행 멱등, CHECK 위반 INSERT 거부 테스트, `plan_overlay` 결과 불변, 기존 하향 불변 + 신규 하향(CRS·ACWR·체크인) 테스트, race 행 조정 제외, taper 창 BOOST hold, 신규 파일 300줄 이하, `check_docs.py` 통과.
- 호환·v1: v1 `views_training_loaders:45`·`plan.py`는 `adjust_todays_plan` 직접 호출만, `src/web`에서 `plan_adjustments` 조회 없음 → 영향 없음.

## 6. 대안
- **A. `reasons_json`에 신호 내장** — 마이그레이션 없음, 단 칩·원장·근거 혼재, rev 필터 필요. ADJ-4로 재생성이 확정돼 "무마이그레이션" 이점이 사라짐.
- **B. `signals_json` 컬럼(추천)** — v37 재생성에 합류해 추가 비용 거의 0.
- **source 대안(기각, ADJ-4 결정)**: `'crs'` 유지 + API 별칭 / `'auto'` 치환 — 사용자 결정으로 "주 트리거 종류" 채택.

## 7. 결정 필요
- **D1(ADJ-1) 결정됨(2026-10-11)**: (c) + 대회 계획(계획 중간·추가 대회 포함). 추가 후보 최종 목록은 D10.
- **D2(ADJ-2) 결정됨(2026-10-11)**: (c) CRS+ACWR 과부하+체크인 피로·통증 하향, `adjuster_v3`. 임계값은 D13, 빈도 기준은 D14.
- **D3 우선순위·counter 표시(미결정)**: §3.10 순서 채택 여부, counter 노출, 통증 제안 시 다른 신호 숨김. 주 트리거 선정(D15)과 같은 순서를 쓰면 일관, 달리하면 "판정 순서 ≠ 표시 라벨" 혼란.
- **D4(ADJ-4) 결정됨(2026-10-11)**: source = 주 트리거 종류, 기존 'crs' 행 재분류 백필(§3.9).
- **D5 저장 위치(미결정)**: A vs B — ADJ-4로 재생성이 확정돼 B의 추가 비용이 사라졌다는 점 반영.
- **D6 기존 행 signals(미결정)**: (a) `[]` 보존 / (b) reasons 키로 trigger 1건만 부분 백필(값·신선도 없음, source 재분류와 같은 판정 재사용) / (c) 미결정 proposed 행만 다음 조회 때 재기록. source 재분류는 D6과 무관하게 수행.
- **D7 사용자 표시(미결정)**.
- **D8 signals 갱신과 rev(미결정)**: 후보 (a)에 "source 변경 시도 rev+1" 포함 여부 추가.
- **D9 stale 신호 하향 트리거(미결정)**: v3에서 CRS·ACWR·체크인(전일분)이 실제 트리거가 되므로 영향 커짐 — 허용 시 제안 빈도↑, 불허 시 결측일 하향 누락.
- **D10 추가 신호 최종 목록(신규)**: §3.5 가용 6종 중 포함할 것(기록만/support/트리거) + 신규 수집 4종(질병, 여행·시간대, 고도, B/C 우선순위) 착수 여부. 가용분만 먼저 = 즉시 가능 / 신규 수집 포함 = 체크인·목표 UI 확장 필요(product 영역).
- **D11 B/C 레이스 원천(신규)**: (a) `planned_workouts` race 행 + `goals` 외는 모두 `unknown` 우선순위 / (b) `planned_workouts`에 `race_priority` 컬럼 추가 / (c) `goals`에 보조 레이스(status 'secondary') 허용 — 활성 목표 유니크(v32)와 충돌.
- **D12 대회 창 길이·추가 대회 trigger(신규)**: §3.4 제안 값(taper 3/7/14일, recovery 2/4/7일, B/C 절반) 채택 여부, 추가 대회 recovery 창에서 하향 trigger 허용 여부.
- **D13 v3 임계값·결합(신규)**: CRS level≤1, ACWR 1.5/1.8, 피로 ≥4 제안 값 확정 + OR(단일 신호) vs AND(2개 합의).
- **D14 빈도 경보 기준(신규)**: 주 3회 초과 2주 연속·수락률 급락 기준값, 로그만 vs 자동 롤백 플래그(`adjuster_version` 설정).
- **D15 주 트리거 선정(신규)**: §3.8 (a) 안전 고정 순서 / (b) 강도 기여 최대 / (c) 사용자 입력 우선.
- **D16 판별 불가 레거시 행(신규)**: (a) `readiness` 간주 / (b) `crs` 유지(레거시 의미) — (b)면 CHECK에 'crs' 의미가 둘로 갈림.

## 8. 범위 밖 메모
- `session_outcomes.crs_at_session`·replanner CRS 경고 문구, 폭염 보정의 일일 조정 연결(본 설계는 support/context 기록까지), R8 거리 비율 규칙, 신규 수집 신호의 입력 UI(product-architect), `b_race_week` 죽은 경로 정리.
