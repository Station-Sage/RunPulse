# v0.2 설계 결정 기록

## D-V2-01: 2차 메트릭 계산을 별도 src/metrics/ 모듈로 분리
- **결정**: `src/analysis/` 에 넣지 않고 `src/metrics/` 독립 모듈로 분리
- **이유**: analysis는 리포트 생성, metrics는 수치 계산 — 역할이 다름. metrics는 sync 후 자동 실행되고 DB에 저장되는 사이드이펙트가 있어 분리가 명확함
- **결과**: `src/metrics/engine.py`가 sync 완료 후 호출

## D-V2-02: computed_metrics 테이블 (date + metric_name 복합 유니크)
- **결정**: 날짜별로 메트릭 이름을 키로 저장 (`UNIQUE(date, metric_name)`)
- **이유**: 활동별이 아니라 일별 상태 값이 대부분 (UTRS, CIRS, ACWR 등). 활동별 메트릭은 기존 `activity_detail_metrics` 테이블 사용
- **결과**: `ON CONFLICT DO UPDATE`로 재계산 시 덮어쓰기

## D-V2-03: 날씨 API는 Open-Meteo (무료, 키 없음)
- **결정**: OpenWeatherMap(유료), WeatherAPI(한도 제한) 대신 Open-Meteo 사용
- **이유**: 프로젝트 목표가 "전액 무료". Open-Meteo는 과거 날씨 조회 지원, 상업적 이용도 무료
- **결과**: `src/weather/provider.py`에서 httpx로 직접 호출, `weather_data` 테이블에 캐싱

## D-V2-04: Chart.js는 CDN 방식 (npm/pip 설치 없음)
- **결정**: `<script src="https://cdn.jsdelivr.net/npm/chart.js">` CDN 방식
- **이유**: Python 백엔드에 JS 빌드 도구 추가하지 않음. 오프라인 환경(Termux)을 고려하여 CDN 실패 시 SVG fallback 구현
- **결과**: 레이더 차트(SVG) + PMC/추세 차트(Chart.js) 혼용

## D-V2-05: FEARP 계산에 필요한 경사도는 GPS 스트림 기반
- **결정**: 별도 지형 API 사용하지 않고 Strava altitude stream에서 경사도 계산
- **이유**: 외부 지형 API 추가 비용/복잡성 방지. Strava 스트림에 altitude[] 포함됨
- **결과**: `fearp.py`에서 altitude stream 미존재 시 grade_factor=1.0(평지 가정)으로 graceful fallback

## D-V2-06: DI 계산에 최소 데이터 요건 설정
- **결정**: 90분 이상 세션이 최근 8주간 3회 이상 없으면 DI = None
- **이유**: 데이터 부족 시 부정확한 값 노출보다 "데이터 부족" 상태가 낫다
- **결과**: DI None이면 UI에서 "장거리 세션 부족 (8주 3회 이상 필요)" 메시지 표시

## D-V2-07: 하단 네비게이션을 Jinja2 매크로로 공통화
- **결정**: 5개 탭 네비게이션을 `templates/macros/nav.html`에 정의, 모든 페이지에 include
- **이유**: 각 뷰 파일마다 중복 HTML 방지, 탭 활성화 상태만 파라미터로 전달
- **결과**: `{% from 'macros/nav.html' import bottom_nav %}` + `{{ bottom_nav('dashboard') }}`

## D-V2-08: 2가지 메트릭 버전 병행 유지 후 비교 선택
- **결정**: `metrics.md`(PDF 원본)와 `metrics_by_claude.md`(Claude 연구) 두 버전을 병행 유지
- **이유**: 어떤 계산식이 실제 훈련 데이터에서 더 정확한지 아직 검증 안 됨. 사용자가 두 버전 중 선택하거나 A/B 비교 가능하게 구현 예정
- **결과**: 구현 시 metrics.md 우선 사용, 설정으로 버전 전환 가능하도록 설계

