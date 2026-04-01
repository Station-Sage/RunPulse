# DONE.md — 완료 이력 (최근 10건)

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