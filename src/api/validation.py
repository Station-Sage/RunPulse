"""라우트 경계 요청 검증 — 선언형 Field + `parse_body`/`parse_args` (SRV 2.2, ADR-048).

외부 의존성 없는 순수 함수. 규칙:
- 형식이 틀리거나 범위 밖이면 조용히 보정하지 않고 `400 INVALID_PARAM` + `details={필드: 이유}`.
- 타입 강제 변환은 손실 없는 경우만: 정수 문자열 "5"·`5.0` → int 허용, `5.5`·`True`·`"5.5"` → int 거부.
  float 은 int/숫자 문자열 허용, `True`·NaN·Infinity 거부.
- 선택 필드는 키가 없거나 `null`·`""` 이면 '없음'으로 보고 `default`(기본 None)를 돌려준다.
  필수 필드가 없으면 400. 스키마에 없는 키는 무시한다(프론트가 보내는 부가 필드 허용).
- `parse_body(require_json=True)`: JSON 이 아닌 Content-Type 은 `415 UNSUPPORTED_MEDIA_TYPE`,
  깨진 JSON·객체가 아닌 JSON 은 `400 INVALID_PARAM`.
- 반환은 `(clean, err)` — 기존 `_reported_km`·`validate_patch` 의 `(clean, err)` 규약과 같다.
  호출부는 `if err: return err`.

`/api/v1/csp-report` 는 `application/csp-report` 로 오므로 이 모듈을 쓰지 않는다(SRV-12).
상수는 `src/services/input_limits.py` 한 곳에서 가져온다.
"""
from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Callable, Iterable

from flask import request

from . import api_error

