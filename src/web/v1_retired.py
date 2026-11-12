"""퇴역한 v1 화면·동작 URL — GET 은 v2 대응 화면으로 302, POST 는 410 (AUDIT-SERVICE-LAYER 2단계, ADR-056).

외부 북마크·오래된 링크가 404 로 끝나지 않게 URL 만 남긴다. 화면·동작 코드는 S4-91 에서 삭제했다.
- GET: `RETIRED_GET` 의 v2 경로로 302(쿼리스트링은 버린다 — v1 전용 `msg`·`error` 였다).
- POST: 410 `{error:{code:"GONE", message, moved_to}}` — 폼 재전송·스크립트가 조용히 성공한 것처럼 보이지 않게.
  POST 도 Origin 관문(request_guard)을 먼저 지나므로 Origin 없는 요청은 403 이다.
유지(여기 없음): `/connect/garmin*`(views_settings_garmin — CF 설정 폼의 v2 대체 없음), Strava OAuth
`/connect/strava/oauth-start`·`/callback`(views_strava_oauth), `/api/garmin/local-sync`(routes_garmin_local_sync).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect

v1_retired_bp = Blueprint("v1_retired", __name__)

_DATA_SYNC = "/v2/data/sync"
_DATA_IMPORT = "/v2/data/import"

# 퇴역 GET URL → v2 대응 화면
RETIRED_GET: dict[str, str] = {
    "/connect/strava": "/v2/data/sources/strava",
    "/connect/intervals": "/v2/data/sources/intervals",
    "/connect/runalyze": "/v2/data/sources/runalyze",
    "/import": _DATA_IMPORT,
    "/import-preview": _DATA_IMPORT,
    "/sync-status": _DATA_SYNC,
    "/bg-sync/status": _DATA_SYNC,
    "/activities/export.csv": "/v2/data/export",
}

# 퇴역 POST URL → 안내용 v2 화면(moved_to)
RETIRED_POST: dict[str, str] = {
    "/connect/strava/save-app": "/v2/data/sources/strava",
    "/connect/strava/disconnect": "/v2/data/sources/strava",
    "/connect/intervals": "/v2/data/sources/intervals",
    "/connect/intervals/disconnect": "/v2/data/sources/intervals",
    "/connect/runalyze": "/v2/data/sources/runalyze",
    "/connect/runalyze/disconnect": "/v2/data/sources/runalyze",
    "/import/upload": _DATA_IMPORT,
    "/import/upload-archive": _DATA_IMPORT,
    "/trigger-sync": _DATA_SYNC,
    "/trigger-sync-stream": _DATA_SYNC,
    "/trigger-sync-bg": _DATA_SYNC,
    "/bg-sync/start": _DATA_SYNC,
    "/bg-sync/pause": _DATA_SYNC,
    "/bg-sync/stop": _DATA_SYNC,
    "/bg-sync/resume": _DATA_SYNC,
}


def gone_response(moved_to: str):
    """퇴역 POST 응답 — 410 + API 오류 봉투."""
    resp = jsonify({"error": {
        "code": "GONE",
        "message": "이 기능은 새 화면으로 옮겨졌어요.",
        "moved_to": moved_to,
    }})
    resp.status_code = 410
    return resp


def _redirect_view(target: str):
    return lambda: redirect(target, code=302)


def _gone_view(target: str):
    return lambda: gone_response(target)


for _i, (_path, _target) in enumerate(RETIRED_GET.items()):
    v1_retired_bp.add_url_rule(_path, f"get_{_i}", _redirect_view(_target), methods=["GET"])
for _i, (_path, _target) in enumerate(RETIRED_POST.items()):
    v1_retired_bp.add_url_rule(_path, f"post_{_i}", _gone_view(_target), methods=["POST"])
