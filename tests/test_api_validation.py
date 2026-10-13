"""tests/test_api_validation.py — src/api/validation.py Field·parse_body·parse_args (SRV 2.2, ADR-048)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from flask import Flask

from src.api.validation import (
    FieldError, date_field, dict_field, enum_field, float_field, int_field, int_list_field,
    parse_args, parse_body, str_field,
)


def _ok(field, raw):
    return field.parse(raw)


def _bad(field, raw):
    with pytest.raises(FieldError):
        field.parse(raw)


# ── int_field ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [(1, 1), (10, 10), ("5", 5), (" 7 ", 7), (5.0, 5)])
def test_int_accepts_lossless(raw, expected):
    assert _ok(int_field(1, 10), raw) == expected


@pytest.mark.parametrize("raw", [0, 11, -1, 5.5, "5.5", "x", "", True, False, [], {}, float("nan"), float("inf"),
                                 "1e3", "99999999999999999999"])
def test_int_rejects(raw):
    _bad(int_field(1, 10), raw)


# ── float_field ──────────────────────────────────────────────────────────────

def test_float_exclusive_lower_bound():
    f = float_field(0, 250, lo_exclusive=True)
    _bad(f, 0)
    _bad(f, 250.01)
    assert _ok(f, 250) == 250.0
    assert _ok(f, "0.1") == 0.1
    assert _ok(f, 42) == 42.0


def test_float_inclusive_lower_bound():
    assert _ok(float_field(0, 5), 0) == 0.0


@pytest.mark.parametrize("raw", ["abc", True, None, float("nan"), float("inf"), "nan", "inf", "1e999", [], "--1"])
def test_float_rejects(raw):
    _bad(float_field(0, 250, lo_exclusive=True), raw)


# ── enum / str / date ────────────────────────────────────────────────────────

def test_enum_field():
    f = enum_field(("a", "b"))
    assert _ok(f, "a") == "a"
    for raw in ("c", 1, None, ["a"]):
        _bad(f, raw)


def test_str_field_limits_and_strip():
    f = str_field(5)
    assert _ok(f, "  abc  ") == "abc"
    assert _ok(f, "12345") == "12345"
    _bad(f, "123456")
    _bad(f, 123)
    _bad(f, ["a"])
    assert str_field(5, required=True).parse("ab") == "ab"
    _bad(str_field(5, required=True), "   ")


def test_date_field_strict_format_and_bounds():
    today = date.today()
    f = date_field(min_date=today, max_date=today + timedelta(days=10))
    assert _ok(f, today.isoformat()) == today.isoformat()   # 오늘은 통과
    _bad(f, (today - timedelta(days=1)).isoformat())
    _bad(f, (today + timedelta(days=11)).isoformat())
    for raw in ("garbage", "2026-13-40", "2026-1-1", "20261001", 20261001, "2026-10-01T00:00", None):
        _bad(f, raw)


def test_date_field_callable_bounds_evaluated_each_time():
    calls = []
    f = date_field(min_date=lambda: (calls.append(1), date(2000, 1, 1))[1])
    _ok(f, "2001-01-01")
    _ok(f, "2002-01-01")
    assert len(calls) == 2


# ── int_list_field / dict_field ──────────────────────────────────────────────

def test_int_list_dedupes_keeps_order():
    assert _ok(int_list_field(), [3, 1, 3, "2", 1]) == [3, 1, 2]
    assert _ok(int_list_field(), []) == []


@pytest.mark.parametrize("raw", ["1,2", [1, "x"], [0], [True], [1.5], list(range(1, 60))])
def test_int_list_rejects(raw):
    _bad(int_list_field(), raw)


def test_dict_field_nested():
    f = dict_field({"kind": str_field(5), "ref": str_field(5)})
    assert _ok(f, {"kind": "a", "ref": " b ", "extra": 1}) == {"kind": "a", "ref": "b"}
    with pytest.raises(FieldError, match="ref"):
        f.parse({"kind": "a", "ref": "toolong"})
    _bad(f, "x")


# ── parse_body / parse_args ──────────────────────────────────────────────────

@pytest.fixture
def app():
    app = Flask(__name__)
    from src.api import api_bp  # noqa: F401  (api_error 가 jsonify 만 쓰므로 앱만 있으면 됨)
    return app


SCHEMA = {
    "n": int_field(1, 10, required=True),
    "s": str_field(3),
    "d": float_field(0, 1, default=0.5),
}


def test_parse_body_ok_and_defaults(app):
    with app.test_request_context("/x", method="POST", json={"n": "4", "extra": "ignored"}):
        clean, err = parse_body(SCHEMA)
    assert err is None
    assert clean == {"n": 4, "s": None, "d": 0.5}


def test_parse_body_null_and_empty_string_mean_absent(app):
    with app.test_request_context("/x", method="POST", json={"n": 3, "s": "", "d": None}):
        clean, err = parse_body(SCHEMA)
    assert err is None and clean["s"] is None and clean["d"] == 0.5


def test_parse_body_details_shape(app):
    with app.test_request_context("/x", method="POST", json={"n": 99, "s": "toolong", "d": "x"}):
        _, err = parse_body(SCHEMA)
    resp, status = err
    body = resp.get_json()
    assert status == 400
    assert body["error"]["code"] == "INVALID_PARAM"
    assert set(body["error"]["details"]) == {"n", "s", "d"}


def test_parse_body_missing_required(app):
    with app.test_request_context("/x", method="POST", json={}):
        _, err = parse_body(SCHEMA)
    assert err[1] == 400 and err[0].get_json()["error"]["details"] == {"n": "필수 항목입니다"}


def test_parse_body_non_json_is_415(app):
    with app.test_request_context("/x", method="POST", data="n=1", content_type="text/plain"):
        _, err = parse_body(SCHEMA)
    assert err[1] == 415 and err[0].get_json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_parse_body_no_content_type_is_415(app):
    with app.test_request_context("/x", method="POST"):
        _, err = parse_body(SCHEMA)
    assert err[1] == 415


def test_parse_body_require_json_false_allows_empty(app):
    with app.test_request_context("/x", method="DELETE"):
        clean, err = parse_body({"s": str_field(3)}, require_json=False)
    assert err is None and clean == {"s": None}


def test_parse_body_broken_json_is_400(app):
    with app.test_request_context("/x", method="POST", data="{not json", content_type="application/json"):
        _, err = parse_body(SCHEMA)
    assert err[1] == 400 and err[0].get_json()["error"]["details"] == {"body": "JSON 객체여야 합니다"}


@pytest.mark.parametrize("payload", ["[1,2]", "3", '"str"', "null"])
def test_parse_body_non_object_json_is_400(app, payload):
    with app.test_request_context("/x", method="POST", data=payload, content_type="application/json"):
        _, err = parse_body(SCHEMA)
    assert err[1] == 400


def test_parse_args(app):
    with app.test_request_context("/x?n=3&s=ab"):
        clean, err = parse_args({"n": int_field(1, 5, required=True), "s": str_field(3)})
    assert err is None and clean == {"n": 3, "s": "ab"}
    with app.test_request_context("/x?n=9"):
        _, err = parse_args({"n": int_field(1, 5, required=True)})
    assert err[1] == 400
    with app.test_request_context("/x"):
        _, err = parse_args({"n": int_field(1, 5, required=True)})
    assert err[0].get_json()["error"]["details"] == {"n": "필수 항목입니다"}
