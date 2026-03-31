# 코딩 규칙

## Python 스타일
- Python 3.11+ 문법 사용 (match-case, type hints, f-string)
- 함수에 type hint 필수
- docstring: 함수 목적 1줄 + Args/Returns (한국어 허용)
- 변수명/함수명: snake_case 영어
- 클래스명: PascalCase 영어
- 상수: UPPER_SNAKE_CASE
- 한국어 주석 허용, 코드와 변수명은 영어
- 커밋 메시지: conventional commits (feat: fix: docs: refactor: test:)

## 파일 규칙
- 파일당 300줄 이하. 초과 시 분리
- 각 모듈에 __init__.py 유지
- import 순서: 표준 라이브러리 > 서드파티 > 로컬 (빈 줄로 구분)

## DB 규칙
- 모든 DB 접근은 context manager (with문) 사용
- SQL 파라미터는 반드시 ? placeholder 사용 (SQL injection 방지)
- 테이블/컬럼명: snake_case

## 에러 처리
- API 호출 실패 시 재시도 1회 후 로그 남기고 계속 진행 (전체 sync 중단 금지)
- 파일 I/O 에러는 명확한 메시지 출력 후 종료
- AI 응답 파싱 실패 시 항상 graceful fallback (규칙 기반 등)
- 메트릭 데이터 없을 때 에러 대신 "데이터 수집 중" graceful UI

## 테스트
- tests/ 폴더에 test_모듈명.py 형식
- pytest 사용
- 새 함수 작성 시 최소 1개 테스트 동반