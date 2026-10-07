# RunPulse 파일 인덱스

> 자동 생성 (`python3 scripts/gen_files_index.py`) — 수동 편집 금지
> 디렉토리 설명 변경: 해당 `__init__.py` docstring 수정 후 재생성
> 파일 설명 변경: 해당 `.py` 모듈 docstring 수정 후 재생성

## `src/services/`

> 서비스 레이어 — Phase 5(읽기 전용 3개) + Phase 7 D5 확장(today/coach 추가, 3개는 스텁).
> 
> DB에서 데이터를 읽어 가공된 dict를 반환한다. 원칙은 읽기 전용이지만, Today의
> save_checkin()과 Coach의 스레드/메시지 저장은 명시적 예외다(07-migration-roadmap.md
> Phase 7a). 첫 번째 인자는 항상 sqlite3.Connection. 반환값은 dict (snake_case 키).
> 단위 변환 하지 않음 — SI 그대로 반환.
> 
> 파일: activity_service·dashboard_service·wellness_service(Phase 5, 구현 완료) /
> today_service·coach_service(Phase 7a, 구현 완료) / metrics_service·plan_service·
> data_service(Phase 7b~7d 스텁). story_service는 없음 — Story는 Today L2로 흡수됨
> (REVIEW-03, 00-diagnostic-and-direction.md §5.1).
> 
> 설계 문서: v0.3/data/phase-5-impl/01-service-layer.md,
> v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D5)
> 의존: src/utils/db_helpers.py, src/utils/metric_registry.py, src/ai/chat_engine.py(Coach)
> 주의: metric_store 조회 시 is_primary=1 필터 필수. CalcContext는 사용하지 않는다
> (ADR-009는 Calculator 전용, 서비스 레이어와 다른 레이어).

### `_narrative.py` (209줄) — 내러티브 생성 헬퍼 — today_service.get_today_narrative() 전용.

- functions: month_date_range, peak_ctl_in_range, query_metric, sleep_trend, build_evidence, build_narrative_prompt, attach_drill, get_narrative_cache, set_narrative_cache, rule_narrative

### `activity_detail_service.py` (225줄) — Phase 5 서비스 레이어 - 활동 상세 조회.

- functions: get_activity_detail

### `activity_feedback_service.py` (106줄) — 활동별 주관 입력(RPE·통증·메모) 저장 서비스 — activity_feedback(ADR-022).

- class **FeedbackError**: 없음
- functions: validate, get_feedback, put_feedback, delete_feedback, feedback_for_activities

### `activity_gpx.py` (67줄) — 단일 활동 GPX 1.1 생성 — activity_streams 의 위치 점이 가장 많은 그룹 구성원을 사용(ADR-022). DB 쓰기 없음.

- class **NoGpsError**: 없음
- functions: build_gpx

### `activity_impact_service.py` (137줄) — 활동 상세 임팩트 — CTL Δ·유사 활동 비교·레이스 맥락.

- functions: get_activity_impact

### `activity_list_filters.py` (91줄) — 활동 목록 필터·정렬 SQL 조립 (UX 리뷰 20 §7-2 ④, B-3 공용).

- functions: parse_args, sport_types, build_where, order_clause

### `activity_list_rows.py` (62줄) — 활동 목록 행 부가 필드 — workout_class·display_title·load·is_race (UX 리뷰 20 §7-2 ④).

- functions: is_generic_name, display_title, enrich_rows

### `activity_list_summary.py` (124줄) — 활동 목록 facets·주간 요약 (UX 리뷰 20 §7-2 ⑤, B-3).

- functions: get_facets, get_summary

### `activity_service.py` (173줄) — Phase 5 서비스 레이어 - 활동 데이터 조회.

- functions: get_activity_list, get_activity_streams, get_activity_streams_meta, get_activity_trend

### `activity_similar.py` (95줄) — 활동 상세 '비슷한 활동' 비교 — 같은 코스 → 같은 유형 → 비슷한 거리 순으로 기준을 고른다.

- functions: find_similar

### `activity_source_links.py` (29줄) — 활동의 원본 서비스 페이지 링크 — 그룹 구성원마다 (source, source_id)로 URL 구성. 외부 호출 없음(ADR-022).

- functions: source_links

### `activity_splits.py` (155줄) — 활동 상세 S1 — km 스플릿·요약 시계열(series) 서버 계산.

- functions: cumulative_distance, stopped_flags, compute_splits, series_step_m, build_series

### `activity_summary_extras.py` (132줄) — 활동 상세 S1 부가 필드 — workout_class·environment·hr_zones·source_diffs·verdict.

- functions: pace_cv, build_workout_class, build_environment, build_hr_zones, build_source_diffs, build_verdict

### `adaptation_service.py` (70줄) — 플랜 적응 상태 서비스 — 03e-coach.md 5-F "적응 상태"(ACWR·HRV·주간 피로도). 읽기 전용.

- functions: get_adaptation_status

### `archive_service.py` (121줄) — 러닝 아카이브 — 누적 통계·월별 거리·365일 히트맵·개인 최고 기록(읽기 전용).

- functions: get_archive

### `coach_activity_context.py` (96줄) — Coach 활동 컨텍스트 — `/coach/new?activity={id}` 근거 카드·추천 질문·프롬프트 요약.

- functions: suggested_questions, get_activity_context, activity_prompt_summary

### `coach_async.py` (229줄) — Coach 비동기 답변 실행기 — 워커 스레드·메시지별 이벤트 로그·취소 플래그·SSE 직렬화 (design §6.2, §7.1).

- class **_Run**: emit, finish
- functions: source_text, replay_events, start, cancel, sse, stream

### `coach_consent.py` (41줄) — Coach LLM 전송 동의 저장소 — coach_consent 단일 행(30-coach-chat design §4.3).

- functions: get_consent, save_consent

### `coach_engine_health.py` (130줄) — Coach 엔진 상태 — 메시지별 엔진 라벨, 최근 20개 집계(H0 배너), GET /coach/engine 페이로드.

- functions: model_label, reason_label, engine_label, parse_engine, message_engine_view, health_summary, get_engine

### `coach_evidence.py` (217줄) — Coach 답변 근거 v2 (30-coach-chat design §4.4·§7.3) — "이 답변이 실제로 쓴 입력"만 칩으로 남긴다.

- functions: is_drifted, with_current, build_answer_evidence, view_evidence

### `coach_service.py` (300줄) — Phase 7 서비스 레이어 - Coach 스레드 CRUD + AI 호출 래핑.

- functions: list_threads, get_thread, create_thread, add_message, generate_reply, get_message, regenerate

### `dashboard_service.py` (214줄) — Phase 5 서비스 레이어 - 대시보드 데이터 조회.

- functions: get_dashboard_data, get_pmc_chart_data, get_daily_metric_chart

### `data_health_service.py` (32줄) — 데이터 건강 — 부하(TRIMP) 커버리지 등, 지표를 믿어도 되는지 알려주는 읽기 전용 진단.

- functions: get_load_coverage

### `data_service.py` (7줄) — Phase 7d 서비스 레이어 - 데이터 소스 연결 상태·동기화 트리거 (스텁).

- (public API 없음)

### `metric_browse_groups.py` (101줄) — 메트릭 브라우저 표시 분류·정렬 — 8의도 그룹 slug 매핑 + 당일 주목도(salience) 정렬.

- functions: classify, baseline_z, salience_key

### `metric_display.py` (56줄) — 메트릭 표시 메타 — API가 내려주는 format·decimal_places·higher_is_better (21 design §7.2).

- functions: display_name, action_hint, min_span, display_meta

### `metrics_basis_events.py` (68줄) — 예측 추세의 기준 대회 교체 이벤트(◇) — race_pred_vdot json 의 anchor.activity_id 가 전날과 달라진 첫 날.

- functions: load_json, basis_change_events

### `metrics_browser_service.py` (298줄) — 메트릭 브라우저·추세 서비스 — 3-E/3-F (daily-scope 전용).

- functions: confidence_label, get_metrics_browser, get_metric_trend

### `metrics_explain.py` (242줄) — Phase 7 UX 리뷰 2-5 — 메트릭 분해 v2(`explain=1`, §C3.2).

- functions: personal_text, get_metric_explain

### `metrics_explain_activity.py` (68줄) — 분해 v2 활동 scope(`@a{id}`, DESIGN-PENDING-12 §3) — 활동 단위 지표 explainer.

- functions: explain_trimp_activity

### `metrics_explain_composite.py` (140줄) — 분해 v2 — 합성형(UTRS·CIRS) + 곱셈형(RRI) explainer.

- functions: explain_utrs, explain_cirs, explain_rri

### `metrics_explain_conclusion.py` (32줄) — 분해 v2 결론 한 줄(`conclusion{top_loss,text}`, 21 §7.2(c)) — UTRS·CIRS·RRI만.

- functions: build_conclusion

### `metrics_explain_prediction.py` (52줄) — 레이스 예측(race_pred_*_sec) 분해 v2 — 신호별 환산 기록·가중치·범위·신뢰 제한 요인을 evidence로 제공.

- functions: explain_prediction

### `metrics_explain_shared.py` (44줄) — 분해 v2(`metrics_explain.py`/`metrics_explain_composite.py`) 공유 헬퍼.

- functions: daily_trimp_sum, top_activity_sources

### `metrics_explain_whatif.py` (66줄) — 분해 v2 what-if(B-5) — "오늘 쉬면 내일 아침 값" 추정. 순수 함수 + 얇은 조립.

- functions: tomorrow_tsb_if_rest, utrs_with_tsb, build_what_if

### `metrics_service.py` (88줄) — Phase 7b 서비스 레이어 - 메트릭 계산 분해 트리.

- functions: get_metric_breakdown

### `metrics_version_events.py` (60줄) — 추세 차트의 계산 버전 마커(◆) — 대표 시계열에서 (provider, algorithm_version)이 바뀐 첫 날 + 전 기간 재계산 캡션.

- functions: version_change_events, recompute_note

### `milestone_present.py` (51줄) — 마일스톤 표시용 가공(순수) — 갱신(같은 알고리즘 안의 값 변화) 항목의 내부 메트릭 키를 사람이 읽는 이름으로 바꾸고, 같은 날 예측 갱신은 한 줄로 묶는다.

- functions: present_milestones

### `milestone_service.py` (266줄) — Phase 7b 마일스톤 탐지 + 저장 서비스 (03a-today.md 1-D).

- functions: detect_and_store_milestones, get_recent_milestones

### `narrative_warm.py` (82줄) — 이번 달 Today 내러티브 사전 생성(워밍) — 동기화 직후 AI 문장을 캐시에 미리 채운다 (DESIGN-U17 §3).

- functions: warm_month_narrative, warm_in_background

### `plan_service.py` (214줄) — Phase 7b 서비스 레이어 - 훈련 플랜 조회 (진행 중 플랜 + 오늘 조정).

- functions: get_active_plan, get_todays_adjustment, get_session_detail, get_session_note, save_session_note

### `plan_template_service.py` (193줄) — Phase 7b — 플랜 템플릿 조회 + 새 플랜 생성 서비스.

- functions: get_static_plan_templates, create_plan_from_template

### `prediction_compare_service.py` (88줄) — 레이스 예측 3경로 비교(P7-PRED-71) — (a) Garmin 예측, (b) RunPulse·기기 심박 기준, (c) RunPulse·자체 추정(기본, r3)

- functions: compare, profile

### `prediction_snapshot_service.py` (115줄) — 예측 스냅샷·전향 평가(P7-PRED-63) — 모델별(r3 기본·기기·r4 섀도·Garmin) 예측을 그날 값 그대로 보존하고,

- functions: record_snapshots, evaluate_race, summary

### `progression_service.py` (25줄) — 품질 세션 사다리 단계 저장·갱신 서비스(U16l) — progression.py 순수 함수와 plan_progression 테이블을 잇는다.

- functions: get_step, advance

### `provider_comparison_service.py` (296줄) — Provider 비교 서비스 — 활동 그룹 내 소스별 메트릭 비교 (3-G-2).

- functions: get_provider_comparison

### `provider_diff.py` (50줄) — 소스 비교 차이 판정 — 항목별 임계·정규화(UX 리뷰 20 design §7-2 ③, F-DATA-03).

- functions: normalize, diff, legacy_discrepancy

### `provider_matrix_collect.py` (202줄) — Provider 매트릭스 수집·통계 헬퍼 (S6, ADR-021).

- functions: plabel, quantile, median, iqr_bounds, running_groups, collect_activity_values, collect_daily_values, cell_summary, pair_points, summarize_pairs, severity_key, provider_pair_order

### `provider_matrix_service.py` (97줄) — 소스 비교 매트릭스 서비스 (S6, ADR-021) — 같은 러닝을 소스별로 어떻게 계산하는지 한눈에.

- functions: window, diffs_for, representative, get_matrix

### `provider_pairs_service.py` (43줄) — 소스 비교 쌍 목록 서비스 (S6, ADR-021) — 한 행의 같은 러닝(또는 같은 날) 값 쌍과 이상치.

- functions: get_pairs

### `provider_status_service.py` (83줄) — Provider별 데이터 현황 조회 서비스 (읽기 전용).

- functions: get_provider_status, get_provider_coverage

### `race_hub_service.py` (181줄) — Today 목표 레이스 허브 — 활성 목표 + D-day + 예측 기록·목표 격차·예측 추이.

- functions: bucket_for_distance, get_race_hub, form_band, race_briefing

### `race_projection_service.py` (100줄) — 레이스 아침 폼 예측 — 현재 CTL/ATL에서 테이퍼 유무 두 시나리오로 TSB를 전방 투영한다.

- functions: project_race_form

### `race_result_service.py` (64줄) — 대회 확인(race_results, P7-PRED-53) — 사용자가 대회 여부·전력 여부·공식 기록을 확정한다.

- functions: confirm, remove, get, candidates

### `sync_state_service.py` (175줄) — 동기화 상태 계약(SyncState) — 40-v2-unimplemented design §7.3 `GET /api/v1/data/sync-state`.

- functions: classify_error, get_sync_state

### `sync_trigger_service.py` (151줄) — 수동 증분 동기화 트리거 — 소스별 판정(plan)과 bg_sync 시작(trigger). v1/v2 공용.

- class **SkipReason**: to_dict
- class **TriggerResult**: 없음
- functions: days_since_last_sync, plan_incremental, trigger_incremental

### `today_hero.py` (199줄) — Today 히어로·주간 스트립 데이터 — briefing.state 판정, 세션·조정·결손 caveat, week_compliance.

- functions: race_days_left, build_week, build_briefing_state, build_race_summary, build_today_extras

### `today_readiness.py` (47줄) — Today 게이지 데이터 — UTRS/CIRS/TSB의 값·전일 대비·서버 등급(status/status_label)·provider.

- functions: build_readiness

### `today_service.py` (300줄) — Phase 7 서비스 레이어 - Today(관여 계층 L0~L2) 데이터 조회 + 체크인 저장.

- functions: get_today_status, get_recent_activities, get_today_briefing, get_todays_checkin, get_today_milestones, get_today_narrative, save_checkin

### `unified_activities.py` (17줄) — 하위호환 re-export 심 — 직접 import는 각 모듈을 사용할 것.

- (public API 없음)

### `unified_view.py` (360줄) — 멀티 소스 활동 통합 뷰 — UnifiedActivity 빌드 + 페이지 조회.

- class **UnifiedField**: 없음
- class **UnifiedActivity**: date, can_expand
- functions: build_unified_activity, fetch_unified_activities, build_source_comparison

### `user_settings_service.py` (42줄) — 사용자 UI 설정 key-value 저장소(user_settings, ADR-023) — 화이트리스트 키만 허용.

- functions: get_setting, set_setting, global_ui_default, resolve_ui_default

### `week_digest.py` (109줄) — 주간 다이제스트 — 월간 내러티브의 주(週) 단위 근거 (DESIGN-U17 U17g).

- functions: week_start_of, weeks_overlapping, week_digest, week_digests, digest_prompt_lines

### `weekly_adapt_service.py` (57줄) — 주간 적응 서비스 — 지난주 이행도·CRS·ACWR를 읽어 weekly_adapt 규칙으로 이번 주 계획 행을 조정한다(v2 목표만).

- functions: load_input, adapt_plan

### `wellness_day.py` (202줄) — 웰니스 /:date 일 상세 — 헤드라인·근거·준비도·수면·Body Battery·기준선·7일 점·이전/다음 날짜.

- functions: percentile_band, build_day

### `wellness_service.py` (148줄) — Phase 5 서비스 레이어 - 웰니스 데이터 조회.

- functions: get_wellness_detail, get_wellness_trend

## `src/metrics/`

> Phase 4 메트릭 엔진.
> 
> CalcContext API로 데이터를 읽고 metric_store에 결과를 쓴다.
> 모든 calculator는 MetricCalculator를 상속. 의존성은 produces/depends로 선언.
> 데이터 부족 시 None 반환. confidence로 신뢰도 표시.
> 
> 설계 문서: v0.3/data/phase-4.md
> 의존: src/utils/db_helpers.py, src/utils/metric_registry.py, src/utils/metric_groups.py
> 주의: category는 calculator의 self.category가 DB 저장값 (registry 아님)

### `acwr.py` (54줄) — ACWR Calculator — 설계서 4-3 기준. P7-PRED-89: 만성 부하가 형성되기 전(CTL < 10 또는 28일 전 CTL 없음)엔

- class **ACWRCalculator**: compute
- functions: has_history

### `adti.py` (47줄) — ADTI (Adaptive Training Trend Index) — 설계서 4-4 기준.

- class **ADTICalculator**: compute

### `bands.py` (94줄) — 메트릭 등급 밴드 SSOT — 값 → (status, 한국어 라벨).

- functions: grade, band_ranges, with_grade

### `base.py` (557줄) — MetricCalculator 기본 클래스 + CalcContext + CalcResult.

- class **CalcResult**: is_empty
- class **MetricCalculator**: compute
- class **CalcContext**: activity, get_metric, get_metric_json, get_metric_text, get_daily_metric_series, get_activities_in_range, get_activity_metric, get_activity_metric_text, get_streams, get_group_metric, get_stream_meta, get_group_streams, get_laps, get_wellness, get_athlete_sex, get_daily_load, get_activity_metric_series, get_wellness_series, update_metric_cache
- class **ConfidenceBuilder**: add_input, compute
- functions: load_group_streams

### `cirs.py` (124줄) — CIRS (Composite Injury Risk Score) — 설계서 4-4 기준.

- class **CIRSCalculator**: compute

### `classifier.py` (108줄) — Workout Classifier v2 — 세그먼트(랩 구조) 기반 세션 유형 판정(REVIEW-07 r4, REVIEW-09 §3, P7-PRED-23).

- class **WorkoutClassifier**: compute

### `cli.py` (132줄) — Metrics CLI 인터페이스 (보강 #10).

- functions: show_metric_status, main

### `context_runs.py` (152줄) — CalcContext 러닝 이력 API(RunHistoryMixin) — canonical 러닝 + 트윈 HR 병합 + 랩(경사보정 속도) + 대회 판정.

- class **RunHistoryMixin**: get_runs, get_activity_metric_json, get_active_goal, get_latest_daily_metric, get_best_efforts, get_race_results
- functions: nominal_distance, lap_block

### `critical_power.py` (98줄) — CP/W' (Critical Power / W Prime) — 임계 파워 및 무산소 용량.

- class **CriticalPowerCalculator**: compute

### `crs.py` (206줄) — CRS (Composite Readiness Score) — 복합 훈련 준비도 평가.

- class **CRSCalculator**: compute

### `darp.py` (140줄) — DARP v2 레이스 예측 — 앵커 대회(15℃ 정규화·감쇠) + 작업 블록 + HR@LTHR 결합, 개인 내구성 지수, 마라톤 Daniels·Tanda.

- class **DARPCalculator**: hr_refs, compute
- class **DARPRefCalculator**: hr_refs, compute
- functions: sg_pairs

### `darp_r4.py` (180줄) — DARP r4 섀도 예측 — 전력 대회·품질 세트(Daniels 등가 강도)·심박-속도 H 를 칼만 필터로 정밀도 가중 결합.

- class **DARPShadowCalculator**: ctl_at, hr_refs, compute
- class **DARPShadowAsymCalculator**: ctl_at

### `decoupling.py` (77줄) — Aerobic Decoupling Calculator — 설계서 4-2 기준.

- class **AerobicDecouplingCalculator**: compute

### `di.py` (71줄) — DI (Durability Index) v2 — 90분 이상 러닝에서 후반 효율 유지율(P7-PRED-89).

- class **DICalculator**: compute

### `display_rules.py` (24줄) — 활동 메트릭 표시 규칙 — UX 리뷰 20 design §4-5 (계산은 그대로 두고 화면에 낼지만 정한다).

- functions: visible_activity_metrics

### `efficiency.py` (35줄) — Efficiency Factor Calculator — 설계서 4-2 기준.

- class **EfficiencyFactorCalculator**: compute

### `eftp.py` (103줄) — eFTP (Estimated Functional Threshold Pace) — 기능적 역치 페이스 추정.

- class **EFTPCalculator**: compute

### `engine.py` (799줄) — Metrics Engine — topological sort 기반 실행. 설계서 4-5 + 보강 #1,#2,#11 기준.

- class **ComputeResult**: summary
- functions: prune_noncanonical_runpulse, run_activity_metrics, run_daily_metrics, run_for_date, compute_for_activities, compute_for_dates, recompute_single_metric, run_for_date_range, recompute_recent, clear_runpulse_metrics, recompute_all, find_missing_load_dates, backfill_missing_loads

### `fearp.py` (76줄) — FEARP (Fitness & Environment Adjusted Running Pace) v2 — 외기 기온·이슬점·고도로 보정한 환경 보정 페이스(P7-PRED-90).

- class **FEARPCalculator**: compute
- functions: heat_penalty

### `gap.py` (86줄) — GAP (Grade Adjusted Pace) Calculator — Minetti (2002) 에너지 비용 모델.

- class **GAPCalculator**: compute
- functions: effort_factor, stream_grades

### `heat_model.py` (70줄) — 개인 기온 영향 모델(일별) — 정상 주행 랩의 HR·속도·외기 기온 회귀로 더위/추위 계수(%/℃)를 추정해 기본값으로 수축(P7-PRED-33).

- class **HeatModelCalculator**: compute
- functions: ols, fit_heat

### `hr_profile.py` (97줄) — HR 프로필(일별) — RunPulse 자체 추정(HRmax·LTHR·RHR)과 소스 참조값(Garmin 등)을 나란히 산출(P7-PRED-24).

- class **HRProfileCalculator**: compute
- functions: race_second_part_hr

### `hrss.py` (56줄) — HRSS Calculator — 설계서 4-2 기준.

- class **HRSSCalculator**: compute

### `lsi.py` (57줄) — LSI (Load Spike Index) Calculator — 설계서 4-3 기준.

- class **LSICalculator**: compute

### `marathon_shape.py` (80줄) — Marathon Shape v2 — 마라톤 볼륨·롱런 구조(P7-PRED-52, REVIEW-09 §7). 기기 불필요(GPS·시간).

- class **MarathonShapeCalculator**: compute
- functions: tanda_required_km

### `monotony.py` (61줄) — Monotony & Strain Calculator — 설계서 4-3 기준.

- class **MonotonyStrainCalculator**: compute

### `pmc.py` (99줄) — PMC (ATL/CTL/TSB/Ramp Rate) Calculator — 설계서 4-3 기준.

- class **PMCCalculator**: compute
- functions: elapsed_day_fraction, ewma_loads, get_daily_loads

### `rec.py` (54줄) — REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.

- class **RECCalculator**: compute

### `relative_effort.py` (90줄) — Relative Effort (Strava 방식) — 심박존 기반 노력도 점수.

- class **RelativeEffortCalculator**: compute

### `reprocess.py` (87줄) — Reprocess — Raw payload에서 Layer 1/2 재구축. 설계서 4-7 기준.

- functions: reprocess_from_payloads

### `rmr.py` (66줄) — RMR (Recovery & Metabolic Readiness) — 설계서 4-4 기준.

- class **RMRCalculator**: compute

### `rri.py` (74줄) — RRI (Race Readiness Index) — 레이스 준비도 종합 지수.

- class **RRICalculator**: compute

### `rtti.py` (78줄) — RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

- class **RTTICalculator**: compute

### `sapi.py` (104줄) — SAPI (Seasonal-Adjusted Performance Index) — 계절·날씨 성과 비교.

- class **SAPICalculator**: compute

### `segments.py` (220줄) — 세그먼트 분해 — 랩/스트림 블록을 워밍업·작업·휴식·쿨다운으로 나누고 세트·세션 유형을 판정한다(순수 함수).

- functions: label_blocks, build_bouts, work_set, session_type, set_summary, stream_to_blocks, repair_time_axis, cumulative_distance

### `stream_meta_access.py` (28줄) — 스트림 시간축 meta 조회(U18c) — CalcContext.get_stream_meta 의 구현. meta 테이블이 없거나 행이 없으면 None.

- functions: load_stream_meta, is_trusted

### `stream_utils.py` (54줄) — 스트림·심박 공용 헬퍼 — 정지 제외 이동 샘플, 선수 최대심박.

- functions: sample_times, moving_segments, athlete_max_hr

### `teroi.py` (65줄) — TEROI (Training Effect Return On Investment) — 훈련 효과 투자 수익률.

- class **TEROICalculator**: compute

### `tids.py` (75줄) — TIDS (Training Intensity Distribution Score) — 8주 러닝 시간의 3구간 분포(P7-PRED-88, REVIEW-08 §R4).

- class **TIDSCalculator**: compute
- functions: distribution, pattern

### `today_refresh.py` (40줄) — 달력 오늘의 일별 메트릭을 "현 시각 기준"으로 유지하는 지연 갱신.

- functions: refresh_today_if_stale

### `tpdi.py` (64줄) — TPDI (Trainer Physical Disparity Index) — 실내/실외 FEARP 격차 지수.

