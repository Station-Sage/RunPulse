# RunPulse v0.3 — 파일 인덱스

> 자동 생성: 2026-04-04
> 총 테스트: **791 passed** | 32 metric calculators | 4 data sources | 74 test files

## 1. 진입점 스크립트

| 파일 | 줄수 | 크기 | 역할 |
|------|------|------|------|
| `src/__init__.py` | 0 | 0 B |  |
| `src/analyze.py` | 217 | 7.0 KB |  |
| `src/db_setup.py` | 680 | 23.3 KB | DB 스키마 생성 (16 tables) |
| `src/import_history.py` | 379 | 13.2 KB |  |
| `src/mcp_server.py` | 163 | 4.1 KB |  |
| `src/plan.py` | 213 | 7.4 KB |  |
| `src/serve.py` | 19 | 494 B | Flask 개발 서버 실행 |
| `src/sync.py` | 96 | 3.4 KB |  |
| `src/sync_cli.py` | 115 | 3.4 KB | sync CLI (garmin/strava/intervals/runalyze) |

## 2. Metrics 엔진 (`src/metrics/`)

### 코어
| 파일 | 줄수 | 역할 |
|------|------|------|
| `__init__.py` | 0 | 패키지 init |
| `base.py` | 440 | MetricCalculator ABC, CalcResult, CalcContext (13 API + prefetch), ConfidenceBuilder |
| `engine.py` | 639 | ALL_CALCULATORS 등록, _save_results, run_activity/daily_metrics |
| `cli.py` | 122 | CLI: status, recompute, validate |

### Calculator 모듈 (32개)
| 파일 | 줄수 | scope | category |
|------|------|-------|----------|
| `acwr.py` | 35 | daily | rp_load |
| `adti.py` | 48 | daily | rp_trend |
| `cirs.py` | 106 | daily | rp_risk |
| `classifier.py` | 120 | activity | rp_classification |
| `critical_power.py` | 106 | activity | rp_performance |
| `crs.py` | 208 | daily | rp_readiness |
| `darp.py` | 69 | daily | rp_prediction |
| `decoupling.py` | 64 | activity | rp_efficiency |
| `di.py` | 59 | daily | rp_endurance |
| `efficiency.py` | 35 | activity | rp_efficiency |
| `eftp.py` | 107 | daily | rp_performance |
| `fearp.py` | 73 | activity | rp_performance |
| `gap.py` | 71 | activity | rp_performance |
| `hrss.py` | 53 | activity | rp_load |
| `lsi.py` | 55 | daily | rp_load |
| `marathon_shape.py` | 105 | daily | rp_performance |
| `monotony.py` | 61 | daily | rp_load |
| `pmc.py` | 80 | daily | rp_load |
| `rec.py` | 77 | daily | rp_efficiency |
| `relative_effort.py` | 76 | activity | rp_load |
| `reprocess.py` | 87 | — | 인프라 (재처리) |
| `rmr.py` | 66 | daily | rp_recovery |
| `rri.py` | 74 | daily | rp_performance |
| `rtti.py` | 81 | daily | rp_load |
| `sapi.py` | 141 | daily | rp_performance |
| `teroi.py` | 77 | daily | rp_trend |
| `tids.py` | 61 | daily | rp_distribution |
| `tpdi.py` | 79 | daily | rp_trend |
| `trimp.py` | 85 | activity | rp_load |
| `utrs.py` | 90 | daily | rp_readiness |
| `vdot.py` | 66 | activity | rp_performance |
| `vdot_adj.py` | 150 | daily | rp_performance |
| `wlei.py` | 80 | activity | rp_load |

## 3. 유틸리티 (`src/utils/`)

| 파일 | 줄수 | 역할 |
|------|------|------|
| `__init__.py` | 0 |  |
| `activity_types.py` | 84 |  |
| `api.py` | 189 |  |
| `clipboard.py` | 44 |  |
| `config.py` | 166 |  |
| `credential_store.py` | 165 |  |
| `daniels_table.py` | 242 | VDOT 테이블, 페이스 변환 |
| `db_helpers.py` | 694 | upsert_metric, upsert_metrics_batch, DB 유틸 |
| `dedup.py` | 218 |  |
| `metric_groups.py` | 155 | SEMANTIC_GROUPS (13개), get_group_for_metric() |
| `metric_priority.py` | 138 | PROVIDER_PRIORITY, resolve_primary/resolve_for_scope |
| `metric_registry.py` | 468 | MetricDef 등록, CATEGORY_LABELS, METRIC_REGISTRY |
| `pace.py` | 73 |  |
| `raw_payload.py` | 160 |  |
| `sync_jobs.py` | 238 |  |
| `sync_policy.py` | 176 |  |
| `sync_state.py` | 166 |  |
| `zones.py` | 90 |  |

