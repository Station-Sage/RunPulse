# P7-PRED-00 — 예측 리뉴얼 r3 유닛 색인 (autopilot 실행 순서)

- 작성: 2026-09-25, running-data-coach. 근거 문서: `../REVIEW-07-prediction-renewal.md`(r3), `../REVIEW-08-metric-audit.md`(r3).
- 모든 코드는 저장소 사본(`/tmp/rp_sandbox`)에서 구현·검증했다: 전체 `pytest` **1,703 통과**(실패 3건은 샌드박스에 autopilot 워크트리가 없어서 나는 `test_autopilot_run_unit.py` — 저장소에서는 해당 없음), `check_docs` 필수 오류 0, `check_data_consistency` 오류 0. 프론트는 사본에서 `svelte-check` 0 errors·`node --test` 통과·`build` 성공.
- 실DB 사본(읽기 전용으로 복제)에서 재추출·기상·재계산·수용 백테스트까지 종단 실행했다(P7-PRED-61 표의 "기대" 값).
- 명세 파일: `PRED-1x-data-integrity.md`, `PRED-2x-segments-hr.md`, `PRED-3x-weather.md`, `PRED-4x-training-plan.md`, `PRED-5x-prediction.md`, `PRED-6x-backfill.md`, `PRED-7x-ui.md`, `PRED-8x-metric-fixes.md`.

## 실행 순서 (위에서 아래로. 같은 단계 안에서는 의존만 지키면 병렬 가능)

