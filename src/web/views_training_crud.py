"""훈련 계획 — CRUD 라우트 + 목표 관리 + ICS 내보내기.

300줄 규칙 준수를 위해 views_training.py에서 분리.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, Response, redirect, request

from src.web.helpers import db_path
from src.web.views_training_loaders import load_workouts

training_crud_bp = Blueprint("training_crud", __name__)


# ── 워크아웃 CRUD ──────────────────────────────────────────────────────


@training_crud_bp.route("/training/workout", methods=["POST"])
def workout_create():
    """워크아웃 생성."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    workout_date = request.form.get("date", "")
    workout_type = request.form.get("workout_type", "easy")
    distance = request.form.get("distance_km", "")
    pace_min = request.form.get("target_pace_min", "")
    pace_max = request.form.get("target_pace_max", "")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute(
                """INSERT INTO planned_workouts
                   (date, workout_type, distance_km, target_pace_min, target_pace_max, source)
                   VALUES (?, ?, ?, ?, ?, 'manual')""",
                (
                    workout_date,
                    workout_type,
                    float(distance) if distance else None,
                    int(pace_min) if pace_min else None,
                    int(pace_max) if pace_max else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


@training_crud_bp.route("/training/workout/<int:workout_id>/update", methods=["POST"])
def workout_update(workout_id: int):
    """워크아웃 수정."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    workout_type = request.form.get("workout_type")
    distance = request.form.get("distance_km", "")
    pace_min = request.form.get("target_pace_min", "")
    pace_max = request.form.get("target_pace_max", "")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute(
                """UPDATE planned_workouts
                   SET workout_type=?, distance_km=?, target_pace_min=?, target_pace_max=?,
                       updated_at=datetime('now')
                   WHERE id=?""",
                (
                    workout_type,
                    float(distance) if distance else None,
                    int(pace_min) if pace_min else None,
                    int(pace_max) if pace_max else None,
                    workout_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


@training_crud_bp.route("/training/workout/<int:workout_id>/delete", methods=["POST"])
def workout_delete(workout_id: int):
    """워크아웃 삭제."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute("DELETE FROM planned_workouts WHERE id=?", (workout_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


@training_crud_bp.route("/training/workout/<int:workout_id>/toggle", methods=["POST"])
def workout_toggle(workout_id: int):
    """워크아웃 완료 상태 토글."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute(
                "UPDATE planned_workouts SET completed = NOT completed, "
                "updated_at=datetime('now') WHERE id=?",
                (workout_id,),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    week = request.form.get("week", "0")
    return redirect(f"/training?week={week}")


# ── 목표 관리 ──────────────────────────────────────────────────────────


@training_crud_bp.route("/training/goal", methods=["POST"])
def goal_create():
    """목표 추가."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    from src.training.goals import add_goal

    name = request.form.get("name", "").strip()
    distance = request.form.get("distance_km", "")
    race_date = request.form.get("race_date", "") or None
    target_time = request.form.get("target_time", "")

    if not name or not distance:
        return redirect("/training")

    target_sec = None
    if target_time:
        try:
            parts = target_time.split(":")
            if len(parts) == 3:
                target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                target_sec = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            pass

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            add_goal(conn, name, float(distance), race_date, target_sec)
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


@training_crud_bp.route("/training/goal/<int:goal_id>/complete", methods=["POST"])
def goal_complete(goal_id: int):
    """목표 완료."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    from src.training.goals import complete_goal

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            complete_goal(conn, goal_id)
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


@training_crud_bp.route("/training/goal/<int:goal_id>/cancel", methods=["POST"])
def goal_cancel(goal_id: int):
    """목표 취소."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    from src.training.goals import cancel_goal

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            cancel_goal(conn, goal_id)
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


# ── ICS 내보내기 ──────────────────────────────────────────────────────


@training_crud_bp.route("/training/export.ics")
def training_export_ics():
    """주간 훈련 계획을 iCal 형식으로 내보내기."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return Response("No data", status=404)

    week_offset = request.args.get("week", 0, type=int)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            workouts, _ = load_workouts(conn, week_offset)
        finally:
            conn.close()
    except Exception:
        workouts = []

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//RunPulse//Training Plan//KO",
        "CALSCALE:GREGORIAN",
    ]
    for w in workouts:
        wtype = w.get("workout_type", "easy")
        if wtype == "rest":
            continue
        dist = w.get("distance_km")
        d = w.get("date", "").replace("-", "")
        summary = f"RunPulse: {wtype}"
        if dist:
            summary += f" {dist:.1f}km"
        desc = w.get("description", "")
        lines += [
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{d}",
            f"DTEND;VALUE=DATE:{d}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")

    return Response(
        "\r\n".join(lines),
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=runpulse-training.ics"},
    )


# ── Garmin 워크아웃 전송 ──────────────────────────────────────────


@training_crud_bp.route("/training/push-garmin", methods=["POST"])
def push_to_garmin():
    """주간 훈련 계획을 Garmin Connect에 전송."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    from src.training.garmin_push import push_weekly_plan
    from src.utils.config import load_config

    try:
        config = load_config()
        conn = sqlite3.connect(str(dbp))
        try:
            count = push_weekly_plan(config, conn)
        finally:
            conn.close()
        if count > 0:
            return redirect(f"/training?msg=Garmin에 {count}개 워크아웃 전송 완료")
        else:
            return redirect("/training?msg=전송할 워크아웃이 없습니다 (이미 전송되었거나 휴식일)")
    except Exception as exc:
        return redirect(f"/training?msg=Garmin 전송 실패: {str(exc)[:100]}")