## 4. Sync 파이프라인 (`src/sync/`)

| 파일 | 줄수 |
|------|------|
| `__init__.py` | 5 |
| `_helpers.py` | 132 |
| `dedup.py` | 85 |
| `extractors/__init__.py` | 51 |
| `extractors/base.py` | 139 |
| `extractors/garmin_extractor.py` | 575 |
| `extractors/intervals_extractor.py` | 201 |
| `extractors/runalyze_extractor.py` | 102 |
| `extractors/strava_extractor.py` | 211 |
| `garmin.py` | 193 |
| `garmin_activity_sync.py` | 226 |
| `garmin_api_extensions.py` | 400 |
| `garmin_athlete_extensions.py` | 177 |
| `garmin_auth.py` | 129 |
| `garmin_backfill.py` | 209 |
| `garmin_daily_extensions.py` | 472 |
| `garmin_helpers.py` | 113 |
| `garmin_v2_mappings.py` | 289 |
| `garmin_wellness_sync.py` | 138 |
| `integration.py` | 55 |
| `intervals.py` | 55 |
| `intervals_activity_sync.py` | 168 |
| `intervals_athlete_sync.py` | 120 |
| `intervals_auth.py` | 58 |
| `intervals_wellness_sync.py` | 111 |
| `orchestrator.py` | 114 |
| `rate_limiter.py` | 137 |
| `raw_store.py` | 46 |
| `reprocess.py` | 291 |
| `runalyze.py` | 300 |
| `runalyze_activity_sync.py` | 86 |
| `strava.py` | 67 |
| `strava_activity_sync.py` | 164 |
| `strava_athlete_sync.py` | 188 |
| `strava_auth.py` | 91 |
| `sync_result.py` | 65 |

## 5. AI 엔진 (`src/ai/`)

| 파일 | 줄수 |
|------|------|
| `__init__.py` | 1 |
| `ai_cache.py` | 152 |
| `ai_context.py` | 347 |
| `ai_message.py` | 311 |
| `ai_parser.py` | 125 |
| `ai_schema.py` | 121 |
| `ai_validator.py` | 127 |
| `briefing.py` | 101 |
| `chat_context.py` | 81 |
| `chat_context_builders.py` | 287 |
| `chat_context_format.py` | 266 |
| `chat_context_intent.py` | 83 |
| `chat_context_rich.py` | 192 |
| `chat_context_utils.py` | 32 |
| `chat_engine.py` | 208 |
| `chat_engine_providers.py` | 380 |
| `chat_engine_rules.py` | 259 |
| `context_builders.py` | 426 |
| `genspark_driver.py` | 384 |
| `prompt_config.py` | 244 |
| `suggestions.py` | 171 |
| `tools.py` | 547 |

## 6. Training 엔진 (`src/training/`)

| 파일 | 줄수 |
|------|------|
| `__init__.py` | 11 |
| `adjuster.py` | 167 |
| `caldav_push.py` | 176 |
| `garmin_push.py` | 197 |
| `goals.py` | 119 |
| `interval_calc.py` | 221 |
| `matcher.py` | 359 |
| `planner.py` | 304 |
| `planner_config.py` | 173 |
| `planner_rules.py` | 278 |
| `readiness.py` | 457 |
| `replanner.py` | 286 |

## 7. Web 뷰 (`src/web/`)

