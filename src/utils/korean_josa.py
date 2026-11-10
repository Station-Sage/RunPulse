"""한국어 조사 선택 — 받침 유무로 '이/가'·'은/는'을 고른다('이(가)' 템플릿 노출 방지, M-31)."""
from __future__ import annotations

import re

_PAREN_TAIL = re.compile(r"\s*\([^)]*\)\s*$")
# 영문·숫자로 끝나는 말의 받침 근사(읽는 소리 기준): 1·3·6·7·8·0, L·M·N·R 은 받침 있음
_LATIN_FINAL = set("136780lmnr")


def has_final(word: str) -> bool | None:
    """마지막 글자에 받침이 있으면 True, 없으면 False, 판단 불가면 None. 끝의 '(약어)'는 무시한다."""
    w = _PAREN_TAIL.sub("", word or "").strip()
    if not w:
        return None
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isascii() and ch.isalnum():
        return ch.lower() in _LATIN_FINAL
    return None


def josa(word: str, with_final: str, without_final: str) -> str:
    """word + 알맞은 조사. 판단 불가면 '이(가)' 형태로 둘 다 붙인다."""
    f = has_final(word)
    if f is None:
        return f"{word}{with_final}({without_final})"
    return f"{word}{with_final if f else without_final}"
