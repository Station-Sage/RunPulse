# v0.2 todo.md 업데이트 패치

> 작성일: 2026-03-24
> 근거: v0.2 3-Layer 감사 보고서
> 적용: design/.ai/todo.md 해당 섹션에 병합

---

## Phase 5 (분석 레포트) — 추가 항목

- [ ] V2-5-3: Report AI 인사이트 실체화
  - render_ai_insight()를 src/ai/briefing.py 출력과 연결
  - 표시: DI 향상, 유산소 효율성, 주간 거리 경고 (3개 카드)
  - 참고 디자인: design/app-UI/analysis_report.html .insights-section

- [ ] V2-5-4: Report 기간 선택기 7개 확장
  - 기존: week / month / 3month
  - 추가: today / quarter / year / 1year / custom
  - custom: 시작일-종료일 date input
  - 참고 디자인: design/app-UI/analysis_report.html .report-selector

---

## Phase 6 (레이스 예측 UI) — 추가 항목

기존 V2-6-1 하위에 추가:

- [ ] V2-6-1a: 거리 선택기 — 5K/10K/하프/마라톤/커스텀 5칸 그리드 카드
- [ ] V2-6-1b: DARP 결과 카드 — 대형 시간 + 페이스 + 4칸 스플릿 (5K/10K/15K/순위%)
- [ ] V2-6-1c: DI 시각화 — 수평 그라데이션 바 + % 마커 + 3단계 라벨
- [ ] V2-6-1d: 페이스 전략 — 구간별 수평 바 (green/yellow/red)
- [ ] V2-6-1e: Hitting the Wall — 확률% 뱃지 + 빨간 보더 카드 + 설명
- [ ] V2-6-1f: 훈련 조정 권장 — cyan 보더 카드 + 반영 버튼 (Training Plan 미구현 시 disabled)

참고 디자인: design/app-UI/race_prediction.html

---

## Phase 7 (AI 코칭 UI) — 추가 항목

기존 V2-7-1 하위에 추가:

- [ ] V2-7-1a: 코치 프로필 카드 — 80px 아바타 + 이름 + pulse 상태 indicator
- [ ] V2-7-1b: 오늘의 브리핑 카드 — src/ai/briefing.py 연결 + 재생성/공유 버튼
- [ ] V2-7-1c: 추천 칩 4개 — 회복(UTRS)/훈련(DI)/FEARP/부상(CIRS) 기반
- [ ] V2-7-1d: 빠른 질문 버튼 4개 — 고정 하단 영역
- [ ] V2-7-1e: 채팅 placeholder — v0.3에서 대화형 코칭이 추가됩니다 안내

참고 디자인: design/app-UI/ai_coaching.html

---

## Phase 8 (훈련 계획) — 범위 축소

- [ ] V2-8-1a: views_training_plan.py 스캐폴딩
  - Blueprint training_bp, /training GET
  - placeholder 페이지: 훈련 계획 기능이 곧 추가됩니다
  - bottom_nav('training') 연결
- [->] V2-8-1 풀 구현 -> v0.3으로 이연 (캘린더 UI, 운동 CRUD, 캘린더 연동)

참고 디자인: design/app-UI/training_plan.html

---

## Phase 9 (설정 + 마무리) — 추가 항목

### Import/Export 확장

- [ ] V2-9-4a: GPX/FIT/TCX 개별 파일 Import
  - views_import.py에 /import/file GET/POST 추가
  - 파일 업로드 -> 파싱 -> activity_summaries 저장 -> 결과 카드
- [ ] V2-9-4b: CSV/JSON Export
  - /export/data POST -> 활동+메트릭 CSV 다운로드
  - Content-Disposition: attachment; filename=runpulse_export_YYYYMMDD.csv

### 디자인 문서 원격 커밋

- [ ] V2-9-10: 비전 문서 커밋
  - design/3_통합_대시보드_UI_설계.html -> git add + commit
- [ ] V2-9-11: 참고 디자인 커밋 (7개 파일)
  - design/app-UI/dashboard.html
  - design/app-UI/activity_detail.html
  - design/app-UI/analysis_report.html
  - design/app-UI/settings_sync.html
  - design/app-UI/race_prediction.html
  - design/app-UI/ai_coaching.html
  - design/app-UI/training_plan.html

