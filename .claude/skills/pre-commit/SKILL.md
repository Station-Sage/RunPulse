---
name: pre-commit
description: >
  커밋 직전 전체 검증 게이트. pytest 전체 + 문서 정합성 + 코드 규칙을
  순서대로 검증한다. 전체 PASS일 때만 커밋 가능.
  "커밋 전 체크", "커밋 가능?", "pre-commit" 요청 시 사용.
disable-model-invocation: true
user-invocable: true
---

# /pre-commit — 커밋 직전 전체 게이트

커밋해도 되는지 전체를 검증한다. (~35초)
/doc-sync의 검사를 모두 포함하며, pytest 전체 실행 + 코드 규칙 검사가 추가된다.

## 검증 항목 (순서대로)

### 1. pytest 전체 통과

    python -m pytest tests/ --tb=short -q

기준: 0 failures

### 2. check_docs.py 통과

    python scripts/check_docs.py

기준: 0 errors

### 3. metric_dictionary 동기화

    python scripts/gen_metric_dictionary.py
    git diff --stat v0.3/data/metric_dictionary.md

기준: diff 없음

### 4. 300줄 초과 파일 확인

    find src tests -name "*.py" -exec wc -l {} + | awk '$1 > 300' | sort -rn

기준: 목록 출력 (경고, 블로커 아님)

### 5. BACKLOG.md NOW 항목 수

    sed -n '/^## NOW/,/^## /p' BACKLOG.md | grep -c "^-"

기준: 3개 이하

## 결과 보고

    ## /pre-commit 결과
    1. pytest:            PASS/FAIL (N passed, N failed)
    2. check_docs.py:     PASS/FAIL (errors N, warnings N)
    3. metric_dictionary: 동기화됨 / 불일치
    4. 300줄 초과 파일:    N개 (경고)
    5. BACKLOG NOW:       N개 (3개 이하 OK)
    -> 전체: 커밋 가능 / 커밋 불가 (사유: ...)
