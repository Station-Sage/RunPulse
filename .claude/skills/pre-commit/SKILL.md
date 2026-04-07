---
name: pre-commit
description: >
  커밋 직전 전체 검증 게이트. pytest 전체 + check_docs.py(18개 검사)
  + check_data_consistency.py(12개 검사) + metric_dictionary 동기화
  + files_index 동기화를 순서대로 검증한다.
  전체 PASS일 때만 커밋 가능.
  "커밋 전 체크", "커밋 가능?", "pre-commit" 요청 시 사용.
disable-model-invocation: true
user-invocable: true
---

# /pre-commit — 커밋 직전 전체 게이트

커밋해도 되는지 전체를 검증한다. (~35초)
/doc-sync의 검사를 모두 포함하며, pytest 전체 실행이 추가된다.

## 검증 항목 (순서대로)

### 1. pytest 전체 통과

    python3 -m pytest tests/ --tb=short -q

기준: 0 failures

### 2. check_docs.py 통과

    python3 scripts/check_docs.py

18개 검사(general, code, metric, schema, phase) 전부 실행.
기준: 0 errors

### 3. check_data_consistency.py 통과

    python3 scripts/check_data_consistency.py

12개 검사(SSOT ↔ DDL ↔ Extractor 교차 검증) 전부 실행.
기준: 🔴 0건 (🟠 경고는 허용, 단 내용 확인 후 커밋)

### 4. metric_dictionary 동기화

    python3 scripts/gen_metric_dictionary.py
    git diff --stat v0.3/data/metric_dictionary.md

기준: diff 없음

### 5. files_index 동기화

    python3 scripts/gen_files_index.py
    git diff --stat v0.3/data/files_index.md

기준: diff 없음

## 결과 보고

    ## /pre-commit 결과
    1. pytest:                    PASS/FAIL (N passed, N failed)
    2. check_docs.py:             PASS/FAIL (검사 18개, errors N, warnings N)
    3. check_data_consistency.py: PASS/FAIL (검사 12개, 🔴 N, 🟠 N)
    4. metric_dictionary:         동기화됨 / 불일치
    5. files_index:               동기화됨 / 불일치
    -> 전체: 커밋 가능 / 커밋 불가 (사유: ...)
