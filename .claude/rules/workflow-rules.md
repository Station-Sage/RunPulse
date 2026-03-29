# 워크플로 규칙

## 작업 순서
1. `BACKLOG.md`에서 NOW 항목 확인
2. 작업 시작 전 계획(plan)을 제시하고 승인 대기
3. 승인 후 구현
4. 완료 시 아래 "완료 체크리스트" 수행

## 세션 시작 프로토콜
1. `BACKLOG.md` 읽기 (NOW + BUGS만)
2. 작업 대상 폴더의 `GUIDE.md` 읽기
3. 현재 작업 상태 한 줄 요약 출력
4. 다음 작업 제안

## 세션 종료 체크리스트
1. `BACKLOG.md` 해당 항목 상태 업데이트 (`[x]` 또는 진행률 메모)
2. 변경/생성된 파일이 해당 `GUIDE.md`에 반영되었는지 확인
3. `python -m pytest tests/` 전체 통과 확인
4. 신규 설계 결정이 있었으면 `v0.2/.ai/decisions.md`에 기록
5. `python scripts/check_docs.py` 실행 및 불일치 수정

## BACKLOG.md 운영 규칙
- `BACKLOG.md`에 없는 작업은 임의 진행 금지
- 사용자가 구두로 지시한 수정사항 → 먼저 BACKLOG.md BUGS에 기록 후 진행
- NOW 항목 모두 완료 시 → NEXT에서 NOW로 승격 (사용자 확인 후)
- DONE 10건 초과 시 → 오래된 것부터 삭제 (git log에 이력 보존)

## Hotfix 절차
- BACKLOG.md 기록이 어려운 긴급 1건은 직접 지시로 진행 가능
- 단, 완료 후 반드시 BACKLOG.md DONE에 기록할 것

## 금지 사항
- BACKLOG.md에 없는 작업 임의 진행 금지
- config.json 파일 생성 또는 커밋 금지 (config.json.example만 허용)
- running.db 파일 커밋 금지
- data/ 폴더 내 실제 데이터 커밋 금지 (.gitkeep만 허용)