- class **TPDICalculator**: compute

### `training_response.py` (36줄) — 훈련 반응(일별) — 품질 세트 구간별 주간 시간·품질 세션 수·롱런 MP 거리·세트 VDOT 추세(P7-PRED-41, r4).

- class **TrainingResponseCalculator**: compute

### `trimp.py` (83줄) — TRIMP Calculator — 설계서 4-2 기준.

- class **TRIMPCalculator**: compute

### `trimp_est.py` (101줄) — TRIMP 추정 Calculator — 심박 결측 활동의 부하를 페이스로 추정(DATA-CTL-WARMUP).

- class **TRIMPEstCalculator**: compute
- functions: fit_hr_from_speed

### `utrs.py` (114줄) — UTRS (Unified Training Readiness Score) — 설계서 4-4 기준.

- class **UTRSCalculator**: compute, tsb_component

### `vdot.py` (69줄) — VDOT Calculator — 설계서 4-2 기준.

- class **VDOTCalculator**: compute

### `wlei.py` (80줄) — WLEI (Weather-Loaded Effort Index) — 날씨 가중 노력 지수.

- class **WLEICalculator**: compute

### `workout_classifier.py` (38줄) — 운동 유형 분류 상수 — TAG_COLORS, TAG_LABELS, _EFFECTS.

- (public API 없음)

## `src/sync/`

> Phase 3 동기화 오케스트레이터.
> 
> API 호출 → raw 저장 → 추출 → DB 적재.
> 비즈니스 로직은 extractor에, sync는 배관(plumbing)만 담당.
> RateLimiter로 소스별 속도 제한. SyncResult로 결과 집계.
> 
> 진입점: orchestrator.full_sync()
> 개별 소스: garmin_activity_sync.sync(), strava_activity_sync.sync() 등.
> 
> 설계 문서: v0.3/data/phase-3.md
> 의존: src/sync/extractors/, src/utils/db_helpers.py, src/utils/rate_limiter.py
> 주의: Garmin은 rate-limit 감지 후 동적 대기 필요

### `_helpers.py` (129줄) — Orchestrator 내부 어댑터 — Extractor 출력을 db_helpers 인터페이스에 연결.

- functions: sanitize_activity_core, save_activity_core, save_metrics, save_laps, save_streams, save_best_efforts, save_daily_wellness, save_daily_fitness, resolve_primaries

### `dedup.py` (119줄) — 활동 중복 감지 — 7분 / 15% 규칙.

- functions: run

### `garmin.py` (245줄) — Garmin Connect 데이터 동기화 — 메인 진입점.

- functions: sync_activities, sync_wellness, sync_daily_extensions, sync_athlete_extensions, sync_garmin

### `garmin_activity_sync.py` (286줄) — Garmin 활동 동기화 Orchestrator.

- class **_RateLimitStop**: 없음
- functions: sync

### `garmin_api_extensions.py` (145줄) — Garmin 활동 확장 API — gear, exercise_sets.

- functions: sync_activity_gear, sync_activity_exercise_sets

### `garmin_athlete_extensions.py` (176줄) — Garmin 선수 프로필/통계/기록 동기화 — athlete_profile, athlete_stats,

- functions: sync_athlete_profile, sync_athlete_stats, sync_athlete_personal_records

### `garmin_auth.py` (184줄) — Garmin Connect 인증 — garminconnect 0.3.x 네이티브 DI OAuth.

- class **GarminAuthRequired**: 없음
- functions: check_garmin_connection

### `garmin_backfill.py` (233줄) — Garmin ZIP export → activity_summaries backfill (v2)

- functions: backfill_from_zip

### `garmin_bulk_loader.py` (250줄) — Garmin Bulk Export ZIP 로더.

- class **GarminBulkLoader**: load

### `garmin_daily_extensions.py` (428줄) — Garmin 일별 확장 API — race_predictions, training_status, fitness_metrics,

- functions: sync_daily_race_predictions, sync_daily_training_status, sync_daily_fitness_metrics, sync_daily_user_summary, sync_daily_all_day_stress, sync_daily_body_battery_events, sync_daily_heart_rates, sync_daily_hydration, sync_daily_weigh_ins, sync_daily_running_tolerance

### `garmin_helpers.py` (104줄) — Garmin 동기화 공통 헬퍼.

- (public API 없음)

### `garmin_ref_parsers.py` (70줄) — Garmin 참조값 파서(순수) — 젖산역치(LTHR·역치속도·FTP)와 레이스 예측 payload → 날짜별 값(P7-PRED-25).

- functions: parse_lactate_threshold, parse_race_predictions

### `garmin_ref_sync.py` (99줄) — Garmin 참조값 동기화(P7-PRED-25) — 젖산역치(LTHR·역치속도) 일별 스냅샷, 레이스 예측 일별 스냅샷 + 이력 백필.

- functions: sync_lactate_threshold, sync_race_predictions, backfill_history

### `garmin_v2_mappings.py` (283줄) — Garmin → activity_summaries v2.5 필드 매핑 정의.

- functions: extract_summary_fields_from_api, extract_summary_fields_from_zip, extract_detail_fields, build_upsert_sql

### `garmin_wellness_sync.py` (169줄) — Garmin 일별 wellness 동기화 Orchestrator.

- class **_RateLimitStop**: 없음
- functions: sync

### `intervals.py` (82줄) — Intervals.icu 데이터 동기화 (Basic Auth) — 하위 모듈 wrapper.

- functions: sync_activities, sync_wellness, sync_intervals

### `intervals_activity_sync.py` (175줄) — Intervals.icu 활동 + wellness 동기화 Orchestrator.

- functions: sync, sync_wellness

### `intervals_athlete_sync.py` (123줄) — Intervals.icu 선수 프로필 동기화.

- functions: sync_athlete_profile, sync_athlete_stats_snapshot

### `intervals_auth.py` (58줄) — Intervals.icu API 인증 및 연결 상태 확인.

- functions: base_url, auth, check_intervals_connection

### `intervals_wellness_sync.py` (103줄) — Intervals.icu 웰니스 / 피트니스 동기화.

- functions: sync_wellness

### `ledger.py` (58줄) — 동기화 원장 기록 진입점 — sync_jobs.db에 실행 1건(manual·auto·cli)을 남긴다. bg 경로는 bg_sync가 직접 기록.

- functions: start_run, finish_run, fail_run

### `orchestrator.py` (120줄) — 통합 sync 진입점.

- functions: full_sync

### `plan_ingest.py` (244줄) — 외부 계획 인제스트(P7-PRED-44) — Garmin 저장 워크아웃·적응형 계획, Intervals 계획 이벤트 → planned_workouts.

- functions: parse_garmin_workout, parse_garmin_adaptive_task, store_planned, ingest_garmin_executed, ingest_garmin_adaptive, main

### `plan_ingest_intervals.py` (84줄) — Intervals 계획 이벤트 인제스트(P7-PRED-44) — planned_workouts 저장, paired_activity_id 로 실행 활동 연결.

- functions: parse_intervals_event, ingest_intervals_events

### `rate_limiter.py` (137줄) — 소스별 API Rate-Limit 관리.

- class **RateLimitPolicy**: 없음
- class **RateLimiter**: pre_request, post_request, handle_rate_limit, call_count, should_stop

### `raw_store.py` (46줄) — Raw payload 저장 — db_helpers.upsert_payload()의 Sync-friendly 래퍼.

- functions: upsert_raw_payload, update_raw_activity_id

### `reextract.py` (77줄) — 제자리 재추출 — 기존 activity_summaries id 를 유지한 채 source_payloads 에서 랩·스트림·활동 메트릭을 다시 뽑는다(P7-PRED-13).

- functions: orphan_activity_count, reextract_laps_streams

### `reprocess.py` (298줄) — Raw payload(Layer 0)에서 Layer 1/2 재구축.

- functions: reprocess_all

### `runalyze.py` (261줄) — Runalyze 데이터 동기화 (API Token).

- functions: sync_activities, check_runalyze_connection

### `runalyze_activity_sync.py` (88줄) — Runalyze 활동 동기화 Orchestrator.

- functions: sync

### `strava.py` (85줄) — Strava 데이터 동기화 (OAuth2) — 하위 모듈 wrapper.

- functions: sync_activities, sync_strava

### `strava_activity_sync.py` (185줄) — Strava 활동 동기화 Orchestrator.

- functions: sync

### `strava_athlete_sync.py` (186줄) — Strava 선수 프로필, 통계, 기어 동기화.

- functions: sync_athlete_profile, sync_athlete_stats, sync_gear, sync_athlete_and_gear

### `strava_auth.py` (91줄) — Strava OAuth2 토큰 관리 및 연결 상태 확인.

- functions: refresh_token, check_strava_connection

### `stream_meta_backfill.py` (31줄) — 스트림 meta 백필(U18e) — Garmin 은 payload 재추출로 meta 생성, 나머지는 기존 행 기준으로 meta 기록(없으면 unknown).

- functions: backfill_stream_meta

### `stream_meta_store.py` (70줄) — 스트림 저장 + 시간축 meta 기록(U18b) — scaled 환산, stored_count(동일 초 중복 탈락 반영), UPSERT.

- functions: summary_total_sec, save_stream_meta, store_streams

### `sync_errors.py` (71줄) — 동기화 오류 분류 — 예외/결과를 error_code로 정규화하고 한국어 안내 문구를 제공한다.

- class **SyncSourceError**: 없음
- functions: classify_exception, from_result

### `sync_result.py` (72줄) — Sync 작업 결과 데이터 구조.

- class **SyncResult**: is_rate_limited, merge, to_sync_job_dict

## `src/sync/extractors/`

> RunPulse v0.3 Extractor 모듈.
> 
> 각 소스(Garmin, Strava, Intervals, Runalyze)의 raw JSON을
> DB에 독립적인 dict/list로 변환하는 순수 함수 모듈입니다.
> 
> 설계 문서: v0.3/data/phase-2.md
> 의존: src/utils/metric_registry.py
> 주의: 순수 함수 — DB/API 접근 금지.
>       거리는 meters, 시간은 seconds (SI).
>       activity_summaries에 있는 값은 metric_store에 중복 저장 금지.

### `base.py` (139줄) — Extractor 공통 인터페이스 및 MetricRecord 데이터 구조.

- class **MetricRecord**: is_empty
- class **BaseExtractor**: extract_activity_core, extract_activity_metrics, extract_activity_laps, extract_activity_streams, extract_best_efforts, extract_wellness_core, extract_wellness_metrics, extract_fitness

### `garmin_extractor.py` (687줄) — Garmin raw JSON → Layer 1 + Layer 2 변환.

- class **GarminExtractor**: extract_activity_core, extract_activity_metrics, extract_activity_laps, extract_activity_streams, extract_wellness_core, extract_wellness_metrics, extract_fitness

### `garmin_lap_fields.py` (36줄) — Garmin 랩(lapDTOs)·스트림 확장 필드 — 예측 리뉴얼(P7-PRED-12)에서 보존하는 값.

- functions: lap_extras, pick

### `intervals_extractor.py` (197줄) — Intervals.icu raw JSON → Layer 1 + Layer 2 변환.

- class **IntervalsExtractor**: extract_activity_core, extract_activity_metrics, extract_wellness_core, extract_fitness

### `runalyze_extractor.py` (105줄) — Runalyze raw JSON → Layer 1 + Layer 2 변환.

- class **RunalyzeExtractor**: extract_activity_core, extract_activity_metrics

### `strava_extractor.py` (216줄) — Strava raw JSON → Layer 1 + Layer 2 변환.

- class **StravaExtractor**: extract_activity_core, extract_activity_metrics, extract_activity_streams, extract_best_efforts

### `stream_time.py` (95줄) — 스트림 시간축 결정(U18a) — 경과시간 키 선택·보간·출처(time_basis) 판정과 meta 요약 (순수 함수).

- class **StreamRows**: 없음
- functions: resolve_time_axis, stream_meta

## `src/ai/`

> AI 코칭 컨텍스트 빌더.
> 
> 서비스 레이어 데이터를 LLM 프롬프트용 마크다운으로 변환.
> 직접 SQL 금지 — 서비스 레이어만 호출. None 메트릭은 출력에서 제외.
> 
> 설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
> 의존: src/services/, src/web/template_helpers.py

### `ai_cache.py` (167줄) — AI 캐시 관리 — DB 기반 AI 해석 결과 저장/조회/갱신.

- functions: get_cached, set_cached, get_cache_age, invalidate

### `ai_context.py` (185줄) — Phase 5 AI 컨텍스트 빌더 — 서비스 레이어 기반 LLM 프롬프트 생성.

- functions: build_daily_briefing, build_activity_analysis, build_ai_context

### `ai_context_legacy.py` (290줄) — 레거시 dict 기반 AI 컨텍스트 — build_context/format_context_text/format_activity_context.

- functions: build_context, format_context_text, format_activity_context

### `ai_message.py` (311줄) — AI 우선 메시지 생성기 — API 있으면 AI, 없으면 규칙 기반.

- functions: get_ai_message, get_card_ai_message, get_tab_ai

### `ai_parser.py` (125줄) — AI 응답에서 JSON 추출 및 훈련 계획/추천 칩 파싱.

- functions: extract_json_block, parse_weekly_plan, parse_suggestions, parse_ai_chips

### `ai_schema.py` (121줄) — AI 훈련 계획 JSON 스키마 정의 및 검증.

- functions: validate_weekly_plan, normalize_workout

### `ai_validator.py` (127줄) — AI 응답 검증 — 포맷 + 길이 + 데이터 정합성.

- functions: validate_response, parse_json_response

### `briefing.py` (101줄) — AI 코치 브리핑 프롬프트 조립.

- functions: build_briefing_prompt, build_chip_prompt, get_clipboard_prompt

### `chat_context.py` (101줄) — AI 채팅 전용 컨텍스트 빌더 — 의도 감지 → DB 자동 수집.

- functions: build_chat_context, build_chat_context_scoped

### `chat_context_builders.py` (310줄) — AI 채팅 컨텍스트 — 기본 + 의도별 빌더.

- (public API 없음)

### `chat_context_checkin.py` (45줄) — AI 채팅 컨텍스트 — 러너 자기 보고(QuickInput 체크인).

- functions: build_checkin_context, format_checkin_line

### `chat_context_format.py` (289줄) — AI 채팅 컨텍스트 — 포맷터 (컨텍스트 dict → 프롬프트 텍스트).

- (public API 없음)

### `chat_context_intent.py` (83줄) — AI 채팅 컨텍스트 — 의도 감지 모듈.

- functions: detect_intent

### `chat_context_rich.py` (202줄) — AI 채팅 컨텍스트 — 풍부한 컨텍스트 빌더 (Gemini/Claude용).

- (public API 없음)

### `chat_context_scope.py` (51줄) — AI 채팅 컨텍스트 — 외부 LLM으로 나가는 항목 목록(sent_scope, 30-coach-chat design §4.3).

- functions: describe_scope, scope_catalog

### `chat_context_utils.py` (32줄) — AI 채팅 컨텍스트 — 공통 유틸리티.

- functions: seconds_to_pace

### `chat_engine.py` (252줄) — AI 채팅 엔진 — 교체 가능 구조.

- functions: get_ai_provider, chat_result, chat

### `chat_engine_providers.py` (263줄) — AI 채팅 — 외부 API provider 호출 모듈.

- functions: complete, call_with_tools, call_claude, call_openai, call_gemini, call_groq, call_genspark, call_genspark_selenium

### `chat_engine_result.py` (139줄) — 채팅 엔진 결과 모델 + provider 체인 실행 (30-coach-chat design §4.1·§4.3·§6.2).

- class **Attempt**: 없음
- class **EngineInfo**: 없음
- class **ChatResult**: engine_dict
- functions: build_chain, run_chain, engine_for_rule, engine_for_ok

### `chat_engine_rules.py` (24줄) — AI 채팅 — 규칙 기반 답변 디스패처 (30-coach-chat design §7.3).

- functions: rule_based_response

### `chat_readiness.py` (48줄) — Coach 채팅용 컨디션 판정 — Today 브리핑·계획 다운그레이드와 같은 `readiness_decision`을 쓴다.

- functions: attach_readiness, decision_lines, plan_line

### `coach_rule_grade.py` (55줄) — Coach 규칙 답변 — 회복 등급 → 오늘 강도 매핑 (30-coach-chat design §7.2).

- class **RecoveryGrade**: parse
- functions: checkin_drop, intensity_step, intensity_label

### `coach_rule_handlers.py` (216줄) — Coach 규칙 답변 핸들러 레지스트리 — chip_id → 핸들러 (30-coach-chat design §7.3).

- functions: today_advice, explain_metric, injury_check, answer_chip, answerable_chips, suggestion_chips, free_text_answer

### `coach_rule_plan_handlers.py` (176줄) — Coach 규칙 답변 — 목표·계획 계열 핸들러 (goal_feasibility · race_build · week_plan · taper_when).

- functions: goal_feasibility, race_build, week_plan, taper_when

### `coach_rule_types.py` (35줄) — Coach 규칙 답변 공통 타입 — RuleAnswer, 칩 문구 표 (30-coach-chat design §7.3).

- class **RuleAnswer**: 없음
- functions: chip_view

### `context_builders.py` (437줄) — 탭별 컨텍스트 빌더 — AI 프롬프트에 필요한 데이터를 탭별로 조합.

- functions: build_dashboard_context, build_training_context, build_report_context, build_race_context, build_wellness_context, build_activity_context, format_context_compact

### `genspark_driver.py` (384줄) — Genspark AI 채팅 DOM 자동화 — proot subprocess 브릿지.

- functions: send_and_receive

### `prompt_config.py` (244줄) — 프롬프트 템플릿 관리 — 카드별 AI 프롬프트 정의 + 사용자 커스터마이즈.

- functions: get_prompt, get_all_prompts, get_tab_prompt

### `provider_common.py` (94줄) — AI provider 공통 — 구조화 오류(ProviderError), 모델 ID 해석, 타임아웃(30-coach-chat design §4.3·§6.2).

- class **ProviderError**: 없음
- class **RateLimitError**: 없음
- functions: model_for, api_key_for, reason_for_status, check_response, timeout_for, wrap_transport_error

### `suggestions.py` (174줄) — 추천 칩 생성 — 규칙 기반 + AI 응답 파싱 하이브리드.

- class **RunnerState**: 없음
- functions: get_runner_state, rule_based_chips

### `tool_declarations.py` (210줄) — AI Function Calling 도구 선언 — Gemini function_declarations 형식.

- (public API 없음)

### `tool_exec_activity.py` (185줄) — 활동 단위 도구 실행기 — 요약, 기간 목록, 상세, 랩, 세트 비교.

- (public API 없음)

### `tool_exec_context.py` (235줄) — 일별/기간 단위 도구 실행기 — 메트릭, 웰니스, 피트니스, 날씨, 기간 비교, 프로필.

- functions: fitness_rows

### `tool_exec_laps.py` (112줄) — 랩(세트) 단위 도구 실행기 — 랩별 기록, 세션 간 세트 비교.

- (public API 없음)

### `tool_exec_summary.py` (80줄) — 기간 요약 도구 실행기 — get_training_summary (주별 볼륨·부하 + 주요 세션).

- (public API 없음)

### `tool_format.py` (125줄) — 도구 응답 압축 헬퍼 — 호출당 토큰 사용량 절감.

- functions: num, columnar, span_days, resolve_granularity, week_start_of, group_by_week, weekly_activity_rows, weekly_mean, weekly_last

### `tool_guide.py` (23줄) — 도구 사용 가이드 — MCP initialize의 instructions로 전달되는 호출 레시피.

- (public API 없음)

### `tools.py` (50줄) — AI Function Calling 도구 진입점 — 선언 재노출 + 실행 디스패치.

- functions: execute_tool

## `src/web/`

> Flask 웹 뷰 + 템플릿 헬퍼.
> 
> Phase 7까지 기존 69개 뷰 파일은 수정하지 않음.
> Phase 5에서 template_helpers.py만 신규 추가.
> 
> 설계 문서: v0.3/data/phase-5-impl/03-template-helpers.md
> 의존: src/services/, src/utils/metric_registry.py
> 주의: 기존 뷰는 v0.2 스키마 기준 — 새 스키마와 혼용 금지

### `app.py` (1358줄) — RunPulse integration workbench web app.

- functions: create_app

### `auth_cf.py` (114줄) — Cloudflare Zero Trust 헤더 기반 사용자 식별 미들웨어.

- functions: init_cf_auth, get_current_user_email

### `auto_sync.py` (120줄) — 자동 주기 동기화 — 설정된 간격마다 incremental sync 트리거.

- functions: start, stop, restart, status

### `bg_sync.py` (581줄) — 백그라운드 기간 동기화 실행기 — 서비스별 Thread + pause/stop 제어.

- class **_Starting**: is_alive
- class **BgSyncThread**: pause, resume, stop, run
- functions: start_job, pause_job, stop_job, resume_job, start_basic_sync, get_status

### `helpers.py` (902줄) — 웹 뷰 공통 헬퍼 함수.

- functions: project_root, get_current_user_id, db_path, render_sub_nav, bottom_nav, html_page, make_table, metric_row, score_badge, readiness_badge, fmt_min, fmt_duration, safe_str, connected_services, tooltip, race_shape_label, no_data_card, fmt_pace, last_sync_info

### `helpers_svg.py` (171줄) — SVG 시각화 헬퍼 — 반원 게이지 + 레이더 차트.

- functions: svg_semicircle_gauge, svg_radar_chart

### `route_svg.py` (118줄) — GPS 경로 SVG 썸네일 생성 — activity_streams에서 latlng 데이터를 SVG polyline으로 변환.

- functions: render_route_svg

### `sync_ui.py` (246줄) — 동기화 카드 UI 컴포넌트 — 기본(마지막 동기화 이후) / 기간 2탭.

- functions: sync_card_html

### `template_helpers.py` (204줄) — Phase 5 템플릿 헬퍼 — UI와 AI context 공용 포맷/해석 함수.

- functions: format_distance, format_pace, format_duration, format_speed, format_time_prediction, format_metric, interpret_metric_level, metric_level_color, confidence_badge, provider_badge, metric_display_name, metric_unit

### `views_activities.py` (184줄) — 활동 목록 뷰 — Flask Blueprint + 라우트 핸들러.

- functions: activities_list

### `views_activities_filter.py` (214줄) — 활동 목록 뷰 — 필터 폼 + 날짜 프리셋 JS.

- (public API 없음)

### `views_activities_helpers.py` (265줄) — 활동 목록 뷰 — 포맷 헬퍼 + 아이콘/배지.

- (public API 없음)

### `views_activities_table.py` (423줄) — 활동 목록 뷰 — 활동 테이블 + 요약 + 편집 바 + JS.

- (public API 없음)

### `views_activity.py` (339줄) — 활동 심층 분석 뷰 — Flask Blueprint.

- functions: activity_deep_view, activity_service_data

### `views_activity_cards_common.py` (317줄) — 활동 상세 — 공통 헬퍼·포매터·독립 카드 함수.

- functions: fmt_int, fmt_float1, fmt_min_sec, fmt_val, metric_tooltip_icon, set_ai_metric_cache, clear_ai_metric_cache, metric_interp_badge, gauge_bar, rp_row, source_badge, no_data_msg, group_header, render_activity_summary, render_activity_nav, render_horizontal_scroll, render_classification_badge, render_splits

### `views_activity_g1_status.py` (142줄) — 활동 상세 — 그룹1: 오늘의 상태 (Daily Status Strip).

- functions: render_group1_daily_status

### `views_activity_g2_performance.py` (206줄) — 활동 상세 — 그룹2: 퍼포먼스.

- functions: render_group2_performance

### `views_activity_g3_load.py` (119줄) — 활동 상세 — 그룹3: 부하/노력.

- functions: render_group3_load

### `views_activity_g4_risk.py` (87줄) — 활동 상세 — 그룹4: 과훈련/부상 위험.

- functions: render_group4_risk

### `views_activity_g5_biomechanics.py` (104줄) — 활동 상세 — 그룹5: 폼/바이오메카닉스.

- functions: render_group5_biomechanics

### `views_activity_g6_distribution.py` (161줄) — 활동 상세 — 그룹6: 훈련 분포.

- functions: render_group6_distribution

### `views_activity_g7_fitness.py` (170줄) — 활동 상세 — 그룹7: 피트니스 컨텍스트.

- functions: render_group7_fitness

### `views_activity_loaders.py` (278줄) — 활동 상세 — 데이터 로딩 함수.

- (public API 없음)

### `views_activity_loaders_v2.py` (104줄) — 활동 상세 — 신규 데이터 로더 (UI 재설계용).

- functions: load_ef_decoupling_series, load_risk_series, load_tids_weekly_series, load_darp_values

### `views_activity_map.py` (90줄) — 활동 상세 — Leaflet + OpenStreetMap 경로 지도 렌더링.

- functions: render_map_placeholder

### `views_activity_merge.py` (128줄) — 활동 그룹 병합/분리 API — Flask Blueprint.

- functions: activities_merge, activities_ungroup, activities_auto_group

### `views_activity_s5_cards.py` (277줄) — S5-C2 신규 메트릭 카드 — RTTI, WLEI, TPDI, Running Tolerance, HR 존 차트.

- functions: render_rtti_card, render_wlei_card, render_tpdi_card, render_running_tolerance_card, render_hr_zone_chart

### `views_activity_source_cards.py` (437줄) — 활동 상세 — 소스별 서비스 카드 렌더링.

- (public API 없음)

### `views_ai_coach.py` (411줄) — AI 코칭 뷰 — Flask Blueprint.

- functions: ai_coach_page, ai_coach_chat_async, ai_coach_chat, ai_coach_get_prompt, ai_coach_paste_response

### `views_ai_coach_cards.py` (591줄) — AI 코칭 페이지 렌더링 카드 — views_ai_coach.py에서 분리.

- functions: render_coach_profile, render_briefing_card, render_wellness_card, render_chips, render_chat_section, render_recent_training, render_risk_summary

