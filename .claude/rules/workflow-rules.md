# 워크플로 규칙

## 작업 순서
1. `BACKLOG.md`에서 NOW 확인
2. 복잡한 작업 시 sequential-thinking MCP로 단계 분해
3. 계획(plan) 제시 → 승인 대기 → 구현
4. 완료 시 "완료 체크리스트" 수행
5. `BACKLOG.md`, 해당 `GUIDE.md`, `requirements.txt` 등 문서 업데이트

## 세션 시작
1. `BACKLOG.md` 읽기 (NOW + BUGS만)
2. 작업 대상 폴더 `GUIDE.md` 읽기
3. 현재 작업 상태 한 줄 요약 → 다음 작업 제안

## 완료 체크리스트
1. `BACKLOG.md` 항목 상태 업데이트
2. 변경/생성 파일이 해당 `GUIDE.md`에 반영되었는지 확인
3. `python -m pytest tests/` 전체 통과
4. 신규 설계 결정 시 `v0.2/.ai/decisions.md` 기록
5. `python scripts/check_docs.py` 실행 및 불일치 수정

## BACKLOG 운영
- NOW 최대 3개, NEXT 최대 5개
- NOW 전부 완료 시 → NEXT에서 승격 (사용자 확인 후)
- BUGS: 수정 완료 시 `DONE.md`로 이동. **(판단 필요)** 태그 항목은 사용자 지시 없이 진행 금지
- DONE.md: 10건 초과 시 오래된 것부터 삭제 (git log에 이력 보존)
- 사용자가 미룬 항목 → `LATER.md` 기록. Claude가 자발적으로 읽지 않음
- `LATER.md` → BACKLOG 승격은 사용자 지시로만
- Hotfix: 긴급 1건은 직접 지시로 진행 가능. 완료 후 DONE.md 기록

## 금지
- BACKLOG.md에 없는 작업 임의 진행
- config.json 생성/커밋 (config.json.example만 허용)
- .mcp.json, running.db, data/ 내 실제 데이터 커밋