| 유닛 | 이름 | 의존 | UI 노출 | 실DB·재동기화 | 명세 | mode |
|---|---|---|---|---|---|---|
| P7-PRED-11 | 스키마 v20 | – | 없음 | 앱 기동 시 멱등 ALTER | `PRED-1x-*.md` | auto |
| P7-PRED-12 | Garmin 추출 보존(랩·스트림·활동 GAP) | P7-PRED-11 | 없음 | P7-PRED-13 재추출 후 반영 | `PRED-1x-*.md` | auto |
| P7-PRED-13 | 제자리 재추출 + reprocess 파손 수정 | P7-PRED-11, P7-PRED-12 | 없음 | **런북 2단계(사람)** | `PRED-1x-*.md` | auto |
| P7-PRED-14 | CalcContext 러닝 이력 API | P7-PRED-11 | 없음 | 없음 | `PRED-1x-*.md` | auto |
| P7-PRED-84 | runpulse_vdot 상한 가드 | P7-PRED-11 | 활동 VDOT 이상치 제거 | 재계산 시 | `PRED-8x-*.md` | auto |
| P7-PRED-81 | 시리즈 canonical 집계 + rec 백분위(P7-PRED-82 포함) | P7-PRED-14 | teroi·rec 카드 값 | 재계산 시 | `PRED-8x-*.md` | auto |
| P7-PRED-21 | 세그먼트 분해(순수) | – | 없음 | 없음 | `PRED-2x-*.md` | auto |
| P7-PRED-22 | 예측·생리 순수 라이브러리 | – | 없음 | 없음 | `PRED-2x-*.md` | auto |
| P7-PRED-23 | 분류기 v2 + TIDS | P7-PRED-14, P7-PRED-21, P7-PRED-22 | 운동 유형 라벨 값 변화 | 재계산 시 | `PRED-2x-*.md` | auto |
| P7-PRED-24 | HR 프로필(자체·기기, 두 존 체계) | P7-PRED-14, P7-PRED-22 | P7-PRED-74에서 | 재계산 시 | `PRED-2x-*.md` | auto |
| P7-PRED-25 | Garmin 참조값(LTHR·레이스 예측) 동기화 | P7-PRED-11 | P7-PRED-72·74에서 | **런북 4단계(Garmin API)** | `PRED-2x-*.md` | auto |
| P7-PRED-31 | Open-Meteo 클라이언트 | P7-PRED-22 | 없음 | 없음 | `PRED-3x-*.md` | auto |
| P7-PRED-32 | 활동 외기 기상 인제스트 + 우선순위 + sync 훅 | P7-PRED-11, P7-PRED-31 | 활동 날씨 값 | **런북 3단계(Open-Meteo API)** | `PRED-3x-*.md` | auto |
| P7-PRED-33 | 개인 기온 모델 | P7-PRED-14, P7-PRED-22, P7-PRED-32 | P7-PRED-72·74에서 | 재계산 시 | `PRED-3x-*.md` | auto |
| P7-PRED-83 | sapi 외기 기온 | P7-PRED-14, P7-PRED-32 | SAPI 카드 0행 → 값 | 재계산 시 | `PRED-8x-*.md` | auto |
| P7-PRED-41 | 훈련 반응(세그먼트 단위) | P7-PRED-14, P7-PRED-22, P7-PRED-24, P7-PRED-33 | P7-PRED-74에서 | 재계산 시 | `PRED-4x-*.md` | auto |
| P7-PRED-42 | 계획 구조 형식 + 세그먼트 비교(순수) | P7-PRED-11, P7-PRED-21 | 없음 | 없음 | `PRED-4x-*.md` | auto |
| P7-PRED-43 | 매처 세그먼트 이행 저장 | P7-PRED-11, P7-PRED-23, P7-PRED-42 | 없음 | 런북 6단계 | `PRED-4x-*.md` | auto |
| P7-PRED-51 | DARP v2 (b)(c) | P7-PRED-14, P7-PRED-22, P7-PRED-24, P7-PRED-25, P7-PRED-33 | 레이스 허브 예측값 교체 | 재계산 시 | `PRED-5x-*.md` | auto |
| P7-PRED-52 | 일별 VDOT 의존 메트릭 복구 | P7-PRED-51 | 셰이프·RRI 카드 0행 → 값 | 재계산 시 | `PRED-5x-*.md` | auto |
| P7-PRED-53 | 대회 확인 서비스 | P7-PRED-11 | P7-PRED-73에서 | 사용자 입력 | `PRED-5x-*.md` | auto |
| P7-PRED-62 | 수용 백테스트 스크립트 | P7-PRED-24, P7-PRED-33, P7-PRED-51 | 없음 | 읽기 전용 | `PRED-6x-*.md` | auto |
| P7-PRED-61 | 실DB 백필 런북 | P7-PRED-13, P7-PRED-25, P7-PRED-32, P7-PRED-43, P7-PRED-51, P7-PRED-52, P7-PRED-62 | – | **사람 실행** | `PRED-6x-*.md` | manual |
| P7-PRED-71 | 비교·근거·대회 확인 API | P7-PRED-25, P7-PRED-51, P7-PRED-53 | 없음(데이터) | 없음 | `PRED-7x-*.md` | auto |
| P7-PRED-72 | 레이스 허브 범위·신뢰도·3경로 비교·근거·대회 확인 UI(73·74 포함) | P7-PRED-71 | **Today 레이스 허브** | 없음 | `PRED-7x-*.md` | auto |
| P7-PRED-44 | 외부 계획 인제스트(Garmin·Intervals) | P7-PRED-42 | Plan 출처 배지 | **API 응답 확인 필요(사람)** | `PRED-4x-*.md` | manual |

단계 구분: ① 무결성·보존 P7-PRED-11·12·13·14·84·81 → ② 세그먼트·HR P7-PRED-21·22·23·24·25 → ③ 날씨 P7-PRED-31·32·33·83 → ④ 훈련 반응·계획 P7-PRED-41·42·43 → ⑤ 예측 P7-PRED-51·52·53·62 → ⑥ 백필 P7-PRED-61(사람) → ⑦ UI P7-PRED-71·72 → (별도) P7-PRED-44(사람). P7-PRED-81은 P7-PRED-82를, P7-PRED-72는 P7-PRED-73·74를 포함한다(같은 파일을 건드리므로 한 유닛).

## 의존 그래프

```
P7-PRED-11 ─┬─ 12 ── 13 ──────────────────────────────┐
            ├─ 14 ─┬─ 81(+82)                          │
            │      ├─ 23 ◀─ 21, 22                     │
            │      ├─ 24 ◀─ 22 ─┐                      │
            ├─ 25 ─────────────┤                      │
            ├─ 31 ◀─ 22 ── 32 ─┼─ 33 ─┬─ 41           │
            │                  │      └─ 83           ├─▶ 61(사람: 백필)
            ├─ 42 ◀─ 21 ── 43 ◀─ 23                   │
            ├─ 53                                      │
            └─ 84           24·25·33 ─▶ 51 ─┬─ 52 ────┤
                                            ├─ 62 ────┘
                              25·51·53 ─▶ 71 ─▶ 72(+73·74)
            42 ─▶ 44(사람)
```

