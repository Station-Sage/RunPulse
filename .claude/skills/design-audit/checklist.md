# Phase별 검증 체크리스트

## Phase 1: DB 스키마

- [ ] phase-1.md CREATE TABLE 수 == db_setup.py 실제 테이블 수
- [ ] activity_summaries 컬럼 수 일치 (현재 44)
- [ ] CREATE INDEX 수 일치 (현재 20)
- [ ] SCHEMA_VERSION == 10
- [ ] 5개 앱 테이블 DDL이 문서에 포함되어 있는가
- [ ] metric_registry.py의 MetricDef 수가 문서와 일치

## Phase 2: Extractor

- [ ] BaseExtractor의 메서드 수/이름이 phase-2.md와 일치
- [ ] MetricRecord 필드가 문서와 일치
- [ ] get_extractor() 팩토리가 4개 소스 모두 지원
- [ ] activity_types.py의 스포츠 유형 수가 문서와 일치
- [ ] DoD 11개 항목 모두 통과 표시

## Phase 3: Sync

- [ ] SyncResult dataclass 필드가 phase-3.md와 일치
- [ ] RateLimiter 구현이 문서와 일치
- [ ] 플로우 다이어그램에 compute_metrics_after_sync 포함
- [ ] 4개 소스별 sync 모듈 존재

## Phase 4: Metrics Engine

- [ ] CalcContext API 수 == 13 (phase-4.md와 GUIDE.md 일치)
- [ ] ALL_CALCULATORS 수 == 32 (engine.py와 문서 일치)
- [ ] ctx.conn.execute 잔존 == 0 (ADR-009)
- [ ] 모든 calculator에 display_name, description, unit 존재
- [ ] requires/produces 의존성 그래프가 순환 없음
- [ ] metric_dictionary.md가 최신 (gen_metric_dictionary.py 결과와 일치)

## Phase 5-6: UI/AI (Phase 진입 후 추가)

- [ ] phase-5.md의 페이지/컴포넌트 목록 vs 실제 파일
- [ ] phase-6.md의 AI 인터페이스 vs 실제 구현
- [ ] 라우팅 정의와 실제 라우트 일치

## 전체 정합성

- [ ] architecture.md 테이블 수/이름이 db_setup.py와 일치
- [ ] phase_summary.md의 수치가 최신
- [ ] files_index.md의 파일 수/테스트 수가 최신
- [ ] CHANGELOG.md에 최근 변경 반영
- [ ] decisions.md에 모든 ADR 기록
