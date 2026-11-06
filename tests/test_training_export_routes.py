"""v1 훈련 내보내기 블루프린트 — ICS 만 남고 push-garmin/push-caldav 는 제거됐다 (S4-70)."""
from __future__ import annotations

from flask import Flask

from src.web.views_training_export import training_export_bp


def test_only_ics_route_remains():
    app = Flask(__name__)
    app.register_blueprint(training_export_bp)
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/training/export.ics" in rules
    assert "/training/push-garmin" not in rules
    assert "/training/push-caldav" not in rules
