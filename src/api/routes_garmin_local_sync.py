"""Garmin 로컬 동기화 수신 — `POST /api/garmin/local-sync` (외부 클라이언트 `scripts/garmin_local_sync.py`).

v1 동기화 라우트 모듈(routes_v1_sync)에서 이 엔드포인트만 남겼다(S4-91, ADR-056) — `/trigger-sync*`·`/bg-sync/*` 는
`src/web/v1_retired.py`(410)로 퇴역. URL·응답(`{status, job_id}`/`{error}`)은 불변이다.
Origin 관문 면제(`request_guard.EXEMPT_PATHS`)·CF 인증 우회(`auth_cf`)·공개 경로(`auth.public_paths`) — body 의 sync_key 로 인증.
"""
from __future__ import annotations

import logging

from flask import Blueprint, request

from src.utils.config import get_config_path, load_config

log = logging.getLogger(__name__)
garmin_local_sync_bp = Blueprint("garmin_local_sync", __name__)
bp = garmin_local_sync_bp


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
    from src.ops.activity import touch as _touch_activity
    _touch_activity(user_id)  # 활동 신호(휴면 판정)
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
