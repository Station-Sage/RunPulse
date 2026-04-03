# DONE.md — 완료 이력 (최근 10건)

## 2026-04-03 (v0.3 Phase 3)
- **PHASE3-SYNC**: Sync Orchestrator 전체 구현 완료
  - SyncResult, RateLimiter, raw_store, dedup, orchestrator, reprocess, CLI
  - 5개 소스 orchestrator (garmin activity/wellness, strava, intervals, runalyze)
  - Strava extractor start_date_local fallback 버그 수정
  - v0.2 legacy 테스트 52개 삭제, 74개 신규 테스트 추가
  - 전체 600 tests passed, DoD 11/11 충족

## 2026-04-02
- **AI-TOOL-UNIFIED**: 전 provider 공통 tool calling 함수 `call_with_tools` 구현
  - Gemini/Groq/OpenAI: OpenAI 호환 엔드포인트 통합
  - Claude: Messages API 별도 분기
  - 기존 `call_gemini_with_tools` 제거
- **AI-TOOL-NEW**: `get_activity_detail` (km별 스플릿/HR zone/파워), `get_weather` tool 추가
  - latlng 기반 거리 계산 (두 형식 지원: 분리형/통합형)
  - time 스트림 있으면 정확한 페이스, 없으면 균등 근사
- **AI-CONTEXT-ID**: 컨텍스트에 activity_id 포함 (30일/14일/레이스/유사/lookup 활동)
  - chat_context_rich.py, chat_context_builders.py, chat_context_format.py 수정
- **AI-TOOL-PROMPT**: tool calling 시스템 프롬프트 강화 (구간별/스플릿 요청 시 반드시 tool 호출)
- **AI-PROVIDER-DISPLAY**: 실제 응답한 provider 표시 (chat() → 튜플 반환)
- **FIX-ELEVATION**: elevation_gain_m → elevation_gain 수정 (4파일)
- **FIX-GEMINI-ENDPOINT**: Gemini OpenAI 호환 엔드포인트로 전환

## 2026-04-01
- BUG-GARMIN-AUTH: Garmin 토큰 경로 수정 + 비밀번호 서버 저장 제거 + load_config user_id 전달
- BUG-TEST-PWA: test_pwa.py DB 경로 monkeypatch 수정 (helpers.db_path + views_dashboard.db_path)
- fix: subprocess --user 인자 추가 (sync.py에 user_id 전달)
- fix: 하단탭 UI (overflow-x hidden, nav-items width 100%, body background-color)
- fix: _SYNC_JS IIFE sync 탭에서만 bg-sync 폴링
- fix: views_dashboard → html_page() 통합 (render_template 제거)
- fix: views_sync.py load_config(user_id) 전달
- infra: PYTHONUNBUFFERED=1 docker-compose 추가

## 2026-03-31
- DESIGN-TRAINING: CRS 게이트 제거 + auto_gen 제거 (일일 추천카드에만 CRS 유지)
- BUG-TRAINING-2: Q훈련 미생성/1주일만표시/재생성4주/삭제auto-gen
- INFRA-SEC: 자격증명 암호화 저장
- INFRA-3: CF 헤더 기반 사용자 식별 + secret_key env

## 2026-03-30
- BUG-TRAINING: 페이스/Q-day/recovery/재생성/계획삭제/월간토스트/스와이프 7종
- INFRA-3: CF 헤더 사용자식별 미들웨어 + FLASK_SECRET_KEY
- INFRA-SEC: Fernet 암호화 + garth 격리 + 마이그레이션

## 2026-03-29
- REFAC-1: views_report_sections.py 707줄 분리