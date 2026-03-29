# AGENTS.md - RunPulse

## 프로젝트
RunPulse — Garmin/Strava/Intervals.icu/Runalyze 4개 소스 통합 러닝 코치 에이전트

## 기술 스택
Python 3.11+ / SQLite3 / Flask 3.x / ECharts / Leaflet+OSM / Gemini Function Calling

## 브랜치
- `main`: 안정 릴리스 (보호됨)
- `fix/metrics-everythings`: v0.2 개발
- 작업 브랜치: `chore/*`, `feat/*`, `fix/*`

## 실행
    python src/db_setup.py              # DB 초기화
    python src/serve.py                 # 웹 localhost:18080
    python -m pytest tests/             # 테스트 (1122개)
    python scripts/check_docs.py        # 문서 정합성

## 문서 체계
- **상세 규칙/아키텍처**: `CLAUDE.md` 참조
- **현재 작업**: `BACKLOG.md` 참조
- **폴더별 가이드**: `src/*/GUIDE.md` 참조

## Codex 검수자 규칙
- 코드 수정 금지. 검수 리포트만 생성.
- `BACKLOG.md`의 해당 항목 `done` 조건 기준으로 검수.
- 확인 항목: 기능 누락, 보안 취약점, 테스트 커버리지, GUIDE.md 정합성.
- 검수 결과는 GitHub Issue 또는 PR comment로 보고.
