"""훈련 계획 Wizard — Blueprint + 라우트 (Phase C).

GET  /training/wizard          — Step 1 전체 페이지
POST /training/wizard/step     — step별 AJAX (JSON: {step, html})
POST /training/wizard/complete — 목표+설정 저장 + 플랜 생성 → redirect
"""
from __future__ import annotations

import json
import sqlite3

from flask import Blueprint, jsonify, redirect, request

from src.web.helpers import db_path

wizard_bp = Blueprint("training_wizard", __name__)

_DIST_KM: dict[str, float] = {
    "1.5k": 1.5, "3k": 3.0, "5k": 5.0,
    "10k": 10.0, "half": 21.097, "full": 42.195,
}


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────


def _parse_time(s: str) -> int | None:
    """H:MM:SS 또는 MM:SS → 초."""
    if not s:
        return None
    try:
        parts = s.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _dist_km(label: str, custom: str) -> float:
    """거리 레이블 → km."""
    if label == "custom":
        try:
            return max(1.0, float(custom))
        except (ValueError, TypeError):
            return 10.0
    return _DIST_KM.get(label, 10.0)


def _collect_mask(prefix: str) -> int:
    """form에서 요일 체크박스 비트마스크 수집."""
    mask = 0
    for i in range(7):
        if request.form.get(f"{prefix}{i}"):
            mask |= (1 << i)
    return mask


def _load_wizard_data() -> dict:
    """hidden wizard_data JSON 파싱. 실패 시 빈 dict."""
    raw = request.form.get("wizard_data", "{}")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


# ── 라우트 ─────────────────────────────────────────────────────────────


@wizard_bp.route("/training/wizard")
def wizard_page():
    """Step 1 전체 페이지. ?mode=edit&goal_id=N 이면 기존 목표 pre-populate."""
    from src.web.views_training_wizard_render import render_wizard_page

    mode = request.args.get("mode", "create")
    goal_id = request.args.get("goal_id", type=int)
    data: dict = {}

    if mode == "edit" and goal_id:
        dbp = db_path()
        if dbp and dbp.exists():
            try:
                with sqlite3.connect(str(dbp)) as conn:
                    from src.training.goals import get_goal
                    g = get_goal(conn, goal_id)
                    if g:
                        data = _goal_to_wizard_data(g)
            except Exception:
                pass
        data["_mode"] = "edit"
        data["_goal_id"] = goal_id

    return render_wizard_page(step=1, data=data, mode=mode, goal_id=goal_id)


@wizard_bp.route("/training/wizard/step", methods=["POST"])
def wizard_step():
    """AJAX step 처리. Returns JSON {step, html}."""
    step = request.form.get("step", type=int)

    if step == 1:
        return _handle_step1()
    if step == 2:
        return _handle_step2()
    if step == 3:
        return _handle_step3()
    return jsonify({"error": "unknown step"}), 400


@wizard_bp.route("/training/wizard/complete", methods=["POST"])
def wizard_complete():
    """목표 + 환경설정 저장 + 이번 주 플랜 생성."""
    data = _load_wizard_data()
    if not data:
        return redirect("/training?msg=위저드 데이터 오류")

    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training?msg=DB를 찾을 수 없습니다")

    is_edit = data.get("_mode") == "edit" and data.get("_goal_id")
    # 체크박스 값은 form 필드로 별도 전달됨 (wizard_data에 없음)
    if is_edit and request.form.get("_regen_plan_val") == "1":
        data["_regen_plan"] = True

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            if is_edit:
                count = _update_and_maybe_regen(conn, data)
                msg = f"목표가 수정되었습니다"
                if count > 0:
                    msg += f" (플랜 재생성: {count}개 워크아웃)"
            else:
                count = _save_and_generate(conn, data)
                msg = f"훈련 계획이 생성되었습니다 ({count}개 워크아웃)"
        finally:
            conn.close()
    except Exception as exc:
        return redirect(f"/training?msg=저장 실패: {str(exc)[:80]}")

    return redirect(f"/training?msg={msg}")


# ── step 핸들러 ────────────────────────────────────────────────────────


