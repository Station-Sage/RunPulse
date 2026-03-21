from __future__ import annotations

import json
from pathlib import Path


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


def fixture_path(*parts: str) -> Path:
    return FIXTURES_ROOT.joinpath(*parts)


def read_text_fixture(*parts: str, encoding: str = "utf-8") -> str:
    return fixture_path(*parts).read_text(encoding=encoding)


def read_json_fixture(*parts: str):
    return json.loads(read_text_fixture(*parts))
