"""훈련 목표 관리 CRUD 라우트 (goal_create/complete/cancel/detail/import).

views_training_crud.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html
from datetime import date as _date, timedelta as _td

from flask import Blueprint, Response, jsonify, redirect, request

from src.web.helpers import db_path

training_goal_crud_bp = Blueprint("training_goal_crud", __name__)


# ── 목표 기본 CRUD ─────────────────────────────────────────────────────


@training_goal_crud_bp.route("/training/goal", methods=["POST"])
def goal_create():
    """목표 추가."""
    import sqlite3
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


@training_goal_crud_bp.route("/training/goal/<int:goal_id>/complete", methods=["POST"])
def goal_complete(goal_id: int):
    """목표 완료."""
    import sqlite3
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


@training_goal_crud_bp.route("/training/goal/<int:goal_id>/cancel", methods=["POST"])
def goal_cancel(goal_id: int):
    """목표 취소. AJAX(Accept: application/json) → JSON, 일반 → redirect."""
    import sqlite3
    dbp = db_path()
    is_ajax = "application/json" in request.headers.get("Accept", "")
    if not dbp or not dbp.exists():
        return jsonify({"ok": False, "error": "DB 없음"}) if is_ajax else redirect("/training")

    from src.training.goals import cancel_goal

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            cancel_goal(conn, goal_id)
        finally:
            conn.close()
        if is_ajax:
            return jsonify({"ok": True})
    except Exception as exc:
        if is_ajax:
            return jsonify({"ok": False, "error": str(exc)})

    return redirect("/training")


# ── G-2: 목표 드릴다운 ────────────────────────────────────────────────


@training_goal_crud_bp.route("/training/goal/<int:goal_id>/detail")
def goal_detail(goal_id: int):
    """목표 드릴다운 HTML partial (AJAX용)."""
    import sqlite3
    dbp = db_path()
    if not dbp or not dbp.exists():
        return Response("DB 없음", status=404)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.goals import get_goal
            from src.web.views_training_loaders import load_goal_weeks, load_goals_with_stats
            from src.web.views_training_goals import render_goal_detail_html

            goal = get_goal(conn, goal_id)
            if not goal:
                return Response("목표를 찾을 수 없습니다.", status=404)
            weeks = load_goal_weeks(conn, goal)
            all_goals = load_goals_with_stats(conn)
        finally:
            conn.close()
    except Exception as exc:
        return Response(f"오류: {exc}", status=500)

    html = render_goal_detail_html(goal, weeks, all_goals)
    return Response(html, status=200, mimetype="text/html")


# ── G-4: 가져오기 미리보기 / 실행 ────────────────────────────────────────


@training_goal_crud_bp.route("/training/goal/<int:goal_id>/import-preview")
def goal_import_preview(goal_id: int):
    """가져오기 미리보기 HTML partial.

    Query params:
        src: 소스 goal_id
        start: 새 시작일 (YYYY-MM-DD)
        range: all | date | period
        src_date: 특정일 (date 범위용)
        src_from / src_to: 기간 (period 범위용)
    """
    import sqlite3
    dbp = db_path()
    if not dbp or not dbp.exists():
        return Response("DB 없음", status=404)

    src_id = request.args.get("src", type=int)
    new_start = request.args.get("start", "")
    range_type = request.args.get("range", "all")
    src_date = request.args.get("src_date", "")
    src_from = request.args.get("src_from", "")
    src_to = request.args.get("src_to", "")

    if not new_start:
        return Response("시작일 필요", status=400)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.goals import get_goal
            from src.web.views_training_loaders import _goal_date_range

            src_goal = get_goal(conn, src_id) if src_id else None
            if not src_goal:
                return Response(
                    "<p style='color:#ff6b6b;font-size:12px;'>소스 목표를 찾을 수 없습니다.</p>",
                    status=200, mimetype="text/html",
                )

            g_start, g_end = _goal_date_range(src_goal)
            if range_type == "date" and src_date:
                q_start, q_end = src_date, src_date
            elif range_type == "period" and src_from and src_to:
                q_start, q_end = src_from, src_to
            else:
                q_start, q_end = g_start, g_end

            rows = conn.execute(
                """SELECT date, workout_type, distance_km, target_pace_min, target_pace_max
                   FROM planned_workouts
                   WHERE date >= ? AND date <= ? AND workout_type != 'rest'
                   ORDER BY date""",
                (q_start, q_end),
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        return Response(
            f"<p style='color:#ff6b6b;font-size:12px;'>오류: {exc}</p>",
            status=200, mimetype="text/html",
        )

    if not rows:
        html = "<p style='color:var(--muted);font-size:12px;'>해당 범위에 워크아웃이 없습니다.</p>"
        return Response(html, status=200, mimetype="text/html")

    from src.web.helpers import fmt_pace

    try:
        src_first = _date.fromisoformat(rows[0][0])
        new_first = _date.fromisoformat(new_start)
        offset = (new_first - src_first).days
    except ValueError:
        offset = 0

    _TYPE_KO = {
        "easy": "이지런", "tempo": "템포런", "interval": "인터벌",
        "long": "롱런", "recovery": "회복조깅", "race": "레이스",
    }
    table_rows = ""
    for r in rows:
        orig = r[0]
        try:
            new_d = (_date.fromisoformat(orig) + _td(days=offset)).isoformat()
        except ValueError:
            new_d = orig
        wtype = r[1]
        dist = f"{r[2]:.1f}km" if r[2] else "—"
        pace = ""
        if r[3] and r[4]:
            pace = f"{fmt_pace(r[3])}~{fmt_pace(r[4])}"
        elif r[3]:
            pace = fmt_pace(r[3])
        table_rows += (
            f"<tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>"
            f"<td style='padding:3px 8px;font-size:11px;color:var(--muted);'>{orig}</td>"
            f"<td style='padding:3px 8px;font-size:11px;color:#00d4ff;'>→ {new_d}</td>"
            f"<td style='padding:3px 8px;font-size:11px;'>"
            f"{_TYPE_KO.get(wtype, wtype)}</td>"
            f"<td style='padding:3px 8px;font-size:11px;'>{dist}</td>"
            f"<td style='padding:3px 8px;font-size:11px;color:var(--muted);'>{pace}</td>"
            f"</tr>"
        )

    html = (
        f"<div style='font-size:11px;color:var(--muted);margin-bottom:6px;'>"
        f"총 {len(rows)}개 워크아웃 · 오프셋 {offset:+d}일</div>"
        "<div style='overflow-x:auto;max-height:200px;overflow-y:auto;'>"
        "<table style='width:100%;border-collapse:collapse;font-size:11px;'>"
        "<thead><tr>"
        + "".join(
            f"<th style='padding:3px 8px;text-align:left;font-size:10px;"
            f"color:var(--muted);font-weight:500;white-space:nowrap;'>{h}</th>"
            for h in ["원본일", "새날짜", "종류", "거리", "페이스"]
        )
        + "</tr></thead><tbody>"
        + table_rows
        + "</tbody></table></div>"
    )
    return Response(html, status=200, mimetype="text/html")


@training_goal_crud_bp.route("/training/goal/<int:goal_id>/import", methods=["POST"])
def goal_import(goal_id: int):
    """훈련 가져오기 실행 (워크아웃 복사)."""
    import sqlite3
    dbp = db_path()
    if not dbp or not dbp.exists():
        return jsonify({"ok": False, "error": "DB 없음"})

    data = request.get_json(silent=True) or {}
    src_id = data.get("src")
    new_start = data.get("start", "")
    range_type = data.get("range", "all")
    src_date = data.get("src_date", "")
    src_from = data.get("src_from", "")
    src_to = data.get("src_to", "")

    if not new_start:
        return jsonify({"ok": False, "error": "시작일 필요"})

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.goals import get_goal
            from src.web.views_training_loaders import _goal_date_range

            src_goal = get_goal(conn, int(src_id)) if src_id else None
            if not src_goal:
                return jsonify({"ok": False, "error": "소스 목표 없음"})

            g_start, g_end = _goal_date_range(src_goal)
            if range_type == "date" and src_date:
                q_start, q_end = src_date, src_date
            elif range_type == "period" and src_from and src_to:
                q_start, q_end = src_from, src_to
            else:
                q_start, q_end = g_start, g_end

            rows = conn.execute(
                """SELECT date, workout_type, distance_km,
                          target_pace_min, target_pace_max, description, rationale
                   FROM planned_workouts
                   WHERE date >= ? AND date <= ? AND workout_type != 'rest'
                   ORDER BY date""",
                (q_start, q_end),
            ).fetchall()

            if not rows:
                return jsonify({"ok": False, "error": "해당 범위에 워크아웃 없음"})

            src_first = _date.fromisoformat(rows[0][0])
            new_first = _date.fromisoformat(new_start)
            offset = (new_first - src_first).days

            count = 0
            for r in rows:
                new_d = (_date.fromisoformat(r[0]) + _td(days=offset)).isoformat()
                conn.execute(
                    """INSERT INTO planned_workouts
                       (date, workout_type, distance_km,
                        target_pace_min, target_pace_max,
                        description, rationale, completed, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'imported')""",
                    (new_d, r[1], r[2], r[3], r[4], r[5], r[6]),
                )
                count += 1
            conn.commit()
        finally:
            conn.close()
        return jsonify({"ok": True, "count": count})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})
