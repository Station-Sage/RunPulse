"""설정 — 메트릭 재계산 라우트 (SSE 스트림 포함).

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import sqlite3
import threading as _threading

from flask import Blueprint, jsonify, redirect, request

from src.web.helpers import db_path

settings_metrics_bp = Blueprint("settings_metrics", __name__)

_recompute_state: dict = {"status": "idle"}
_recompute_lock = _threading.Lock()


def _set_recompute_state(**kwargs) -> None:
    with _recompute_lock:
        _recompute_state.update(kwargs)


@settings_metrics_bp.post("/metrics/recompute")
def metrics_recompute():
    """기존 DB 데이터 기반 2차 메트릭 일괄 재계산 (백그라운드 + SSE 진행)."""
    from src.metrics import engine as metrics_engine

    with _recompute_lock:
        if _recompute_state.get("status") == "running":
            return redirect("/settings?msg=재계산이 이미 진행 중입니다.")

    try:
        days = int(request.form.get("days", 90))
        if days < 0:
            days = 0
    except (ValueError, TypeError):
        days = 90

    import time as _time
    _set_recompute_state(status="running", days=days, completed=0, total=days,
                         current_date="", pct=0, error=None,
                         started_at=_time.time())

    def _on_progress(date_str: str, completed: int, total: int) -> None:
        pct = round(completed / total * 100, 1) if total > 0 else 0
        _set_recompute_state(completed=completed, total=total,
                             current_date=date_str, pct=pct)

    def _run() -> None:
        try:
            with sqlite3.connect(str(db_path())) as conn:
                metrics_engine.recompute_all(conn, days=days, on_progress=_on_progress)
            _set_recompute_state(status="completed", pct=100)
        except Exception as exc:
            _set_recompute_state(status="error", error=str(exc)[:200])

    _threading.Thread(target=_run, daemon=True, name="metrics-recompute").start()
    return redirect("/settings#metrics-section")


@settings_metrics_bp.get("/metrics/recompute-stream")
def metrics_recompute_stream():
    """메트릭 재계산 진행 상황 SSE 스트림."""
    import json
    import time
    from flask import Response, stream_with_context

    def _generate():
        while True:
            with _recompute_lock:
                state = dict(_recompute_state)
            data = json.dumps(state)
            yield f"data: {data}\n\n"
            if state.get("status") in ("completed", "error", "idle"):
                break
            time.sleep(0.8)

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@settings_metrics_bp.get("/metrics/recompute-status")
def metrics_recompute_status():
    """재계산 현재 상태 JSON (폴링 fallback용)."""
    with _recompute_lock:
        return jsonify(dict(_recompute_state))


@settings_metrics_bp.get("/recompute-metrics")
def recompute_metrics_get():
    """동기화 탭에서 호출하는 GET 재계산 엔드포인트 (간단 버전, JSON 응답)."""
    from src.metrics import engine as metrics_engine

    with _recompute_lock:
        if _recompute_state.get("status") == "running":
            return jsonify({"message": "재계산이 이미 진행 중입니다."})

    try:
        days = int(request.args.get("days", 90))
        if days < 0:
            days = 0
    except (ValueError, TypeError):
        days = 90

    import time as _time
    _set_recompute_state(status="running", days=days, completed=0, total=days,
                         current_date="", pct=0, error=None,
                         started_at=_time.time())

    def _run() -> None:
        try:
            with sqlite3.connect(str(db_path())) as conn:
                metrics_engine.recompute_all(conn, days=days)
            _set_recompute_state(status="completed", pct=100)
        except Exception as exc:
            _set_recompute_state(status="error", error=str(exc)[:200])

    _threading.Thread(target=_run, daemon=True, name="metrics-recompute-get").start()
    label = "전체 기간" if days == 0 else f"최근 {days}일"
    return jsonify({"message": f"재계산 시작 ({label}). 백그라운드에서 진행 중..."})
