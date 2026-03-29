# src/web/ — Flask 웹 대시보드

## 진입점
| 파일 | 역할 |
|------|------|
| `app.py` | Flask 앱 팩토리 (`create_app()`), 블루프린트 등록, TTL 캐시 |
| `helpers.py` | 공통 유틸 — `db_path()`, `fmt_pace()`, `fmt_duration()`, ECharts 헬퍼, nav HTML |
| `helpers_svg.py` | SVG 게이지·레이더 차트 헬퍼 |

## 탭별 뷰 파일

### 홈 (`/`)
`app.py` 내 인라인 라우트 (`/`, `/home`)

### 활동 탭 (`/activities`, `/activity`)
| 파일 | 라우트 |
|------|--------|
| `views_activities.py` | GET /activities (목록, 필터, 정렬) |
| `views_activity.py` | GET /activity/deep (상세 오케스트레이션) |
| `views_activity_cards_common.py` | 공통 헬퍼 (포매터, 위젯, summary/nav/scroll) |
| `views_activity_loaders.py` | 기존 로더 (소스/인접/메트릭/PMC/HR존) |
| `views_activity_loaders_v2.py` | 신규 로더 (EF시리즈/위험/TIDS/DARP) |
| `views_activity_source_cards.py` | 소스 비교 + 서비스 탭 (접이식) |
| `views_activity_map.py` | Mapbox GPS 경로 지도 |
| `views_activity_g1_status.py` | G1 일일상태 스트립 |
| `views_activity_g2_performance.py` | G2 퍼포먼스 |
| `views_activity_g3_load.py` | G3 부하/노력 |
| `views_activity_g4_risk.py` | G4 과훈련 위험 |
| `views_activity_g5_biomechanics.py` | G5 폼/바이오메카닉스 (RMR 레이더) |
| `views_activity_g6_distribution.py` | G6 훈련분포 (HR존/TIDS/TPDI) |
| `views_activity_g7_fitness.py` | G7 피트니스 (PMC/DI/DARP) |
| `views_activity_merge.py` | 활동 그룹 관리 |

### 대시보드 (`/dashboard`)
| 파일 | 역할 |
|------|------|
| `views_dashboard.py` | 오케스트레이션 (7섹션) |
| `views_dashboard_cards.py` | 카드 렌더러 (880줄 — 분리 후보) |
| `views_dashboard_loaders.py` | 신규 로더 (웰니스/주간/추세/리스크7일) |

### 레포트 (`/report`)
| 파일 | 역할 |
|------|------|
| `views_report.py` | 오케스트레이션 (8섹션) |
| `views_report_sections.py` | 기존 섹션 렌더러 |
| `views_report_loaders.py` | 신규 로더 |
| `views_report_charts.py` | 신규 차트 |

### 훈련 탭 (`/training`) — 상세 구조 중요
| 파일 | 역할 | 줄수 |
|------|------|------|
| `views_training.py` | 메인 라우트 + 섹션 조립 | ~130 |
| `views_training_shared.py` | 공통 상수 `_TYPE_STYLE`, `_TYPE_BG`, `_esc` | 31 |
| `views_training_cal_js.py` | `CALENDAR_JS` 상수 (H-1 스와이프/H-2 모달/H-3 툴팁) | 298 |
| `views_training_cards.py` | S1 헤더 + S2 목표카드 + S3 주간요약 + re-export | 372 |
| `views_training_condition.py` | S5 컨디션+AI추천 통합 카드 | 152 |
| `views_training_wellness.py` | S4 컨디션조정 + S4.5 체크인 + S4.6 인터벌처방 | 320 |
| `views_training_week.py` | 주간 캘린더 + 인라인 편집패널 | 293 |
| `views_training_month.py` | 월간 4주 캘린더 + 네비게이션 | 211 |
| `views_training_plan_ui.py` | S6 AI추천 + S6b 계획개요 + S7 동기화상태 | 247 |
| `views_training_goals.py` | 목표 리스트 (수행률/D-day/드릴다운/가져오기 JS) | 431 |
| `views_training_fullplan.py` | 전체 일정 뷰 (주별 collapsible) | 260 |
| `views_training_wizard.py` | Wizard 렌더러 (create/edit 모드) | 363 |
| `views_training_wizard_render.py` | Wizard 스텝별 렌더러 | 343 |
| `views_training_loaders.py` | 훈련 데이터 로더 (readiness/workouts/goals 등) | 349 |
| `views_training_crud.py` | 워크아웃 CRUD 라우트 + AJAX + prefs | 468 |
| `views_training_goal_crud.py` | 목표 CRUD 라우트 (create/complete/cancel/detail/import) | 336 |
| `views_training_export.py` | 내보내기/전송 (ICS, Garmin, CalDAV) | 117 |
| `views_training_prefs.py` | 훈련 환경설정 카드 렌더링 | 207 |

**훈련탭 레이아웃 순서 (views_training.py 조립 기준):**
헤더 → 목표 카드 → 플랜 개요 → 목표 패널 → 체크인 → 인터벌처방
→ 주간 요약 → **[S5] 컨디션+AI 통합 카드** → [캘린더] → 동기화 상태 → 설정

### 레이스 (`/race`)
| 파일 | 역할 |
|------|------|
| `views_race.py` | 오케스트레이션 |
| `views_race_enhanced.py` | 신규 로더+렌더러 |

### AI 코치 (`/ai-coach`)
| 파일 | 역할 |
|------|------|
| `views_ai_coach.py` | 채팅 라우트 + SSE |
| `views_ai_coach_cards.py` | AI 코칭 카드 |

### 웰니스 (`/wellness`)
| 파일 | 역할 |
|------|------|
| `views_wellness.py` | 오케스트레이션 |
| `views_wellness_enhanced.py` | 신규 로더+렌더러 (557줄) |

### 기타
| 파일 | 역할 |
|------|------|
| `views_settings.py` | GET /settings (1508줄 — v0.3 분리 예정) |
| `views_export_import.py` | CSV 임포트/내보내기 |
| `views_shoes.py` | /shoes |
| `views_import.py` | Strava 아카이브 임포트 |
| `views_dev.py` | GET /dev (dev_mode 조건부) |
| `bg_sync.py` | 백그라운드 sync 스레드 |
| `sync_ui.py` | SSE 병렬 동기화 프로그레스 |

## Blueprint 등록 순서 (app.py)
1. wellness_bp, activity_bp, activities_bp, settings_bp, merge_bp, export_import_bp, shoes_bp
2. dashboard_bp, report_bp, import_bp, race_bp, ai_coach_bp
3. training_bp, training_crud_bp, training_goal_crud_bp, training_export_bp, wizard_bp, fullplan_bp
4. sync_bp, guide_bp, dev_bp

## 주요 패턴
- HTML 렌더링: 모든 렌더러는 `str` 반환 (템플릿 없음, f-string 인라인 HTML)
- 공통 스타일: `views_training_shared.py`의 `_TYPE_STYLE`, `_TYPE_BG` dict 참조
- AJAX 라우트: `Accept: application/json` 헤더 감지 → JSON 반환, 나머지 → redirect
- DB 접근: `db_path()` → `sqlite3.connect()` with try/finally
