# v0.3 문서 인덱스 — RunPulse Data Architecture

## 세션 시작 시 필수 읽기
1. **이 파일** (index.md) — 문서 구조 파악
2. **phase_summary.md** — 전체 Phase 상태, 진행률, 테스트 현황
3. 작업 대상 Phase의 설계 문서 (phase-1~7.md)

## 문서 맵

### 설계 문서 (v0.3/data/)
| 파일 | 내용 | 줄수 |
|------|------|------|
| phase_summary.md | 전체 Phase 상태 요약, 산출물 목록 | 683 |
| architecture.md | 5-Layer 아키텍처, 테이블 설계, EAV vs Wide Table | 1307 |
| decisions.md | ADR-001~008 설계 결정 기록 | 50+ |
| CHANGELOG.md | Phase별 변경 이력 | 170+ |
| phase-1.md | Schema v10 — 12 pipeline tables, metric_store EAV | 1111 |
| phase-2.md | Extractors — JSON to MetricRecord, 4소스 추출기 | 1857 |
| phase-3.md | Sync Orchestrators — 5-Layer 파이프라인 | 2242 |
| phase-4.md | Metrics Engine — 32 calculators, topological sort | 3500+ |
| phase-5.md | Consumer Migration — 뷰 모듈 metric_store 전환 (미구현) | 1577 |
| phase-6.md | Full Data Load — 전체 데이터 재로드 (미구현) | 339 |
| phase-7(preview).md | Preview — ML 메트릭, A/B 테스트 (미구현) | 572 |

### 소스 코드 가이드 (GUIDE.md)
| 파일 | 내용 |
|------|------|
| src/metrics/GUIDE.md | 32 calculators, 의존성 그래프, 추가 체크리스트 |
| src/sync/GUIDE.md | 5-Layer sync 파이프라인, rate limit, reprocess |
| src/ai/GUIDE.md | AI 코치 엔진, provider chain, function calling |
| src/training/GUIDE.md | 훈련 엔진, Daniels VDOT, CRS gate |
| src/web/GUIDE.md | Flask 대시보드, 3-tier 패턴, 7+1 탭 |

### 메트릭 참조 문서 (v0.2/.ai/)
| 파일 | 내용 |
|------|------|
| metrics.md | PDF 원본 기반 1차/2차 메트릭 공식 |
| metrics_by_claude.md | Claude 추정 공식 (UTRS, CIRS, FEARP 등) |

## 현재 상태 (2026-04-03)

| Phase | 상태 | 테스트 | 핵심 산출물 |
|-------|------|--------|-------------|
| 1 — Schema | 완료 | 64 | 12 pipeline tables, metric_store |
| 2 — Extractors | 완료 | 83 | 4소스 추출기, MetricRecord |
| 3 — Sync | 완료 | 74 | 5개 소스 orchestrator, dedup |
| 4 — Metrics | 완료 | 755 | 32 calculators, engine, CLI |
| 5 — Consumer | 대기 | — | 뷰 모듈 전환 |
| 6 — Full Load | 대기 | — | 전체 데이터 재로드 |
| 7 — Preview | 대기 | — | ML 메트릭 |

## 핵심 아키텍처

    Layer 0: source_payloads (raw JSON)
    Layer 1: activity_summaries, daily_wellness, daily_fitness
    Layer 2: metric_store (EAV — 소스 + RunPulse 공존, provider로 구분)
    Layer 3: views/loaders (Phase 5)
    Layer 4: AI/Training engine

## 빌드/테스트 명령어

    python3 src/db_setup.py                              # DB 초기화
    python3 -m pytest tests/                              # 전체 테스트 (755)
    python3 -m src.metrics.cli status                     # 메트릭 현황
    python3 -m src.metrics.cli recompute --days 7         # 최근 7일 재계산
    python3 src/sync_cli.py sync --source garmin --days 7 # Garmin sync
    python3 src/sync_cli.py reprocess --source garmin     # raw to Layer 1/2 재구축

## 토큰 절약 규칙
- 세션당 2~3개 문서만 읽기
- phase_summary.md로 전체 파악 후 필요한 phase-N.md만 열기
- GUIDE.md로 소스 구조 파악 후 실제 코드 읽기
