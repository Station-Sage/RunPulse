---
name: doc-sync
description: >
  문서 정합성 검증. check_docs.py, gen_metric_dictionary.py, test_doc_sync.py를
  실행하고 결과를 요약한다. "문서 검증", "커밋 전 체크", "dictionary 재생성",
  "문서 동기화" 요청 시 사용.
user-invocable: true
argument-hint: "[--fix]"
---

# /doc-sync — 문서 정합성 검증

## 실행 절차

### Step 1: check_docs.py 실행
```bash
python scripts/check_docs.py
```
결과에서 `[ERROR]`와 `[WARN]` 항목을 확인하라.
Errors가 0이면 PASS, 1개 이상이면 FAIL.

### Step 2: metric_dictionary 동기화 확인
```bash
python scripts/gen_metric_dictionary.py
git diff --stat v0.3/data/metric_dictionary.md
```
diff가 있으면 dictionary가 코드와 불일치한 것이다.
`$ARGUMENTS`에 `--fix`가 포함되어 있으면 변경을 유지하고,
아니면 `git checkout v0.3/data/metric_dictionary.md`로 되돌려라.

### Step 3: test_doc_sync 실행
```bash
python -m pytest tests/test_doc_sync.py -v --tb=short
```
전체 통과 여부를 확인하라.

## 결과 보고 형식

```
## doc-sync 결과
- check_docs.py: PASS/FAIL (통과 N/9, errors N, warnings N)
- metric_dictionary: 동기화됨 / 불일치 (변경 파일 N개)
- test_doc_sync: PASS/FAIL (통과 N/6)
- 수정 필요 항목: (있으면 번호 매긴 목록)
```
