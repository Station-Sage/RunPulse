"""컨텍스트 신호 수집(illness·travel·altitude) — 신선도·재확인·창 경계."""
import json

import pytest

from src.services import adjustment_signals as S
from src.services import adjustment_signals_context as C
from tests.helpers_pred import mem_conn


@pytest.fixture
def c():
    return mem_conn()


def _ep(c, kind, start, end=None, sev=None, detail=None, last=None):
    c.execute("INSERT INTO context_episodes(kind,start_date,end_date,severity,detail_json,origin,status,last_confirmed_date)"
              " VALUES(?,?,?,?,?,'user','confirmed',?)", (kind, start, end, sev, json.dumps(detail or {}), last))


def test_illness_freshness_and_reconfirm(c):
    _ep(c, "illness", "2026-10-01", sev=2, last="2026-10-10")
    f = lambda d: C.collect_illness(c, d)[0]
    assert f("2026-10-10")["freshness"] == "fresh"
    assert f("2026-10-12")["freshness"] == "partial"
    assert f("2026-10-13")["freshness"] == "stale" and not f("2026-10-13")["detail"]["reconfirm"]
    assert f("2026-10-16")["detail"]["reconfirm"] is False
    assert f("2026-10-17")["detail"]["reconfirm"] is True and f("2026-10-17")["value"] == 2


def test_illness_return_context_boundary(c):
    _ep(c, "illness", "2026-10-01", end="2026-10-05", sev=1)
    assert C.collect_illness(c, "2026-10-12")[0]["role"] == "context"
    x = C.collect_illness(c, "2026-10-13")[0]
    assert x["value"] is False and x["role"] is None


def test_travel_windows(c):
    _ep(c, "travel", "2026-10-01", end="2026-10-05", detail={"delta_h": 8, "direction": "east"})
    f = lambda d: C.collect_travel(c, d)
    assert C.travel_window_days(8) == 6 and C.return_window_days(6) == 3
    assert f("2026-10-04")[0]["role"] == "hold" and f("2026-10-04")[0]["detail"]["phase"] == "depart"
    assert f("2026-10-05")[0]["detail"]["phase"] == "return"
    assert f("2026-10-07")[0]["detail"]["phase"] == "return"
    assert f("2026-10-08")[0]["role"] == "context"
    assert f("2026-10-09") == []


def test_travel_departure_window_expires(c):
    _ep(c, "travel", "2026-10-01", detail={"delta_h": 4})
    assert C.travel_window_days(4) == 4
    assert C.collect_travel(c, "2026-10-04") and C.collect_travel(c, "2026-10-05") == []


def test_altitude_adapt_and_return(c):
    _ep(c, "altitude", "2026-10-01", end="2026-10-10", detail={"band": "mid", "altitude_m": 2000})
    f = lambda d: C.collect_altitude(c, d)
    assert f("2026-10-05")[0]["role"] == "hold" and f("2026-10-06") == []
    assert f("2026-10-10")[0]["detail"]["phase"] == "return" and f("2026-10-13")[0]["role"] == "context"
    assert f("2026-10-14") == []


def test_collect_wires_illness_trigger(c):
    _ep(c, "illness", "2026-10-15", sev=1, last="2026-10-15")
    sigs = S.collect(c, "2026-10-15", readiness={"fatigue_level": 0}, crs=None, hold={"hold": False})
    assert S.evaluate(sigs)["source"] == "illness"
