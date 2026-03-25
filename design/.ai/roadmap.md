# v0.2 개발 로드맵

## 목표
4소스 통합 데이터를 기반으로 2차 메트릭을 계산하고, 고도화된 웹 대시보드로 표현한다.
사용자가 기존 러닝앱에서 볼 수 없는 통합 인사이트를 RunPulse에서 확인할 수 있게 한다.

---

## PDF 2번 파일 기준 구현 단계

### 0-3개월: 즉시 구현 (단순, 높은 가치)
LSI, FEARP, ADTI, TIDS, SAPI
- 단일 소스 또는 간단한 계산으로 구현 가능
- 즉각적인 사용자 가치 제공

### 3-6개월: 복합 구현 (다소스, 고도 계산)
CIRS, UTRS, DI, REC, RRI
- 여러 소스의 데이터 통합 필요
- ACWR/Monotony/Decoupling 전제 필요

### 6-12개월: ML 기반 (고급)
TQI, TEROI, PLTD, SAPI 고도화
- 충분한 데이터 누적 후 구현
- 머신러닝/통계 모델 필요

---

## Sprint 1: 기반 + 0-3개월 메트릭 (Phase 0-1 일부)
**목표**: DB 준비 + LSI/FEARP/ADTI/TIDS 동작

- DB 스키마 확장 (computed_metrics, weather_data)
- 날씨 API 연동 (Open-Meteo, 무료)
- LSI: today_load / rolling_21day_avg
- FEARP: 날씨 + 고도 + 경사 보정 페이스
- ADTI: 8주 Aerobic Decoupling 선형 회귀 기울기
- TIDS: 심박존별 훈련 강도 분포 + 목표 모델 비교
- 단위 테스트

**검증 기준**: `python src/sync.py --source all --days 7` 후 `computed_metrics`에 lsi, tids, adti 값 저장됨

---

## Sprint 2: 복합 메트릭 엔진 (Phase 1 나머지)
**목표**: ACWR → TRIMP → UTRS → CIRS → Decoupling → DI → DARP → RMR

- TRIMP 자체 계산 (TRIMPexp Banister 공식)
- ACWR (7일 급성 / 28일 만성 비율)
- UTRS (5요소 가중합: sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15)
- CIRS (4요소: ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1)
- Aerobic Decoupling (Pa:HR 전/후반 비교)
- DI (pace/HR 비율법, 90분+ 세션 최소 3회 필요)
- DARP (VDOT 기반 + DI 보정)
- RMR (**5개 축**: 유산소용량/역치강도/지구력/동작효율성/회복력)
- 메트릭 배치 엔진 (sync 완료 후 자동 계산)

**검증 기준**: `computed_metrics`에 utrs, cirs, acwr, di, darp_half 저장 확인

---

## Sprint 3: 통합 대시보드 (Phase 3) ✅ 완료 (2026-03-23)
**목표**: 메인 화면을 대시보드로 전환

- [x] UTRS/CIRS 반원 SVG 게이지 + 하위 요인 표시
- [x] CIRS≥50/75 경고 배너 (조건부)
- [x] RMR 5축 SVG 레이더 차트 (3개월 전 비교 오버레이)
- [x] PMC 차트 (Chart.js CDN, CTL/ATL/TSB 60일)
- [x] 최근 활동 목록 (FEARP/RelativeEffort 배지)
- [x] `/` → `/dashboard` 리다이렉트, 블루프린트 등록
- [x] helpers.py SVG 게이지·레이더·no_data_card 헬퍼 추가

**검증 기준**: `/dashboard` 접속 시 UTRS/CIRS 게이지와 PMC 차트가 실제 데이터로 렌더링 ✅

---

## Sprint 4-A: 공통 UI 기반 ✅ 완료

- [x] ECharts CDN으로 교체 (Chart.js → ECharts, PMC 재작성)
- [x] `bottom_nav(active_tab)` 함수 (7탭, 개발자 탭 조건부)
- [x] 다크 테마 CSS 공통화
- [x] 기존 `/dashboard`, `/settings`, `/activities`에 bottom_nav 적용

---

## Sprint 4-B: Jinja2 render_template 전환 ✅ 완료

- [x] `templates/base.html` — 공통 레이아웃
- [x] `templates/macros/gauge.html`, `radar.html`, `no_data.html`
- [x] views_dashboard.py, views_settings.py → render_template 전환

---

## Sprint 4-C: 화면 구현 (Phase 4-5) ✅ 완료

