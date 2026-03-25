# .ai/index.md - RunPulse AI 문서 라우터

## 세션 시작 시 필수 읽기
- .ai/todo.md (현재 작업 목록 - Phase별 스프린트 단위)
- .ai/architecture.md (시스템 구조 - 분석/AI코치/워크아웃 레이어 포함)

## 참조 문서 (필요할 때 읽기)
- .ai/decisions.md: 설계 결정 이력 D1~D18. 새로운 기술 선택이나 구조 변경 시 참조
- .ai/data-sources.md: 4개 소스 API 상세 + 가민 워크아웃 API + Strava Stream 상세
- .ai/files.md: 소스 파일별 역할 (analysis, ai, workout, web 모듈 포함)
- .ai/roadmap.md: 개발 로드맵 및 스프린트 단위 예상 시간
- .ai/changelog.md: 최근 변경 이력 3건만 확인

## 빌드 명령어

    python src/db_setup.py
    python -m pytest tests/
    python src/sync.py --source garmin --days 1
    python src/analyze.py today
    python src/analyze.py deep --activity-id 123
    python src/analyze.py race

## 토큰 절약 규칙
- 한 세션에 2~3개 파일만 읽기
- 이미 읽은 파일 재읽기 금지
- 출력은 코드 diff 위주로 간결하게
