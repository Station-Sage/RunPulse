"""설정 파일(config.json) 로드/저장 유틸리티."""

import json
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"

# 화면에 표시할 때 마스킹할 키 목록
_REDACT_KEYS = {"password", "client_secret", "refresh_token", "access_token", "token", "api_key"}


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


def _resolve_path(path: Path | str | None) -> Path:
    """설정 파일 경로 결정. None이면 기본 경로 반환."""
    if path is None:
        return _CONFIG_PATH
    return Path(path).expanduser().resolve()


def load_config(path: Path | None = None) -> dict:
    """config.json을 읽어서 dict로 반환. 없으면 기본값 반환."""
    config_path = _resolve_path(path)
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


def save_config(config: dict, path: Path | None = None) -> None:
    """config 딕셔너리를 config.json에 저장.

    Args:
        config: 저장할 설정 딕셔너리.
        path: 저장 경로. None이면 기본 경로.
    """
    config_path = _resolve_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_service_config(
    service_name: str,
    updates: dict,
    path: Path | None = None,
) -> dict:
    """특정 서비스 설정 블록을 업데이트하고 저장.

    Args:
        service_name: 서비스 이름 (garmin, strava, intervals, runalyze).
        updates: 업데이트할 키/값 딕셔너리.
        path: 설정 파일 경로. None이면 기본 경로.

    Returns:
        업데이트된 전체 설정 딕셔너리.
    """
    config_path = _resolve_path(path)

    # 기존 파일에서 로드 (없으면 기본값)
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            current = json.load(f)
    else:
        current = _default_config()

    if service_name not in current:
        current[service_name] = {}

    current[service_name].update(updates)
    save_config(current, path)
    return current


def redact_config_for_display(config: dict) -> dict:
    """민감한 값(패스워드, 토큰 등)을 마스킹하여 반환.

    Args:
        config: 원본 설정 딕셔너리.

    Returns:
        민감 값이 마스킹된 새 딕셔너리.
    """
    import copy
    redacted = copy.deepcopy(config)
    for section in redacted.values():
        if isinstance(section, dict):
            for key in list(section.keys()):
                if key in _REDACT_KEYS and section[key]:
                    # 전체 마스킹 (길이 노출도 방지)
                    section[key] = "****"
    return redacted
