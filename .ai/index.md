# .ai/index.md - RunPulse AI 문서 라우터

## 세션 시작 시 필수 읽기
- .ai/todo.md (현재 작업 목록)
- .ai/architecture.md (시스템 구조)

## 참조 문서 (필요할 때 읽기)
- .ai/decisions.md: 설계 결정 이력. 새로운 기술 선택이나 구조 변경 시 참조
- .ai/data-sources.md: 4개 소스 API 상세, 고유 데이터 필드. sync 모듈 작업 시 참조
- .ai/files.md: 소스 파일별 역할 설명. 파일 구조 파악 시 참조
- .ai/roadmap.md: 개발 로드맵. 다음 작업 결정 시 참조
- .ai/changelog.md: 최근 변경 이력 3건만 확인

## 빌드 명령어

    python src/db_setup.py
    python -m pytest tests/
    python src/sync.py --source garmin --days 1
    python src/analyze.py today

## 토큰 절약 규칙
- 한 세션에 2~3개 파일만 읽기
- 이미 읽은 파일 재읽기 금지
- 출력은 코드 diff 위주로 간결하게
