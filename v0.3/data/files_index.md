# RunPulse 파일 인덱스

> 자동 생성 (`python3 scripts/gen_files_index.py`) — 수동 편집 금지
> 디렉토리 설명 변경: 해당 `__init__.py` docstring 수정 후 재생성
> 파일 설명 변경: 해당 `.py` 모듈 docstring 수정 후 재생성

## `src/services/`

> Phase 5 서비스 레이어.
> 
> DB에서 데이터를 읽어 가공된 dict를 반환한다.
> 읽기 전용 — DB 쓰기 금지. 첫 번째 인자는 항상 sqlite3.Connection.
> 반환값은 dict (snake_case 키). 단위 변환 하지 않음 — SI 그대로 반환.
> 
> 설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
> 의존: src/utils/db_helpers.py, src/utils/metric_registry.py
> 주의: metric_store 조회 시 is_primary=1 필터 필수

### `unified_activities.py` (448줄) — 통합 활동 서비스 — 멀티 소스 활동을 Garmin 우선으로 병합.

- class **UnifiedField**: 없음
- class **UnifiedActivity**: date, can_expand
- functions: build_unified_activity, fetch_unified_activities, build_source_comparison, assign_group_to_activities, remove_from_group

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

### `acwr.py` (35줄) — ACWR Calculator — 설계서 4-3 기준.

- class **ACWRCalculator**: compute

### `adti.py` (48줄) — ADTI (Adaptive Training Trend Index) — 설계서 4-4 기준.

- class **ADTICalculator**: compute

### `base.py` (494줄) — MetricCalculator 기본 클래스 + CalcContext + CalcResult.

- class **CalcResult**: is_empty
- class **MetricCalculator**: compute
- class **CalcContext**: activity, get_metric, get_metric_json, get_metric_text, get_daily_metric_series, get_activities_in_range, get_activity_metric, get_activity_metric_text, get_streams, get_laps, get_wellness, get_daily_load, get_activity_metric_series, get_wellness_series, update_metric_cache
- class **ConfidenceBuilder**: add_input, compute

### `cirs.py` (109줄) — CIRS (Composite Injury Risk Score) — 설계서 4-4 기준.

- class **CIRSCalculator**: compute

### `classifier.py` (120줄) — Workout Classifier — 설계서 4-2 기준.

- class **WorkoutClassifier**: compute

### `cli.py` (122줄) — Metrics CLI 인터페이스 (보강 #10).

- functions: show_metric_status, main

### `critical_power.py` (98줄) — CP/W' (Critical Power / W Prime) — 임계 파워 및 무산소 용량.

- class **CriticalPowerCalculator**: compute

### `crs.py` (206줄) — CRS (Composite Readiness Score) — 복합 훈련 준비도 평가.

- class **CRSCalculator**: compute

### `darp.py` (69줄) — DARP (Dynamic Adjusted Race Prediction) — 설계서 4-4 기준.

- class **DARPCalculator**: compute

### `decoupling.py` (64줄) — Aerobic Decoupling Calculator — 설계서 4-2 기준.

- class **AerobicDecouplingCalculator**: compute

### `di.py` (59줄) — DI (Durability Index) — 설계서 4-4 기준.

- class **DICalculator**: compute

### `efficiency.py` (35줄) — Efficiency Factor Calculator — 설계서 4-2 기준.

- class **EfficiencyFactorCalculator**: compute

### `eftp.py` (103줄) — eFTP (Estimated Functional Threshold Pace) — 기능적 역치 페이스 추정.

- class **EFTPCalculator**: compute

### `engine.py` (639줄) — Metrics Engine — topological sort 기반 실행. 설계서 4-5 + 보강 #1,#2,#11 기준.

- class **ComputeResult**: summary
- functions: run_activity_metrics, run_daily_metrics, run_for_date, compute_for_activities, compute_for_dates, recompute_single_metric, recompute_recent, clear_runpulse_metrics, recompute_all

### `fearp.py` (73줄) — FEARP (Fitness & Environment Adjusted Running Pace) — 설계서 4-4 기준.

- class **FEARPCalculator**: compute

### `gap.py` (71줄) — GAP (Grade Adjusted Pace) Calculator — 설계서 4-2 기준.

- class **GAPCalculator**: compute

### `hrss.py` (53줄) — HRSS Calculator — 설계서 4-2 기준.

- class **HRSSCalculator**: compute

### `lsi.py` (55줄) — LSI (Load Spike Index) Calculator — 설계서 4-3 기준.

- class **LSICalculator**: compute

### `marathon_shape.py` (96줄) — Marathon Shape — 마라톤 훈련 완성도.

- class **MarathonShapeCalculator**: compute

### `monotony.py` (61줄) — Monotony & Strain Calculator — 설계서 4-3 기준.

- class **MonotonyStrainCalculator**: compute

### `pmc.py` (74줄) — PMC (ATL/CTL/TSB/Ramp Rate) Calculator — 설계서 4-3 기준.

- class **PMCCalculator**: compute

### `rec.py` (64줄) — REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.

- class **RECCalculator**: compute

### `relative_effort.py` (76줄) — Relative Effort (Strava 방식) — 심박존 기반 노력도 점수.

- class **RelativeEffortCalculator**: compute

### `reprocess.py` (87줄) — Reprocess — Raw payload에서 Layer 1/2 재구축. 설계서 4-7 기준.

- functions: reprocess_from_payloads

### `rmr.py` (66줄) — RMR (Recovery & Metabolic Readiness) — 설계서 4-4 기준.

- class **RMRCalculator**: compute

### `rri.py` (74줄) — RRI (Race Readiness Index) — 레이스 준비도 종합 지수.

- class **RRICalculator**: compute

### `rtti.py` (81줄) — RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

- class **RTTICalculator**: compute

### `sapi.py` (126줄) — SAPI (Seasonal-Adjusted Performance Index) — 계절·날씨 성과 비교.

- class **SAPICalculator**: compute

### `teroi.py` (65줄) — TEROI (Training Effect Return On Investment) — 훈련 효과 투자 수익률.

- class **TEROICalculator**: compute

### `tids.py` (54줄) — TIDS (Training Intensity Distribution Score) — 설계서 4-4 기준.

- class **TIDSCalculator**: compute

### `tpdi.py` (64줄) — TPDI (Trainer Physical Disparity Index) — 실내/실외 FEARP 격차 지수.

- class **TPDICalculator**: compute

### `trimp.py` (85줄) — TRIMP Calculator — 설계서 4-2 기준.

- class **TRIMPCalculator**: compute

### `utrs.py` (93줄) — UTRS (Unified Training Readiness Score) — 설계서 4-4 기준.

- class **UTRSCalculator**: compute

### `vdot.py` (66줄) — VDOT Calculator — 설계서 4-2 기준.

- class **VDOTCalculator**: compute

### `vdot_adj.py` (148줄) — VDOT_ADJ — 현재 체력 기반 VDOT 보정.

- class **VDOTAdjCalculator**: compute

### `wlei.py` (80줄) — WLEI (Weather-Loaded Effort Index) — 날씨 가중 노력 지수.

- class **WLEICalculator**: compute

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

### `_helpers.py` (132줄) — Orchestrator 내부 어댑터 — Extractor 출력을 db_helpers 인터페이스에 연결.

- functions: save_activity_core, save_metrics, save_laps, save_streams, save_best_efforts, save_daily_wellness, save_daily_fitness, resolve_primaries, record_sync_job

### `dedup.py` (85줄) — 활동 중복 감지 — 5분 / 3% 규칙.

- functions: run

### `garmin.py` (193줄)

- functions: sync_daily_extensions, sync_athlete_extensions, sync_garmin

### `garmin_activity_sync.py` (226줄) — Garmin 활동 동기화 Orchestrator.

- class **_RateLimitStop**: 없음
- functions: sync

### `garmin_api_extensions.py` (400줄)

- functions: sync_activity_streams, sync_activity_gear, sync_activity_exercise_sets, sync_activity_weather, sync_activity_hr_zones, sync_activity_power_zones

