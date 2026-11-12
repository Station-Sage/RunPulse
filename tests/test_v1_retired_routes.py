"""S4-91 (AUDIT-SERVICE-LAYER 2단계, ADR-056) — 퇴역 v1 URL 은 GET 302→v2, POST 410,
유지 라우트(Strava OAuth·Garmin local-sync·/connect/garmin·내보내기 .ics·/mcp·/feeds/cal)는 그대로."""
from __future__ import annotations

import pytest

from src.web.app import create_app
from src.web.v1_retired import RETIRED_GET, RETIRED_POST, gone_response

ORIGIN = {"Origin": "http://localhost"}


@pytest.fixture(scope="module")
def app():
    a = create_app()
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def _rules(app) -> dict[tuple[str, str], str]:
    out = {}
    for r in app.url_map.iter_rules():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            out[(r.rule, m)] = r.endpoint
    return out


@pytest.mark.parametrize("path,target", sorted(RETIRED_GET.items()))
def test_retired_get_redirects_to_v2(client, path, target):
    r = client.get(path + "?msg=old")
    assert r.status_code == 302, path
    assert r.headers["Location"] == target
    assert target.startswith("/v2/")


@pytest.mark.parametrize("path,target", sorted(RETIRED_POST.items()))
def test_retired_post_is_gone(client, path, target):
    r = client.post(path, data={"source": "garmin"}, headers=ORIGIN)
    assert r.status_code == 410, path
    err = r.get_json()["error"]
    assert err["code"] == "GONE" and err["moved_to"] == target


def test_retired_post_without_origin_still_blocked(client):
    assert client.post("/trigger-sync", data={"source": "garmin"}).status_code == 403


def test_gone_response_shape(app):
    with app.test_request_context("/x", method="POST"):
        r = gone_response("/v2/data/sync")
    assert r.status_code == 410
    assert r.get_json() == {"error": {"code": "GONE", "message": "이 기능은 새 화면으로 옮겨졌어요.",
                                      "moved_to": "/v2/data/sync"}}


def test_kept_routes_registered(app):
    rules = _rules(app)
    kept = {
        ("/connect/strava/oauth-start", "GET"): "strava_oauth.",
        ("/connect/strava/callback", "GET"): "strava_oauth.",
        ("/api/garmin/local-sync", "POST"): "garmin_local_sync.",
        ("/connect/garmin", "GET"): "settings_garmin.",
        ("/connect/garmin/cf-settings", "POST"): "settings_garmin.",
        ("/training/export.ics", "GET"): "training_export.",
    }
    for key, prefix in kept.items():
        assert rules[key].startswith(prefix), key
    assert any(r.startswith("/mcp") for r, _ in rules)
    assert any(r.startswith("/feeds/cal/") for r, _ in rules)


def test_no_duplicate_rules(app):
    seen: dict = {}
    for r in app.url_map.iter_rules():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            assert (r.rule, m) not in seen or seen[(r.rule, m)] == r.endpoint
            seen[(r.rule, m)] = r.endpoint


def test_garmin_local_sync_stays_origin_exempt(client):
    """토큰 기반 server-to-server 호출 — Origin 없이도 관문을 통과해야 한다(인증은 라우트 몫)."""
    r = client.post("/api/garmin/local-sync", json={})
    assert "FORBIDDEN_ORIGIN" not in r.get_data(as_text=True)
    assert r.status_code in (400, 401, 500)


def test_smoke_root_v2_and_kept_screens(client):
    assert client.get("/").status_code == 302
    assert client.get("/v2/").status_code in (200, 404)  # 404 = frontend/build 없음
    assert client.get("/connect/garmin").status_code == 200
    assert client.get("/training/export.ics").status_code != 500
