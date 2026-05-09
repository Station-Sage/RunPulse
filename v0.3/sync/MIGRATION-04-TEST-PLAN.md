문서 4 (TEST): 기존 테스트 6개 파일 영향 없음 확인, 신규 테스트 2개 파일 설계, VPS 통합 테스트 체크리스트, 실행 순서 8단계, 롤백 계획, 미해결 5건 정리.
📄 문서 4: MIGRATION-04-TEST-PLAN.md — 테스트 계획 + 마이그레이션 실행 절차
Garmin 마이그레이션 — 테스트 계획 + 실행 절차
작성일: 2026-04-09 | 브랜치: renew/data-architecture
1. 기존 테스트 영향 분석
1.1 garmin 관련 테스트 파일 목록
| 테스트 파일 | 변경 필요 | 이유 ||---|---|---|| test_garmin_activity_sync.py | ❌ 불필요 | MagicMock으로 api 주입, garth 무의존 || test_garmin_wellness_sync.py | ❌ 불필요 | MagicMock으로 api 주입, garth 무의존 || test_garmin_extractor.py | ❌ 불필요 | extractor 로직만 테스트, API 무관 || test_orchestrator.py | ❌ 불필요 | mock api_clients 주입 || test_rate_limiter.py | ❌ 불필요 | 독립적 유닛 테스트 || test_bulk_loader.py | ❌ 불필요 | 파일 파싱 전용, API 무관 || test_flask_routes.py | ⚠️ 확인 필요 | garmin connect 라우트 포함 시 |
1.2 확인 결과: test_garmin_activity_sync.pypythonfrom src.sync.garmin_activity_sync import syncapi = MagicMock()api.get_activities_by_date.return_value = [...]result = sync(conn, api, days=7, _sleep_fn=lambda _: None)→ garminconnect/garth import 없음. api는 MagicMock. 변경 불필요 ✅
1.3 확인 결과: test_garmin_wellness_sync.py동일 패턴. MagicMock api. 변경 불필요 ✅
2. 신규 테스트 작성 계획
2.1 test_garmin_auth_migration.py (신규)python"""garmin_auth.py garminconnect 0.3.x 마이그레이션 테스트."""
class TestTokenstorePath:    def test_default_path(self):        """config 없으면 ~/.garminconnect 반환."""        def test_explicit_path(self):        """garmin.tokenstore 설정 시 그 경로 반환."""        def test_user_id_path(self):        """garmin.user_id 설정 시 ~/.garminconnect/{safe_uid} 반환."""        def test_user_id_email_sanitize(self):        """이메일의 @, / 등 안전 문자로 변환."""

class TestLogin:    def test_no_token_file_raises(self):        """토큰 파일 없으면 GarminAuthRequired."""        def test_token_file_exists_calls_login(self, mocker):        """토큰 파일 존재 시 Garmin().login(tokenstore=...) 호출."""        def test_429_propagated(self, mocker):        """GarminConnectTooManyRequestsError는 그대로 전파."""        def test_auth_error_wraps_to_auth_required(self, mocker):        """GarminConnectAuthenticationError → GarminAuthRequired 변환."""

class TestCheckConnection:    def test_no_tokenstore(self):        """디렉터리 없으면 미설정."""        def test_old_garth_token_detected(self, tmp_path):        """oauth2_token.json 존재, garmin_tokens.json 없음 → 마이그레이션 안내."""        def test_valid_token(self, tmp_path):        """garmin_tokens.json 정상 → ok=True."""        def test_corrupted_token(self, tmp_path):        """garmin_tokens.json JSON 파싱 실패 → 토큰 손상."""2.2 test_views_settings_garmin_migration.py (신규)python"""views_settings_garmin.py garminconnect 0.3.x 마이그레이션 테스트."""
class TestGarminConnectView:    def test_renders_without_garth(self, client):        """GET /connect/garmin — garth 없이 정상 렌더링."""        def test_token_status_shows_garminconnect_path(self, client):        """토큰 경로가 ~/.garminconnect 포함."""

class TestServerLogin:    def test_login_calls_garminconnect(self, client, mocker):        """POST /connect/garmin — Garmin(email, pw, return_on_mfa=True) 호출."""        def test_mfa_redirect(self, client, mocker):        """MFA 필요 시 /connect/garmin/mfa로 리다이렉트."""        def test_429_shows_error(self, client, mocker):        """429 에러 시 에러 메시지 표시."""

class TestTokenUpload:    def test_upload_garmin_tokens_json(self, client, tmp_path):        """garmin_tokens.json 업로드 → ~/.garminconnect/{user}/ 저장."""        def test_old_oauth2_rejected(self, client, tmp_path):        """oauth2_token.json 형식 업로드 시 안내 메시지."""

