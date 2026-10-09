"""레거시 `<소스>_disabled` 키 마이그레이션과 is_source_enabled."""
import json

from src.utils import config as C


def test_legacy_key_moves_and_disables():
    out = C._migrate_legacy_source_keys({"strava_disabled": {"a": 1}, "sync_sources": ["garmin", "strava"]})
    assert out["strava"] == {"a": 1} and "strava_disabled" not in out and out["sync_sources"] == ["garmin"]


def test_canonical_key_not_overwritten():
    out = C._migrate_legacy_source_keys({"strava": {"a": 1}, "strava_disabled": {"a": 2}})
    assert out["strava"] == {"a": 1} and "strava_disabled" not in out


def test_idempotent_and_default_base_is_all():
    once = C._migrate_legacy_source_keys({"strava_disabled": {"a": 1}})
    assert once["sync_sources"] == ["garmin", "intervals", "runalyze"]
    assert C._migrate_legacy_source_keys(json.loads(json.dumps(once))) == once


def test_load_config_applies_migration(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"intervals_disabled": {"api_key": "x"}}), encoding="utf-8")
    cfg = C.load_config(p)
    assert cfg["intervals"]["api_key"] == "x" and not C.is_source_enabled(cfg, "intervals")
    assert C.is_source_enabled(cfg, "garmin")