### `views_dashboard.py` (437줄) — 통합 대시보드 뷰 — Flask Blueprint.

- functions: dashboard

### `views_dashboard_cards.py` (34줄) — 대시보드 카드 진입점 — 하위 모듈 re-export (backward compat).

- (public API 없음)

### `views_dashboard_cards_fitness.py` (280줄) — 대시보드 피트니스 카드 — 추세 차트 + PMC + 활동 목록 + 피트니스 미니.

- functions: render_fitness_trends_chart

### `views_dashboard_cards_recommend.py` (267줄) — 대시보드 권장/예측 카드 — 훈련 권장 + DARP + 게이지/RMR.

- (public API 없음)

### `views_dashboard_cards_risk.py` (185줄) — 대시보드 리스크 카드 — ACWR/LSI/Monotony/TSB + UTRS/CIRS 상세.

- functions: render_risk_pills_v2

### `views_dashboard_cards_status.py` (145줄) — 대시보드 상태 카드 — 오늘의 상태 스트립 + 주간 요약.

- functions: render_daily_status_strip, render_weekly_summary

### `views_dashboard_loaders.py` (129줄) — 대시보드 — 신규 데이터 로더 (UI 재설계용).

- functions: load_wellness_mini, load_weekly_summary, load_fitness_trends, load_risk_7day_trends

### `views_dev.py` (595줄) — Developer/debug routes — config, payloads, DB summary, analyze preview.

- functions: dev_index, config_summary, config_db_path, payloads, payload_view, db_summary, analyze_preview

### `views_export.py` (99줄) — 활동 데이터 CSV 내보내기 라우트.

- functions: activities_export_csv

### `views_export_import.py` (233줄) — Export 데이터 임포트 뷰 — Flask Blueprint.

- functions: export_import_page, export_import_run

### `views_guide.py` (240줄) — 용어집/가이드 페이지 — 메트릭 설명 + 분류 기준 + 적정 범위 통합.

- functions: guide_page

### `views_import.py` (311줄) — Strava Archive Import 뷰 — Flask Blueprint.

- functions: strava_archive_view, strava_archive_post, strava_archive_backfill

### `views_perf.py` (161줄) — 성능 최적화 — 배치 데이터 로더 + TTL 캐시.

- functions: cached_page, invalidate_cache, load_latest_metric_date, load_metrics_batch, load_metrics_json_batch, load_activity_metrics_batch, load_darp_batch

### `views_race.py` (410줄) — Sprint 5 · V2-6-1 — Race Prediction (DARP) UI Blueprint.

- functions: race_page

### `views_race_enhanced.py` (381줄) — 레이스 예측 보강 — 추세 차트, 목표 갭, 준비 요소, 메트릭 해설.

- functions: load_prediction_trend, load_fitness_factors, render_goal_gap, render_prediction_trend_chart, render_fitness_factors_chart, render_race_shape_trio, render_di_interpretation, render_metric_glossary

### `views_report.py` (350줄) — 분석 레포트 뷰 — Flask Blueprint.

- functions: report_view

### `views_report_charts.py` (335줄) — 레포트 — 신규 차트 렌더러 (UI 재설계용).

- functions: render_summary_delta, render_training_quality_chart, render_tids_weekly_chart, render_risk_trend_chart, render_form_trend, render_wellness_trend_chart

### `views_report_loaders.py` (182줄) — 레포트 — 신규 데이터 로더 (UI 재설계용).

- functions: load_prev_period_stats, load_training_quality_series, load_risk_trend_series, load_form_trend_series, load_wellness_trend_series, load_tids_weekly_series

### `views_report_sections.py` (312줄) — 레포트 추가 섹션 — AI 인사이트 + 요약 카드 + 테이블 + Export.

- functions: render_ai_insight, render_ai_insight_placeholder, render_export_buttons, render_summary_cards, render_weekly_chart, render_metrics_table

### `views_report_sections_cards.py` (276줄) — 레포트 섹션 — 메트릭 카드 렌더러.

- functions: render_tids_section, render_trimp_weekly_chart, render_risk_overview, render_darp_card, render_fitness_trend, render_endurance_trend

### `views_report_sections_data.py` (111줄) — 레포트 섹션 — 데이터 로더.

- (public API 없음)

### `views_settings.py` (320줄) — 서비스 연동 설정 뷰 — 메인 허브 + 설정 저장 라우트.

- functions: settings_view, settings_profile_post, settings_training_prefs_post, settings_ai_post, settings_mapbox_post, settings_prompts_post, settings_prompts_reset, settings_caldav_post, settings_caldav_test

### `views_settings_garmin.py` (586줄) — 설정 — Garmin 연동 라우트 (connect/MFA/disconnect).

- functions: garmin_connect_view, garmin_connect_post, garmin_mfa_view, garmin_mfa_submit, garmin_disconnect, garmin_browser_login, garmin_upload_token, garmin_paste_token, garmin_cf_settings_post, garmin_download_script, garmin_download_env

### `views_settings_hub.py` (94줄) — Settings 허브 보조 렌더링 — sync 상태 요약 + 시스템 정보.

- functions: render_sync_overview, render_system_info

### `views_settings_integrations.py` (315줄) — 설정 — Strava / Intervals.icu / Runalyze 연동 라우트.

- functions: strava_connect_view, strava_save_app, strava_oauth_start, strava_oauth_callback, strava_disconnect, intervals_connect_view, intervals_connect_post, intervals_disconnect, runalyze_connect_view, runalyze_connect_post, runalyze_disconnect

### `views_settings_metrics.py` (125줄) — 설정 — 메트릭 재계산 라우트 (SSE 스트림 포함).

- functions: metrics_recompute, metrics_recompute_stream, metrics_recompute_status, recompute_metrics_get

### `views_settings_render.py` (222줄) — 설정 페이지 렌더 헬퍼 — 서비스 카드 + 프로필 + Mapbox + CalDAV.

- (public API 없음)

### `views_settings_render_prefs.py` (264줄) — 설정 페이지 렌더 헬퍼 — 훈련 환경설정 + AI + 프롬프트 관리.

- (public API 없음)

### `views_shoes.py` (85줄) — 신발 목록 뷰 — Flask Blueprint.

- functions: shoes_list

### `views_sync.py` (265줄) — 동기화 탭 뷰 — 데이터 동기화 + 서비스 연결 + 임포트/익스포트.

- functions: sync_page, sync_sources_post, auto_sync_settings_post

### `views_training.py` (349줄) — 훈련 계획 뷰 — Flask Blueprint.

- functions: training_page, training_calendar_partial, training_generate

### `views_training_cal_js.py` (313줄) — 훈련 캘린더 공통 JS — week/month 뷰 공유 (H-1 스와이프, H-2 모달, H-3 툴팁 포함).

- (public API 없음)

### `views_training_cards.py` (372줄) — 훈련 계획 뷰 — 카드 렌더러 (S1~S3).

- functions: render_header_actions, render_goal_card, render_weekly_summary

### `views_training_condition.py` (152줄) — 훈련탭 — 컨디션 + AI추천 통합 카드 렌더러.

- functions: render_condition_ai_card

### `views_training_crud.py` (468줄) — 훈련 계획 — 워크아웃 CRUD 라우트 + 환경설정.

- functions: workout_create, workout_update, workout_delete, workout_confirm, workout_match_check, workout_skip, training_replan, workout_toggle, workout_patch, workout_interval_calc, training_prefs_post

### `views_training_export.py` (117줄) — 훈련 계획 내보내기/전송 라우트 (ICS, Garmin, CalDAV).

- functions: training_export_ics, push_to_garmin, push_to_caldav

### `views_training_fullplan.py` (260줄) — 훈련 전체 일정 뷰 — GET /training/fullplan.

- functions: training_fullplan

### `views_training_goal_crud.py` (387줄) — 훈련 목표 관리 CRUD 라우트 (goal_create/complete/cancel/detail/import).

- functions: goal_create, goal_complete, goal_cancel, goal_delete_plan, goal_delete, goal_detail, goal_import_preview, goal_import

### `views_training_goals.py` (486줄) — 훈련 목표 관리 패널 렌더러 (Phase G: G-1 ~ G-4).

- functions: render_goals_panel, render_goal_detail_html

### `views_training_loaders.py` (347줄) — 훈련 계획 뷰 — 데이터 로더.

- functions: load_goal, load_workouts, load_adjustment, load_training_metrics, load_yesterday_pending, load_actual_activities, load_month_workouts, load_full_plan_weeks, load_goals_with_stats, load_goal_weeks, load_sync_status

### `views_training_month.py` (211줄) — 훈련 계획 — 월간 캘린더 렌더러 (4주 뷰).

- functions: render_month_calendar

### `views_training_plan_ui.py` (247줄) — 훈련탭 — AI 추천 / 훈련 계획 개요 / 동기화 상태 렌더러.

- functions: render_ai_recommendation, render_plan_overview, render_sync_status

### `views_training_prefs.py` (207줄) — 훈련 환경 설정 카드 렌더러 — 훈련탭 내 Collapsible 섹션.

- functions: render_training_prefs_collapsed

### `views_training_shared.py` (31줄) — 훈련탭 공용 상수/헬퍼 — 여러 렌더러 모듈에서 공유.

- (public API 없음)

### `views_training_week.py` (293줄) — 훈련탭 — 주간 캘린더 렌더러 (S5).

- functions: render_week_calendar

### `views_training_wellness.py` (320줄) — 훈련탭 — 웰니스/컨디션 카드 렌더러.

- functions: render_adjustment_card, render_checkin_card, render_interval_prescription_card

### `views_training_wizard.py` (413줄) — 훈련 계획 Wizard — Blueprint + 라우트 (Phase C).

- functions: wizard_page, wizard_step, wizard_complete

### `views_training_wizard_render.py` (343줄) — 훈련 계획 Wizard — HTML 렌더러 (Phase C).

- functions: render_step1, render_step2, render_step3, render_step4, wizard_js, render_wizard_page

### `views_wellness.py` (440줄) — 회복/웰니스 상세 뷰 — Flask Blueprint.

- functions: wellness_view

### `views_wellness_enhanced.py` (570줄) — 웰니스 보강 — 기준선 밴드, 패턴 인사이트, 주간 비교, 미니차트.

- functions: load_wellness_14d, load_sleep_times, load_hrv_baseline, load_weekly_comparison, render_metrics_dash, render_7day_chart_enhanced, render_sleep_mini_chart, render_hrv_mini_chart, render_pattern_insights, render_weekly_comparison, render_wellness_glossary, render_sleep_time_pattern, build_outlier_mark_points, build_pattern_recovery_tips

## `src/training/`

> 훈련 계획 및 프로그램 관리.
> 
> 설계 문서: v0.3/data/phase-7(preview).md

### `adjuster.py` (114줄) — 컨디션 기반 당일 훈련 계획 조정.

- functions: adjust_todays_plan

### `caldav_push.py` (176줄) — CalDAV 캘린더 연동 — 훈련 계획을 외부 캘린더에 등록.

- functions: push_workout_to_caldav, push_weekly_plan_to_caldav, test_connection

### `constraints.py` (81줄) — 주간 제약 규칙(순수) — 폭염 보정·차단일 재분배·B 레이스 미니 테이퍼·교차훈련 대체 (DESIGN-U16 §3.5).

- functions: heat_adjust, redistribute_blocked, b_race_week, cross_substituted

### `fatigue.py` (158줄) — 공용 피로도·컨디션 판정 — wellness(Body Battery/수면/스트레스) + TSB 결합.

- functions: get_todays_wellness, get_latest_tsb, fatigue_level, readiness_decision

### `garmin_push.py` (197줄) — Garmin Connect 워크아웃 전송 — 훈련 계획을 워치 + 캘린더에 등록.

- functions: push_workout_to_garmin, push_weekly_plan

### `goals.py` (167줄) — 훈련 목표 CRUD.

- functions: plan_rules_v2_enabled, get_rules_version, set_rules_version, set_reported_load, get_reported_load, add_goal, list_goals, get_goal, get_active_goal, update_goal, complete_goal, cancel_goal

### `interval_calc.py` (221줄) — 인터벌 트레이닝 처방 계산.

- functions: prescribe_interval, prescribe_from_vdot

### `long_run_rules.py` (192줄) — 롱런 하한·상한 규칙(순수) — 엔진 후처리·주기화·게이트가 같은 함수를 부른다 (DESIGN-U16-LONGRUN §3~§5).

- class **LongCtx**: 없음
- class **LongBudget**: 없음
- functions: abs_min_km, basis_km, time_cap_km, abs_cap_km, share_ratio, long_floor_km, prog_cap_km, long_cap_km, min_viable_week_km, budget_floor_km, plan_long_budget, feasible_week_km

### `marathon_rules.py` (51줄) — 마라톤 페이스(MP) 규칙 R6(순수) — 처방 MP, 롱런 페이스, long_mp 비중, 테이퍼 MP 세션 (DESIGN-U16 §2.3).

- functions: prescribed_mp, long_run_pace, long_mp_km, taper_week1_mp_km, race_week_session

### `match_select.py` (61줄) — 계획↔활동 매칭 선택 규칙(순수) — 같은 날 활동 중 계획에 맞는 하나를 고르고, 결과 라벨을 분류한다.

- functions: compatible, pick_activity, is_done, classify_outcome

### `matcher.py` (259줄) — 날짜 기반 계획 ↔ 실제 활동 자동 매칭 + session_outcomes 저장.

- functions: match_week_activities, save_skipped_outcome, get_actual_activities_for_week

### `matcher_context.py` (122줄) — 세션 결과 컨텍스트 — 활동 HR 존 분포·훈련 당일 컨디션 스냅샷(matcher.py 에서 분리).

- (public API 없음)

### `outcome_store.py` (57줄) — 세그먼트 이행 결과 저장(P7-PRED-43) — 매칭된 계획·활동 쌍에 v2 비교(outcome_v2.compare)와 소스 컴플라이언스를 기록.

- functions: update_outcome_v2

### `outcome_v2.py` (130줄) — 계획↔실행 세그먼트 비교(순수, P7-PRED-42) — 계획 단계 구조(structure_json)와 실행 bout(classifier v2 json)를 맞춰 이행률 산출.

- functions: expand_work, is_continuous, compare_continuous, compare, prediction_note

### `periodization.py` (117줄) — 목표 대회 역산 주기화(순수) — 대회 주에서 거꾸로 감량·피크·빌드 구간을 배치하고 주간 거리·롱런을 점진 증가시킨다.

- class **WeekTarget**: 없음
- functions: build_schedule

### `personalize.py` (35줄) — 개인화 규칙(순수) — 복귀 구간 램프율과 시작 롱런 (DESIGN-U16-PLAN-ENGINE §3.2, v2 전용).

- functions: is_comeback, comeback_ceiling, next_level, start_long_km

### `plan_backtest.py` (224줄) — 계획 엔진 백테스트(읽기 전용) — v1/v2 엔진을 같은 시나리오로 돌려 plan_gates 로 판정한다.

- class **Scenario**: start_monday
- functions: rest_mask, engine_v1, engine_v2, grid_scenarios, seed_grid_history, history_inputs, history_scenarios, judge, run_scenario, summarize

### `plan_gates.py` (182줄) — 계획 백테스트 게이트(순수) — 주간 계획이 구조 불변식(G1~G9)과 실행 가능성(F1~F6)을 지키는지 판정한다.

- class **Session**: 없음
- class **WeekPlan**: km, run_days, long_km, mp_session_km
- class **GateResult**: ok
- functions: g1_rest_days, g3_min_session, g4_mp_sessions, g5_taper, g6_ramp, g7_mp_not_faster, serialize, g8_deterministic, f1_start_fit, f2_peak_long, f3_peak_week, f4_total_ratio, f5_race_pace

### `plan_gates_long.py` (108줄) — 롱런 게이트(순수) — G2a 공유 상한·G2b 외피·G9 하한·F6 진행 (DESIGN-U16-LONGRUN §4.4).

- functions: week_ctx, g2a_long_cap, g2b_long_envelope, g9_long_floor, f6_long_step

### `plan_readiness.py` (65줄) — 계획 준비 볼륨·경고 — 피크 롱런 하한을 담을 주간 거리에 대회 전까지 닿는지 판정한다 (DESIGN-U16-LONGRUN §5.2-5).

- functions: ready_week_km, cold_peak_km, readiness_warning, plan_warnings

### `plan_structure.py` (43줄) — 계획 행 → 세그먼트 구조(structure_json, 순수) — 거리뿐 아니라 세트 수·반복 거리·구간 페이스로 이행을 판정하기 위한 기준.

- functions: structure_for_plan

### `planned_query.py` (38줄) — 주간 planned_workouts 조회(결과·대체됨 플래그 포함) — planner.py 에서 분리.

- functions: get_planned_workouts

### `planner.py` (292줄) — 규칙 기반 주간 훈련 계획 생성 (v2 — 논문 기반 재설계).

- functions: generate_weekly_plan, save_weekly_plan, upsert_user_training_prefs

### `planner_config.py` (185줄) — 훈련 계획 — 상수 및 설정/메트릭 조회 헬퍼.

- functions: load_prefs, get_available_days, get_latest_fitness, get_vdot_adj, get_eftp, get_marathon_shape_pct, get_week_index

### `planner_rules.py` (323줄) — 훈련 계획 — 훈련 단계·볼륨·Q-day·페이스·볼륨 배분·설명 규칙.

- functions: weeks_to_race, plan_weeks_until_race, plan_start_monday, apply_race_week, training_phase, resolve_distance_label, weekly_volume_km, assign_qday_slots, assign_long_run_slot, get_paces_from_vdot, pace_range, distribute_volume, description

### `planner_schedule.py` (181줄) — 목표 대회 역산 주간 목표 조회 — 최근 훈련량(DB)을 읽어 periodization.build_schedule 에 넣는다.

- functions: recent_load, recent_long_max, recent_avg_km, cold_start_km, start_load, schedule_for_goal, week_cap_km, plan_start_source, week_target

### `planner_v2.py` (192줄) — 계획 규칙 v2 후처리(DESIGN-U16) — v1 주간 행에 MP 세션·롱런 페이스·주간 구조 규칙을 입힌다.

- functions: apply_v2, apply_for_goal

### `planner_v2_long.py` (107줄) — 계획 규칙 v2 롱런 후처리 — 예산(§5.1)으로 러닝 일수·롱런 거리를 정하고 주간 합계를 보존해 재분배한다.

- functions: total, rebalance, trim_run_days, plan_long_week, long_fill_km

### `progression.py` (46줄) — 품질 세션 진행 사다리(순수) — 유형별 단계 정수와 R5 라벨 기반 승급·유지·강등 (DESIGN-U16 §3.3).

- functions: max_step, next_step, prescription

### `readiness.py` (458줄) — 훈련 준비도 분석 + 목표 달성 가능성 예측.

- functions: vdot_to_time, get_taper_weeks, get_recommended_weeks, recommend_weekly_km, get_phase_for_week, analyze_readiness

### `rematch.py` (110줄) — 기존 계획 정정 도구 — 자동 매칭 재평가 + 대회일 기준 미래 주차 재생성.

- functions: rematch, replan_future, main

### `replanner.py` (286줄) — 건너뜀/이행 미달 시 이번 주 잔여 계획 재조정.

- functions: replan_remaining_week

### `week_compliance.py` (188줄) — 날짜별 유효 계획·이행 수치 — UX 리뷰 31-coach-plan design §4.1 R1·R2·R3·R5 (읽기 시점 계산).

- functions: outcome_label, compute

### `week_structure.py` (132줄) — 주간 구조 규칙 R7(순수) — 러닝 일수 기본값, 롱런 상한, 최소 세션 병합·재분배 (DESIGN-U16 §2.3).

- functions: default_run_days, default_ctx, long_ratio, long_cap_km, feasible_week_km, apply_week_structure, spill

### `weekly_adapt.py` (78줄) — 주간 적응 규칙(순수, DESIGN-U16 §3.4) — 지난주 이행도로 다음 주 목표 km·퀄리티 수·사다리 동결을 정한다.

- class **AdaptInput**: 없음
- class **AdaptDecision**: 없음
- functions: decide, apply_to_rows

## `src/utils/`

> 공유 유틸리티.
> 
> DB 헬퍼, 메트릭 레지스트리, 시맨틱 그룹, rate limiter 등.
> 다른 모듈이 공통으로 사용하는 기능만 배치.
> metric_registry는 category의 single source of truth.
> 
> 설계 문서: v0.3/data/architecture.md
> 주의: db_helpers의 upsert 함수는 Phase 3 sync에서만 호출.
>       서비스 레이어는 read 함수만 사용.

### `activity_types.py` (85줄) — 활동 유형 정규화.

- functions: normalize_activity_type

### `api.py` (189줄) — httpx 기반 HTTP GET/POST 래퍼. 재시도 및 에러 처리.

- class **ApiError**: 없음
- functions: get, get_with_headers, post

### `canonical.py` (25줄) — 캐노니컬 활동 — 같은 활동의 소스 사본(Garmin·Intervals·Strava·Runalyze) 중 대표 1개(`v_canonical_activities`).

- functions: canonical_activity_id, group_activity_ids

### `clipboard.py` (44줄) — termux-clipboard-set 래퍼 유틸리티.

- functions: copy_to_clipboard, handle_clipboard_option

### `config.py` (188줄) — 설정 파일(config.json) 로드/저장 유틸리티.

- functions: get_config_path, enabled_sources, set_sync_source, load_config, save_config, update_service_config, redact_config_for_display

### `credential_store.py` (165줄) — 자격증명 암호화/복호화 유틸리티 (Fernet AES-128-CBC + HMAC-SHA256).

- functions: encrypt_config_credentials, decrypt_config_credentials, generate_key

### `daniels_table.py` (146줄) — Jack Daniels VDOT 유틸 — 훈련 페이스·레이스 시간은 Daniels–Gilbert 공식(`metrics/prediction/daniels.py`)으로 계산,

- functions: get_training_paces, get_race_predictions, get_marathon_volume_targets, get_race_volume_targets, vdot_to_t_pace, t_pace_to_vdot

### `db_helpers.py` (754줄) — RunPulse v0.3 DB 헬퍼 유틸리티.

- functions: upsert_payload, get_payload, upsert_activity, get_activity, get_activity_list, upsert_metric, upsert_metrics_batch, get_primary_metric, get_primary_metrics, get_all_providers, get_metrics_by_category, get_metric_history, upsert_daily_wellness, get_db_status, upsert_laps_batch, upsert_streams_batch, load_activity_streams, upsert_best_efforts_batch

### `db_status.py` (147줄) — DB 상태 대시보드 — 빠른 현황 확인.

- functions: get_status, print_status, main

### `dedup.py` (292줄) — 중복 활동 매칭 유틸리티 (timestamp ±5분, distance ±3%).

- functions: is_duplicate, find_duplicates, assign_group_id, auto_group_all, assign_group_to_activities, remove_from_group

### `format_ko.py` (78줄) — 한국어 표시 포맷터 — Coach 규칙 답변·근거 칩이 같은 숫자 표기를 쓰도록 하는 단일 소스 (30-coach-chat §4.5).

- functions: fmt_distance, fmt_pace, fmt_duration, fmt_gap, fmt_signed, fmt_int, workout_ko, grade_ko, sanitize

### `log_config.py` (39줄) — 로깅 중앙 설정 — 모든 진입점에서 setup_logging() 한 번 호출.

- functions: setup_logging

### `metric_def.py` (24줄) — MetricDef — 메트릭/컬럼 정의 dataclass (metric_registry·metric_defs_* 공용, 순환 import 방지).

- class **MetricDef**: 없음

### `metric_defs_layer1.py` (89줄) — 메트릭 정의 — Layer 1 (activity_summaries·daily_wellness 컬럼). metric_registry가 합쳐서 사용.

- (public API 없음)

### `metric_defs_load.py` (144줄) — 메트릭 정의 — Layer 2 hr~load 도메인. metric_registry가 합쳐서 사용.

- (public API 없음)

### `metric_defs_misc.py` (175줄) — 메트릭 정의 — Layer 2 efficiency~meta/athlete 도메인. metric_registry가 합쳐서 사용.

- (public API 없음)

### `metric_groups.py` (150줄) — 메트릭 의미 그룹핑 — 소스 비교 뷰 지원 (보강 #8).

- functions: get_group_for_metric, get_group_members

### `metric_label_texts.py` (70줄) — 지표 한 줄 설명(description_short)·상태별 행동 힌트(action_hint) — B-4 1차 범위(기본 8 + 대표 20).

- (public API 없음)

### `metric_labels.py` (124줄) — 메트릭 표시 이름 SSOT — 레지스트리 canonical name → (name_ko, abbr). ADR-018.

- class **MetricLabel**: 없음
- functions: label_for

### `metric_priority.py` (139줄) — RunPulse 메트릭 우선순위 해소 (Provider Priority Resolution) v0.3

- functions: get_provider_priority, resolve_primary, resolve_for_scope, resolve_all_primaries

### `metric_registry.py` (111줄) — RunPulse 메트릭 레지스트리 v0.3.1

- functions: canonicalize, get_metric, list_by_category, list_by_scope, list_by_storage

### `pace.py` (73줄) — 페이스 변환 유틸리티 (초 ↔ 분:초, km/h ↔ min/km).

- functions: seconds_to_pace, pace_to_seconds, kmh_to_pace, pace_to_kmh, format_duration

### `provider_matrix_rows.py` (116줄) — Provider 매트릭스 행 정의 SSOT (S6, ADR-021).

- class **MatrixRow**: providers
- functions: get_row, compare_group_for_slug, normalize_provider

### `raw_payload.py` (117줄) — source_payloads 저장/병합 유틸리티.

- functions: store_raw_payload, update_changed_fields, fill_null_columns

### `sync_jobs.py` (292줄) — 백그라운드 동기화 작업 관리 — DB 기반 상태 추적 (sync_jobs 테이블).

