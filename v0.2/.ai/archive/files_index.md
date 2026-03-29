# v0.2 파일 인덱스 (2026-03-29 기준)

## ✅ src/metrics/ (23개, Sprint 1+2+5)

| 파일 | 역할 | 주요 함수 |
|------|------|-----------|
| `store.py` | DB UPSERT 헬퍼 | `save_metric`, `load_metric`, `load_metric_series` |
| `gap.py` | GAP + NGP | `calc_gap`, `calc_ngp_from_laps` |
| `lsi.py` | 부하 스파이크 | `calc_lsi`, `calc_and_save_lsi` |
| `fearp.py` | 환경 보정 페이스 | `calc_fearp`, `calc_and_save_fearp` |
| `adti.py` | 유산소 분리 추세 | `calc_adti`, `calc_and_save_adti` |
| `tids.py` | 훈련 강도 분포 | `calc_tids`, `calc_and_save_tids` |
| `relative_effort.py` | Relative Effort | `calc_relative_effort` |
| `marathon_shape.py` | Marathon Shape | `calc_marathon_shape` |
| `trimp.py` | TRIMPexp + HRSS | `calc_trimp`, `calc_and_save_daily_trimp` |
| `acwr.py` | ACWR | `calc_acwr`, `calc_and_save_acwr` |
| `monotony.py` | Monotony + Strain | `calc_monotony`, `calc_strain` |
| `utrs.py` | UTRS | `calc_utrs`, `calc_and_save_utrs` |
| `cirs.py` | CIRS | `calc_cirs`, `calc_and_save_cirs` |
| `decoupling.py` | Aerobic Decoupling | `calc_decoupling`, `calc_ef` |
| `di.py` | Durability Index | `calc_di_from_laps`, `calc_and_save_di` |
| `darp.py` | 레이스 예측 | `calc_darp`, `vdot_to_marathon_pace_sec_km` |
| `rmr.py` | RMR 5축 레이더 | `calc_rmr`, `calc_and_save_rmr` |
| `vdot.py` | VDOT 계산 | `calc_vdot` |
| `rtti.py` | 러닝 내성 훈련 지수 | `calc_rtti` (Sprint 5) |
| `wlei.py` | 날씨 가중 노력 지수 | `calc_wlei` (Sprint 5) |
| `tpdi.py` | 실내/야외 퍼포먼스 격차 | `calc_tpdi` (Sprint 5) |
| `engine.py` | 배치 오케스트레이터 | `run_for_date`, `run_for_date_range`, `recompute_all` |

## ✅ src/weather/ (Sprint 0)

| 파일 | 역할 | 주요 함수 |
|------|------|-----------|
| `provider.py` | Open-Meteo API | `get_weather`, `get_weather_for_activity` |

## ✅ src/sync/ (v0.2 모듈 분리)

### Garmin (8개)
| 파일 | 역할 |
|------|------|
| `garmin.py` | 통합 sync 오케스트레이터 |
| `garmin_auth.py` | 인증 |
| `garmin_activity_sync.py` | 활동 + splits + backfill |
| `garmin_api_extensions.py` | streams/gear/exercise_sets |
| `garmin_daily_extensions.py` | race_predictions/training_status/fitness/HR/stress/BB |
| `garmin_athlete_extensions.py` | profile/stats/personal_records |
| `garmin_wellness_sync.py` | 수면/HRV/BB/스트레스/SPO2 |
| `garmin_v2_mappings.py` | ZIP/detail 필드 매핑 |
| `garmin_backfill.py` | 기존 활동 보강 |
| `garmin_helpers.py` | 공통 헬퍼 |

### Strava (4개)
| 파일 | 역할 |
|------|------|
| `strava.py` | 통합 sync 오케스트레이터 |
| `strava_auth.py` | OAuth2 토큰 관리 |
| `strava_activity_sync.py` | 활동/streams/laps/best_efforts |
| `strava_athlete_sync.py` | profile/stats/gear |

