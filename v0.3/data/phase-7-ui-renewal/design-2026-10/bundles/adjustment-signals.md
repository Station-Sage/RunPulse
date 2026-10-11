# 조정 제안 근거 신호 확장 (adjustment-signals)

> 작성 2026-10-11 · 상태: 설계 초안(미확정) · 관련: [ADJUSTMENT-SOURCE-CRS-LABEL], [CRS-EVALUATE-MISSING], FRS-12~19(`patterns/data-freshness.md` §2.6·§2.7), ADR-035
> 전제(결정됨): `crs.evaluate()` 복원(저장 CRS·신선도 읽기 전용), CRS stale/게이트 불명 시 BOOST만 보류(`adjuster_v2`), `plan_service.todays_adjustment_with_hold` 래퍼, Hero `as_planned`+`hold_reason`.

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
**3.1 개념 분리.** `source` = 생성 주체(actor: 시스템 자동·사용자·코치)로만 해석하고, 근거는 새 구조 `signals`로 옮긴다. `source='crs'` 값은 레거시 이름으로 유지(값 변경은 결정 필요 D4).

**3.2 저장(추천: 컬럼 추가).** 스키마 v37: `ALTER TABLE plan_adjustments ADD COLUMN signals_json TEXT NOT NULL DEFAULT '[]'`. 테이블 재생성·CHECK 변경 없음, ADR-035 오버레이(`plan_overlay`는 `after_json`만 읽음)·유니크 인덱스 불변. 항목 형태:
```json
{"signal":"crs","role":"trigger|support|counter|hold|context","value":2,"detail":{"level_label":"…","gates":["hrv"]},
 "as_of":"2026-10-11","freshness":"fresh|stale|partial|missing","provider":"runpulse:formula_v1"}
```
`role`: trigger=제안 방향을 만든 신호, support=같은 방향, counter=반대 방향(예: 피로도 high인데 UTRS 높음), hold=BOOST 보류 사유(FRS-16 `reasons` 재사용), context=판정 미사용 참고값. `reasons_json`은 현행대로 UI 칩·advisory 원장으로 남긴다(무수정).

**3.3 수집 모듈 `src/services/adjustment_signals.py`(신규, 서비스 계층 — ADR-009는 Calculator 대상이라 해당 없음, 단 기존 함수 재사용 우선).**
- `collect(conn, day, *, readiness=None, crs=None, hold=None) -> list[dict]`: `readiness_decision`(이미 계산된 dict 주입 가능)·`crs.evaluate(conn, day)`·metric_store `utrs`/`acwr` 1건·`plan_pain._pain_rows`·체크인 최신 1건을 읽어 위 형태로 정규화. 각 수집기는 try/except → 해당 신호만 `freshness:"missing"`(전체 실패 금지). 외부 호출(폭염 예보)은 **캐시 조회만**, 없으면 생략.
- `classify(signals, proposal) -> signals`: 제안 dict(`adjusted_type`, `fatigue_level`, `reasons`)를 보고 role 부여. 통증 제안이면 pain=trigger, 나머지는 context.
- 순수 함수 분리(`classify`)로 DB 없이 테스트.

**3.4 생성 흐름(`ensure_proposal`).** 현행 우선순위 유지: `plan_pain.proposal` → 래퍼 `todays_adjustment_with_hold`(FRS-18 6단계). 그 결과에 `collect`+`classify`로 `signals_json`을 함께 기록. **1단계에서는 제안 방향·`after`·`reasons`를 바꾸지 않는다**(근거 기록만) → `rule_version` 불변(`adjuster_v2`/`pain_v1`). 트리거 확장(CRS level≤1·ACWR 과부하·체크인 피로/통증이 새 하향을 만듦)은 D2 결정 시 2단계에서 `adjuster_v3`로 상향.

**3.5 우선순위·충돌(2단계 적용 시 후보, 확정은 D3).** 통증 기록 > 체크인 통증 > 하향 신호(피로도 high, CRS level≤1, …) > 상향. 하향·상향 동시 → 하향 우선(현 Hero `adjusted` 우선과 동일). BOOST 보류(FRS-12~17)는 상향 경로만 막고 하향 판정·signals 기록에는 `role:"hold"`로만 합류 — 저장 행은 하향뿐이라 hold는 보통 Hero 쪽에만 나타남. stale 신호를 하향 트리거로 쓸지(D9)는 FRS D17과 비대칭 문제.

**3.6 rev·갱신.** 현행 `ensure_proposal`은 `after/reasons/before`가 바뀌면 `rev+1`. signals는 값이 매 조회 바뀔 수 있어(BB 동기화 등) rev에 포함하면 수락 중 `REV_MISMATCH` 409가 늘어난다 → 제안 상태에서는 **trigger 집합이 바뀔 때만 rev+1**, 값만 바뀌면 rev 유지 UPDATE, accepted 이후 동결(D8).

**3.7 읽기·소비처.** `_to_dict`에 `signals` 추가(API 필드 추가만), 프론트 `PlanAdjustment.signals?: AdjustmentSignal[]`, `AdjustmentCard`는 표시 범위(D7) 결정 후 렌더. `coach_evidence`는 `_adjustment_in_effect` 시 trigger 신호를 근거 label로 사용(문구는 FRS-4 문구 체계). `rowActionView.ts:185`의 `source==='crs'` 판정은 D4가 (a)면 무수정. R·M은 `crs.evaluate` 복원만으로 CRS가 채워지며 본 설계 범위는 그 출력 형태를 `collect`와 공유하는 것까지.