### `garmin_athlete_extensions.py` (177줄)

- functions: sync_athlete_profile, sync_athlete_stats, sync_athlete_personal_records

### `garmin_auth.py` (129줄)

- class **GarminAuthRequired**: 없음
- functions: check_garmin_connection

### `garmin_backfill.py` (209줄) — Garmin ZIP export → activity_summaries backfill (v2)

- functions: backfill_from_zip

### `garmin_daily_extensions.py` (472줄)

- functions: sync_daily_race_predictions, sync_daily_training_status, sync_daily_fitness_metrics, sync_daily_user_summary, sync_daily_all_day_stress, sync_daily_body_battery_events, sync_daily_heart_rates, sync_daily_hydration, sync_daily_weigh_ins, sync_daily_running_tolerance

### `garmin_helpers.py` (113줄)

- (public API 없음)

### `garmin_v2_mappings.py` (289줄) — Garmin → activity_summaries v2.5 필드 매핑 정의.

- functions: extract_summary_fields_from_api, extract_summary_fields_from_zip, extract_detail_fields, build_upsert_sql

### `garmin_wellness_sync.py` (138줄) — Garmin 일별 wellness 동기화 Orchestrator.

- class **_RateLimitStop**: 없음
- functions: sync

### `integration.py` (55줄) — Phase 3 → Phase 4 통합 지점 (보강 #12).

- functions: compute_metrics_after_sync

### `intervals.py` (55줄) — Intervals.icu 데이터 동기화 (Basic Auth) — 하위 모듈 wrapper.

- functions: sync_intervals

### `intervals_activity_sync.py` (168줄) — Intervals.icu 활동 + wellness 동기화 Orchestrator.

- functions: sync, sync_wellness

### `intervals_athlete_sync.py` (120줄) — Intervals.icu 선수 프로필 동기화.

- functions: sync_athlete_profile, sync_athlete_stats_snapshot

### `intervals_auth.py` (58줄) — Intervals.icu API 인증 및 연결 상태 확인.

- functions: base_url, auth, check_intervals_connection

### `intervals_wellness_sync.py` (111줄) — Intervals.icu 웰니스 / 피트니스 동기화.

- functions: sync_wellness

### `orchestrator.py` (114줄) — 통합 sync 진입점.

- functions: full_sync

### `rate_limiter.py` (137줄) — 소스별 API Rate-Limit 관리.

- class **RateLimitPolicy**: 없음
- class **RateLimiter**: pre_request, post_request, handle_rate_limit, call_count, should_stop

### `raw_store.py` (46줄) — Raw payload 저장 — db_helpers.upsert_payload()의 Sync-friendly 래퍼.

- functions: upsert_raw_payload, update_raw_activity_id

### `reprocess.py` (291줄) — Raw payload(Layer 0)에서 Layer 1/2 재구축.

- functions: reprocess_all

### `runalyze.py` (300줄) — Runalyze 데이터 동기화 (API Token).

- functions: sync_activities, check_runalyze_connection

### `runalyze_activity_sync.py` (86줄) — Runalyze 활동 동기화 Orchestrator.

- functions: sync

### `strava.py` (67줄) — Strava 데이터 동기화 (OAuth2) — 하위 모듈 wrapper.

- functions: sync_strava

### `strava_activity_sync.py` (164줄) — Strava 활동 동기화 Orchestrator.

- functions: sync

### `strava_athlete_sync.py` (188줄) — Strava 선수 프로필, 통계, 기어 동기화.

- functions: sync_athlete_profile, sync_athlete_stats, sync_gear, sync_athlete_and_gear

### `strava_auth.py` (91줄) — Strava OAuth2 토큰 관리 및 연결 상태 확인.

- functions: refresh_token, check_strava_connection

### `sync_result.py` (65줄) — Sync 작업 결과 데이터 구조.

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

### `garmin_extractor.py` (575줄) — Garmin raw JSON → Layer 1 + Layer 2 변환.

- class **GarminExtractor**: extract_activity_core, extract_activity_metrics, extract_activity_laps, extract_wellness_core, extract_wellness_metrics, extract_fitness

### `intervals_extractor.py` (201줄) — Intervals.icu raw JSON → Layer 1 + Layer 2 변환.

- class **IntervalsExtractor**: extract_activity_core, extract_activity_metrics, extract_wellness_core, extract_fitness

### `runalyze_extractor.py` (102줄) — Runalyze raw JSON → Layer 1 + Layer 2 변환.

- class **RunalyzeExtractor**: extract_activity_core, extract_activity_metrics

### `strava_extractor.py` (211줄) — Strava raw JSON → Layer 1 + Layer 2 변환.

- class **StravaExtractor**: extract_activity_core, extract_activity_metrics, extract_activity_streams, extract_best_efforts

## `src/ai/`

> AI 코칭 컨텍스트 빌더.
> 
> 서비스 레이어 데이터를 LLM 프롬프트용 마크다운으로 변환.
> 직접 SQL 금지 — 서비스 레이어만 호출. None 메트릭은 출력에서 제외.
> 
> 설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
> 의존: src/services/, src/web/template_helpers.py

### `ai_cache.py` (152줄) — AI 캐시 관리 — DB 기반 AI 해석 결과 저장/조회/갱신.

- functions: get_cached, set_cached, get_cache_age, invalidate, invalidate_after_sync

### `ai_context.py` (347줄) — 분석 데이터를 AI 프롬프트 컨텍스트로 변환.

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

### `chat_context.py` (81줄) — AI 채팅 전용 컨텍스트 빌더 — 의도 감지 → DB 자동 수집.

- functions: build_chat_context

### `chat_context_builders.py` (287줄) — AI 채팅 컨텍스트 — 기본 + 의도별 빌더.

- (public API 없음)

### `chat_context_format.py` (266줄) — AI 채팅 컨텍스트 — 포맷터 (컨텍스트 dict → 프롬프트 텍스트).

- (public API 없음)

### `chat_context_intent.py` (83줄) — AI 채팅 컨텍스트 — 의도 감지 모듈.

- functions: detect_intent

### `chat_context_rich.py` (192줄) — AI 채팅 컨텍스트 — 풍부한 컨텍스트 빌더 (Gemini/Claude용).

- (public API 없음)

### `chat_context_utils.py` (32줄) — AI 채팅 컨텍스트 — 공통 유틸리티.

- functions: seconds_to_pace

### `chat_engine.py` (208줄) — AI 채팅 엔진 — 교체 가능 구조.

- functions: get_ai_provider, chat

### `chat_engine_providers.py` (380줄) — AI 채팅 — 외부 API provider 호출 모듈.

- class **RateLimitError**: 없음
- functions: call_with_tools, call_claude, call_openai, call_gemini, call_groq, call_genspark, call_genspark_selenium

### `chat_engine_rules.py` (259줄) — AI 채팅 — 규칙 기반 fallback 응답.

- functions: rule_based_response

### `context_builders.py` (426줄) — 탭별 컨텍스트 빌더 — AI 프롬프트에 필요한 데이터를 탭별로 조합.

- functions: build_dashboard_context, build_training_context, build_report_context, build_race_context, build_wellness_context, build_activity_context, format_context_compact

### `genspark_driver.py` (384줄) — Genspark AI 채팅 DOM 자동화 — proot subprocess 브릿지.

- functions: send_and_receive

### `prompt_config.py` (244줄) — 프롬프트 템플릿 관리 — 카드별 AI 프롬프트 정의 + 사용자 커스터마이즈.

- functions: get_prompt, get_all_prompts, get_tab_prompt

### `suggestions.py` (171줄) — 추천 칩 생성 — 규칙 기반 + AI 응답 파싱 하이브리드.

- class **RunnerState**: 없음
- functions: get_runner_state, rule_based_chips

### `tools.py` (547줄) — AI Function Calling 도구 — DB 조회 함수 정의 + 실행기.

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