## D-V2-08b: HTML 변환 PDF 계산식과 구현 차이 발생 시 PDF 우선
- **결정**: 본 설계 문서의 계산식은 HTML 변환 PDF 원본 기반. 구현 시 PDF 계산식 준수
- **이유**: PDF가 최초 설계 의도를 담고 있음. metrics_by_claude.md는 PDF 기반으로 재작성됨
- **결과**: 계산식 수정 필요 시 해당 metrics/*.py 파일만 수정, 테스트 재실행

## D-V2-09: RMR은 5개 축 (6개 아님)
- **결정**: Runner Maturity Radar는 5개 축 — 유산소용량/역치강도/지구력/동작효율성/회복력
- **이유**: PDF 2번 파일(2차 가공 메트릭) 확정 사양. 이전 설계 초안(6개 축)은 오류
- **결과**: `src/metrics/rmr.py` 5개 축 계산, `computed_metrics`에 rmr JSON 저장 (5 키), SVG 레이더 5각형

## D-V2-10: UTRS 가중치는 sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15
- **결정**: PDF 2번 파일 확정 가중치 사용
- **이유**: 이전 초안(body_battery×0.30 기준)과 다름. HRV와 수면이 각각 25%로 가장 중요
- **결과**: `utrs.py` 구현 시 5가지 요소 정확히 반영

## D-V2-11: CIRS 구성요소는 ACWR×0.4 + Monotony×0.2 + Weekly_spike×0.3 + Asymmetry×0.1
- **결정**: PDF 2번 파일 확정 가중치 — Asymmetry는 GCT 좌우 비대칭 (Garmin 데이터 필요)
- **이유**: 이전 초안(consecutive_days_risk, 피로 누적 등 다른 구성)과 다름
- **결과**: Asymmetry 데이터 없으면 나머지 3개 정규화 후 계산 (graceful fallback)

## D-V2-12: DI는 pace/HR 비율법 사용 (페이스 저하율 아님)
- **결정**: DI(t) = (pace_t/pace_0) / (HR_t/HR_0) — 심박 변화 대비 페이스 유지력
- **이유**: PDF 2번 파일 확정 공식. 이전 초안(pace_drop_pct * 5 방식)은 단순 페이스 저하만 측정
- **결과**: 동일 HR 증가에도 페이스 유지 시 DI 높게 평가됨. 90분+ 세션 3회 미달 시 None

## D-V2-13: 구현 우선순위는 LSI/FEARP/ADTI/TIDS 우선 (0-3개월)
- **결정**: PDF 2번 파일 로드맵 따라 단순 계산 메트릭 먼저 구현
- **이유**: LSI/FEARP/ADTI/TIDS는 단일 소스 계산 가능, 즉각적인 사용자 가치 제공
- **결과**: Phase 1 순서 변경: LSI→FEARP→ADTI→TIDS 먼저, CIRS/UTRS/DI는 이후

## D-V2-14: 홈 화면 TTL 캐시는 db_path별 독립 항목
- **결정**: `_home_cache`를 단일 dict가 아니라 `{str(db_path): {ts, data}}` 맵으로 구현
- **이유**: 단일 키 캐시는 테스트 환경에서 서로 다른 tmp_path 간 오염 발생. 운영 환경에서도 DB 경로 변경 시 오래된 데이터 반환 위험
- **결과**: 각 DB 경로별 독립 TTL 60초 캐시, 전체 테스트 통과

## D-V2-16: 데이터 계층 아키텍처 — 저장 분리 + 입력 유연성
- **결정**: 4계층으로 구분하고 **저장 위치**는 분리하되, **RunPulse 계산 입력**은 모든 소스에서 받을 수 있음
  - **서비스 데이터**: 원본 서비스 API 응답 → `activity_summaries`, `activity_detail_metrics`, `daily_wellness`, `daily_fitness` 등
  - **서비스 1차 메트릭**: 서비스가 자체 제공하는 메트릭 (Garmin training_effect, Strava suffer_score, Intervals icu_training_load 등) → 동일 테이블 내 서비스 컬럼
  - **RunPulse 1차 메트릭**: 서비스 데이터 기반 RunPulse 로직 계산 (TRIMP, FEARP, RelativeEffort, VDOT 등) → `computed_metrics`
  - **RunPulse 2차 메트릭**: 서비스 데이터 + 서비스 1차 + RunPulse 1차 + 외부 소스 조합 복합 지수 (UTRS, CIRS, RTTI, WLEI, TPDI 등) → `computed_metrics`
- **이유**: 저장 분리로 RunPulse 계산 결과를 서비스 값과 명확히 구분. 입력은 가용한 최선의 데이터를 사용하되(예: Garmin 날씨가 있으면 Open-Meteo보다 정확), 결과는 항상 `computed_metrics`에 저장
- **결과**:
  - FEARP 날씨: Garmin 동기화 날씨(activity_detail_metrics.weather_*) 우선, 없으면 Open-Meteo fallback
  - WLEI: Garmin 날씨 + TRIMP(RunPulse 1차) 조합 사용
  - TPDI: Strava/Garmin trainer 컬럼(서비스 데이터) + FEARP(RunPulse 1차) 조합
  - UI에서 RunPulse 메트릭(`computed_metrics`)을 primary, 서비스 1차 메트릭을 secondary subtab으로 표시

## D-V2-17: Settings Platform Roadmap
- **결정**: 설정 페이지 진화 로드맵을 3단계로 설정
  - v0.2: 4소스 연결 상태 확인 + API 키/토큰 설정 (현재)
  - v0.3: 인증/로그인, PWA 설정, REST API 키 관리, 알림 설정, 데이터 백업/복원
  - v0.4: 멀티유저 프로필 관리, 모바일 앱 연동 설정, ML 모델 파라미터 튜닝
- **이유**: 설정 페이지가 버전별로 확장되므로 로드맵을 미리 문서화하여 UI/DB 설계 시 확장성 고려
- **결과**: `views_settings.py` 확장 시 이 로드맵 참조, v0.3 인증 시스템과 자연스럽게 통합

## D-V2-18: Training Plan UI를 loaders/cards 패턴으로 분리
- **결정**: `views_training.py`를 3파일로 분리 (메인 100줄 + cards 300줄 + loaders 100줄)
- **이유**: 다른 재설계 뷰(Dashboard, Race, AI Coach)와 동일한 3-tier 패턴 유지. 300줄 규칙 준수
- **결과**: 로더는 `views_training_loaders.py`, 렌더러는 `views_training_cards.py`로 분리

## D-V2-19: Training 캘린더를 7열 그리드 + week_offset 파라미터로 구현
- **결정**: 리스트형 → 7열 CSS Grid + `?week=` 쿼리 파라미터로 이전/다음 주 이동
- **이유**: 프로토타입(training_plan.html) 디자인 준수. 월/일 뷰는 v0.3으로 이연 (서버 사이드 렌더링 한계)
- **결과**: `repeat(7, 1fr)` 그리드, 모바일에서 가로 스크롤 지원

## D-V2-20: AI 훈련 추천은 규칙 기반 (LLM 호출 없이)
- **결정**: UTRS/CIRS 값 기반 if-else 규칙으로 추천 텍스트 생성
- **이유**: Training 페이지 로드마다 LLM API 호출은 지연/비용 부담. AI Coach 탭에서 이미 LLM 기반 브리핑 제공
- **결과**: `render_ai_recommendation()`에서 UTRS ≥70/40/0 기준 3단계 메시지 + CIRS 부상 위험 알림

## D-V2-21: Wizard 렌더러를 라우트 파일과 분리 (views_training_wizard_render.py)
- **결정**: `views_training_wizard.py`(라우트+로직)와 `views_training_wizard_render.py`(HTML 렌더러) 분리
- **이유**: 300줄 규칙. 4단계 Step HTML + JS + 라우트를 한 파일에 넣으면 350+ 줄 초과
- **결과**: 라우트 파일 ~170줄 / 렌더러 파일 ~220줄. 기존 prefs(renderers)↔crud(routes) 패턴과 일관성 유지

## D-V2-22: Wizard step 전환은 `_wizHistory` JS 배열 기반 (서버 왕복 없이 뒤로가기)
- **결정**: 뒤로가기 시 서버에 재요청하지 않고 `_wizHistory.push/pop`으로 innerHTML 복원
- **이유**: 서버 재요청 시 이전 step의 사용자 입력값이 사라짐. JS 메모리 배열이 단순하고 충분
- **결과**: Step 전환 AJAX + `wizardBack()` JS 함수. history 배열은 페이지 reload 시 초기화됨

## D-V2-23: Wizard step3 — DB 없을 때 graceful (analyze_readiness 스킵)
- **결정**: `_handle_step2()`에서 DB 없거나 `analyze_readiness` 실패 시 경고 메시지 포함 fallback dict 반환
- **이유**: 초기 설치 시 DB가 없어도 Wizard를 사용할 수 있어야 함. 오류로 막히면 UX 불량
- **결과**: `readiness = {"status_summary": "...", "warnings": [...]}` fallback → step3 HTML은 항상 반환

## D-V2-15: sync 병렬화는 src/sync/__init__.py에 _sync_source 배치
- **결정**: SOURCES 딕트와 _sync_source 함수를 `src/sync/__init__.py`에 두고, `src/sync.py` CLI는 이를 임포트
- **이유**: Python 패키지 우선 규칙 — `src/sync/`(패키지)가 있으면 `src.sync`는 패키지를 가리킴. CLI 파일(`src/sync.py`)에 둔 함수는 `from src.sync import`로 접근 불가
- **결과**: `from src.sync import _sync_source` 정상 동작, 테스트 가능
