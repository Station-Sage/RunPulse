# RunPulse - 변경 이력

## 2026-03-18
- 프로젝트 초기 설정
- CLAUDE.md, AGENTS.md 생성
- .ai 문서 세트 생성 (index, todo, architecture, decisions, data-sources, files, roadmap)
- 디렉터리 구조 생성
- Phase 1 기반 구축 완료
  - requirements.txt 생성
  - db_setup.py: SQLite 스키마 5개 테이블 (activities, source_metrics, daily_wellness, planned_workouts, goals)
  - src/utils/config.py: 설정 파일 로드 유틸리티
  - src/utils/pace.py: 페이스 변환 (초↔분:초, km/h↔sec/km)
  - src/utils/zones.py: HR존/페이스존 계산 (5존)
  - src/utils/dedup.py: 중복 활동 매칭 (±5분, ±3%)
  - src/utils/clipboard.py: termux-clipboard-set 래퍼
  - tests/ 45개 테스트 (db_setup, pace, zones, dedup)
- Phase 2 데이터 수집 완료
  - src/utils/api.py: httpx 기반 GET/POST 래퍼 (1회 재시도)
  - src/sync/garmin.py: Garmin Connect 활동/웰니스 동기화
  - src/sync/strava.py: Strava OAuth2 토큰 갱신, 활동/스트림 동기화
  - src/sync/intervals.py: Intervals.icu Basic Auth 활동/웰니스(CTL/ATL) 동기화
  - src/sync/runalyze.py: Runalyze API Token 활동/VO2Max 동기화
  - src/sync.py: CLI 진입점 (--source all --days 7)
  - src/import_history.py: GPX/FIT 파일 일괄 임포트
  - tests/ 68개 테스트 전체 통과 (api, sync 4개, import, 통합 dedup)

## 2026-03-19
- Phase 3 분석 모듈 확장 설계
  - 기존 3개(compare, trends, report) → 10개 모듈로 확장
  - 신규: efficiency.py (EF/Decoupling), zones_analysis.py (80/20),
    activity_deep.py (단일활동 심층), race_readiness.py (레이스 준비도),
    recovery.py (Garmin 웰니스 기반), weekly_score.py (종합 점수)
- AI 코치 브리핑 시스템 설계
  - briefing.py: 탭 진입 시 자동 데이터 수집 + 프롬프트 조립
  - 오늘 활동 유무에 따른 분기 프롬프트
- 추천 칩(Suggestion Chips) 시스템 설계
  - suggestions.py: 규칙 기반(즉시) + AI 동적(응답 후) 하이브리드
  - RunnerState 기반 우선순위 정렬 로직
  - 칩 클릭 시 해당 프롬프트 템플릿 + 데이터 자동 조립
- Phase 4-1/4-2 분리 확정, Phase 5 AI 코치 탭 상세화
- 설계 결정 D11~D18 추가
- .ai 문서 전체 업데이트 (todo, architecture, files, roadmap, decisions, data-sources, changelog)
