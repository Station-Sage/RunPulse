# S1 결과 (2026-10-13) — `crs.evaluate()` 복원 (ADJ-22)

커밋 `20acc7e`(브랜치 `ccr-8ec9b1bc-q2i3u3`). 롤백 = 해당 커밋 revert. 미확인은 '미확인'으로 표시.

## 1. 구현된 계약

- `src/metrics/crs.py: evaluate(conn, target_date) -> dict | None` — 읽기 전용, `target_date` 필수.
- 그 날짜의 daily CRS 대표 행(`is_primary=1`)만 읽는다. 이전 날짜 행으로 대체하지 않는다(ADJ-24).
- `None` = 행 없음 / JSON 손상 / JSON이 dict 아님 / `level`이 int 0~4가 아님(bool 제외).
- DB 오류(테이블 없음 등)는 잡지 않고 전파한다(ADJ-25). 호출부의 `except Exception`은 제거했다.
- Calculator 클래스·version 불변 → `algo_changelog`·`gen_metric_dictionary` 대상 아님.

## 2. 사용자에게 보이는 변화

- 재계획 결과(`replan_remaining_week`)에 `현재 CRS 레벨 {휴식|이지런만} — 남은 고강도 훈련을 이지런으로 전환하는 것을 고려하세요.` 경고가 나올 수 있다(level ≤ 1, 그날 CRS 행이 있을 때만).
- 이후 새로 만들어지는 `session_outcomes.crs_at_session`이 채워진다(매칭 완료·건너뜀 모두).

## 3. 위험·한계 (알려진 것)

| # | 내용 | 근거 | 처리 |
|---|---|---|---|
| R1 | **기존 `session_outcomes` 행은 채워지지 않는다.** 건너뜀·매칭의 `ON CONFLICT DO UPDATE`가 `crs_at_session`을 갱신하지 않아 과거 행은 NULL 유지. 백필이 필요하면 별도 작업 | `matcher.py` upsert 절 | 미결정 — 필요 시 사용자 확인 |
| R2 | **그날 CRS가 아직 계산 전이면 경고·스냅샷이 비어 있다.** 정확한 날짜만 읽기 때문(ADJ-24의 대가). 재계획은 '오늘' CRS를 쓰므로 당일 동기화·계산 전에는 경고가 나오지 않는다 | `evaluate` 계약 | 수용. FRS(S4)의 `crs_missing` 표시와 함께 다룸 |
| R3 | **DB 오류가 더는 삼켜지지 않는다.** `views_training_crud` 건너뜀 라우트(`/training/workout/<id>/skip`)는 전체를 `except Exception: pass`로 감싸 오류가 조용히 사라진다(건너뜀 UPDATE는 먼저 commit됨). `/training/replan`은 "재조정 실패" 메시지로 보인다. matcher 호출부는 `app.py`·`bg_sync.py`에서 로깅 후 계속 | `views_training_crud.py:225-262` | 수용(v1 라우트, V1-13). 인접 tsb·acwr 쿼리도 이미 보호 없이 같은 방식 |
| R4 | **입력이 전부 None이어도 CRS 행(기본 60)이 만들어진다.** 따라서 '데이터 없음'인 날도 level 3 행이 있어 경고·스냅샷이 "정상값"처럼 채워질 수 있다 | `data-freshness.md` §8, `crs.py` `_compute_crs_score` | 건드리지 않음. FRS(S4)의 confidence·`gate_unknown` 설계 범위 |
| R5 | `replanner`의 `today`는 `date.today()`(서버 로컬). TZ-1 '오늘'(최근 활동 시간대)과 다를 수 있다 | `replanner.py` | S4(TZ) 구현 시 같은 헬퍼로 교체 |
| R6 | 경고 문구가 level 0(휴식)에서도 "이지런으로 전환" 문장이라 어색하다 | `replanner.py` | TXT-1 미확정(아래 4) |

## 4. 미결정 사항

1. **TXT-1**: 위 경고 문구 확정(특히 level 0 문장). 현재는 기존 문구 유지. → `decisions-table.md` TXT-1 행에 추가.
2. **FRS-28(신규, 미결정)**: tsb·acwr 스냅샷의 날짜 규칙. 지금은 `scope_id<=날짜` 최신 행(기간 제한 없음)이라 `evaluate`(정확 날짜)와 규칙이 다르다. → 결정표에 등록.
3. R1 백필 여부(위).

## 5. 다음에 다른 작업과 함께 처리할 것

| 작업 | 단계 | 내용 |
|---|---|---|
| FRS-12·15~18 BOOST 보류 | S4 | `evaluate()`(또는 `crs_boost_hold`)를 신선도와 연결. 삭제된 BACKLOG 항목이 "FRS와 함께 구현"이라 한 범위. `adjustment-signals.md` §4·§5의 이후 단계가 이 위에서 시작 |
| tsb·acwr 스냅샷 날짜 규칙 (FRS-28) | S4 | 위 4-2 |
| `metrics_browser_service._crs_level` | S4 | 같은 조건(daily·`is_primary=1`·정확 날짜)으로 CRS를 따로 읽는다. `evaluate()`로 통합 가능한지 FRS에서 판단. S1에서는 변경하지 않음 |
| `replanner` '오늘' | S4 (TZ) | R5 |
| `crs.py` Calculator 정리 | FRS crs 1.1 | `compute` 안의 거짓 주석 "NOTE: raw SQL 사용"·미사용 변수 `since`(`data-freshness.md` §8). 동작 무관, version을 올리는 1.1 변경 때 함께 |
| `test_plan_creation` 실패 | 미배정 | 기준선(S1 이전)부터 `assert 9 == 10`로 실패. S1과 무관. 원인 미확인(`date.today()` 의존 의심) → BACKLOG BUGS 등록 |

## 6. 검증 (S1 커밋 기준)

- 환경: 시스템 `python3` 3.13, 프로젝트 `.venv`(gitignore, `requirements.txt`+pytest). 지정 venv(`/home/ubuntu/.venvs/runpulse`)는 이 샌드박스에 없음. 샌드박스 SQLite 3.46.1.
- 전체 pytest: 기준선 `1 failed, 2798 passed, 247 skipped` → 변경 후 `1 failed, 2829 passed, 247 skipped`(실패 1건은 위 `test_plan_creation`, 기준선과 동일).
- `check_docs.py`: 오류 0 / 경고 63(기준선 동일).
- 프런트 검사·실제 브라우저·운영 DB 확인: 해당 없음 또는 미수행.
