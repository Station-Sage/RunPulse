# P7-PRED-00 — 예측 리뉴얼 r4 유닛 색인 (autopilot 실행 순서)

- 작성: 2026-09-26, running-data-coach. 근거: `../REVIEW-07-prediction-renewal.md` §R4(R4-8·R4-9 포함), `../REVIEW-08-metric-audit.md` §R4, `../REVIEW-09-signal-design-r4.md`, 미검증 항목 `P7-PRED-99-TODO-UNVERIFIED.md`.
- **사용자 결정 반영(2026-09-26)**: r3 (c) 예측이 기본 표시, r4는 섀도(후보) 병행 계산 + 스냅샷(P7-PRED-63) 전향 평가. 85·87~90은 승인(판단 → 자동), 86은 삭제가 아니라 통합.
- 모든 코드는 저장소 사본(샌드박스)에서 작성·테스트했고, 명세 블록만으로 새 사본에 순서대로 적용해 검증했다(아래 "검증 상태").
- 명세 파일: `PRED-1x-data-integrity.md`, `PRED-2x-segments-hr.md`, `PRED-3x-weather.md`, `PRED-4x-training-plan.md`, `PRED-5x-prediction.md`, `PRED-6x-backfill.md`, `PRED-7x-ui.md`, `PRED-8x-metric-fixes.md`.

## 실행 순서 (위에서 아래로 — 이 순서가 곧 의존 순서다. BACKLOG 메타의 deps 는 모두 `[]`)

