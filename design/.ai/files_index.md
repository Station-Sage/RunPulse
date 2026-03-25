# v0.2 파일 인덱스 (2026-03-25 기준)

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

## ✅ src/web/ (16개)

| 파일 | 라우트 | 줄수 |
|------|--------|------|
| `app.py` | Flask 앱 팩토리 + 블루프린트 | 839 ⚠️ |
| `bg_sync.py` | 백그라운드 sync 스레드 | — |
| `sync_ui.py` | SSE 병렬 동기화 프로그레스 | — |
| `helpers.py` | ECharts/nav/다크테마 (SVG는 helpers_svg.py로 분리) | 854 ⚠️ |
| `helpers_svg.py` | SVG 게이지·레이더 차트 헬퍼 (신규) | 177 |
| `views_dashboard.py` | GET /dashboard | 222 |
| `views_dashboard_cards.py` | 대시보드 하위 카드 | — |
| `views_activities.py` | GET /activities | 1024 ⚠️ |
| `views_activity.py` | GET /activity/deep (분리 후) | 185 |
| `views_activity_cards.py` | 활동 상세 카드 (re-export 포함) | 731 ⚠️ |
| `views_activity_source_cards.py` | 소스별 카드 (garmin/strava/intervals/runalyze) (신규) | 384 |
| `views_activity_loaders.py` | 활동 데이터 로더 (신규) | — |
| `views_activity_merge.py` | 활동 그룹 관리 | — |
| `views_report.py` | GET /report | — |
| `views_report_sections.py` | 레포트 하위 섹션 | 358 ⚠️ |
| `views_race.py` | GET /race | 225 |
| `views_ai_coach.py` | GET /ai-coaching | 204 |
| `views_wellness.py` | GET /wellness | 250 |
| `views_import.py` | GET/POST /import/strava-archive | — |
| `views_settings.py` | GET /settings + POST /settings/profile | 941 ⚠️ |
| `views_training.py` | GET /training (스캐폴딩) (신규) | — |
| `views_dev.py` | GET /dev (개발자 탭, 조건부) (신규) | — |
| `views_export_import.py` | CSV 임포트/내보내기 | — |
| `views_shoes.py` | /shoes | — |

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

총 717개 수집 (fitparse 미설치 시 6개 collect error)

---

## ⚠️ 300줄 초과 파일 (잔여)

| 파일 | 줄수 | 비고 |
|------|------|------|
| `app.py` | 839 | 블루프린트 등록 + 팩토리 — 기능 분리 완료 |
| `helpers.py` | 854 | ECharts/nav 공통 — SVG 분리 완료 |
| `views_activity_cards.py` | 731 | 활동 상세 카드 — 소스 카드 분리 완료 |
| `views_settings.py` | 941 | 설정 허브 고도화로 증가 — v0.3 이후 검토 |
| `views_activities.py` | 1024 | 필터링/정렬 복잡도 — v0.3 이후 검토 |
| `views_report_sections.py` | 358 | 섹션별 분리 가능하나 현재 허용 |
| `db_setup.py` | 1026 | 마이그레이션 분리 — v0.3 이후 검토 |

## ✅ B-1 리팩토링 완료 (2026-03-25)

| 분리 전 | 분리 후 | 줄수 변화 |
|---------|---------|---------|
| `views_activity.py` 1529줄 | views_activity.py + views_activity_cards.py + views_activity_loaders.py | 185줄 |
| `helpers.py` 1042줄 | helpers.py + helpers_svg.py | 854 + 177 |
| `views_activity_cards.py` 1102줄 | views_activity_cards.py + views_activity_source_cards.py | 731 + 384 |
| `app.py` 1351줄 | app.py + views_dev.py | 839줄 |

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

> 주의: 프로토타입은 `design/app-UI/`가 아니라 루트 `app-UI/`에 위치
