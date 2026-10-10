"""v1 부작용 GET /recompute-metrics 퇴역 — 라우트 부재와 동기화 탭의 v2 POST 전환."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.web.views_settings_metrics import settings_metrics_bp


def test_get_recompute_route_removed():
    app = Flask(__name__)
    app.register_blueprint(settings_metrics_bp)
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/recompute-metrics" not in rules
    assert "/metrics/recompute-status" in rules


def test_sync_tab_uses_v2_recompute_post():
    src = Path("src/web/views_sync.py").read_text(encoding="utf-8")
    assert "/api/v1/data/recompute" in src
    assert "/recompute-metrics" not in src