class TestMFA:    def test_mfa_submit_calls_resume_login(self, client, mocker):        """MFA 코드 제출 → garmin.resume_login() 호출."""        def test_expired_session(self, client):        """만료된 MFA 세션 → 에러 리다이렉트."""3. 통합 테스트 (수동)
3.1 VPS 환경 검증 체크리스트bash1. 의존성 설치pip uninstall garth -ypip install --upgrade "garminconnect>=0.3.1" curl_cffi ua-generator
2. curl_cffi TLS impersonation 검증python3 -c "from curl_cffi import requestsr = requests.get('https://tls.browserleaks.com/json', impersonate='safari')print('TLS OK:', r.status_code)"
3. 토큰 발급 (인터랙티브 — SSH 세션)python3 -c "from garminconnect import Garming = Garmin('your@email.com', 'your_password', prompt_mfa=lambda: input('MFA: '))g.login(tokenstore='~/.garminconnect/your_at_email.com')print('Login OK:', g.get_full_name())"
4. 토큰 파일 확인ls -la ~/.garminconnect/your_at_email.com/garmin_tokens.json
5. 토큰 기반 재로그인 확인python3 -c "from garminconnect import Garming = Garmin()g.login(tokenstore='~/.garminconnect/your_at_email.com')print('Token login OK:', g.get_full_name())"
6. 기본 동기화 테스트python3 src/sync_cli.py sync --source garmin --days 1
7. 웹 UI 확인/connect/garmin 페이지 로드 → 토큰 상태 배지 확인/sync 페이지 → 기본 동기화 실행
8. 백그라운드 동기화 테스트/sync → 기간 동기화 → 백그라운드 모드 체크 → 실행 → 진행률 확인3.2 AWS IP 차단 대응 시나리오
[2026-04-25 업데이트] diauth.garmin.com이 AWS IP를 차단함이 확인됨. A안(로컬 토큰 발급) 채택. 상세: MIGRATION-01-01/02.
| 시나리오 | 원인 | 조치 ||---------|------|------|| VPS에서 429 발생 (login 성공처럼 보임) | diauth.garmin.com 차단 + silent fail | A안: scripts/garmin_local_sync.py 실행 후 토큰 업로드 || 웹 업로드 후 sync 즉시 실패 | 업로드 직후 갱신 임박 토큰 사용 | 로컬에서 방금 발급한 토큰만 사용 (만료 잔여 3600s) || 45분+ 장시간 sync 도중 실패 | 토큰 만료 (갱신 불가) | B안 구현 전까지 30일 단위 분할 실행 || VPS에서 직접 로그인 시 즉각 401 | _refresh_session() silent fail → 이후 API 401 | A안으로 우회 |
4. 마이그레이션 실행 순서
Step 1: 의존성 변경bashrequirements.txt 수정pip install 실행pip uninstall garth -ypip install -r requirements.txtStep 2: garmin_auth.py 재작성- 문서 1 (MIGRATION-01-AUTH.md) 섹션 1.3 코드 적용
Step 3: views_settings_garmin.py 재작성- 문서 1 (MIGRATION-01-AUTH.md) 섹션 2 설계 적용
Step 4: 인프라 파일 수정- Dockerfile, docker-compose.yml, config.json.example, .gitignore- 문서 3 (MIGRATION-03-INFRA.md) 적용
Step 5: 테스트 실행bashpython -m pytest tests/ -v --tb=shortStep 6: 초기 토큰 발급- VPS SSH 직접 로그인 시도- 실패 시 로컬 발급 후 전송
Step 7: 동기화 검증- 기본 동기화 → 기간 동기화 → 백그라운드 동기화 순차 확인
Step 8: 정리bash기존 garth 토큰 백업 후 제거mv /.garth /.garth.bak.$(date +%Y%m%d)docker-compose.yml에서 .garth 마운트 제거5. 롤백 계획
garth 패키지를 재설치하고 원본 파일 복원:bashpip install garth>=0.4.0git checkout -- src/sync/garmin_auth.py src/web/views_settings_garmin.py requirements.txt단, garth 로그인 자체가 429로 차단된 상태이므로 롤백해도 신규 로그인은 불가. 기존 토큰이 만료되지 않은 경우에만 롤백이 유의미.
6. 미해결 확인 사항
| # | 항목 | 우선순위 | 비고 ||---|------|---------|------|| 1 | garmin.py에서 sync_activities/sync_wellness re-export 경로 확인 | 높음 | bg_sync.py가 참조 || 2 | garminconnect 0.3.x connectapi 내부 자동 토큰 갱신 여부 | ~~높음~~ 해소 | VPS IP 차단으로 갱신 불가 확인 → A안으로 우회 (ADR-010). B안 구현 시 재검토. || 3 | curl_cffi ARM64 wheel 존재 여부 (AWS Graviton) | 중간 | Dockerfile 빌드 || 4 | test_flask_routes.py garmin 라우트 포함 여부 | 낮음 | 테스트 커버리지 || 5 | garminconnect 0.3.x의 get_body_battery_events(cdate) 시그니처 | 낮음 | 현행 코드가 (cdate, cdate) 2인자 호출 |
