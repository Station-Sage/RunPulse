# 코딩 규칙

## 파일
- 300줄 이하. 초과 시 분리

## 에러 처리
- API 호출 실패: 재시도 1회 → 로그 → 계속 진행 (sync 중단 금지)
- AI 응답 파싱 실패: graceful fallback (규칙 기반)
- 메트릭 데이터 없음: 에러 대신 "데이터 수집 중" UI

## 메트릭
- Calculator 내부에서 raw SQL 금지 (CalcContext API만 사용, ADR-009)
- 데이터 부족 시 빈 리스트 반환 (에러 raise 금지)

## 테스트
- 새 함수 작성 시 최소 1개 테스트 동반

## 커밋
- conventional commits (feat: fix: docs: refactor: test:)
- 한국어 주석 허용, 코드와 변수명은 영어
