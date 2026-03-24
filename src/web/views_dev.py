"""Developer/debug routes — config, payloads, DB summary, analyze preview."""

from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from flask import Blueprint, redirect, request

from src.analysis import generate_report
from src.utils.config import load_config, redact_config_for_display
from src.sync.garmin import check_garmin_connection
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection

dev_bp = Blueprint("dev", __name__)


# ── 헬퍼 함수 ────────────────────────────────────────────────────────────


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return _project_root() / "running.db"


def _html_page(title: str, body: str) -> str:
    """helpers.html_page 위임 — CSS/nav 중복 제거."""
    from .helpers import html_page as _hp
    return _hp(title, body)


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


def _payload_recent_table(rows: list[tuple]) -> str:
    if not rows:
        return "<p class='muted'>(no rows)</p>"

    headers = ["id", "source", "entity_type", "entity_id", "activity_id", "payload_len", "updated_at", "view"]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)

    body_rows = []
    for row in rows:
        payload_id, source, entity_type, entity_id, activity_id, payload_len, updated_at = row
        view_html = f"<a href='/payloads/view?id={payload_id}'>open</a>"
        cols = "".join(
            [
                f"<td>{html.escape(str(payload_id))}</td>",
                f"<td>{html.escape(str(source))}</td>",
                f"<td>{html.escape(str(entity_type))}</td>",
                f"<td>{html.escape(str(entity_id))}</td>",
                f"<td>{html.escape(str(activity_id))}</td>",
                f"<td>{html.escape(str(payload_len))}</td>",
                f"<td>{html.escape(str(updated_at))}</td>",
                f"<td>{view_html}</td>",
            ]
        )
        body_rows.append(f"<tr>{cols}</tr>")

    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _json_pretty_block(value) -> str:
    import json

    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        pretty = str(value)
    return f"<pre>{html.escape(pretty)}</pre>"


def _scan_history_dir(base_dir: Path) -> dict:
    from collections import Counter

    _SUPPORTED = {".fit", ".gpx", ".tcx", ".fit.gz", ".gpx.gz", ".tcx.gz"}
    if not base_dir.exists():
        return {
            "exists": False,
            "base_dir": str(base_dir),
            "total_files": 0,
            "by_ext": [],
            "sample_files": [],
        }

    files = [
        p for p in base_dir.rglob("*")
        if p.is_file() and any(
            "".join(p.suffixes).lower().endswith(ext) for ext in _SUPPORTED
        )
    ]

    def _ext(p: Path) -> str:
        s = "".join(p.suffixes).lower()
        for ext in (".fit.gz", ".gpx.gz", ".tcx.gz"):
            if s.endswith(ext):
                return ext
        return p.suffix.lower()

    counts = Counter(_ext(p) for p in files)
    samples = [str(p.relative_to(_project_root())) for p in sorted(files)[:20]]

    return {
        "exists": True,
        "base_dir": str(base_dir),
        "total_files": len(files),
        "by_ext": sorted(counts.items()),
        "sample_files": samples,
    }


# ── Routes ────────────────────────────────────────────────────────────────


@dev_bp.get("/config")
def config_summary():
    """설정 현황 + 각 서비스별 직접 수정 링크 제공."""
    import json as _json
    config = load_config()
    db_path = _db_path()
    redacted = redact_config_for_display(config)

    garmin_status = check_garmin_connection(config)
    strava_status = check_strava_connection(config)
    intervals_status = check_intervals_connection(config)
    runalyze_status = check_runalyze_connection(config)

    def _svc_card(name: str, href: str, status: dict) -> str:
        ok = status["ok"]
        badge_cls = "grade-good" if ok else "grade-poor"
        badge_txt = html.escape(status["status"])
        detail = html.escape(status.get("detail", ""))
        icon = "✅" if ok else "❌"
        return (
            f"<div class='card' style='flex:1; min-width:200px; margin:0;'>"
            f"<h2 style='margin-bottom:0.3rem;'>{icon} {html.escape(name)}</h2>"
            f"<p><span class='score-badge {badge_cls}' style='font-size:0.85rem;'>{badge_txt}</span></p>"
            f"<p class='muted' style='font-size:0.82rem;'>{detail}</p>"
            f"<a href='{href}'><button style='padding:0.3rem 0.8rem; cursor:pointer;'>설정 변경</button></a>"
            f"</div>"
        )

    svc_cards = (
        "<div class='cards-row'>"
        + _svc_card("Garmin Connect", "/connect/garmin", garmin_status)
        + _svc_card("Strava", "/connect/strava", strava_status)
        + _svc_card("Intervals.icu", "/connect/intervals", intervals_status)
        + _svc_card("Runalyze", "/connect/runalyze", runalyze_status)
        + "</div>"
    )

    db_form = f"""
    <div class="card">
      <h2>DB 경로</h2>
      <form method="post" action="/config/db-path">
        <input type="text" name="db_path" value="{html.escape(str(db_path))}"
               style="width:340px; padding:0.3rem 0.5rem;">
        <button type="submit" style="padding:0.3rem 0.8rem; cursor:pointer; margin-left:0.5rem;">저장</button>
      </form>
      <p class='muted' style='font-size:0.82rem;'>DB 존재: {_bool_text(db_path.exists())}</p>
    </div>
    """

    body = (
        "<h2>서비스 연동 상태 / 설정 변경</h2>"
        + svc_cards
        + db_form
        + "<h2>전체 설정 내용 (민감정보 전체 마스킹)</h2>"
        + f"<pre>{html.escape(_json.dumps(redacted, indent=2, ensure_ascii=False))}</pre>"
        + "<p class='muted'>민감 정보(비밀번호/토큰/API키)는 ****로 완전 숨김 처리됩니다.</p>"
    )
    return _html_page("Config", body)


