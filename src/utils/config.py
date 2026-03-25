"""설정 파일(config.json) 로드/저장 유틸리티."""

import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.json"


def get_config_path(user_id: str | None = None) -> Path:
    """사용자별 config.json 경로. None이면 프로젝트 루트 config.json."""
    if user_id and user_id != "default":
        user_dir = _PROJECT_ROOT / "data" / "users" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "config.json"
    return _CONFIG_PATH

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
        "mapbox": {},
    }


def _resolve_path(path: Path | str | None) -> Path:
    """설정 파일 경로 결정. None이면 기본 경로 반환."""
    if path is None:
        return _CONFIG_PATH
    return Path(path).expanduser().resolve()


def _auto_user_id(user_id: str | None) -> str | None:
    """user_id 미지정 시 Flask 세션에서 자동 추출."""
    if user_id is not None:
        return user_id
    try:
        from src.web.helpers import get_current_user_id
        return get_current_user_id()
    except (ImportError, RuntimeError):
        return None


def load_config(path: Path | None = None, *, user_id: str | None = None) -> dict:
    """config.json을 읽어서 dict로 반환. 없으면 기본값 반환.

    user_id가 지정되면 사용자별 config를 로드.
    path가 명시되면 path 우선.
    Web 컨텍스트에서 둘 다 미지정이면 Flask 세션 user_id 자동 사용.
    """
    if path is not None:
        config_path = _resolve_path(path)
    else:
        config_path = get_config_path(_auto_user_id(user_id))
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


def save_config(
    config: dict, path: Path | None = None, *, user_id: str | None = None
) -> None:
    """config 딕셔너리를 config.json에 저장."""
    if path is not None:
        config_path = _resolve_path(path)
    else:
        config_path = get_config_path(_auto_user_id(user_id))
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_service_config(
    service_name: str,
    updates: dict,
    path: Path | None = None,
    *,
    user_id: str | None = None,
) -> dict:
    """특정 서비스 설정 블록을 업데이트하고 저장."""
    config_path = _resolve_path(path) if path else get_config_path(_auto_user_id(user_id))

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            current = json.load(f)
    else:
        current = _default_config()

    if service_name not in current:
        current[service_name] = {}

    current[service_name].update(updates)
    save_config(current, config_path)
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
