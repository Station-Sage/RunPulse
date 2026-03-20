"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import sqlite3
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
            <li><a href="/analyze/today">today 리포트 미리보기</a></li>
            <li><a href="/analyze/full">full 리포트 미리보기</a></li>
            <li><a href="/analyze/race?date=2026-06-01&distance=42.195">race 리포트 미리보기</a></li>
          </ul>
        </div>

        <div class="card">
          <h2>다음 구현 후보</h2>
          <ul>
            <li>Import preview 페이지</li>
            <li>Sync status / recent fetch 페이지</li>
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