### Intervals.icu (5개)
| 파일 | 역할 |
|------|------|
| `intervals.py` | 통합 sync 오케스트레이터 |
| `intervals_auth.py` | API 인증 |
| `intervals_activity_sync.py` | 활동/intervals/streams |
| `intervals_athlete_sync.py` | profile/stats |
| `intervals_wellness_sync.py` | 웰니스/피트니스 |

### Runalyze (1개)
| 파일 | 역할 |
|------|------|
| `runalyze.py` | VDOT/Marathon Shape/Race Prediction |

## ✅ src/web/ (31개)

### 공통
| 파일 | 역할 | 줄수 |
|------|------|------|
| `app.py` | Flask 앱 팩토리 + 블루프린트 | 839 ⚠️ |
| `bg_sync.py` | 백그라운드 sync 스레드 | — |
| `sync_ui.py` | SSE 병렬 동기화 프로그레스 | — |
| `helpers.py` | ECharts/nav/다크테마 | 854 ⚠️ |
| `helpers_svg.py` | SVG 게이지·레이더 차트 헬퍼 | 177 |

### 활동 상세 (UI-R1 재설계, 13개)
| 파일 | 역할 | 줄수 |
|------|------|------|
| `views_activity.py` | GET /activity/deep 오케스트레이션 | 200 |
| `views_activity_cards_common.py` | 공통 헬퍼 (포매터, 위젯, summary/nav/scroll) | 294 |
| `views_activity_map.py` | Mapbox GPS 경로 지도 | 52 |
| `views_activity_loaders.py` | 데이터 로더 (소스/인접/메트릭/PMC/HR존) | 315 |
| `views_activity_loaders_v2.py` | 신규 로더 (EF시리즈/위험시리즈/TIDS/DARP) | 104 |
| `views_activity_source_cards.py` | 소스 비교 + 서비스 탭 (접이식) | 441 |
| `views_activity_g1_status.py` | G1 일일상태 스트립 | 142 |
| `views_activity_g2_performance.py` | G2 퍼포먼스 | 206 |
| `views_activity_g3_load.py` | G3 부하/노력 | 119 |
| `views_activity_g4_risk.py` | G4 과훈련 위험 (멀티라인 차트) | 87 |
| `views_activity_g5_biomechanics.py` | G5 폼/바이오메카닉스 (RMR 레이더) | 104 |
| `views_activity_g6_distribution.py` | G6 훈련분포 (HR존/TIDS/TPDI) | 161 |
| `views_activity_g7_fitness.py` | G7 피트니스 (PMC/DI/DARP) | 170 |

