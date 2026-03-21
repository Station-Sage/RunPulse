"""AI 코치 브리핑 프롬프트 조립."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"


def _load_template(name: str) -> str:
    """템플릿 파일 로드. 파일 없으면 플레이스홀더 반환."""
    path = _TEMPLATE_DIR / f"{name}.txt"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"[템플릿 파일 없음: {name}.txt]\n\n{{{{CONTEXT}}}}"


def build_briefing_prompt(conn: sqlite3.Connection, config: dict | None = None) -> str:
    """일일 AI 코치 브리핑 프롬프트 조립.

    briefing.txt 템플릿에 오늘 분석 컨텍스트를 주입하여 반환.
    AI 채팅(Genspark 등)에 그대로 붙여넣을 수 있는 완성 프롬프트.

    Args:
        conn: SQLite 연결.
        config: 설정 dict. None이면 내부에서 load_config() 호출.

    Returns:
        완성 프롬프트 문자열.
    """
    from .ai_context import build_context, format_context_text

    ctx = build_context(conn)
    ctx_text = format_context_text(ctx)
    template = _load_template("briefing")
    return template.replace("{{CONTEXT}}", ctx_text)


def build_chip_prompt(
    conn: sqlite3.Connection,
    chip_id: str,
    config: dict | None = None,
) -> str:
    """추천 칩 ID에 대응하는 전용 프롬프트 조립.

    칩 ID → CHIP_REGISTRY → template 이름 → <template>.txt 로드.
    today_deep 칩은 오늘 활동 상세 컨텍스트를 추가로 주입.

    Args:
        conn: SQLite 연결.
        chip_id: CHIP_REGISTRY 키 (예: 'today_deep', 'weekly_plan').
        config: 설정 dict.

    Returns:
        완성 프롬프트 문자열.
    """
    from .ai_context import build_context, format_activity_context, format_context_text
    from .suggestions import CHIP_REGISTRY

    chip_info = CHIP_REGISTRY.get(chip_id)
    if not chip_info:
        return f"[알 수 없는 칩 ID: {chip_id}]"

    template_name = chip_info.get("template") or chip_id
    template = _load_template(template_name)

    ctx = build_context(conn)
    ctx_text = format_context_text(ctx)

    # today_deep: 오늘 활동 상세 컨텍스트 추가
    extra = ""
    if chip_id == "today_deep":
        act = ctx.get("today_activity")
        if act and act.get("id"):
            try:
                extra = "\n\n" + format_activity_context(conn, int(act["id"]))
            except Exception:
                pass

    return template.replace("{{CONTEXT}}", ctx_text + extra)


def get_clipboard_prompt(
    conn: sqlite3.Connection,
    mode: str = "briefing",
    chip_id: str | None = None,
) -> str:
    """클립보드 복사용 프롬프트 반환.

    Args:
        conn: SQLite 연결.
        mode: 'briefing' | 'chip'.
        chip_id: mode='chip'일 때 필요.

    Returns:
        프롬프트 문자열.
    """
    if mode == "chip" and chip_id:
        return build_chip_prompt(conn, chip_id)
    return build_briefing_prompt(conn)
