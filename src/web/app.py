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
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 0.5rem;
      text-align: left;
    }}
    th {{
      background: #f0f0f0;
    }}
    .muted {{
      color: #666;
    }}
  </style>
</head>
<body>
  <nav>
    <a href="/">홈</a>
    <a href="/db">DB 요약</a>
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


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        db_path = _db_path()
        body = f"""
        <p>RunPulse 데이터 연동 검증용 최소 workbench.</p>
        <ul>
          <li><a href="/db">DB 상태 확인</a></li>
          <li><a href="/analyze/today">today 리포트 미리보기</a></li>
          <li><a href="/analyze/full">full 리포트 미리보기</a></li>
          <li><a href="/analyze/race?date=2026-06-01&distance=42.195">race 리포트 미리보기</a></li>
        </ul>
        <p class="muted">DB path: {html.escape(str(db_path))}</p>
        """
        return _html_page("Integration Workbench", body)

    @app.get("/db")
    def db_summary():
        db_path = _db_path()
        if not db_path.exists():
            body = f"<p>데이터베이스가 없습니다: {html.escape(str(db_path))}</p>"
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