### 기타 뷰
| 파일 | 라우트 | 줄수 |
|------|--------|------|
| `views_activities.py` | GET /activities (라우트 핸들러) | ~155 |
| `views_activities_helpers.py` | 포맷 헬퍼 + 아이콘/배지 (type/source/label) | ~245 |
| `views_activities_filter.py` | 필터 폼 + 날짜 프리셋 JS | ~195 |
| `views_activities_table.py` | 테이블 + 요약 + 편집 바 + JS + 페이지네이션 | ~290 |
| `views_activity_merge.py` | 활동 그룹 관리 | — |
| `views_dashboard.py` | GET /dashboard (7섹션 오케스트레이션) | 210 |
| `views_dashboard_cards.py` | 대시보드 카드 진입점 (re-export) | 34 |
| `views_dashboard_cards_status.py` | 상태 스트립 + 주간 요약 + 색상상수 | 145 |
| `views_dashboard_cards_fitness.py` | 피트니스 추세/PMC/활동목록/피트니스미니 | 280 |
| `views_dashboard_cards_risk.py` | 리스크 pills + CIRS/UTRS 상세 | 185 |
| `views_dashboard_cards_recommend.py` | 훈련 권장 + DARP + 게이지/RMR | 267 |
| `views_dashboard_loaders.py` | 대시보드 신규 로더 (웰니스/주간/추세/리스크7일) | 119 |
| `views_report.py` | GET /report (8섹션 오케스트레이션) | 265 |
| `views_report_sections.py` | 레포트 기존 섹션 (TIDS/TRIMP+비교선/Risk/DARP/Fitness/AI) | 566 ⚠️ |
| `views_report_loaders.py` | 레포트 신규 로더 (질/리스크/폼/웰니스 시리즈) | 155 |
| `views_report_charts.py` | 레포트 신규 차트 (질/TIDS주간/리스크/폼/컨디션) | 285 |
| `views_race.py` | GET /race (6섹션 오케스트레이션) | ~340 |
| `views_race_enhanced.py` | 레이스 신규 로더+렌더러 (추세/준비요소/목표갭+훈련권장/DI해석/해설) | 307 |
| `views_ai_coach.py` | GET /ai-coach | 254 |
| `views_ai_coach_cards.py` | AI 코칭 카드 분리 | — |
| `views_wellness.py` | GET /wellness (9섹션 보강) | ~370 |
| `views_wellness_enhanced.py` | 웰니스 신규 로더+렌더러 (대시/패턴/주간비교/미니차트/해설/수면시간/이상치/패턴권장) | 557 ⚠️ |
| `views_import.py` | GET/POST /import/strava-archive | — |
| `views_settings.py` | GET /settings + POST 저장 라우트 | ~285 |
| `views_settings_render.py` | 서비스카드/프로필/Mapbox/CalDAV 렌더러 (블루프린트 없음) | ~210 |
| `views_settings_render_prefs.py` | 훈련환경설정/AI/프롬프트 렌더러 (블루프린트 없음) | ~270 |
| `views_settings_garmin.py` | settings_garmin_bp — Garmin 연동/MFA/해제 라우트 | ~230 |
| `views_settings_integrations.py` | settings_integrations_bp — Strava/Intervals/Runalyze 라우트 | ~280 |
| `views_settings_metrics.py` | settings_metrics_bp — 메트릭 재계산 SSE 라우트 | ~120 |
| `views_settings_hub.py` | sync 상태/시스템 정보 카드 | — |
| `views_training.py` | GET /training 메인 라우트 + 조립 | ~130 |
| `views_training_shared.py` | 공통 상수 (`_TYPE_STYLE`, `_TYPE_BG`, `_esc`) | 31 |
| `views_training_cal_js.py` | 캘린더 공통 JS — `CALENDAR_JS` (H-1 스와이프/H-2 모달/H-3 툴팁) | 298 |
| `views_training_cards.py` | S1 헤더 + S2 목표카드 + S3 주간요약 + re-export | 372 ⚠️ |
| `views_training_condition.py` | S5 컨디션+AI추천 통합 카드 (UTRS/CIRS/BB/수면/HRV/TSB 배지) | 152 |
| `views_training_wellness.py` | S4 컨디션조정 + S4.5 체크인 + S4.6 인터벌처방 | 320 ⚠️ |
| `views_training_week.py` | S5 주간캘린더 + 인라인 편집패널 (`CALENDAR_JS` 공유) | 293 |
| `views_training_month.py` | 월간 4주 캘린더 + 네비게이션 (`CALENDAR_JS` 공유) | 211 |
| `views_training_plan_ui.py` | S6 AI추천 + S6b 계획개요 + S7 동기화상태 | 247 |
| `views_training_goals.py` | 목표 리스트(수행률/D-day/드릴다운) | 431 ⚠️ |
| `views_training_fullplan.py` | 전체 일정 뷰 (주별 collapsible) | 260 |
| `views_training_wizard.py` | Wizard 렌더러 (create/edit 모드) | 363 ⚠️ |
| `views_training_wizard_render.py` | Wizard 스텝별 렌더러 | 343 ⚠️ |
| `views_training_loaders.py` | 훈련 데이터 로더 (readiness/workouts/goals 등) | 349 ⚠️ |
| `views_training_crud.py` | 워크아웃 CRUD 라우트 (create/update/delete/confirm/skip/toggle/patch/prefs) | 468 ⚠️ |
| `views_training_goal_crud.py` | 목표 CRUD 라우트 (create/complete/cancel/detail/import) | 336 ⚠️ |
| `views_training_export.py` | 내보내기/전송 (ICS, Garmin, CalDAV) | 117 |
| `views_training_prefs.py` | 훈련 환경설정 카드 (렌더링 전용) | 207 |
| `views_dev.py` | GET /dev (dev_mode 조건부) | — |
| `views_export_import.py` | CSV 임포트/내보내기 | 233 |
| `views_shoes.py` | /shoes | — |

