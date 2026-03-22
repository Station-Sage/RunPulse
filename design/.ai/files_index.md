# v0.2 파일 인덱스 (2026-03-23 Sprint 3 기준)

## ✅ 구현 완료

### src/metrics/ (Sprint 0+1+2)
| 파일 | 역할 | 주요 함수 | 상태 |
|------|------|-----------|------|
| `store.py` | DB UPSERT 헬퍼 | `save_metric`, `load_metric`, `load_metric_series` | ✅ |
| `gap.py` | GAP + NGP | `calc_gap`, `calc_ngp_from_laps` | ✅ |
| `lsi.py` | 부하 스파이크 | `calc_lsi`, `calc_and_save_lsi` | ✅ |
| `fearp.py` | 환경 보정 페이스 | `calc_fearp`, `calc_and_save_fearp` | ✅ |
| `adti.py` | 유산소 분리 추세 | `calc_adti`, `calc_and_save_adti` | ✅ |
| `tids.py` | 훈련 강도 분포 | `calc_tids`, `calc_and_save_tids` | ✅ |
| `relative_effort.py` | Relative Effort | `calc_relative_effort` | ✅ |
| `marathon_shape.py` | Marathon Shape | `calc_marathon_shape` | ✅ |
| `trimp.py` | TRIMPexp + HRSS | `calc_trimp`, `calc_and_save_daily_trimp` | ✅ |
| `acwr.py` | ACWR | `calc_acwr`, `calc_and_save_acwr` | ✅ |
| `monotony.py` | Monotony + Strain | `calc_monotony`, `calc_strain` | ✅ |
| `utrs.py` | UTRS | `calc_utrs`, `calc_and_save_utrs` | ✅ |
| `cirs.py` | CIRS | `calc_cirs`, `calc_and_save_cirs` | ✅ |
| `decoupling.py` | Aerobic Decoupling | `calc_decoupling`, `calc_ef` | ✅ |
| `di.py` | Durability Index | `calc_di_from_laps`, `calc_and_save_di` | ✅ |
| `darp.py` | 레이스 예측 | `calc_darp`, `vdot_to_marathon_pace_sec_km` | ✅ |
| `rmr.py` | RMR 5축 레이더 | `calc_rmr`, `calc_and_save_rmr` | ✅ |
| `engine.py` | 배치 오케스트레이터 | `run_for_date`, `run_for_date_range`, `recompute_all` | ✅ |

### src/weather/ (Sprint 0)
| 파일 | 역할 | 주요 함수 | 상태 |
|------|------|-----------|------|
| `provider.py` | Open-Meteo API | `get_weather`, `get_weather_for_activity` | ✅ |

### src/web/ (Sprint 3)
| 파일 | 라우트 | 역할 | 상태 |
|------|--------|------|------|
| `views_dashboard.py` | `GET /dashboard` | 통합 대시보드 (UTRS/CIRS/RMR/PMC) | ✅ |
| `helpers.py` | — | SVG 게이지·레이더·no_data_card 헬퍼 추가 | ✅ |

### tests/ (Sprint 1+2)
| 파일 | 대상 | 테스트 수 |
|------|------|-----------|
| `test_db_v2.py` | DB v2 스키마/마이그레이션 | 23개 |
| `test_metrics_sprint1.py` | Sprint 1 메트릭 전체 | 49개 |
| `test_metrics_sprint2.py` | Sprint 2 메트릭 전체 | 67개 |

---

## ⏳ 미구현 (Sprint 4~6)

### src/web/
| 파일 | 라우트 | 역할 | 스프린트 |
|------|--------|------|---------|
| `views_report.py` | `GET /report` | 분석 레포트 | Sprint 4 |
| `views_race.py` | `GET /race` | 레이스 예측 | Sprint 5 |
| `views_training_plan.py` | `GET /training` | 훈련 계획 캘린더 | Sprint 6 |
| `test_metrics_engine.py` | 배치 엔진 통합 |
| `test_web_dashboard.py` | 대시보드 뷰 |
| `test_web_report.py` | 분석 레포트 뷰 |
| `test_web_race.py` | 레이스 예측 뷰 |

---

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/db_setup.py` | `computed_metrics`, `weather_data` 테이블 추가, `migrate_db()` 업데이트 |
| `src/sync.py` | sync 완료 후 `engine.recompute_recent()` 호출 |
| `src/web/app.py` | 새 블루프린트 등록, `/` → `/dashboard` 리다이렉트 |
| `src/web/bg_sync.py` | 백그라운드 sync 완료 후 메트릭 재계산 훅 |
| `src/web/views_activity.py` | activity_deep에 FEARP + 2차 메트릭 섹션 추가 |

---

## 메트릭 정의 파일

| 파일 | 내용 | 역할 |
|------|------|------|
| `design/.ai/metrics.md` | PDF 원본 기반 확정 계산식 | 구현 기준 (우선) |
| `design/.ai/metrics_by_claude.md` | Claude 공개자료 조사 기반 추정 계산식 | 비교 대안 버전 |

> 두 버전을 비교 후 최종 채택 또는 사용자 선택 옵션으로 구현 예정.
> 차이 있는 메트릭: UTRS(가중치), CIRS(구성요소), DI(계산법), RMR(축 수)

---

## 참고 파일 (변경 없음)

| 파일 | v0.2에서의 역할 |
|------|----------------|
| `src/sync/garmin.py` | Body Battery, HRV, Sleep, TE 데이터 공급 |
| `src/sync/strava.py` | HR/Pace/Altitude stream 공급 |
| `src/sync/intervals.py` | CTL/ATL/TSB/TRIMP 공급 |
| `src/sync/runalyze.py` | VDOT, Marathon Shape, Race Prediction 공급 |
| `src/analysis/activity_deep.py` | Aerobic Decoupling 계산 입력 |
| `src/training/planner.py` | 훈련 계획 캘린더 데이터 공급 |

---

## 레퍼런스 파일 (design 폴더)

### PDF 변환 HTML (계산식 원본 — 구현 시 반드시 참조)
| 파일 | 내용 | 활용 방법 |
|------|------|-----------|
| `design/1_러닝플랫폼_1차_상세메트릭.html` | 7개 플랫폼 1차 메트릭 계산식 (TRIMP, PMC, GAP, VDOT, Decoupling 등) | 1차 메트릭 계산식 구현 기준 |
| `design/2_러닝플랫폼_2차_가공메트릭_후보군.html` | 16개 2차 메트릭 후보군, 우선순위 매트릭스, 구현 로드맵 | 2차 메트릭 계산식 및 우선순위 기준 |
| `design/3_통합_대시보드_UI_설계.html` | 기존 플랫폼 UI 분석, 데이터 시각화 베스트 프랙티스, 통합 대시보드 상세 설계 | UI 구현 시 레이아웃/컴포넌트 기준 |

### UI 레퍼런스 HTML
| 파일 | 활용 방법 |
|------|-----------|
| `design/app-UI/dashboard.html` | 대시보드 UI 구조 참고 |
| `design/app-UI/activity_detail.html` | 활동 상세 UI 참고 |
| `design/app-UI/ai_coaching.html` | AI 코칭 UI 참고 |
| `design/app-UI/race_prediction.html` | 레이스 예측 UI 참고 |
| `design/app-UI/analysis_report.html` | 분석 레포트 UI 참고 |
| `design/app-UI/training_plan.html` | 훈련 계획 UI 참고 |