- class **SyncJob**: progress_pct, current_to, rate_limit
- functions: windows, cleanup_stale_running_jobs, cleanup_stale_running_jobs_all_users, create_job, get_job, get_active_job, get_latest_job, update_job, list_recent_jobs

### `sync_jobs_schema.py` (44줄) — sync_jobs.db 스키마 — 테이블 생성과 원장 열(error_code·http_status·source_path·counts_json·trigger·started_at·finished_at) 멱등 보장.

- functions: ensure_ledger

### `sync_policy.py` (176줄) — 동기화 정책 — 서비스별 rate limit / cooldown / 기간 제한 정책 정의 및 검사.

- class **SyncPolicy**: 없음
- class **SyncGuardResult**: 없음
- functions: check_incremental_guard, check_range_guard, should_reduce_expensive_calls

### `sync_state.py` (266줄) — 동기화 상태 관리 — 실행 중 여부, 마지막 동기화 시각, rate limit 상태, 오류.

- functions: set_current_user, get_service_state, is_running, get_last_sync_at, get_retry_after_sec, get_rate_state, get_all_states, mark_running, mark_finished, set_retry_after, clear_retry_after, get_last_auto_sync, mark_auto_sync_ran

### `zones.py` (90줄) — HR존 및 페이스존 계산 유틸리티.

- functions: hr_zones, get_hr_zone, pace_zones, get_pace_zone

## `src/validation/`

> RunPulse 데이터 검증 패키지.
> 
> 초기 데이터 적재 후 파이프라인 정합성을 자동 검증합니다.
> 12개 체크: row_counts, source_distribution, unmapped_metric_ratio,
> metric_density, primary_uniqueness, provider_distribution,
> dedup_consistency, data_quality, wellness_coverage,
> fitness_continuity, referential_integrity, engine_coverage.
> 
> 사용법:
>     from src.validation.validator import DataValidator
>     results = DataValidator(conn).run_all()

### `__main__.py` (92줄) — python -m src.validation CLI 진입점.

- functions: main

### `validator.py` (334줄) — DataValidator — 12개 데이터 정합성 체크.

- class **CheckResult**: 없음
- class **DataValidator**: run_all

## `tests/`

### `conftest.py` (146줄) — pytest 공통 fixture — v0.3 스키마.

- functions: db_conn, db_conn_default, db_conn_user, sample_config

### `helpers_pred.py` (29줄) — 예측 v2 테스트 공용 시드 헬퍼(P7-PRED-11).

- functions: mem_conn, seed_run, seed_laps

### `test_activity_calcs.py` (172줄) — Activity-Scope calculator 테스트 (decoupling, gap, classifier, vdot, ef).

- class **TestDecoupling**: test_with_streams, test_too_short, test_no_streams
- class **TestGAP**: test_with_streams, test_no_streams
- class **TestClassifier**: test_easy_run, test_long_run, test_non_running
- class **TestVDOT**: test_compute, test_too_short, test_non_running
- class **TestEF**: test_compute, test_no_hr
- class **TestClassifierV2Segments**: test_interval_from_laps, test_continuous_tempo_auto_laps

### `test_activity_core_sanitize.py` (97줄) — 센서 미측정/GPS 글리치 값 정리 — sanitize_activity_core, ACWR 캡.

- class **TestSanitizeActivityCore**: test_zero_hr_becomes_none, test_valid_hr_is_kept, test_impossible_max_speed_becomes_none, test_plausible_max_speed_is_kept, test_input_is_not_mutated, test_save_activity_core_stores_null
- class **TestStreamHeartRate**: test_zero_heart_rate_becomes_null
- class **TestACWRCap**: test_steady_load_ratio, test_low_chronic_load_returns_empty, test_no_history_returns_empty, test_zero_ctl_returns_empty

### `test_activity_derived_v2.py` (159줄) — tests/test_activity_derived_v2.py — 1-3 활동 파생 수치(UX 리뷰 20 design S1): RE·디커플링·스트림 헬퍼.

- functions: test_easy_run_re_uses_athlete_max_not_activity_max, test_re_integrates_stream_zones, test_moving_segments_drop_stops_and_rescale_index_elapsed, test_decoupling_excludes_warmup_and_stops, test_activity_vdot_and_low_confidence_re_hidden, test_te_bands_follow_garmin_scale, test_gap_uphill_is_faster_than_actual_pace, test_gap_without_elevation_is_empty, test_u18c_measured_meta_skips_rescale, test_u18c_dwell_sum_matches_measured_moving_time, test_u18c_ctx_get_stream_meta

### `test_activity_export.py` (70줄) — 원본 링크·GPX 내보내기 테스트.

- functions: conn_ids, test_source_links_skip_unsafe_id, test_gpx_no_gps, test_gpx_ok_and_missing, test_export_routes

### `test_activity_feedback_service.py` (90줄) — activity_feedback_service 테스트.

- functions: conn, test_upsert_and_get, test_two_activities_same_day_independent, test_all_empty_deletes, test_invalid_rejected, test_pain_none_clears_sites, test_group_member_lookup_and_canonical_cleanup, test_missing_activity_raises, test_feedback_for_activities_bulk, test_delete

### `test_activity_impact_service.py` (271줄) — tests/test_activity_impact_service.py — activity_impact_service 단위 테스트.

- functions: test_non_running_returns_none, test_no_distance_returns_none, test_missing_activity_returns_none, test_ctl_delta_computed, test_ctl_delta_none_when_no_prev_day, test_tsb_none_when_missing, test_similar_distance_basis_n5, test_similar_under_min_returns_none, test_similar_same_class_preferred_over_distance, test_similar_same_course_preferred, test_similar_excludes_self_and_future, test_race_present, test_race_none_when_no_goal, test_race_ignores_past_goals, test_get_activity_detail_includes_impact_key, test_get_activity_detail_impact_none_for_non_running, test_race_uses_activity_date_not_today, test_load_is_activity_trimp

### `test_activity_list_summary.py` (118줄) — 활동 목록 facets·summary·확장 필터/정렬/행 필드 테스트 (U10, A-17/A-18/B-3).

- functions: conn, test_facets_running_group_counts_indoor, test_facets_types_respect_sport_group, test_list_type_filter_maps_long_run, test_list_sport_group_month_and_row_fields, test_list_sort_load_and_q, test_parse_args_rejects_bad_values, test_display_title_keeps_user_names, test_summary_boundary_week_in_range_only, test_summary_month_block_prev_month_pct, test_summary_prev_month_empty_is_null_and_no_month_without_param, test_summary_avg_12w_ignores_filters_and_needs_history, test_summary_shares_type_filter

### `test_activity_merge.py` (152줄) — 활동 그룹 병합/분리 API 엔드포인트 테스트.

- class **TestMergeEndpoint**: test_merge_two_activities, test_merge_requires_two, test_merge_missing_ids, test_merge_invalid_ids
- class **TestUngroupEndpoint**: test_ungroup_activity, test_ungroup_missing_id, test_ungroup_invalid_id
- functions: app

### `test_activity_service.py` (308줄) — tests/test_activity_service.py — Phase 5-A 서비스 레이어 테스트.

- functions: conn, test_get_activity_list_basic, test_get_activity_list_filter_type, test_get_activity_list_filter_date_range, test_get_activity_list_pagination, test_get_activity_list_sort, test_get_activity_list_sort_injection_guard, test_get_activity_list_empty, test_get_activity_detail_core, test_get_activity_detail_metrics_by_category, test_get_activity_detail_source_comparison, test_get_activity_detail_semantic_groups, test_get_activity_detail_streams, test_get_activity_detail_streams_downsampled_over_500_points, test_get_activity_detail_not_found, test_get_activity_streams, test_get_activity_streams_source_filter, test_get_activity_streams_meta_unknown_without_row, test_get_activity_streams_empty, test_get_activity_trend, test_get_activity_trend_empty, test_list_route_preview_downsampled_and_none_without_gps, test_route_previews_skips_when_too_many

### `test_activity_splits.py` (84줄) — activity_splits — 서버 스플릿·series 계산 테스트.

- functions: test_splits_even_pace, test_splits_stop_excluded_from_pace, test_splits_partial_and_short, test_cumulative_distance_integrates_speed_when_missing, test_series_bounded_and_aligned, test_series_none_without_distance, test_detail_includes_splits_series_siblings

### `test_activity_summary_extras.py` (64줄) — activity_summary_extras 단위 테스트.

- functions: test_pace_cv_needs_three_splits, test_workout_class_and_environment, test_hr_zones_from_detail_and_device, test_source_diffs_threshold, test_verdict_text_and_none

### `test_activity_types.py` (43줄) — activity_types.py 단위 테스트.

- class **TestNormalizeActivityType**: test_garmin_running, test_garmin_trail, test_strava_run, test_strava_trail_run, test_strava_ride, test_intervals_run, test_unknown_type_passthrough, test_empty_string, test_case_insensitive, test_cycling_variants, test_garmin_indoor_running, test_indoor_running_case_whitespace

### `test_adaptation_service.py` (121줄) — tests/test_adaptation_service.py — adaptation_service.get_adaptation_status() 단위 테스트.

- functions: test_acwr_zone_boundaries, test_hrv_zone_boundaries, test_get_adaptation_status_all_none, test_get_adaptation_status_acwr_latest_before_date, test_get_adaptation_status_hrv_zone, test_get_adaptation_status_hrv_null_baseline, test_get_adaptation_status_fatigue_avg

### `test_adjuster.py` (120줄) — tests/test_adjuster.py — adjuster 단위 테스트.

- functions: conn, test_adjust_returns_none_no_plan, test_adjust_returns_dict_with_plan, test_adjustment_reason_parts_is_list, test_adjust_past_date_uses_that_dates_data, test_adjust_today_default_unchanged, test_adjust_past_date_no_plan_returns_none

### `test_ai_context.py` (236줄) — tests/test_ai_context.py — Phase 5-D AI 컨텍스트 빌더 테스트.

- functions: conn, test_build_daily_briefing_full, test_build_daily_briefing_contains_readiness, test_build_daily_briefing_contains_fitness, test_build_daily_briefing_no_wellness, test_build_daily_briefing_race_predictions, test_build_daily_briefing_format, test_build_activity_analysis_full, test_build_activity_analysis_contains_core, test_build_activity_analysis_no_rp_metrics, test_build_ai_context_daily_only, test_build_ai_context_with_activity, test_build_context_today_activity, test_build_context_no_activity, test_build_context_fitness, test_build_context_no_data_graceful, test_format_context_text_is_string, test_format_context_text_no_data_graceful, test_format_activity_context_is_string, test_format_activity_context_missing_activity, test_rule_based_response_does_not_raise, test_rule_based_response_no_data_graceful, test_legacy_reexport_paths_identical

### `test_ai_parser.py` (154줄) — ai_parser 모듈 테스트.

- functions: test_extract_json_block_from_code_block, test_extract_json_block_bare_code_block, test_extract_json_block_no_code_block, test_extract_json_block_list, test_extract_json_block_none_when_invalid, test_extract_json_block_broken_json, test_parse_weekly_plan_valid, test_parse_weekly_plan_no_json, test_parse_weekly_plan_invalid_type, test_parse_weekly_plan_missing_date, test_parse_weekly_plan_rest_no_distance_ok, test_parse_weekly_plan_empty_workouts, test_parse_suggestions_string_list, test_parse_suggestions_dict_list, test_parse_suggestions_max_5, test_parse_suggestions_no_json, test_parse_ai_chips_basic, test_parse_ai_chips_with_id, test_parse_ai_chips_empty_on_failure

### `test_ai_schema.py` (92줄) — ai_schema 모듈 테스트.

- functions: test_validate_valid_plan, test_validate_not_dict, test_validate_no_workouts, test_validate_invalid_type, test_validate_invalid_date, test_validate_distance_out_of_range, test_validate_too_many_workouts, test_validate_rest_no_distance_ok, test_normalize_uses_type_key, test_normalize_uses_workout_type_key, test_normalize_source_is_ai, test_normalize_none_distance

### `test_ai_tool_format.py` (115줄) — 도구 응답 압축 헬퍼 — columnar, 반올림, 주별 롤업.

- class **TestNum**: test_integer_valued_float_becomes_int, test_rounds_to_digits, test_none_passthrough, test_integer_after_rounding_drops_decimal
- class **TestColumnar**: test_rows_follow_fields, test_all_null_column_is_dropped, test_empty_rows
- class **TestGranularity**: test_auto_short_is_daily, test_auto_long_is_weekly, test_explicit_day_within_limit, test_explicit_day_beyond_limit_falls_back_with_note, test_explicit_week, test_unknown_value_is_auto, test_span_days_inclusive
- class **TestWeekStart**: test_sunday_start, test_monday_start, test_accepts_timestamp
- class **TestWeeklyActivity**: test_totals_pace_and_long_run, test_pace_is_time_over_distance_not_mean_of_paces, test_hr_is_time_weighted, test_gap_weeks_are_filled_within_span, test_no_span_keeps_only_active_weeks
- class **TestWeeklyAggregates**: test_mean_skips_nulls_and_counts_days, test_last_takes_final_non_null_per_column

### `test_ai_tool_guide.py` (44줄) — 호출 가이드 — 도구 목록과 어긋나지 않는지, 세션 고정 비용이 상한을 넘지 않는지.

- functions: test_guide_within_length_budget, test_guide_mentions_every_tool, test_guide_and_skill_reference_only_real_tools, test_skill_mentions_every_tool, test_declaration_fixed_cost_budget, test_tool_system_text_mentions_every_tool

### `test_ai_tools_compact.py` (276줄) — 토큰 최적화 도구 — 압축 응답(fields+rows), 주별 롤업, get_training_summary.

- class **TestActivitiesRange**: test_short_range_is_daily_columnar_with_id, test_long_range_rolls_up_weekly, test_weekly_fills_gap_weeks, test_explicit_day_overrides_auto_within_limit, test_day_beyond_limit_falls_back_with_note, test_columnar_is_much_smaller_than_keyed_rows
- class **TestWellness**: test_daily_values_are_rounded, test_long_range_weekly_mean_with_day_count
- class **TestFitness**: test_daily_and_weekly, test_weekly_takes_end_of_week_value
- class **TestMetricsTrend**: test_daily_columnar, test_long_period_weekly
- class **TestTrainingSummary**: test_totals_and_weekly_rows_include_gap_week, test_weekly_load_is_end_of_week_value, test_notable_has_race_and_structured_session_with_sets, test_notable_is_capped_with_omitted_count_and_races_first, test_empty_period_returns_zero_totals, test_monday_week_start
- class **TestWorkoutTypeFromTextValue**: test_get_activity_reports_workout_type, test_race_history_matches_classified_race_without_keyword_in_name
- class **TestWeather**: test_columnar_and_empty
- class **TestDeclarations**: test_all_tools_execute_without_error_on_empty_db, test_list_tools_expose_granularity, test_response_json_has_no_padding_whitespace

### `test_ai_tools_laps.py` (193줄) — 랩(세트) 조회 도구 — get_activity_laps, compare_workout_sets.

- class **TestToolDeclarations**: test_new_tools_declared, test_declarations_have_schema
- class **TestGetActivityLaps**: test_returns_compact_rows, test_pace_formatted, test_lap_types_counted, test_filter_active_only, test_all_null_column_dropped, test_no_laps_returns_message
- class **TestCompareWorkoutSets**: test_sessions_sorted_recent_first, test_set_aggregates, test_positive_drift_means_slowdown, test_excludes_non_active_laps, test_name_filter, test_date_range_filter, test_limit, test_auto_lap_run_is_not_a_workout
- class **TestActivityIdExposed**: test_get_activity_includes_id, test_get_activities_range_includes_id

### `test_api.py` (81줄) — api.py httpx 래퍼 테스트.

- class **TestGet**: test_success, test_retry_then_success, test_double_failure_raises
- class **TestPost**: test_post_json

### `test_api_activity_feedback.py` (56줄) — 활동 피드백 API 테스트.

- functions: client, test_get_empty_null, test_unknown_activity_404, test_put_get_delete, test_put_invalid_400_code

### `test_api_coach.py` (272줄) — tests/test_api_coach.py — /api/v1/coach 테스트(스레드·메시지·SSE·취소·재생성·엔진·동의).

- functions: mini_app, test_list_threads_empty, test_create_thread, test_create_thread_missing_message, test_get_thread_detail, test_get_thread_detail_not_found, test_add_message, test_add_message_thread_not_found, test_add_message_missing_content, test_engine_rule_by_choice_without_consent, test_consent_roundtrip_builds_chain, test_consent_rejects_bad_provider, test_suggestions_are_handler_backed, test_create_thread_by_chip_id, test_unknown_chip_or_empty_body_rejected, test_stream_returns_sse_events_and_headers, test_stream_resumes_with_last_event_id, test_get_message_poll, test_client_msg_id_makes_resend_idempotent, test_cancel_route, test_regenerate_ai_and_rule_modes, test_activity_context_endpoint, test_create_thread_with_activity_context, test_get_thread_returns_context

### `test_api_data_sync.py` (115줄) — POST /api/v1/data/sync — 상태코드 매핑·입력 검증, api_error details.

- functions: client, test_202_partial_start, test_422_no_sources, test_409_all_running, test_429_cooldown_has_retry_after, test_400_invalid, test_non_json_body_is_empty, test_503_missing_db, test_api_error_details_optional, test_cancel_404, test_cancel_running_requests_stop, test_cancel_finished_is_idempotent

### `test_api_library.py` (420줄) — tests/test_api_library.py — GET /api/v1/library/activities(+:id, +:id/streams, /metrics/:slug) 테스트.

- functions: mini_app, test_list_activities_default, test_list_activities_sport_filter, test_list_activities_search_filter, test_list_activities_dist_min_filter, test_list_activities_dist_min_invalid, test_get_activity_detail, test_get_activity_detail_not_found, test_get_activity_streams, test_get_activity_streams_returns_meta, test_get_activity_detail_etag_304_on_revalidate, test_get_activity_streams_etag_304_on_revalidate, metric_app, test_get_metric_breakdown_200, test_get_metric_breakdown_404, test_get_metric_breakdown_missing_scope_id, test_get_metric_breakdown_default_scope_type, test_get_activity_providers_200, test_get_activity_providers_404, test_get_metrics_browser_200, test_get_metrics_browser_no_date, test_get_metric_trend_200, test_get_metric_trend_404, test_get_wellness_200, test_get_wellness_no_date, test_get_wellness_bad_date_400, test_get_wellness_future_date_clamped_to_today, test_get_wellness_trend_bad_end_400, test_get_wellness_trend_200, test_get_wellness_trend_invalid_days, test_get_providers_matrix_200, test_get_providers_matrix_invalid_days, test_get_providers_pairs_route, test_get_providers_coverage_200, test_get_activity_detail_streams_opt_in

### `test_api_plan.py` (311줄) — tests/test_api_plan.py — GET /api/v1/coach/plan/* 라우트 테스트.

- functions: mini_app, app_with_goal, test_get_active_plan_404_no_goal, test_get_active_plan_200, test_get_plan_by_id_200, test_get_plan_by_id_404, test_get_adjustment_200_no_plan, test_get_adjustment_200_with_plan, test_get_templates_400_no_distance, test_get_templates_200, test_post_plan_400_missing_fields, test_post_plan_201_creates_goal, app_with_session, test_get_session_detail_200, test_get_session_detail_404_missing_date, test_get_session_detail_404_invalid_goal, test_post_session_note_200, test_post_session_note_400_empty_note, test_post_session_note_400_missing_note, test_get_plan_adaptation_empty, test_get_plan_adaptation_with_acwr

### `test_api_plan_reported.py` (53줄) — POST /api/v1/coach/plan 선택 입력(최근 주간·최장 km)과 준비도 경고(warnings) — DESIGN-U16-LONGRUN §5.2.

- functions: mini_app, test_post_plan_reported_load_saved_and_warnings, test_post_plan_400_bad_reported_load

### `test_api_prediction.py` (55줄) — P7-PRED-53·71: 예측 비교·대회 확인 API.

- functions: client, test_compare, test_profile, test_confirm_flow

### `test_api_today.py` (173줄) — tests/test_api_today.py — GET/POST /api/v1/today Flask 라우트 테스트.

- functions: mini_app, test_get_today_no_data, test_get_today_reflects_saved_checkin, test_post_checkin_saves_and_returns, test_post_checkin_no_body, test_get_today_checkin_none, test_get_today_checkin_after_post, test_get_today_narrative_no_data, test_get_today_narrative_highlights_field, test_get_today_narrative_year_month_params, test_get_today_narrative_invalid_year_month, test_get_race_hub_no_goal, test_get_library_archive_empty, test_get_today_includes_data_health, test_get_today_status_date_is_local, test_today_response_has_v2_fields

### `test_archive_service.py` (89줄) — tests/test_archive_service.py — 러닝 아카이브 집계.

- functions: test_months_back_crosses_year, test_empty_db, test_totals_monthly_heatmap_longest, test_personal_bests_pick_min_and_skip_missing, test_personal_bests_merge_race_results_with_source_labels

### `test_auth_cf.py` (120줄) — auth_cf.py 테스트 — Cloudflare Zero Trust 헤더 기반 사용자 식별.

- functions: dev_app, prod_app, test_dev_cf_header_sets_session, test_dev_no_header_fallback_to_dev_user, test_dev_session_reused_without_reparse, test_dev_email_with_special_chars, test_prod_cf_header_sets_session, test_prod_no_header_returns_401, test_prod_empty_header_returns_401

### `test_autopilot_gate.py` (32줄) — tests/test_autopilot_gate.py — gate.check()의 ignore_budget 옵션 테스트.

- functions: test_ignore_budget_false_blocks_when_over_daily_cap, test_ignore_budget_true_skips_budget_check

### `test_autopilot_queue.py` (124줄) — scripts/autopilot/queue.py 테스트 — kind="code" 확장(scope/verify) 라운드트립 중심.

- class **TestParseKindDefault**: test_missing_kind_defaults_to_docs
- class **TestParseCodeKind**: test_reads_kind_scope_verify
- class **TestUpdateItemPreservesCodeFields**: test_stage_update_keeps_scope_and_verify, test_docs_item_meta_shape_unchanged
- class **TestFindMalformedMeta**: test_wrapped_meta_flagged, test_wellformed_meta_not_flagged, test_wrapped_meta_item_silently_becomes_manual
- class **TestNextRunnableIgnoresKind**: test_code_and_docs_both_runnable

### `test_autopilot_run_unit.py` (141줄) — scripts/autopilot/run_unit.py 테스트 — kind="code" 확장 부분만.

- class **TestBuildPrompt**: test_docs_kind_uses_docs_template, test_code_kind_uses_code_template_with_scope_and_verify, test_code_kind_prompt_requires_following_embedded_spec, test_code_kind_prompt_forbids_git_dash_c, test_code_kind_missing_scope_warns_instead_of_empty
- class **TestBuildCmd**: test_docs_kind_uses_base_allowed_tools_and_budget, test_code_kind_uses_code_allowed_tools_and_budget
- class **TestPostVerify**: test_docs_kind_skips_verification, test_code_kind_passes_when_command_succeeds, test_code_kind_fails_when_command_fails, test_code_kind_defaults_to_full_pytest_when_verify_empty
- class **TestCommitLeftovers**: test_clean_worktree_is_noop, test_commits_in_scope_files_only, test_directory_scope_prefix_matches

### `test_backfill_activity_groups.py` (84줄) — activity_groups 백필 스크립트 테스트.

- class **TestBackfill**: test_backfill_creates_groups, test_backfill_primary_source_priority, test_backfill_ignores_ungrouped, test_backfill_idempotent, test_backfill_multiple_groups, test_backfill_activity_date_from_start_time
- functions: conn

### `test_bg_sync_batch_error.py` (63줄) — bg_sync — 일반 예외로 끝난 배치는 전체 0건일 때 failed로 마감한다.

- class **_Timeout**: 없음
- functions: test_all_batches_failed_marks_failed, test_partial_success_stays_completed, test_exception_in_batch_is_classified

### `test_bg_sync_concurrency.py` (64줄) — bg_sync — 동시 시작 중복 방지, (user, service) 키 분리.

- class **_FakeThread**: start, is_alive
- functions: test_concurrent_start_creates_one_job, test_different_users_do_not_collide, test_create_failure_releases_slot

### `test_briefing.py` (79줄) — tests/test_briefing.py — briefing.py 클립보드 프롬프트 조립 테스트.

- functions: conn, test_build_briefing_prompt_contains_context, test_build_briefing_prompt_no_data_graceful, test_build_chip_prompt_weekly_review, test_build_chip_prompt_today_deep_injects_activity_extra, test_build_chip_prompt_unknown_chip, test_get_clipboard_prompt_briefing_mode, test_get_clipboard_prompt_chip_mode

### `test_bulk_loader.py` (247줄) — GarminBulkLoader 테스트.

- class **TestSingleSummary**: test_loads_one_activity, test_activity_core_fields
- class **TestMultipleSummaries**: test_loads_multiple_activities
- class **TestDuplicateSkip**: test_duplicate_is_skipped
- class **TestInvalidJson**: test_bad_json_is_counted_as_error
- class **TestMissingZip**: test_missing_file_returns_failed
- class **TestBadZip**: test_not_a_zip_returns_failed
- class **TestSummaryAndDetail**: test_detail_metrics_saved, test_detail_without_summary_is_skipped
- class **TestNonJsonFilesIgnored**: test_fit_and_gpx_ignored

### `test_calculate_acwr_canonical.py` (32줄) — calculate_acwr 는 metric_store 의 정식 acwr(EWMA 7/42)를 읽는다 (D1f 통일).

- functions: test_none_when_no_metric, test_latest_primary_value_and_status

### `test_chat_context_checkin.py` (131줄) — tests/test_chat_context_checkin.py — build_checkin_context / format_checkin_line 단위 + 통합.

