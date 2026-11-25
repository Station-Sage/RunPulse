# DESIGN-COACH-PLAN-ADJUSTMENT-ACCEPT — 조정 수락 영속화 (포인터·현황)

- 상태: 2026-11-25 대조 결과. **설계·구현이 이미 존재**한다. 이 문서는 BACKLOG `P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`가 요구한 파일명의 진입점이며, 새 설계를 추가하지 않는다.
- 본 설계: `DESIGN-PLAN-ADJUSTMENTS.md` (A안: `plan_adjustments` 이력 테이블 + 읽을 때 오버레이). ADR-035(`v0.3/data/decisions.md`).
- BACKLOG의 "`planned_workouts`에 `adjusted_distance_km` 추가 또는 `distance_km` 덮어쓰기" 방안은 채택하지 않았다. 원본 행을 건드리지 않고 되돌리기·이력을 보존하기 위해 오버레이 방식이다.

## 코드 현황 (확인한 것만)

| 항목 | 위치 |
|---|---|
| 테이블 | `src/db_schema_v31.py`, 이후 v37 재생성(커밋 1ba709a4) |
| 오버레이 | `src/training/plan_overlay.py` |
| 서비스 | `src/services/plan_adjustment_service.py` (제안 upsert·수락·되돌리기·이력) |
| API | `src/api/routes_plan_adjust.py`: `POST /coach/plan/adjustments/<id>/accept`, `.../revert`, `GET /coach/plan/<goal_id>/adjustments` |

BACKLOG·03e가 적은 `PUT .../accept-adjustment` 경로는 존재하지 않고, 실제 계약은 위 POST 두 개다.

## 남은 확인 (TODO: 확인 필요)

- DESIGN-PLAN-ADJUSTMENTS §7의 T4(R1 순위·이행률 연결), T6(matcher), T7(프론트 `AdjustmentCard`), T9(문서) 구현 여부. 이 실행에서 pytest·브라우저 검증을 하지 않았다.
- §8 결정 4건(제안 행 생성 시점, v1 거리 규칙, 원본 행 변경 시 stale, 외부 출력(ICS·garmin_push·caldav_push) 반영)의 사용자 확정 여부. DECISIONS.md에 확정 기록이 없다.
- 후속 `P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT-IMPL`의 처리 방향 → DECISIONS.md `[P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT]` 참조.