## 검증 상태 (무엇을 실제로 돌렸나)

| 항목 | 방법 | 결과 |
|---|---|---|
| 명세만으로 구현 가능한가 | 저장소 새 사본에 명세의 전문·diff 블록만 순서대로 적용(`patch -p1`) → 유닛마다 `gen_metric_dictionary`·`gen_files_index` 후 해당 verify 실행 | 24단계 전부 통과, 최종 사본 = 샌드박스와 파일 단위 동일 |
| 전체 회귀 | 적용 완료 사본에서 `pytest tests/` | 1,707 통과, 실패 3(autopilot 워크트리 부재로 인한 `test_autopilot_run_unit.py` — 저장소에선 해당 없음) |
| 순수 계산 기대값 | 모든 테스트 기대값은 /tmp에서 실행해 확인한 값 | 통과 |
| 실데이터 종단 | 실DB를 `mode=ro`로 복제한 사본에서 재추출·기상 주입·400일 재계산(159초)·수용 백테스트 | D-0 MAE 1.26%(n=8) PASS |
| 프론트 | 사본에서 `svelte-check`(0 errors, 기존 경고 15)·`node --test`·`build` | 통과. **브라우저 스모크는 하지 않음**(REVIEW.md 절차대로 병합 전 사람이 확인) |
| 미검증(가정) | Garmin 이력 API 응답 형태(P7-PRED-25), LT 속도 ×10 단위, Strava `Z` 시작 시각=현지, 외부 계획 API(P7-PRED-44) | 런북 4단계·P7-PRED-44에서 확인 |

## 공유 파일 규칙

- `src/metrics/engine.py`·`src/utils/metric_registry.py`·`scripts/check_docs.py`는 P7-PRED-24 → 25 → 32 → 33 → 41 → 51 순서로 **누적** 편집한다. 각 유닛의 diff는 직전 유닛까지 적용된 상태 기준이다(순서를 바꾸면 diff 문맥이 맞지 않는다).
- calculator 수: 32 → 33(P7-PRED-24) → 34(P7-PRED-33) → 35(P7-PRED-41) → 36(P7-PRED-51).
- 새 테이블·CalcContext API·Calculator를 추가하므로 `.claude/skills/*/SKILL.md`의 grep 레시피가 유효한지 확인한다(`tests/test_ai_tool_guide.py`가 일부 검사 — 샌드박스 통과).
- calculator·registry를 바꾼 유닛은 `python3 scripts/gen_metric_dictionary.py`로 `v0.3/data/metric_dictionary.md`를 재생성한다. 새 파일이 생긴 유닛은 `python3 scripts/gen_files_index.py`도 실행한다(`check_docs`의 files_index 검사).

## 실DB 시점 (재추출 vs 재동기화)

| 필요 작업 | 이유 | API | 시점 |
|---|---|---|---|
| 스키마 v20 | 새 컬럼·테이블 | 없음 | P7-PRED-11 병합 후 앱 기동 |
| **제자리 재추출** | P7-PRED-12 추출기 수정은 기존 행을 바꾸지 않는다 → 랩 GAP·경과시간·기온·스트림 시간축·활동 `gap`은 재추출해야 채워진다 | 없음(`source_payloads`) | 런북 2단계. **`reprocess_all` 쓰지 말 것**(id 재발급) |
| 외기 기상 백필 | 저장된 payload에 외기 기상 없음(기기 온도만) | Open-Meteo 300~600회 | 런북 3단계 |
| Garmin 참조 이력 | LT·레이스 예측 스냅샷 2개뿐 | Garmin 2회 | 런북 4단계(응답 형태 미확인) |
| 메트릭 재계산 | 새 calculator·의존 변경 | 없음 | 런북 5단계(`recompute --days 1100`, `recompute-all` 금지) |
| 매칭 소급 | session_outcomes 0행 | 없음 | 런북 6단계 |
| 외부 계획 인제스트 | 미수집 | Garmin·Intervals | P7-PRED-44(사람) |

