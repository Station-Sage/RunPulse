"""v1 동기화 JSON·SSE 라우트 — `/trigger-sync*`·`/api/garmin/local-sync`·`/bg-sync/*` (V1S-12 b안).

`app.py` 의 `create_app` 안에 있던 직접 라우트를 **URL·동작 불변**으로 옮겼다(S3 6단계). 삭제하지 않는다 —
v1 UI(`helpers.py` 의 동기화 JS)·로컬 동기화 클라이언트가 이 URL 을 호출한다. 삭제 여부는 v1 일몰 단계에서
별도 결정한다(사용처 조사는 운영 접근이 필요해 미확인). 응답은 `{data}` 봉투가 아닌 기존 `{ok, error}` 형식이다.

`/api/garmin/local-sync` 는 Origin 관문 면제(`request_guard.EXEMPT_PATHS`, body 의 sync_key 인증).
"""
from __future__ import annotations

import logging
import sqlite3

from flask import Blueprint, request

from src.sync.garmin import check_garmin_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.sync.strava import check_strava_connection
from src.utils.config import get_config_path, load_config
from src.utils.user_context import db_path

log = logging.getLogger(__name__)
v1_sync_bp = Blueprint("v1_sync", __name__)
bp = v1_sync_bp


def _days_since_last_sync(sources: list[str]) -> int:
    from src.services.sync_trigger_service import days_since_last_sync
    return days_since_last_sync(db_path(), sources)


def _auto_match_after_sync() -> None:
    """동기화 완료 후 이번 주 + 지난 주 계획↔활동 자동 매칭."""
    from datetime import date as _date, timedelta as _td
    db = db_path()
    if not db.exists():
        return
    try:
        from src.training.matcher import match_week_activities
        today = _date.today()
        this_week = today - _td(days=today.weekday())
        last_week = this_week - _td(weeks=1)
        with sqlite3.connect(str(db)) as conn:
            n_this = match_week_activities(conn, this_week)
            n_last = match_week_activities(conn, last_week)
            conn.commit()
        log.debug("자동 매칭 완료: 이번 주 %d건, 지난 주 %d건", n_this, n_last)
    except Exception:
        log.warning("자동 매칭 실패", exc_info=True)


@bp.post("/trigger-sync")
def trigger_sync():
    """동기화 실행 — 연결 확인 + 정책 검사 + 중복 방지 + JSON 응답."""
    from datetime import date
    from flask import jsonify
    from src.services.manual_sync_service import precheck, run_one

    mode = request.form.get("mode", "basic").strip()
    source = request.form.get("source", "all").strip()
    from_date = request.form.get("from_date", "").strip()
    to_date = request.form.get("to_date", "").strip()
    log.info("[trigger_sync] 요청: mode=%s, source=%s, from=%s, to=%s",
             mode, source, from_date or "-", to_date or "-")

    _VALID_SOURCES = {"garmin", "strava", "intervals", "runalyze"}
    checkers = {
        "garmin": check_garmin_connection,
        "strava": check_strava_connection,
        "intervals": check_intervals_connection,
        "runalyze": check_runalyze_connection,
    }
    if source == "all":
        sources_to_sync = list(checkers.keys())
    else:
        # 콤마 구분 다중 소스 지원
        parts = [s.strip() for s in source.split(",") if s.strip() in _VALID_SOURCES]
        sources_to_sync = parts if parts else list(checkers.keys())
    from src.utils.user_context import get_current_user_id
    user_id = get_current_user_id()
    config = load_config(user_id=user_id)

    # 기간 동기화: days 공통 계산
    hist_days: int | None = None
    if mode in ("historical", "hist") and from_date:
        try:
            d = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date) if to_date else date.today()
            hist_days = max(1, min((end - d).days + 1, 3650))
        except (ValueError, TypeError):
            hist_days = 30

    results = []
    for src in sources_to_sync:
        # 1) 연결 상태 확인
        conn_status = checkers[src](config)
        if not conn_status["ok"]:
            log.info("[trigger_sync] %s 미연결: %s", src, conn_status["status"])
            results.append({
                "source": src, "ok": False, "skipped": True,
                "count": 0, "error": f"미연결 ({conn_status['status']})",
            })
            continue

        # 2) 재시도 대기·정책 검사
        days_for_src, guard, blocked = precheck(src, user_id, hist_days, _days_since_last_sync([src]))
        if blocked:
            log.info("[trigger_sync] %s 건너뜀: %s", src, blocked.get("reason"))
            results.append(blocked)
            continue

        # 3) 원장 선점 + 동기화 실행
        results.append(run_one(src, days_for_src, user_id, guard.message_ko))

    total_count = sum(r.get("count", 0) for r in results)
    overall_ok = any(r.get("ok") for r in results)

    # 동기화 성공 시 이번 주 + 지난 주 계획 자동 매칭
    if overall_ok:
        _auto_match_after_sync()

    return jsonify({"ok": overall_ok, "results": results, "total_count": total_count})


