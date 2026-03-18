"""설정 파일(config.json) 로드 유틸리티."""

import json
import sys
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"


def load_config(path: Path | None = None) -> dict:
    """config.json을 읽어서 dict로 반환.

    Args:
        path: 설정 파일 경로. None이면 프로젝트 루트의 config.json 사용.

    Returns:
        설정 딕셔너리.
    """
    config_path = path or _CONFIG_PATH
    if not config_path.exists():
        print(
            f"설정 파일이 없습니다: {config_path}\n"
            "config.json.example을 복사하여 config.json을 생성하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)