- functions: test_no_checkin_returns_none, test_today_checkin_fields, test_old_checkin_ignored, test_yesterday_checkin_included, test_empty_checkin_returns_none, test_empty_checkin_note_whitespace_returns_none, test_note_truncated_at_200, test_integration_checkin_in_chat_context, test_integration_no_checkin_not_in_context

### `test_chat_context_intents.py` (69줄) — AI 채팅 의도별 컨텍스트 빌더 회귀 테스트 — 스키마 드리프트 방지.

- functions: test_every_intent_builder_runs_on_current_schema, test_today_context_reads_todays_activity, test_today_context_without_activity_is_none, test_lookup_context_reads_target_date_activities

### `test_chat_context_race.py` (87줄) — test_chat_context_race.py — _add_race_context + _format_chat_context 통합 테스트.

- class **TestRaceContextWithGoal**: test_race_hub_in_context, test_formatted_text_contains_form_prediction, test_formatted_text_contains_target_prediction, test_formatted_text_contains_tsb_values
- class **TestRaceContextNoGoal**: test_race_hub_is_none_or_no_goal, test_formatted_text_no_form_prediction, test_formatted_text_no_target_prediction
- functions: ctx_with_goal, ctx_no_goal

### `test_chat_context_scope.py` (30줄) — chat_context_scope·exclude_notes — 전송 범위 목록과 메모 제외 (design §4.3).

- functions: test_describe_scope_marks_note_optional, test_describe_scope_no_note_when_blank, test_exclude_notes_drops_memo_from_prompt

### `test_chat_context_workout_type.py` (122줄) — workout_type_classified 컬럼 버그 수정 회귀 테스트 (BUG-WORKOUT-TYPE-COLUMN).

- class **TestRaceHistoryFromTextValue**: test_race_included_without_name_keyword, test_race_not_included_when_only_numeric_value
- class **TestTodayDetailWorkoutType**: test_today_detail_has_workout_type, test_today_detail_no_classification_key_absent
- class **TestSimilarActivities**: test_similar_activities_populated, test_no_similar_activities_without_classification

### `test_chat_engine_events.py` (52줄) — chat_result on_event/cancelled 훅 — 비동기 답변 단계 이벤트(30-coach-chat design §6.2).

- class **_Resp**: json
- functions: test_stage_events_per_provider_and_rule, test_cancelled_stops_chain_before_next_provider, test_tool_stage_emitted

### `test_chat_engine_result.py` (121줄) — chat_result — 엔진 상태·동의 게이트·체인 구성·예산 (30-coach-chat design §4.1·§4.3·§8).

- class **_Resp**: json
- functions: calls, test_404_on_selected_falls_to_second_provider, test_all_fail_gives_rule_fallback_with_reason, test_no_external_call_before_consent, test_consent_for_other_provider_requires_reconsent, test_fallback_disabled_uses_single_provider, test_rule_only_without_keys_and_rule_by_choice, test_exclude_notes_keeps_memo_out_of_prompt, test_budget_exhausted_stops_chain, test_legacy_chat_returns_tuple, test_rule_text_has_no_ai_coach_self_reference, test_v2_chip_with_ai_uses_free_text_path_with_tools

### `test_chat_engine_rules_grade.py` (54줄) — Coach 규칙 답변 — 회복 등급 → 강도 매핑과 오늘 판정 일치 (design 30-coach-chat §7.2, §8).

- functions: test_grade_to_intensity, test_no_grade_uses_fatigue_level, test_grade_codes_match_recovery_output, test_fatigue_level_caps_good_grade, test_checkin_steps_down_at_least_one_level, test_no_abc_grade_strings_in_rule_modules

### `test_chat_engine_threads.py` (42줄) — chat_engine._load_recent_chat()의 thread_id 필터링 — Phase 7 Coach 다중 스레드(D3).

- class **TestLoadRecentChat**: test_default_thread_id_none_ignores_thread, test_thread_id_filters_to_that_thread_only, test_empty_thread_returns_empty

### `test_chat_readiness.py` (81줄) — tests/test_chat_readiness.py — Coach 채팅이 Today·adjuster와 같은 readiness_decision을 쓰는지 검증.

- functions: conn, test_adjuster_fatigue_matches_readiness_decision, test_build_context_has_decision_and_adjustment, test_plan_line_shows_original_and_adjusted, test_chat_verdict_equals_today_headline, test_rested_runner_keeps_planned_session, test_no_data_graceful

### `test_cirs.py` (78줄) — CIRS (Composite Injury Risk Score) 단위 테스트 — 설계서 4-6.

- class **TestCIRS**: test_high_acwr_means_high_cirs, test_optimal_acwr_means_low_cirs, test_confidence_present, test_category_is_readiness, test_no_data, test_child_metrics_have_parent_and_correct_names

### `test_coach_activity_context.py` (72줄) — tests/test_coach_activity_context.py — Coach 활동 컨텍스트(근거 카드·추천 질문·프롬프트 요약).

- functions: test_suggested_questions_by_class, test_activity_context_card, test_activity_context_missing, test_prompt_summary_and_thread_injection, test_prompt_summary_includes_feedback_and_respects_note_consent, test_list_rows_carry_rpe

### `test_coach_async.py` (153줄) — coach_async 테스트 — 워커 실행·이벤트 로그·SSE 복원·취소 (INLINE 모드로 결정적 실행).

- functions: db_file, test_start_runs_and_streams_events, test_stream_honors_last_event_id, test_stream_restores_from_db_when_log_is_gone, test_duplicate_start_while_running_is_rejected, test_start_unknown_message_returns_false, test_rule_mode_skips_ai, test_worker_exception_emits_error, test_cancel_running_sets_flag, test_cancel_orphan_pending_marks_row, test_orphan_pending_stream_becomes_error, test_source_text_follows_regenerate_chain

### `test_coach_engine_health.py` (79줄) — coach_engine_health / coach_consent — 엔진 라벨, H0 집계, 동의 upsert.

- functions: test_labels, test_health_degraded_after_three_fallbacks_and_clears_on_ok, test_health_ignores_rule_only, test_save_consent_upsert_keeps_accepted_at_for_same_provider, test_save_consent_rejects_non_llm, test_get_engine_rule_only_when_no_keys, test_legacy_rule_label_single_source, test_row_status_overrides_engine_json

### `test_coach_evidence.py` (141줄) — coach_evidence 테스트 — 답변 근거 v2 (role·스냅샷·drift·legacy).

- class **TestPureHelpers**: test_rest_signal, test_is_drifted_threshold_and_sign, test_cited_needs_keyword_and_number, test_cited_rounding_tolerance
- class **TestBuildAnswerEvidence**: test_rule_path_roles_and_snapshot, test_llm_path_keeps_only_cited_and_pinned, test_exception_returns_empty, test_dedupes_by_metric
- class **TestViewEvidence**: test_legacy_without_snapshot, test_user_message_and_empty, test_drift_detected_after_recalc, test_no_drift_when_unchanged, test_wellness_current, test_kst_date_invalid

### `test_coach_rule_handlers.py` (153줄) — Coach 규칙 핸들러 레지스트리 (design 30-coach-chat §7.3, §8).

- functions: conn, test_registry_and_chip_text_match, test_today_advice_first_sentence_is_today_headline, test_today_advice_no_recovery_row, test_today_advice_checkin_fatigue_steps_down, test_unknown_chip_and_free_text_are_honest, test_chips_hide_unanswerable, test_every_answerable_chip_answers_without_raw_numbers, test_no_goal_answers_point_to_registering, test_goal_without_prediction, test_goal_answer_has_goal_prediction_and_gap, test_taper_date, test_week_plan_lists_remaining, test_free_text_answer_without_data

### `test_coach_service.py` (370줄) — coach_service 테스트 — Phase 7a D5.

- class **TestListThreads**: test_empty, test_lists_with_last_message_preview
- class **TestGetThread**: test_not_found, test_returns_thread_and_messages
- class **TestCreateThread**: test_creates_thread_and_stores_both_messages, test_title_truncated_for_long_message, test_does_not_leak_into_other_threads
- class **TestEvidence**: test_create_thread_evidence_is_list, test_create_thread_evidence_has_snapshot_and_role, test_create_thread_empty_db_has_no_evidence, test_get_thread_assistant_has_evidence_list, test_get_thread_user_message_evidence_empty, test_get_thread_no_evidence_json_key
- class **TestAddMessage**: test_appends_to_existing_thread, test_updates_thread_timestamp
- class **TestEngineState**: test_message_carries_engine_view_and_as_of, test_get_thread_exposes_engine, test_legacy_message_without_engine_json, test_engine_called_with_stored_consent_and_require_consent
- class **TestRegenerate**: test_creates_pending_child_and_hides_parent_after_success, test_failed_child_keeps_parent_visible, test_unknown_or_user_message_returns_none
- class **TestAsyncContract**: test_create_returns_pending_and_user_message_immediately, test_create_thread_is_idempotent_by_client_msg_id, test_add_message_is_idempotent_by_client_msg_id, test_status_mapping, test_followups_json_preferred_over_engine_json
- class **TestChipAndFollowups**: seen, test_chip_only_thread_uses_chip_text, test_followups_exclude_asked_chips, test_regenerate_keeps_chip_id, test_user_messages_have_no_followups
- functions: create_thread, add_message

### `test_condition_ai_card.py` (112줄) — tests/test_condition_ai_card.py — render_condition_ai_card 단위 테스트.

- functions: test_returns_empty_when_no_data, test_shows_utrs_badge, test_utrs_green_when_high, test_utrs_red_when_low, test_cirs_badge_shown, test_cirs_red_border_when_danger, test_wellness_badges_from_adj, test_adjustment_section_when_adjusted, test_no_adjustment_section_when_not_adjusted, test_ai_section_shown_with_utrs, test_ai_override_shown, test_ai_badge_only_when_override, test_volume_boost_shown_when_applicable, test_volume_boost_hidden_when_cirs_high, test_card_title_present

### `test_config_utils.py` (99줄) — config.py 헬퍼 함수 테스트 — save_config, update_service_config, redact.

- functions: tmp_config, test_save_config_creates_file, test_save_config_roundtrip, test_save_config_overwrites, test_update_service_config_creates_file, test_update_service_config_partial_update, test_update_service_config_new_service, test_redact_masks_password, test_redact_masks_token, test_redact_does_not_mutate_original, test_redact_empty_value_unchanged

### `test_constraints.py` (42줄)

- functions: test_heat_moves_quality_and_keeps_km, test_heat_below_threshold_noop, test_blocked_redistribute_cap, test_b_race_week, test_cross_substituted

### `test_consumer_migration.py` (270줄) — Phase 5-J consumer migration 검증 테스트.

- class **TestActivityService**: test_distance_m_present_in_row, test_filter_min_distance_m
- class **TestTrends**: test_weekly_distance_km, test_fitness_trend_daily_metrics, test_fitness_trend_activity_metrics, test_fitness_trend_returns_none_when_no_data
- class **TestCompare**: test_compare_periods_distance_km
- class **TestWeeklyScore**: test_total_distance_km
- class **TestActivityDeep**: test_distance_km_alias_sql
- class **TestDedup**: test_assign_group_no_crash, test_auto_group_all_no_crash
- class **TestGarminV2Mappings**: test_extract_api_returns_distance_m, test_extract_zip_returns_distance_m
- class **TestRunalyzeExtractor**: test_extract_core_distance_m
- class **TestIntervalsExtractor**: test_extract_core_distance_m
- class **TestViewsExportCSV**: test_csv_distance_km_conversion
- functions: conn

### `test_context_runs.py` (66줄) — P7-PRED-14: RunHistoryMixin.get_runs / get_active_goal / get_race_results / canonical 시리즈.

- functions: test_get_runs_twin_hr_and_race, test_get_runs_excludes_end_day_and_laps, test_tempo_name_not_race, test_perf_time_uses_elapsed_when_close, test_active_goal_and_race_results, test_metric_series_canonical_only

### `test_credential_store.py` (195줄) — credential_store.py 테스트 — Fernet 암호화/복호화 라운드트립.

- functions: fernet_key, with_key, without_key, production_without_key, test_roundtrip, test_non_sensitive_fields_unchanged, test_encrypted_values_have_prefix, test_no_double_encryption, test_empty_values_not_encrypted, test_plaintext_passthrough_on_decrypt, test_no_key_development_passthrough, test_no_key_production_raises, test_generate_key_is_valid_fernet_key, test_original_config_not_mutated

### `test_critical_power.py` (81줄)

- class **TestCriticalPower**: test_with_power_data, test_no_power, test_confidence

### `test_crs.py` (107줄)

- class **TestCRS**: test_full_level, test_high_acwr_restricts, test_low_body_battery, test_boost_condition, test_no_signals, test_category

### `test_daily2_calcs.py` (139줄) — Daily-Scope 2차 calculator 테스트.

- class **TestUTRS**: test_with_wellness_and_tsb, test_no_data
- class **TestCIRS**: test_with_metrics, test_no_data
- class **TestFEARP**: test_compute, test_non_running
- class **TestRMR**: test_with_wellness, test_no_data
- class **TestADTI**: test_with_ctl_series, test_insufficient_data

### `test_daily_calcs.py` (108줄) — Daily-Scope 1차 calculator 테스트 (PMC, ACWR, LSI, Monotony).

- class **TestPMC**: test_compute, test_no_data
- class **TestACWR**: test_compute, test_no_ctl
- class **TestLSI**: test_compute, test_no_today
- class **TestMonotony**: test_compute, test_no_data

### `test_daniels_kalman.py` (33줄) — P7-PRED-20: Daniels–Gilbert 공식·강도 구간·세트 등가 지속시간, 로컬 레벨 칼만(순수).

- functions: test_formula_anchors, test_zone_order, test_equivalent_minutes_rest_ratio, test_kalman_weights_and_decay

### `test_daniels_table.py` (75줄) — daniels_table 유틸리티 테스트.

- class **TestTrainingPaces**: test_vdot_50_paces, test_interpolation, test_boundary_low, test_boundary_high
- class **TestRacePredictions**: test_vdot_50_predictions, test_sub3_marathon
- class **TestVolume**: test_marathon_volume, test_race_volume_half, test_race_volume_10k
- class **TestTpaceConversion**: test_vdot_to_t_pace, test_t_pace_to_vdot_roundtrip, test_t_pace_to_vdot_interpolated

### `test_darp_r4.py` (114줄) — P7-PRED-51: DARP r4 섀도 — 칼만 결합, 비대칭·유지 앵커 변형, T0 동작, 섀도는 primary 가 아님.

- functions: test_path_c_kalman_combination, test_shadow_providers_never_primary, test_asym_maint_variant, test_maint_loss_only_when_ctl_drops, test_t0_without_heart_rate, test_no_data_returns_empty, test_paced_race_is_lower_bound_not_anchor, test_auto_effort_by_duration

### `test_darp_v2.py` (77줄) — P7-PRED-51: DARP v2 (c)/(b) 경로.

- functions: test_path_c_values, test_path_b_needs_ref, test_pairs_same_distance_skipped, test_5k_best_effort_signal

### `test_dashboard_service.py` (202줄) — tests/test_dashboard_service.py — Phase 5-B 서비스 레이어 테스트.

- functions: conn, test_get_dashboard_data_full, test_get_dashboard_data_wellness, test_get_dashboard_data_readiness_values, test_get_dashboard_data_training_status, test_get_dashboard_training_phase_maintaining, test_get_dashboard_data_race_predictions, test_get_dashboard_data_weekly_summary, test_get_dashboard_data_no_wellness, test_get_dashboard_data_no_metrics, test_get_dashboard_data_default_date, test_get_pmc_chart_data, test_get_pmc_chart_data_structure, test_get_pmc_chart_data_empty, test_get_daily_metric_chart, test_get_daily_metric_chart_empty, test_get_daily_metric_chart_nonexistent_metric

### `test_data_health_service.py` (36줄) — tests/test_data_health_service.py — 부하 커버리지.

- functions: test_empty, test_counts_missing_within_window_only

### `test_data_quality.py` (481줄) — 분석 파이프라인 데이터 품질 검증 테스트.

- class **TestTrendsRanges**: test_weekly_distances_in_km, test_weekly_pace_range, test_fitness_ctl_atl_range, test_fitness_tsb_range, test_nonzero_weeks_exist, test_fitness_ctl_present
- class **TestCompareRanges**: test_all_required_keys, test_delta_equals_p2_minus_p1, test_distances_in_km_range, test_avg_hr_range_when_present
- class **TestWeeklyScoreRanges**: test_score_0_to_100, test_grade_valid, test_components_non_negative, test_data_distance_km
- class **TestRaceReadinessRanges**: test_readiness_score_range, test_grade_valid, test_5k_prediction_range, test_10k_prediction_range, test_half_prediction_range, test_full_prediction_range, test_recommendation_nonempty, test_component_scores_range, test_predictions_come_from_fixture_data
- class **TestActivityDeepRanges**: first_act_id, test_structure_keys, test_pace_format, test_distance_km_not_m, test_hr_range, test_fitness_context_ctl_present
- class **TestSuggestionsRanges**: test_state_acwr_status_valid, test_weekly_run_count_plausible, test_total_distance_non_negative, test_chips_count_range, test_chips_have_required_keys, test_danger_acwr_triggers_injury_chip, test_safe_acwr_no_injury_as_first_chip
- class **TestDashboardRanges**: test_required_keys, test_training_phase_valid, test_weekly_summary_non_negative, test_ctl_range_when_present, test_recent_activities_have_distance
- class **TestWellnessRanges**: test_hrv_range, test_resting_hr_range, test_sleep_score_range, test_trend_arrays_same_length, test_wellness_detail_has_core
- functions: rich_conn

### `test_db_helpers.py` (238줄) — db_helpers.py 단위 테스트 — Phase 1 조건 8, 9

- class **TestUpsertActivitySummary**: test_insert_new, test_upsert_updates, test_no_duplicate_rows
- class **TestUpsertMetric**: test_insert_single, test_batch_upsert, test_upsert_updates_value
- class **TestUpsertDailyWellness**: test_insert, test_merge_keeps_first_non_null, test_default_does_not_overwrite_existing, test_overwrite_updates_non_null_values, test_overwrite_ignores_null_new_values
- class **TestGetPrimaryMetrics**: test_get_primary_returns_list, test_get_all_providers, test_get_primary_empty_scope
- class **TestUpsertPayload**: test_insert_and_no_change, test_update_on_change
- class **TestDbStatus**: test_returns_dict
- functions: db

### `test_db_helpers_batch.py` (101줄) — db_helpers batch 함수 테스트 (Phase 3 추가분).

- class **TestLapsBatch**: test_insert_laps, test_upsert_laps_update, test_skip_no_lap_index
- class **TestStreamsBatch**: test_insert_streams, test_replace_on_reinsert
- class **TestBestEffortsBatch**: test_insert_efforts, test_upsert_effort, test_skip_no_effort_name

### `test_db_schema_v25.py` (41줄) — v25 스키마(activity_feedback·user_settings) 테스트.

- functions: test_tables_created_and_idempotent, test_rpe_check_rejects_out_of_range, test_note_length_check, test_create_tables_wires_v25_and_version

### `test_db_setup.py` (234줄) — db_setup 테스트.

- class **TestPhase1Schema**: setup_db, test_schema_version_is_20, test_pipeline_tables_count, test_app_tables_exist, test_canonical_view_exists, test_activity_summaries_38_columns
- functions: test_get_db_path, test_create_tables, test_planned_workouts_new_columns, test_migrate_db_idempotent, test_activities_unique_index, test_activities_insert, test_migrate_v18_adds_evidence_json, test_canonical_view_untouched_when_definition_unchanged, test_canonical_view_recreated_when_definition_differs, test_canonical_view_survives_concurrent_create_tables

### `test_dedup.py` (189줄) — Dedup 단위 테스트.

- class **TestDedup**: test_same_activity_different_sources, test_different_activities_not_grouped, test_same_source_not_grouped, test_distance_threshold_exceeded, test_three_sources_same_activity, test_no_distance_falls_back_to_time, test_one_sided_zero_distance_not_grouped, test_preserves_existing_groups_on_rerun, test_third_source_joins_existing_group
- class **TestActivityGroupsUpsert**: test_assign_group_id_creates_activity_group, test_auto_group_all_creates_activity_groups, test_primary_source_priority, test_activity_groups_updated_on_rerun

### `test_di_v2.py` (28줄) — P7-PRED-89: DI v2 — 랩 기반 후반 효율 유지율, 상한 없음.

- functions: test_drift_lowers_di_and_no_cap, test_short_runs_empty

### `test_doc_sync.py` (97줄) — 문서 동기화 검증 테스트.

- class **TestMetricDictionarySync**: setup, test_dictionary_exists, test_calculator_count_matches, test_group_count_matches, test_all_calculators_documented, test_all_groups_documented, test_no_outdated_table_count

### `test_eftp.py` (70줄)

- class **TestEFTP**: test_from_vdot, test_no_vdot, test_confidence

### `test_engine.py` (209줄) — Metrics Engine 통합 테스트.

- class **TestTopologicalSort**: test_trimp_before_hrss, test_pmc_before_acwr, test_acwr_before_cirs, test_all_calculators_included
- class **TestRunActivityMetrics**: test_produces_metrics, test_metrics_in_store
- class **TestRunDailyMetrics**: test_with_trimp, test_ramp_rate_parent_metric_id_links_to_ctl, test_utrs_child_parent_metric_id_links, test_cirs_child_parent_metric_id_links
- class **TestRunForDate**: test_full_pipeline
- class **TestClearRunpulse**: test_clears_only_runpulse

### `test_engine_backfill.py` (45줄) — tests/test_engine_backfill.py — 부하(TRIMP) 누락 보정 백필.

- functions: test_find_missing_only_running_with_hr_and_duration, test_backfill_computes_trimp_and_ctl_then_is_idempotent, test_nothing_to_do_returns_empty

### `test_extractor_base.py` (76줄) — BaseExtractor와 MetricRecord 단위 테스트.

- class **DummyExtractor**: extract_activity_core, extract_activity_metrics
- class **TestMetricRecord**: test_is_empty_all_none, test_is_not_empty_numeric, test_is_not_empty_text, test_is_not_empty_json
- class **TestBaseExtractorHelpers**: setup_method, test_metric_returns_none_when_all_none, test_metric_returns_record_with_value, test_metric_with_text, test_metric_with_json, test_collect_filters_none, test_default_methods_return_empty

### `test_extractors_cross.py` (303줄) — Cross-extractor 일관성 테스트.

- class **TestGetExtractorFactory**: test_returns_correct_instance, test_case_insensitive, test_unknown_source_raises, test_returns_new_instance_each_call
- class **TestCoreKeysConsistency**: test_required_keys_present, test_all_keys_are_valid_columns, test_no_none_values_in_output
- class **TestMetricNoDuplicateWithCore**: test_no_overlap
- class **TestAllMetricsHaveCategory**: test_category_set, test_no_empty_metrics
- class **TestDistanceUnit**: test_distance_key_is_meters
- class **TestSecondsHelper**: test_already_seconds, test_milliseconds_conversion, test_none_returns_none, test_boundary_86400, test_exactly_86400, test_float_input
- class **TestCrossExtractorConsistency**: test_all_extractors_registered, test_all_have_unique_source, test_source_field_matches_class_source, test_activity_type_is_normalized, test_source_url_contains_source_id, test_all_extractors_inherit_base, test_pace_sec_km_reasonable, test_duration_sec_reasonable

### `test_fatigue.py` (85줄) — tests/test_fatigue.py — src.training.fatigue.readiness_decision 단위 테스트.

- functions: conn, test_no_data_returns_data_pending_headline, test_high_fatigue_overrides_good_tsb_headline, test_low_fatigue_falls_back_to_tsb_headline, test_explicit_tsb_overrides_lookup

### `test_fearp_v2.py` (10줄) — P7-PRED-90: fearp v2 — 외기·이슬점 보정, 기기 온도 미사용.

- functions: test_heat_penalty_table

### `test_fixture_loader.py` (17줄)

- functions: test_fixture_root_exists, test_fixture_path_resolves_readme, test_read_text_fixture_reads_readme

### `test_fixtures_layout.py` (21줄)

- functions: test_fixtures_layout_exists

### `test_flask_routes.py` (136줄) — Flask 라우트 스모크 테스트 (DoD #12).

- class **TestRouteSmoke**: test_activities_200, test_activities_with_data_rendered, test_activities_export_csv_200, test_activities_export_csv_has_rows, test_activities_export_csv_distance_km, test_activities_filter_source, test_activities_filter_type, test_activities_pagination, test_merge_bad_ids_no_500, test_ungroup_missing_id_no_500
- functions: mini_app

### `test_format_ko.py` (37줄) — format_ko — Coach 규칙 답변 표기 단일 소스.

- functions: test_distance_pace_duration, test_signed_uses_unicode_minus, test_labels, test_sanitize_raw_floats_and_sec_per_km

### `test_garmin_activity_sync.py` (262줄) — DoD #6: Garmin activity sync 흐름 — mock API 기반.

- class **TestGarminActivitySync**: test_sync_empty_list, test_sync_one_activity, test_sync_skip_unchanged, test_sync_with_streams, test_sync_rate_limit_error, test_sync_detail_failure_continues, test_primary_resolution
- class **TestGarminLaps**: test_laps_saved_from_splits, test_splits_payload_stored, test_existing_activity_missing_splits_is_refetched, test_splits_failure_does_not_break_sync

### `test_garmin_auth_migration.py` (190줄) — garmin_auth.py garminconnect 0.3.x 마이그레이션 테스트.

- class **TestTokenstorePath**: test_default_path, test_explicit_path, test_user_id_path, test_user_id_email_sanitize, test_explicit_takes_precedence_over_user_id
- class **TestLogin**: test_no_token_file_raises, test_token_file_exists_calls_login, test_token_dump_called_on_success, test_429_propagated, test_auth_error_wraps_to_auth_required, test_generic_exception_wraps_to_auth_required
- class **TestCheckConnection**: test_no_tokenstore_dir, test_dir_exists_no_token_file, test_old_garth_token_detected, test_valid_token_with_access_token, test_valid_token_with_di_access_token, test_corrupted_token_json, test_token_missing_access_key

