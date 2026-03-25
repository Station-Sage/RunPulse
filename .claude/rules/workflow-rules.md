# 워크플로 규칙

## 작업 순서
1. v0.2/.ai/todo.md에서 현재 Phase의 미완료 작업 확인
2. 작업 시작 전 계획(plan)을 제시하고 승인 대기
3. 승인 후 구현
4. 구현 완료 시 v0.2/.ai/todo.md에서 해당 항목 체크 표시
5. 주요 변경 시 v0.2/.ai/changelog.md 업데이트
6. 설계 결정 발생 시 v0.2/.ai/decisions.md에 추가

## 세션 시작 프로토콜
1. v0.2/.ai/todo.md 읽기
2. 현재 작업 상태 한 줄 요약 출력
3. 다음 작업 제안

## 세션 종료 프로토콜
1. 완료한 작업 목록 출력
2. v0.2/.ai/todo.md 업데이트
3. v0.2/.ai/changelog.md에 날짜와 변경 내용 추가

## 금지 사항
- v0.2/.ai/todo.md에 없는 작업 임의 진행 금지
- config.json 파일 생성 또는 커밋 금지 (config.json.example만 허용)
- running.db 파일 커밋 금지
- data/ 폴더 내 실제 데이터 커밋 금지 (.gitkeep만 허용)
