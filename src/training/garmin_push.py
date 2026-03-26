"""Garmin Connect 워크아웃 전송 — 훈련 계획을 워치 + 캘린더에 등록.

RunPulse planned_workouts → Garmin RunningWorkout → upload + schedule.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.sync.garmin_auth import _login


def push_workout_to_garmin(
    config: dict,
    conn: sqlite3.Connection,
    workout: dict,
    client=None,
) -> dict | None:
    """단일 워크아웃을 Garmin Connect에 업로드 + 스케줄.

    Args:
        config: 설정 dict.
        conn: DB 연결 (garmin_workout_id 저장용).
        workout: planned_workouts 행 dict.
        client: Garmin 클라이언트 (None이면 로그인).

    Returns:
        Garmin API 응답 또는 None.
    """
    if client is None:
        client = _login(config)

    wtype = workout.get("workout_type", "easy")
    dist_km = workout.get("distance_km")
    pace_min = workout.get("target_pace_min")  # sec/km
    pace_max = workout.get("target_pace_max")  # sec/km
    workout_date = workout.get("date")
    workout_id = workout.get("id")

    if wtype == "rest":
        return None

    garmin_workout = _build_running_workout(wtype, dist_km, pace_min, pace_max)
    if garmin_workout is None:
        return None

    try:
        # 1. 업로드
        result = client.upload_running_workout(garmin_workout)
        garmin_wk_id = result.get("workoutId")

        # 2. 날짜 스케줄
        if garmin_wk_id and workout_date:
            client.schedule_workout(garmin_wk_id, workout_date)

        # 3. DB에 garmin_workout_id 저장
        if garmin_wk_id and workout_id:
            conn.execute(
                "UPDATE planned_workouts SET garmin_workout_id=? WHERE id=?",
                (str(garmin_wk_id), workout_id),
            )
            conn.commit()

        return result
    except Exception as exc:
        print(f"[garmin] 워크아웃 전송 실패: {exc}")
        return None


def push_weekly_plan(
    config: dict,
    conn: sqlite3.Connection,
    week_offset: int = 0,
) -> int:
    """주간 훈련 계획 전체를 Garmin에 전송.

    Returns:
        전송 성공 수.
    """
    from src.training.planner import get_planned_workouts
    from datetime import timedelta

    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    workouts = get_planned_workouts(conn, week_start)

    if not workouts:
        return 0

    client = _login(config)
    count = 0
    for w in workouts:
        if w.get("workout_type") == "rest":
            continue
        if w.get("garmin_workout_id"):
            continue  # 이미 전송됨
        result = push_workout_to_garmin(config, conn, w, client=client)
        if result:
            count += 1

    return count


def _build_running_workout(
    wtype: str,
    dist_km: float | None,
    pace_min: int | None,
    pace_max: int | None,
) -> "RunningWorkout | None":
    """RunPulse 워크아웃 → Garmin RunningWorkout 변환."""
    try:
        from garminconnect.workout import (
            RunningWorkout,
            WorkoutSegment,
            create_warmup_step,
            create_interval_step,
            create_cooldown_step,
            create_recovery_step,
            TargetType,
        )
    except ImportError:
        print("[garmin] garminconnect[workout] 패키지 필요: pip install garminconnect[workout]")
        return None

    # 타입별 한국어 이름
    _NAMES = {
        "easy": "이지런", "tempo": "템포런", "threshold": "역치런",
        "interval": "인터벌", "long": "장거리런", "recovery": "회복조깅",
        "race": "레이스",
    }
    name = f"RunPulse: {_NAMES.get(wtype, wtype)}"
    if dist_km:
        name += f" {dist_km:.1f}km"

    # 목표 시간 추정 (거리 × 평균 페이스)
    est_sec = 1800  # 기본 30분
    if dist_km and pace_min and pace_max:
        avg_pace = (pace_min + pace_max) / 2
        est_sec = int(dist_km * avg_pace)

    # 페이스 목표 (sec/km → m/s: 1000/pace_sec)
    target = None
    if pace_min and pace_max:
        speed_min = round(1000 / pace_max, 2)  # 느린 페이스 = 낮은 속도
        speed_max = round(1000 / pace_min, 2)  # 빠른 페이스 = 높은 속도
        target = {
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "speed.zone"},
            "targetValueOne": speed_min,
            "targetValueTwo": speed_max,
        }

    # 워크아웃 구조
    if wtype in ("easy", "recovery", "long"):
        # 단순 구조: 워밍업 5분 + 메인 + 쿨다운 5분
        main_sec = max(300, est_sec - 600)
        steps = [
            create_warmup_step(300.0, step_order=1),
            create_interval_step(float(main_sec), step_order=2, target_type=target),
            create_cooldown_step(300.0, step_order=3),
        ]
    elif wtype in ("tempo", "threshold"):
        # 워밍업 10분 + 메인 + 쿨다운 10분
        main_sec = max(600, est_sec - 1200)
        steps = [
            create_warmup_step(600.0, step_order=1),
            create_interval_step(float(main_sec), step_order=2, target_type=target),
            create_cooldown_step(600.0, step_order=3),
        ]
    elif wtype == "interval":
        # 워밍업 10분 + (빠르게 3분 + 회복 2분) × 5 + 쿨다운 10분
        steps = [create_warmup_step(600.0, step_order=1)]
        order = 2
        for _ in range(5):
            steps.append(create_interval_step(180.0, step_order=order, target_type=target))
            order += 1
            steps.append(create_recovery_step(120.0, step_order=order))
            order += 1
        steps.append(create_cooldown_step(600.0, step_order=order))
    else:
        # 기본: 단순 런
        steps = [
            create_warmup_step(300.0, step_order=1),
            create_interval_step(float(max(300, est_sec - 600)), step_order=2, target_type=target),
            create_cooldown_step(300.0, step_order=3),
        ]

    return RunningWorkout(
        workoutName=name,
        estimatedDurationInSecs=est_sec,
        workoutSegments=[
            WorkoutSegment(
                segmentOrder=1,
                sportType={"sportTypeId": 1, "sportTypeKey": "running"},
                workoutSteps=steps,
            )
        ],
    )
