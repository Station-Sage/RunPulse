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
| `planner_rules.py` | 훈련 단계·볼륨·Q-day·페이스·배분 규칙 (Daniels VDOT 존 기반) | `training_phase()`, `weekly_volume_km()`, `distribute_volume()`, `pace_range()` |
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

## 페이스 존 (Daniels VDOT 기반, `planner_rules.py::pace_range()`)
| 타입 | 기준 | 범위 |
|------|------|------|
| `easy` | E존 | E−10 ~ E+30 초/km |
| `long` | E존 (느리게 biased) | E+10 ~ E+50 초/km |
| `recovery` | E존 (매우 느림) | E+50 ~ E+90 초/km |
| `tempo` | T존 | T−5 ~ T+10 초/km |
| `interval` | I존 | I−5 ~ I+10 초/km |

## n_q (Quality Day) 계산 규칙
- `math.ceil(n_avail * 0.20)` — Seiler 80/20 원칙
- `round()` 사용 금지 (round(7*0.2)=1 버그 → build/peak Q-day 미생성)
- Q-slot 다음날 → recovery_slot 자동 배정 (Daniels Hard-Easy 원칙 — 구조적 적용, 항상)
- **플랜 생성 시 CRS 게이트 없음**: 컨디션(TSB/ACWR/BB/HRV/CIRS)은 일일 추천카드(adjuster.py)에서만 적용
- Q-day 타입: build/peak → interval, base/taper/recovery_week → tempo (phase 기반 순수 결정)

## CRS Gate 5종 (`src/metrics/crs.py`) — 일일 추천카드 전용
1. 급성 부하 스파이크 (ACWR)
2. 회복 상태 (UTRS)
3. 수면 품질
4. 스트레스/HRV
5. 근육 준비도

**적용 범위**: `adjuster.py` (오늘의 훈련 추천카드)만 CRS 게이트 사용. `planner.py`는 사용 안 함.

## 규칙
1. `readiness.py` 입력: 최근 7일 활동, UTRS, CIRS, HRV, 수면, TSB
2. `readiness.py` 출력: `readiness_score` 0~100, `readiness_level`, `limiting_factors`
3. goals 테이블: `SCHEMA_VERSION = 3.1` (내부 migration v4) — `src/db_setup.py` 관리
4. session_outcomes ML: v0.4에서 CRS 가중치 자동 도출 예정 (현재 데이터 축적)

## 전체 기간 플랜 생성 (wizard + 재생성)
- `_save_and_generate` / `_update_and_maybe_regen` (views_training_wizard.py): race_date 또는 plan_weeks까지 루프로 전체 주 생성
- `/training/generate` (views_training.py): goal의 race_date/plan_weeks 기반으로 주 수 결정
- 재생성 시 현재 주 이후 기존 source='planner' 워크아웃 삭제 후 재생성
- **auto_gen 없음**: 페이지 로드 시 자동 플랜 생성 제거 — wizard 또는 재생성 버튼으로만 생성

## 주의사항 — 300줄 초과
없음 (REFAC-2 완료: planner.py 307줄 + planner_config.py 173줄 + planner_rules.py 264줄)

## 의존성
- `src/metrics/crs.py` — CRS Gate 참조
- `src/metrics/engine.py` — UTRS, CIRS, ACWR 등 메트릭 로드 (metric_store 기반)
- `src/utils/metric_registry.py` — 메트릭 이름/카테고리 조회
- `src/web/views_training*.py` — 웹 UI에서 호출
- `src/ai/` — AI 코치가 훈련 계획 생성 시 호출
