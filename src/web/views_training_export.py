"""훈련 계획 내보내기/전송 라우트 (ICS, Garmin, CalDAV).

views_training_crud.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import sqlite3

from flask import Blueprint, Response, redirect, request

from src.web.helpers import db_path
from src.web.views_training_loaders import load_workouts

training_export_bp = Blueprint("training_export", __name__)


@training_export_bp.route("/training/export.ics")
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


@training_export_bp.route("/training/push-garmin", methods=["POST"])
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


@training_export_bp.route("/training/push-caldav", methods=["POST"])
def push_to_caldav():
    """주간 훈련 계획을 CalDAV 캘린더에 전송."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    from src.training.caldav_push import push_weekly_plan_to_caldav
    from src.utils.config import load_config

    try:
        config = load_config()
        if not config.get("caldav", {}).get("url"):
            return redirect("/training?msg=CalDAV 설정이 필요합니다. 설정 페이지에서 입력하세요.")
        conn = sqlite3.connect(str(dbp))
        try:
            count = push_weekly_plan_to_caldav(config, conn)
        finally:
            conn.close()
        if count > 0:
            return redirect(f"/training?msg=캘린더에 {count}개 워크아웃 등록 완료")
        else:
            return redirect("/training?msg=등록할 워크아웃이 없습니다")
    except Exception as exc:
        return redirect(f"/training?msg=캘린더 등록 실패: {str(exc)[:100]}")