## 4. 변경 파일 표 (추천안 B 기준)
| 파일 | 구분 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v37.py` | 신규 | `signals_json` ADD COLUMN(존재 시 skip, 멱등) | ~25 |
| `src/db_setup.py` | 수정 | `SCHEMA_VERSION=37`, ensure 호출 | +3 |
| `src/services/adjustment_signals.py` | 신규 | `collect`·`classify`·정규화 | ~150 |
| `src/services/plan_adjustment_proposal.py` | 신규(분리) | `_build`·`_live`·`ensure_proposal` 이동(원 파일 301줄 > 300 규칙) | ~90 |
| `src/services/plan_adjustment_service.py` | 수정 | 이동분 제거·재노출, `_COLS`/`_to_dict`에 signals | −70/+10 |
| `src/metrics/crs.py` | 수정(선행 항목) | `evaluate()` 복원 — [CRS-EVALUATE-MISSING] | +30 |
| `src/services/coach_evidence.py` | 수정 | trigger 신호 label | +15 |
| `frontend/src/lib/types/index.ts`, `components/plan/AdjustmentCard.svelte` | 수정 | 타입 추가·근거 표시(D7) | +10 / +25 |
| `tests/test_adjustment_signals.py` | 신규 | 수집기별 정상·결측, classify 역할, 외부 호출 없음 | ~12개 |
| `tests/test_plan_adjustment_service.py`, `tests/test_db_schema_v37.py` | 수정/신규 | signals 저장·rev 규칙·레거시 행 `[]`·멱등 마이그레이션 | +6 / 2 |
| `v0.3/data/decisions.md` | 수정(구현 시) | ADR-035 부록 "근거 신호 signals_json" | +5 |

## 5. 단계·검증
0. 선행: `crs.evaluate` 복원 → FRS `boost_hold`·래퍼(§2.7 1~6단계). 각 기존 테스트 통과.
1. `adjustment_signals` 추가(호출자 없음) + 단위 테스트.
2. v37 마이그레이션 + `plan_adjustment_proposal` 분리(동작 불변 리팩터 커밋 별도) → signals 기록. 회귀: 같은 픽스처에서 `after`·`reasons`·`rule_version`·rev가 이전과 동일.
3. API·프론트·coach_evidence. `pytest tests/`, `npm run check`, 픽스처 DB로 브라우저 `/today`·`/plan` 조정 카드(운영 DB 미사용).
4. (D2 채택 시) 트리거 확장 + `adjuster_v3` + `algo_changelog`는 해당 없음(Calculator 아님) — 대신 ADR-035 부록·하향 불변/신규 하향 테스트.
- 검증 체크: 레거시 행(`source='crs'`, `signals_json='[]'`) 읽기·수락·되돌리기 정상, `plan_overlay` 결과 불변, `check_docs.py` 통과, 신규 파일 300줄 이하.
- 호환·v1: v1 `views_training_loaders:45`·`plan.py`는 `adjust_todays_plan` 직접 호출만 하고 `src/web`에서 `plan_adjustments` 조회 없음(grep 확인) → 영향 없음. v1 제거 시 추가 작업 없음.

## 6. 대안
- **A. `reasons_json`에 `{key:"signal",…}` 항목으로 내장** — 마이그레이션 없음, 프론트는 `label` 없는 항목을 이미 걸러 호환. 단 칩·advisory 원장·근거가 한 배열에 섞이고, `ensure_proposal`의 reasons 비교가 신호 값 변동마다 rev를 올려 D8 처리에 별도 필터 필요.
- **B. `signals_json` 컬럼 추가(추천)** — ADD COLUMN 1회(재생성 없음), 의미 분리·rev 규칙 단순, 레거시 행은 기본값 `[]`로 자연 호환. 비용은 스키마 버전 +1.

## 7. 결정 필요
- **D1 근거 기록 신호 목록**: (a) 현행 판정 입력만(BB·수면·스트레스·TSB·통증) — 정확·최소 / (b) (a)+CRS·UTRS·ACWR·HRV·체크인 context — 설명력↑, 판정에 안 쓴 값이 근거처럼 보일 위험 / (c) (b)+대회 임박·폭염(캐시) — 최대, 외부 의존.
- **D2 트리거 확장**: (a) 기록만(1단계에서 종료) / (b) CRS level≤1 하향 추가 / (c) CRS+ACWR 과부하+체크인 피로·통증 하향 추가 — (b)(c)는 `adjuster_v3`·제안 빈도 변화.
- **D3 우선순위·counter 표시**: 반대 방향 신호(counter)를 사용자에게 보일지, 통증 제안 시 다른 신호 숨김 여부.
- **D4 source 라벨**: (a) `'crs'` 유지, API에서 `origin:"auto"` 별칭 노출 — 무마이그레이션 / (b) 테이블 재생성으로 CHECK에 `'auto'` 추가·기존 값 치환 — 이름 정확, SQLite 재생성·코드 6곳+`rowActionView.ts` 수정.
- **D5 저장 위치**: §6 A vs B.
- **D6 기존 행**: (a) 보존·`[]` / (b) `reasons` 키(`readiness`·`pain`)로 부분 백필(값·신선도 없음) / (c) 미결정 proposed 행만 다음 조회 때 재기록.
- **D7 사용자 표시**: 카드 목록에도 신호 칩 / 상세만 / Coach 근거에만, 신호명·신선도 문구(FRS-4·FRS-13 체계 편입 여부).
- **D8 signals 갱신과 rev**: trigger 변화 시만 rev+1(제안) / 모든 변화 rev+1 / 생성 시 동결.
- **D9 stale 신호의 하향 트리거 허용**: 허용(안전 방향) / 불허(FRS D17과 대칭) / 신선도별 가중.

## 8. 범위 밖 메모
- `session_outcomes.crs_at_session`·replanner CRS 경고의 문구·임계 재설계, 폭염 보정의 일일 조정 연결, R8 거리 비율 규칙은 이 문서 범위 밖(각 항목 별도 설계).