### 문서 정합성 해소

- [ ] V2-9-12: decisions.md Settings Platform Roadmap 섹션 추가
  - v0.2: Garmin / Strava / Intervals.icu / Runalyze (현행 유지)
  - v0.3: TrainingPeaks 추가 검토
  - v0.4: Google Calendar / Naver Calendar 연동
- [ ] V2-9-13: 비전-코드 공식 불일치 주석
  - DI: 비전 (후반효율-전반효율)/전반효율 vs 구현 pace/HR 비율법
    -> decisions.md 참조 주석 추가, 구현이 정본
  - CIRS: 비전 구성요소명 vs decisions.md 가중치
    -> decisions.md가 정본임을 명시
- [ ] V2-9-14: design/app-UI/dashboard.html RMR SVG 6축->5축
  - 경제성 축 제거
  - 비전 5차원 + decisions.md + 코드와 일치

---

## Priority B — 추가/상세화

### B-1 파일 크기 리팩토링 (상세화)

분리 대상:

- [ ] B-1a: app.py -> app.py + app_routes.py + app_helpers.py
- [ ] B-1b: views_activity.py -> views_activity.py + views_activity_sources.py + views_activity_metrics.py
- [ ] B-1c: helpers.py -> helpers.py + helpers_svg.py + helpers_nav.py
- [ ] B-1d: views_activities.py -> views_activities.py + views_activities_filters.py
- [ ] B-1e: views_settings.py -> views_settings.py + views_settings_garmin.py + views_settings_strava.py

검증: 분리 후 모든 파일 300줄 이하, 797+ 테스트 통과

### B-4 (신규): 참고 디자인 RMR 수정

- [ ] B-4: design/app-UI/dashboard.html RMR 6축->5축
  (V2-9-14와 동일, B-Priority로도 추적)

---

## 감사 보고서 참조 문서

| 레이어 | 파일 | 역할 |
|--------|------|------|
| L1 비전 | design/3_통합_대시보드_UI_설계.html | 최종 지향점, 메트릭 체계, 7대 기능, 4-Phase 로드맵 |
| L2 참고 | design/app-UI/dashboard.html | 대시보드 다크테마 프로토타입 |
| L2 참고 | design/app-UI/activity_detail.html | 활동 상세 프로토타입 |
| L2 참고 | design/app-UI/analysis_report.html | 분석 레포트 프로토타입 |
| L2 참고 | design/app-UI/settings_sync.html | 설정/동기화 프로토타입 |
| L2 참고 | design/app-UI/race_prediction.html | 레이스 예측 프로토타입 |
| L2 참고 | design/app-UI/ai_coaching.html | AI 코칭 프로토타입 |
| L2 참고 | design/app-UI/training_plan.html | 훈련 계획 프로토타입 |
| L3 명세 | design/.ai/decisions.md | RMR 5축, DI 공식, CIRS 가중치 등 |
| L3 명세 | design/.ai/metrics.md | PDF 기반 공식 메트릭 정의 |
| L3 명세 | design/.ai/v0.2_ui_gap_analysis.md | UI 갭 분석 |
| L4 코드 | src/web/views_*.py, src/metrics/*.py | 실제 구현체 |

---

## v0.2 잔여 작업 순서

현재 상태: Sprint 4-C + UI-Gap 완료, 797 테스트 통과

-> Sprint 5 (V2-6-1 Race + V2-7-1 AI Coach + V2-5-3 Report AI 인사이트)
   충돌 위험: 중 (app.py Blueprint 등록, report_sections 수정)

-> Sprint 6 전반 (V2-8-1a Training 스캐폴딩 + V2-9-4a/b Import/Export + V2-5-4 기간 확장)
   충돌 위험: 중 (views_import.py 라우트 추가)

-> Sprint 6 후반 (V2-9-10~14 디자인 커밋 + 문서 정합성 + V2-9-5~8 마무리)
   충돌 위험: 저 (문서 추가, 설정 변경 없음)

-> Priority B (B-1 파일 리팩토링 + B-2 fallback + B-3 Settings hub + B-4 RMR)
   충돌 위험: 중 (대규모 파일 분리, import 경로 변경)

-> v0.2 완료 -> changelog 업데이트 -> v0.3 브랜치 생성
