# src/training/ — 훈련 엔진 v2

논문 기반 훈련 계획 생성·관리 엔진. DB 테이블: `planned_workouts`, `goals`, `user_training_prefs`, `session_outcomes`.

## 파일 구조

| 파일 | 역할 | 주요 함수 |
|------|------|-----------|
| `planner.py` | 훈련 계획 생성 오케스트레이터 (713줄) | `generate_weekly_plan()`, `upsert_user_training_prefs()` |
| `replanner.py` | 스킵 시 잔여 주 재조정 | `replan_remaining_week()` |
| `readiness.py` | 준비도(Readiness) 계산 (457줄) | `calc_readiness()`, `get_readiness_summary()` |
| `goals.py` | 목표 CRUD | `add_goal()`, `get_active_goal()`, `complete_goal()`, `cancel_goal()`, `get_goal()` |
| `matcher.py` | 실제 활동-계획 자동 매칭 | `match_week_activities()`, `save_skipped_outcome()` |
| `interval_calc.py` | 인터벌 처방 계산 | `prescribe_interval(rep_m, pace_sec)` |
| `adjuster.py` | 컨디션 기반 부하 조정 | `apply_condition_adjustment()` |
| `crs.py` | CRS(복합 준비도 점수) 5종 Gate | `calc_crs()` |
| `garmin_push.py` | Garmin Connect 워크아웃 전송 | `push_weekly_plan(config, conn)` |
| `caldav_push.py` | CalDAV 캘린더 전송 | `push_weekly_plan_to_caldav(config, conn)` |

## 핵심 흐름

```
readiness.py ──→ planner.py ──→ planned_workouts 테이블
                     ↑
              user_training_prefs (휴식요일/롱런요일/차단날짜/인터벌거리)

실제 활동 완료 → matcher.py → session_outcomes 누적
스킵 발생     → replanner.py → 잔여 계획 재조정
```

## 훈련 타입
`easy` | `tempo` | `interval` | `long` | `recovery` | `race` | `rest`

각 타입별 스타일: `views_training_shared.py`의 `_TYPE_STYLE` dict 참조

## 준비도 계산 (readiness.py)
- 입력: 최근 7일 활동 데이터, UTRS, CIRS, HRV, 수면, TSB
- 출력: `readiness_score` (0~100), `readiness_level` (very_low~excellent), `limiting_factors`
- `get_readiness_summary()` → 웹 뷰 표시용 dict

## goals.py 스키마 연동
```sql
CREATE TABLE goals (
    id, name, distance_km, distance_label, weekly_km_target, plan_weeks,
    race_date, target_time_sec, status, created_at, completed_at
)
```
`SCHEMA_VERSION = 3.1` (내부 migration v4) — `db_setup.py`에서 관리

## CRS Gate 5종 (crs.py)
Gate 1: 급성 부하 스파이크 (ACWR)
Gate 2: 회복 상태 (UTRS)
Gate 3: 수면 품질
Gate 4: 스트레스/HRV
Gate 5: 근육 준비도

각 Gate 통과 여부에 따라 `planner.py`가 운동 강도를 조정

## session_outcomes ML 연동
`matcher.py`의 `save_skipped_outcome()` → `session_outcomes` 테이블 누적
→ v0.4에서 CRS 가중치 자동 도출 예정 (현재 데이터 축적 단계)