### 폐기 (UI-R1에서 분배 완료)
| 파일 | 상태 |
|------|------|
| `views_activity_cards.py` | 내용 → cards_common + g1~g7로 분배 |
| `views_activity_s5_cards.py` | 내용 → g1~g7로 분배 |

## ✅ src/services/

| 파일 | 역할 |
|------|------|
| `unified_activities.py` | DB 레벨 2단계 페이지네이션 + 통합 활동 조회 (408줄 ⚠️) |

## ✅ src/import_export/

| 파일 | 역할 |
|------|------|
| `strava_archive.py` | Strava ZIP 아카이브 임포트 |
| `strava_csv.py` | Strava activities.csv 파싱 |
| `garmin_csv.py` | Garmin CSV 파싱 |
| `intervals_fit.py` | Intervals.icu FIT 파싱 (fitparse 필요) |

## ✅ src/utils/ (10개)

| 파일 | 역할 |
|------|------|
| `api.py` | 외부 API 래퍼 (모든 API 호출) |
| `config.py` | config.json 로드/저장 |
| `dedup.py` | 중복 활동 매칭/그룹 관리 |
| `pace.py` | 페이스 변환 |
| `zones.py` | HR/Pace 존 계산 |
| `clipboard.py` | termux-clipboard-set 래퍼 |
| `raw_payload.py` | 원시 API 응답 저장/조회 |
| `sync_jobs.py` | 동기화 작업 관리 |
| `sync_policy.py` | 동기화 정책 |
| `sync_state.py` | 동기화 상태 추적 |

## ✅ templates/ (8개)

| 파일 | 역할 |
|------|------|
| `base.html` | 공통 레이아웃 (stylesheet/nav/sync context_processor) |
| `dashboard.html` | 대시보드 |
| `ai_coaching.html` | AI 코칭 |
| `race.html` | 레이스 예측 |
| `generic_page.html` | 범용 페이지 래퍼 |
| `macros/gauge.html` | 반원 게이지 SVG 매크로 |
| `macros/radar.html` | 레이더 차트 SVG 매크로 |
| `macros/no_data.html` | 데이터 없음 카드 매크로 |

## ✅ tests/ (56개 파일)

| 파일 | 대상 | 테스트 수 |
|------|------|-----------|
| `test_db_setup.py` | DB 초기화/마이그레이션 | 8 |
| `test_db_v2.py` | DB v2 스키마 | 23 |
| `test_metrics_sprint1.py` | Sprint 1 메트릭 | 49 |
| `test_metrics_sprint2.py` | Sprint 2 메트릭 | 67 |
| `test_metrics_sprint5.py` | Sprint 5 메트릭 (RTTI/WLEI/TPDI) | 14 |
| 기타 51개 | sync/analysis/web/ai/utils | — |

총 **1122개 통과** (2026-03-29, fitparse 미설치 시 일부 collect error 허용)

---

## ⚠️ 300줄 초과 파일 (2026-03-29 기준 wc -l 실측)

| 파일 | 실측 | 비고 |
|------|------|------|
| ~~`views_dashboard_cards.py`~~ | ~~880~~ | → 4분리 완료 |
| `helpers.py` | 915 | ECharts/nav 공통 — SVG 분리 완료 |
| `app.py` | 902 | 블루프린트 등록 + 팩토리 |
| `src/ai/chat_engine.py` | 696 | AI 채팅 엔진 |
| `views_report_sections.py` | 707 | 레포트 섹션별 렌더러 |
| `src/training/planner.py` | 713 | 훈련 플래너 — 복잡도 높음 |
| `db_setup.py` | 968 | 마이그레이션 시스템 포함 |
| `views_training_goals.py` | 431 | 목표 렌더링 — 분리 후보 |
| `views_training_cards.py` | 372 | 약간 초과 |
| `views_training_wizard.py` | 363 | Wizard 렌더러 |
| `views_training_wizard_render.py` | 343 | Wizard 스텝별 |
| `views_training_loaders.py` | 349 | 훈련 로더 |
| `views_training_wellness.py` | 320 | 컨디션/체크인/인터벌처방 |
| `views_activity_source_cards.py` | 436 | 소스 비교 + 서비스 탭 |
| `views_training_goal_crud.py` | 336 | 목표 CRUD + import |

