# AGENTS.md - RunPulse

## 프로젝트 개요
- 이름: RunPulse — 개인 러닝 코치 에이전트
- 목적: Garmin, Strava, Intervals.icu, Runalyze 4개 소스의 러닝/건강 데이터를 통합 분석하고, AI 코치가 훈련 계획을 추천하며, 가민 워치에 자동 등록
- 저장소: https://github.com/Station-Sage/RunPulse
- 실행 환경: Android Termux, Python 3.11+, SQLite3, 파일 기반 저장
- 버전/테스트/브랜치 현황: **`BACKLOG.md` 상단** 참조

---

## 기술 스택
- Python 3.11+, SQLite3 (running.db)
- garminconnect[workout] (비공식, Typed Workout 모델 포함)
- httpx (Strava/Intervals/Runalyze API)
- gpxpy, fitparse (GPX/FIT 파싱)
- Flask 3.x (웹 대시보드)
- ECharts (CDN, 차트), SVG (게이지/레이더)
- Leaflet + OSM (지도, 오픈소스)
- Open-Meteo API (날씨, 무료, 키 없음)

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
