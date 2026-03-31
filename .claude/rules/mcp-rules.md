# MCP 활용 규칙

## sequential-thinking (복잡한 작업 시)
- BACKLOG.md의 NOW 항목 작업 시작 전에 반드시 sequential-thinking으로 작업을 분해할 것
- 3개 이상의 파일을 수정하는 작업은 반드시 sequential-thinking 사용

## context7
- 외부 라이브러리 API 사용 시 최신 문서 확인
- Flask, ECharts, Chart.js, pytest 관련 코드 작성 시 문서 참조 필수

## sqlite
- DB 스키마 변경 전후로 sqlite MCP로 테이블 구조 확인
- 새 메트릭 구현 시 computed_metrics 테이블 데이터 검증

## github
- 세션 종료 시 최근 커밋과 BACKLOG.md 대비 누락 체크

## pytest
- 코드 수정 완료 후 관련 테스트 실행 및 결과 확인

## fetch
- 외부 API(Open-Meteo, Garmin, Strava) 연동 시 응답 구조 확인
