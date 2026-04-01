# src/sync/ GUIDE — 4소스 데이터 동기화

## 구조
- 소스별 오케스트레이터 (`garmin.py`, `strava.py`, `intervals.py`, `runalyze.py`)
- 각 오케스트레이터 아래 세부 모듈 (auth, activity_sync, wellness_sync 등)
- `src/sync.py` (CLI 진입점) → ThreadPoolExecutor 4소스 병렬 실행
- sync 완료 후 `src/metrics/engine.py` 자동 호출 (메트릭 재계산 훅)

## 파일 맵

### Garmin (10개)
| 파일 | 역할 |
|------|------|
| `garmin.py` | 통합 sync 오케스트레이터 |
| `garmin_auth.py` | 인증. 토큰 전용 (비밀번호 fallback 없음). 경로: config `tokenstore` → `user_id` 서브폴더 → `~/.garth/` 순. 429는 `GarminConnectTooManyRequestsError`, 토큰 없음은 `GarminAuthRequired` 발생 |
| `garmin_activity_sync.py` | 활동 + splits + backfill |
| `garmin_api_extensions.py` | streams/gear/exercise_sets |
| `garmin_athlete_extensions.py` | profile/stats/personal_records |
| `garmin_daily_extensions.py` | race_predictions/training_status/fitness/HR/stress/BB |
| `garmin_wellness_sync.py` | 수면/HRV/BB/스트레스/SPO2 |
| `garmin_v2_mappings.py` | ZIP/detail 필드 매핑 |
| `garmin_backfill.py` | 기존 활동 보강 |
| `garmin_helpers.py` | 공통 헬퍼 |

### Strava (4개)
| 파일 | 역할 |
|------|------|
| `strava.py` | 통합 sync 오케스트레이터 |
| `strava_auth.py` | OAuth2 토큰 관리 |
| `strava_activity_sync.py` | 활동/streams/laps/best_efforts |
| `strava_athlete_sync.py` | profile/stats/gear |

### Intervals.icu (5개)
| 파일 | 역할 |
|------|------|
| `intervals.py` | 통합 sync 오케스트레이터 |
| `intervals_auth.py` | API 인증 |
| `intervals_activity_sync.py` | 활동/intervals/streams |
| `intervals_athlete_sync.py` | profile/stats |
| `intervals_wellness_sync.py` | 웰니스/피트니스 (CTL/ATL/TSB) |

### Runalyze (1개)
| 파일 | 역할 |
|------|------|
| `runalyze.py` | VDOT/Marathon Shape/Race Prediction |

## 규칙
1. 모든 외부 API 호출은 `src/utils/api.py` 래퍼 사용 (직접 httpx/requests 금지)
2. API 실패 시 재시도 1회 후 로그 남기고 계속 (전체 sync 중단 금지)
3. 비밀 정보(토큰)는 `config.json`에서 로드 (`load_config()` 호출 시 자동 복호화됨). 절대 하드코딩/커밋 금지
4. 중복 활동 매칭: timestamp ±5분 AND distance ±3% (`src/utils/dedup.py`)

## 의존성
- `src/utils/api.py` — HTTP 래퍼
- `src/utils/config.py` — config.json 로드
- `src/utils/dedup.py` — 중복 매칭
- `src/utils/sync_jobs.py` — 동기화 작업 관리
- `src/utils/sync_policy.py` — 동기화 정책
- `src/utils/sync_state.py` — 동기화 상태 추적
- `src/metrics/engine.py` — sync 완료 후 메트릭 재계산 훅
- `src/web/bg_sync.py` — 웹에서 백그라운드 동기화 실행