### `app.py` (950줄) — RunPulse integration workbench web app.

- functions: create_app

### `auth_cf.py` (82줄) — Cloudflare Zero Trust 헤더 기반 사용자 식별 미들웨어.

- functions: init_cf_auth, get_current_user_email

### `bg_sync.py` (407줄)

- (public API 없음)

### `helpers.py` (931줄) — 웹 뷰 공통 헬퍼 함수.

- functions: project_root, get_current_user_id, db_path, render_sub_nav, bottom_nav, html_page, make_table, metric_row, score_badge, readiness_badge, fmt_min, fmt_duration, safe_str, connected_services, tooltip, race_shape_label, no_data_card, fmt_pace, last_sync_info

### `helpers_svg.py` (171줄) — SVG 시각화 헬퍼 — 반원 게이지 + 레이더 차트.

- functions: svg_semicircle_gauge, svg_radar_chart

### `route_svg.py` (136줄) — GPS 경로 SVG 썸네일 생성 — activity_streams에서 latlng 데이터를 SVG polyline으로 변환.

- functions: render_route_svg

### `sync_ui.py` (238줄) — 동기화 카드 UI 컴포넌트 — 기본(마지막 동기화 이후) / 기간 2탭.

- functions: sync_card_html

### `views_activities.py` (184줄) — 활동 목록 뷰 — Flask Blueprint + 라우트 핸들러.

- functions: activities_list

### `views_activities_filter.py` (214줄) — 활동 목록 뷰 — 필터 폼 + 날짜 프리셋 JS.

- (public API 없음)

### `views_activities_helpers.py` (264줄) — 활동 목록 뷰 — 포맷 헬퍼 + 아이콘/배지.

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

### `views_activity_loaders.py` (315줄) — 활동 상세 — 데이터 로딩 함수.

- (public API 없음)

### `views_activity_loaders_v2.py` (104줄) — 활동 상세 — 신규 데이터 로더 (UI 재설계용).

- functions: load_ef_decoupling_series, load_risk_series, load_tids_weekly_series, load_darp_values

### `views_activity_map.py` (98줄) — 활동 상세 — Leaflet + OpenStreetMap 경로 지도 렌더링.

- functions: render_map_placeholder

### `views_activity_merge.py` (132줄) — 활동 그룹 병합/분리 API — Flask Blueprint.

- functions: activities_merge, activities_ungroup, activities_auto_group

### `views_activity_s5_cards.py` (277줄) — S5-C2 신규 메트릭 카드 — RTTI, WLEI, TPDI, Running Tolerance, HR 존 차트.

- functions: render_rtti_card, render_wlei_card, render_tpdi_card, render_running_tolerance_card, render_hr_zone_chart

### `views_activity_source_cards.py` (436줄) — 활동 상세 — 소스별 서비스 카드 렌더링.

- (public API 없음)

### `views_ai_coach.py` (402줄) — AI 코칭 뷰 — Flask Blueprint.

- functions: ai_coach_page, ai_coach_chat_async, ai_coach_chat, ai_coach_get_prompt, ai_coach_paste_response

### `views_ai_coach_cards.py` (588줄) — AI 코칭 페이지 렌더링 카드 — views_ai_coach.py에서 분리.

- functions: render_coach_profile, render_briefing_card, render_wellness_card, render_chips, render_chat_section, render_recent_training, render_risk_summary

### `views_dashboard.py` (436줄) — 통합 대시보드 뷰 — Flask Blueprint.

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

### `views_dashboard_loaders.py` (127줄) — 대시보드 — 신규 데이터 로더 (UI 재설계용).

- functions: load_wellness_mini, load_weekly_summary, load_fitness_trends, load_risk_7day_trends

### `views_dev.py` (589줄) — Developer/debug routes — config, payloads, DB summary, analyze preview.

- functions: config_summary, config_db_path, payloads, payload_view, db_summary, analyze_preview

### `views_export_import.py` (233줄) — Export 데이터 임포트 뷰 — Flask Blueprint.

- functions: export_import_page, export_import_run

### `views_guide.py` (240줄) — 용어집/가이드 페이지 — 메트릭 설명 + 분류 기준 + 적정 범위 통합.

- functions: guide_page

### `views_import.py` (311줄) — Strava Archive Import 뷰 — Flask Blueprint.

- functions: strava_archive_view, strava_archive_post, strava_archive_backfill

### `views_perf.py` (160줄) — 성능 최적화 — 배치 데이터 로더 + TTL 캐시.

- functions: cached_page, invalidate_cache, load_latest_metric_date, load_metrics_batch, load_metrics_json_batch, load_activity_metrics_batch, load_darp_batch

### `views_race.py` (408줄) — Sprint 5 · V2-6-1 — Race Prediction (DARP) UI Blueprint.

- functions: race_page

### `views_race_enhanced.py` (422줄) — 레이스 예측 보강 — 추세 차트, 목표 갭, 준비 요소, 메트릭 해설.

- functions: load_prediction_trend, load_fitness_factors, render_goal_gap, render_prediction_trend_chart, render_fitness_factors_chart, render_race_shape_trio, render_di_interpretation, render_metric_glossary

### `views_report.py` (349줄) — 분석 레포트 뷰 — Flask Blueprint.

- functions: report_view

### `views_report_charts.py` (335줄) — 레포트 — 신규 차트 렌더러 (UI 재설계용).

- functions: render_summary_delta, render_training_quality_chart, render_tids_weekly_chart, render_risk_trend_chart, render_form_trend, render_wellness_trend_chart

### `views_report_loaders.py` (179줄) — 레포트 — 신규 데이터 로더 (UI 재설계용).

- functions: load_prev_period_stats, load_training_quality_series, load_risk_trend_series, load_form_trend_series, load_wellness_trend_series, load_tids_weekly_series

### `views_report_sections.py` (312줄) — 레포트 추가 섹션 — AI 인사이트 + 요약 카드 + 테이블 + Export.

- functions: render_ai_insight, render_ai_insight_placeholder, render_export_buttons, render_summary_cards, render_weekly_chart, render_metrics_table

### `views_report_sections_cards.py` (276줄) — 레포트 섹션 — 메트릭 카드 렌더러.

- functions: render_tids_section, render_trimp_weekly_chart, render_risk_overview, render_darp_card, render_fitness_trend, render_endurance_trend

### `views_report_sections_data.py` (112줄) — 레포트 섹션 — 데이터 로더.

- (public API 없음)

### `views_settings.py` (320줄) — 서비스 연동 설정 뷰 — 메인 허브 + 설정 저장 라우트.

- functions: settings_view, settings_profile_post, settings_training_prefs_post, settings_ai_post, settings_mapbox_post, settings_prompts_post, settings_prompts_reset, settings_caldav_post, settings_caldav_test

### `views_settings_garmin.py` (422줄) — 설정 — Garmin 연동 라우트 (connect/MFA/disconnect).

- functions: garmin_connect_view, garmin_connect_post, garmin_mfa_view, garmin_mfa_submit, garmin_disconnect, garmin_browser_login, garmin_upload_token, garmin_paste_token

### `views_settings_hub.py` (94줄) — Settings 허브 보조 렌더링 — sync 상태 요약 + 시스템 정보.

- functions: render_sync_overview, render_system_info

### `views_settings_integrations.py` (315줄) — 설정 — Strava / Intervals.icu / Runalyze 연동 라우트.

- functions: strava_connect_view, strava_save_app, strava_oauth_start, strava_oauth_callback, strava_disconnect, intervals_connect_view, intervals_connect_post, intervals_disconnect, runalyze_connect_view, runalyze_connect_post, runalyze_disconnect

### `views_settings_metrics.py` (125줄) — 설정 — 메트릭 재계산 라우트 (SSE 스트림 포함).

- functions: metrics_recompute, metrics_recompute_stream, metrics_recompute_status, recompute_metrics_get

### `views_settings_render.py` (221줄) — 설정 페이지 렌더 헬퍼 — 서비스 카드 + 프로필 + Mapbox + CalDAV.

