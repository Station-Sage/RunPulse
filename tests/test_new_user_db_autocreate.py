"""신규 가입자: 인증된 /api/v1 요청에서 빈 DB 자동 생성, 그 외 경로·미인증은 생성 안 함."""
import pytest

import src.db_setup as dbs
import src.web.app as web_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)
    app = web_app.create_app()
    app.config["TESTING"] = True
    monkeypatch.setattr(web_app, "load_config", lambda user_id=None: {})
    with app.test_client() as c:
        yield c


def _db(tmp_path, uid):
    return tmp_path / "data" / "users" / uid / "running.db"


def test_api_request_creates_empty_db(client, tmp_path):
    with client.session_transaction() as s:
        s["user_id"] = "new@example.com"
    r = client.get("/api/v1/today")
    assert _db(tmp_path, "new@example.com").exists()
    assert r.status_code != 503


def test_non_api_path_does_not_create_db(client, tmp_path):
    with client.session_transaction() as s:
        s["user_id"] = "other@example.com"
    client.get("/nonexistent-page")
    assert not _db(tmp_path, "other@example.com").exists()
