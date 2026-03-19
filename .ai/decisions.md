# RunPulse - 설계 결정 기록 (ADR)

## D1: SQLite 단일 파일 DB 사용 (2026-03-18)
- 결정: PostgreSQL 대신 SQLite 사용
- 이유: Termux에서 추가 설치 불필요, 단일 파일로 백업 간편, 개인용이므로 동시성 불필요
- 절충: 고급 JSON 쿼리나 전문 검색은 제한됨

## D2: 4개 소스 전부 활용 (2026-03-18)
- 결정: Garmin, Strava, Intervals.icu, Runalyze 모두 데이터 수집
- 이유: 동일 활동이지만 각 플랫폼이 생산하는 2차 데이터(지표)가 서로 다름
- Garmin은 Training Effect/Body Battery, Strava는 Suffer Score/Stream,
  Intervals는 CTL/ATL/TSB, Runalyze는 Effective VO2Max/Race Prediction 제공

## D3: Python에서 계산, Genspark에서 해석 (2026-03-18)
- 결정: 숫자 통계와 비교는 Python 코드로 수행하고, 해석과 훈련 조언은 Genspark에 마크다운으로 전달
- 이유: LLM API 비용 없이 무료 Genspark Chat 활용, 정확한 수치는 코드가 담당

## D4: 클립보드 기반 AI 연동 (2026-03-18)
- 결정: API 직접 호출 대신 termux-clipboard-set으로 리포트를 복사하고 Genspark에 수동 붙여넣기
- 이유: Genspark은 API를 제공하지 않음. 클립보드 방식이 무료이며 어떤 AI Chat에도 사용 가능

## D5: CLI 우선, 웹은 선택 (2026-03-18)
- 결정: 모든 기능을 CLI로 먼저 구현하고, 웹 대시보드는 Phase 5에서 선택적으로 추가
- 이유: Termux 터미널에서 바로 실행 가능하고, 웹 없이도 핵심 기능 완전히 동작

## D6: 중복 매칭 허용 오차 (2026-03-18)
- 결정: timestamp 5분, distance 3퍼센트
- 이유: GPS 기록 시작/종료 시점 차이와 거리 계산 알고리즘 차이를 수용

## D7: config.json으로 인증 관리 (2026-03-18)
- 결정: 환경 변수 대신 config.json 파일 사용
- 이유: Termux에서 환경 변수 설정이 번거로움. JSON 파일이 직관적이고 편집 용이
- 주의: .gitignore에 반드시 포함

## D8: 비공식 garminconnect 라이브러리 사용 (2026-03-18)
- 결정: 공식 Garmin Connect Developer API 대신 python-garminconnect 사용
- 이유: 공식 API는 기업용 승인 필요. 비공식 라이브러리는 개인용으로 즉시 사용 가능
- 위험: Garmin 정책 변경 시 차단 가능성. 요청 빈도를 최소화하여 대응

## D9: Strava Stream은 JSON 파일로 저장 (2026-03-18)
- 결정: 1초 단위 스트림 데이터는 DB 대신 data/sources/strava/ 에 JSON 파일로 저장
- 이유: 스트림 데이터 용량이 크고 구조가 가변적. 파일로 저장 시 DB 부담 감소

## D10: 리포트 내 소스별 섹션 분리 (2026-03-18)
- 결정: 분석 리포트에서 공통 지표와 각 소스 고유 지표를 분리하여 표시
- 이유: 4개 소스를 활용하는 핵심 목적이 서로 다른 2차 데이터 비교에 있음

## D11: AI 코치는 외부 AI가 담당, RunPulse는 데이터/파싱/실행 (2026-03-19)
- 결정: RunPulse 자체가 훈련 계획을 생성하지 않음. Genspark 등 외부 AI가 생성하고 RunPulse는 데이터 제공, 응답 파싱, 가민 실행을 담당
- 이유: 무료 AI 서비스(Genspark)에 최신 LLM 모델 활용 가능. 프롬프트 엔지니어링으로 품질 확보

## D12: AI 서비스 비종속 설계 (2026-03-19)
- 결정: Genspark 기본이지만 ChatGPT, Claude, DeepSeek 등 교체 가능하게 설계
- 이유: 특정 서비스 종속 위험 회피. 프롬프트 템플릿 + 붙여넣기 방식은 모든 채팅 AI에 범용 적용

## D13: AI 응답 수신은 붙여넣기 입력창 우선 (2026-03-19)
- 결정: 방법 3(붙여넣기 입력창)을 기본으로 하고, 방법 1(iframe DOM 감지)은 Phase 6에서 확장
- 이유: 붙여넣기는 구현이 단순하고 모든 AI 서비스에 범용. DOM 감지는 서비스별 구조가 달라 복잡

