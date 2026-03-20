"""import_history 테스트."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.import_history import parse_gpx, parse_fit, import_file


class TestParseGpx:
    def test_valid_gpx(self, tmp_path):
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Run</name>
    <trkseg>
      <trkpt lat="37.5" lon="127.0">
        <ele>50</ele>
        <time>2026-03-18T07:00:00Z</time>
      </trkpt>
      <trkpt lat="37.501" lon="127.001">
        <ele>55</ele>
        <time>2026-03-18T07:30:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text(gpx_content)

        result = parse_gpx(gpx_file)
        assert result is not None
        assert result["duration_sec"] == 1800
        assert result["distance_km"] > 0
        assert "2026-03-18" in result["start_time"]

    def test_empty_gpx(self, tmp_path):
        gpx_file = tmp_path / "empty.gpx"
        gpx_file.write_text('<?xml version="1.0"?><gpx version="1.1"></gpx>')

        result = parse_gpx(gpx_file)
        assert result is None


class TestImportFile:
    def test_import_gpx(self, db_conn, tmp_path):
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk><name>Run</name><trkseg>
    <trkpt lat="37.5" lon="127.0"><time>2026-03-18T07:00:00Z</time></trkpt>
    <trkpt lat="37.501" lon="127.001"><time>2026-03-18T07:30:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
        gpx_file = tmp_path / "morning_run.gpx"
        gpx_file.write_text(gpx_content)

        result = import_file(db_conn, gpx_file, "garmin")
        assert result is True

        row = db_conn.execute("SELECT source, source_id FROM activity_summaries").fetchone()
        assert row[0] == "garmin"
        assert row[1] == "import_morning_run"

    def test_duplicate_import_skipped(self, db_conn, tmp_path):
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk><name>Run</name><trkseg>
    <trkpt lat="37.5" lon="127.0"><time>2026-03-18T07:00:00Z</time></trkpt>
    <trkpt lat="37.501" lon="127.001"><time>2026-03-18T07:30:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
        gpx_file = tmp_path / "run.gpx"
        gpx_file.write_text(gpx_content)

        import_file(db_conn, gpx_file, "garmin")
        result = import_file(db_conn, gpx_file, "garmin")
        assert result is False

    def test_unsupported_format(self, db_conn, tmp_path):
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("not a gpx or fit")
        assert import_file(db_conn, txt_file, "garmin") is False