@bp.post("/trigger-sync-stream")
def trigger_sync_stream():
    """동기화 실행 — SSE 스트리밍 응답 (소스별 실시간 진행 상황)."""
    import json as _json
    from datetime import date
    from flask import Response, stream_with_context
    from src.services.manual_sync_service import precheck, run_one

    mode = request.form.get("mode", "basic").strip()
    source = request.form.get("source", "all").strip()
    from_date = request.form.get("from_date", "").strip()
    to_date = request.form.get("to_date", "").strip()
    log.info("[trigger_sync_stream] 요청: mode=%s, source=%s", mode, source)

    _VALID_SOURCES = {"garmin", "strava", "intervals", "runalyze"}
    checkers = {
        "garmin": check_garmin_connection,
        "strava": check_strava_connection,
        "intervals": check_intervals_connection,
        "runalyze": check_runalyze_connection,
    }
    if source == "all":
        sources_to_sync = list(checkers.keys())
    else:
        parts = [s.strip() for s in source.split(",") if s.strip() in _VALID_SOURCES]
        sources_to_sync = parts if parts else list(checkers.keys())

    from src.utils.user_context import get_current_user_id
    user_id = get_current_user_id()
    config = load_config(user_id=user_id)

    hist_days: int | None = None
    if mode in ("historical", "hist") and from_date:
        try:
            d = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date) if to_date else date.today()
            hist_days = max(1, min((end - d).days + 1, 3650))
        except (ValueError, TypeError):
            hist_days = 30

    def _sse(data: dict) -> str:
        return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        results = []
        yield _sse({"type": "start", "sources": sources_to_sync})

        from src.utils.config import enabled_sources as _enabled
        for src in sources_to_sync:
            yield _sse({"type": "source_start", "source": src})
            if src not in _enabled(config):
                yield _sse({"type": "source_done", "source": src, "ok": False, "skipped": True,
                            "count": 0, "reason": "disabled"})
                continue

            conn_status = checkers[src](config)
            if not conn_status["ok"]:
                r = {"source": src, "ok": False, "skipped": True, "count": 0,
                     "error": f"미연결 ({conn_status['status']})"}
                results.append(r)
                yield _sse({"type": "source_done", **r})
                continue

            days_for_src, guard, blocked = precheck(src, user_id, hist_days, _days_since_last_sync([src]))
            if blocked:
                results.append(blocked)
                yield _sse({"type": "source_done", **blocked})
                continue

            r = run_one(src, days_for_src, user_id, guard.message_ko)
            results.append(r)
            yield _sse({"type": "source_done", **r})

        total_count = sum(r.get("count", 0) for r in results)
        overall_ok = any(r.get("ok") for r in results)
        if overall_ok:
            _auto_match_after_sync()
        yield _sse({"type": "done", "ok": overall_ok,
                    "total_count": total_count, "results": results})

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@bp.post("/trigger-sync-bg")
def trigger_sync_bg():
    """기본 동기화 — 백그라운드 실행 후 즉시 JSON 응답 (브라우저 연결 독립)."""
    from datetime import date as _date
    from flask import jsonify
    from src.services.sync_trigger_service import ALL_SOURCES, plan_incremental
    from src.sync.bg_sync import start_basic_sync
    from src.utils.user_context import get_current_user_id

    source = request.form.get("source", "all").strip()
    if source == "all":
        sources_to_sync = list(ALL_SOURCES)
    else:
        sources_to_sync = [s.strip() for s in source.split(",") if s.strip() in ALL_SOURCES]

    user_id = get_current_user_id()
    config = load_config(user_id=user_id)
    today = _date.today()
    started, from_dates, plan_skipped = plan_incremental(
        config, user_id, sources_to_sync, today, db_file=db_path())
    skipped = []
    for sk in plan_skipped:
        item = {"source": sk.provider, "error": sk.message_ko}
        if sk.retry_after_sec is not None:
            item["retry_after_sec"] = sk.retry_after_sec
        skipped.append(item)

    job_ids: dict[str, str] = {}
    if started:
        job_ids = start_basic_sync(started, from_dates, today.isoformat(), config, user_id)

    log.info("[trigger_sync_bg] started=%s, skipped=%s", started, [s["source"] for s in skipped])
    return jsonify({"ok": len(started) > 0, "started": started, "skipped": skipped, "job_ids": job_ids})


