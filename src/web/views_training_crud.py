"""훈련 계획 — CRUD 라우트 + 목표 관리 + ICS 내보내기.

300줄 규칙 준수를 위해 views_training.py에서 분리.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, Response, jsonify, redirect, request

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


@training_crud_bp.route("/training/workout/<int:workout_id>/confirm", methods=["POST"])
def workout_confirm(workout_id: int):
    """어제 체크인: 훈련 완료 확인."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")
    try:
        conn = sqlite3.connect(str(dbp))
        try:
            # 같은 날 실제 활동 자동 매칭 시도
            row = conn.execute(
                "SELECT date FROM planned_workouts WHERE id=?", (workout_id,)
            ).fetchone()
            if row:
                from src.training.matcher import match_week_activities
                from datetime import date as _date, timedelta as _td
                plan_date = _date.fromisoformat(row[0])
                week_start = plan_date - _td(days=plan_date.weekday())
                match_week_activities(conn, week_start)
            # 매칭 안 됐으면 수동 완료
            conn.execute(
                "UPDATE planned_workouts SET completed=1, updated_at=datetime('now') "
                "WHERE id=? AND completed=0",
                (workout_id,),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    if request.headers.get("Accept") == "application/json":
        return jsonify({"ok": True})
    return redirect("/training?msg=훈련 완료로 기록했습니다.")


@training_crud_bp.route("/training/workout/<int:workout_id>/skip", methods=["POST"])
def workout_skip(workout_id: int):
    """어제 체크인: 훈련 건너뜀 처리 + 재조정 여부 반환."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")
    skip_reason = request.form.get("reason", "")
    result: dict = {}
    msg = "건너뜀 처리 완료"
    try:
        conn = sqlite3.connect(str(dbp))
        try:
            row = conn.execute(
                "SELECT date, distance_km FROM planned_workouts WHERE id=?",
                (workout_id,),
            ).fetchone()
            conn.execute(
                "UPDATE planned_workouts SET completed=-1, skip_reason=?, "
                "updated_at=datetime('now') WHERE id=?",
                (skip_reason or None, workout_id),
            )
            conn.commit()

            # session_outcomes: skipped 기록
            if row:
                from src.training.matcher import save_skipped_outcome
                save_skipped_outcome(conn, workout_id, row[0], row[1])

            # 재조정 자동 실행
            from src.training.replanner import replan_remaining_week
            result = replan_remaining_week(conn, workout_id)
            msg = result.get("message", "건너뜀 처리 완료")
        finally:
            conn.close()
    except Exception:
        pass

    if request.headers.get("Accept") == "application/json":
        return jsonify({
            "ok": True,
            "message": msg,
            "changes": result.get("changes", []),
            "warnings": result.get("warnings", []),
            "moved": result.get("moved", False),
            "target_date": result.get("target_date"),
        })
    return redirect(f"/training?msg={msg}")


@training_crud_bp.route("/training/replan", methods=["POST"])
def training_replan():
    """이번 주 잔여 계획 재조정 (수동 요청)."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")
    skipped_id = request.form.get("skipped_id", type=int)
    if not skipped_id:
        return redirect("/training")
    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.replanner import replan_remaining_week
            result = replan_remaining_week(conn, skipped_id)
            msg = result.get("message", "재조정 완료")
        finally:
            conn.close()
    except Exception as exc:
        msg = f"재조정 실패: {str(exc)[:80]}"
    return redirect(f"/training?msg={msg}")


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


@training_crud_bp.route("/training/push-caldav", methods=["POST"])
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


# ── 훈련 환경 설정 저장 ────────────────────────────────────────────────────

@training_crud_bp.route("/training/prefs", methods=["POST"])
def training_prefs_post():
    """훈련 환경 설정 저장 (휴식 요일, 롱런 요일, 차단 날짜, 인터벌 거리)."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training?msg=DB를 찾을 수 없습니다")

    # 휴식 요일 비트마스크
    rest_mask = 0
    for i in range(7):
        if request.form.get(f"rest_day_{i}"):
            rest_mask |= (1 << i)

    # 롱런 요일 비트마스크
    long_mask = 0
    for i in range(7):
        if request.form.get(f"long_day_{i}"):
            long_mask |= (1 << i)

    # 일회성 차단 날짜
    blocked_raw = request.form.get("blocked_dates", "").strip()
    blocked = [
        d.strip() for d in blocked_raw.split(",")
        if len(d.strip()) == 10 and d.strip()[4] == "-" and d.strip()[7] == "-"
    ] if blocked_raw else []

    # 인터벌 거리
    try:
        rep_m = max(100, min(5000, int(request.form.get("interval_rep_m", 1000))))
    except (ValueError, TypeError):
        rep_m = 1000

    # Q-day 최대 수
    try:
        max_q = max(0, min(4, int(request.form.get("max_q_days", 0))))
    except (ValueError, TypeError):
        max_q = 0

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.planner import upsert_user_training_prefs
            upsert_user_training_prefs(
                conn, rest_mask, blocked, rep_m, max_q, long_mask
            )
        finally:
            conn.close()
    except Exception as exc:
        return redirect(f"/training?msg=설정 저장 오류: {str(exc)[:80]}")

    return redirect("/training?msg=훈련 환경 설정이 저장되었습니다")
