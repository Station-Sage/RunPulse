# v0.2 작업 목록

최종 업데이트: 2026-03-25

---

## 현재 미완료 작업 (이 섹션만 읽을 것)

### v0.2 잔여

- [x] **6.4**: Settings 보완 — sync 상태 허브, 시스템 정보 카드
- [x] **6.5**: Race Prediction 잔여 — 예측 이력 테이블
- [x] **6.6**: AI Coach 잔여 — 최근 훈련 요약, 리스크 요약 카드
- [ ] **6.7**: Training Plan UI (v0.3 예정)
- [x] **6.8**: Wellness 보완 — 7일 트렌드 차트, 회복 권장 카드
- [ ] **S5-C2**: 대폭 확장된 데이터 반영 UI 전면 재설계
  - Sprint 5-A~C로 추가된 데이터(날씨/존/running dynamics/running tolerance 등) UI 노출
- [x] **V2-5-3**: Report AI 인사이트 실체화 (규칙 기반 메트릭 분석, briefing.py 구조 활용)
- [x] **V2-5-4**: Report 기간 선택기 7개 확장 (today/week/month/quarter/year/1year/custom)
- [x] **V2-6-1a~f**: 레이스 예측 UI 참고 디자인 수준 보강 (splits 그리드, VDOT/순위, DI 게이지)
- [x] **V2-7-1a~e**: AI 코칭 UI 참고 디자인 수준 보강 (프로필 애니메이션, 브리핑 액션, 채팅 레이아웃)
- [x] **V2-9-12**: decisions.md Settings Platform Roadmap 추가 (D-V2-17)
- [x] **V2-9-13**: 비전-코드 DI/CIRS 공식 불일치 주석
- [x] **V2-9-14**: design/app-UI/dashboard.html RMR 6축→5축 수정
- [x] **B-4**: 참고 디자인 RMR 5축 수정 (V2-9-14와 동일)

### v0.3 예정 (메트릭)

- [ ] **V3-1-3**: eFTP (Intervals.icu 데이터)
- [ ] **V3-1-4**: Critical Power / W' (파워 데이터)
- [ ] **V3-2-1**: REC (통합 러닝 효율성)
- [ ] **V3-2-2**: RRI (레이스 준비도 지수)
- [ ] **V3-2-3**: SAPI (계절·날씨 성과 비교)
- [ ] **V3-2-4**: TEROI (훈련 효과 투자 수익률)

### v0.3 예정 (인프라)

- [ ] 인증/로그인 시스템 (bcrypt, 세션, 리다이렉트)
- [ ] PWA (오프라인, manifest, service worker)
- [ ] REST API (`/api/v1/*`)
- [ ] DB 정규화, 멀티유저 강화
- [ ] AI 채팅 (대화형 코칭)
- [ ] Training Plan 풀 구현 (캘린더 UI, 운동 CRUD, 캘린더 연동)

### v0.4 예정

- [ ] React Native 모바일 앱
- [ ] **V4-1-1**: TQI (훈련 품질 지수) — ML 기반
- [ ] **V4-1-2**: PLTD (개인화 역치 자동 탐지) — ML 기반
- [ ] **V2-9-4a**: GPX/FIT/TCX 개별 파일 Import (v0.2에서 이동)
- [ ] **V2-9-4b**: CSV/JSON Export (v0.2에서 이동)

---
---

## 아래는 완료 히스토리 (참고용)

---

## 메트릭 전체 현황

### 1차 메트릭 커버리지

| 메트릭 | 상태 |
|--------|------|
| ATL/CTL/TSB (PMC) | ✅ v0.2 |
| TRIMP / HRSS | ✅ v0.2 |
| rTSS | ✅ v0.2 |
| VDOT | ✅ v0.2 |
| Aerobic Decoupling | ✅ v0.2 |
| GAP / NGP | ✅ v0.2 |
| EF (효율 계수) | ✅ v0.2 |
| Monotony & Strain | ✅ v0.2 |
| Relative Effort | ✅ v0.2 |
| Marathon Shape | ✅ v0.2 |
| Running Dynamics | ✅ v0.2 |
| eFTP | ⏳ v0.3 |
| Critical Power | ⏳ v0.3 |

### 2차 메트릭 (RunPulse 고유)

