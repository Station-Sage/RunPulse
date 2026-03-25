# RunPulse v0.2 — Claude 작업 가이드 (마스터 인덱스)

> 세션 시작 시 이 파일을 먼저 읽는다.
> 현재 상태 파악 → 해당 Phase 파일 참조 → 작업 시작.

---

## 현재 상태 (2026-03-25)

| 항목 | 내용 |
|------|------|
| 현재 버전 | v0.2 개발 중 — Sprint 6 후반 |
| 작업 브랜치 | `claude/sprint6-settings-refactor` (dev 기반) |
| v0.1 기반 | `main` 브랜치에 태그됨, 테스트 652개 통과 |
| 현재 테스트 | **792개 통과** (gpxpy 미설치 2개 collect error 별개) |
| 완료 | Phase 0~7 · Sprint 4A~5F · Sprint 6 전체 (V2-8-1b/V2-9-3~V2-9-7/V2-9-10~11/B-1~B-3) |
| 현재 테스트 | **829개 통과** (기존 792 + 신규 37) |
| 다음 작업 | V2-9-8 changelog · V2-9-9 Mapbox 토큰 · 탭 UI 리뉴얼 |

---

## 파일 네비게이션

### 작업 계획
| 파일 | 용도 | 언제 읽나 |
|------|------|-----------|
| `design/.ai/todo.md` | v0.2 전체 작업 체크리스트 (Phase 0~9) | 매 세션 시작 |
| `design/.ai/roadmap.md` | 스프린트 단계, 검증 기준, 의존 관계 | 스프린트 시작/전환 시 |

### 설계 기준
| 파일 | 용도 | 언제 읽나 |
|------|------|-----------|
| `design/.ai/architecture.md` | v0.1 기존 코드 구조 + v0.2 추가 모듈 맵 | 새 모듈 작성 전 |
| `design/.ai/metrics.md` | 2차 메트릭 확정 계산식 (PDF 원본 기준) | 메트릭 함수 구현 시 |
| `design/.ai/metrics_by_claude.md` | 2차 메트릭 대안 계산식 (비교용) | 두 버전 비교 시 |
| `design/.ai/decisions.md` | v0.2 설계 결정 기록 (D-V2-01~) | 설계 판단 필요 시 |

### 파일 목록
| 파일 | 용도 | 언제 읽나 |
|------|------|-----------|
| `design/.ai/files_index.md` | 신규/수정/참고 파일 인덱스 | 어떤 파일을 만들어야 할지 모를 때 |

### UI 레퍼런스
| 파일 | 용도 |
|------|------|
| `design/3_통합_대시보드_UI_설계.html` | 대시보드 레이아웃/컴포넌트/색상 기준 |
| `design/1_러닝플랫폼_1차_상세메트릭.html` | 1차 메트릭 계산식 원본 |
| `design/2_러닝플랫폼_2차_가공메트릭_후보군.html` | 2차 메트릭 공식/우선순위 원본 |
| `design/app-UI/*.html` | 각 화면별 UI 프로토타입 |

### v0.1 히스토리 (참고용)
| 파일 | 용도 |
|------|------|
| `.ai/todo.md` | v0.1 완료 작업 전체 히스토리 |
| `.ai/architecture.md` | v0.1 아키텍처 상세 |
| `.ai/decisions.md` | v0.1 설계 결정 D1~D18 |

---

## v0.2 구현 목표 요약

### 무엇을 만드나
v0.1의 4소스 동기화 + 기본 웹 위에 **2차 메트릭 계산 엔진**과 **고도화 UI**를 추가한다.

```
v0.1 (완료): 4소스 sync → DB → 기초분석 → Flask 기본 웹
                                               ↓
v0.2 (진행): + [2차 메트릭 엔진] + [고도화 대시보드 UI]
               computed_metrics 테이블          ↑
               weather_data 테이블         Chart.js + SVG 컴포넌트
```

### 생성된 파일 (v0.2 구현 완료)
```
src/metrics/ (23개)     ← 2차 메트릭 계산 함수들
  lsi.py, fearp.py, adti.py, tids.py, gap.py
  acwr.py, trimp.py, utrs.py, cirs.py, monotony.py
  decoupling.py, di.py, darp.py, rmr.py, vdot.py
  relative_effort.py, marathon_shape.py
  rtti.py, wlei.py, tpdi.py              # Sprint 5 추가
  engine.py, store.py

src/weather/
  provider.py     ← Open-Meteo API (FEARP용)

src/web/ (신규 뷰 14개)
  views_dashboard.py, views_dashboard_cards.py
  views_report.py, views_report_sections.py
  views_race.py, views_ai_coach.py, views_wellness.py
  views_import.py, views_shoes.py, sync_ui.py
  views_training.py, views_dev.py           # Sprint 6 추가
  views_activity_source_cards.py            # B-1 분리
  helpers_svg.py                            # B-1 분리

src/sync/ (모듈 분리 — Garmin/Strava/Intervals 각각)
  garmin_activity_sync.py, garmin_api_extensions.py
  garmin_daily_extensions.py, garmin_athlete_extensions.py
  garmin_v2_mappings.py, garmin_backfill.py, garmin_helpers.py
  strava_auth.py, strava_activity_sync.py, strava_athlete_sync.py
  intervals_auth.py, intervals_activity_sync.py
  intervals_athlete_sync.py, intervals_wellness_sync.py

src/services/
  unified_activities.py  ← DB 레벨 2단계 페이지네이션

src/import_export/
  strava_archive.py, strava_csv.py, garmin_csv.py, intervals_fit.py

templates/
  base.html, dashboard.html, ai_coaching.html, race.html, generic_page.html
  macros/ gauge.html, radar.html, no_data.html
```