_INT_RE = re.compile(r"^[+-]?\d{1,18}$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d{1,3})?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ABSENT = object()


class FieldError(ValueError):
    """필드 값이 규칙에 맞지 않을 때 — 메시지가 `details[필드]` 가 된다."""


class Field:
    """한 필드의 파서. `parse(raw)` 는 정규화된 값을 돌려주거나 `FieldError` 를 던진다."""

    def __init__(self, parse: Callable[[Any], Any], *, required: bool = False, default: Any = None):
        self.parse = parse
        self.required = required
        self.default = default


def _num_text(lo, hi, lo_exclusive: bool, unit: str = "") -> str:
    left = "초과" if lo_exclusive else "이상"
    return f"{lo:g}{unit} {left} {hi:g}{unit} 이하"


def int_field(lo: int, hi: int, *, required: bool = False, default: Any = None) -> Field:
    def parse(raw):
        if isinstance(raw, bool):
            raise FieldError("정수여야 합니다")
        if isinstance(raw, int):
            val = raw
        elif isinstance(raw, float):
            if not math.isfinite(raw) or not raw.is_integer():
                raise FieldError("정수여야 합니다")
            val = int(raw)
        elif isinstance(raw, str) and _INT_RE.match(raw.strip()):
            val = int(raw.strip())
        else:
            raise FieldError("정수여야 합니다")
        if not lo <= val <= hi:
            raise FieldError(f"{lo}~{hi} 범위여야 합니다")
        return val

    return Field(parse, required=required, default=default)


def float_field(lo: float, hi: float, *, lo_exclusive: bool = False, required: bool = False,
                default: Any = None) -> Field:
    def parse(raw):
        if isinstance(raw, bool):
            raise FieldError("숫자여야 합니다")
        if isinstance(raw, (int, float)):
            val = float(raw)
        elif isinstance(raw, str) and _FLOAT_RE.match(raw.strip()):
            val = float(raw.strip())
        else:
            raise FieldError("숫자여야 합니다")
        if not math.isfinite(val):
            raise FieldError("숫자여야 합니다")
        below = val <= lo if lo_exclusive else val < lo
        if below or val > hi:
            raise FieldError(f"{_num_text(lo, hi, lo_exclusive)}여야 합니다")
        return val

    return Field(parse, required=required, default=default)


def enum_field(values: Iterable[str], *, required: bool = False, default: Any = None) -> Field:
    allowed = tuple(values)

    def parse(raw):
        if not isinstance(raw, str) or raw not in allowed:
            raise FieldError(f"허용 값 중 하나여야 합니다: {', '.join(allowed)}" if len(allowed) <= 8
                             else "허용되지 않는 값입니다")
        return raw

    return Field(parse, required=required, default=default)


def date_field(min_date: date | Callable[[], date] | None = None,
               max_date: date | Callable[[], date] | None = None, *,
               required: bool = False, default: Any = None) -> Field:
    """`YYYY-MM-DD` 문자열만 허용(Python 3.11 `fromisoformat` 의 느슨한 형식은 거부). 값은 ISO 문자열로 돌려준다."""
    def bound(b):
        return b() if callable(b) else b

    def parse(raw):
        if not isinstance(raw, str) or not _DATE_RE.match(raw.strip()):
            raise FieldError("YYYY-MM-DD 형식의 날짜여야 합니다")
        try:
            val = date.fromisoformat(raw.strip())
        except ValueError:
            raise FieldError("존재하는 날짜여야 합니다") from None
        lo, hi = bound(min_date), bound(max_date)
        if lo is not None and val < lo:
            raise FieldError(f"{lo.isoformat()} 이후여야 합니다")
        if hi is not None and val > hi:
            raise FieldError(f"{hi.isoformat()} 이전이어야 합니다")
        return val.isoformat()

    return Field(parse, required=required, default=default)


def str_field(max_len: int, *, required: bool = False, strip: bool = True, default: Any = None) -> Field:
    """문자열 필드. `strip` 이면 앞뒤 공백을 제거한 길이로 검사하고, 비면 '없음'(선택) 또는 오류(필수)."""
    def parse(raw):
        if not isinstance(raw, str):
            raise FieldError("문자열이어야 합니다")
        val = raw.strip() if strip else raw
        if not val.strip():
            if required:
                raise FieldError("비어 있을 수 없습니다")
            return _ABSENT
        if len(val) > max_len:
            raise FieldError(f"{max_len}자 이하여야 합니다")
        return val

    return Field(parse, required=required, default=default)


def int_list_field(lo: int = 1, hi: int = 2**31 - 1, *, max_items: int = 50, required: bool = False,
                   default: Any = None) -> Field:
    """정수 배열 — 중복은 제거하고 처음 순서를 유지한다(NEW-40 `chat_thread_ids`)."""
    item = int_field(lo, hi)

    def parse(raw):
        if not isinstance(raw, list):
            raise FieldError("배열이어야 합니다")
        if len(raw) > max_items:
            raise FieldError(f"항목은 {max_items}개 이하여야 합니다")
        out: list[int] = []
        for el in raw:
            try:
                val = item.parse(el)
            except FieldError as exc:
                raise FieldError(f"항목 {el!r}: {exc}") from None
            if val not in out:
                out.append(val)
        return out

    return Field(parse, required=required, default=default)


def dict_field(schema: dict[str, Field], *, required: bool = False, default: Any = None) -> Field:
    """중첩 객체 — 하위 오류는 `상위.하위` 키로 합쳐진다. 스키마 밖 키는 버린다."""
    def parse(raw):
        if not isinstance(raw, dict):
            raise FieldError("객체여야 합니다")
        clean, details = _apply(schema, raw)
        if details:
            raise FieldError("; ".join(f"{k}: {v}" for k, v in details.items()))
        return clean

    return Field(parse, required=required, default=default)


def _apply(schema: dict[str, Field], source) -> tuple[dict, dict]:
    clean: dict = {}
    details: dict = {}
    for key, field in schema.items():
        raw = source.get(key, _ABSENT) if hasattr(source, "get") else _ABSENT
        if raw is _ABSENT or raw is None or (isinstance(raw, str) and raw == ""):
            if field.required:
                details[key] = "필수 항목입니다"
            else:
                clean[key] = field.default
            continue
        try:
            val = field.parse(raw)
        except FieldError as exc:
            details[key] = str(exc)
            continue
        if val is _ABSENT:  # 공백뿐인 선택 문자열
            clean[key] = field.default
        else:
            clean[key] = val
    return clean, details


def _invalid(details: dict):
    return api_error("INVALID_PARAM", "요청 값이 올바르지 않습니다.", 400, details)


def parse_body(schema: dict[str, Field], *, require_json: bool = True) -> tuple[dict, Any]:
    """JSON 본문을 스키마로 검증한다. 반환 `(clean, err)` — err 가 있으면 그대로 return 한다."""
    if request.is_json:
        body = request.get_json(silent=True)
        if body is None or not isinstance(body, dict):
            return {}, _invalid({"body": "JSON 객체여야 합니다"})
    elif require_json:
        return {}, api_error("UNSUPPORTED_MEDIA_TYPE", "Content-Type 은 application/json 이어야 합니다.", 415)
    else:
        body = {}
    clean, details = _apply(schema, body)
    return (clean, _invalid(details)) if details else (clean, None)


def parse_args(schema: dict[str, Field]) -> tuple[dict, Any]:
    """GET 쿼리스트링을 스키마로 검증한다(값은 항상 문자열로 오므로 숫자는 문자열 규칙을 따른다)."""
    clean, details = _apply(schema, request.args)
    return (clean, _invalid(details)) if details else (clean, None)
