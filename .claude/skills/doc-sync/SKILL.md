---
name: doc-sync
description: >
  문서 정합성 빠른 확인. 코딩 중 수시로 실행하는 가벼운 검증.
  check_docs.py + metric_dictionary 동기화 + test_doc_sync만 실행한다.
  pytest 전체 실행은 포함하지 않는다.
  "문서 검증", "dictionary 확인", "문서 동기화" 요청 시 사용.
user-invocable: true
argument-hint: "[--fix]"
---

# /doc-sync — 문서 정합성 빠른 확인

코딩 중 문서가 코드와 맞는지 빠르게 확인한다. (~5초)
pytest는 실행하지 않는다. 커밋 전 전체 검증은 `/pre-commit`을 사용하라.

## 실행 절차

### Step 1: check_docs.py

    python scripts/check_docs.py

`[ERROR]` 0개이면 PASS, 1개 이상이면 FAIL.
`[WARN]`은 참고용으로 보고만 한다.

### Step 2: metric_dictionary 동기화

    python scripts/gen_metric_dictionary.py
    git diff --stat v0.3/data/metric_dictionary.md

diff가 없으면 동기화됨.
diff가 있고 `$ARGUMENTS`에 `--fix`가 있으면 변경을 유지하고,
없으면 `git checkout v0.3/data/metric_dictionary.md`로 되돌려라.

### Step 3: test_doc_sync

    python -m pytest tests/test_doc_sync.py -v --tb=short

## 결과 보고

    ## /doc-sync 결과
    - check_docs.py: PASS/FAIL (errors N, warnings N)
    - metric_dictionary: 동기화됨 / 불일치
    - test_doc_sync: PASS/FAIL (통과 N/6)