- [x] activity_deep에 FEARP + DI + 2차 메트릭 카드 + classification 배지
- [x] 분석 레포트 `/report` (기간 선택, ECharts, TIDS/TRIMP/Risk/DARP)

---

## Sprint 5: 데이터 파이프라인 + 레이스 + AI 코칭 ✅ 완료 (2026-03-25)

- [x] Sprint 5-A: 데이터 레이어 아키텍처 확립
- [x] Sprint 5-B: 동기화 인프라 (4소스 병렬, Garmin/Strava/Intervals 신규 API)
- [x] Sprint 5-C: 메트릭 추가 (RTTI, WLEI, TPDI) + zone 소스 fallback
- [x] Sprint 5-E: 버그 수정 (unified_activities, icu_intensity, 4xx 로그)
- [x] Sprint 5-F: API 데이터 감사 수정 (5건)
- [x] `/race` 레이스 예측 화면 (DARP, DI, templates/race.html)
- [x] `/ai-coaching` AI 코칭 (브리핑+추천칩, templates/ai_coaching.html)
- [x] `/wellness` 웰니스 트렌드 (수면/HRV/BB/스트레스)

---

## Multi-User: 사용자별 DB/config 분리 ✅ 완료 (2026-03-25)

- [x] `data/users/{user_id}/running.db` + `config.json` 분리
- [x] Flask 세션 기반 user_id + `/switch-user` UI
- [x] CLI `--user` 파라미터
- [ ] 인증/로그인 → v0.3

---

## Sprint 6: 훈련 계획 + 설정 통합 + 마무리 (Phase 8-9) ⏳ 진행 중

- [x] V2-8-1a: `/training` 스캐폴딩 (placeholder) ✅ 완료 (2026-03-25)
- [x] V2-9-3: graceful fallback 전면 보강 ✅ 완료 (2026-03-25)
- [x] V2-9-4: Settings hub 고도화 (last_sync 표시 + 사용자 프로필 설정) ✅ 완료 (2026-03-25)
- [ ] V2-9-5: `/dev` 개발자 탭 (views_dev.py 구현됨, 탭 등록만)
- [ ] A: 탭/화면 구성 정리 (wellness/race 탭 배치 결정)
- [ ] V2-9-10/11: 디자인 파일 원격 커밋
- [x] B-1: 파일 크기 리팩토링 (기능 기준 분리) ✅ 부분 완료 (2026-03-25)
  - [x] helpers.py → helpers_svg.py 분리 (1042→854줄)
  - [x] views_activity_cards.py → views_activity_source_cards.py 분리 (1102→731줄)
  - [x] views_activity.py → views_activity_cards.py + views_activity_loaders.py 분리 (1529→185줄)
  - [x] app.py → views_dev.py 분리 (1351→839줄)

---

## 의존 관계
```
Phase 0 (DB+날씨) → Phase 1 (메트릭 엔진)           ← ✅ 완료
                            ↓
Phase 2 (sync 연동) → Phase 3 (대시보드)              ← ✅ 완료
                            ↓
                    Sprint 4-A/B/C (UI 기반+화면)     ← ✅ 완료
                            ↓
                    Sprint 5 (데이터+Race+AI+Wellness) ← ✅ 완료
                            ↓
                    Sprint 6 (Training+Settings+마무리) ← ⏳ 진행 중
                            ↓
                    A (탭/화면 구성 정리)               ← ⏳ 다음
```

---

## 구현 시 주의사항
1. **메트릭 데이터 없을 때**: 모든 UI는 "데이터 없음" 대신 "수집 중" 상태를 graceful하게 표시
2. **PDF 계산식 우선**: 본 문서와 구현 차이 발생 시 HTML 변환 PDF(1번, 2번) 기준으로 수정
3. **ECharts**: CDN 방식 사용 (Sprint 4-A에서 Chart.js → ECharts 교체 완료)
4. **파일 300줄 제한**: 각 metrics/*.py 파일 분리 유지
5. **날씨 API**: Open-Meteo (https://open-meteo.com) - 키 없이 사용, 과거 날씨 지원
6. **RMR**: 5개 축 (유산소용량/역치강도/지구력/동작효율성/회복력) — 6개 축 아님
7. **DI**: pace/HR 비율법 사용, 최소 90분+ 세션 8주간 3회 없으면 None 반환
8. **CIRS 가중치**: ACWR×0.4 + Monotony×0.2 + Weekly_spike×0.3 + Asymmetry×0.1
