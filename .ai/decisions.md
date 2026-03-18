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
