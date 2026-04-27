# BACKLOG

## NOW

## BUGS
- ✅ Garmin 인증 실패: A안 구현 완료 — `scripts/garmin_local_sync.py` + `POST /api/garmin/local-sync` + `/connect/garmin` 2탭 UI + CF Service Token bypass (`auth_cf.py`). 17개 테스트 추가. 설계: ADR-010
- 아래 3개 항목 오류를 보면, db 마이그레이션이 제대로 되지 않은 것으로 판단 됨. 
- 활동 > 활동 심층 분석 탭 : 조회 오류: no such column: calories
- 레포트 > 레이스 예측 탭 : 오류가 발생했습니다: cannot import name 'calc_marathon_shape' from 'src.metrics.marathon_shape' (/app/src/metrics/marathon_shape.py)
- 홈(대시브도) 탭 : OperationalError
sqlite3.OperationalError: no such column: data_json

Traceback (most recent call last)
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 1536, in __call__
return self.wsgi_app(environ, start_response)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 1514, in wsgi_app
response = self.handle_exception(e)
           ^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 1511, in wsgi_app
response = self.full_dispatch_request()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 919, in full_dispatch_request
rv = self.handle_user_exception(e)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 917, in full_dispatch_request
rv = self.dispatch_request()
     ^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 902, in dispatch_request
return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

## 미해결 확인 사항 (MIGRATION-04 §6)
- [높음] garminconnect 0.3.x connectapi 내부 자동 토큰 갱신 여부 — 장시간 배치 안정성
- [중간] curl_cffi ARM64 wheel 존재 여부 (AWS Graviton) — Dockerfile 빌드
- [낮음] test_flask_routes.py garmin 라우트 포함 여부 — 테스트 커버리지
- [낮음] garminconnect 0.3.x get_body_battery_events(cdate) 시그니처 — 현행 코드가 (cdate, cdate) 2인자 호출

## NEXT
- **GARMIN-LOCAL-REUSE**: `garmin_local_sync.py` — tokenstore에 만료되지 않은 OAuth2 토큰(`expires_at > now+300`)이 있으면 로그인 생략하고 바로 VPS 업로드. tokenstore 경로 결정 로직을 `_garmin_login()` → `main()`으로 이동 필요.
- **GARMIN-B**: SSH 역방향 터널 방식 — 로컬 SOCKS5 데몬 + `ssh -R` + `HTTPS_PROXY`. 전체기간 sync, 백그라운드 sync 가능. 상세: `v0.3/data/garmin-ip-block-research.md`
- Phase 7: UI 재설계 (views_activities_table.py → activity_service 전환 포함)

## DONE (recent)
- fix: strava/intervals sync_activities/sync_wellness undefined 버그 수정 (wrapper 추가)
- garminconnect 0.3.x 마이그레이션 (MIGRATION-01~04) — curl_cffi, tokenstore, MFA, 38 new tests
- Phase 6: Initial Data Load & Validation — GarminBulkLoader, DataValidator(12-check), initial-load CLI(9-step), db_status, snapshot.sh