def _handle_step1():
    """Step 1 입력 검증 → Step 2 HTML 반환."""
    from src.training.readiness import get_recommended_weeks
    from src.web.views_training_wizard_render import render_step2

    label = request.form.get("distance_label", "10k")
    custom = request.form.get("custom_km", "")
    race_date = request.form.get("race_date", "")
    target_time = request.form.get("target_time", "")
    target_pace = request.form.get("target_pace", "")
    goal_name = request.form.get("goal_name", "").strip()

    dist = _dist_km(label, custom)
    time_sec = _parse_time(target_time)
    pace_sec = _parse_time(target_pace)
    if not time_sec and pace_sec and dist > 0:
        time_sec = int(pace_sec * dist)

    rec = get_recommended_weeks(dist)
    data = {
        "goal_name": goal_name,
        "distance_label": label,
        "custom_km": custom,
        "dist_km": dist,
        "race_date": race_date,
        "target_time": target_time,
        "time_sec": time_sec,
        "target_pace": target_pace,
        "pace_sec": pace_sec,
    }
    return jsonify({"step": 2, "html": render_step2(data, rec)})


def _handle_step2():
    """Step 2 입력 수집 + readiness 분석 → Step 3 HTML 반환."""
    from src.training.readiness import analyze_readiness, get_recommended_weeks
    from src.web.views_training_wizard_render import render_step3

    data = _load_wizard_data()
    rest_mask = _collect_mask("rest_day_")
    long_mask = _collect_mask("long_day_")
    blocked_raw = request.form.get("blocked_dates", "").strip()
    blocked = (
        [d.strip() for d in blocked_raw.split(",") if len(d.strip()) == 10]
        if blocked_raw else []
    )
    try:
        rep_m = max(100, min(5000, int(request.form.get("interval_rep_m", 1000))))
    except (ValueError, TypeError):
        rep_m = 1000
    try:
        plan_weeks = max(1, min(52, int(request.form.get("plan_weeks", 12))))
    except (ValueError, TypeError):
        plan_weeks = 12

    data.update({
        "rest_mask": rest_mask, "long_mask": long_mask,
        "blocked": blocked, "interval_rep_m": rep_m, "plan_weeks": plan_weeks,
    })

    readiness: dict = {}
    dbp = db_path()
    if dbp and dbp.exists() and data.get("dist_km") and data.get("time_sec"):
        try:
            with sqlite3.connect(str(dbp)) as conn:
                readiness = analyze_readiness(
                    conn, data["dist_km"], data["time_sec"], plan_weeks
                )
            data["current_vdot"] = readiness.get("current_vdot")
        except Exception:
            pass

    if not readiness:
        # DB 없어도 추천 기간은 제공
        rec = get_recommended_weeks(data.get("dist_km", 10.0))
        readiness = {
            "recommended_weeks": rec,
            "status_summary": "VDOT 데이터가 없습니다. 동기화 후 정확한 분석이 가능합니다.",
            "warnings": ["VDOT 데이터가 없습니다 — 동기화 후 재분석하세요."],
        }

    return jsonify({"step": 3, "html": render_step3(data, readiness)})


def _handle_step3():
    """Step 3 확인 → Step 4 HTML 반환."""
    from src.web.views_training_wizard_render import render_step4
    data = _load_wizard_data()
    mode = "edit" if data.get("_mode") == "edit" else "create"
    return jsonify({"step": 4, "html": render_step4(data, mode=mode)})


# ── 유틸 ───────────────────────────────────────────────────────────────


def _fmt_time_hms(sec: int | None) -> str:
    """초 → H:MM:SS 문자열. None 이면 빈 문자열."""
    if not sec:
        return ""
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _fmt_pace_mmss(sec: int | None) -> str:
    """초/km → MM:SS 문자열. None 이면 빈 문자열."""
    if not sec:
        return ""
    return f"{sec // 60}:{sec % 60:02d}"


def _goal_to_wizard_data(g: dict) -> dict:
    """goals DB 행 → wizard_data dict (Step 1 pre-populate용)."""
    dist = g.get("distance_km", 10.0)
    # distance_label 추정
    label_map = {1.5: "1.5k", 3.0: "3k", 5.0: "5k",
                 10.0: "10k", 21.097: "half", 42.195: "full"}
    label = next((k for k, v in {
        "1.5k": 1.5, "3k": 3.0, "5k": 5.0,
        "10k": 10.0, "half": 21.097, "full": 42.195,
    }.items() if abs(v - dist) < 0.01), "custom")
    return {
        "goal_name": g.get("name", ""),
        "distance_label": label,
        "custom_km": "" if label != "custom" else str(dist),
        "dist_km": dist,
        "race_date": g.get("race_date") or "",
        "target_time": _fmt_time_hms(g.get("target_time_sec")),
        "time_sec": g.get("target_time_sec"),
        "target_pace": _fmt_pace_mmss(g.get("target_pace_sec_km")),
        "pace_sec": g.get("target_pace_sec_km"),
        "plan_weeks": g.get("plan_weeks"),
    }


