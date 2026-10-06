"""U16l: 품질 사다리 순수 함수·v29 테이블·저장 서비스."""
import sqlite3

from src.db_schema_v29 import ensure_v29
from src.services import progression_service as S
from src.training import progression as P


def test_next_step_up_hold_down_and_clamp():
    assert P.next_step("long_mp", 1, ["on_target"]) == (2, "up")
    assert P.next_step("long_mp", 1, ["over"])[0] == 2
    assert P.next_step("long_mp", 1, ["under"]) == (1, "hold")
    assert P.next_step("long_mp", 1, ["missed"])[0] == 1
    assert P.next_step("long_mp", 2, ["under", "under"]) == (1, "down_2under")
    assert P.next_step("long_mp", 0, ["under", "under"])[0] == 0
    assert P.next_step("interval", 3, ["on_target"])[0] == 3
    assert P.next_step("tempo", 2, []) == (2, "no_history")


def test_prescription_shapes():
    assert P.prescription("long_mp", 0) == {"mp_km": 6.0}
    assert P.prescription("long_mp", 99) == {"mp_km": 16.0}
    assert P.prescription("tempo", 0) == {"reps": 3, "rep_km": 1.6}
    assert P.prescription("tempo", 4) == {"continuous_min": 25}
    assert P.prescription("interval", 2) == {"reps": 5, "rep_km": 1.2}


def test_service_persists_and_migration_idempotent():
    c = sqlite3.connect(":memory:")
    assert S.get_step(c, 1, "tempo") == 0          # 테이블 없음
    ensure_v29(c)
    ensure_v29(c)
    assert S.advance(c, 1, "tempo", ["on_target"]) == 1
    assert S.advance(c, 1, "tempo", ["on_target", "under"]) == 1
    assert S.get_step(c, 1, "tempo") == 1
    assert S.advance(c, 1, "tempo", ["under", "under"]) == 0
    assert S.get_step(c, 2, "tempo") == 0