| 코드 | 명칭 | 상태 |
|------|------|------|
| UTRS | 통합 훈련 준비도 | ✅ v0.2 |
| DI | 내구성 지수 | ✅ v0.2 |
| CIRS | 복합 부상 위험 | ✅ v0.2 |
| LSI | 부하 스파이크 | ✅ v0.2 |
| ACWR | 급성/만성 부하 비율 | ✅ v0.2 |
| FEARP | 환경 보정 페이스 | ✅ v0.2 |
| ADTI | 유산소 분리 추세 | ✅ v0.2 |
| TIDS | 훈련 강도 분배 | ✅ v0.2 |
| DARP | 내구성 보정 레이스 예측 | ✅ v0.2 |
| RMR | 러너 성숙도 레이더 | ✅ v0.2 |
| RTTI | 러닝 내성 훈련 지수 | ✅ v0.2 |
| WLEI | 날씨 가중 노력 지수 | ✅ v0.2 |
| TPDI | 실내/야외 퍼포먼스 격차 | ✅ v0.2 |
| REC | 통합 러닝 효율성 | ⏳ v0.3 |
| RRI | 레이스 준비도 지수 | ⏳ v0.3 |
| SAPI | 계절·날씨 성과 비교 | ⏳ v0.3 |
| TEROI | 훈련 효과 ROI | ⏳ v0.3 |
| TQI | 훈련 품질 지수 | ⏳ v0.4 (ML) |
| PLTD | 개인화 역치 탐지 | ⏳ v0.4 (ML) |

---

## Phase 0: 기반 준비 ✅ 완료

- [x] V2-0-1~3: DB 스키마 확장, Open-Meteo 날씨, 마이그레이션 테스트

## Phase 1: 2차 메트릭 계산 엔진 ✅ 완료

- [x] 그룹 A: GAP/NGP/LSI/FEARP/ADTI/TIDS/RelativeEffort/MarathonShape + store
- [x] 그룹 B: ACWR/TRIMP/Monotony/UTRS/CIRS/Decoupling/DI/DARP/RMR + engine

## Phase 2: 동기화 후 메트릭 자동 계산 ✅ 완료

- [x] sync 후 engine 호출, 재계산 엔드포인트

## Phase 3: 통합 대시보드 UI ✅ 완료

- [x] UTRS/CIRS 게이지, RMR 레이더, PMC 차트, 최근 활동

## Sprint 4-A/B/C: UI 기반 + Jinja2 + 화면 구현 ✅ 완료

- [x] ECharts, bottom_nav, 다크 테마, templates, 활동 상세 2차 메트릭, 레포트

## Phase UI-Gap: v0.2 UI 보완 ✅ 부분 완료

- [x] 6.1~6.3: Dashboard/Activity/Report 보완
- [x] 7.3: Strava Archive Import UI

## Phase API-Garmin/Strava/Intervals: 전체 API 수집 ✅ 완료

- [x] Garmin: 80컬럼 확장, streams/gear/exercise_sets, 일별 확장, 선수 데이터
- [x] Strava: 모듈 분리, 29컬럼, streams DB, best_efforts, athlete/stats/gear
- [x] Intervals: 모듈 분리, 31컬럼, intervals/streams, athlete/stats

## Phase PERF: 성능 개선 ✅ 완료

- [x] 복합 인덱스, 페이지네이션, TTL 캐시, 4소스 병렬 sync

## Sprint 5: 데이터 파이프라인 + 레이스 + AI 코칭 ✅ 완료

- [x] 5-A: 데이터 레이어 아키텍처 (4계층)
- [x] 5-B: 병렬 동기화, Garmin/Strava/Intervals 신규 API
- [x] 5-C: RTTI/WLEI/TPDI 메트릭, zone fallback
- [x] 5-E: 버그 수정 (hex 오분류, 서비스 메트릭 누락 등)
- [x] 5-F: API 데이터 감사 (Bug #1~#5, Check #6~#7)
- [x] /race 레이스 예측, /ai-coaching AI 코칭, /wellness 웰니스

## Sprint 5-D: 미완료 항목 처리 ✅ 부분 완료

- [x] S5-B1: 재계산 ETA 표시
- [x] S5-C1: 서비스 탭 UI 분리

## Phase 6-7: 레이스 예측 + AI 코칭 ✅ 기본 구현 완료

- [x] /race (DARP, DI, 페이스전략, HTW)
- [x] /ai-coach (브리핑, 추천칩, 웰니스 컨텍스트)

## Phase 8-9: 훈련 계획 + 설정 + 마무리 ✅ 기본 완료

- [x] V2-8-1a/b: /training 스캐폴딩 + 기본 구현
- [x] V2-9-3~V2-9-11: graceful fallback, Settings hub, 통합 테스트, 리다이렉트, DB 마이그레이션, Mapbox

## Multi-User ✅ 기본 완료

- [x] 사용자별 DB/config 분리, Flask 세션, CLI --user

## Priority B ✅ 부분 완료

- [x] B-1: 파일 크기 리팩토링 (helpers_svg, views_activity 분리 등)
- [x] B-2: graceful fallback 전면 보강
- [x] B-3: Settings hub 고도화

---

테스트: **829개** 통과 (2026-03-25 기준)