| 순서 | 유닛 | 이름 | r3 대비 | UI 노출 | 실DB·재동기화 | 명세 | mode | 명세 상태 |
|---|---|---|---|---|---|---|---|---|
| 1 | P7-PRED-11 | 스키마 v20 | 동일 | 없음 | 앱 기동 시 멱등 ALTER | `PRED-1x-*.md` | auto | **작성·적용 검증 통과** |
| 2 | P7-PRED-12 | Garmin 추출 보존(랩·스트림·활동 GAP) | 동일 | 없음 | P7-PRED-13 재추출 후 반영 | `PRED-1x-*.md` | auto | **작성·적용 검증 통과** |
| 3 | P7-PRED-13 | 제자리 재추출 + reprocess 파손 수정 | 동일 | 없음 | **런북 2단계(사람)** | `PRED-1x-*.md` | auto | **작성·적용 검증 통과** |
| 4 | P7-PRED-14 | CalcContext 러닝 이력 API | 동일 | 없음 | 없음 | `PRED-1x-*.md` | auto | **작성·적용 검증 통과** |
| 5 | P7-PRED-84 | runpulse_vdot 상한 가드 | 동일 | 활동 VDOT 이상치 제거 | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 6 | P7-PRED-81 | 시리즈 canonical 집계 + rec 백분위(P7-PRED-82 포함) | 동일 | teroi·rec 카드 값 | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 7 | P7-PRED-87 | recompute-all 전 기간 기본·삭제 범위 = 재계산 범위 | 판단→자동(승인) | 없음 | 없음(도구) | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 8 | P7-PRED-20 | Daniels 공식·세트 등가 지속시간 + 칼만(순수) | 신규 | 없음 | 없음 | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 9 | P7-PRED-21 | 세그먼트 분해 r4(세트 구조) | 변경 | 없음 | 없음 | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 10 | P7-PRED-22 | 예측 라이브러리(r3 기본 + r4 섀도 + 전력 판정) | 변경 | 없음 | 없음 | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 11 | P7-PRED-23 | 분류기 v2(예측 비의존) | 변경 | 운동 유형 라벨 값 변화 | 재계산 시 | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 12 | P7-PRED-88 | TIDS 세그먼트 시간 기준 | 판단→자동(승인) | TIDS 분포·패턴 | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 13 | P7-PRED-24 | HR 프로필(자체·기기, 두 존 체계) | 동일(전력 판정만 effort.py) | P7-PRED-74에서 | 재계산 시 | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 14 | P7-PRED-25 | Garmin 참조값(LTHR·레이스 예측) 동기화 | 동일 | P7-PRED-72·74에서 | **런북 4단계(Garmin API)** | `PRED-2x-*.md` | auto | **작성·적용 검증 통과** |
| 15 | P7-PRED-86 | 날씨 모듈 통합(provider.py = 단일 Open-Meteo 클라이언트) | 재정의(r3 31 대체) | 없음 | 없음 | `PRED-3x-*.md` | auto | **작성·적용 검증 통과** |
| 16 | P7-PRED-32 | 활동 외기 기상 인제스트 + 우선순위 + sync 훅 | 변경(import) | 활동 날씨 값 | **런북 3단계(Open-Meteo API)** | `PRED-3x-*.md` | auto | **작성·적용 검증 통과** |
| 17 | P7-PRED-33 | 개인 기온 모델 | 동일 | P7-PRED-72·74에서 | 재계산 시 | `PRED-3x-*.md` | auto | **작성·적용 검증 통과** |
| 18 | P7-PRED-83 | sapi 외기 기온 | 동일 | SAPI 카드 0행 → 값 | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 19 | P7-PRED-90 | vdot_adj 폐기 + fearp 외기·이슬점 | 판단→자동(승인) | VDOT 출처 = race_pred_vdot | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 20 | P7-PRED-41 | 훈련 반응 r4(세트 기반, 기기 불필요) | 변경 | P7-PRED-74에서 | 재계산 시 | `PRED-4x-*.md` | auto | **작성·적용 검증 통과** |
| 21 | P7-PRED-42 | 계획 구조 형식 + 세그먼트 비교(순수) | 동일 | 없음 | 없음 | `PRED-4x-*.md` | auto | **작성·적용 검증 통과** |
| 22 | P7-PRED-43 | 매처 세그먼트 이행 저장 | 동일 | 없음 | 런북 6단계 | `PRED-4x-*.md` | auto | **작성·적용 검증 통과** |
| 23 | P7-PRED-51 | DARP r3 기본 + r4 섀도 2종 | 변경(섀도 추가) | 레이스 허브 예측값(r3 c) | 재계산 시 | `PRED-5x-*.md` | auto | **작성·적용 검증 통과** |
| 24 | P7-PRED-52 | rri·eftp 의존 복구 + marathon_shape v2 | 변경 | 셰이프·RRI 카드 | 재계산 시 | `PRED-5x-*.md` | auto | **작성·적용 검증 통과** |
| 25 | P7-PRED-89 | acwr·lsi·adti·rtti·hrss·di 재정의 | 판단→자동(승인) | 카드 값·데이터 부족 상태 | 재계산 시 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| 26 | P7-PRED-53 | 대회 확인 서비스 | 동일 | P7-PRED-73에서 | 사용자 입력 | `PRED-5x-*.md` | auto | **작성·적용 검증 통과** |
| 27 | P7-PRED-62 | 수용 백테스트 스크립트(r3·r4 나란히) | 변경 | 없음 | 읽기 전용 | `PRED-6x-*.md` | auto | **작성·적용 검증 통과** |
| 28 | P7-PRED-63 | 예측 스냅샷(v21) + 대회 전향 평가 | 신규(승인) | 없음(데이터) | 앱 기동 시 테이블 | `PRED-6x-*.md` | auto | **작성·적용 검증 통과** |
| 29 | P7-PRED-71 | 비교·근거·대회 확인 API(+섀도 후보 행) | 변경 | 없음(데이터) | 없음 | `PRED-7x-*.md` | auto | **작성·적용 검증 통과** |
| 30 | P7-PRED-72 | 레이스 허브 UI(73·74 포함) | 변경 | **Today 레이스 허브** | 없음 | `PRED-7x-*.md` | auto | **작성·적용 검증 통과** |
| 31 | P7-PRED-85 | 내장 Daniels 표 → 공식, import 경로 수정 | 신규(승인 2026-09-26) | 플래너 처방 페이스 변경 | 없음 | `PRED-8x-*.md` | auto | **작성·적용 검증 통과** |
| – | P7-PRED-61 | 실DB 백필 런북 | 변경(4b·5b) | – | **사람 실행** | `PRED-6x-*.md` | manual | 사람 실행 절 작성 |
| – | P7-PRED-44 | 외부 계획 인제스트(Garmin·Intervals) | 동일 | Plan 출처 배지 | **API 응답 확인 필요(사람)** | `PRED-4x-*.md` | manual | 사람 실행 절 작성 |

폐기: r3 P7-PRED-31(`src/weather/openmeteo.py` 신설 → P7-PRED-86 통합), r3 P7-PRED-86 "삭제" 정의, r3 P7-PRED-52의 vdot_adj 의존 교체(→ P7-PRED-90 폐기).