@dev_bp.post("/config/db-path")
def config_db_path():
    """DB 경로 설정 저장."""
    from src.utils.config import update_service_config
    new_path = request.form.get("db_path", "").strip()
    if new_path:
        update_service_config("database", {"path": new_path})
    return redirect("/config")


@dev_bp.get("/payloads")
def payloads():
    db_path = _db_path()
    if not db_path.exists():
        body = "<div class='card'><h2>DB 없음</h2><p>running.db가 없습니다.</p></div>"
        return _html_page("Payloads", body)

    source = request.args.get("source", "").strip()
    entity_type = request.args.get("entity_type", "").strip()
    activity_id = request.args.get("activity_id", "").strip()
    limit = max(1, min(_to_int(request.args.get("limit", "20"), 20), 200))

    where = []
    params = []

    if source:
        where.append("source = ?")
        params.append(source)
    if entity_type:
        where.append("entity_type = ?")
        params.append(entity_type)
    if activity_id:
        where.append("activity_id = ?")
        params.append(activity_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    try:
        with sqlite3.connect(db_path) as conn:
            payload_counts = conn.execute(
                """
                SELECT source, entity_type, count(*) AS cnt
                FROM raw_source_payloads
                GROUP BY source, entity_type
                ORDER BY source, entity_type
                """
            ).fetchall()

            metric_counts = conn.execute(
                """
                SELECT source, metric_name, count(*) AS cnt
                FROM activity_detail_metrics
                GROUP BY source, metric_name
                ORDER BY source, metric_name
                LIMIT 100
                """
            ).fetchall()

            recent_payloads = conn.execute(
                f"""
                SELECT id, source, entity_type, entity_id, activity_id,
                       length(payload_json) AS payload_len, updated_at
                FROM raw_source_payloads
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
    except Exception as e:
        return _html_page("Payloads", f"<div class='card'><h2>조회 실패</h2><pre>{html.escape(str(e))}</pre></div>")

    filter_form = f"""
    <div class="card">
      <h2>filters</h2>
      <form method="get" action="/payloads">
        <label>source <input type="text" name="source" value="{html.escape(source)}"></label>
        <label> entity_type <input type="text" name="entity_type" value="{html.escape(entity_type)}"></label>
        <label> activity_id <input type="text" name="activity_id" value="{html.escape(activity_id)}"></label>
        <label> limit <input type="number" name="limit" min="1" max="200" value="{limit}"></label>
        <button type="submit">apply</button>
      </form>
      <p class="muted">예: /payloads?source=intervals&entity_type=wellness&limit=50</p>
    </div>
    """

    body = (
        filter_form
        + "<div class='card'><h2>source_payloads counts</h2>"
        + _table(["source", "entity_type", "count"], payload_counts)
        + "</div>"
        + "<div class='card'><h2>source_metrics counts</h2>"
        + _table(["source", "metric_name", "count"], metric_counts)
        + "</div>"
        + "<div class='card'><h2>recent payloads</h2>"
        + _payload_recent_table(recent_payloads)
        + "</div>"
    )
    return _html_page("Payloads", body)


@dev_bp.get("/payloads/view")
def payload_view():
    db_path = _db_path()
    if not db_path.exists():
        body = "<div class='card'><h2>DB 없음</h2><p>running.db가 없습니다.</p></div>"
        return _html_page("Payload View", body)

    payload_id = request.args.get("id", "").strip()
    if not payload_id:
        body = "<div class='card'><h2>잘못된 요청</h2><p>id 파라미터가 필요합니다.</p></div>"
        return _html_page("Payload View", body)

    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT id, source, entity_type, entity_id, activity_id, payload_json, created_at, updated_at
                FROM raw_source_payloads
                WHERE id = ?
                """,
                (payload_id,),
            ).fetchone()

            if not row:
                body = f"<div class='card'><h2>없음</h2><p>payload id={html.escape(payload_id)} 를 찾을 수 없습니다.</p></div>"
                return _html_page("Payload View", body)

            metrics = []
            if row[4]:
                metrics = conn.execute(
                    """
                    SELECT source, metric_name,
                           COALESCE(CAST(metric_value AS TEXT), metric_json) AS metric_data
                    FROM activity_detail_metrics
                    WHERE activity_id = ?
                    ORDER BY source, metric_name
                    LIMIT 100
                    """,
                    (row[4],),
                ).fetchall()
    except sqlite3.Error as exc:
        body = f"<div class='card'><h2>DB 오류</h2><pre>{html.escape(str(exc))}</pre></div>"
        return _html_page("Payload View", body)

    detail_rows = [
        ("id", row[0]),
        ("source", row[1]),
        ("entity_type", row[2]),
        ("entity_id", row[3]),
        ("activity_id", row[4]),
        ("created_at", row[6]),
        ("updated_at", row[7]),
    ]

    extra = ""
    if row[4]:
        extra += (
            "<div class='card'><h2>연관 source_metrics</h2>"
            + _table(["source", "metric_name", "metric_data"], metrics)
            + "</div>"
        )

    body = (
        "<div class='card'><h2>payload metadata</h2>"
        + _table(["field", "value"], detail_rows)
        + "</div>"
        + "<div class='card'><h2>payload json</h2>"
        + _json_pretty_block(row[5])
        + "</div>"
        + extra
        + "<p><a href='/payloads'>← payloads 목록으로</a></p>"
    )
    return _html_page(f"Payload View #{row[0]}", body)


@dev_bp.get("/db")
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
            ("activity_summaries", _query_value(conn, "select count(*) from activity_summaries")),
            ("activity_detail_metrics", _query_value(conn, "select count(*) from activity_detail_metrics")),
            ("daily_wellness", _query_value(conn, "select count(*) from daily_wellness")),
            ("daily_fitness", _query_value(conn, "select count(*) from daily_fitness")),
            ("goals", _query_value(conn, "select count(*) from goals")),
        ]

        activities_total = dict(table_counts).get("activity_summaries", 0)

        activities_by_source = _query_rows(
            conn,
            """
            select source, count(*)
            from activity_summaries
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
            from activity_summaries
            order by start_time desc
            limit 20
            """,
        )
        matched_groups = _query_rows(
            conn,
            """
            select matched_group_id, count(*)
            from activity_summaries
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

    # 최근 활동 테이블에 심층 분석 링크 추가
    act_rows_with_link = []
    for row in recent_activities:
        act_id = row[0]
        act_rows_with_link.append(row + (f"/activity/deep?id={act_id}",))

    def _recent_acts_table(rows):
        if not rows:
            return "<p class='muted'>(no rows)</p>"
        headers = ["id", "source", "activity_type", "start_time", "distance_km", "duration_sec", "심층 분석"]
        head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        body_rows = []
        for row in rows:
            *data_cols, link = row
            cols = "".join(f"<td>{html.escape(str(v))}</td>" for v in data_cols)
            cols += f"<td><a href='{html.escape(str(link))}'>보기</a></td>"
            body_rows.append(f"<tr>{cols}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    body += (
        "<h2>Activities by source</h2>"
        + _table(["source", "count"], activities_by_source)
        + "<h2>Daily fitness by source</h2>"
        + _table(["source", "count"], fitness_by_source)
        + "<h2>Daily wellness by source</h2>"
        + _table(["source", "count"], wellness_by_source)
        + "<h2>Recent activities</h2>"
        + _recent_acts_table(act_rows_with_link)
        + "<h2>Matched groups</h2>"
        + _table(["matched_group_id", "count"], matched_groups)
    )
    return _html_page("DB Summary", body)


@dev_bp.get("/analyze/<report_type>")
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
