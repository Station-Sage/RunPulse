# RunPulse — 통합 러닝 데이터 플랫폼

## 개요
여러 러닝 앱(Garmin, Strava, Intervals.icu, Runalyze)의 데이터를 통합하고,
2차 메트릭을 계산하여 고차원 러닝 분석, AI 코칭, 훈련 프로그램 생성을 제공합니다.

## 핵심 기능
- 4개 소스 데이터 통합 (Garmin, Strava, Intervals.icu, Runalyze)
- 32개 RunPulse 자체 메트릭 (TRIMP, PMC, UTRS, CIRS, FEARP, DARP 등)
- AI 코치 (Gemini/Groq/Claude function calling)
- 논문 기반 훈련 계획 생성 (Daniels VDOT)
- Flask 웹 대시보드 (다크 테마, ECharts/SVG)

## 아키텍처 (v0.3)

    Layer 0: source_payloads ─── raw JSON 보존
    Layer 1: activity_summaries, daily_wellness ─── 핵심 테이블
    Layer 2: metric_store ─── EAV 통합 (소스 + RunPulse, provider로 구분)
    Layer 3: views/loaders ─── 소비자 (Flask 뷰)
    Layer 4: AI/Training ─── AI 코치 + 훈련 엔진

## 프로젝트 구조

    src/
      metrics/     32 calculators + engine (Phase 4)
      sync/        5-Layer sync pipeline (Phase 3)
        extractors/  4소스 JSON 추출기 (Phase 2)
      ai/          AI 코치 엔진
      training/    훈련 계획 생성
      web/         Flask 대시보드
      utils/       metric_registry, metric_priority, daniels_table
      db_setup.py  Schema v10 (12 pipeline tables)
    tests/         755 tests
    v0.3/data/     설계 문서 (phase-1~7, architecture, decisions)

## 빌드/실행

    python3 src/db_setup.py                              # DB 초기화
    python3 -m pytest tests/                              # 전체 테스트
    python3 -m src.metrics.cli status                     # 메트릭 현황
    python3 src/sync_cli.py sync --source garmin --days 7 # 데이터 동기화
    python3 src/web/app.py                                # 웹 서버 시작

## 개발 현황

| Phase | 상태 | 내용 |
|-------|------|------|
| 1 — Schema | 완료 | 12 pipeline tables, metric_store EAV |
| 2 — Extractors | 완료 | 4소스 추출기, 83 tests |
| 3 — Sync | 완료 | 5개 소스 orchestrator, 74 tests |
| 4 — Metrics | 완료 | 32 calculators, 755 tests total |
| 5 — Consumer | 대기 | 뷰 모듈 metric_store 전환 |
| 6 — Full Load | 대기 | 전체 데이터 재로드 |
| 7 — Preview | 대기 | ML 메트릭 |

## 참고 문서
- 설계 문서: v0.3/data/index.md
- 소스 가이드: src/*/GUIDE.md
- 메트릭 공식: v0.2/.ai/metrics.md, metrics_by_claude.md
- 참고 PDF: v0.2/design/ (1차 메트릭, 2차 메트릭, UI 설계)
