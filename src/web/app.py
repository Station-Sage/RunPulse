"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from pathlib import Path

from flask import Flask, request

from src.analysis import generate_report
from src.utils.config import load_config

# Phase 5 Blueprint imports
from .views_wellness import wellness_bp
from .views_activity import activity_bp


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
    .cards-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      margin: 1rem 0;
    }}
    .cards-row > .card {{
      flex: 1;
      min-width: 200px;
      margin: 0;
    }}
    .score-badge {{
      display: inline-block;
      padding: 0.2rem 0.8rem;
      border-radius: 20px;
      font-weight: bold;
      font-size: 1.05rem;
    }}
    .grade-excellent {{ background: #c8f7c5; color: #1a7a17; }}
    .grade-good      {{ background: #d4edff; color: #0056b3; }}
    .grade-moderate  {{ background: #fff3cd; color: #856404; }}
    .grade-poor      {{ background: #ffd6d6; color: #c0392b; }}
    .grade-unknown   {{ background: #eee;    color: #555; }}
    .mrow {{ display: flex; justify-content: space-between; padding: 0.25rem 0; border-bottom: 1px solid #eee; }}
    .mrow:last-child {{ border-bottom: none; }}
    .mlabel {{ color: #555; font-size: 0.9rem; }}
    .mval   {{ font-weight: 500; }}
    h2 {{ margin-top: 0; }}
  </style>
</head>
<body>
  <nav>
    <a href="/">홈</a>
    <a href="/db">DB</a>
    <a href="/wellness">회복/웰니스</a>
    <a href="/activity/deep">활동 심층</a>
    <a href="/analyze/today">Today</a>
    <a href="/analyze/full">Full</a>
    <a href="/analyze/race?date=2026-06-01&distance=42.195">Race</a>
    <a href="/payloads">Payloads</a>
    <a href="/config">Config</a>
    <a href="/sync-status">Sync</a>
    <a href="/import-preview">Import</a>
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

        if not db_path.exists():
            body = f"""
            <p>RunPulse 대시보드 — DB 미초기화 상태입니다.</p>
            <div class="card">
              <h2>시작 방법</h2>
              <ol>
                <li><code>python src/db_setup.py</code> 로 DB 생성</li>
                <li><code>python src/sync.py --source all --days 7</code> 로 데이터 동기화</li>
                <li>이 페이지를 새로고침하면 대시보드가 표시됩니다.</li>
              </ol>
            </div>
            <p class="muted">DB path: {html.escape(str(db_path))}</p>
            """
            return _html_page("RunPulse 대시보드", body)

        # ── 대시보드 데이터 수집 ────────────────────────────────────────
        recovery_card_html = ""
        weekly_card_html = ""
        recent_acts_html = ""

        try:
            from src.analysis.recovery import get_recovery_status
            from src.analysis.weekly_score import calculate_weekly_score

            with sqlite3.connect(str(db_path)) as conn:
                # 회복 상태 (오늘)
                from datetime import date as _date
                today = _date.today().isoformat()
                recovery = get_recovery_status(conn, today)

                # 주간 점수
                try:
                    weekly = calculate_weekly_score(conn)
                except Exception:
                    weekly = None

                # 최근 활동 5개
                recent_rows = conn.execute(
                    """
                    SELECT id, source, activity_type, start_time,
                           distance_km, duration_sec, avg_hr
                    FROM activity_summaries
                    ORDER BY start_time DESC
                    LIMIT 5
                    """
                ).fetchall()

        except Exception as exc:
            body = (
                f"<div class='card'><p>대시보드 로드 오류: {html.escape(str(exc))}</p></div>"
                f"<p class='muted'>DB path: {html.escape(str(db_path))}</p>"
            )
            return _html_page("RunPulse 대시보드", body)

        # ── 회복 카드 ────────────────────────────────────────────────
        if recovery.get("available"):
            detail = recovery.get("detail") or {}
            readiness = detail.get("training_readiness_score")
            score = recovery.get("recovery_score")
            grade = recovery.get("grade")
            grade_kor = {"excellent": "최상", "good": "좋음", "moderate": "보통", "poor": "부족"}.get(grade or "", "—")

            def _rbadge(val, lo, mid, hi):
                if val is None:
                    return "<span class='score-badge grade-unknown'>—</span>"
                v = float(val)
                if v >= hi:
                    cls = "grade-excellent"
                elif v >= mid:
                    cls = "grade-good"
                elif v >= lo:
                    cls = "grade-moderate"
                else:
                    cls = "grade-poor"
                return f"<span class='score-badge {cls}'>{html.escape(str(val))}</span>"

            readiness_badge = _rbadge(readiness, 30, 50, 70)
            recovery_badge = (
                f"<span class='score-badge grade-{html.escape(grade or 'unknown')}'>"
                f"{html.escape(str(score) if score is not None else '—')} ({html.escape(grade_kor)})</span>"
            )
            raw = recovery.get("raw") or {}

            recovery_card_html = f"""
            <div class="card">
              <h2>오늘 회복 상태 <a href="/wellness" style="font-size:0.8rem; font-weight:normal;">상세 &rarr;</a></h2>
              <p><strong>훈련 준비도:</strong> {readiness_badge}
                 &nbsp; <strong>회복 점수:</strong> {recovery_badge}</p>
              <div style="display:flex; gap:2rem; flex-wrap:wrap; margin-top:0.5rem;">
                <span>바디 배터리: <strong>{html.escape(str(raw.get("body_battery") or "—"))}</strong></span>
                <span>수면 점수: <strong>{html.escape(str(raw.get("sleep_score") or "—"))}</strong></span>
                <span>HRV: <strong>{html.escape(str(raw.get("hrv_value") or "—"))} ms</strong></span>
                <span>SpO2: <strong>{html.escape(str(detail.get("spo2_avg") or "—"))}%</strong></span>
              </div>
            </div>
            """
        else:
            recovery_card_html = f"""
            <div class="card">
              <h2>오늘 회복 상태 <a href="/wellness" style="font-size:0.8rem; font-weight:normal;">상세 &rarr;</a></h2>
              <p class="muted">오늘 Garmin 웰니스 데이터가 없습니다.
                <code>python src/sync.py --source garmin --days 1</code></p>
            </div>
            """

        # ── 주간 점수 카드 ────────────────────────────────────────────
        if weekly:
            w_score = weekly.get("total_score")
            w_grade = weekly.get("grade") or "—"
            w_data = weekly.get("data") or {}
            weekly_card_html = f"""
            <div class="card">
              <h2>이번 주 훈련 점수 <a href="/analyze/today" style="font-size:0.8rem; font-weight:normal;">리포트 &rarr;</a></h2>
              <p style="font-size:1.4rem; margin:0.3rem 0;">
                <strong>{html.escape(str(w_score) if w_score is not None else "—")}</strong>
                <span style="font-size:1rem; color:#666;">/ 100 ({html.escape(str(w_grade))})</span>
              </p>
              <div style="display:flex; gap:2rem; flex-wrap:wrap; margin-top:0.5rem;">
                <span>거리: <strong>{html.escape(str(w_data.get("total_distance_km") or "—"))} km</strong></span>
                <span>런 횟수: <strong>{html.escape(str(w_data.get("run_count") or "—"))}</strong></span>
              </div>
            </div>
            """
        else:
            weekly_card_html = """
            <div class="card">
              <h2>이번 주 훈련 점수</h2>
              <p class="muted">데이터 부족</p>
            </div>
            """

        # ── 최근 활동 카드 ────────────────────────────────────────────
        if recent_rows:
            act_rows_html = ""
            for rid, rsrc, rtype, rstart, rdist, rdur, rhr in recent_rows:
                dist_str = f"{float(rdist):.2f}" if rdist else "—"
                dur_min = f"{int(rdur)//60}m" if rdur else "—"
                hr_str = str(rhr) if rhr else "—"
                deep_link = f"<a href='/activity/deep?id={rid}'>심층</a>"
                act_rows_html += (
                    f"<tr>"
                    f"<td>{html.escape(str(rstart)[:10])}</td>"
                    f"<td>{html.escape(str(rsrc))}</td>"
                    f"<td>{html.escape(str(rtype))}</td>"
                    f"<td>{html.escape(dist_str)} km</td>"
                    f"<td>{html.escape(dur_min)}</td>"
                    f"<td>{html.escape(hr_str)} bpm</td>"
                    f"<td>{deep_link}</td>"
                    f"</tr>"
                )
            recent_acts_html = f"""
            <div class="card">
              <h2>최근 활동 <a href="/db" style="font-size:0.8rem; font-weight:normal;">전체 &rarr;</a></h2>
              <table>
                <thead><tr>
                  <th>날짜</th><th>소스</th><th>유형</th>
                  <th>거리</th><th>시간</th><th>심박</th><th>상세</th>
                </tr></thead>
                <tbody>{act_rows_html}</tbody>
              </table>
            </div>
            """
        else:
            recent_acts_html = """
            <div class="card">
              <h2>최근 활동</h2>
              <p class="muted">활동 데이터가 없습니다.</p>
            </div>
            """

        body = f"""
        <div class="cards-row">
          {recovery_card_html}
          {weekly_card_html}
        </div>
        {recent_acts_html}
        <p class="muted">DB: {html.escape(str(db_path))}</p>
        """
        return _html_page("RunPulse 대시보드", body)

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


    @app.get("/payloads")
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


    @app.get("/payloads/view")
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

    # ── /db 테이블에 활동 심층 링크 추가는 recent_activities 쿼리에서 처리 ──

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

    # ── Phase 5 Blueprint 등록 ─────────────────────────────────────────
    app.register_blueprint(wellness_bp)
    app.register_blueprint(activity_bp)

    return app