### `test_garmin_backfill.py` (225줄) — garmin_backfill.py 테스트 — Layer 0 저장 + 라우팅 검증.

- class **TestSaveZipMetrics**: test_routes_metric_fields_to_metric_store, test_skips_none_values
- class **TestBackfillFromZip**: test_insert_new_stores_raw_payload, test_insert_new_no_operationalerror_on_nondll_columns, test_insert_new_routes_metrics, test_update_filters_nondll_columns, test_update_links_raw_payload_to_activity

### `test_garmin_extractor.py` (323줄) — Garmin Extractor 단위 테스트.

- class **TestGarminActivityCore**: test_required_fields, test_distance_and_time, test_pace_calculated, test_heart_rate, test_training_effects_in_metrics, test_running_dynamics, test_location, test_no_none_values, test_source_url, test_empty_input_returns_minimal
- class **TestGarminActivityMetrics**: test_basic_metrics, test_no_empty_metrics, test_detail_hr_zones, test_detail_weather, test_no_core_duplicates
- class **TestGarminLaps**: test_lap_extraction, test_lap_pace_calculated, test_empty_detail
- class **TestGarminDataQualityGuards**: test_doubled_cadence_is_halved, test_normal_cadence_is_kept, test_missing_cadence_stays_none, test_lap_doubled_cadence_is_halved, test_negative_stress_is_ignored
- class **TestGarminWellness**: test_wellness_core, test_resting_hr_prefers_user_summary_over_sleep, test_resting_hr_falls_back_to_sleep_payload, test_missing_sleep_dto_yields_no_sleep_fields, test_body_battery_without_levels_is_skipped, test_wellness_metrics, test_wellness_metric_values, test_fitness
- class **TestGarminExtractorStreams**: test_basic_parsing, test_elapsed_sec_sequence, test_none_values_excluded, test_elapsed_sec_fallback_to_index, test_empty_descriptors_returns_empty, test_non_dict_input_returns_empty, test_temperature_prefers_air
- functions: ext, summary_raw, detail_raw, wellness_raw

### `test_garmin_lap_fields.py` (72줄) — P7-PRED-12: Garmin 랩 확장 필드·스트림 키 선택.

- functions: test_lap_extras_drops_none, test_pick_prefers_first_key_list_and_dict, test_extractor_uses_real_time_axis, test_laps_keep_gap_and_step, test_activity_gap_metric_sec_per_km, test_garmin_lap_extras_preserved, test_garmin_stream_uses_sum_elapsed_and_distance

### `test_garmin_local_sync_api.py` (556줄) — POST /api/garmin/local-sync 엔드포인트 테스트.

- class **TestGarminLocalSyncEndpoint**: test_returns_202_on_valid_token, test_missing_token_returns_400, test_empty_token_dict_returns_400, test_days_clamped_to_90, test_di_access_token_accepted, test_token_saved_to_disk, test_combined_token_saved_to_disk, test_combined_token_accepted, test_non_json_body_returns_400
- class **TestUploadTokenTriggerSync**: garmin_settings_app, test_upload_with_trigger_sync_redirects, test_paste_without_trigger_sync_no_bg_job, test_paste_with_trigger_sync_calls_redirect
- class **TestCfSettingsAndDownload**: garmin_app, test_cf_settings_saves_and_redirects, test_cf_settings_strips_header_prefix, test_cf_settings_missing_fields_returns_error_redirect, test_download_script_returns_python_file, test_download_env_contains_cf_values
- class **TestSyncKeyValidation**: test_valid_sync_key_returns_202, test_missing_sync_key_returns_401, test_wrong_sync_key_returns_401, test_no_cf_config_dev_allows_any_key, test_no_cf_config_production_returns_500
- class **TestAuthCfBypass**: test_local_sync_path_bypasses_auth, test_other_path_blocked_in_production

### `test_garmin_local_sync_script.py` (248줄) — scripts/garmin_local_sync.py 유닛 테스트.

- class **TestEnsureDeps**: test_skips_install_when_garminconnect_importable, test_installs_when_garminconnect_missing
- class **TestLoadDotenv**: test_loads_from_env_file, test_ignores_comments_and_blank_lines
- class **TestGarminLogin**: test_returns_token_dict_on_success, test_fresh_login_creates_token_file, test_exits_on_too_many_requests
- class **TestUploadToken**: test_posts_json_with_cf_headers, test_exits_on_401
- class **TestTokenOnlyMode**: test_saves_token_locally

### `test_garmin_ref_parsers.py` (43줄) — P7-PRED-25: Garmin 참조값 파서.

- functions: test_lt_latest_shape, test_lt_history_list_and_garbage, test_race_predictions_latest_and_history, test_lt_history_dict_shape

### `test_garmin_ref_sync.py` (69줄) — P7-PRED-25: Garmin 참조값 동기화(가짜 클라이언트).

- class **FakeClient**: get_lactate_threshold, get_race_predictions
- class **WindowClient**: get_race_predictions, get_lactate_threshold
- functions: test_snapshots, test_history_and_failure, test_history_is_split_into_windows

### `test_garmin_wellness_sync.py` (151줄) — DoD #7: Garmin wellness sync 6 endpoint — mock API 기반.

- class **TestGarminWellnessSync**: test_sync_one_day, test_resync_updates_partial_day_values, test_sync_multi_day, test_sync_skip_unchanged, test_sync_stores_raw_payloads, test_sync_metrics_created, test_sync_partial_endpoint_failure

### `test_goal_reported_load.py` (27줄) — v28: 목표 생성 시 사용자 입력 시작 부하(최근 주간 km·최장 롱런 km).

- functions: test_reported_load_roundtrip_and_default_none, test_v28_migration_idempotent_and_missing_column_safe

### `test_goal_rules_version.py` (57줄) — U16e: 목표별 계획 규칙 버전 고정·플래그·마이그레이션.

- functions: test_schema_version_and_default_one, test_flag_on_new_goal_is_v2_and_existing_stays_v1, test_explicit_version_and_downgrade, test_migration_adds_column_to_legacy_goals_idempotent, test_get_rules_version_missing_goal_is_one

### `test_goals.py` (116줄) — goals.py 테스트.

- functions: test_add_goal_returns_id, test_get_goal, test_get_goal_not_found, test_list_goals_active_default, test_list_goals_all, test_get_active_goal_returns_latest, test_get_active_goal_none_when_empty, test_update_goal, test_update_goal_invalid_field, test_complete_goal, test_cancel_goal, test_complete_nonexistent_goal, test_cancel_nonexistent_goal, test_list_goals_empty, test_add_goal_minimal

### `test_group_once.py` (62줄) — tests/test_group_once.py — activity 계산 그룹당 1회·그룹 입력 병합(21 design §7.3 C3, DECISIONS D10).

- functions: test_copy_id_is_computed_on_canonical_only, test_stale_copy_rows_pruned, test_group_streams_and_metric_filled_from_sibling

### `test_heat_model.py` (25줄) — P7-PRED-33: 기온 계수 적합 + 수축.

- functions: test_ols_exact, test_few_points_returns_default, test_shrinkage_toward_truth

### `test_hr_profile.py` (45줄) — P7-PRED-24: HR 프로필 자체 추정 + 참조값.

- functions: test_second_part_hr, test_self_profile_from_race, test_fallback_and_ref

### `test_initial_load_cli.py` (219줄) — initial-load CLI 테스트.

- class **TestParseSteps**: test_all_steps, test_subset, test_dedup_and_sort, test_whitespace_tolerance, test_invalid_exits
- class **TestArgparse**: test_defaults, test_custom_flags
- class **TestDryRun**: test_dry_run_no_db_changes, test_step_subset_executes_only_requested
- class **TestStepDedup**: test_dedup_sets_group_id, test_dedup_dry_run_no_groups

### `test_integration_realdb.py` (1194줄) — 실 데이터(pansongit@gmail.com) 기반 통합 테스트.

- class **TestRawActivitySummaries**: test_distance_m_range, test_elapsed_time_range, test_avg_pace_running_only, test_hr_range, test_elevation_nonneg, test_source_valid, test_timestamp_iso, test_no_duplicate_source_ids
- class **TestRawWellness**: test_sleep_score_range, test_sleep_duration_range, test_hrv_range, test_resting_hr_range, test_body_battery_range, test_stress_range, test_weight_range, test_no_duplicate_dates
- class **TestRawMetricStore**: test_ctl_atl_range, test_tsb_range, test_acwr_range, test_vo2max_range, test_training_load_range, test_hr_zone_sec_range, test_is_primary_uniqueness
- class **TestRawActivityStreams**: test_heart_rate_range, test_cadence_range, test_speed_ms_range, test_altitude_range, test_lat_lon_bounds
- class **TestRawCanonicalView**: test_no_source_id_dupes, test_canonical_lte_summaries, test_valid_sources, test_distance_range
- class **TestTrendsRangesReal**: test_weekly_distances_in_km, test_weekly_pace_running, test_fitness_ctl_atl_range, test_fitness_tsb_range, test_nonzero_weeks_count
- class **TestCompareRangesReal**: test_compare_periods_keys, test_compare_periods_delta_math, test_compare_this_week_vs_last, test_compare_today_vs_yesterday, test_compare_this_month_vs_last
- class **TestWeeklyScoreRangesReal**: test_score_range, test_grade_valid, test_components_non_negative
- class **TestRaceReadinessRangesReal**: test_readiness_score_range, test_grade_valid, test_predictions_range, test_component_scores_range, test_vdot_race_predictions
- class **TestActivityDeepRangesReal**: recent_run_ids, test_structure_keys, test_pace_format_or_none, test_distance_km_unit, test_hr_in_range
- class **TestEfficiencyRangesReal**: run_with_streams_id, test_calculate_efficiency_structure, test_decoupling_pct_range, test_efficiency_trend_structure, test_efficiency_trend_ef_values
- class **TestRecoveryRangesReal**: test_recovery_status_always_dict, test_recovery_score_range, test_recovery_grade_valid, test_recovery_trend_structure
- class **TestZonesRangesReal**: test_analyze_zones_structure, test_zone_pct_sums, test_weekly_zone_trend_length, test_weekly_zone_trend_pct_range
- class **TestSuggestionsRangesReal**: test_acwr_status_valid, test_weekly_run_count_plausible, test_chips_count_range, test_chips_keys, test_no_exception
- class **TestDashboardRangesReal**: dashboard, test_required_keys, test_training_phase_valid, test_weekly_summary_non_negative, test_ctl_when_present, test_pmc_chart_sorted, test_pmc_chart_values, test_daily_metric_chart
- class **TestWellnessRangesReal**: test_detail_is_dict, test_hrv_range, test_resting_hr_range, test_sleep_score_range, test_trend_arrays_same_length
- class **TestActivityServiceRangesReal**: test_list_pagination, test_list_distance_km, test_detail_structure, test_filter_sport, test_streams_values
- class **TestUnifiedViewRangesReal**: unified_page, test_pagination, test_distance_km_range, test_meta_keys, test_source_comparison
- class **TestDedupIntegrity**: test_group_source_uniqueness, test_canonical_ratio_plausible, test_no_orphan_canonical
- class **TestExportRangesReal**: test_distance_km_from_canonical, test_pace_conversion_plausible
- class **TestAllActivitySummaryColumns**: test_column_range
- class **TestAllWellnessColumns**: test_column_range, test_sleep_start_time_exists
- class **TestAllMetricStoreRanges**: test_metric_range
- class **TestAllLapsRanges**: has_laps, test_laps_table_has_data, test_lap_distance_m_range, test_lap_duration_sec_range, test_lap_avg_hr_range, test_lap_avg_pace_running
- class **TestAllBestEffortsRanges**: has_efforts, test_efforts_table_has_data, test_effort_distance_m_range, test_effort_elapsed_time_range, test_effort_implied_pace_running
- functions: real_conn

### `test_intervals_extractor.py` (88줄) — Intervals.icu Extractor 단위 테스트.

- class **TestIntervalsActivityCore**: test_required_fields, test_distance_time, test_stride_length_converted, test_training_load_in_metrics
- class **TestIntervalsActivityMetrics**: test_training_metrics, test_hr_zones, test_metric_values
- class **TestIntervalsWellness**: test_wellness_core, test_fitness
- functions: ext, activity_raw, wellness_raw

### `test_intervals_sync.py` (156줄) — DoD #9: Intervals.icu activity + wellness sync — mock 기반.

- class **TestIntervalsActivitySync**: test_sync_one_activity, test_sync_empty, test_sync_skip_unchanged, test_sync_no_credentials
- class **TestIntervalsWellnessSync**: test_wellness_sync, test_wellness_skip_unchanged, test_wellness_fitness_stored

### `test_long_run_rules.py` (92줄) — U16-LR L1: 롱런 하한·상한 순수 규칙 — 설계서 §8.1 경계값 표(#1~#17).

- functions: ctx, test_floor_boundaries, test_floor_uses_long12_basis, test_half_base_low_volume_week_has_no_long, test_cap_boundaries, test_share_ratio_by_days, test_min_viable_week_km, test_floor_never_exceeds_cap, test_prog_cap_only_with_prev_long, test_budget_full_build_moves_mp_into_long, test_budget_relaxes_floor_before_dropping_long, test_budget_floor_matches_recorded_ctx, test_feasible_week_km_monotone_and_full_peak_share

### `test_marathon_rules.py` (43줄) — U16g: R6 MP 규칙(순수 함수).

- functions: test_prescribed_mp_without_goal_and_data, test_prescribed_mp_weekly_progress, test_prescribed_mp_capped_by_12s_and_goal, test_long_run_pace_clamped, test_long_mp_share_by_phase, test_taper_week1_mp_range, test_race_week_session

### `test_marathon_shape.py` (93줄)

- class **TestMarathonShape**: test_with_data, test_no_vdot, test_goal_basis_and_unreachable
- functions: test_tanda_required_roundtrip

### `test_marathon_types_wiring.py` (56줄) — U16h: marathon·long_mp 유형 배선(스키마 CHECK·구조·판정·매처·라벨·푸시).

- functions: test_fresh_schema_accepts_new_types, test_v27_rebuild_keeps_rows_columns_and_indexes, test_marathon_structure_and_outcome_on_target, test_long_mp_structure_is_max_only, test_matcher_and_labels

### `test_mcp_server.py` (124줄) — MCP 서버 — DB 결정, 읽기 전용, stdio 프레임, 프로토콜 응답.

- class **TestResolveDbPath**: test_requires_user_id, test_blank_user_id_is_rejected, test_path_traversal_is_rejected, test_unknown_user_raises_and_creates_no_directory, test_env_var_is_used
- class **TestReadOnly**: test_connection_rejects_writes
- class **TestFraming**: test_write_is_single_line_with_no_padding, test_read_skips_blank_lines_and_returns_none_at_eof
- class **TestProtocol**: test_initialize_carries_usage_guide, test_tools_list_matches_declarations, test_notification_gets_no_response, test_ping, test_unknown_method_is_error, test_tool_call_success, test_unknown_tool_flags_is_error, test_missing_arguments_key_is_tolerated, test_missing_db_is_reported_as_tool_error_not_crash
- functions: db_path

### `test_metric_bands.py` (46줄) — tests/test_metric_bands.py — 등급 밴드 SSOT(src/metrics/bands.py).

- functions: test_tsb_conventional_bands, test_tsb_race_phase_overrides, test_cirs_lower_is_better, test_decoupling_uses_absolute_value, test_unknown_or_missing_returns_none, test_utrs_bands_match_calculator_ranges, test_rri_bands

### `test_metric_browse_groups.py` (64줄) — tests/test_metric_browse_groups.py — 메트릭 브라우저 8의도 그룹 매핑·정렬 단위 테스트.

- functions: test_every_daily_slug_is_mapped, test_no_mapping_key_outside_daily, test_groups_are_known, test_unknown_slug_goes_to_other_detail, test_baseline_z_null_under_7_days, test_baseline_z_null_when_not_fresh, test_baseline_z_sd_zero_uses_floor, test_fresh_before_stale, test_caution_before_big_z_neutral, test_z_null_goes_last_among_same_status, test_tie_then_tier_then_registry

### `test_metric_labels.py` (100줄) — metric_labels SSOT 일관성 + 지표가 이름 때문에 사라지지 않음 검증 (ADR-018).

- functions: test_keys_subset_of_registry, test_all_daily_metrics_registered, test_label_shape, test_no_duplicate_name_ko_within_category, test_core_terms_pinned, test_fallback_strips_parent_and_uses_name_last, test_every_registry_metric_has_displayable_name, test_first_batch_has_description_short, test_texts_within_40_chars, test_action_hint_keys_are_five_level_status, test_action_hint_picks_current_status_only, test_crs_hint_uses_gate_level_not_score_status, test_marathon_shape_label_and_new_texts

### `test_metric_naming.py` (59줄) — 메트릭 이름 충돌 방지 검증 테스트 (보강 #9).

- class **TestMetricNaming**: test_no_calculator_uses_activity_summary_column_name, test_no_duplicate_produces_across_calculators, test_all_produces_are_non_empty, test_all_names_are_unique

### `test_metric_priority.py` (100줄) — metric_priority.py 단위 테스트 — Phase 1 조건 7

- class **TestProviderPriority**: test_user_highest, test_garmin_before_strava, test_runpulse_ml_before_garmin, test_unknown_provider_low_priority
- class **TestResolvePrimary**: test_single_provider, test_multi_provider_garmin_wins, test_user_override_wins, test_resolve_for_scope
- functions: db

### `test_metric_registry.py` (74줄) — metric_registry.py 단위 테스트 — Phase 1 조건 5, 6

- class **TestMetricDefinitions**: test_metric_count_minimum, test_no_alias_collision, test_all_metrics_have_category, test_all_metrics_have_unit, test_categories_non_empty
- class **TestCanonicalize**: test_canonical_name_returns_itself, test_alias_resolves, test_unknown_returns_none_or_input, test_get_metric_returns_metric_def
- functions: test_definitions_split_modules_cover_registry_in_order

### `test_metrics_basis_events.py` (43줄)

- functions: test_id_change_gives_one_event, test_no_change_and_missing_key_and_other_slug, test_load_json_tolerates_bad_input

### `test_metrics_browser_service.py` (310줄) — tests/test_metrics_browser_service.py — metrics_browser_service 단위 테스트.

- functions: conn, test_get_metrics_browser_structure, test_get_metrics_browser_no_empty_categories, test_get_metrics_browser_entry_fields, test_get_metrics_browser_auto_date, test_get_metric_trend_returns_data, test_get_metric_trend_unknown_returns_none, test_get_metric_trend_invalid_period_falls_back, test_sparkline_matches_batched_history_over_multiple_days, test_get_metric_trend_peak_and_change_pct, test_confidence_label_thresholds, test_change_and_baseline_helpers, test_browser_entries_have_meta, test_display_meta_dispatch, test_display_name_strips_parent_and_maps_core, test_label_registry_does_not_affect_which_metrics_are_listed, test_wellness_stored_metrics_are_listed, test_metric_without_value_on_base_date_uses_latest_in_window, test_metric_older_than_window_is_dropped, test_trend_reads_wellness_column, test_band_ranges_cover_axis_without_gaps, test_display_meta_min_span, test_race_events_filters_by_window, test_browser_groups_hide_components_and_sort, test_flat_kind_distinguishes_fixed_and_uncomputed, test_load_headline_is_none_on_empty_db, test_display_meta_description_and_action_hint, test_crs_level_reads_gate_level

### `test_metrics_explain.py` (268줄) — tests/test_metrics_explain.py — get_metric_explain() 분해 v2(explain=1) 테스트.

- class **TestUnsupportedSlug**: test_returns_none_for_slug_without_explainer, test_returns_none_for_no_data
- class **TestTSBExplain**: test_terms_have_ctl_and_atl_with_opposite_signs, test_formula_text_and_bands_present
- class **TestPMCExplain**: test_ctl_terms_have_prev_and_today_load, test_atl_alpha_is_one_seventh
- class **TestUTRSExplain**: test_terms_have_contribution_and_loss, test_contributions_sum_to_score, test_terms_have_trend_drill, test_sources_is_wellness_day
- class **TestCIRSExplain**: test_terms_have_contribution_no_loss, test_higher_is_better_false, test_terms_sorted_by_contribution_desc
- class **TestRRIExplain**: test_terms_use_factor_role_and_ratio, test_higher_is_better_true, test_sources_reference_component_metrics
- class **TestConclusion**: test_utrs_top_loss, test_cirs_top_contribution, test_rri_lowest_ratio, test_none_cases, test_explain_includes_conclusion_for_utrs
- class **TestPersonalText**: test_higher_lower_and_none
- functions: test_activity_scope_trimp_explain, test_activity_scope_unsupported_slug_and_missing_activity, test_prediction_explain_evidence_and_sources, test_prediction_explain_omits_missing_fields

### `test_metrics_explain_whatif.py` (33줄) — what-if(B-5) 순수 함수 테스트.

- functions: test_tsb_one_step_formula, test_utrs_only_tsb_term_changes, test_past_date_omitted

### `test_metrics_service.py` (145줄) — tests/test_metrics_service.py — get_metric_breakdown() 통합 테스트.

- class **TestGetMetricBreakdownNoneCase**: test_returns_none_for_unknown_slug, test_returns_none_for_no_data
- class **TestGetMetricBreakdownChildren**: test_ctl_has_ramp_rate_child, test_children_have_required_fields
- class **TestGetMetricBreakdownInputs**: test_rri_inputs_include_cirs, test_metric_without_calculator_has_empty_inputs
- class **TestGetMetricBreakdownStructure**: test_top_level_keys, test_utrs_children

### `test_metrics_version_events.py` (47줄)

- functions: test_mixed_versions_give_one_event, test_provider_switch_gives_one_event, test_single_version_and_no_data, test_recompute_note_present_and_absent

### `test_milestone_service.py` (355줄) — tests/test_milestone_service.py — milestone_service 단위 테스트.

- class **TestDistanceThreshold**: test_100km_created_on_crossing, test_multiple_thresholds_crossed, test_no_duplicate_on_second_call
- class **TestPB**: test_pb_created_when_faster, test_no_pb_when_slower, test_no_pb_for_first_race, test_pb_no_duplicate, test_pb_race_keyword_detection
- class **TestMetricRecompute**: test_recompute_milestone_created_on_version_change, test_no_recompute_below_threshold, test_no_recompute_for_non_allowlist_metric
- class **TestGetRecentMilestones**: test_returns_empty_when_no_milestones, test_returns_ordered_by_date_desc, test_limit_respected, test_date_range_filters, test_no_date_range_returns_all
- functions: test_present_merges_prediction_updates_and_humanizes, test_recompute_kinds_are_stored_for_ab_but_only_data_changes_are_shown, test_v22_reclassifies_old_version_change_rows

### `test_mock_calcs.py` (127줄) — MockCalcContext를 활용한 calculator 단위 테스트 (보강 #5).

- class **TestTRIMPMock**: test_basic, test_no_hr, test_short_duration
- class **TestHRSSMock**: test_with_trimp, test_no_trimp
- class **TestEFMock**: test_basic, test_no_hr
- class **TestVDOTMock**: test_10k, test_non_running
- class **TestConfidenceBuilder**: test_all_available, test_partial_available, test_estimated_penalty, test_empty, test_mixed

### `test_narrative_cache.py` (153줄) — tests/test_narrative_cache.py — get_today_narrative() ai_cache 연동 테스트.

- class **TestNarrativeCacheHelpers**: test_cache_miss_returns_none, test_set_then_get_roundtrip, test_different_keys_do_not_collide, test_set_cache_failure_is_swallowed
- class **TestGetTodayNarrativeCache**: test_rule_fallback_not_cached, test_ai_result_is_cached, test_cache_hit_skips_ai_call, test_cache_hit_returns_cached_text, test_past_month_uses_correct_cache_key, test_stale_cache_on_new_activity_triggers_ai, test_cache_save_failure_does_not_raise
- class **TestFingerprintRecompute**: test_fingerprint_changes_on_ctl_recompute, test_fingerprint_ignores_other_metrics

### `test_narrative_warm.py` (47줄) — tests/test_narrative_warm.py — 내러티브 워밍 가드·반환값 검증.

- functions: test_no_consent_skips_llm, test_warmed_and_counts_call, test_rule_fallback_is_failed, test_exception_is_failed_and_no_cache_row, test_capped_after_daily_limit, test_fresh_cache_skips

### `test_orchestrator.py` (115줄) — DoD #11: orchestrator.full_sync + sync_jobs 기록.

- class **TestFullSync**: test_no_clients_all_skipped, test_garmin_sync_records_job, test_multi_source_sync, test_dedup_runs_after_sync, test_sync_jobs_have_dates

### `test_outcome_store.py` (38줄) — P7-PRED-43: 매칭 → 세그먼트 이행률 저장.

- functions: test_structured_plan_gets_compliance, test_unstructured_plan_keeps_legacy_label

### `test_outcome_v2.py` (45줄) — P7-PRED-42: 계획↔실행 세그먼트 비교.

- functions: test_expand, test_full_on_target, test_five_of_six_sets, test_slow_and_short, test_fast, test_skipped_and_note

### `test_pace.py` (74줄) — pace 유틸리티 테스트.

- class **TestSecondsToPace**: test_even_minutes, test_with_seconds, test_single_digit_seconds, test_fast_pace
- class **TestPaceToSeconds**: test_even_minutes, test_with_seconds, test_roundtrip
- class **TestKmhToPace**: test_12kmh, test_10kmh, test_zero_raises
- class **TestPaceToKmh**: test_300sec, test_360sec, test_zero_raises
- class **TestFormatDuration**: test_under_hour, test_over_hour, test_zero, test_exact_hour

### `test_periodization.py` (130줄) — 목표 대회 역산 주기화.

