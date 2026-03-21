from pathlib import Path


def test_fixtures_layout_exists():
    root = Path(__file__).resolve().parent
    fixtures = root / "fixtures"

    assert fixtures.exists()
    assert (fixtures / "README.md").exists()

    expected_dirs = [
        fixtures / "api" / "intervals",
        fixtures / "api" / "garmin",
        fixtures / "api" / "strava",
        fixtures / "api" / "runalyze",
        fixtures / "history" / "garmin",
        fixtures / "history" / "strava",
    ]

    for path in expected_dirs:
        assert path.exists(), f"missing fixture directory: {path}"
