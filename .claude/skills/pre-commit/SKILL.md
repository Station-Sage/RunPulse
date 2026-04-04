---
name: pre-commit
description: >
  커밋 전 전체 검증 체크리스트. 수동으로만 실행 (/pre-commit).
  pytest, check_docs.py, metric_dictionary 동기화, 300줄 초과 파일,
  BACKLOG.md 상태를 순서대로 검증한다.
disable-model-invocation: true
context: fork
agent: general-purpose
---

# Pre-Commit 검증

커밋 전 아래 항목을 순서대로 검증하고 결과를 보고하라.

## 검증 항목

1. pytest 전체 통과 확인
   실행: python -m pytest tests/ --tb=short -q
   기준: 0 failures

2. check_docs.py 통과 확인
   실행: python scripts/check_docs.py
   기준: 0 errors

3. metric_dictionary 동기화 확인
   실행: python scripts/gen_metric_dictionary.py
   확인: git diff v0.3/data/metric_dictionary.md
   기준: diff가 없으면 OK, 있으면 재생성 필요 보고

4. 300줄 초과 파일 확인
   실행: find src tests -name "*.py" -exec wc -l {} + | awk '$1 > 300' | sort -rn
   기준: 목록 출력 (경고)

5. BACKLOG.md NOW 항목 확인
   실행: grep -c "^-" 섹션에서 NOW 항목 수 카운트
   기준: 3개 이하

## 보고 형식

각 항목별로 PASS 또는 FAIL 표시.
FAIL 항목에는 구체적인 수정 필요 사항을 함께 보고.
전체 PASS일 때만 "커밋 가능" 표시.