- (public API 없음)

### `views_settings_render_prefs.py` (264줄) — 설정 페이지 렌더 헬퍼 — 훈련 환경설정 + AI + 프롬프트 관리.

- (public API 없음)

### `views_shoes.py` (85줄) — 신발 목록 뷰 — Flask Blueprint.

- functions: shoes_list

### `views_sync.py` (132줄) — 동기화 탭 뷰 — 데이터 동기화 + 서비스 연결 + 임포트/익스포트.

- functions: sync_page

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

### `views_training_loaders.py` (349줄) — 훈련 계획 뷰 — 데이터 로더.

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

### `views_wellness_enhanced.py` (568줄) — 웰니스 보강 — 기준선 밴드, 패턴 인사이트, 주간 비교, 미니차트.

- functions: load_wellness_14d, load_sleep_times, load_hrv_baseline, load_weekly_comparison, render_metrics_dash, render_7day_chart_enhanced, render_sleep_mini_chart, render_hrv_mini_chart, render_pattern_insights, render_weekly_comparison, render_wellness_glossary, render_sleep_time_pattern, build_outlier_mark_points, build_pattern_recovery_tips

## `src/training/`

> 훈련 계획 및 프로그램 관리.
> 
> 설계 문서: v0.3/data/phase-7(preview).md

### `adjuster.py` (167줄) — 컨디션 기반 당일 훈련 계획 조정.

- functions: adjust_todays_plan

### `caldav_push.py` (176줄) — CalDAV 캘린더 연동 — 훈련 계획을 외부 캘린더에 등록.

- functions: push_workout_to_caldav, push_weekly_plan_to_caldav, test_connection

### `garmin_push.py` (197줄) — Garmin Connect 워크아웃 전송 — 훈련 계획을 워치 + 캘린더에 등록.

- functions: push_workout_to_garmin, push_weekly_plan

### `goals.py` (119줄) — 훈련 목표 CRUD.

- functions: add_goal, list_goals, get_goal, get_active_goal, update_goal, complete_goal, cancel_goal

### `interval_calc.py` (221줄) — 인터벌 트레이닝 처방 계산.

- functions: prescribe_interval, prescribe_from_vdot

### `matcher.py` (359줄) — 날짜 기반 계획 ↔ 실제 활동 자동 매칭 + session_outcomes 저장.

- functions: match_week_activities, save_skipped_outcome, get_actual_activities_for_week

### `planner.py` (304줄) — 규칙 기반 주간 훈련 계획 생성 (v2 — 논문 기반 재설계).

- functions: generate_weekly_plan, save_weekly_plan, get_planned_workouts, upsert_user_training_prefs

### `planner_config.py` (173줄) — 훈련 계획 — 상수 및 설정/메트릭 조회 헬퍼.

- functions: load_prefs, get_available_days, get_latest_fitness, get_vdot_adj, get_eftp, get_marathon_shape_pct, get_week_index

### `planner_rules.py` (278줄) — 훈련 계획 — 훈련 단계·볼륨·Q-day·페이스·볼륨 배분·설명 규칙.

- functions: weeks_to_race, training_phase, resolve_distance_label, weekly_volume_km, assign_qday_slots, assign_long_run_slot, get_paces_from_vdot, pace_range, distribute_volume, description

### `readiness.py` (457줄) — 훈련 준비도 분석 + 목표 달성 가능성 예측.

- functions: vdot_to_time, get_taper_weeks, get_recommended_weeks, recommend_weekly_km, get_phase_for_week, analyze_readiness

### `replanner.py` (286줄) — 건너뜀/이행 미달 시 이번 주 잔여 계획 재조정.

- functions: replan_remaining_week

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

### `activity_types.py` (84줄) — 활동 유형 정규화.

- functions: normalize_activity_type

### `api.py` (189줄) — httpx 기반 HTTP GET/POST 래퍼. 재시도 및 에러 처리.

- class **ApiError**: 없음
- functions: get, get_with_headers, post

### `clipboard.py` (44줄) — termux-clipboard-set 래퍼 유틸리티.

- functions: copy_to_clipboard, handle_clipboard_option

### `config.py` (166줄) — 설정 파일(config.json) 로드/저장 유틸리티.

- functions: get_config_path, load_config, save_config, update_service_config, redact_config_for_display

### `credential_store.py` (165줄) — 자격증명 암호화/복호화 유틸리티 (Fernet AES-128-CBC + HMAC-SHA256).

- functions: encrypt_config_credentials, decrypt_config_credentials, generate_key

### `daniels_table.py` (242줄) — Jack Daniels VDOT 룩업 테이블 — Running Formula 3rd Edition 기반.

- functions: get_training_paces, get_race_predictions, get_marathon_volume_targets, get_race_volume_targets, vdot_to_t_pace, t_pace_to_vdot

### `db_helpers.py` (694줄) — RunPulse v0.3 DB 헬퍼 유틸리티.

- functions: upsert_payload, get_payload, upsert_activity, get_activity, get_activity_list, upsert_metric, upsert_metrics_batch, get_primary_metric, get_primary_metrics, get_all_providers, get_metrics_by_category, get_metric_history, upsert_daily_wellness, upsert_daily_fitness, get_db_status, upsert_laps_batch, upsert_streams_batch, upsert_best_efforts_batch

### `dedup.py` (218줄) — 중복 활동 매칭 유틸리티 (timestamp ±5분, distance ±3%).

- functions: is_duplicate, find_duplicates, assign_group_id, auto_group_all

### `metric_groups.py` (147줄) — 메트릭 의미 그룹핑 — 소스 비교 뷰 지원 (보강 #8).

- functions: get_group_for_metric, get_group_members

### `metric_priority.py` (138줄) — RunPulse 메트릭 우선순위 해소 (Provider Priority Resolution) v0.3

- functions: get_provider_priority, resolve_primary, resolve_for_scope, resolve_all_primaries

### `metric_registry.py` (468줄) — RunPulse 메트릭 레지스트리 v0.3

- class **MetricDef**: 없음
- functions: canonicalize, get_metric, list_by_category, list_by_scope, list_unmapped_aliases

### `pace.py` (73줄) — 페이스 변환 유틸리티 (초 ↔ 분:초, km/h ↔ min/km).

- functions: seconds_to_pace, pace_to_seconds, kmh_to_pace, pace_to_kmh, format_duration

### `raw_payload.py` (160줄) — raw_source_payloads 저장/병합 유틸리티.

- functions: store_raw_payload, update_changed_fields, fill_null_columns

### `sync_jobs.py` (238줄) — 백그라운드 동기화 작업 관리 — DB 기반 상태 추적 (sync_jobs 테이블).

- class **SyncJob**: progress_pct, current_to, rate_limit
- functions: windows, cleanup_stale_running_jobs, create_job, get_job, get_active_job, update_job, list_recent_jobs

### `sync_policy.py` (176줄) — 동기화 정책 — 서비스별 rate limit / cooldown / 기간 제한 정책 정의 및 검사.

- class **SyncPolicy**: 없음
- class **SyncGuardResult**: 없음
- functions: check_incremental_guard, check_range_guard, should_reduce_expensive_calls

### `sync_state.py` (166줄) — 동기화 상태 관리 — 실행 중 여부, 마지막 동기화 시각, rate limit 상태, 오류.

- functions: get_service_state, is_running, get_last_sync_at, get_retry_after_sec, get_rate_state, get_all_states, mark_running, mark_finished, set_retry_after, clear_retry_after

### `zones.py` (90줄) — HR존 및 페이스존 계산 유틸리티.

- functions: hr_zones, get_hr_zone, pace_zones, get_pace_zone

## `tests/`

### `conftest.py` (138줄) — pytest 공통 fixture — v0.3 스키마.

- functions: db_conn, db_conn_default, db_conn_user, sample_config

### `test_activity_calcs.py` (146줄) — Activity-Scope calculator 테스트 (decoupling, gap, classifier, vdot, ef).

