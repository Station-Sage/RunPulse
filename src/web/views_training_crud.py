"""훈련 계획 — 워크아웃 CRUD 라우트 + 환경설정.

목표 CRUD → views_training_goal_crud.py
내보내기/전송 → views_training_export.py
"""
from __future__ import annotations

import sqlite3
from datetime import date

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
    """어제 체크인: 훈련 완료 확인. JSON 모드에서 matched + activity_summary 반환."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    matched = False
    activity_summary = ""
    try:
        conn = sqlite3.connect(str(dbp))
        try:
            row = conn.execute(
                "SELECT date, workout_type, distance_km FROM planned_workouts WHERE id=?",
                (workout_id,),
            ).fetchone()
            if row:
                from src.training.matcher import match_week_activities
                from datetime import date as _date, timedelta as _td
                plan_date = _date.fromisoformat(row[0])
                week_start = plan_date - _td(days=plan_date.weekday())
                match_week_activities(conn, week_start)

                # 매칭 결과 확인: matched_activity_id가 채워졌으면 성공
                m_row = conn.execute(
                    "SELECT matched_activity_id FROM planned_workouts WHERE id=?",
                    (workout_id,),
                ).fetchone()
                if m_row and m_row[0]:
                    matched = True
                    # 실제 활동 요약 (거리 + 페이스)
                    act = conn.execute(
                        "SELECT distance_km, avg_pace_sec_km FROM activity_summaries WHERE id=?",
                        (m_row[0],),
                    ).fetchone()
                    if act and act[0]:
                        summary_parts = [f"{act[0]:.1f}km"]
                        if act[1]:
                            m, s = divmod(int(act[1]), 60)
                            summary_parts.append(f"{m}:{s:02d}/km")
                        activity_summary = " · ".join(summary_parts)

            # 매칭 여부 무관하게 수동 완료 표시
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
        return jsonify({
            "ok": True,
            "matched": matched,
            "activity_summary": activity_summary,
        })
    return redirect("/training?msg=훈련 완료로 기록했습니다.")


@training_crud_bp.route("/training/workout/<int:workout_id>/match-check", methods=["GET"])
def workout_match_check(workout_id: int):
    """매칭 상태 폴링용 — matched 여부 + activity_summary 반환 (JSON)."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return jsonify({"ok": False, "matched": False}), 404

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            row = conn.execute(
                "SELECT matched_activity_id FROM planned_workouts WHERE id=?",
                (workout_id,),
            ).fetchone()
            if not row:
                return jsonify({"ok": False, "matched": False, "error": "없음"}), 404

            activity_id = row[0]
            matched = bool(activity_id)
            activity_summary = ""
            if matched:
                act = conn.execute(
                    "SELECT distance_km, avg_pace_sec_km FROM activity_summaries WHERE id=?",
                    (activity_id,),
                ).fetchone()
                if act and act[0]:
                    parts = [f"{act[0]:.1f}km"]
                    if act[1]:
                        m, s = divmod(int(act[1]), 60)
                        parts.append(f"{m}:{s:02d}/km")
                    activity_summary = " · ".join(parts)
        finally:
            conn.close()
    except Exception as exc:
        return jsonify({"ok": False, "matched": False, "error": str(exc)[:80]}), 500

    return jsonify({"ok": True, "matched": matched, "activity_summary": activity_summary})


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
    """워크아웃 완료 상태 토글. Accept: application/json → JSON 반환."""
    dbp = db_path()
    is_ajax = request.headers.get("Accept") == "application/json"
    if not dbp or not dbp.exists():
        return jsonify({"ok": False, "error": "DB 없음"}) if is_ajax else redirect("/training")

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

    if is_ajax:
        return jsonify({"ok": True})
    week = request.form.get("week", "0")
    return redirect(f"/training?week={week}")


# ── 훈련 환경 설정 저장 ────────────────────────────────────────────────────

@training_crud_bp.route("/training/workout/<int:workout_id>", methods=["PATCH"])
def workout_patch(workout_id: int):
    """워크아웃 AJAX 편집 (JSON 반환).

    인터벌 타입이고 interval_rep_m이 있으면 interval_calc 처방을 description에 저장.
    """
    dbp = db_path()
    if not dbp or not dbp.exists():
        return jsonify({"ok": False, "error": "DB 없음"}), 404

    data = request.get_json(silent=True) or {}
    workout_type = data.get("workout_type")
    distance = data.get("distance_km")
    pace_min = data.get("target_pace_min")
    pace_max = data.get("target_pace_max")
    interval_rep_m = data.get("interval_rep_m")

    # 인터벌 처방 계산
    description: str | None = None
    if workout_type == "interval" and interval_rep_m:
        try:
            from src.training.interval_calc import prescribe_interval
            i_pace = int(pace_min) if pace_min else 240
            rx = prescribe_interval(int(interval_rep_m), i_pace)
            description = rx["rationale"]
        except Exception:
            pass

    fields: list[str] = []
    values: list = []
    if workout_type is not None:
        fields.append("workout_type=?")
        values.append(workout_type)
    if distance is not None:
        fields.append("distance_km=?")
        values.append(float(distance) if distance != "" else None)
    if pace_min is not None:
        fields.append("target_pace_min=?")
        values.append(int(pace_min) if pace_min != "" else None)
    if pace_max is not None:
        fields.append("target_pace_max=?")
        values.append(int(pace_max) if pace_max != "" else None)
    if description is not None:
        fields.append("description=?")
        values.append(description)
    if not fields:
        return jsonify({"ok": False, "error": "변경 없음"}), 400

    fields.append("updated_at=datetime('now')")
    values.append(workout_id)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute(
                f"UPDATE planned_workouts SET {','.join(fields)} WHERE id=?",
                values,
            )
            conn.commit()
            row = conn.execute(
                "SELECT workout_type, distance_km, target_pace_min, target_pace_max, description "
                "FROM planned_workouts WHERE id=?",
                (workout_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:100]}), 500

    result: dict = {"ok": True}
    if row:
        result.update({
            "workout_type": row[0],
            "distance_km": row[1],
            "target_pace_min": row[2],
            "target_pace_max": row[3],
            "description": row[4],
        })
    return jsonify(result)


@training_crud_bp.route(
    "/training/workout/<int:workout_id>/interval-calc", methods=["GET"]
)
def workout_interval_calc(workout_id: int):
    """인터벌 처방 미리보기 (JSON).

    Query params: rep_m (int, 기본 1000), pace (int 초/km, 기본 240)
    """
    try:
        rep_m = request.args.get("rep_m", 1000, type=int)
        pace = request.args.get("pace", 240, type=int)
        from src.training.interval_calc import prescribe_interval
        rx = prescribe_interval(rep_m, pace)
        return jsonify({"ok": True, **rx})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:100]}), 400


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
