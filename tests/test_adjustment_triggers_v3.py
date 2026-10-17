"""adjuster_v3 트리거 판정(순수 함수) 단위 테스트."""
from src.services import adjustment_triggers_v3 as T


def S(name, value, fresh="fresh"):
    return {"signal": name, "value": value, "freshness": fresh}


def test_standalone_triggers():
    assert T.triggered([S("pain", True)]) == ["pain"]
    assert T.triggered([S("checkin_pain", "moderate")]) == ["checkin_pain"]
    assert T.triggered([S("checkin_pain", "mild")]) == []
    assert T.triggered([S("illness", True)]) == ["illness"]


def test_and_needs_two_members():
    assert T.triggered([S("crs", 1)]) == []
    assert T.triggered([S("acwr", 1.6)]) == []
    assert T.triggered([S("crs", 1), S("acwr", 1.6)]) == ["crs", "acwr"]
    assert T.triggered([S("acwr", 1.4), S("checkin_fatigue", 8)]) == []
    assert T.triggered([S("checkin_fatigue", 7), S("crs", 0)]) == ["crs", "checkin_fatigue"]


def test_missing_signal_ignored():
    assert T.triggered([S("crs", 0, "missing"), S("acwr", 2.0)]) == []


def test_intensity():
    assert T.intensity([S("pain", True)], ["pain"]) == "rest"
    assert T.intensity([S("checkin_pain", "severe")], ["checkin_pain"]) == "rest"
    assert T.intensity([S("checkin_pain", "moderate")], ["checkin_pain"]) == "reduce"
    sg = [S("crs", 0), S("acwr", 1.6)]
    assert T.intensity(sg, ["crs", "acwr"]) == "rest"
    sg = [S("crs", 1), S("acwr", 1.9)]
    assert T.intensity(sg, ["crs", "acwr"]) == "easy_replace"
    sg = [S("crs", 1), S("acwr", 1.6)]
    assert T.intensity(sg, ["crs", "acwr"]) == "reduce"


def test_primary_order():
    assert T.primary(["crs", "acwr"]) == "crs"
    assert T.primary(["checkin_fatigue", "acwr"]) == "checkin"
    assert T.primary(["illness", "checkin_pain"]) == "illness"
    assert T.primary(["pain", "illness"]) == "pain"
    assert T.primary([]) is None


def test_classify_roles():
    sg = [S("crs", 1), S("acwr", 1.6), S("checkin_fatigue", 3), {**S("boost", True), "role": "hold"}]
    out = {s["signal"]: s["role"] for s in T.classify(sg, ["crs", "acwr"])}
    assert out == {"crs": "trigger", "acwr": "trigger", "checkin_fatigue": "counter", "boost": "hold"}
    solo = {s["signal"]: s["role"] for s in T.classify([S("crs", 0)], [])}
    assert solo["crs"] == "support"