- class **TestDecoupling**: test_with_streams, test_too_short, test_no_streams
- class **TestGAP**: test_with_streams, test_no_streams
- class **TestClassifier**: test_easy_run, test_long_run, test_non_running
- class **TestVDOT**: test_compute, test_too_short, test_non_running
- class **TestEF**: test_compute, test_no_hr

### `test_activity_merge.py` (152줄) — 활동 그룹 병합/분리 API 엔드포인트 테스트.

- class **TestMergeEndpoint**: test_merge_two_activities, test_merge_requires_two, test_merge_missing_ids, test_merge_invalid_ids
- class **TestUngroupEndpoint**: test_ungroup_activity, test_ungroup_missing_id, test_ungroup_invalid_id
- functions: app

### `test_activity_types.py` (37줄) — activity_types.py 단위 테스트.

- class **TestNormalizeActivityType**: test_garmin_running, test_garmin_trail, test_strava_run, test_strava_trail_run, test_strava_ride, test_intervals_run, test_unknown_type_passthrough, test_empty_string, test_case_insensitive, test_cycling_variants

### `test_ai_parser.py` (154줄) — ai_parser 모듈 테스트.

- functions: test_extract_json_block_from_code_block, test_extract_json_block_bare_code_block, test_extract_json_block_no_code_block, test_extract_json_block_list, test_extract_json_block_none_when_invalid, test_extract_json_block_broken_json, test_parse_weekly_plan_valid, test_parse_weekly_plan_no_json, test_parse_weekly_plan_invalid_type, test_parse_weekly_plan_missing_date, test_parse_weekly_plan_rest_no_distance_ok, test_parse_weekly_plan_empty_workouts, test_parse_suggestions_string_list, test_parse_suggestions_dict_list, test_parse_suggestions_max_5, test_parse_suggestions_no_json, test_parse_ai_chips_basic, test_parse_ai_chips_with_id, test_parse_ai_chips_empty_on_failure

### `test_ai_schema.py` (92줄) — ai_schema 모듈 테스트.

- functions: test_validate_valid_plan, test_validate_not_dict, test_validate_no_workouts, test_validate_invalid_type, test_validate_invalid_date, test_validate_distance_out_of_range, test_validate_too_many_workouts, test_validate_rest_no_distance_ok, test_normalize_uses_type_key, test_normalize_uses_workout_type_key, test_normalize_source_is_ai, test_normalize_none_distance

### `test_api.py` (81줄) — api.py httpx 래퍼 테스트.

- class **TestGet**: test_success, test_retry_then_success, test_double_failure_raises
- class **TestPost**: test_post_json

### `test_auth_cf.py` (120줄) — auth_cf.py 테스트 — Cloudflare Zero Trust 헤더 기반 사용자 식별.

- functions: dev_app, prod_app, test_dev_cf_header_sets_session, test_dev_no_header_fallback_to_dev_user, test_dev_session_reused_without_reparse, test_dev_email_with_special_chars, test_prod_cf_header_sets_session, test_prod_no_header_returns_401, test_prod_empty_header_returns_401

### `test_cirs.py` (64줄) — CIRS (Composite Injury Risk Score) 단위 테스트 — 설계서 4-6.

- class **TestCIRS**: test_high_acwr_means_high_cirs, test_optimal_acwr_means_low_cirs, test_confidence_present, test_category_is_rp_risk, test_no_data

### `test_condition_ai_card.py` (112줄) — tests/test_condition_ai_card.py — render_condition_ai_card 단위 테스트.

- functions: test_returns_empty_when_no_data, test_shows_utrs_badge, test_utrs_green_when_high, test_utrs_red_when_low, test_cirs_badge_shown, test_cirs_red_border_when_danger, test_wellness_badges_from_adj, test_adjustment_section_when_adjusted, test_no_adjustment_section_when_not_adjusted, test_ai_section_shown_with_utrs, test_ai_override_shown, test_ai_badge_only_when_override, test_volume_boost_shown_when_applicable, test_volume_boost_hidden_when_cirs_high, test_card_title_present

### `test_config_utils.py` (99줄) — config.py 헬퍼 함수 테스트 — save_config, update_service_config, redact.

- functions: tmp_config, test_save_config_creates_file, test_save_config_roundtrip, test_save_config_overwrites, test_update_service_config_creates_file, test_update_service_config_partial_update, test_update_service_config_new_service, test_redact_masks_password, test_redact_masks_token, test_redact_does_not_mutate_original, test_redact_empty_value_unchanged

### `test_credential_store.py` (195줄) — credential_store.py 테스트 — Fernet 암호화/복호화 라운드트립.

- functions: fernet_key, with_key, without_key, production_without_key, test_roundtrip, test_non_sensitive_fields_unchanged, test_encrypted_values_have_prefix, test_no_double_encryption, test_empty_values_not_encrypted, test_plaintext_passthrough_on_decrypt, test_no_key_development_passthrough, test_no_key_production_raises, test_generate_key_is_valid_fernet_key, test_original_config_not_mutated

### `test_critical_power.py` (81줄)

- class **TestCriticalPower**: test_with_power_data, test_no_power, test_confidence

### `test_crs.py` (107줄)

- class **TestCRS**: test_full_level, test_high_acwr_restricts, test_low_body_battery, test_boost_condition, test_no_signals, test_category

### `test_daily2_calcs.py` (137줄) — Daily-Scope 2차 calculator 테스트.

- class **TestUTRS**: test_with_wellness_and_tsb, test_no_data
- class **TestCIRS**: test_with_metrics, test_no_data
- class **TestFEARP**: test_compute, test_non_running
- class **TestRMR**: test_with_wellness, test_no_data
- class **TestADTI**: test_with_ctl_series, test_insufficient_data

### `test_daily_calcs.py` (110줄) — Daily-Scope 1차 calculator 테스트 (PMC, ACWR, LSI, Monotony).

- class **TestPMC**: test_compute, test_no_data
- class **TestACWR**: test_compute, test_no_ctl
- class **TestLSI**: test_compute, test_no_today
- class **TestMonotony**: test_compute, test_no_data

### `test_daniels_table.py` (78줄) — daniels_table 유틸리티 테스트.

- class **TestTrainingPaces**: test_vdot_50_paces, test_interpolation, test_boundary_low, test_boundary_high
- class **TestRacePredictions**: test_vdot_50_predictions, test_sub3_marathon
- class **TestVolume**: test_marathon_volume, test_race_volume_half, test_race_volume_10k
- class **TestTpaceConversion**: test_vdot_to_t_pace, test_t_pace_to_vdot_roundtrip, test_t_pace_to_vdot_interpolated

### `test_db_helpers.py` (235줄) — db_helpers.py 단위 테스트 — Phase 1 조건 8, 9

- class **TestUpsertActivitySummary**: test_insert_new, test_upsert_updates, test_no_duplicate_rows
- class **TestUpsertMetric**: test_insert_single, test_batch_upsert, test_upsert_updates_value
- class **TestUpsertDailyWellness**: test_insert, test_merge_keeps_first_non_null
- class **TestGetPrimaryMetrics**: test_get_primary_returns_list, test_get_all_providers, test_get_primary_empty_scope
- class **TestUpsertPayload**: test_insert_and_no_change, test_update_on_change
- class **TestDailyFitness**: test_insert, test_upsert_coalesce
- class **TestDbStatus**: test_returns_dict
- functions: db

### `test_db_helpers_batch.py` (101줄) — db_helpers batch 함수 테스트 (Phase 3 추가분).

- class **TestLapsBatch**: test_insert_laps, test_upsert_laps_update, test_skip_no_lap_index
- class **TestStreamsBatch**: test_insert_streams, test_replace_on_reinsert
- class **TestBestEffortsBatch**: test_insert_efforts, test_upsert_effort, test_skip_no_effort_name

### `test_db_setup.py` (150줄) — db_setup 테스트.