### Python 뷰
| 파일 | 줄수 |
|------|------|
| `__init__.py` | 0 |
| `app.py` | 950 |
| `auth_cf.py` | 82 |
| `bg_sync.py` | 407 |
| `helpers.py` | 931 |
| `helpers_svg.py` | 171 |
| `route_svg.py` | 136 |
| `sync_ui.py` | 238 |
| `views_activities.py` | 184 |
| `views_activities_filter.py` | 214 |
| `views_activities_helpers.py` | 264 |
| `views_activities_table.py` | 423 |
| `views_activity.py` | 339 |
| `views_activity_cards_common.py` | 317 |
| `views_activity_g1_status.py` | 142 |
| `views_activity_g2_performance.py` | 206 |
| `views_activity_g3_load.py` | 119 |
| `views_activity_g4_risk.py` | 87 |
| `views_activity_g5_biomechanics.py` | 104 |
| `views_activity_g6_distribution.py` | 161 |
| `views_activity_g7_fitness.py` | 170 |
| `views_activity_loaders.py` | 315 |
| `views_activity_loaders_v2.py` | 104 |
| `views_activity_map.py` | 98 |
| `views_activity_merge.py` | 132 |
| `views_activity_s5_cards.py` | 277 |
| `views_activity_source_cards.py` | 436 |
| `views_ai_coach.py` | 402 |
| `views_ai_coach_cards.py` | 588 |
| `views_dashboard.py` | 436 |
| `views_dashboard_cards.py` | 34 |
| `views_dashboard_cards_fitness.py` | 280 |
| `views_dashboard_cards_recommend.py` | 267 |
| `views_dashboard_cards_risk.py` | 185 |
| `views_dashboard_cards_status.py` | 145 |
| `views_dashboard_loaders.py` | 127 |
| `views_dev.py` | 589 |
| `views_export_import.py` | 233 |
| `views_guide.py` | 240 |
| `views_import.py` | 311 |
| `views_perf.py` | 160 |
| `views_race.py` | 408 |
| `views_race_enhanced.py` | 422 |
| `views_report.py` | 349 |
| `views_report_charts.py` | 335 |
| `views_report_loaders.py` | 179 |
| `views_report_sections.py` | 312 |
| `views_report_sections_cards.py` | 276 |
| `views_report_sections_data.py` | 112 |
| `views_settings.py` | 320 |
| `views_settings_garmin.py` | 422 |
| `views_settings_hub.py` | 94 |
| `views_settings_integrations.py` | 315 |
| `views_settings_metrics.py` | 125 |
| `views_settings_render.py` | 221 |
| `views_settings_render_prefs.py` | 264 |
| `views_shoes.py` | 85 |
| `views_sync.py` | 132 |
| `views_training.py` | 349 |
| `views_training_cal_js.py` | 313 |
| `views_training_cards.py` | 372 |
| `views_training_condition.py` | 152 |
| `views_training_crud.py` | 468 |
| `views_training_export.py` | 117 |
| `views_training_fullplan.py` | 260 |
| `views_training_goal_crud.py` | 387 |
| `views_training_goals.py` | 486 |
| `views_training_loaders.py` | 349 |
| `views_training_month.py` | 211 |
| `views_training_plan_ui.py` | 247 |
| `views_training_prefs.py` | 207 |
| `views_training_shared.py` | 31 |
| `views_training_week.py` | 293 |
| `views_training_wellness.py` | 320 |
| `views_training_wizard.py` | 413 |
| `views_training_wizard_render.py` | 343 |
| `views_wellness.py` | 440 |
| `views_wellness_enhanced.py` | 568 |

### 템플릿 (HTML)
| 파일 | 줄수 |
|------|------|

## 8. 테스트 (`tests/`)

