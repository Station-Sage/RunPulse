"""PWA 인프라 테스트 — manifest, service worker, 오프라인 폴백, 메타 태그."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.web.app import create_app


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


class TestStaticFiles:
    """정적 파일 서빙."""

    def test_manifest_json(self, app_client):
        resp = app_client.get("/static/manifest.json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["short_name"] == "RunPulse"
        assert data["display"] == "standalone"
        assert data["theme_color"] == "#1a1a2e"
        assert len(data["icons"]) >= 4

    def test_service_worker(self, app_client):
        resp = app_client.get("/static/sw.js")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "CACHE_VERSION" in text
        assert "cacheFirst" in text
        assert "networkFirstHtml" in text

    def test_offline_html(self, app_client):
        resp = app_client.get("/static/offline.html")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "오프라인" in html
        assert "다시 시도" in html

    def test_icon_192(self, app_client):
        resp = app_client.get("/static/icons/icon-192.png")
        assert resp.status_code == 200
        assert resp.content_type == "image/png"

    def test_icon_512(self, app_client):
        resp = app_client.get("/static/icons/icon-512.png")
        assert resp.status_code == 200

    def test_icon_maskable(self, app_client):
        resp = app_client.get("/static/icons/icon-192-maskable.png")
        assert resp.status_code == 200


class TestPwaMetaTags:
    """HTML 페이지에 PWA 메타 태그 포함 확인."""

    def test_html_page_has_manifest(self, app_client):
        resp = app_client.get("/dashboard")
        html = resp.data.decode()
        assert 'rel="manifest"' in html
        assert "/static/manifest.json" in html

    def test_html_page_has_theme_color(self, app_client):
        resp = app_client.get("/dashboard")
        html = resp.data.decode()
        assert 'name="theme-color"' in html
        assert "#1a1a2e" in html

    def test_html_page_has_apple_meta(self, app_client):
        resp = app_client.get("/dashboard")
        html = resp.data.decode()
        assert "apple-mobile-web-app-capable" in html
        assert "apple-touch-icon" in html

    def test_html_page_has_sw_registration(self, app_client):
        resp = app_client.get("/dashboard")
        html = resp.data.decode()
        assert "serviceWorker" in html
        assert "/static/sw.js" in html

    def test_html_page_has_favicon(self, app_client):
        resp = app_client.get("/dashboard")
        html = resp.data.decode()
        assert 'rel="icon"' in html
        assert "icon-192.png" in html


class TestManifestIntegrity:
    """manifest.json 유효성."""

    def test_icons_have_required_fields(self, app_client):
        resp = app_client.get("/static/manifest.json")
        data = json.loads(resp.data)
        for icon in data["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon
            assert "purpose" in icon

    def test_icons_are_accessible(self, app_client):
        resp = app_client.get("/static/manifest.json")
        data = json.loads(resp.data)
        for icon in data["icons"]:
            icon_resp = app_client.get(icon["src"])
            assert icon_resp.status_code == 200, f"Icon {icon['src']} not found"

    def test_start_url(self, app_client):
        resp = app_client.get("/static/manifest.json")
        data = json.loads(resp.data)
        assert data["start_url"] == "/dashboard"

    def test_background_matches_theme(self, app_client):
        resp = app_client.get("/static/manifest.json")
        data = json.loads(resp.data)
        assert data["background_color"] == data["theme_color"]