- class **TestPhase1Schema**: setup_db, test_schema_version_is_10, test_pipeline_tables_count, test_app_tables_exist, test_canonical_view_exists, test_activity_summaries_46_columns
- functions: test_get_db_path, test_create_tables, test_daily_fitness_unique_constraint, test_planned_workouts_new_columns, test_migrate_db_idempotent, test_migrate_db_adds_daily_fitness, test_activities_unique_index, test_activities_insert

### `test_dedup.py` (74줄) — Dedup 단위 테스트.

- class **TestDedup**: test_same_activity_different_sources, test_different_activities_not_grouped, test_same_source_not_grouped, test_distance_threshold_exceeded, test_three_sources_same_activity, test_no_distance_falls_back_to_time

### `test_doc_sync.py` (97줄) — 문서 동기화 검증 테스트.

- class **TestMetricDictionarySync**: setup, test_dictionary_exists, test_calculator_count_matches, test_group_count_matches, test_all_calculators_documented, test_all_groups_documented, test_no_outdated_table_count

### `test_eftp.py` (70줄)

- class **TestEFTP**: test_from_vdot, test_no_vdot, test_confidence

### `test_engine.py` (117줄) — Metrics Engine 통합 테스트.

- class **TestTopologicalSort**: test_trimp_before_hrss, test_pmc_before_acwr, test_acwr_before_cirs, test_all_calculators_included
- class **TestRunActivityMetrics**: test_produces_metrics, test_metrics_in_store
- class **TestRunDailyMetrics**: test_with_trimp
- class **TestRunForDate**: test_full_pipeline
- class **TestClearRunpulse**: test_clears_only_runpulse

### `test_extractor_base.py` (76줄) — BaseExtractor와 MetricRecord 단위 테스트.

- class **DummyExtractor**: extract_activity_core, extract_activity_metrics
- class **TestMetricRecord**: test_is_empty_all_none, test_is_not_empty_numeric, test_is_not_empty_text, test_is_not_empty_json
- class **TestBaseExtractorHelpers**: setup_method, test_metric_returns_none_when_all_none, test_metric_returns_record_with_value, test_metric_with_text, test_metric_with_json, test_collect_filters_none, test_default_methods_return_empty

### `test_extractors_cross.py` (305줄) — Cross-extractor 일관성 테스트.

- class **TestGetExtractorFactory**: test_returns_correct_instance, test_case_insensitive, test_unknown_source_raises, test_returns_new_instance_each_call
- class **TestCoreKeysConsistency**: test_required_keys_present, test_all_keys_are_valid_columns, test_no_none_values_in_output
- class **TestMetricNoDuplicateWithCore**: test_no_overlap
- class **TestAllMetricsHaveCategory**: test_category_set, test_no_empty_metrics
- class **TestDistanceUnit**: test_distance_key_is_meters
- class **TestSecondsHelper**: test_already_seconds, test_milliseconds_conversion, test_none_returns_none, test_boundary_86400, test_exactly_86400, test_float_input
- class **TestCrossExtractorConsistency**: test_all_extractors_registered, test_all_have_unique_source, test_source_field_matches_class_source, test_activity_type_is_normalized, test_source_url_contains_source_id, test_all_extractors_inherit_base, test_pace_sec_km_reasonable, test_duration_sec_reasonable

### `test_fixture_loader.py` (17줄)

- functions: test_fixture_root_exists, test_fixture_path_resolves_readme, test_read_text_fixture_reads_readme

### `test_fixtures_layout.py` (21줄)

- functions: test_fixtures_layout_exists

### `test_garmin_activity_sync.py` (159줄) — DoD #6: Garmin activity sync 흐름 — mock API 기반.

- class **TestGarminActivitySync**: test_sync_empty_list, test_sync_one_activity, test_sync_skip_unchanged, test_sync_with_streams, test_sync_rate_limit_error, test_sync_detail_failure_continues, test_primary_resolution

### `test_garmin_extractor.py` (169줄) — Garmin Extractor 단위 테스트.

- class **TestGarminActivityCore**: test_required_fields, test_distance_and_time, test_pace_calculated, test_heart_rate, test_training_effects, test_running_dynamics, test_location, test_no_none_values, test_source_url, test_empty_input_returns_minimal
- class **TestGarminActivityMetrics**: test_basic_metrics, test_no_empty_metrics, test_detail_hr_zones, test_detail_weather, test_no_core_duplicates
- class **TestGarminLaps**: test_lap_extraction, test_lap_pace_calculated, test_empty_detail
- class **TestGarminWellness**: test_wellness_core, test_wellness_metrics, test_wellness_metric_values, test_fitness
- functions: ext, summary_raw, detail_raw, wellness_raw

### `test_garmin_wellness_sync.py` (125줄) — DoD #7: Garmin wellness sync 6 endpoint — mock API 기반.

- class **TestGarminWellnessSync**: test_sync_one_day, test_sync_multi_day, test_sync_skip_unchanged, test_sync_stores_raw_payloads, test_sync_metrics_created, test_sync_partial_endpoint_failure

### `test_goals.py` (116줄) — goals.py 테스트.

- functions: test_add_goal_returns_id, test_get_goal, test_get_goal_not_found, test_list_goals_active_default, test_list_goals_all, test_get_active_goal_returns_latest, test_get_active_goal_none_when_empty, test_update_goal, test_update_goal_invalid_field, test_complete_goal, test_cancel_goal, test_complete_nonexistent_goal, test_cancel_nonexistent_goal, test_list_goals_empty, test_add_goal_minimal

### `test_intervals_extractor.py` (85줄) — Intervals.icu Extractor 단위 테스트.

- class **TestIntervalsActivityCore**: test_required_fields, test_distance_time, test_stride_length_converted, test_training_load
- class **TestIntervalsActivityMetrics**: test_training_metrics, test_hr_zones, test_metric_values
- class **TestIntervalsWellness**: test_wellness_core, test_fitness
- functions: ext, activity_raw, wellness_raw

### `test_intervals_sync.py` (148줄) — DoD #9: Intervals.icu activity + wellness sync — mock 기반.

- class **TestIntervalsActivitySync**: test_sync_one_activity, test_sync_empty, test_sync_skip_unchanged, test_sync_no_credentials
- class **TestIntervalsWellnessSync**: test_wellness_sync, test_wellness_skip_unchanged, test_wellness_fitness_stored

### `test_marathon_shape.py` (83줄)

- class **TestMarathonShape**: test_with_data, test_no_vdot, test_json_structure

### `test_metric_naming.py` (50줄) — 메트릭 이름 충돌 방지 검증 테스트 (보강 #9).

- class **TestMetricNaming**: test_no_calculator_uses_activity_summary_column_name, test_no_duplicate_produces_across_calculators, test_all_produces_are_non_empty, test_all_names_are_unique

### `test_metric_priority.py` (100줄) — metric_priority.py 단위 테스트 — Phase 1 조건 7

- class **TestProviderPriority**: test_user_highest, test_garmin_before_strava, test_runpulse_ml_before_garmin, test_unknown_provider_low_priority
- class **TestResolvePrimary**: test_single_provider, test_multi_provider_garmin_wins, test_user_override_wins, test_resolve_for_scope
- functions: db

### `test_metric_registry.py` (64줄) — metric_registry.py 단위 테스트 — Phase 1 조건 5, 6

- class **TestMetricDefinitions**: test_metric_count_minimum, test_no_alias_collision, test_all_metrics_have_category, test_all_metrics_have_unit, test_categories_non_empty
- class **TestCanonicalize**: test_canonical_name_returns_itself, test_alias_resolves, test_unknown_returns_none_or_input, test_get_metric_returns_metric_def

### `test_mock_calcs.py` (127줄) — MockCalcContext를 활용한 calculator 단위 테스트 (보강 #5).

- class **TestTRIMPMock**: test_basic, test_no_hr, test_short_duration
- class **TestHRSSMock**: test_with_trimp, test_no_trimp
- class **TestEFMock**: test_basic, test_no_hr
- class **TestVDOTMock**: test_10k, test_non_running
- class **TestConfidenceBuilder**: test_all_available, test_partial_available, test_estimated_penalty, test_empty, test_mixed

