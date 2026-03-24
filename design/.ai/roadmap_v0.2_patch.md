# v0.2 로드맵 업데이트 패치

> 작성일: 2026-03-24
> 근거: v0.2 3-Layer 감사 보고서 (비전 문서 ↔ 참고 디자인 ↔ 코드 대조)
> 적용 대상: design/.ai/roadmap.md

---

## 변경 요약

감사 결과 아래 항목이 v0.2 범위 내 미완료로 확인됨.
기존 Sprint 5/6/B-Priority에 반영하여 v0.2 브랜치에서 완료한다.

---

## Sprint 5 업데이트 (Phase 6-7: 레이스 예측 + AI 코칭)

### 추가/변경 항목

기존 Sprint 5 항목에 아래를 추가한다:

#### Phase 6 (Race Prediction) 보강

V2-6-1 기존 명세에 감사 결과 확인된 참고 디자인 컴포넌트를 명시:

- 거리 선택기: 5K/10K/하프/마라톤/커스텀 5칸 그리드 카드
  (참고: design/app-UI/race_prediction.html .race-options)
- DARP 예측 결과 카드: 대형 시간(56px급) + 평균 페이스 + 5K/10K/15K 스플릿 4칸
- DI 시각화: 수평 그라데이션 바 + 마커 + 부족/양호/우수 라벨 + 설명 텍스트
- 페이스 전략: 구간별 수평 바 (green/yellow/red segment-fill)
- Hitting the Wall 확률: 빨간 그라데이션 보더 카드 + 확률% 뱃지 + 설명
- 훈련 플랜 조정 권장: cyan 보더 카드 + 반영하기 버튼
  (Training Plan 미구현 시 버튼 disabled + tooltip)

#### Phase 7 (AI Coaching) 보강

V2-7-1 기존 명세에 추가:

- 코치 프로필 카드: 80px 그라데이션 아바타 + RunPulse AI 코치 + pulse 상태
  (참고: design/app-UI/ai_coaching.html .coach-profile)
- 오늘의 브리핑 카드: briefing.py 엔진 출력 연결, 재생성/공유 버튼
  (채팅은 placeholder: v0.3에서 대화형 코칭이 추가됩니다)
- 추천 칩 4개: 회복/훈련/FEARP/부상 경고 (UTRS/CIRS/FEARP/LSI 기반)
- 빠른 질문 4개: 오늘 훈련 강도는? / 내구성 지수가 떨어졌어요 / 마라톤 준비도 확인 / FEARP 보정 방법

#### 신규: Report AI 인사이트 실체화

- V2-5-3 (신규): views_report_sections.py render_ai_insight()를
  src/ai/briefing.py 출력과 연결하여 placeholder를 실제 분석 텍스트로 교체
- 표시 항목: DI 향상 인사이트, 유산소 효율성 코멘트, 주간 거리 경고
  (참고: design/app-UI/analysis_report.html .insights-section 3개 카드 구조)

Sprint 5 검증 기준 업데이트:
- /race 라우트에서 5K/10K/Half/Full 선택 시 DARP 예측 + DI 바 + HTW 확률 표시
- /ai-coach 라우트에서 코치 프로필 + 브리핑 카드 + 추천 칩 4개 표시
- /report AI 인사이트 섹션에 briefing.py 기반 실제 텍스트 표시
- 참고 디자인 대비 80%+ 컴포넌트 커버리지
- 기존 테스트 suite 전체 통과

---

## Sprint 6 업데이트 (Phase 8-9: 훈련 계획 + 설정 + 마무리)

### 추가/변경 항목

#### Phase 8 (Training Plan) — 스캐폴딩만 진행

기존 V2-8-1의 풀 캘린더 구현 대신 v0.2에서는 스캐폴딩만 수행:

- V2-8-1a (변경): views_training_plan.py 생성, Blueprint training_bp,
  /training GET -> placeholder 페이지 렌더
- V2-8-1b (변경): bottom_nav에서 훈련 탭 클릭 시 /training으로 이동 확인
- V2-8-1 풀 구현(캘린더 UI, 운동 CRUD, 캘린더 연동)은 v0.3으로 이연

#### Phase 9 (Settings + 마무리) 보강

V2-9-4 기존 명세에 감사 결과 항목 추가:

- V2-9-4a (신규): GPX/FIT/TCX 개별 파일 Import
  views_import.py에 /import/file GET/POST 라우트 추가
  (비전 문서 Part 3 5번 데이터 Import/Export 대응)
- V2-9-4b (신규): CSV/JSON Export
  /export/data POST 라우트 추가
  활동 + 메트릭 CSV 다운로드 (Content-Disposition: attachment)
