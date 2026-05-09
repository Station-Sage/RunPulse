문서 2 (SYNC-MODES): 3개 동기화 모드 전수 조사 결과, activity_sync/wellness_sync/api_extensions/daily_extensions/athlete_extensions/bulk_loader 총 12개 모듈은 garth 직접 의존 없음 확인. 백그라운드 동기화의 장시간 토큰 갱신과 bg_sync 내 import 경로 불일치 2건 주의사항 식별.
📄 문서 2: MIGRATION-02-SYNC-MODES.md — 3개 동기화 모드 영향 분석
Garmin 마이그레이션 — 동기화 모드별 영향 상세 분석
작성일: 2026-04-09 | 브랜치: renew/data-architecture
1. 기본 동기화 (Basic Sync)
1.1 호출 경로views_sync.py → /api/sync (AJAX)   → orchestrator.full_sync(conn, sources=["garmin"], days=7, api_clients={"garmin": client})    → garmin_activity_sync.sync(conn, api, days=7)    → garmin_wellness_sync.sync(conn, api, days=7)1.2 client 생성 지점- views_sync.py 또는 호출부에서 garmin._login(config) → Garmin 객체 생성- orchestrator.full_sync()는 api_clients["garmin"]으로 전달받음
1.3 영향 분석
garmin_activity_sync.py — 전수 확인 결과:- garth/garminconnect import: 없음 (garminconnect.Garmin은 TYPE_CHECKING에서만 참조)- api 사용 메서드: api.get_activities_by_date(), api.get_activity(), api.get_activity_splits()- 0.3.x 호환: ✅ 동일 시그니처 확인 (garminconnect/init.py 소스 대조)- 429 감지: _is_rate_limit_error() → 문자열 기반 ("429", "too many requests", "TooManyRequests") → ✅ 호환- 변경 불필요
garmin_wellness_sync.py — 전수 확인 결과:- garth/garminconnect import: 없음- api 사용 메서드: api.get_sleep_data(), api.get_hrv_data(), api.get_body_battery(), api.get_stress_data(), api.get_user_summary(), api.get_training_readiness()- 0.3.x 호환: ✅ 전부 동일 시그니처- 변경 불필요
garmin_helpers.py — 전수 확인 결과:- garth/garminconnect import: 없음- API 호출: 없음 (DB 헬퍼만)- 변경 불필요
1.4 기본 동기화 결론client 객체가 garminconnect 0.3.x Garmin 인스턴스로 바뀌어도 하위 모듈은 코드 변경 없이 동작. _login() 내부만 바뀜.
2. 기간 동기화 (Period Sync)
2.1 호출 경로sync_ui.js → doSync('hist') → /api/sync (AJAX, from/to date params)  → orchestrator.full_sync(conn, sources=[...], days=N, include_streams=True)  → 또는 bg_sync 모드 (hist-bg-mode 체크 시)2.2 추가 모듈 — garmin_api_extensions.py 전수 확인
| 함수 | API 메서드 | 0.3.x 호환 | 변경 ||------|-----------|-----------|------|| sync_activity_streams() | client.get_activity_details(source_id, maxpoly=9999999) | ✅ | 불필요 || sync_activity_gear() | client.get_activity_gear(source_id) | ✅ | 불필요 || sync_activity_exercise_sets() | client.get_activity_exercise_sets(source_id) | ✅ | 불필요 || sync_activity_weather() | client.get_activity_weather(source_id) | ✅ | 불필요 || sync_activity_hr_zones() | client.get_activity_hr_in_timezones(source_id) | ✅ | 불필요 || sync_activity_power_zones() | client.get_activity_power_in_timezones(source_id) | ✅ | 불필요 |
모든 함수는 client: "Garmin" 타입 힌트만 사용, garth/garminconnect 직접 import 없음. → 변경 불필요
2.3 기간 동기화 결론기본 동기화 + include_streams=True + force 모드. 추가 API 호출 모두 호환 확인. 변경 불필요.
3. 백그라운드 동기화 (Background Sync)
3.1 호출 경로sync_ui.js → doSync('hist', bg=true) → /api/bg-sync/start (AJAX)  → bg_sync.start_job(service, from_date, to_date, config, user_id)    → BgSyncThread._run_batches()      → _garmin_login() → garmin._login(config)      → _run_one_batch() → garmin.sync_activities() / garmin_wellness_sync.sync_wellness()3.2 bg_sync.py 전수 garth/garminconnect 의존 분석
| 위치 | 코드 | 영향 ||------|------|------|| _run_one_batch() | from garminconnect import GarminConnectTooManyRequestsError as _G429 | ✅ 동일 클래스 || _garmin_login() | from src.sync.garmin import _login | _login() 내부만 바뀜, 인터페이스 동일 || _garmin_login() | from garminconnect import GarminConnectTooManyRequestsError | ✅ 동일 || _garmin_login() | isinstance(exc, GarminConnectTooManyRequestsError) | ✅ || _garmin_login() | isinstance(exc, GarminAuthRequired) | ✅ 자체 예외 || _run_one_batch() | from src.sync.garmin import sync_activities | orchestrator 레벨 || _run_one_batch() | from src.sync.garmin_wellness_sync import sync_wellness | 주의: garmin_wellness_sync에 sync_wellness 존재 여부 확인 |
3.3 ⚠️ 발견 사항: bg_sync 내 import 경로 불일치
bg_sync.py L176:pythonfrom src.sync.garmin_wellness_sync import sync_wellness그러나 garmin_wellness_sync.py의 공개 함수는 sync() (not sync_wellness).→ 이것은 기존 버그이거나 garmin.py에 re-export가 있을 수 있음.
garmin.py 확인: sync_activities와 sync_wellness는 from src.sync.garmin import ...으로 호출되지만 garmin.py에는 해당 re-export가 보이지 않음. bg_sync.py가 from src.sync.garmin import sync_activities를 호출하는데 garmin.py에 sync_activities 정의가 없음.
→ 확인 필요: garmin.py에서 garmin_activity_sync.sync를 sync_activities로 re-export하는지, garmin_wellness_sync.sync를 sync_wellness로 re-export하는지 garmin.py의 전체 코드에서 확인 (현재 가져온 코드에서는 보이지 않지만 중간이 잘렸을 수 있음).
3.4 장시간 세션 토큰 자동 갱신
핵심 확인 포인트: 백그라운드 동기화는 garmin_client를 한 번 생성해서 수십~수백 배치에 재사용.
garminconnect 0.3.x login() 소스 확인 결과:pythonProactively refresh DI token if it's expired or about to expire.if self.client.di_refresh_token and self.client._token_expires_soon():    self.client._refresh_session()그리고 connectapi() 내부:pythonHTTPError 401 → GarminConnectAuthenticationError결론:- 0.3.x는 login() 호출 시 토큰 자동 갱신을 수행- 하지만 이후 API 호출(connectapi) 시에는 자동 갱신 로직이 호출되지 않음 (확인 필요)- 장시간 배치 중 access_token이 만료되면 401이 발생할 수 있음
[2026-04-25 업데이트] 갱신 시도 자체가 AWS IP에서 차단됨 (diauth.garmin.com → 429). 
결과: VPS에서 장시간 배치(45분+)는 토큰 갱신 불가로 원천적으로 실패.
→ A안(로컬 토큰 발급) 채택으로 이 문제 우회: 발급 직후 토큰(잔여 ~3600s)으로 45분 내 sync.
→ B안(SSH 역방향 터널) 구현 시 근본 해결. 상세: MIGRATION-01-01/02/03.
대응 방안:1. _run_one_batch() 시작 시 garmin_client.login(tokenstore=...) 재호출로 토큰 refresh 트리거2. 또는 connectapi() 래퍼에서 401 catch → 자동 재로그인 → 재시도 로직 추가3. 0.3.x client 내부 코드 추가 확인 후 결정
3.5 Rate Limiter 이중 retry 확인
현행 RunPulse rate_limiter.py:- garmin 정책: per_request_sleep=2s, max_retries=3, backoff_base=120s- pre_request() → 2초 sleep- handle_rate_limit() → 120s * 2^n backoff
garminconnect 0.3.x 내부:- connectapi() 내 retry 로직: 없음 (429 → 즉시 GarminConnectTooManyRequestsError raise)- login() 내 retry: 없음 (429 → 즉시 raise)
결론: 이중 retry 위험 없음. 0.3.x는 예외만 raise하고 RunPulse의 rate_limiter가 retry 제어.
3.6 백그라운드 동기화 결론
| 항목 | 상태 | 조치 ||------|------|------|| garminconnect import | ✅ 호환 | 변경 불필요 || 예외 클래스 | ✅ 동일 | 변경 불필요 || 장시간 토큰 갱신 | ❌ VPS 차단 확인 | diauth.garmin.com AWS IP 차단. A안(45분 내 sync)으로 우회. B안으로 근본 해결. || Rate limiter | ✅ 충돌 없음 | 변경 불필요 || sync_activities/sync_wellness import | ⚠️ 확인 필요 | garmin.py re-export 확인 |
4. 기간 동기화 UX 개선: 연도 × 월 그리드
4.1 현행 문제
기간 동기화는 시작일~종료일 날짜 피커 2개로 구성. 어느 달 데이터가 이미 있는지 알 수 없고, "2024년 전체 채우기" 같은 월 단위 의도를 표현하기 불편. A안 로컬 sync 이후 "어느 달 sync 할지" 선택 시 특히 어색.
4.2 제안: 연도 × 월 그리드
```
             1월  2월  3월  4월  5월  6월  7월  8월  9월  10월 11월 12월
            ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
2024 [전체]  │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │
            ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
2025 [전체]  │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │ ✓ │   │   │   │
            ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
2026 [전체]  │ ✓ │ ✓ │ ✓ │[★]│   │   │   │   │   │   │   │   │
            └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
[빠진 달만 선택]  [초기화]                              [동기화 시작 →]
```
- ✓ (초록): 해당 월 데이터 존재 / ★ (파란 테두리): sync 대상 선택됨 / 빈 칸: 데이터 없음
- [전체]: 해당 연도 12개월 토글 / [빠진 달만 선택]: 데이터 없는 달 자동 선택
- 기존 날짜 피커는 <details> 고급 옵션으로 접어둠
4.3 커버리지 API (신규)
GET /api/sync/coverage?source=garmin
응답: { "2025": [true×9, false×3], "2026": [true×4, false×8] }
쿼리: SELECT strftime('%Y',date), strftime('%m',date), COUNT(*) FROM activities WHERE source=:source GROUP BY 1,2
4.4 A안 연동
로컬 스크립트 실행 후 VPS 응답에 웹 URL 포함:
  "https://your.vps/sync?source=garmin&suggest=missing"
