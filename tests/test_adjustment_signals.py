"""조정 신호 수집(adjustment_signals, _race) 단위 테스트."""
import sqlite3

from src.db_setup import create_tables
from src.services import adjustment_signals as A
from src.services.adjustment_signals_race import collect_race, phase_of

D = "2026-10-08"


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _race(c, rdate, prio="A", adapt="adapt", taper=None, rec=None, status="planned"):
    c.execute("INSERT INTO race_calendar(name,race_date,distance_km,priority,adapt_choice,taper_days,recovery_days,status)"
              " VALUES ('r',?,42.195,?,?,?,?,?)", (rdate, prio, adapt, taper, rec, status))


def test_phase_of_windows():
    assert phase_of(0, "A", None, None) == "race_day"
    assert phase_of(14, "A", None, None) == "taper" and phase_of(15, "A", None, None) == "pre_taper"
    assert phase_of(7, "B", None, None) == "taper" and phase_of(8, "B", None, None) == "pre_taper"
    assert phase_of(-7, "A", None, None) == "recovery" and phase_of(-8, "A", None, None) is None
    assert phase_of(-4, "B", None, None) == "recovery" and phase_of(-5, "B", None, None) is None
    assert phase_of(10, "C", 12, None) == "taper"


def test_collect_race_filters():
    c = _conn()
    assert collect_race(c, D) is None
    _race(c, "2026-10-15", "B")
    s = collect_race(c, D)
    assert s["value"] == 7 and s["detail"]["phase"] == "taper" and s["detail"]["unplanned"] is False
    c2 = _conn()
    _race(c2, "2026-10-15", "B", adapt="no_adapt")
    assert collect_race(c2, D) is None
    c3 = _conn()
    _race(c3, "2026-10-05", "A", adapt="unasked", status="done")
    s = collect_race(c3, D)
    assert s["detail"]["phase"] == "recovery" and s["detail"]["unplanned"] is True


def test_collect_isolates_failures_and_reads_db():
    c = _conn()
    c.execute("INSERT INTO user_inputs(input_date,input_type,fatigue,pain) VALUES (?, 'checkin', 8, 'none')", (D,))
    c.execute("INSERT INTO metric_store(scope_type,scope_id,metric_name,numeric_value,is_primary,provider)"
              " VALUES ('daily',?,'acwr',1.6,1,'runpulse:formula_v1')", (D,))
    s = {x["signal"]: x for x in A.collect(c, D, readiness={"fatigue_level": "low", "tsb": 1.0},
                                           crs={"level": 1, "level_label": "x", "crs": 40.0},
                                           hold={"hold": False, "reasons": []})}
    assert s["checkin_fatigue"]["value"] == 8 and s["acwr"]["value"] == 1.6 and s["acwr"]["freshness"] == "fresh"
    assert s["crs"]["value"] == 1 and s["boost_hold"]["role"] == "hold"
    assert s["illness"]["value"] is False and s["pain"]["value"] is False
    ev = A.evaluate(list(s.values()))
    assert ev["triggers"] == ["crs", "acwr", "checkin_fatigue"] and ev["source"] == "checkin"
    assert ev["intensity"] == "reduce"


def test_collect_missing_when_collector_raises():
    c = sqlite3.connect(":memory:")
    out = A.collect(c, D, readiness={"fatigue_level": "low"}, crs={"level": 3}, hold={"hold": False})
    names = {x["signal"]: x["freshness"] for x in out}
    assert names["acwr"] == "missing" or names["acwr"] == "error"
    assert A.evaluate(out)["triggers"] == []


def test_evaluate_no_trigger():
    ev = A.evaluate([{"signal": "crs", "value": 3, "freshness": "fresh"}])
    assert ev["source"] is None and ev["intensity"] is None