- functions: test_last_week_is_race_week_and_taper_comes_last, test_ramp_is_capped_and_peak_week_is_not_recovery, test_long_run_progresses_then_tapers_off, test_taper_volume_falls_below_peak, test_short_or_invalid_inputs, test_v2_full_taper_is_two_weeks_with_d14_long, test_v2_three_week_taper_only_for_long_high_volume_plans, test_v1_unchanged_by_rules_version, test_v2_low_volume_ramp_never_exceeds_ten_percent, test_v2_long_progresses_from_capped_value, test_v2_d14_long_respects_shared_cap, test_schedule_for_goal_uses_goal_rules_version, test_build_schedule_max_week_km_caps_volume

### `test_personalize.py` (37줄)

- functions: test_is_comeback_boundaries, test_comeback_ceiling, test_next_level_ramp, test_start_long_km, test_schedule_comeback_ramps_faster_and_v1_unchanged

### `test_phase1_schema.py` (756줄) — Phase 1 스키마 & 기반 인프라 테스트.

- class **TestSchemaCreation**: test_all_pipeline_tables_exist, test_all_app_tables_exist, test_canonical_view_exists, test_schema_version, test_activity_summaries_column_count, test_distance_is_meters_not_km, test_metric_store_columns, test_daily_wellness_no_source_column
- class **TestConstraints**: test_activity_summaries_unique, test_metric_store_unique, test_metric_store_same_name_different_provider, test_daily_wellness_unique_date
- class **TestCanonicalView**: test_canonical_returns_one_per_group, test_canonical_prefers_garmin, test_canonical_intervals_second_priority
- class **TestMetricRegistry**: test_registry_size, test_canonicalize_garmin_alias, test_canonicalize_intervals_trimp, test_canonicalize_direct_name, test_canonicalize_unmapped, test_get_metric_exists, test_get_metric_not_exists, test_list_by_category, test_list_by_scope, test_all_categories_documented
- class **TestMetricPriority**: test_user_highest_priority, test_runpulse_ml_higher_than_formula, test_runpulse_higher_than_garmin, test_garmin_higher_than_strava, test_unknown_provider, test_resolve_primary_basic, test_user_override, test_resolve_for_scope
- class **TestDbHelpers**: test_upsert_payload_new, test_upsert_payload_unchanged, test_upsert_payload_changed, test_get_payload, test_upsert_activity, test_upsert_activity_update, test_upsert_metric_and_get_primary, test_upsert_metrics_batch, test_get_all_providers, test_get_metrics_by_category, test_upsert_daily_wellness_merge, test_get_db_status, test_get_activity_list
- class **TestMigration**: test_migrate_idempotent, test_create_tables_idempotent
- class **TestPerformance**: test_activity_list_under_200ms, test_metric_store_bulk_insert
- class **TestRealDbDefault**: test_existing_tables, test_migrate_creates_new_tables, test_existing_data_preserved, test_schema_version_updated
- class **TestRealDbUser**: test_has_real_data, test_migrate_preserves_data, test_migrate_adds_metric_store, test_source_payloads_exist, test_source_distribution, test_canonical_view_after_migrate, test_daily_wellness_has_data, test_db_summary

### `test_phase4_dod.py` (326줄) — Phase 4 DoD (Definition of Done) 검증 테스트 — 설계서 4-8 기준.

- class **TestDoD1**: test_19_calculators, test_calculator_names
- class **TestDoD2**: test_full_chain
- class **TestDoD3**: test_recompute_recent_no_error
- class **TestDoD4**: test_runpulse_provider_exists
- class **TestDoD5**: test_min_3_metrics_per_activity
- class **TestDoD6**: test_min_4_daily_metrics
- class **TestDoD7**: test_idempotent_recompute
- class **TestDoD8**: test_source_metrics_preserved
- class **TestDoD9**: test_utrs_confidence, test_cirs_confidence, test_fearp_confidence
- class **TestDoD10**: test_workout_type_json, test_rmr_json, test_tids_json

### `test_phase4_spec.py` (271줄) — Phase 4-6 설계서 테스트 계획 – 누락 케이스 구현

- class **TestTRIMPMissingDuration**: test_zero_duration_returns_empty, test_null_duration_returns_empty
- class **TestPMCBehavior**: test_ctl_increases_with_training, test_tsb_negative_after_hard_training, test_tsb_positive_after_rest
- class **TestUTRSPartialInputs**: test_partial_inputs_confidence_below_1
- class **TestCIRSScenarios**: test_high_acwr_produces_high_cirs, test_optimal_acwr_produces_low_cirs
- class **TestCircularDependency**: test_circular_dependency_does_not_crash

### `test_plan_backtest.py` (102줄)

- functions: test_rest_mask_leaves_requested_days, test_grid_size, test_cold_grid_scenario_passes_gates, test_v1_full_plan_fails_marathon_gates, test_deterministic, test_summarize_counts, test_history_scenarios_from_seeded_db, test_v1_output_snapshot_protects_existing_goals, test_v1_output_snapshot_full_and_cold, test_seed_grid_history_matches_start_load, test_engine_v2_grid_passes_gates

### `test_plan_creation.py` (67줄) — 목표 대회 역산 계획 생성 — 시작·기간·볼륨 진행.

- functions: test_plan_start_monday, test_recent_load_reads_history, test_created_plan_follows_periodization_and_ends_on_race, test_shorter_plan_starts_in_future_and_week_index_is_zero_before_start

### `test_plan_gates.py` (145줄)

- functions: wk, test_g1, test_g2a_boundary_uses_recorded_ctx, test_g2a_flags_ctx_mismatch, test_g2b_envelope_boundary, test_g9_floor_boundary, test_g9_no_long_week_and_taper_exempt, test_f6_long_step, test_g3, test_g4, test_g5, test_g6_boundary, test_g6_week1_cold_exception, test_g7, test_g8, test_soft_gates

### `test_plan_ingest.py` (127줄) — 외부 계획 인제스트(P7-PRED-44) — Garmin 실측 응답 형태(2026-09-26) 기반 파서·저장·이행률.

- class **FakeClient**: get_workout_by_id
- functions: test_parse_garmin_workout_structure_and_unknown_step_skipped, test_parse_adaptive_task_and_rest_day, test_parse_intervals_event_real_shapes, test_ingest_intervals_links_paired_activity, test_store_planned_upsert_keeps_runpulse_rows, test_ingest_garmin_executed_links_by_workout_id_and_skips_deleted

### `test_plan_match_rules.py` (200줄) — A1/A2: 대회일 기준 계획 기간·단계, 매칭 배타·호환 규칙, 결과 라벨, 연속 러닝 이행률.

- functions: test_plan_weeks_until_race_counts_both_ends, test_weeks_to_race_is_relative_to_as_of, test_phase_differs_by_week_and_race_week_is_built, test_apply_race_week_rests_after_race, test_create_plan_is_clamped_to_race_week, test_templates_are_capped_by_race_date, test_pick_activity_skips_claimed_and_incompatible, test_classify_outcome_prioritises_distance, test_matcher_does_not_steal_activity_claimed_by_external_plan, test_matcher_partial_run_is_linked_but_not_completed, test_continuous_plan_outcome_uses_duration, test_continuous_garmin_plan_is_not_marked_skipped_when_executed, test_rematch_resets_wrong_completion_and_replan_trims_after_race, test_taper_wins_over_recovery_week, test_plan_structure_for_each_workout_type, test_easy_run_too_fast_is_modified_not_on_target, test_matcher_rejects_hard_session_for_easy_plan_and_uses_set_analysis, test_adjustment_skips_day_already_executed

### `test_plan_readiness.py` (69줄) — 준비 볼륨·경고(DESIGN-U16-LONGRUN §5.2-5)와 콜드 피크 목표(§5.2 L5 후속).

- functions: test_ready_and_cold_peak_km_by_distance, test_readiness_warning_ramp_message, test_readiness_warning_none_when_reached_or_empty, test_readiness_warning_days_cap_message, test_cold_v2_peak_aims_at_ready_volume_with_ramp_kept, test_plan_warnings_cold_full_short_plan, test_plan_warnings_uses_reported_load

### `test_plan_service.py` (214줄) — tests/test_plan_service.py — plan_service 단위 테스트.

- functions: conn, test_get_active_plan_no_goal_returns_none, test_get_active_plan_returns_structure, test_get_active_plan_by_goal_id, test_get_active_plan_by_invalid_goal_id_returns_none, test_compliance_pct_with_mixed_workouts, test_compliance_pct_ignores_prior_goal_leftovers, test_week_index_ignores_prior_goal_leftovers, test_get_todays_adjustment_no_plan_returns_none, test_get_todays_adjustment_with_plan, test_get_session_detail_existing_date, test_get_session_detail_missing_date_returns_none, test_get_session_detail_invalid_goal_id_returns_none, test_get_session_note_empty, test_save_session_note_and_retrieve, test_save_session_note_upsert, test_active_plan_next_session_skips_done_and_superseded

### `test_plan_template_service.py` (145줄) — tests/test_plan_template_service.py — get_static_plan_templates + create_plan_from_template 단위 테스트.

- functions: conn, test_templates_with_target_time_sec, test_templates_completion_with_vdot, test_templates_completion_no_vdot, test_templates_dedup_weeks, test_templates_risk_level_mapping, test_create_plan_inserts_goal, test_create_plan_fills_planned_workouts, test_create_plan_no_race_date, test_create_plan_custom_name, test_create_plan_respects_weeks_not_race_date

### `test_planner_as_of.py` (20줄)

- functions: test_as_of_passthrough_and_default

### `test_planner_config_as_of.py` (37줄) — planner_config 조회 헬퍼의 as_of 시점 고정(U16a).

- functions: test_default_reads_latest, test_as_of_cuts_future_values, test_as_of_before_data_is_empty

### `test_planner_schedule_cold.py` (65줄) — v2 콜드스타트 시작 부하(DESIGN-U16-LONGRUN §5.2).

- functions: test_cold_start_km_sources, test_cold_start_km_week1_limited_by_history, test_recent_avg_km, test_start_load_cold_only_for_v2, test_schedule_for_goal_cold_v2_not_empty_v1_empty, test_start_load_uses_reported_load_only_when_cold, test_week_cap_km_v2_only

### `test_planner_v2.py` (126줄) — planner_v2 후처리 단위 테스트(순수 함수).

- functions: test_rebalance_trims_easy_then_long, test_rebalance_grow_never_drops_km, test_rebalance_grows_easy, test_shakeout_sets_eve_row, test_shakeout_fits_low_volume_race_week, test_note_cold_start_adds_source_to_rationale, test_mp_session_retypes_longest_quality, test_race_week_adds_mp_session, test_apply_v2_full_build_has_mp_and_no_input_mutation, test_apply_v2_half_has_no_mp, test_apply_v2_low_volume_week_has_no_long, test_apply_v2_full_build_low_budget_mp_inside_long, test_apply_v2_preserves_weekly_total, test_apply_for_goal_without_target_returns_rows

### `test_pmc.py` (82줄) — PMC (Performance Management Chart) 단위 테스트 — 설계서 4-6.

- class **TestPMC**: test_produces_four_metrics, test_ctl_increases_with_training, test_tsb_negative_after_hard_training, test_no_data, test_ramp_rate_has_parent_metric_name_ctl

### `test_pmc_intraday.py` (90줄) — PMC 오늘 부분일 처리 + 오늘 메트릭 지연 갱신 테스트.

- functions: test_elapsed_day_fraction, test_today_rest_decay_is_prorated, test_today_actual_load_counts_fully, test_refresh_today_if_stale

### `test_pmc_trimp_v2.py` (62줄) — tests/test_pmc_trimp_v2.py — 부하 모델 재기준화(DECISIONS [P7-UX-REVIEW-0928] D1·D2) 회귀 테스트.

- functions: test_rest_day_decays_ctl_by_one_over_tau, test_long_window_reaches_steady_state, test_no_load_returns_empty, test_trimp_banister_coefficients

### `test_pred_backtest.py` (19줄) — P7-PRED-62: 수용 백테스트 스크립트 — 대회 없음이면 n=0.

- functions: test_no_races

### `test_pred_schema_v20.py` (46줄) — P7-PRED-11: 스키마 v20 컬럼·race_results·session_outcomes 유일 제약.

- functions: test_v20_columns_exist_after_create, test_ensure_v20_idempotent, test_migrate_from_19_adds_columns, test_session_outcomes_unique_planned_id

### `test_prediction_compare.py` (68줄) — P7-PRED-71: 3경로 비교 서비스.

- functions: test_three_rows_and_notes, test_missing_paths, test_race_hub_includes_compare, test_profile_reads_latest, test_shadow_candidates_only_when_present

### `test_prediction_core.py` (72줄)

- functions: test_vdot_roundtrip, test_temp, test_anchor_decay, test_best_block, test_combine, test_k_personal, test_convert_equals_daniels_at_k0, test_marathon, test_confidence_and_range, test_hr_profile, test_weather

### `test_prediction_core_r4.py` (84줄) — P7-PRED-20·22: Daniels 공식·강도 역산, 칼만 결합, 예측 코어(r4).

- functions: test_daniels_formula_and_zones, test_set_zone_and_equivalent_minutes, test_temp, test_k_personal_disjoint_pairs, test_distance_extrapolation, test_quality_multiplier, test_kalman_weights_and_add, test_summary_and_marathon, test_hr_profile_and_weather_helpers, test_kalman_low_mult_weakens_low_observations

### `test_prediction_signals.py` (36줄) — P7-PRED-22: 예측 신호(순수).

- functions: test_allout_rules, test_tanda_inputs, test_spread_pct

### `test_prediction_signals_r4.py` (55줄) — P7-PRED-22: 예측 관측 생성(순수, r4).

- functions: test_allout_rules, test_set_observation_device_free, test_observations_and_inputs

### `test_prediction_snapshot.py` (64줄) — P7-PRED-63: 예측 스냅샷 기록·중복 억제·대회 전향 평가·요약.

- functions: test_record_only_today_and_dedupe, test_garmin_uses_recent_value_only, test_evaluate_on_confirm, test_not_allout_not_evaluated

### `test_progression.py` (37줄) — U16l: 품질 사다리 순수 함수·v29 테이블·저장 서비스.

- functions: test_next_step_up_hold_down_and_clamp, test_prescription_shapes, test_service_persists_and_migration_idempotent

### `test_provider_common.py` (118줄) — provider 오류 구조화(30-coach-chat design §6.2) — HTTP 상태→reason 매핑, 모델 ID 설정화, 타임아웃.

- class **_Resp**: json
- functions: test_status_maps_to_reason, test_429_is_rate_limit_error, test_timeout_maps_to_timeout, test_no_key_and_empty_response, test_success_uses_config_model_only, test_deadline_exhausted_raises_timeout, test_legacy_call_keeps_string_contract, test_tool_loop_executes_tool_then_answers, test_complete_counts_tool_calls_in_stats

### `test_provider_comparison_service.py` (301줄) — tests/test_provider_comparison_service.py — provider_comparison_service 단위 테스트.

- functions: two_source_conn, solo_conn, test_unknown_activity_returns_none, test_solo_activity_returns_single_provider, test_two_source_returns_loaded, test_avg_hr_raw_metric_present, test_avg_hr_no_discrepancy, test_discrepancy_warning_triggered, test_preferred_provider_uses_primary_source, test_runpulse_only_metric_gets_runpulse_always, test_semantic_training_load_flattened_to_one_row, test_missing_provider_cell_available_false, test_all_none_raw_column_skipped, test_runpulse_value_only_from_canonical_row, test_related_group_has_no_discrepancy, test_training_load_row_marked_scale_and_includes_intervals

### `test_provider_diff.py` (30줄) — tests/test_provider_diff.py — 소스 비교 항목별 임계·정규화(UX 리뷰 20 F-DATA-03).

- functions: test_small_elevation_gap_is_not_significant, test_temperature_uses_absolute_threshold, test_duration_one_percent, test_single_leg_cadence_normalized, test_different_quantities_not_compared

### `test_provider_matrix_service.py` (146줄) — tests/test_provider_matrix_service.py — S6 소스 비교 매트릭스/쌍 서비스 단위 테스트.

- functions: test_empty_db_no_data, test_scale_row_has_ratio_and_no_warning, test_fewer_than_three_pairs_insufficient, test_non_running_excluded, test_summarize_same_threshold, test_cell_summary_stale, test_pairs_outlier_and_unknown_group, test_row_definitions_sane

### `test_provider_status.py` (154줄) — provider_status_service.get_provider_status() 단위 테스트.

- functions: test_empty_db_returns_four_providers, test_empty_db_has_data_false, test_garmin_activity_sets_has_data, test_activity_count_aggregates_correctly, test_last_synced_at_from_source_payloads, test_last_synced_at_none_when_no_payload, test_provider_order_fixed, test_unknown_source_not_in_result, test_payload_only_provider_has_data, api_client, test_api_providers_status_returns_four, test_api_providers_status_counts_activity

### `test_provider_status_service.py` (135줄) — tests/test_provider_status_service.py — get_provider_coverage 단위 테스트.

- functions: coverage_conn, test_months_range, test_garmin_counts, test_strava_counts, test_intervals_runalyze_all_zero, test_providers_length_always_four, test_months_first, test_empty_db_returns_all_zeros, test_enabled_sources_default_and_filter, test_coverage_marks_disabled_sources, test_start_basic_sync_skips_disabled, test_set_sync_source_toggles_and_keeps_order, test_sync_page_widgets_reflect_sources, test_sync_sources_post_saves_checked_only

### `test_race_effort.py` (39줄) — P7-PRED-22(r4 보강): 거리·지속시간별 전력 판정 — 이 러너 대회 값으로 검증(REVIEW-09 §10).

- functions: test_runner_races, test_expected_ratio_monotone_and_t0, test_point_in_time_hrmax_and_proxy

### `test_race_hub_service.py` (284줄) — tests/test_race_hub_service.py — race_hub_service 단위 테스트.

- functions: conn, test_bucket_marathon, test_bucket_marathon_near, test_bucket_half, test_bucket_half_near, test_bucket_10k, test_bucket_5k, test_bucket_none_out_of_range, test_bucket_none_input, test_no_goal_all_none, test_past_goal_only_returns_none, test_nearest_future_goal_selected, test_days_left_and_weeks_left, test_prediction_value_and_gap, test_prediction_history_ascending, test_prediction_history_90d_window, test_no_bucket_no_prediction, test_no_target_gap_is_none, test_form_with_ctl_tsb, test_form_no_metrics_both_none, test_hub_includes_projection_key, test_form_band_boundaries, test_race_briefing_none_without_goal_or_tsb, test_race_briefing_phases, test_today_briefing_uses_race_context

### `test_race_projection_service.py` (81줄) — tests/test_race_projection_service.py — 레이스 아침 폼 예측.

- functions: test_taper_factor_bands, test_none_without_ctl_atl, test_none_when_race_past_today_or_too_far, test_taper_gives_higher_tsb_than_keep, test_zero_load_decays_toward_positive_tsb, test_scenarios_have_ctl_change_pct

### `test_race_result_service.py` (35줄) — P7-PRED-53: 대회 확인 서비스.

- functions: test_confirm_update_remove, test_validation, test_candidates

### `test_rate_limiter.py` (52줄) — RateLimiter 단위 테스트.

- class **TestRateLimitPolicy**: test_four_sources_defined, test_garmin_conservative, test_strava_window
- class **TestRateLimiter**: test_call_count, test_handle_rate_limit_retry, test_429_reset_on_success, test_should_stop_daily, test_unknown_source_default

### `test_raw_payload.py` (209줄) — source_payloads 저장/병합 유틸리티 테스트 (v0.3 스키마).

- class **TestStoreRawPayload**: test_insert_new, test_second_call_replaces_payload, test_update_replaces_when_changed, test_activity_id_set_on_insert, test_activity_id_coalesce_on_update, test_activity_id_updated_when_provided, test_empty_payload_skipped, test_none_payload_skipped, test_different_sources_same_entity_id, test_graceful_on_missing_table, test_fetched_at_present_after_update
- class **TestFillNullColumns**: test_fills_null_hr, test_does_not_overwrite_existing_value, test_multiple_columns, test_none_values_skipped, test_returns_activity_id, test_returns_none_if_not_found, test_partial_override
- functions: conn

### `test_raw_store.py` (48줄) — raw_store 단위 테스트.

- class **TestUpsertRawPayload**: test_new_payload_returns_true, test_same_payload_returns_false, test_changed_payload_returns_true, test_row_count
- class **TestUpdateRawActivityId**: test_sets_activity_id

### `test_readiness.py` (254줄) — src/training/readiness.py 단위 테스트.

- class **TestVdotFormulas**: test_vdot_from_5k_known, test_vdot_from_marathon_known, test_vdot_from_race_invalid, test_vdot_to_time_roundtrip, test_vdot_to_time_invalid, test_vdot_to_time_higher_vdot_faster
- class **TestDistanceRules**: test_taper_5k, test_taper_10k, test_taper_half, test_taper_full, test_recommended_5k, test_recommended_full, test_recommended_half
- class **TestPhaseForWeek**: test_last_week_is_taper, test_second_to_last_is_taper_too, test_first_week_is_base, test_mid_week_is_build, test_late_week_is_peak
- class **TestRecommendWeeklyKm**: test_base_lower_than_build, test_taper_lowest, test_recovery_week_lower, test_higher_vdot_higher_km, test_returns_positive
- class **TestAnalyzeReadiness**: test_no_vdot_returns_zero_pct, test_easy_goal_high_pct, test_hard_goal_lower_pct, test_moderate_goal_reasonable_pct, test_below_min_weeks_capped, test_recommended_weeks_structure, test_projected_times_make_sense, test_status_summary_not_empty, test_weekly_vdot_gain_positive
- functions: empty_conn, populated_conn

### `test_rec.py` (94줄)

- class **TestREC**: test_with_data, test_no_ef, test_category
- class **TestRECPercentile**: test_recent_best_is_high

### `test_recompute_all_range.py` (38줄) — P7-PRED-87: recompute_all 이 재계산 범위 밖 이력을 지우지 않는다.

- functions: test_clear_range_keeps_history, test_recompute_all_default_spans_all_history, test_recompute_all_commits_results

### `test_reextract.py` (70줄) — P7-PRED-13: 제자리 재추출 — id 유지, 랩 GAP·스트림 경과시간 채움.

- functions: test_reextract_keeps_ids_and_fills_fields, test_activity_metrics_reextracted, test_dry_run_writes_nothing, test_orphan_guard_blocks_destructive_reprocess

### `test_relative_effort.py` (116줄)

- class **TestRelativeEffort**: test_from_avg_hr, test_high_intensity, test_low_intensity, test_no_hr, test_confidence_from_avg_hr, test_category
- class **TestRelativeEffortMock**: test_basic_mock, test_no_hr_mock

### `test_replanner.py` (220줄) — replanner.py 테스트 — 재조정 규칙 (고강도 이동, 볼륨 축소, 테이퍼 보호).

- functions: test_rule1_interval_moved_to_easy_day, test_rule1_tempo_moved, test_rule1_easy_not_moved, test_rule1_no_available_slot, test_rule2_consecutive_skips_reduce_volume, test_rule3_low_dist_ratio_warning, test_rule4_taper_no_move, test_result_has_required_keys, test_unknown_workout_id_returns_error

### `test_reprocess.py` (285줄) — DoD #4 (reprocess): Layer 0 → Layer 1/2 재구축 테스트.

- class **TestReprocessActivity**: test_rebuilds_from_raw, test_metrics_rebuilt, test_primary_resolved, test_preserves_raw, test_clears_derived_only, test_no_clear_accumulates
- class **TestReprocessWellness**: test_wellness_rebuilt, test_sleep_columns_rebuilt, test_garmin_reprocess_corrects_stale_partial_day_row, test_wellness_metrics_rebuilt
- class **TestReprocessSourceFilter**: test_source_filter
- class **TestReprocessDedup**: test_dedup_runs

### `test_round2.py` (193줄) — 라운드 2 테스트: ComputeResult, compute_for_activities/dates, recompute_single_metric.

- class **TestComputeResult**: test_summary, test_defaults
- class **TestComputeForActivities**: test_basic, test_empty_list
- class **TestComputeForDates**: test_basic, test_empty_dates
- class **TestRecomputeSingleMetric**: test_trimp, test_invalid_metric
- class **TestComputeForDatesRunsActivityMetrics**: test_trimp_is_computed, test_trimp_is_marked_primary, test_ctl_reflects_trimp_from_same_call, test_no_activities_still_runs_daily
- class **TestRecomputeAll**: test_ctl_recomputed_after_clear, test_on_progress_callback

### `test_round4.py` (88줄) — 라운드 4 테스트: 메타데이터, semantic grouping, CLI.

- class **TestCalculatorMetadata**: test_all_have_display_name, test_all_have_description, test_format_types_valid, test_ranges_are_dict_or_none, test_groups_have_members, test_get_group_for_metric, test_get_group_members, test_get_group_members_nonexistent
- class **TestCLI**: test_status_empty, test_status_with_data, test_cli_no_command

### `test_rri.py` (108줄)

- class **TestRRI**: test_with_all_inputs, test_high_cirs_lowers_rri, test_no_vdot, test_category
- class **TestRRIMock**: test_with_all_inputs_mock, test_no_vdot_mock

### `test_rtti.py` (103줄)

- class **TestRTTI**: test_optimal, test_overload, test_no_data, test_category
- class **TestRTTIMock**: test_optimal_mock, test_no_data_mock

### `test_runalyze_extractor.py` (58줄) — Runalyze Extractor 단위 테스트.

- class **TestRunalyzeActivityCore**: test_required_fields, test_distance_time, test_pace_calculated
- class **TestRunalyzeActivityMetrics**: test_fitness_metrics, test_race_predictions, test_trimp
- functions: ext, activity_raw

### `test_runalyze_sync.py` (106줄) — DoD #10: Runalyze basic sync — mock 기반.

- class **TestRunalyzeSync**: test_sync_one_activity, test_sync_empty, test_sync_skip_unchanged, test_sync_no_token, test_sync_dict_response, test_metrics_stored

