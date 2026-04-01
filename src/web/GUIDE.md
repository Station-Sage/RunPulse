# src/web/ GUIDE — Flask 웹 대시보드

## 구조
3-tier 패턴: **loaders** (DB 조회) → **cards** (HTML 렌더러) → **views** (라우트 오케스트레이션)
- 모든 렌더러는 `str` 반환 (f-string 인라인 HTML, 템플릿 없음)
- AJAX 라우트: `Accept: application/json` → JSON 반환, 그 외 → redirect

## 파일 맵

### 진입점
| 파일 | 역할 |
|------|------|
| `app.py` | Flask 앱 팩토리, 블루프린트 등록, context_processor, FLASK_SECRET_KEY env 적용 |
| `auth_cf.py` | Cloudflare Zero Trust 헤더(`CF-Access-Authenticated-User-Email`) → `session["user_id"]` 세팅. production 시 헤더 없으면 401 |
| `helpers.py` | 공통 유틸 — `db_path()`, `fmt_pace()`, ECharts 헬퍼, bottom_nav |
| `helpers_svg.py` | SVG 게이지/레이더 차트 헬퍼 |
| `route_svg.py` | SVG 라우트 |
| `bg_sync.py` | 백그라운드 sync 스레드 + 메트릭 재계산 |
| `sync_ui.py` | SSE 병렬 동기화 프로그레스 |

### 대시보드 (`/dashboard`)
| 파일 | 역할 |
|------|------|
| `views_dashboard.py` | 오케스트레이션 (7섹션) |
| `views_dashboard_cards.py` | 카드 렌더러 (메인) |
| `views_dashboard_cards_fitness.py` | 피트니스 카드 |
| `views_dashboard_cards_recommend.py` | 추천 카드 |
| `views_dashboard_cards_risk.py` | 위험 카드 |
| `views_dashboard_cards_status.py` | 상태 카드 |
| `views_dashboard_loaders.py` | 로더 (웰니스/주간/추세/리스크) |

### 활동 (`/activities`, `/activity`)
| 파일 | 역할 |
|------|------|
| `views_activities.py` | 활동 목록 오케스트레이션 |
| `views_activities_filter.py` | 필터 UI |
| `views_activities_helpers.py` | 목록 헬퍼 |
| `views_activities_table.py` | 테이블 렌더러 |
| `views_activity.py` | 활동 상세 오케스트레이션 |
| `views_activity_cards_common.py` | 공통 헬퍼 (포매터, 위젯) |
| `views_activity_loaders.py` | 기존 로더 (소스/인접/메트릭) |
| `views_activity_loaders_v2.py` | 신규 로더 (EF/위험/TIDS) |
| `views_activity_source_cards.py` | 소스 비교 + 서비스 탭 |
| `views_activity_s5_cards.py` | S5 카드 |
| `views_activity_map.py` | Leaflet GPS 경로 지도 |
| `views_activity_g1_status.py` | G1 일일상태 스트립 |
| `views_activity_g2_performance.py` | G2 퍼포먼스 |
| `views_activity_g3_load.py` | G3 부하/노력 |
| `views_activity_g4_risk.py` | G4 과훈련 위험 |
| `views_activity_g5_biomechanics.py` | G5 폼/바이오메카닉스 |
| `views_activity_g6_distribution.py` | G6 훈련분포 |
| `views_activity_g7_fitness.py` | G7 피트니스 |
| `views_activity_merge.py` | 활동 그룹 관리 |

### 레포트 (`/report`)
| 파일 | 역할 |
|------|------|
| `views_report.py` | 오케스트레이션 |
| `views_report_sections.py` | AI 인사이트 + 요약/테이블/Export + re-export |
| `views_report_sections_cards.py` | 메트릭 카드 렌더러 (TIDS/TRIMP/Risk/DARP/피트니스/내구력) |
| `views_report_sections_data.py` | 데이터 로더 (TIDS/TRIMP/리스크/ADTI/DARP/피트니스) |
| `views_report_charts.py` | 차트 렌더러 |
| `views_report_loaders.py` | 로더 |

