"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from pathlib import Path

from flask import Flask, request

from src.analysis import generate_report
from src.utils.config import load_config


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return _project_root() / "running.db"


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: sans-serif;
      max-width: 980px;
      margin: 2rem auto;
      padding: 0 1rem;
      line-height: 1.5;
    }}
    nav a {{
      margin-right: 1rem;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f5f5f5;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
    }}
    code {{
      background: #f5f5f5;
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 0.5rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f0f0f0;
    }}
    .muted {{
      color: #666;
    }}
    .card {{
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 1rem;
      margin: 1rem 0;
      background: #fafafa;
    }}
  </style>
</head>
<body>
  <nav>
    <a href="/">홈</a>
    <a href="/db">DB 요약</a>
    <a href="/config">Config</a>
    <a href="/import-preview">Import Preview</a>
    <a href="/sync-status">Sync Status</a>
    <a href="/analyze/today">Today</a>
    <a href="/analyze/full">Full</a>
    <a href="/analyze/race?date=2026-06-01&distance=42.195">Race</a>
  </nav>
  <hr>
  <h1>{html.escape(title)}</h1>
  {body}
</body>
</html>
"""


def _query_rows(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    return conn.execute(sql).fetchall()


def _query_value(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _table(headers: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "<p class='muted'>(no rows)</p>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cols = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        body_rows.append(f"<tr>{cols}</tr>")
    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _scan_history_dir(base_dir: Path) -> dict:
    exts = {".fit", ".gpx", ".tcx"}
    if not base_dir.exists():
        return {
            "exists": False,
            "base_dir": str(base_dir),
            "total_files": 0,
            "by_ext": [],
            "sample_files": [],
        }

    files = [p for p in base_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    counts = Counter(p.suffix.lower() for p in files)
    samples = [str(p.relative_to(_project_root())) for p in sorted(files)[:20]]

    return {
        "exists": True,
        "base_dir": str(base_dir),
        "total_files": len(files),
        "by_ext": sorted(counts.items()),
        "sample_files": samples,
    }


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        db_path = _db_path()
        body = f"""
        <p>RunPulse 데이터 연동 검증용 최소 workbench.</p>

        <div class="card">
          <h2>읽기 전용 점검</h2>
          <ul>
            <li><a href="/db">DB 상태 확인</a></li>
            <li><a href="/config">설정 상태 확인</a></li>
            <li><a href="/import-preview">import 대상 파일 미리보기</a></li>
            <li><a href="/sync-status">sync 설정/명령 미리보기</a></li>
            <li><a href="/analyze/today">today 리포트 미리보기</a></li>
            <li><a href="/analyze/full">full 리포트 미리보기</a></li>
            <li><a href="/analyze/race?date=2026-06-01&distance=42.195">race 리포트 미리보기</a></li>
          </ul>
        </div>

        <div class="card">
          <h2>다음 구현 후보</h2>
          <ul>
            <li>Import 실행 트리거</li>
            <li>실제 recent sync trigger</li>
            <li>최근 activity / dedup 그룹 drill-down</li>
          </ul>
        </div>

        <p class="muted">DB path: {html.escape(str(db_path))}</p>
        """
        return _html_page("Integration Workbench", body)

    @app.get("/config")
    def config_summary():
        config = load_config()
        db_path = _db_path()

        rows = [
            ("database.path", str(db_path), _bool_text(db_path.exists())),
            ("garmin configured", "email/password", _bool_text(bool(config.get("garmin")))),
            ("strava configured", "oauth fields", _bool_text(bool(config.get("strava")))),
            ("intervals configured", "athlete_id/api_key", _bool_text(bool(config.get("intervals")))),
            ("runalyze configured", "token", _bool_text(bool(config.get("runalyze")))),
            ("user config", "max_hr / threshold_pace / weekly target", _bool_text(bool(config.get("user")))),
            ("ai config", "provider / prompt language", _bool_text(bool(config.get("ai")))),
        ]

        body = (
            f"<p class='muted'>Project root: {html.escape(str(_project_root()))}</p>"
            + f"<p class='muted'>Resolved DB path: {html.escape(str(db_path))}</p>"
            + "<h2>Configuration Summary</h2>"
            + _table(["item", "detail", "present"], rows)
            + """
            <div class="card">
              <h2>메모</h2>
              <ul>
                <li>여기서는 민감정보 값을 노출하지 않고, 설정 존재 여부만 표시합니다.</li>
                <li><code>config.json</code>이 없으면 기본값 기반으로 동작합니다.</li>
              </ul>
            </div>
            """
        )
        return _html_page("Config Summary", body)

    @app.get("/import-preview")
    def import_preview():
        project_root = _project_root()
        garmin_dir = project_root / "data/history/garmin"
        strava_dir = project_root / "data/history/strava"

        garmin_info = _scan_history_dir(garmin_dir)
        strava_info = _scan_history_dir(strava_dir)

        def section(title: str, source: str, info: dict) -> str:
            by_ext_rows = [(ext, count) for ext, count in info["by_ext"]]
            sample_rows = [(path,) for path in info["sample_files"]]

            return (
                f"<div class='card'>"
                f"<h2>{html.escape(title)}</h2>"
                f"<p><strong>Path:</strong> <code>{html.escape(info['base_dir'])}</code></p>"
                f"<p><strong>Exists:</strong> {html.escape(_bool_text(info['exists']))}</p>"
                f"<p><strong>Total files:</strong> {info['total_files']}</p>"
                f"<h3>By extension</h3>"
                + _table(["ext", "count"], by_ext_rows)
                + "<h3>Sample files</h3>"
                + _table(["path"], sample_rows)
                + "<h3>Import example</h3>"
                + f"<pre>python src/import_history.py data/history/{html.escape(source)} --source {html.escape(source)} -r</pre>"
                + "</div>"
            )

        body = (
            """
            <div class="card">
              <h2>설명</h2>
              <p>이 페이지는 실제 import 실행 전에 대상 파일 배치를 미리 점검하기 위한 read-only preview 입니다.</p>
              <p>권장 경로:</p>
              <pre>data/history/garmin/
