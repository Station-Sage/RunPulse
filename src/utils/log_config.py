"""로깅 중앙 설정 — 모든 진입점에서 setup_logging() 한 번 호출."""
from __future__ import annotations

import logging
import logging.config
import os


def setup_logging(level: str | None = None, *, stderr: bool = False) -> None:
    """dictConfig 기반 통합 로깅 설정.

    Args:
        level: 로그 레벨 (기본: LOG_LEVEL 환경변수 → INFO 순으로 fallback)
        stderr: True이면 stderr 출력 (MCP 서버 전용 — stdout이 프로토콜 스트림인 경우)
    """
    log_level = level or os.environ.get("LOG_LEVEL", "INFO")
    stream = "ext://sys.stderr" if stderr else "ext://sys.stdout"
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": stream,
                "formatter": "standard",
            }
        },
        "root": {"level": log_level, "handlers": ["console"]},
        "loggers": {
            # 200 OK 폴링 스팸 억제 — WARNING 이상만 출력
            "werkzeug": {"level": "WARNING", "propagate": True},
        },
    })
