# BACKLOG.md — RunPulse 작업 추적

## 현재 상태
| 항목 | 값 |
|------|---|
| 현재 버전 | v0.3 진행 중 |
| 개발 브랜치 | `fix/metrics-everythings` |
| DB | SCHEMA_VERSION 3.1 (내부 migration v4) |
| 테스트 | 1122개 통과 (2026-03-29) |
| 기술 스택 | Python 3.11+ / Flask 3.x / SQLite3 / ECharts / Leaflet+OSM / Gemini |

> **운영 규칙**
> - NOW: 최대 3개. 모두 완료 시 NEXT에서 승격.
> - NEXT: 최대 5개. 우선순위 높은 순.
> - BUGS: 사용자 테스트 발견 즉시 기록. 수정 후 DONE으로.
> - DONE: 최근 10건만 유지. 초과 시 오래된 것부터 삭제 (git log에 이력 보존).
> - Claude Code는 BACKLOG.md에 없는 작업을 임의 진행하지 않는다.
> - 긴급 hotfix 1건은 직접 지시 가능. 완료 후 반드시 DONE에 기록.

---

## NOW (진행 중)

- [ ] **REFAC-1**: `views_report_sections.py` (707줄) 분리
  - scope: 섹션별 렌더러를 개별 파일로 분리
  - files: `src/web/views_report_sections.py` → 복수 파일
  - done: 각 파일 300줄 이하 + 기존 테스트 전체 통과 + GUIDE.md 파일맵 갱신

- [ ] **REFAC-2**: `src/training/planner.py` (713줄) 분리
  - scope: 계획 생성 로직과 헬퍼 분리
  - files: `src/training/planner.py` → 복수 파일
  - done: 각 파일 300줄 이하 + 기존 테스트 전체 통과 + GUIDE.md 파일맵 갱신

- [ ] **REFAC-3**: `src/ai/chat_engine.py` (696줄) 분리
  - scope: 의도 감지, 도구 라우팅, SSE 스트림 분리
  - files: `src/ai/chat_engine.py` → 복수 파일
  - done: 각 파일 300줄 이하 + 기존 테스트 전체 통과 + GUIDE.md 파일맵 갱신

---

## NEXT (대기)

- [ ] **REFAC-4**: `helpers.py` (915줄) 분리 검토
  - scope: SVG 헬퍼, ECharts 헬퍼, nav 헬퍼 등 역할별 분리
  - done: 각 파일 300줄 이하 + 기존 테스트 전체 통과

- [ ] **REFAC-5**: `db_setup.py` (968줄) 분리 검토
  - scope: 마이그레이션 로직과 스키마 정의 분리
  - done: 각 파일 300줄 이하 + DB 초기화/마이그레이션 정상 동작

- [ ] **INFRA-1**: 인증/로그인 시스템
  - scope: bcrypt, Flask 세션, 미인증 리다이렉트
  - files: `src/web/auth.py`(신규), `views_settings.py`(수정), `app.py`(수정)
  - done: 테스트 5개+ 작성 + /login 동작 + 기존 테스트 전체 통과

- [ ] **INFRA-2**: REST API (`/api/v1/*`)
  - scope: 활동/메트릭/웰니스 JSON 엔드포인트
  - files: `src/web/api_v1.py`(신규)
  - done: 주요 엔드포인트 테스트 + Swagger/OpenAPI 문서

- [ ] **INFRA-3**: DB 정규화, 멀티유저 강화
  - scope: user 테이블 분리, FK 정리, 멀티유저 쿼리
  - done: 마이그레이션 스크립트 + 기존 테스트 전체 통과

---

## BUGS (사용자 테스트 발견)

(현재 없음)

---

## DONE (최근 완료, 최대 10건)

- [x] **REFAC-D1**: `views_dashboard_cards.py` 880줄 → 5분리 (2026-03-29)
- [x] **REFAC-D2**: `views_settings.py` 1508줄 → 6분리 (2026-03-28)
- [x] **REFAC-D3**: `views_activities.py` 1096줄 → 4분리 (2026-03-28)
- [x] **REFAC-D4**: `chat_context.py` 932줄 → 6분리 (2026-03-28)
- [x] **REFAC-D5**: `views_training_crud.py` 896줄 → 3분리 (2026-03-27)
- [x] **DOC-D1**: v0.3 워크플로 리뉴얼 — 문서 재편 + GUIDE.md + check_docs.py (2026-03-29)