data/history/strava/</pre>
            </div>
            """
            + section("Garmin history preview", "garmin", garmin_info)
            + section("Strava history preview", "strava", strava_info)
        )
        return _html_page("Import Preview", body)

    @app.get("/sync-status")
    def sync_status():
        config = load_config()

        def present_dict(key: str) -> bool:
            value = config.get(key)
            return isinstance(value, dict) and bool(value)

        rows = [
            ("garmin", "email / password", _bool_text(present_dict("garmin"))),
            ("strava", "client_id / client_secret / refresh_token", _bool_text(present_dict("strava"))),
            ("intervals", "athlete_id / api_key", _bool_text(present_dict("intervals"))),
            ("runalyze", "token", _bool_text(present_dict("runalyze"))),
        ]

        body = (
            "<div class='card'>"
            "<h2>설정 상태</h2>"
            "<p>민감정보 값 자체는 노출하지 않고, 각 서비스 설정 존재 여부만 표시합니다.</p>"
            + _table(["source", "required fields", "configured"], rows)
            + "</div>"
            + """
            <div class="card">
              <h2>추천 sync 명령</h2>
              <pre>python src/sync.py --source garmin --days 7
python src/sync.py --source strava --days 7
python src/sync.py --source intervals --days 28
python src/sync.py --source runalyze --days 28
python src/sync.py --source all --days 7</pre>
            </div>
            <div class="card">
              <h2>메모</h2>
              <ul>
                <li>제품 사용 플로우 관점에서는 최근 데이터는 API sync가 우선입니다.</li>
                <li>과거 데이터 백필은 export import로 보완하는 전략이 적합합니다.</li>
                <li>설정이 없는 서비스는 먼저 <code>config.json</code>을 채운 뒤 sync를 시도합니다.</li>
              </ul>
            </div>
            """
        )
        return _html_page("Sync Status", body)

    @app.get("/db")
    def db_summary():
        db_path = _db_path()
        if not db_path.exists():
            body = f"""
            <p>데이터베이스가 없습니다: <code>{html.escape(str(db_path))}</code></p>

            <div class="card">
              <h2>다음 액션</h2>
              <ol>
                <li><code>python src/db_setup.py</code> 로 DB 스키마 생성</li>
                <li>최근 데이터는 sync CLI로 가져오기</li>
                <li>과거 파일은 import_history CLI로 가져오기</li>
              </ol>
            </div>

            <div class="card">
              <h2>예시 명령</h2>
              <pre>python src/db_setup.py

python src/import_history.py data/history/garmin --source garmin -r
python src/import_history.py data/history/strava --source strava -r

