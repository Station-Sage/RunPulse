"""동기화 뒤 AI 다듬기 warm 훅(ADR-059 2단계 표면) — bg_sync 가 부르는 단일 진입점, 전부 백그라운드 스레드.

표면: 지표 해석(`metric_interpretation`, 오늘 날짜). 능동 인사이트 다듬기는 기존 `insight_polish.polish_in_background`
훅을 그대로 쓴다(저장 위치가 insight_events 라서). 예외는 전파하지 않는다(동기화 중단 금지).
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def after_sync(db_path: str, config: dict | None, day: str) -> None:
    """day 기준 지표 해석을 백그라운드로 다듬는다. 동의·큐·사용량 관문은 ai_wording.warm 이 본다."""
    try:
        from src.services import ai_wording as aw
        from src.services import metric_interpretation as mi
        aw.warm_in_background(db_path, config, mi.SURFACE, collect=lambda c: mi.collect(c, day))
    except Exception:  # noqa: BLE001
        log.warning("wording warm hook failed", exc_info=True)