@bp.post("/api/garmin/local-sync")
def garmin_local_sync():
    """로컬 기기에서 발급한 Garmin 토큰 수신 후 bg_sync 실행.

    CF Service Token 인증(auth_cf.py)을 통과한 요청만 도달.
    Body JSON: { "token": {...garmin_tokens.json...}, "days": 30, "user_id": "github@email.com" }
    user_id: RunPulse 앱 user_id (GitHub 이메일). CF 서비스 토큰으로 호출 시 필수.
    """
    import json as _json
    from datetime import date as _date, timedelta
    from pathlib import Path
    from flask import jsonify
    from src.sync.bg_sync import start_job
    from src.utils.user_context import get_current_user_id

    import hmac as _hmac
    import os as _os

    data = request.get_json(silent=True) or {}
    log.info("[local-sync] 요청 수신 — keys=%s", list(data.keys()))

    # sync_key 인증 — CF가 서비스 토큰 헤더를 제거하므로 body에서 검증
    sync_key = data.get("sync_key", "")
    _is_prod = _os.environ.get("APP_ENV", "development").lower() == "production"
    root_cfg = load_config(user_id="default")
    expected_key = root_cfg.get("cf", {}).get("service_client_secret", "")
    if expected_key:
        if not sync_key or not _hmac.compare_digest(sync_key, expected_key):
            log.warning("[local-sync] sync_key 인증 실패")
            return jsonify({"error": "sync_key 인증 실패"}), 401
    elif _is_prod:
        return jsonify({"error": "서버 CF 설정이 없습니다. /settings에서 CF Service Token을 설정하세요."}), 500

    token = data.get("token")
    if not isinstance(token, dict) or not token:
        log.warning("[local-sync] token 필드 없음 또는 잘못된 형식")
        return jsonify({"error": "token 필드가 없거나 올바른 형식이 아닙니다."}), 400
    log.info("[local-sync] 토큰 수신 OK — token.keys=%s", list(token.keys())[:6])

    try:
        days = max(1, min(int(data.get("days", 30)), 90))
    except (TypeError, ValueError):
        days = 30

    # CF 서비스 토큰으로 호출 시 body의 user_id 사용 (GitHub 이메일 ≠ Garmin 이메일)
    user_id = data.get("user_id") or get_current_user_id()
    if not user_id:
        log.warning("[local-sync] user_id 없음")
        return jsonify({"error": "user_id 필드가 필요합니다."}), 400
    tokenstore = get_config_path(user_id).parent / ".garminconnect"
    tokenstore.mkdir(parents=True, exist_ok=True)
    log.info("[local-sync] user_id=%s, days=%d, tokenstore=%s", user_id, days, tokenstore)

    try:
        # combined 포맷(garmin_tokens.json)으로 저장 — garth가 OAuth1+OAuth2 모두 로드
        with open(tokenstore / "garmin_tokens.json", "w") as f:
            _json.dump(token, f, indent=2)
        # 구형 garth 호환: 분리 파일도 함께 저장
        _t2 = token.get("oauth2_token")
        if isinstance(_t2, dict):
            with open(tokenstore / "oauth2_token.json", "w") as f:
                _json.dump(_t2, f, indent=2)
            _t1 = token.get("oauth1_token")
            if isinstance(_t1, dict):
                with open(tokenstore / "oauth1_token.json", "w") as f:
                    _json.dump(_t1, f, indent=2)
        else:
            # flat 포맷(구형 garth): oauth2_token.json으로도 저장
            with open(tokenstore / "oauth2_token.json", "w") as f:
                _json.dump(token, f, indent=2)
        log.info("[local-sync] 토큰 파일 저장 완료: %s", tokenstore / "garmin_tokens.json")
    except OSError as e:
        log.error("[local-sync] 토큰 파일 저장 실패: %s", e)
        return jsonify({"error": f"토큰 저장 실패: {e}"}), 500

    from src.utils.config import update_service_config
    update_service_config("garmin", {"tokenstore": str(tokenstore)}, user_id=user_id)

    config = load_config(user_id=user_id)
    from src.utils.config import enabled_sources as _enabled
    if "garmin" not in _enabled(config):
        return jsonify({"status": "token_saved", "job_id": None,
                        "message": "토큰은 저장했어요. Garmin이 동기화 대상에서 꺼져 있어 동기화는 시작하지 않았어요."})
    to_date = _date.today().isoformat()
    from_date = (_date.today() - timedelta(days=days)).isoformat()
    log.info("[local-sync] bg_sync 시작: %s ~ %s", from_date, to_date)
    job_id = start_job("garmin", from_date, to_date, config, user_id=user_id)
    log.info("[local-sync] job_id=%s", job_id)

    return jsonify({
        "status": "sync_started",
        "days": days,
        "job_id": job_id,
        "message": f"토큰 저장 완료. Garmin {days}일 동기화 시작됨.",
    }), 202