### `test_orchestrator.py` (115줄) — DoD #11: orchestrator.full_sync + sync_jobs 기록.

- class **TestFullSync**: test_no_clients_all_skipped, test_garmin_sync_records_job, test_multi_source_sync, test_dedup_runs_after_sync, test_sync_jobs_have_dates

### `test_pace.py` (74줄) — pace 유틸리티 테스트.

- class **TestSecondsToPace**: test_even_minutes, test_with_seconds, test_single_digit_seconds, test_fast_pace
- class **TestPaceToSeconds**: test_even_minutes, test_with_seconds, test_roundtrip
- class **TestKmhToPace**: test_12kmh, test_10kmh, test_zero_raises
- class **TestPaceToKmh**: test_300sec, test_360sec, test_zero_raises
- class **TestFormatDuration**: test_under_hour, test_over_hour, test_zero, test_exact_hour

### `test_phase1_schema.py` (778줄) — Phase 1 스키마 & 기반 인프라 테스트.

- class **TestSchemaCreation**: test_all_pipeline_tables_exist, test_all_app_tables_exist, test_canonical_view_exists, test_schema_version, test_activity_summaries_column_count, test_distance_is_meters_not_km, test_metric_store_columns, test_daily_wellness_no_source_column
- class **TestConstraints**: test_activity_summaries_unique, test_metric_store_unique, test_metric_store_same_name_different_provider, test_daily_wellness_unique_date, test_daily_fitness_unique_date_source
- class **TestCanonicalView**: test_canonical_returns_one_per_group, test_canonical_prefers_garmin, test_canonical_intervals_second_priority
- class **TestMetricRegistry**: test_registry_size, test_canonicalize_garmin_alias, test_canonicalize_intervals_trimp, test_canonicalize_direct_name, test_canonicalize_unmapped, test_get_metric_exists, test_get_metric_not_exists, test_list_by_category, test_list_by_scope, test_all_categories_documented
- class **TestMetricPriority**: test_user_highest_priority, test_runpulse_ml_higher_than_formula, test_runpulse_higher_than_garmin, test_garmin_higher_than_strava, test_unknown_provider, test_resolve_primary_basic, test_user_override, test_resolve_for_scope
- class **TestDbHelpers**: test_upsert_payload_new, test_upsert_payload_unchanged, test_upsert_payload_changed, test_get_payload, test_upsert_activity, test_upsert_activity_update, test_upsert_metric_and_get_primary, test_upsert_metrics_batch, test_get_all_providers, test_get_metrics_by_category, test_upsert_daily_wellness_merge, test_upsert_daily_fitness, test_get_db_status, test_get_activity_list
- class **TestMigration**: test_migrate_idempotent, test_create_tables_idempotent
- class **TestPerformance**: test_activity_list_under_200ms, test_metric_store_bulk_insert
- class **TestRealDbDefault**: test_existing_tables, test_migrate_creates_new_tables, test_existing_data_preserved, test_schema_version_updated
- class **TestRealDbUser**: test_has_real_data, test_migrate_preserves_data, test_migrate_adds_metric_store, test_source_payloads_exist, test_source_distribution, test_canonical_view_after_migrate, test_daily_wellness_has_data, test_db_summary

### `test_phase4_dod.py` (322줄) — Phase 4 DoD (Definition of Done) 검증 테스트 — 설계서 4-8 기준.

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

### `test_pmc.py` (72줄) — PMC (Performance Management Chart) 단위 테스트 — 설계서 4-6.

- class **TestPMC**: test_produces_four_metrics, test_ctl_increases_with_training, test_tsb_negative_after_hard_training, test_no_data

### `test_rate_limiter.py` (52줄) — RateLimiter 단위 테스트.

- class **TestRateLimitPolicy**: test_four_sources_defined, test_garmin_conservative, test_strava_window
- class **TestRateLimiter**: test_call_count, test_handle_rate_limit_retry, test_429_reset_on_success, test_should_stop_daily, test_unknown_source_default

### `test_raw_payload.py` (209줄) — raw_source_payloads 저장/병합 유틸리티 테스트.

- class **TestStoreRawPayload**: test_insert_new, test_merge_preserves_existing_keys, test_merge_new_value_overrides, test_activity_id_set_on_insert, test_activity_id_coalesce_on_update, test_activity_id_updated_when_provided, test_empty_payload_skipped, test_none_payload_skipped, test_different_sources_same_entity_id, test_graceful_on_missing_table, test_updated_at_changes_on_merge
- class **TestFillNullColumns**: test_fills_null_hr, test_does_not_overwrite_existing_value, test_multiple_columns, test_none_values_skipped, test_returns_activity_id, test_returns_none_if_not_found, test_partial_override
- functions: conn

### `test_raw_store.py` (48줄) — raw_store 단위 테스트.

- class **TestUpsertRawPayload**: test_new_payload_returns_true, test_same_payload_returns_false, test_changed_payload_returns_true, test_row_count
- class **TestUpdateRawActivityId**: test_sets_activity_id

### `test_readiness.py` (236줄) — src/training/readiness.py 단위 테스트.

- class **TestVdotFormulas**: test_vdot_from_5k_known, test_vdot_from_marathon_known, test_vdot_from_race_invalid, test_vdot_to_time_roundtrip, test_vdot_to_time_invalid, test_vdot_to_time_higher_vdot_faster
- class **TestDistanceRules**: test_taper_5k, test_taper_10k, test_taper_half, test_taper_full, test_recommended_5k, test_recommended_full, test_recommended_half
- class **TestPhaseForWeek**: test_last_week_is_taper, test_second_to_last_is_taper_too, test_first_week_is_base, test_mid_week_is_build, test_late_week_is_peak
- class **TestRecommendWeeklyKm**: test_base_lower_than_build, test_taper_lowest, test_recovery_week_lower, test_higher_vdot_higher_km, test_returns_positive
- class **TestAnalyzeReadiness**: test_no_vdot_returns_zero_pct, test_easy_goal_high_pct, test_hard_goal_lower_pct, test_moderate_goal_reasonable_pct, test_below_min_weeks_capped, test_recommended_weeks_structure, test_projected_times_make_sense, test_status_summary_not_empty, test_weekly_vdot_gain_positive
- functions: empty_conn, populated_conn

### `test_rec.py` (81줄)

- class **TestREC**: test_with_data, test_no_ef, test_category

### `test_relative_effort.py` (116줄)

- class **TestRelativeEffort**: test_from_avg_hr, test_high_intensity, test_low_intensity, test_no_hr, test_confidence_from_avg_hr, test_category
- class **TestRelativeEffortMock**: test_basic_mock, test_no_hr_mock

### `test_replanner.py` (220줄) — replanner.py 테스트 — 재조정 규칙 (고강도 이동, 볼륨 축소, 테이퍼 보호).

- functions: test_rule1_interval_moved_to_easy_day, test_rule1_tempo_moved, test_rule1_easy_not_moved, test_rule1_no_available_slot, test_rule2_consecutive_skips_reduce_volume, test_rule3_low_dist_ratio_warning, test_rule4_taper_no_move, test_result_has_required_keys, test_unknown_workout_id_returns_error

### `test_reprocess.py` (248줄) — DoD #4 (reprocess): Layer 0 → Layer 1/2 재구축 테스트.

- class **TestReprocessActivity**: test_rebuilds_from_raw, test_metrics_rebuilt, test_primary_resolved, test_preserves_raw, test_clears_derived_only, test_no_clear_accumulates
- class **TestReprocessWellness**: test_wellness_rebuilt, test_wellness_metrics_rebuilt
- class **TestReprocessSourceFilter**: test_source_filter
- class **TestReprocessDedup**: test_dedup_runs

### `test_round2.py` (130줄) — 라운드 2 테스트: ComputeResult, compute_for_activities/dates, recompute_single_metric, integration.