## ✅ 리팩토링 완료 (2026-03-29 세션)

| 분리 전 | 분리 후 | 결과 |
|---------|---------|------|
| `views_training_crud.py` 896줄 | crud(468) + goal_crud(336) + export(117) | 모두 ≤468줄 |
| `views_settings.py` 1508줄 | settings(285) + render(210) + render_prefs(270) + garmin(230) + integrations(280) + metrics(120) | 모두 ≤285줄 |
| `views_activities.py` 1096줄 | activities(155) + helpers(245) + filter(195) + table(290) | 모두 ≤290줄 |
| `src/ai/chat_context.py` 932줄 | context(75) + utils(35) + intent(70) + builders(240) + rich(180) + format(260) | 모두 ≤260줄 |
| `views_dashboard_cards.py` 880줄 | cards(34) + status(145) + fitness(280) + risk(185) + recommend(267) | 모두 ≤280줄 |
| `views_activity_cards.py` 827줄 | 삭제 (미사용 확인) | — |
| 폴더 README 신설 | `src/web/README.md`, `src/training/README.md`, `src/ai/README.md` | CLAUDE.md에 참조 추가 |

## ✅ B-1 리팩토링 완료 (2026-03-25)

| 분리 전 | 분리 후 | 줄수 변화 |
|---------|---------|---------|
| `views_activity.py` 1529줄 | views_activity.py + views_activity_cards.py + views_activity_loaders.py | 185줄 |
| `helpers.py` 1042줄 | helpers.py + helpers_svg.py | 854 + 177 |
| `views_activity_cards.py` 1102줄 | views_activity_cards.py + views_activity_source_cards.py | 731 + 384 |
| `app.py` 1351줄 | app.py + views_dev.py | 839줄 |

## ✅ UI-R1 리팩토링 완료 (2026-03-25)

| 분리 전 | 분리 후 | 줄수 변화 |
|---------|---------|---------|
| `views_activity_cards.py` 731줄 | cards_common(294) + g1(142) + g2(206) + g3(119) + g4(87) + g5(104) + g6(161) + g7(170) + map(52) | 모두 300줄 이하 |
| `views_activity_s5_cards.py` 278줄 | g1~g7로 분배 | 삭제 |
| `views_activity_loaders.py` 411줄 | loaders.py(315) + loaders_v2.py(104) | 분리 |

---

## ⏳ 미구현

| 파일 | 역할 | 스프린트 |
|------|------|---------|
| V2-9-5 `/dev` 탭 등록 | bottom_nav dev_mode 조건부 표시 | Sprint 6 |

---

## 레퍼런스 (design 폴더)

### PDF 변환 HTML (계산식 원본)
| 파일 | 내용 |
|------|------|
| `design/1_러닝플랫폼_1차_상세메트릭.html` | 1차 메트릭 계산식 |
| `design/2_러닝플랫폼_2차_가공메트릭_후보군.html` | 2차 메트릭 후보군 |
| `design/3_통합_대시보드_UI_설계.html` | 통합 대시보드 UI 설계 |

### UI 프로토타입 HTML (경로: `app-UI/`)
| 파일 | 내용 |
|------|------|
| `app-UI/dashboard.html` | 대시보드 다크테마 프로토타입 |
| `app-UI/activity_detail.html` | 활동 상세 프로토타입 |
| `app-UI/analysis_report.html` | 분석 레포트 프로토타입 |
| `app-UI/settings_sync.html` | 설정/동기화 프로토타입 |
| `app-UI/race_prediction.html` | 레이스 예측 프로토타입 |
| `app-UI/ai_coaching.html` | AI 코칭 프로토타입 |
| `app-UI/training_plan.html` | 훈련 계획 프로토타입 |

> 주의: 프로토타입은 `v0.2/app-UI/`에 위치 (gitignore 대상, .ai/*.md만 추적)