## 공유 파일 규칙

- `src/metrics/engine.py`: P7-PRED-87 → 24 → 33 → 90 → 41 → 51 순서로 **누적** 편집한다.
- `scripts/check_docs.py`: 24 → 33 → 90 → 41 → 51 순서로 누적 편집한다.
- `src/utils/metric_registry.py`: 24 → 25 → 32 → 33 → 41 → 51 순서로 누적 편집한다.
- `tests/test_phase4_dod.py`: 87 → 88 순서로 누적 편집한다.
- `src/db_setup.py`·`tests/test_db_setup.py`·`tests/test_phase1_schema.py`: 11 → 63 순서로 누적 편집한다.
- `src/services/race_result_service.py`: 53 → 63 순서로 누적 편집한다.
- 각 diff는 직전 유닛까지 적용된 상태가 기준이다. 순서를 바꾸면 문맥이 맞지 않는다.
- calculator 수: 32 → 33(24) → 34(33) → 33(90, vdot_adj 제거) → 34(41) → 37(51: darp_ref + 섀도 2).
- calculator·registry를 바꾼 유닛은 `python3 scripts/gen_metric_dictionary.py`, 새 파일이 생긴 유닛은 `python3 scripts/gen_files_index.py`를 실행한다.
- "삭제" 블록은 `git rm`이다.

## 검증 상태 (2026-09-26, 무엇을 실제로 돌렸나)

| 항목 | 방법 | 결과 |
|---|---|---|
| 명세만으로 구현 가능한가 | 저장소 새 사본에 명세의 전문·diff·삭제 블록만 위 순서대로 적용(`patch -p1`). 유닛마다 `gen_metric_dictionary`·`gen_files_index` 후 해당 유닛 pytest·`check_docs`·`check_data_consistency` | 31단계 전부 통과. 적용 사본과 샌드박스의 `src/`·`tests/`·`scripts/`가 파일 단위로 같다 |
| 전체 회귀 | 적용 완료 사본에서 `pytest tests/`(realdb 제외) | 실패 3건만 남는다. 모두 `test_autopilot_run_unit.py::TestPostVerify`로, 사본에 autopilot 워크트리가 없어 나는 환경 한정 실패다(r3 때와 같음, 저장소에서는 해당 없음) |
| 프론트 | `node --test`(predictionCompare·raceHub·format) | 통과. **`svelte-check`·`build`는 이번에 돌리지 않았다**(사용자 지시). 병합 전 사람이 REVIEW.md 절차(브라우저 스모크 포함)로 확인 |
| 수치 | 수용 백테스트·현재 예측은 실DB 사본에서 실행한 값(REVIEW-07 §R4-8(6)) | in-sample. 전향 평가는 P7-PRED-63 이후 |

## 실DB 시점

재추출·외기 백필·Garmin 이력·재계산(`recompute --days 1100`, 재계산 전후 예측 비교 4b·5b)·매칭 소급은 모두 P7-PRED-61 런북(사람)에서 **백업 후** 한다. 사용자가 따로 지시할 때만 한다.

## BACKLOG 등록용 (한 줄 메타 — 그대로 붙여 넣기, 위 순서대로)