## D14: 가민 워크아웃 생성-스케줄-삭제 3단계 전략 (2026-03-19)
- 결정: upload_running_workout → schedule_workout → delete_workout으로 25개 슬롯 제한 우회
- 이유: 캘린더 이벤트는 워크아웃 삭제 후에도 유지됨. 슬롯 점유 없이 무제한 스케줄 가능

## D15: garminconnect[workout] Typed Models 사용 (2026-03-19)
- 결정: pip install garminconnect[workout]으로 RunningWorkout, create_warmup_step 등 Typed 모델 활용
- 이유: 딕셔너리 수동 조립 대신 타입 안전한 워크아웃 구성. 유지보수 용이

## D16: 프롬프트 템플릿은 별도 텍스트 파일로 관리 (2026-03-19)
- 결정: src/ai/prompt_templates/ 디렉터리에 .txt 파일로 프롬프트 관리
- 이유: 코드와 프롬프트 분리. 프롬프트만 수정 시 코드 변경 불필요. 사용자 커스터마이즈 용이

## D17: Phase 3 분석 모듈 6개 확장 (2026-03-19)
- 결정: 기존 compare/trends/report 외에 efficiency, zones_analysis, activity_deep, race_readiness, recovery, weekly_score 추가
- 이유: 4개 소스의 고유 데이터를 최대한 활용하려면 전문 분석 모듈 필요
  - efficiency: Strava Stream 1초 데이터로 EF/Decoupling 계산 (다른 소스에서 불가)
  - zones_analysis: Intervals.icu Zone 분포 활용
  - recovery: Garmin 웰니스 데이터(Body Battery/HRV/Sleep) 전용
  - race_readiness: Runalyze VO2Max/VDOT/Marathon Shape 전용
  - weekly_score: 4개 소스 교차 검증 종합 점수
  - activity_deep: 단일 활동에 4개 소스 평가를 병합

## D18: 추천 칩 하이브리드 방식 (규칙 기반 + AI 동적) (2026-03-19)
- 결정: AI 코치 탭 진입 시 규칙 기반 칩 즉시 표시(지연 0), AI 응답 수신 후 동적 칩으로 교체
- 이유: 즉시 표시로 사용자 대기 없음. AI 칩은 맥락 적응성 높음. 파싱 실패 시 규칙 기반 폴백
- 규칙 기반: RunnerState(오늘 활동 유무, ACWR, TSB, 레이스 D-day 등)에 따라 우선순위 정렬
- AI 동적: 브리핑 프롬프트에 "추천 질문 3개를 JSON으로 포함" 지시, 응답 끝에서 파싱

## D20: daily_fitness 테이블 분리 (2026-03-20)
- 결정: CTL/ATL/TSB, VO2Max 등 일별 피트니스 추적 지표를 source_metrics에서 daily_fitness 전용 테이블로 분리
- 이유: source_metrics는 activity 단위 데이터이지만 CTL/ATL/TSB는 날짜 단위 지표. 분리하면 날짜 기준 조회가 간단해지고 4소스 피트니스 지표를 한 행에 병합 가능
- 영향: intervals.py sync_wellness() 변경, compare.py/trends.py의 조회 소스 변경 (source_metrics 폴백 유지)
- 하위호환: daily_fitness 미존재 환경에서 graceful 처리, source_metrics 폴백으로 기존 데이터 활용 가능

## D19: 서비스 연동 이중 방식 - CLI 직접 입력 + 웹 UI 소셜 로그인 (2026-03-19)
- 결정: CLI 모드에서는 config.json에 키/토큰 직접 입력, Phase 5 웹 UI에서는 WebView/OAuth 팝업으로 구글 등 소셜 로그인 지원
- 이유: HealthSync 앱과 동일한 방식. 각 서비스가 자체 소셜 로그인을 지원하므로, 해당 로그인 페이지를 팝업으로 열어 세션/토큰을 획득
- Garmin: sso.garmin.com 팝업 → 구글 SSO → garth 세션 토큰 캡처
- Strava: OAuth2 플로우 자동화 → 구글 로그인 가능 → 토큰 자동 획득
- Intervals.icu: OAuth2 플로우 또는 설정 페이지 직접 링크
- Runalyze: 로그인 팝업 (구글/페이스북) → API 설정 페이지 안내
- CLI 모드는 즉시 사용 가능, 웹 UI 모드는 Phase 5에서 구현
