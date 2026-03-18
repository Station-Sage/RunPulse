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