### 훈련 (`/training`) — 18개 파일
| 파일 | 역할 |
|------|------|
| `views_training.py` | 메인 라우트 + 섹션 조립; **auto_gen 없음** — 페이지 로드 시 자동 플랜 생성 제거. wizard 또는 재생성 버튼으로만 생성. `/training/generate`는 goal의 race_date/plan_weeks 기반 전체 주 재생성 |
| `views_training_shared.py` | 공통 상수 (`_TYPE_STYLE`, `_TYPE_BG`) |
| `views_training_cal_js.py` | 캘린더 JS (스와이프/모달/툴팁); 스와이프 시 가로스크롤 감지, 월간 툴팁 onclick 전용 |
| `views_training_cards.py` | S1 헤더 + S2 목표카드 + S3 주간요약; 계획 없으면 헤더 버튼 전체 숨김 |
| `views_training_condition.py` | S5 컨디션+AI 통합 카드 |
| `views_training_wellness.py` | S4 컨디션조정 + 체크인 + 인터벌처방 |
| `views_training_week.py` | 주간 캘린더 + 인라인 편집 |
| `views_training_month.py` | 월간 4주 캘린더 |
| `views_training_plan_ui.py` | AI추천 + 계획개요 + 동기화상태 |
| `views_training_goals.py` | 목표 리스트 (수행률/D-day); 드롭다운에 훈련계획 삭제 버튼, 취소 목표에 삭제 버튼 |
| `views_training_fullplan.py` | 전체 일정 뷰 |
| `views_training_wizard.py` | Wizard 렌더러; `_save_and_generate` / `_update_and_maybe_regen`에서 race_date/plan_weeks까지 전체 주 루프 생성 |
| `views_training_wizard_render.py` | Wizard 스텝별 렌더러 |
| `views_training_loaders.py` | 훈련 데이터 로더 |
| `views_training_crud.py` | 워크아웃 CRUD + AJAX |
| `views_training_goal_crud.py` | 목표 CRUD 라우트; `/goal/<id>/delete-plan` (AI계획 삭제), `/goal/<id>/delete` (취소목표 삭제) |
| `views_training_export.py` | 내보내기 (ICS, Garmin, CalDAV) |
| `views_training_prefs.py` | 훈련 환경설정 카드 |

### 기타 탭
| 파일 | 역할 |
|------|------|
| `views_race.py` / `views_race_enhanced.py` | 레이스 예측 |
| `views_ai_coach.py` / `views_ai_coach_cards.py` | AI 코치 채팅 |
| `views_wellness.py` / `views_wellness_enhanced.py` | 웰니스 |
| `views_settings.py` | 설정 메인 |
| `views_settings_hub.py` | 설정 허브 |
| `views_settings_garmin.py` | Garmin 설정 |
| `views_settings_integrations.py` | 연동 설정 |
| `views_settings_metrics.py` | 메트릭 설정 |
| `views_settings_render.py` | 설정 렌더러 |
| `views_settings_render_prefs.py` | 설정 환경설정 렌더러 |
| `views_sync.py` | 동기화 탭 |
| `views_export_import.py` / `views_import.py` | 임포트/내보내기 |
| `views_shoes.py` | 신발 관리 |
| `views_guide.py` | 용어집/가이드 |
| `views_dev.py` | 개발자 모드 |
| `views_perf.py` | 성능 모니터링 |

## 훈련탭 설계 원칙
- **플랜 생성**: wizard 또는 재생성 버튼으로만 — 페이지 로드 시 auto_gen 없음
- **CRS 게이트**: `adjuster.py` (일일 추천카드)에서만 적용. 플랜 생성(`planner.py`)에는 CRS/TSB/ACWR/HRV/Body Battery 게이트 없음
- **Q-day 이후 recovery**: Daniels Hard-Easy 원칙에 따라 플랜 생성 시 항상 구조적으로 적용 (컨디션 무관)

## 규칙
- HTML: f-string 인라인. `base.html` 레이아웃 + `bottom_nav(active_tab)`.
- 다크 테마: `background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)`, card: `rgba(255,255,255,0.05)`
- 색상: cyan `#00d4ff` (긍정), green `#00ff88` (안전), red `#ff4444` (위험), orange `#ffaa00` (주의)
- 차트: ECharts CDN (라인/바), SVG (게이지/레이더)
- DB: `db_path()` → `sqlite3.connect()` with try/finally
- config 로드: 웹 라우트에서 `load_config(user_id=get_current_user_id())` 필수. user_id 없이 호출 금지 (글로벌 config 로드됨)
- 하단 네비게이션 7+1탭 유지: 홈 | 활동 | 레포트 | 훈련 | AI코치 | 동기화 | 설정 (+개발자)
- subprocess로 sync.py/import_history.py 호출 시 반드시 --user user_id 전달

## 주의사항 — 300줄 초과 파일
| 파일 | 줄수 | 비고 |
|------|------|------|
| `helpers.py` | 915 | REFAC-4 대상 |
| `app.py` | 912 | 블루프린트 등록 + context_processor |
| `views_dev.py` | 589 | dev 전용, 우선순위 낮음 |
| `views_wellness_enhanced.py` | 568 | |
| `views_ai_coach_cards.py` | 539 | |

## 의존성
- `src/metrics/engine.py` — sync 후 메트릭 재계산 호출
- `src/training/` — 훈련탭 데이터 로더
- `src/ai/` — AI 코치 채팅 엔진
- `src/services/unified_activities.py` — 활동 목록 DB 조회
- `src/utils/credential_store.py` — Fernet 자격증명 암호화/복호화 (`load_config`/`save_config`에 투명 적용)
- `templates/` — `base.html`, 매크로 (gauge, radar, no_data)