- class **TestComputeResult**: test_summary, test_defaults
- class **TestComputeForActivities**: test_basic, test_empty_list
- class **TestComputeForDates**: test_basic, test_empty_dates
- class **TestRecomputeSingleMetric**: test_trimp, test_invalid_metric
- class **TestIntegration**: test_compute_metrics_after_sync

### `test_round4.py` (88줄) — 라운드 4 테스트: 메타데이터, semantic grouping, CLI.

- class **TestCalculatorMetadata**: test_all_have_display_name, test_all_have_description, test_format_types_valid, test_ranges_are_dict_or_none, test_groups_have_members, test_get_group_for_metric, test_get_group_members, test_get_group_members_nonexistent
- class **TestCLI**: test_status_empty, test_status_with_data, test_cli_no_command

### `test_rri.py` (108줄)

- class **TestRRI**: test_with_all_inputs, test_high_cirs_lowers_rri, test_no_vdot, test_category
- class **TestRRIMock**: test_with_all_inputs_mock, test_no_vdot_mock

### `test_rtti.py` (102줄)

- class **TestRTTI**: test_optimal, test_overload, test_no_data, test_category
- class **TestRTTIMock**: test_optimal_mock, test_no_data_mock

### `test_runalyze_extractor.py` (58줄) — Runalyze Extractor 단위 테스트.

- class **TestRunalyzeActivityCore**: test_required_fields, test_distance_time, test_pace_calculated
- class **TestRunalyzeActivityMetrics**: test_fitness_metrics, test_race_predictions, test_trimp
- functions: ext, activity_raw

### `test_runalyze_sync.py` (106줄) — DoD #10: Runalyze basic sync — mock 기반.

- class **TestRunalyzeSync**: test_sync_one_activity, test_sync_empty, test_sync_skip_unchanged, test_sync_no_token, test_sync_dict_response, test_metrics_stored

### `test_sapi.py` (112줄)

- class **TestSAPI**: test_with_fearp_data, test_no_fearp, test_category

### `test_strava_extractor.py` (94줄) — Strava Extractor 단위 테스트.

- class **TestStravaActivityCore**: test_required_fields, test_distance_time, test_suffer_score, test_latlng, test_source_url, test_no_none_values
- class **TestStravaActivityMetrics**: test_basic_metrics, test_splits_as_json
- class **TestStravaBestEfforts**: test_extraction
- class **TestStravaStreams**: test_stream_extraction, test_empty_streams
- functions: ext, activity_raw

### `test_strava_sync.py` (140줄) — DoD #8: Strava sync — OAuth + detail + streams mock 기반.

- class **TestStravaActivitySync**: test_sync_one_activity, test_sync_with_best_efforts, test_sync_empty_list, test_sync_skip_unchanged, test_sync_no_token

### `test_sync_result.py` (39줄) — SyncResult 단위 테스트.

- class **TestSyncResult**: test_defaults, test_rate_limited, test_merge, test_merge_failed_becomes_partial, test_to_sync_job_dict

### `test_teroi.py` (85줄)

- class **TestTEROI**: test_with_data, test_no_trimp, test_category

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

### `test_training_workout_edit.py` (204줄) — Phase D: 워크아웃 편집 AJAX 라우트 테스트.

- class **TestWorkoutPatch**: test_patch_type_and_distance, test_patch_pace, test_patch_interval_saves_description, test_patch_empty_body_returns_400, test_patch_nonexistent_db, test_patch_persists_to_db
- class **TestIntervalCalc**: test_basic_1000m, test_200m_short_interval, test_nonstandard_distance_warning, test_default_params
- functions: app, client, db_file, workout_id

### `test_trimp_calc.py` (89줄) — TRIMP + HRSS calculator 테스트 — 설계서 4-2 기준.

- class **TestTRIMPCalculator**: test_compute, test_no_hr, test_uses_wellness_rest_hr, test_confidence_without_measured_max
- class **TestHRSSCalculator**: test_compute, test_no_trimp

### `test_unified_activities.py` (338줄) — unified_activities 서비스 테스트.

- class **TestPickValue**: test_garmin_first, test_fallback_when_garmin_missing, test_none_when_all_missing, test_all_values_populated, test_service_priority_order
- class **TestBuildUnifiedActivity**: test_single_source, test_multi_source_group, test_representative_id_garmin_first, test_date_property, test_effective_group_id_solo, test_effective_group_id_real_group
- class **TestBuildSourceComparison**: test_returns_list_of_dicts, test_field_names_present, test_values_per_source, test_missing_source_not_in_row, test_unified_value_and_source_present, test_unified_source_fallback, test_unified_value_none_when_all_missing
- class **TestFetchUnifiedActivities**: test_returns_solo_activities, test_groups_by_matched_group_id, test_grouped_activity_has_both_sources, test_pagination, test_stats_total_dist, test_date_filter, test_source_filter
- class **TestGroupOperations**: test_assign_creates_group, test_assign_requires_two, test_remove_from_group
- functions: mem_db

### `test_utrs.py` (96줄) — UTRS (Unified Training Readiness Score) 단위 테스트 — 설계서 4-6.

- class **TestUTRS**: test_full_inputs_confidence_1, test_partial_inputs_lower_confidence, test_three_inputs_confidence, test_score_range, test_json_has_components, test_no_inputs

### `test_vdot_adj.py` (71줄)

- class **TestVDOTAdj**: test_passthrough, test_no_vdot, test_confidence

### `test_wlei.py` (105줄)

- class **TestWLEI**: test_basic, test_hot_weather, test_cold_weather, test_no_trimp, test_json_value, test_confidence

### `test_zones.py` (64줄) — zones 유틸리티 테스트.

- class **TestHrZones**: test_returns_5_zones, test_zone_boundaries, test_zones_ascending
- class **TestGetHrZone**: test_zone1, test_zone3, test_zone5, test_zero_hr, test_above_max
- class **TestPaceZones**: test_returns_5_zones, test_zone1_slowest
- class **TestGetPaceZone**: test_easy_pace, test_threshold_pace, test_vo2max_pace, test_zero_pace

## `scripts/`

### `check_docs.py` (698줄) — 문서 정합성 검증 스크립트 (v0.3 Phase 5 확장판).

- functions: check, section, error, warn, ok, check_backlog, check_files_index, check_line_count, check_pytest_collect, check_metric_dictionary, check_calculator_count, check_semantic_groups, check_test_file_count, check_outdated, check_phase_summary_files, check_schema_columns, check_category_triple, check_db_helpers_functions, check_doc_numbers, check_docstrings, main

### `encrypt_existing_configs.py` (153줄) — 기존 config.json 파일의 자격증명을 Fernet으로 암호화하는 마이그레이션 스크립트.

- functions: main

### `gen_files_index.py` (137줄) — files_index.md 자동 생성.

- functions: get_docstring, get_docstring_first_line, get_public_api, main

### `gen_metric_dictionary.py` (252줄) — 메트릭 사전 (metric_dictionary.md) 자동 생성.

- functions: generate, get_structural_fingerprint

---
총 277개 파일

## docstring 누락

- `src/sync/garmin.py`
- `src/sync/garmin_api_extensions.py`
- `src/sync/garmin_athlete_extensions.py`
- `src/sync/garmin_auth.py`
- `src/sync/garmin_daily_extensions.py`
- `src/sync/garmin_helpers.py`
- `src/web/bg_sync.py`
- `tests/__init__.py`
- `tests/test_critical_power.py`
- `tests/test_crs.py`
- `tests/test_eftp.py`
- `tests/test_fixture_loader.py`
- `tests/test_fixtures_layout.py`
- `tests/test_marathon_shape.py`
- `tests/test_rec.py`
- `tests/test_relative_effort.py`
- `tests/test_rri.py`
- `tests/test_rtti.py`
- `tests/test_sapi.py`
- `tests/test_teroi.py`
- `tests/test_tpdi.py`
- `tests/test_vdot_adj.py`
- `tests/test_wlei.py`