python src/analyze.py today
python src/analyze.py full</pre>
            </div>

            <div class="card">
              <h2>권장 디렉터리</h2>
              <pre>data/history/garmin/
data/history/strava/</pre>
            </div>
            """
            return _html_page("DB Summary", body)

        conn = sqlite3.connect(str(db_path))
        try:
            table_counts = [
                ("activities", _query_value(conn, "select count(*) from activities")),
                ("source_metrics", _query_value(conn, "select count(*) from source_metrics")),
                ("daily_wellness", _query_value(conn, "select count(*) from daily_wellness")),
                ("daily_fitness", _query_value(conn, "select count(*) from daily_fitness")),
                ("goals", _query_value(conn, "select count(*) from goals")),
            ]

            activities_total = dict(table_counts).get("activities", 0)

            activities_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from activities
                group by source
                order by source
                """,
            )
            fitness_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from daily_fitness
                group by source
                order by source
                """,
            )
            wellness_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from daily_wellness
                group by source
                order by source
                """,
            )
            recent_activities = _query_rows(
                conn,
                """
                select id, source, activity_type, start_time, distance_km, duration_sec
                from activities
                order by start_time desc
                limit 20
                """,
            )
            matched_groups = _query_rows(
                conn,
                """
                select matched_group_id, count(*)
                from activities
                where matched_group_id is not null
                group by matched_group_id
                having count(*) > 1
                order by count(*) desc, matched_group_id
                limit 20
                """,
            )
        finally:
            conn.close()

        body = (
            f"<p class='muted'>DB path: {html.escape(str(db_path))}</p>"
            + "<h2>Table row counts</h2>"
            + _table(["table", "count"], table_counts)
        )

        if activities_total == 0:
            body += """
            <div class="card">
              <h2>빈 DB 상태</h2>
              <p>DB 파일과 스키마는 존재하지만 아직 activity 데이터가 없습니다.</p>
              <ol>
                <li>최근 데이터는 <code>sync.py</code>로 가져오기</li>
                <li>과거 파일은 <code>import_history.py</code>로 가져오기</li>
                <li>데이터가 들어오면 이 페이지에 source별 집계와 최근 활동이 표시됩니다.</li>
              </ol>
            </div>
            <div class="card">
              <h2>추천 명령</h2>
              <pre>python src/sync.py --source all --days 7

python src/import_history.py data/history/garmin --source garmin -r
python src/import_history.py data/history/strava --source strava -r</pre>
            </div>
            """
            return _html_page("DB Summary", body)

        body += (
            "<h2>Activities by source</h2>"
            + _table(["source", "count"], activities_by_source)
            + "<h2>Daily fitness by source</h2>"
            + _table(["source", "count"], fitness_by_source)
            + "<h2>Daily wellness by source</h2>"
            + _table(["source", "count"], wellness_by_source)
            + "<h2>Recent activities</h2>"
            + _table(
                ["id", "source", "activity_type", "start_time", "distance_km", "duration_sec"],
                recent_activities,
            )
            + "<h2>Matched groups</h2>"
            + _table(["matched_group_id", "count"], matched_groups)
        )
        return _html_page("DB Summary", body)

    @app.get("/analyze/<report_type>")
    def analyze_preview(report_type: str):
        allowed = {"today", "full", "race"}
        if report_type not in allowed:
            return _html_page(
                "Analyze Preview",
                f"<p>지원하지 않는 report_type: {html.escape(report_type)}</p>",
            ), 404

        db_path = _db_path()
        if not db_path.exists():
            body = f"<p>데이터베이스가 없습니다: {html.escape(str(db_path))}</p>"
            return _html_page("Analyze Preview", body)

        config = load_config()
        if report_type == "race":
            race_date = request.args.get("date")
            race_distance = request.args.get("distance")
            if race_date:
                config.setdefault("race", {})
                config["race"]["date"] = race_date
            if race_distance:
                config.setdefault("race", {})
                try:
                    config["race"]["distance"] = float(race_distance)
                except ValueError:
                    pass

        conn = sqlite3.connect(str(db_path))
        try:
            output = generate_report(conn, report_type=report_type, config=config)
        finally:
            conn.close()

        body = f"<pre>{html.escape(output)}</pre>"
        return _html_page(f"Analyze Preview: {report_type}", body)

    return app
