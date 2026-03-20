"""설정 파일(config.json) 로드 유틸리티."""

import json
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"


def _default_config() -> dict:
    """기본 설정값."""
    return {
        "user": {
            "max_hr": 190,
            "threshold_pace": 300,
            "weekly_distance_target": 40.0,
            "hr_zones": {},
        },
        "ai": {
            "default_provider": "manual",
            "prompt_language": "ko",
        },
        "garmin": {},
        "strava": {},
        "intervals": {},
        "runalyze": {},
    }


def load_config(path: Path | None = None) -> dict:
    """config.json을 읽어서 dict로 반환. 없으면 기본값 반환."""
    config_path = path or _CONFIG_PATH
    base = _default_config()

    if not config_path.exists():
        return base

    with open(config_path, encoding="utf-8") as f:
        loaded = json.load(f)

    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value

    return base