- V2-9-4c (신규): Report 기간 선택기 7개로 확장
  기존 3개(week/month/3month) -> 7개(today/week/month/quarter/year/1year/custom)
  (참고: design/app-UI/analysis_report.html .report-selector 7개 탭)

#### 신규: 디자인 문서 커밋 + 문서 정합성

- V2-9-10 (신규): design/3_통합_대시보드_UI_설계.html 원격 브랜치 커밋
- V2-9-11 (신규): design/app-UI/ 하위 7개 HTML 원격 브랜치 커밋
  파일 목록:
  - design/app-UI/dashboard.html
  - design/app-UI/activity_detail.html
  - design/app-UI/analysis_report.html
  - design/app-UI/settings_sync.html
  - design/app-UI/race_prediction.html
  - design/app-UI/ai_coaching.html
  - design/app-UI/training_plan.html
- V2-9-12 (신규): decisions.md에 Settings Platform Roadmap 섹션 추가
  v0.2: 현재 4소스(Garmin/Strava/Intervals/Runalyze) 유지
  v0.3: TrainingPeaks 추가 검토
  v0.4: Google Calendar / Naver Calendar 연동
- V2-9-13 (신규): 비전 문서 DI/CIRS 공식 주석 추가
  DI: 비전 (후반효율-전반효율)/전반효율 vs 구현 pace/HR 비율법 (decisions.md 참조)
  CIRS: 비전 구성요소명 vs decisions.md 가중치 -> decisions.md가 정본
- V2-9-14 (신규): design/app-UI/dashboard.html RMR SVG 6축->5축 수정

Sprint 6 검증 기준 업데이트:
- /training 라우트에 placeholder 페이지 렌더
- /import/file GET -> 업로드 폼, POST -> 파일 처리 + 결과 카드
- /export/data POST -> CSV 파일 다운로드
- /report 기간 선택기 7개 탭 동작
- design/ 하위 비전+참고 디자인 파일 원격 존재 (8개)
- decisions.md에 Settings Platform Roadmap 존재
- DI/CIRS 문서 불일치 0건
- 기존 테스트 suite 전체 통과

---

## Priority B 업데이트

### B-1 파일 크기 리팩토링 (상세화)

대상 파일 및 분리 방안:

- app.py (~1349줄) -> app.py(create_app만) + app_routes.py(홈/sync) + app_helpers.py(캐시/유틸)
- views_activity.py (~1062줄) -> views_activity.py(메인) + views_activity_sources.py(소스별) + views_activity_metrics.py(2차 메트릭)
- helpers.py (~1002줄) -> helpers.py(핵심) + helpers_svg.py(SVG) + helpers_nav.py(네비/레이아웃)
- views_activities.py (~961줄) -> views_activities.py(리스트) + views_activities_filters.py(필터/정렬)
- views_settings.py (~699줄) -> views_settings.py(허브) + views_settings_garmin.py + views_settings_strava.py

검증: 분리 후 모든 파일 300줄 이하, 797+ 테스트 통과

### B-4 (신규): 참고 디자인 RMR 5축 수정

design/app-UI/dashboard.html의 RMR SVG 레이더를 6축->5축으로 수정
(경제성 축 제거, 비전 5차원 + decisions.md + 코드와 일치)

---

## 수정된 의존 관계

Phase 0-3 (완료) -> Sprint 4-A/B/C (완료)
  -> Sprint 5 (Race + AI Coach + Report AI 인사이트)
    -> Sprint 6 (Training 스캐폴딩 + Import/Export + 기간확장 + 디자인 커밋 + 문서정합)
      -> Priority B (파일 리팩토링 + graceful fallback + Settings hub)
        -> v0.2 완료 -> v0.3 브랜치 시작

---

## v0.2 완료 후 예상 상태

| 화면 | v0.2 현재 | Sprint 5 후 | Sprint 6 후 | B 후 (v0.2 최종) |
|------|----------|------------|------------|-----------------|
| Dashboard | 85% | 85% | 85% | 85% |
| Activity Detail | 80% | 80% | 80% | 80% |
| Report | 80% | 90% | 95% | 95% |
| Settings | 50% | 50% | 70% | 75% |
| Race Prediction | 0% | 90% | 90% | 90% |
| AI Coaching | 10% | 60% | 60% | 60% |
| Training Plan | 0% | 0% | 5% | 5% |
| Import/Export | 30% | 30% | 60% | 60% |

v0.3에서 해결: 지도(Mapbox), Training Plan 풀 구현, AI 채팅,
eFTP/CP/REC/RRI/SAPI/TEROI 메트릭, PWA, REST API