# ── 저장 + 플랜 생성 ───────────────────────────────────────────────────


def _update_and_maybe_regen(conn: sqlite3.Connection, data: dict) -> int:
    """edit 모드: 목표 필드 업데이트 + 선택적 플랜 재생성. 재생성된 워크아웃 수 반환."""
    from datetime import date, timedelta

    from src.training.goals import update_goal
    from src.training.planner import (
        generate_weekly_plan, save_weekly_plan, upsert_user_training_prefs,
    )

    goal_id = int(data["_goal_id"])
    update_goal(
        conn,
        goal_id,
        name=data.get("goal_name", ""),
        distance_km=data.get("dist_km", 10.0),
        race_date=data.get("race_date") or None,
        target_time_sec=data.get("time_sec"),
        target_pace_sec_km=data.get("pace_sec"),
    )
    if data.get("plan_weeks"):
        conn.execute(
            "UPDATE goals SET plan_weeks=? WHERE id=?",
            (int(data["plan_weeks"]), goal_id),
        )
    conn.commit()

    upsert_user_training_prefs(
        conn,
        data.get("rest_mask", 0),
        data.get("blocked", []),
        data.get("interval_rep_m", 1000),
        0,
        data.get("long_mask", 0),
    )

    if not data.get("_regen_plan"):
        return 0

    # 재생성: 현재 주 이후 기존 planner 워크아웃 삭제 후 전체 기간 재생성
    today = date.today()
    current_week = today - timedelta(days=today.weekday())
    conn.execute(
        "DELETE FROM planned_workouts WHERE source='planner' AND date >= ?",
        (current_week.isoformat(),),
    )
    conn.commit()

    race_date_str = data.get("race_date")
    plan_weeks = data.get("plan_weeks")
    if race_date_str:
        try:
            end_date = date.fromisoformat(race_date_str) + timedelta(days=7)
        except ValueError:
            end_date = current_week + timedelta(weeks=int(plan_weeks or 12))
    else:
        end_date = current_week + timedelta(weeks=int(plan_weeks or 12))
    # 레이스 날짜가 과거여도 최소 1주는 생성
    end_date = max(end_date, current_week + timedelta(weeks=1))

    total_count = 0
    ws = current_week
    while ws < end_date:
        plan = generate_weekly_plan(conn, goal_id=goal_id, week_start=ws)
        total_count += save_weekly_plan(conn, plan)
        ws += timedelta(weeks=1)
    return total_count


def _save_and_generate(conn: sqlite3.Connection, data: dict) -> int:
    """goals + prefs 저장 후 전체 기간 플랜 생성. 생성된 워크아웃 수 반환."""
    from datetime import date, timedelta

    from src.training.goals import add_goal
    from src.training.planner import (
        generate_weekly_plan, save_weekly_plan, upsert_user_training_prefs,
    )

    goal_id = add_goal(
        conn,
        data.get("goal_name", "훈련 목표"),
        data.get("dist_km", 10.0),
        data.get("race_date") or None,
        data.get("time_sec"),
        data.get("pace_sec"),
    )

    plan_weeks = data.get("plan_weeks")
    if plan_weeks:
        conn.execute(
            "UPDATE goals SET plan_weeks=? WHERE id=?",
            (int(plan_weeks), goal_id),
        )
    conn.commit()

    upsert_user_training_prefs(
        conn,
        data.get("rest_mask", 0),
        data.get("blocked", []),
        data.get("interval_rep_m", 1000),
        0,
        data.get("long_mask", 0),
    )

    # 전체 기간 플랜 생성: race_date 또는 plan_weeks 기반
    today = date.today()
    current_week = today - timedelta(days=today.weekday())

    race_date_str = data.get("race_date")
    if race_date_str:
        try:
            end_date = date.fromisoformat(race_date_str) + timedelta(days=7)
        except ValueError:
            end_date = current_week + timedelta(weeks=int(plan_weeks or 12))
    else:
        end_date = current_week + timedelta(weeks=int(plan_weeks or 12))
    # 최소 1주 보장
    end_date = max(end_date, current_week + timedelta(weeks=1))

    total_count = 0
    ws = current_week
    while ws < end_date:
        plan = generate_weekly_plan(conn, goal_id=goal_id, week_start=ws)
        total_count += save_weekly_plan(conn, plan)
        ws += timedelta(weeks=1)
    return total_count