### 수정된 기존 파일
```
src/db_setup.py         ← 15+ 테이블, 마이그레이션 대폭 확장
src/sync.py             ← sync 완료 후 engine.recompute_recent() 호출
src/web/app.py          ← 12개 블루프린트 등록, context_processor
src/web/bg_sync.py      ← 백그라운드 sync + 메트릭 재계산
src/web/views_activity.py ← 2차 메트릭 + FEARP + DI + classification
src/web/views_activities.py ← 필터/정렬/그룹핑 대폭 확장
src/web/helpers.py      ← SVG 게이지/레이더/ECharts/bottom_nav/다크테마
```

---

## 구현 우선순위 (PDF 기준)

### 즉시 구현 (0-3개월, 단순 계산)
1. `LSI` — today_load / rolling_21day_avg
2. `FEARP` — 환경 보정 페이스 (날씨 + 고도 + 경사)
3. `ADTI` — 8주 Aerobic Decoupling 선형 회귀
4. `TIDS` — 심박존별 훈련 강도 분포

### 이후 구현 (3-6개월, 복합 계산)
5. `ACWR`, `TRIMP` — 부하 비율, 훈련 임펄스
6. `UTRS` — 통합 훈련 준비도 (5요소 가중합)
7. `CIRS` — 복합 부상 위험 (4요소: ACWR+Monotony+Spike+Asym)
8. `DI` — 내구성 지수 (pace/HR 비율법)
9. `DARP` — 레이스 예측 (VDOT + DI)
10. `RMR` — 러너 성숙도 레이더 (5축)

---

## 메트릭 두 버전 비교 정책

| 항목 | 내용 |
|------|------|
| 기본 구현 | `metrics.md` (PDF 원본 버전) 기준으로 구현 |
| 대안 버전 | `metrics_by_claude.md` (Claude 연구 버전) |
| 향후 | 두 버전 실제 데이터 비교 후 최종 채택 또는 사용자 선택 옵션 |
| 차이 있는 메트릭 | UTRS(가중치), CIRS(구성요소), DI(계산법), RMR(축 수) |

---

## 작업 시 필수 체크리스트

### 새 파일 생성 전
- [ ] `design/.ai/architecture.md`에서 해당 모듈 위치 확인
- [ ] `design/.ai/files_index.md`에서 이미 설계된 파일명 확인
- [ ] 300줄 이하 유지 계획 수립

### 메트릭 함수 구현 전
- [ ] `design/.ai/metrics.md`에서 해당 메트릭 계산식 확인
- [ ] 필요한 DB 컬럼/테이블 확인 (`design/.ai/architecture.md` DB 스키마 섹션)
- [ ] 데이터 없을 때 graceful fallback 방안 결정 (None 반환 또는 기본값)

### UI 구현 전
- [ ] `design/3_통합_대시보드_UI_설계.html` 해당 섹션 참조
- [ ] 다크 테마 색상 코드 사용: `#00d4ff`(cyan), `#00ff88`(green), `#ff4444`(red), `#ffaa00`(orange)
- [ ] Chart.js CDN 사용 (별도 설치 금지), SVG fallback 준비

### 테스트
- [ ] 새 함수마다 최소 1개 테스트
- [ ] `python -m pytest tests/` 전체 통과 확인
- [ ] 메트릭 함수: None 입력, 데이터 부족, 정상 케이스 모두 커버

---

## 주요 설계 결정 빠른 참조

| 결정 | 내용 |
|------|------|
| RMR 축 수 | **5개** (유산소용량/역치강도/지구력/동작효율성/회복력) — 6개 아님 |
| DI 계산법 | pace/HR 비율법 `DI(t) = (pace_t/pace_0)/(HR_t/HR_0)` — 페이스 저하율 아님 |
| CIRS 가중치 | ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asymmetry×0.1 |
| UTRS 가중치 | sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15 |
| DI 최소 요건 | 90분+ 세션, 8주간 3회 이상 (미달 시 None) |
| 날씨 API | Open-Meteo (무료, 키 없음, 과거 날씨 지원) |
| Chart.js | CDN 방식, 오프라인 시 SVG fallback |
| 메트릭 저장 | `computed_metrics` (date + metric_name UNIQUE) / `activity_detail_metrics` |
