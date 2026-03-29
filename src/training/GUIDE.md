# src/training/ GUIDE — 훈련 엔진 v2

## 구조
논문 기반 훈련 계획 생성/관리. DB: `planned_workouts`, `goals`, `user_training_prefs`, `session_outcomes`.

```
readiness.py ──→ planner.py ──→ planned_workouts 테이블
                     ↑
              user_training_prefs (휴식요일/롱런요일/차단날짜/인터벌거리)

실제 활동 완료 → matcher.py → session_outcomes 누적
스킵 발생     → replanner.py → 잔여 계획 재조정
```

## 파일 맵
| 파일 | 역할 | 주요 함수 |
|------|------|-----------|
| `planner.py` | 훈련 계획 생성 오케스트레이터 + 저장/조회 | `generate_weekly_plan()`, `upsert_user_training_prefs()` |
| `planner_config.py` | 상수 정의 + 설정/메트릭 조회 헬퍼 | `load_prefs()`, `get_vdot_adj()`, `get_latest_fitness()` |
| `planner_rules.py` | 훈련 단계·볼륨·Q-day·페이스·배분 규칙 | `training_phase()`, `weekly_volume_km()`, `distribute_volume()` |
| `readiness.py` | 준비도(Readiness) 계산 | `calc_readiness()`, `get_readiness_summary()` |
| `goals.py` | 목표 CRUD | `add_goal()`, `get_active_goal()`, `complete_goal()`, `cancel_goal()` |
| `matcher.py` | 실제 활동-계획 자동 매칭 | `match_week_activities()`, `save_skipped_outcome()` |
| `replanner.py` | 스킵 시 잔여 주 재조정 | `replan_remaining_week()` |
| `interval_calc.py` | 인터벌 처방 계산 | `prescribe_interval()` |
| `adjuster.py` | 컨디션 기반 부하 조정 | `apply_condition_adjustment()` |
| `garmin_push.py` | Garmin Connect 워크아웃 전송 | `push_weekly_plan()` |
| `caldav_push.py` | CalDAV 캘린더 전송 | `push_weekly_plan_to_caldav()` |

## 훈련 타입
`easy` | `tempo` | `interval` | `long` | `recovery` | `race` | `rest`

## CRS Gate 5종 (`src/metrics/crs.py`)
1. 급성 부하 스파이크 (ACWR)
2. 회복 상태 (UTRS)
3. 수면 품질
4. 스트레스/HRV
5. 근육 준비도

각 Gate 통과 여부에 따라 `planner.py`가 강도 조정.

## 규칙
1. `readiness.py` 입력: 최근 7일 활동, UTRS, CIRS, HRV, 수면, TSB
2. `readiness.py` 출력: `readiness_score` 0~100, `readiness_level`, `limiting_factors`
3. goals 테이블: `SCHEMA_VERSION = 3.1` (내부 migration v4) — `src/db_setup.py` 관리
4. session_outcomes ML: v0.4에서 CRS 가중치 자동 도출 예정 (현재 데이터 축적)

## 주의사항 — 300줄 초과
없음 (REFAC-2 완료: planner.py 307줄 + planner_config.py 173줄 + planner_rules.py 264줄)

## 의존성
- `src/metrics/crs.py` — CRS Gate 참조
- `src/metrics/store.py` — UTRS, CIRS, ACWR 등 메트릭 로드
- `src/web/views_training*.py` — 웹 UI에서 호출
- `src/ai/` — AI 코치가 훈련 계획 생성 시 호출
