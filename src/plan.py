"""훈련 계획 CLI 진입점."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import sqlite3

from src.db_setup import get_db_path, init_db
from src.utils.config import load_config
from src.utils.pace import seconds_to_pace
from src.training.goals import add_goal, list_goals, complete_goal, cancel_goal
from src.training.planner import generate_weekly_plan, save_weekly_plan, get_planned_workouts
from src.training.adjuster import adjust_todays_plan


def _fmt_pace(sec: int | None) -> str:
    if sec is None:
        return "-"
    return seconds_to_pace(sec)


def _fmt_goal(g: dict) -> str:
    race = g.get("race_date") or "-"
    target = g.get("target_time_sec")
    target_str = ""
    if target:
        h, rem = divmod(int(target), 3600)
        m, s = divmod(rem, 60)
        target_str = f" 목표 {h}:{m:02d}:{s:02d}"
    return (f"[{g['id']}] {g['name']} | {g['distance_km']}km | "
            f"레이스 {race}{target_str} | {g['status']}")


def _fmt_workout(w: dict, show_adjust: bool = False) -> str:
    dist = f"{w['distance_km']:.1f}km" if w.get("distance_km") else "-"
    pace_min = _fmt_pace(w.get("target_pace_min"))
    pace_max = _fmt_pace(w.get("target_pace_max"))

    if show_adjust:
        adj = w.get("adjusted_type", w["workout_type"])
        orig = w.get("original_type", w["workout_type"])
        type_str = adj + (f" (원래:{orig})" if adj != orig else "")
    else:
        completed = "✓" if w.get("completed") else " "
        type_str = f"[{completed}] {w['workout_type']}"

    return f"{w['date']} {type_str:<18} {dist:<8} pace {pace_min}~{pace_max}"


def cmd_goal_list(conn: sqlite3.Connection, args) -> None:
    status = getattr(args, "status", None) or "active"
    goals = list_goals(conn, status=status)
    if not goals:
        print("목표 없음.")
        return
    for g in goals:
        print(_fmt_goal(g))


def cmd_goal_add(conn: sqlite3.Connection, args) -> None:
    target_sec = None
    if args.target_time:
        try:
            parts = args.target_time.split(":")
            if len(parts) == 3:
                target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60
        except (ValueError, IndexError):
            print(f"[오류] --target-time 형식 오류: {args.target_time} (H:MM:SS 또는 H:MM)")
            return

    goal_id = add_goal(
        conn,
        name=args.name,
        distance_km=args.distance,
        race_date=getattr(args, "date", None),
        target_time_sec=target_sec,
    )
    print(f"목표 추가됨 [id={goal_id}]: {args.name} {args.distance}km")


def cmd_goal_done(conn: sqlite3.Connection, args) -> None:
    if complete_goal(conn, args.id):
        print(f"목표 [id={args.id}] 완료 처리됨.")
    else:
        print(f"목표 [id={args.id}] 를 찾을 수 없습니다.")


def cmd_goal_cancel(conn: sqlite3.Connection, args) -> None:
    if cancel_goal(conn, args.id):
        print(f"목표 [id={args.id}] 취소됨.")
    else:
        print(f"목표 [id={args.id}] 를 찾을 수 없습니다.")


def cmd_week(conn: sqlite3.Connection) -> None:
    workouts = get_planned_workouts(conn)
    if not workouts:
        print("이번 주 계획 없음. 'plan.py generate' 로 생성하세요.")
        return
    print("## 이번 주 훈련 계획\n")
    for w in workouts:
        print(_fmt_workout(w))
        if w.get("rationale"):
            print(f"   → {w['rationale']}")
        print()


def cmd_today(conn: sqlite3.Connection, config: dict) -> None:
    result = adjust_todays_plan(conn, config)
    if result is None:
        print("오늘 계획된 운동 없음.")
        return

    print("## 오늘 훈련 계획\n")
    print(_fmt_workout(result, show_adjust=True))

    w = result.get("wellness", {})
    tsb = result.get("tsb")
    print("\n### 컨디션")
    print(f"- Body Battery : {w.get('body_battery', '-')}")
    print(f"- 수면 점수    : {w.get('sleep_score', '-')}")
    print(f"- TSB          : {f'{tsb:.1f}' if tsb is not None else '-'}")
    print(f"- 피로도       : {result.get('fatigue_level', '-')}")

    if result.get("adjusted"):
        print(f"\n⚠️  조정됨: {result.get('adjustment_reason')}")
        print(f"   {result['original_type']} → {result['adjusted_type']}")
    if result.get("volume_boost"):
        print("\n✅ 컨디션 양호: 볼륨 5~10% 추가 가능")


def cmd_generate(conn: sqlite3.Connection, args, config: dict) -> None:
    goal_id = getattr(args, "goal_id", None)
    plan = generate_weekly_plan(conn, goal_id=goal_id, config=config)
    count = save_weekly_plan(conn, plan)
    print(f"주간 훈련 계획 {count}개 생성/저장 완료.\n")
    for w in plan:
        print(_fmt_workout(w))
        print(f"   → {w['rationale']}")
        print()


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="RunPulse 훈련 계획")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("week", help="이번 주 훈련 계획 표시")
    sub.add_parser("today", help="오늘 훈련 계획 + 컨디션 조정")

    gen_p = sub.add_parser("generate", help="새 주간 훈련 계획 생성 및 저장")
    gen_p.add_argument("--goal-id", type=int, dest="goal_id", help="목표 id (미지정 시 active 목표 자동 선택)")

    goal_p = sub.add_parser("goal", help="목표 관리")
    goal_sub = goal_p.add_subparsers(dest="goal_command")

    gl = goal_sub.add_parser("list", help="목표 목록")
    gl.add_argument("--all", action="store_const", const="all", dest="status",
                    help="전체 상태 표시 (기본: active만)")

    ga = goal_sub.add_parser("add", help="목표 추가")
    ga.add_argument("--name", required=True, help="레이스 이름")
    ga.add_argument("--distance", type=float, required=True, help="거리 (km)")
    ga.add_argument("--date", help="레이스 날짜 (YYYY-MM-DD)")
    ga.add_argument("--target-time", dest="target_time", help="목표 시간 (H:MM:SS)")

    gd = goal_sub.add_parser("done", help="목표 완료 처리")
    gd.add_argument("--id", type=int, required=True, help="목표 id")

    gc = goal_sub.add_parser("cancel", help="목표 취소")
    gc.add_argument("--id", type=int, required=True, help="목표 id")

    parser.add_argument("--user", default="default", help="사용자 ID (기본: default)")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    config = load_config(user_id=args.user)
    init_db(args.user)
    db_path = get_db_path(args.user)

    with sqlite3.connect(db_path) as conn:
        if args.command == "week":
            cmd_week(conn)
        elif args.command == "today":
            cmd_today(conn, config)
        elif args.command == "generate":
            cmd_generate(conn, args, config)
        elif args.command == "goal":
            if args.goal_command == "list":
                cmd_goal_list(conn, args)
            elif args.goal_command == "add":
                cmd_goal_add(conn, args)
            elif args.goal_command == "done":
                cmd_goal_done(conn, args)
            elif args.goal_command == "cancel":
                cmd_goal_cancel(conn, args)
            else:
                goal_p.print_help()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