@bp.post("/bg-sync/start")
def bg_sync_start():
    """백그라운드 기간 동기화 시작."""
    from datetime import date as _date
    from flask import jsonify
    from src.sync.bg_sync import start_job
    from src.utils.config import enabled_sources
    source = request.form.get("source", "").strip()
    from_date = request.form.get("from_date", "").strip()
    to_date = request.form.get("to_date", "").strip() or _date.today().isoformat()

    if source not in ("garmin", "strava", "intervals", "runalyze"):
        return jsonify({"ok": False, "error": "지원하지 않는 서비스입니다."}), 400
    if not from_date:
        return jsonify({"ok": False, "error": "시작일을 입력하세요."}), 400

    try:
        _date.fromisoformat(from_date)
        _date.fromisoformat(to_date)
    except ValueError:
        return jsonify({"ok": False, "error": "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)."}), 400

    from src.utils.user_context import get_current_user_id
    user_id = get_current_user_id()
    config = load_config(user_id=user_id)
    if source not in enabled_sources(config):
        return jsonify({"ok": False, "error": "동기화 대상에서 꺼져 있어요"}), 409
    job_id = start_job(source, from_date, to_date, config, user_id=user_id)
    return jsonify({"ok": True, "job_id": job_id, "source": source})


@bp.post("/bg-sync/pause")
def bg_sync_pause():
    from flask import jsonify
    from src.sync.bg_sync import pause_job
    source = request.form.get("source", "").strip()
    ok = pause_job(source)
    return jsonify({"ok": ok})


@bp.post("/bg-sync/stop")
def bg_sync_stop():
    from flask import jsonify
    from src.sync.bg_sync import stop_job
    source = request.form.get("source", "").strip()
    ok = stop_job(source)
    return jsonify({"ok": ok})


@bp.post("/bg-sync/resume")
def bg_sync_resume():
    from flask import jsonify
    from src.sync.bg_sync import resume_job
    from src.utils.config import enabled_sources
    from src.utils.user_context import get_current_user_id
    source = request.form.get("source", "").strip()
    user_id = get_current_user_id()
    config = load_config(user_id=user_id)
    if source not in enabled_sources(config):
        return jsonify({"ok": False, "error": "동기화 대상에서 꺼져 있어요"}), 409
    ok = resume_job(source, config, user_id=user_id)
    return jsonify({"ok": ok})


@bp.get("/bg-sync/status")
def bg_sync_status():
    from flask import jsonify
    from src.sync.bg_sync import get_status
    source = request.args.get("source", "").strip()
    if source not in ("garmin", "strava", "intervals", "runalyze"):
        return jsonify({"active": False})
    return jsonify(get_status(source))