## BACKLOG 등록용 (한 줄 메타 — 그대로 붙여 넣기)

`BACKLOG.md` 반영은 사용자 승인 후. 검증 명령에서 `python3 -m pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`(저장소 `scripts/.venv`에는 pytest가 없다).

- **[P7-PRED-11]** 스키마 v20 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-11 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/db_schema_v20.py", "src/db_setup.py", "src/utils/db_helpers.py", "tests/helpers_pred.py", "tests/test_pred_schema_v20.py", "tests/test_db_setup.py", "tests/test_phase1_schema.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_schema_v20.py tests/test_db_setup.py tests/test_phase1_schema.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-12]** Garmin 추출 보존(랩·스트림·활동 GAP) — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-12 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11"], "kind": "code", "scope": ["src/sync/extractors/garmin_lap_fields.py", "src/sync/extractors/garmin_extractor.py", "tests/test_garmin_lap_fields.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_lap_fields.py tests/test_garmin_extractor.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-13]** 제자리 재추출 + reprocess 파손 수정 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-13 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11", "P7-PRED-12"], "kind": "code", "scope": ["src/sync/reextract.py", "src/sync/reprocess.py", "tests/test_reextract.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_reextract.py tests/test_reprocess.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-14]** CalcContext 러닝 이력 API — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-14 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11"], "kind": "code", "scope": ["src/metrics/context_runs.py", "src/metrics/base.py", "tests/test_context_runs.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_context_runs.py tests/test_activity_calcs.py tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-84]** runpulse_vdot 상한 가드 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-84 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11"], "kind": "code", "scope": ["src/metrics/vdot.py", "tests/test_vdot_guard.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_vdot_guard.py tests/test_activity_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-81]** 시리즈 canonical 집계 + rec 백분위(P7-PRED-82 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-81 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14"], "kind": "code", "scope": ["src/metrics/teroi.py", "src/metrics/rec.py", "src/metrics/tpdi.py", "src/metrics/critical_power.py", "tests/test_rec.py"], "verify": ["python3 -m pytest tests/test_rec.py tests/test_teroi.py tests/test_tpdi.py tests/test_critical_power.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-21]** 세그먼트 분해(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-21 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/segments.py", "tests/test_segments.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_segments.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-22]** 예측·생리 순수 라이브러리 — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-22 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/__init__.py", "src/metrics/prediction/core.py", "src/metrics/prediction/physio.py", "src/metrics/prediction/signals.py", "tests/test_prediction_core.py", "tests/test_prediction_signals.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_core.py tests/test_prediction_signals.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-23]** 분류기 v2 + TIDS — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-23 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-21", "P7-PRED-22"], "kind": "code", "scope": ["src/metrics/classifier.py", "src/metrics/tids.py", "tests/test_activity_calcs.py"], "verify": ["python3 -m pytest tests/test_activity_calcs.py tests/test_phase4_dod.py tests/test_mock_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-24]** HR 프로필(자체·기기, 두 존 체계) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-24 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-22"], "kind": "code", "scope": ["src/metrics/hr_profile.py", "tests/test_hr_profile.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_hr_profile.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-25]** Garmin 참조값(LTHR·레이스 예측) 동기화 — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-25 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11"], "kind": "code", "scope": ["src/sync/garmin_ref_parsers.py", "src/sync/garmin_ref_sync.py", "src/sync/garmin_daily_extensions.py", "tests/test_garmin_ref_parsers.py", "tests/test_garmin_ref_sync.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_ref_parsers.py tests/test_garmin_ref_sync.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-31]** Open-Meteo 클라이언트 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-31 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-22"], "kind": "code", "scope": ["src/weather/openmeteo.py", "tests/test_openmeteo.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_openmeteo.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-32]** 활동 외기 기상 인제스트 + 우선순위 + sync 훅 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-32 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11", "P7-PRED-31"], "kind": "code", "scope": ["src/weather/activity_weather.py", "src/utils/metric_priority.py", "src/sync.py", "tests/test_weather_ingest.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_openmeteo.py tests/test_weather_ingest.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-33]** 개인 기온 모델 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-33 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-22", "P7-PRED-32"], "kind": "code", "scope": ["src/metrics/heat_model.py", "tests/test_heat_model.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_heat_model.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-83]** sapi 외기 기온 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-83 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-32"], "kind": "code", "scope": ["src/metrics/sapi.py", "tests/test_sapi.py"], "verify": ["python3 -m pytest tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-41]** 훈련 반응(세그먼트 단위) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-41 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-22", "P7-PRED-24", "P7-PRED-33"], "kind": "code", "scope": ["src/metrics/prediction/response.py", "src/metrics/training_response.py", "tests/test_training_response.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_training_response.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-42]** 계획 구조 형식 + 세그먼트 비교(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-42 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11", "P7-PRED-21"], "kind": "code", "scope": ["src/training/outcome_v2.py", "tests/test_outcome_v2.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-43]** 매처 세그먼트 이행 저장 — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-43 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11", "P7-PRED-23", "P7-PRED-42"], "kind": "code", "scope": ["src/training/outcome_store.py", "src/training/matcher.py", "tests/test_outcome_store.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_store.py tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-51]** DARP v2 (b)(c) — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-51 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-14", "P7-PRED-22", "P7-PRED-24", "P7-PRED-25", "P7-PRED-33"], "kind": "code", "scope": ["src/metrics/darp.py", "tests/test_darp_v2.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "tests/test_metric_naming.py", "tests/test_validator.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_darp_v2.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py tests/test_dashboard_service.py tests/test_ai_context.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-52]** 일별 VDOT 의존 메트릭 복구 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-52 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-51"], "kind": "code", "scope": ["src/metrics/marathon_shape.py", "src/metrics/rri.py", "src/metrics/eftp.py", "src/metrics/vdot_adj.py", "tests/test_marathon_shape.py", "tests/test_rri.py", "tests/test_eftp.py", "tests/test_vdot_adj.py"], "verify": ["python3 -m pytest tests/test_marathon_shape.py tests/test_rri.py tests/test_eftp.py tests/test_vdot_adj.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-53]** 대회 확인 서비스 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-53 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-11"], "kind": "code", "scope": ["src/services/race_result_service.py", "tests/test_race_result_service.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_race_result_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-62]** 수용 백테스트 스크립트 — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-*.md`의 P7-PRED-62 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-24", "P7-PRED-33", "P7-PRED-51"], "kind": "code", "scope": ["scripts/pred_backtest.py", "tests/test_pred_backtest.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_backtest.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-61]** 실DB 백필 런북 — 사람 전용(`PRED-6x-*.md`의 P7-PRED-61 절).
- **[P7-PRED-71]** 비교·근거·대회 확인 API — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-71 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-25", "P7-PRED-51", "P7-PRED-53"], "kind": "code", "scope": ["src/services/prediction_compare_service.py", "src/api/routes_prediction.py", "src/api/__init__.py", "src/services/race_hub_service.py", "tests/test_prediction_compare.py", "tests/test_api_prediction.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_compare.py tests/test_api_prediction.py tests/test_api_today.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-72]** 레이스 허브 범위·신뢰도·3경로 비교·근거·대회 확인 UI(73·74 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-72 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-PRED-71"], "kind": "code", "scope": ["frontend/src/lib/predictionCompare.ts", "frontend/tests/predictionCompare.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/prediction.ts", "frontend/src/lib/components/PredictionCompare.svelte", "frontend/src/lib/components/PredictionBasis.svelte", "frontend/src/lib/components/RaceConfirmList.svelte", "frontend/src/lib/components/RaceHub.svelte", "frontend/src/lib/format.ts"], "verify": ["cd frontend && npm run check", "cd frontend && node --test tests/predictionCompare.test.mjs tests/raceHub.test.mjs tests/format.test.mjs", "cd frontend && npm run build"]} -->
- **[P7-PRED-44]** 외부 계획 인제스트(Garmin·Intervals) — 사람 전용(`PRED-4x-*.md`의 P7-PRED-44 절).