- **[P7-PRED-11]** 스키마 v20 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-11 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/db_schema_v20.py", "src/db_setup.py", "src/utils/db_helpers.py", "tests/helpers_pred.py", "tests/test_pred_schema_v20.py", "tests/test_db_setup.py", "tests/test_phase1_schema.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_schema_v20.py tests/test_db_setup.py tests/test_phase1_schema.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-12]** Garmin 추출 보존(랩·스트림·활동 GAP) — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-12 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/sync/extractors/garmin_lap_fields.py", "src/sync/extractors/garmin_extractor.py", "tests/test_garmin_lap_fields.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_lap_fields.py tests/test_garmin_extractor.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-13]** 제자리 재추출 + reprocess 파손 수정 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-13 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/sync/reextract.py", "src/sync/reprocess.py", "tests/test_reextract.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_reextract.py tests/test_reprocess.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-14]** CalcContext 러닝 이력 API — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-14 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/context_runs.py", "src/metrics/base.py", "tests/test_context_runs.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_context_runs.py tests/test_activity_calcs.py tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-84]** runpulse_vdot 상한 가드 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-84 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/vdot.py", "tests/test_vdot_guard.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_vdot_guard.py tests/test_activity_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-81]** 시리즈 canonical 집계 + rec 백분위(P7-PRED-82 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-81 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/teroi.py", "src/metrics/rec.py", "src/metrics/tpdi.py", "src/metrics/critical_power.py", "tests/test_rec.py"], "verify": ["python3 -m pytest tests/test_rec.py tests/test_teroi.py tests/test_tpdi.py tests/test_critical_power.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-87]** recompute-all 전 기간 기본·삭제 범위 = 재계산 범위 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-87 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/engine.py", "src/metrics/cli.py", "tests/test_recompute_all_range.py", "tests/test_phase4_dod.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_recompute_all_range.py tests/test_phase4_dod.py tests/test_engine.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-20]** Daniels 공식·세트 등가 지속시간 + 칼만(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-20 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/__init__.py", "src/metrics/prediction/daniels.py", "src/metrics/prediction/kalman.py", "tests/test_daniels_kalman.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_daniels_kalman.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-21]** 세그먼트 분해 r4(세트 구조) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-21 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/segments.py", "tests/test_segments.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_segments.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-22]** 예측 라이브러리(r3 기본 + r4 섀도 + 전력 판정) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-22 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/__init__.py", "src/metrics/prediction/core.py", "src/metrics/prediction/physio.py", "src/metrics/prediction/effort.py", "src/metrics/prediction/signals.py", "src/metrics/prediction/core_r4.py", "src/metrics/prediction/signals_r4.py", "tests/test_prediction_core.py", "tests/test_prediction_signals.py", "tests/test_prediction_core_r4.py", "tests/test_prediction_signals_r4.py", "tests/test_race_effort.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_core.py tests/test_prediction_signals.py tests/test_prediction_core_r4.py tests/test_prediction_signals_r4.py tests/test_race_effort.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-23]** 분류기 v2(예측 비의존) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-23 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/classifier.py", "tests/test_activity_calcs.py"], "verify": ["python3 -m pytest tests/test_activity_calcs.py tests/test_mock_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-88]** TIDS 세그먼트 시간 기준 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-88 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/tids.py", "tests/test_tids_time.py", "tests/test_phase4_dod.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_tids_time.py tests/test_phase4_dod.py tests/test_activity_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-24]** HR 프로필(자체·기기, 두 존 체계) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-24 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/hr_profile.py", "tests/test_hr_profile.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_hr_profile.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-25]** Garmin 참조값(LTHR·레이스 예측) 동기화 — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-25 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/sync/garmin_ref_parsers.py", "src/sync/garmin_ref_sync.py", "src/sync/garmin_daily_extensions.py", "tests/test_garmin_ref_parsers.py", "tests/test_garmin_ref_sync.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_ref_parsers.py tests/test_garmin_ref_sync.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-86]** 날씨 모듈 통합(provider.py = 단일 Open-Meteo 클라이언트) — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-86 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/weather/provider.py", "tests/test_weather_provider.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_weather_provider.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-32]** 활동 외기 기상 인제스트 + 우선순위 + sync 훅 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-32 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/weather/activity_weather.py", "src/utils/metric_priority.py", "src/sync.py", "tests/test_weather_ingest.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_weather_provider.py tests/test_weather_ingest.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-33]** 개인 기온 모델 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-33 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/heat_model.py", "tests/test_heat_model.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_heat_model.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-83]** sapi 외기 기온 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-83 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/sapi.py", "tests/test_sapi.py"], "verify": ["python3 -m pytest tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-90]** vdot_adj 폐기 + fearp 외기·이슬점 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-90 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/vdot_adj.py", "tests/test_vdot_adj.py", "src/metrics/engine.py", "scripts/check_docs.py", "src/metrics/fearp.py", "tests/test_fearp_v2.py", "src/web/views_dashboard.py", "src/web/views_report_sections_data.py", "src/training/planner_config.py", "src/training/readiness.py", "src/services/plan_template_service.py", "tests/test_readiness.py", "tests/test_plan_template_service.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_fearp_v2.py tests/test_readiness.py tests/test_plan_template_service.py tests/test_sapi.py tests/test_engine.py tests/test_phase4_dod.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-41]** 훈련 반응 r4(세트 기반, 기기 불필요) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-41 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/response.py", "src/metrics/training_response.py", "tests/test_training_response.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_training_response.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-42]** 계획 구조 형식 + 세그먼트 비교(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-42 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/training/outcome_v2.py", "tests/test_outcome_v2.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-43]** 매처 세그먼트 이행 저장 — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-43 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/training/outcome_store.py", "src/training/matcher.py", "tests/test_outcome_store.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_store.py tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-51]** DARP r3 기본 + r4 섀도 2종 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-51 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/darp.py", "src/metrics/darp_r4.py", "tests/test_darp_v2.py", "tests/test_darp_r4.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "tests/test_metric_naming.py", "tests/test_validator.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_darp_v2.py tests/test_darp_r4.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py tests/test_dashboard_service.py tests/test_ai_context.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-52]** rri·eftp 의존 복구 + marathon_shape v2 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-52 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/marathon_shape.py", "src/metrics/rri.py", "src/metrics/eftp.py", "tests/test_marathon_shape.py", "tests/test_rri.py", "tests/test_eftp.py"], "verify": ["python3 -m pytest tests/test_marathon_shape.py tests/test_rri.py tests/test_eftp.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-89]** acwr·lsi·adti·rtti·hrss·di 재정의 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-89 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/acwr.py", "src/metrics/lsi.py", "src/metrics/adti.py", "src/metrics/rtti.py", "src/metrics/hrss.py", "src/metrics/di.py", "tests/test_di_v2.py", "tests/test_activity_core_sanitize.py", "tests/test_daily_calcs.py", "tests/test_rtti.py", "tests/test_engine.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_di_v2.py tests/test_activity_core_sanitize.py tests/test_daily_calcs.py tests/test_rtti.py tests/test_engine.py tests/test_cirs.py tests/test_crs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-53]** 대회 확인 서비스 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-53 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/services/race_result_service.py", "tests/test_race_result_service.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_race_result_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-62]** 수용 백테스트 스크립트(r3·r4 나란히) — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-*.md`의 P7-PRED-62 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["scripts/pred_backtest.py", "tests/test_pred_backtest.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_backtest.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-63]** 예측 스냅샷(v21) + 대회 전향 평가 — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-*.md`의 P7-PRED-63 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/db_schema_v21.py", "src/db_setup.py", "src/services/prediction_snapshot_service.py", "src/services/race_result_service.py", "src/web/bg_sync.py", "tests/test_prediction_snapshot.py", "tests/test_db_setup.py", "tests/test_phase1_schema.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_snapshot.py tests/test_db_setup.py tests/test_phase1_schema.py tests/test_race_result_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-71]** 비교·근거·대회 확인 API(+섀도 후보 행) — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-71 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/services/prediction_compare_service.py", "src/api/routes_prediction.py", "src/api/__init__.py", "src/services/race_hub_service.py", "tests/test_prediction_compare.py", "tests/test_api_prediction.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_compare.py tests/test_api_prediction.py tests/test_api_today.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-72]** 레이스 허브 UI(73·74 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-72 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["frontend/src/lib/predictionCompare.ts", "frontend/tests/predictionCompare.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/prediction.ts", "frontend/src/lib/components/PredictionCompare.svelte", "frontend/src/lib/components/PredictionBasis.svelte", "frontend/src/lib/components/RaceConfirmList.svelte", "frontend/src/lib/components/RaceHub.svelte", "frontend/src/lib/format.ts"], "verify": ["cd frontend && npm run check", "cd frontend && node --test tests/predictionCompare.test.mjs tests/raceHub.test.mjs tests/format.test.mjs", "cd frontend && npm run build"]} -->
- **[P7-PRED-85]** 내장 Daniels 표 → 공식, import 경로 수정 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-85 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/utils/daniels_table.py", "src/ai/tool_exec_context.py", "src/training/interval_calc.py", "src/training/planner_rules.py", "tests/test_daniels_table.py"], "verify": ["python3 -m pytest tests/test_daniels_table.py tests/test_eftp.py tests/test_marathon_shape.py tests/test_replanner.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-61]** 실DB 백필 런북 — 사람 전용(`PRED-6x-*.md`의 P7-PRED-61 절).
- **[P7-PRED-44]** 외부 계획 인제스트(Garmin·Intervals) — 사람 전용(`PRED-4x-*.md`의 P7-PRED-44 절).