| 파일 | 줄수 |
|------|------|
| `test_activity_calcs.py` | 146 |
| `test_activity_merge.py` | 152 |
| `test_activity_types.py` | 37 |
| `test_ai_parser.py` | 154 |
| `test_ai_schema.py` | 92 |
| `test_api.py` | 81 |
| `test_auth_cf.py` | 120 |
| `test_condition_ai_card.py` | 112 |
| `test_config_utils.py` | 99 |
| `test_credential_store.py` | 195 |
| `test_daily2_calcs.py` | 131 |
| `test_daily_calcs.py` | 107 |
| `test_daniels_table.py` | 78 |
| `test_db_helpers.py` | 235 |
| `test_db_helpers_batch.py` | 101 |
| `test_db_setup.py` | 150 |
| `test_dedup.py` | 74 |
| `test_engine.py` | 117 |
| `test_cirs.py` | 65 |
| `test_critical_power.py` | 45 |
| `test_crs.py` | 80 |
| `test_eftp.py` | 50 |
| `test_marathon_shape.py` | 55 |
| `test_pmc.py` | 60 |
| `test_rec.py` | 45 |
| `test_relative_effort.py` | 95 |
| `test_rri.py` | 75 |
| `test_rtti.py` | 70 |
| `test_sapi.py` | 70 |
| `test_teroi.py` | 45 |
| `test_tpdi.py` | 50 |
| `test_utrs.py` | 80 |
| `test_vdot_adj.py` | 45 |
| `test_wlei.py` | 75 |
| `test_extractor_base.py` | 76 |
| `test_extractors_cross.py` | 305 |
| `test_fixture_loader.py` | 17 |
| `test_fixtures_layout.py` | 21 |
| `test_garmin_activity_sync.py` | 159 |
| `test_garmin_extractor.py` | 169 |
| `test_garmin_wellness_sync.py` | 125 |
| `test_goals.py` | 116 |
| `test_intervals_extractor.py` | 85 |
| `test_intervals_sync.py` | 148 |
| `test_metric_naming.py` | 50 |
| `test_metric_priority.py` | 100 |
| `test_metric_registry.py` | 64 |
| `test_mock_calcs.py` | 125 |
| `test_orchestrator.py` | 115 |
| `test_pace.py` | 74 |
| `test_phase1_schema.py` | 778 |
| `test_phase4_dod.py` | 322 |
| `test_phase4_spec.py` | 271 |
| `test_rate_limiter.py` | 52 |
| `test_raw_payload.py` | 209 |
| `test_raw_store.py` | 48 |
| `test_readiness.py` | 236 |
| `test_replanner.py` | 220 |
| `test_reprocess.py` | 248 |
| `test_round2.py` | 130 |
| `test_round4.py` | 88 |
| `test_runalyze_extractor.py` | 58 |
| `test_runalyze_sync.py` | 106 |
| `test_strava_extractor.py` | 94 |
| `test_strava_sync.py` | 140 |
| `test_sync_result.py` | 39 |
| `test_training_fullplan.py` | 145 |
| `test_training_month.py` | 109 |
| `test_training_phase_f.py` | 80 |
| `test_training_phase_g.py` | 75 |
| `test_training_workout_edit.py` | 60 |
| `test_unified_activities.py` | 90 |
| `test_training_phase_f.py` | 226 |
| `test_training_phase_g.py` | 218 |
| `test_training_workout_edit.py` | 204 |
| `test_trimp_calc.py` | 89 |
| `test_unified_activities.py` | 338 |
| `test_zones.py` | 64 |

### Fixtures
| 파일 | 줄수 |
|------|------|
| `fixtures/README.md` | 101 |

## 9. 설계 문서 (`v0.3/data/`)

| 파일 | 줄수 | 크기 |
|------|------|------|
| `CHANGELOG.md` | 168 | 9.1 KB |
| `architecture.md` | 1307 | 57.7 KB |
| `decisions.md` | 49 | 3.3 KB |
| `index.md` | 72 | 3.3 KB |
| `phase-1.md` | 1111 | 45.3 KB |
| `phase-2.md` | 1858 | 78.4 KB |
| `phase-3.md` | 2242 | 78.1 KB |
| `phase-4.md` | 3476 | 117.9 KB |
| `phase-5.md` | 1577 | 57.3 KB |
| `phase-6.md` | 339 | 20.7 KB |
| `phase-7(preview).md` | 573 | 58.9 KB |
| `phase_summary.md` | 684 | 33.9 KB |

## 10. GUIDE 파일

| 경로 | 줄수 |
|------|------|
| `src/ai/GUIDE.md` | 78 |
| `src/web/GUIDE.md` | 143 |
| `src/sync/GUIDE.md` | 116 |
| `src/training/GUIDE.md` | 78 |
| `src/metrics/GUIDE.md` | 230 |

## 통계 요약

| 항목 | 값 |
|------|------|
| Python 파일 | 354 |
| HTML 템플릿 | 16 |
| 테스트 파일 | 74 |
| 총 코드 줄수 (py+html) | ~73,942 |
| 테스트 통과 | 791 |
| Metric Calculators | 32 |
| 데이터 소스 | 4 (Garmin, Strava, Intervals.icu, Runalyze) |
| DB 테이블 | 16 |