→ suggest=missing 수신 시 Garmin 기준 빠진 달 자동 선택 상태로 렌더링
4.5 구현 위치
| 항목 | 파일 |
|------|------|
| 커버리지 API | src/web/app.py |
| 그리드 HTML/JS | src/web/views_sync.py + sync_ui.py |
| suggest=missing 처리 | views_sync.py GET 핸들러 |

5. garmin.py — re-export 허브 분석
현행 garmin.py 상단에서 re-export:pythonfrom src.sync.garmin_auth import (    Garmin, GarminAuthRequired, GarminConnectTooManyRequestsError,    _login, _tokenstore_path, check_garmin_connection,)from src.sync.garmin_helpers import (    _handle_rate_limit, _store_daily_detail_metrics,    _store_raw_payload, _upsert_daily_detail_metric, _upsert_vo2max,)from src.sync.garmin_daily_extensions import (...)from src.sync.garmin_athlete_extensions import (...)garmin.py 자체 정의 함수: sync_daily_extensions(), sync_athlete_extensions(), sync_garmin().
sync_garmin() 내부에서:pythonact_count = sync_activities(config, conn, days, client=client)well_count = sync_wellness(config, conn, days, client=client)→ sync_activities와 sync_wellness가 garmin.py에 정의되지 않고, import도 안 보임.→ garmin.py에서 가져온 코드가 중간에 잘렸을 가능성 높음. 또는 garmin.py 하단에 추가 import/정의가 있을 수 있음.
조치: 전체 garmin.py를 다시 확인하여 sync_activities, sync_wellness 정의 위치 파악.