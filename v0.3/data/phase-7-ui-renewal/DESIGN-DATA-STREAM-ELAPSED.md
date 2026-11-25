# DESIGN-DATA-STREAM-ELAPSED — 스트림 elapsed_sec 샘플 인덱스 저장 문제: 현황 대조와 남은 작업

> 상태: **설계 초안 · 사용자 결정 1건 대기** (2026-11-25). 코드 변경 없음. 구현 단위는 `[P7-DATA-STREAM-ELAPSED-IMPL]`.
> 확정 결정(00의 분기점 A~D, 01의 8원칙)은 바꾸지 않는다. P1 Evidence-First(저장값을 그대로 믿지 않고 출처 표시)와 정합.

## 1. 핵심 발견 — 추출기 수정은 이미 들어가 있다
BACKLOG 원문(2026-09-24 식별)은 `garmin_extractor.extract_activity_streams`가 `… else i`(샘플 인덱스)를 쓴다고 적었다. 현재 브랜치 코드는 다르다.

| 항목 | 현재 코드 (확인함) |
|------|------|
| 시간축 결정 | `src/sync/extractors/stream_time.py` `resolve_time_axis` — `sumElapsedDuration` → `directElapsedDuration`(measured) → `directTimestamp` 차이/1000(derived) → 없으면 `scaled` |
| 인덱스 폴백 | 제거됨. `garmin_extractor.py`에 `else i` 없음(grep 확인). 시간키가 없으면 `elapsed_sec=None` |
| 품질 가드 | 결측 5% 초과 또는 비단조면 measured→derived, derived→scaled로 강등(정렬해서 덮지 않음) |
| scaled 환산 | `stream_meta_store.store_streams` — summary 시간(`elapsed_time_sec`→`duration_sec`→`moving_time_sec`)으로 0..total 비례. summary 시간도 없으면 저장 생략 + 경고 |
| 출처 기록 | `activity_stream_meta`(v30): `time_basis`·`time_key`·`sample_count`·`stored_count`·`span_sec`·`median_dt_sec` |
| 동일 초 충돌 | `sample_idx`로 구분(유실 방지), `stored_count`에 반영 |
| 재처리 도구 | `src/sync/reextract.py`(활동 id 유지, payload→`save_streams`, activity+source 단위 DELETE+INSERT), `scripts/backfill_stream_meta.py`(`src/sync/stream_meta_backfill.py`) |
| 테스트 | `tests/test_stream_time.py`, `test_stream_meta_store.py`, `test_stream_meta_backfill.py`, `test_reextract.py` (이 세션에서 실행은 하지 않음) |
| 이력 | 커밋 `365d8512`(U18a-d), 백필은 U18e |

따라서 BACKLOG가 말한 "추출기 수정 + 재처리 도구"는 **코드 측면에서 기구현**이다. 남은 것은 (a) 실데이터 반영 여부, (b) 소수의 보강 후보다.

## 2. Strava 영향 확인
`strava_extractor.py`는 `time` 스트림 값을 그대로 `elapsed_sec`에 쓴다 → 인덱스 오염 없음(코드로 확인). 다만 `StreamRows.meta`를 채우지 않아 신규 sync는 meta 없이 저장되고, `backfill_stream_meta`가 `measured`/`time_key="time"`으로 사후 기록한다(strava 한정, 그 외 소스는 `unknown`). 영향 없음.

## 3. 확인되지 않은 것 (TODO: 확인 필요)
- 운영 DB에 옛 인덱스형 행이 지금도 남아 있는지 — 이 세션은 DB를 열 수 없다(범위 밖). 확인 질의안(조인 키·컬럼명은 스키마 대조 후 확정):
  `SELECT s.activity_id, MAX(s.elapsed_sec), a.duration_sec FROM activity_streams s JOIN activity_summaries a ON a.id = s.activity_id WHERE s.source='garmin' GROUP BY s.activity_id HAVING MAX(s.elapsed_sec) < 0.9 * a.duration_sec`.
  `activity_stream_meta` 행이 없는 활동 = 아직 재추출되지 않은 활동이다.
- 활동 15302(실제 8357초, 1692점)가 재추출 후 `span_sec≈8357`인지.
- `source_payloads`에 `activity_streams` payload가 없는 Garmin 활동 수 — `reextract`는 이들을 `missing_payload`로 건너뛰고 옛 행을 그대로 둔다.

## 4. 남은 작업 후보 (IMPL 범위)
1. **재처리 실행 절차 문서화**: 사본 DB에 `reextract --dry-run` → 실행 → 15302 등 검증 → (사용자 지시 시) 운영 반영. 신규 코드 없이 절차 + 검증 질의만으로 충분할 수 있다.
2. **payload 없는 활동의 잔존 오염 행**: 재추출 불가. (a) 방치(UI 방어 `streamSeconds`가 90% 미만이면 재환산 — DECISIONS P7-IMPL-STREAMS-TRUTH), (b) summary 시간 비례로 DB 내 사후 환산(근사치, 저장값 변조).
3. UI 교정(`streamSeconds`)은 데이터 정정 뒤에도 무해하므로 **제거하지 않는다**.

## 5. 위험·불변식
- 재처리는 활동 id를 바꾸면 안 된다 → `reprocess_all(clear_first=True)` 금지, `reextract`만 사용(참조 테이블 파손·payload 없는 활동 삭제 위험, `reprocess.py` 가드).
- 스트림 행이 교체되므로 스트림 기반 파생 메트릭은 재계산이 필요할 수 있다. TODO: 확인 필요(재계산 트리거 범위).
- 실데이터 갱신은 되돌리기 어렵다 → DB 사본에서 `--dry-run`·검증을 먼저 하고 백업 후 반영.

## 6. 결정 필요
DECISIONS.md `[P7-DATA-STREAM-ELAPSED]`: 운영 실데이터 재추출을 IMPL 범위에 포함할지, payload 없는 활동을 어떻게 다룰지.

## 7. IMPL 완료 기준 (결정 후)
- 3절 질의로 "옛 인덱스형 행 0건 또는 잔존 사유 명시".
- `.venv/bin/python -m pytest tests/test_garmin_extractor.py tests/test_stream_time.py tests/test_stream_meta_backfill.py -q` 통과.