### `test_sapi.py` (114줄)

- class **TestSAPI**: test_with_fearp_data, test_no_fearp, test_category

### `test_schema_v23.py` (43줄) — 스키마 v23 — chat_messages 엔진 컬럼·coach_consent (30-coach-chat design §4.3·§6.2).

- functions: test_create_tables_has_v23_columns_and_consent, test_ensure_v23_idempotent, test_migrate_from_22, test_consent_single_row_only

### `test_schema_v24.py` (46줄) — 스키마 v24 — chat_messages.client_msg_id·chat_threads 컬럼 (30-coach-chat design §6.2).

- functions: test_create_tables_has_v24_columns, test_ensure_v24_idempotent, test_migrate_from_23, test_client_msg_id_unique_per_thread

### `test_segments.py` (106줄) — P7-PRED-21: 세그먼트 분해 r4 — 구조 기반 세트 구간·세션 유형(기기 불필요).

- functions: B, test_interval_6x1000_jog_rest, test_float_rest_is_not_rest, test_stride_tail_merged_into_work, test_continuous_tempo_auto_laps_no_itype, test_slow_block_is_not_quality, test_repetition_and_sprint, test_easy_long_race, test_set_drop, test_stream_blocks_detect_alternation, test_time_axis_repair, test_time_axis_repair_basis

### `test_strava_403_ledger.py` (49줄) — Strava 403(구독 필요)이 원장에 subscription_required로 남는지.

- functions: test_wrapper_raises_subscription_required, test_sync_source_records_failed_ledger_row, test_classify_403_code

### `test_strava_extractor.py` (98줄) — Strava Extractor 단위 테스트.

- class **TestStravaActivityCore**: test_required_fields, test_distance_time, test_suffer_score_in_metrics, test_latlng, test_source_url, test_no_none_values
- class **TestStravaActivityMetrics**: test_basic_metrics, test_splits_as_json
- class **TestStravaBestEfforts**: test_extraction
- class **TestStravaStreams**: test_stream_extraction, test_empty_streams
- functions: ext, activity_raw

### `test_strava_sync.py` (140줄) — DoD #8: Strava sync — OAuth + detail + streams mock 기반.

- class **TestStravaActivitySync**: test_sync_one_activity, test_sync_with_best_efforts, test_sync_empty_list, test_sync_skip_unchanged, test_sync_no_token

### `test_stream_meta_backfill.py` (37줄) — U18e: 스트림 meta 백필.

- functions: test_backfill_garmin_writes_measured_meta, test_backfill_dry_run_writes_nothing_and_unknown_for_other_sources

### `test_stream_meta_store.py` (63줄) — U18b — 스트림 meta 저장 경로(stream_meta_store) 테스트.

- functions: conn, test_ensure_v30_idempotent, test_upsert_overwrites, test_stored_count_reflects_duplicate_seconds, test_scaled_uses_summary_time, test_scaled_without_summary_skips, test_plain_list_and_missing_table_fall_back

### `test_stream_time.py` (71줄) — U18a — 스트림 시간축 결정(stream_time) + 추출기 연결 테스트.

- functions: test_sum_elapsed_preferred, test_direct_elapsed_fallback, test_timestamp_only_is_derived, test_no_key_scaled_times_none, test_partial_none_interpolated_small_ratio_keeps_basis, test_many_none_lowers_basis, test_non_monotonic_lowers_without_sorting, test_garmin_extractor_meta_and_no_index_fallback, test_strava_time_is_measured, test_stream_meta_empty

### `test_sync_errors.py` (61줄) — sync_errors 분류·SyncResult 전파 테스트.

- functions: test_classify_http, test_classify_non_http, test_messages_cover_all_codes, test_from_result_only_for_total_failure, test_merge_and_job_dict_carry_error_code, test_strava_wrapper_raises_on_403

### `test_sync_jobs_schema.py` (77줄) — 원장 스키마(ensure_ledger) 멱등성·구버전 업그레이드 테스트.

- functions: test_ensure_ledger_idempotent, test_old_15_column_db_upgraded, test_syncjob_has_22_fields, test_cleanup_all_users_closes_only_stale, test_update_job_stamps_started_and_finished

### `test_sync_ledger_paths.py` (39줄) — 원장 기록 4경로(manual·bg·auto·cli)와 fail_run 비덮어쓰기 테스트.

- functions: test_cli_run_completed, test_manual_failed_with_code, test_fail_run_creates_missing_row_for_timeout, test_fail_run_does_not_overwrite_child_failure, test_auto_and_bg_source_path_persist

### `test_sync_result.py` (39줄) — SyncResult 단위 테스트.

- class **TestSyncResult**: test_defaults, test_rate_limited, test_merge, test_merge_failed_becomes_partial, test_to_sync_job_dict

### `test_sync_state_service.py` (102줄) — tests/test_sync_state_service.py — SyncState 계약(작업 원장 기준 동기화 상태).

- functions: conn, test_ok_when_recent_success, test_restart_stopped_job_is_not_an_error, test_auth_error_and_caveat, test_stale_when_success_older_than_12h, test_payload_time_converted_from_utc, test_error_code_takes_priority_and_state_groups, test_legacy_row_403_maps_to_subscription_required, test_upstream_codes_group_to_error_upstream

### `test_sync_trigger_service.py` (100줄) — sync_trigger_service — 판정 순서·시작 실패 격리·days_since_last_sync.

- functions: test_plan_skip_codes, test_plan_cooldown_then_rate_limited, test_plan_from_date_default_seven_days, test_days_since_last_sync, test_trigger_isolates_start_failure, test_trigger_existing_job_becomes_running_skip, test_skip_reason_to_dict_omits_none

### `test_synth_smoke.py` (55줄) — scripts/synth_smoke 합성 DB 시드 테스트 — 시드가 기능 기대치(서비스 입력)와 어긋나면 UI 스모크가 헛돈다.

- functions: test_seed_creates_expected_rows, test_seed_feeds_provider_status_and_adaptation, test_seed_empty_has_schema_but_no_rows, test_seed_overwrites_existing_file_and_writes_only_there

### `test_template_helpers.py` (194줄) — tests/test_template_helpers.py — Phase 5-E 헬퍼 함수 테스트.

- functions: test_format_distance_km, test_format_distance_decimals, test_format_distance_zero, test_format_distance_none, test_format_pace_normal, test_format_pace_exact, test_format_pace_zero, test_format_pace_none, test_format_duration_under_hour, test_format_duration_over_hour, test_format_duration_zero, test_format_duration_none, test_format_speed, test_format_speed_none, test_format_time_prediction, test_format_time_prediction_none, test_interpret_utrs_good, test_interpret_utrs_great, test_interpret_cirs_low, test_interpret_unknown_metric, test_interpret_none_value, test_metric_level_color_green, test_metric_level_color_yellow, test_metric_level_color_low_higher_is_better, test_metric_level_color_low_lower_is_better, test_confidence_badge_high, test_confidence_badge_medium, test_confidence_badge_low, test_confidence_badge_none, test_provider_badge_runpulse, test_provider_badge_garmin, test_provider_badge_unknown, test_provider_badge_none, test_metric_display_name_known, test_metric_display_name_unknown, test_metric_unit_known, test_metric_unit_unknown

### `test_teroi.py` (85줄)

- class **TestTEROI**: test_with_data, test_no_trimp, test_category

### `test_tids_time.py` (25줄) — P7-PRED-88: TIDS 시간 기준.

- functions: test_time_based_distribution_and_patterns, test_pattern_zero_zone1_has_no_polarization_index

### `test_today_hero.py` (139줄) — tests/test_today_hero.py — Today 히어로 state 판정·주간 스트립·게이지(10-today design §2.4·§7.3).

- functions: conn, test_no_goal_is_no_plan, test_planned_session_not_run_is_pre, test_run_on_planned_day_is_done_with_ratio, test_run_on_rest_day_is_extra, test_rest_day_without_run, test_race_week_and_race_day_take_precedence, test_week_summary_km_and_key_sessions, test_readiness_delta_and_missing, test_race_summary_none_without_goal, test_race_summary_without_prediction, test_race_summary_uses_self_row_range, test_extras_include_race_summary

### `test_today_service.py` (415줄) — today_service 테스트 — Phase 7a D5 + Phase 7b L2 내러티브.

- class **TestGetTodayStatus**: test_empty_data_returns_none_metrics, test_with_metrics, test_providers_surfaced_for_metric_cell
- class **TestGetRecentActivities**: test_empty, test_respects_limit_and_order, test_route_is_list_when_stream_exists, test_route_is_none_when_no_stream
- class **TestGetTodayBriefing**: test_no_data_fallback, test_low_tsb_recommends_rest, test_balanced_tsb
- class **TestGetTodaysCheckin**: test_no_checkin_returns_none, test_returns_saved_checkin, test_defaults_to_today_date
- class **TestGetTodayMilestones**: test_empty, test_returns_milestones
- class **TestGetTodayNarrative**: test_no_data_rule_fallback, test_rule_fallback_no_data_text, test_with_ctl_and_distance, test_ctl_increase_in_rule_text, test_ai_success_source_is_ai, test_ai_failure_falls_back_to_rule, test_evidence_excludes_none_metrics, test_milestones_in_response
- class **TestGetTodayNarrativeYearMonth**: test_highlights_field_present, test_highlights_no_data_zeros, test_highlights_with_activities, test_past_month_uses_last_day, test_year_month_label_in_evidence, test_peak_ctl_in_highlights, test_past_month_ctl_now_reflects_that_month_not_today, test_rule_fallback_uses_period_label_not_this_month, test_milestones_scoped_to_queried_month
- class **TestAttachDrill**: test_briefing_tsb_drill_when_metric_store_row_exists, test_briefing_tsb_drill_none_when_no_metric_store_row, test_narrative_ctl_drill_when_row_exists, test_narrative_ctl_drill_none_when_no_row, test_monthly_distance_always_drill_none
- class **TestSaveCheckin**: test_save_and_return, test_upsert_same_day, test_defaults_to_today_date
- functions: test_productive_load_tsb_is_not_rest

### `test_tpdi.py` (117줄)

- class **TestTPDI**: test_with_indoor_outdoor, test_json_has_counts, test_no_indoor

### `test_training_fullplan.py` (145줄) — E-1: 전체 훈련 일정 뷰 테스트.

- class **TestLoadFullPlanWeeks**: test_groups_by_week, test_current_week_flagged, test_total_km_calculated, test_completed_count, test_no_goal_uses_12_week_horizon
- class **TestFullplanRoute**: test_returns_200, test_contains_week_cards, test_current_week_open, test_no_db_graceful, test_goal_info_shown, test_back_link
- functions: app, client, db_file

### `test_training_month.py` (109줄) — E-2: 월간 캘린더 뷰 테스트.

- class **TestLoadMonthWorkouts**: test_returns_4_weeks, test_each_tuple_has_workouts_and_date, test_week_offset_shifts_start
- class **TestRenderMonthCalendar**: test_returns_html_string, test_has_rp_calendar_id, test_shows_day_names, test_empty_weeks_graceful, test_actual_activities_shown
- class **TestViewTabs**: test_contains_all_three_tabs, test_month_active_highlighted, test_week_tab_links_correctly
- functions: db_file

### `test_training_phase_f.py` (226줄) — Phase F: Wizard edit 모드 + 목표 카드 인터랙션 테스트.

- functions: db_file, app, client, test_goal_to_wizard_data_standard, test_goal_to_wizard_data_custom, test_fmt_time_hms, test_fmt_pace_mmss, test_render_step4_edit_mode, test_render_step4_create_mode, test_wizard_edit_get, test_render_goal_card_no_goal, test_render_goal_card_with_goal_no_workout, test_render_goal_card_with_today_workout, test_render_goal_card_already_completed, test_render_goal_card_skipped, test_workout_confirm_json, test_workout_match_check, test_workout_match_check_not_found

### `test_training_phase_g.py` (218줄) — Phase G: 목표 관리 개선 테스트 (G-1 ~ G-4).

- functions: initialize_db, conn, test_load_goals_with_stats_empty, test_load_goals_with_stats_counts, test_load_goals_with_stats_status_all, test_render_goals_panel_empty, test_render_goals_panel_with_goals, test_render_goals_panel_d_day, test_load_goal_weeks, test_render_goal_detail_html, test_render_goal_detail_no_delete_for_cancelled, test_goal_date_range_with_race_date, test_goal_date_range_with_plan_weeks, test_import_all

### `test_training_response.py` (35줄) — P7-PRED-41: 훈련 반응 r4(세트 기반, 기기 불필요).

- functions: test_weekly_zone_minutes_and_summary, test_set_trend_needs_4, test_long_mp_km

### `test_training_workout_edit.py` (204줄) — Phase D: 워크아웃 편집 AJAX 라우트 테스트.

- class **TestWorkoutPatch**: test_patch_type_and_distance, test_patch_pace, test_patch_interval_saves_description, test_patch_empty_body_returns_400, test_patch_nonexistent_db, test_patch_persists_to_db
- class **TestIntervalCalc**: test_basic_1000m, test_200m_short_interval, test_nonstandard_distance_warning, test_default_params
- functions: app, client, db_file, workout_id

### `test_trigger_sync_bg_v1.py` (27줄) — v1 /trigger-sync-bg — 서비스 판정 위임 후에도 응답 포맷 유지.

- functions: test_v1_response_shape

### `test_trimp_calc.py` (89줄) — TRIMP + HRSS calculator 테스트 — 설계서 4-2 기준.

- class **TestTRIMPCalculator**: test_compute, test_no_hr, test_uses_wellness_rest_hr, test_confidence_without_measured_max
- class **TestHRSSCalculator**: test_compute, test_no_trimp

### `test_trimp_est.py` (97줄) — TRIMP 추정 Calculator 테스트 — 심박 결측 러닝의 페이스 기반 부하 추정.

- functions: test_fit_recovers_line, test_fit_rejects_flat_or_negative, test_estimates_missing_hr_with_low_confidence, test_faster_pace_gives_higher_estimate, test_skips_when_hr_measured, test_empty_when_not_enough_history, test_measured_provider_outranks_estimate, test_store_primary_prefers_measured

### `test_unified_activities.py` (338줄) — unified_activities 서비스 테스트.

- class **TestPickValue**: test_garmin_first, test_fallback_when_garmin_missing, test_none_when_all_missing, test_all_values_populated, test_service_priority_order
- class **TestBuildUnifiedActivity**: test_single_source, test_multi_source_group, test_representative_id_garmin_first, test_date_property, test_effective_group_id_solo, test_effective_group_id_real_group
- class **TestBuildSourceComparison**: test_returns_list_of_dicts, test_field_names_present, test_values_per_source, test_missing_source_not_in_row, test_unified_value_and_source_present, test_unified_source_fallback, test_unified_value_none_when_all_missing
- class **TestFetchUnifiedActivities**: test_returns_solo_activities, test_groups_by_matched_group_id, test_grouped_activity_has_both_sources, test_pagination, test_stats_total_dist, test_date_filter, test_source_filter
- class **TestGroupOperations**: test_assign_creates_group, test_assign_requires_two, test_remove_from_group
- functions: mem_db

### `test_user_inputs.py` (130줄) — D3 — user_inputs / ai_feedback / chat_threads 테이블 스키마 테스트.

- class **TestUserInputs**: test_save_checkin, test_checkin_unique_per_day, test_checkin_raw_insert_conflict_without_upsert_raises, test_activity_id_no_fk_enforcement
- class **TestAiFeedback**: test_insert_feedback, test_unique_per_thread_message
- class **TestChatThreads**: test_chat_messages_thread_id_column_exists, test_thread_groups_messages

### `test_user_settings_service.py` (71줄) — 사용자 설정 서비스·API 테스트.

- functions: conn, test_whitelist_and_invalid_value, test_resolve_priority, test_set_overwrites, test_invalid_global_falls_back, client, test_api_get_patch, test_api_patch_invalid_400, test_api_state_persists

### `test_utrs.py` (114줄) — UTRS (Unified Training Readiness Score) 단위 테스트 — 설계서 4-6.

- class **TestUTRS**: test_full_inputs_confidence_1, test_partial_inputs_lower_confidence, test_three_inputs_confidence, test_score_range, test_json_has_components, test_no_inputs, test_child_metrics_have_parent_and_correct_names

### `test_validator.py` (376줄) — DataValidator 테스트.

- class **TestRowCounts**: test_pass, test_fail_empty_db
- class **TestSourceDistribution**: test_pass, test_fail_missing_source
- class **TestUnmappedMetricRatio**: test_pass, test_fail_all_null
- class **TestMetricDensity**: test_pass, test_fail_sparse
- class **TestPrimaryUniqueness**: test_pass, test_fail_duplicate_primary
- class **TestProviderDistribution**: test_pass, test_fail_no_runpulse
- class **TestDedupConsistency**: test_pass, test_fail_same_source_in_group
- class **TestDataQuality**: test_pass, test_fail_negative_distance
- class **TestWellnessCoverage**: test_pass, test_fail_no_wellness
- class **TestFitnessContinuity**: test_pass, test_fail_large_gap
- class **TestReferentialIntegrity**: test_pass, test_fail_orphan_lap
- class **TestEngineCoverage**: test_fail_empty_metric_store, test_pass_all_produces_present
- class **TestRunAll**: test_returns_12_results, test_all_have_valid_status, test_check_result_fields
- functions: empty_conn, populated_conn

### `test_vdot_guard.py` (19줄) — P7-PRED-84: runpulse_vdot moving_time 붕괴 가드.

- functions: test_normal_value, test_collapsed_moving_time_rejected

### `test_views_settings_garmin_migration.py` (352줄) — views_settings_garmin.py garminconnect 0.3.x 마이그레이션 테스트.

- class **TestGarminConnectView**: test_renders_200, test_token_status_shows_garminconnect_path, test_no_token_shows_status_badge
- class **TestServerLogin**: test_save_only_no_password_required, test_login_calls_garminconnect_garmin, test_mfa_redirect_on_needs_mfa, test_no_email_returns_error, test_429_shows_error_redirect
- class **TestTokenUpload**: test_upload_garmin_tokens_json, test_no_file_returns_error, test_invalid_json_returns_error
- class **TestPasteToken**: test_paste_valid_json, test_paste_invalid_json_returns_error, test_empty_input_returns_error
- class **TestMFA**: test_expired_session_returns_error, test_mfa_submit_calls_resume_login, test_empty_mfa_code_redirects_back, test_mfa_resume_exception_returns_error
- class **TestMiscRoutes**: test_browser_login_200, test_disconnect_redirects
- functions: garmin_app

### `test_weather_ingest.py` (57줄) — P7-PRED-32: 활동 기상 인제스트·캐시·폴백·충돌.

- class **FakeGet**: 없음
- functions: test_ingest_open_meteo_then_cache_hit, test_offline_falls_back_to_device_and_retries_later, test_no_coords_no_device, test_conflict_flag

### `test_weather_provider.py` (25줄) — P7-PRED-86: Open-Meteo 단일 클라이언트(provider.py) — 요청 파라미터·보간·WBGT.

- functions: test_request_params_archive_vs_forecast, test_at_time_interpolates_and_wbgt

### `test_week_compliance.py` (103줄) — tests/test_week_compliance.py — 날짜별 유효 계획·이행 수치(31-coach-plan design R1·R2·R3·R5).

- functions: conn, test_superseded_planner_row_not_in_denominator, test_volume_labels, test_easy_run_too_fast_is_intensity_off, test_missed_and_unplanned_run, test_before_effective_start_is_pre_plan, test_future_day_is_upcoming_and_not_counted

### `test_week_digest.py` (52줄) — week_digest / 월간 프롬프트 W 블록 테스트 (U17g).

- functions: test_weeks_overlapping_monday_start, test_empty_week_has_none_values, test_week_with_run_and_plan, test_in_progress_week_is_partial, test_prompt_contains_week_block, test_prompt_lines_empty_week

### `test_week_structure.py` (87줄) — U16f: R7 주간 구조(순수 함수).

- functions: test_default_run_days_median_and_clamp, test_long_ratio_branches, test_long_cap_design_example, test_long_cap_by_time, test_short_session_merged_to_rest_and_redistributed_to_easy, test_shakeout_before_race_kept, test_long_run_capped_and_excess_to_easy, test_total_preserved_when_pool_left_over, test_feasible_week_km_grows_with_days, test_run_days_surplus_trims_smallest_easy, test_min_pass_by_minutes

### `test_weekly_adapt.py` (61줄) — 주간 적응 규칙(§3.4) — 표의 행마다 1건 + 경계값, 행 조정, 서비스 가드.

- functions: test_decide_table_rows, test_decide_boundaries_and_gates, test_taper_start_not_pushed_by_repeat, test_apply_to_rows_scales_and_limits_quality, test_adapt_plan_noop_for_v1_or_no_goal

### `test_wellness_day.py` (87줄) — tests/test_wellness_day.py — 웰니스 /:date 일 상세(헤드라인·기준선·nav·week)와 trend band.

- functions: conn, test_percentile_band_requires_min_n, test_headline_reasons_by_abs_z_and_status, test_headline_without_reasons_when_usual, test_baselines_exclude_current_day_and_omit_small_n, test_no_record_day_has_week_and_nav, test_as_of_only_for_today, test_detail_keeps_legacy_fields, test_trend_end_and_band

### `test_wellness_service.py` (153줄) — tests/test_wellness_service.py — Phase 5-C 서비스 레이어 테스트.

- functions: conn, test_get_wellness_detail_full, test_get_wellness_detail_core, test_get_wellness_detail_metrics_by_category, test_get_wellness_detail_sleep_category, test_get_wellness_detail_hr_category, test_get_wellness_detail_body_category, test_get_wellness_detail_stress_category, test_get_wellness_detail_readiness_summary, test_get_wellness_detail_no_data, test_get_wellness_detail_default_date, test_get_wellness_trend_full, test_get_wellness_trend_includes_utrs, test_get_wellness_trend_with_gaps, test_get_wellness_trend_empty

### `test_wlei.py` (105줄)

- class **TestWLEI**: test_basic, test_hot_weather, test_cold_weather, test_no_trimp, test_json_value, test_confidence

### `test_zones.py` (64줄) — zones 유틸리티 테스트.

- class **TestHrZones**: test_returns_5_zones, test_zone_boundaries, test_zones_ascending
- class **TestGetHrZone**: test_zone1, test_zone3, test_zone5, test_zero_hr, test_above_max
- class **TestPaceZones**: test_returns_5_zones, test_zone1_slowest
- class **TestGetPaceZone**: test_easy_pace, test_threshold_pace, test_vo2max_pace, test_zero_pace

## `scripts/`

### `backfill_activity_groups.py` (89줄) — activity_groups 마스터 테이블 백필 스크립트 (D2).

- functions: backfill, main

### `backfill_stream_meta.py` (17줄) — activity_stream_meta 백필(U18e). 사용: PYTHONPATH=. python3 scripts/backfill_stream_meta.py --db <path> [--dry-run]

- (public API 없음)

### `check_data_consistency.py` (449줄) — RunPulse 데이터 정합성 검증 v1.5

- functions: parse_ddl_tables, parse_db_schema, parse_arch_categories, check_all, main

### `check_docs.py` (1054줄) — 문서 정합성 검증 스크립트 (v0.3 Phase 6 확장판).

- functions: check, section, error, warn, ok, check_backlog, check_files_index, check_line_count, check_pytest_collect, check_metric_dictionary, check_calculator_count, check_semantic_groups, check_test_file_count, check_outdated, check_phase_summary_files, check_schema_columns, check_category_triple, check_db_helpers_functions, check_doc_numbers, check_docstrings, check_phase2_extractors, check_phase3_sync, check_phase4_metrics, check_phase5_services, check_phase6_load_validate, main

### `encrypt_existing_configs.py` (153줄) — 기존 config.json 파일의 자격증명을 Fernet으로 암호화하는 마이그레이션 스크립트.

- functions: main

### `garmin_local_sync.py` (348줄) — Garmin 로컬 토큰 발급 + VPS 동기화 트리거 스크립트.

- functions: main

### `gen_data_master.py` (276줄) — 데이터 마스터 시트 자동 생성 v3.

- functions: parse_db_setup, cross_validate, generate

### `gen_files_index.py` (138줄) — files_index.md 자동 생성.

- functions: get_docstring, get_docstring_first_line, get_public_api, main

### `gen_metric_dictionary.py` (256줄) — 메트릭 사전 (metric_dictionary.md) 자동 생성.

- functions: generate, get_structural_fingerprint

### `plan_backtest.py` (43줄) — 계획 엔진 백테스트 CLI — 실DB 사본(읽기 전용)의 역사 시나리오와 합성 격자를 돌려 게이트 결과를 JSON 으로 낸다.

- functions: main

### `pred_backtest.py` (102줄) — 예측 v2 수용 백테스트(P7-PRED-62) — 실DB 를 읽기 전용으로 열어 메모리에 복제한 뒤, 전력 대회마다 D-0/D-28 시점

- functions: backtest, backtest_all, main

---
총 598개 파일

## docstring 누락

- `tests/__init__.py`
- `tests/test_constraints.py`
- `tests/test_critical_power.py`
- `tests/test_crs.py`
- `tests/test_eftp.py`
- `tests/test_fixture_loader.py`
- `tests/test_fixtures_layout.py`
- `tests/test_marathon_shape.py`
- `tests/test_metrics_basis_events.py`
- `tests/test_metrics_version_events.py`
- `tests/test_personalize.py`
- `tests/test_plan_backtest.py`
- `tests/test_plan_gates.py`
- `tests/test_planner_as_of.py`
- `tests/test_prediction_core.py`
- `tests/test_rec.py`
- `tests/test_relative_effort.py`
- `tests/test_rri.py`
- `tests/test_rtti.py`
- `tests/test_sapi.py`
- `tests/test_teroi.py`
- `tests/test_tpdi.py`
- `tests/test_wlei.py`