"""algo_changelog 계약 테스트 — Calculator 버전과 변경 이력의 일치를 강제."""
import re

from src.metrics.algo_changelog import CHANGELOG, changes_for
from src.metrics.engine import ALL_CALCULATORS

_BY_NAME = {c.name: c for c in ALL_CALCULATORS}


def test_every_non_default_version_has_entry():
    keys = {(c.calculator, c.version) for c in CHANGELOG}
    missing = [(c.name, c.version) for c in ALL_CALCULATORS if c.version != "1.0" and (c.name, c.version) not in keys]
    assert not missing, f"algo_changelog 항목 누락: {missing}"


def test_calculator_names_exist_and_latest_matches():
    for ch in CHANGELOG:
        assert ch.calculator in _BY_NAME, ch.calculator
    for name in {c.calculator for c in CHANGELOG}:
        assert changes_for(name)[-1].version == _BY_NAME[name].version, name


def test_dates_well_formed_and_ascending():
    for c in CHANGELOG:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", c.date), c
    for name in {c.calculator for c in CHANGELOG}:
        dates = [c.date for c in changes_for(name)]
        assert dates == sorted(dates)


def test_prev_chain_consistent():
    for name in {c.calculator for c in CHANGELOG}:
        items = changes_for(name)
        for before, after in zip(items, items[1:]):
            assert after.prev == before.version, (name, after)


def test_reason_non_empty_and_short():
    for c in CHANGELOG:
        assert c.reason.strip() and len(c.reason) <= 80, c
