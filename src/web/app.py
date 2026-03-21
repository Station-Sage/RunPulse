"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from pathlib import Path

from flask import Flask, redirect, request

from src.analysis import generate_report
from src.utils.config import load_config, redact_config_for_display
from src.sync.garmin import check_garmin_connection
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection

# Phase 5 Blueprint imports
from .views_wellness import wellness_bp
from .views_activity import activity_bp
from .views_activities import activities_bp
from .views_settings import settings_bp


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

        sync_card = """
        <div class="card" style="border-color:#b3d9ff;">
          <h2 style="margin-bottom:0.5rem;">동기화</h2>
          <form method="post" action="/trigger-sync" style="display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center;">
            <select name="source" style="padding:0.35rem 0.6rem; border-radius:4px; border:1px solid #ccc;">
              <option value="all">전체 소스</option>
              <option value="garmin">Garmin</option>
              <option value="strava">Strava</option>
              <option value="intervals">Intervals.icu</option>
              <option value="runalyze">Runalyze</option>
            </select>
            <select name="days" style="padding:0.35rem 0.6rem; border-radius:4px; border:1px solid #ccc;">
              <option value="7">최근 7일</option>
              <option value="14">최근 14일</option>
              <option value="30">최근 30일</option>
              <option value="90">최근 90일</option>
            </select>
            <button type="submit" style="padding:0.35rem 1rem; background:#0066cc; color:#fff; border:none; border-radius:4px; cursor:pointer;">
              ▶ 동기화 실행
            </button>
          </form>
        </div>
        """

        body = f"""
        {sync_card}
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
        redacted = redact_config_for_display(config)

        garmin_status = check_garmin_connection(config)
        strava_status = check_strava_connection(config)
        intervals_status = check_intervals_connection(config)
        runalyze_status = check_runalyze_connection(config)

        def _status_cell(s: dict) -> str:
            icon = "✅" if s["ok"] else "❌"
            return f"{icon} {html.escape(s['status'])}"

        rows = [
            ("database.path", str(db_path), _bool_text(db_path.exists())),
            ("garmin", "tokenstore / email", _status_cell(garmin_status)),
            ("strava", "client_id / refresh_token", _status_cell(strava_status)),
            ("intervals", "athlete_id / api_key", _status_cell(intervals_status)),
            ("runalyze", "token", _status_cell(runalyze_status)),
            ("user config", "max_hr / threshold_pace / weekly target", _bool_text(bool(config.get("user")))),
            ("ai config", "provider / prompt language", _bool_text(bool(config.get("ai")))),
        ]

        import json as _json
        body = (
            f"<p class='muted'>Project root: {html.escape(str(_project_root()))}</p>"
            + f"<p class='muted'>Resolved DB path: {html.escape(str(db_path))}</p>"
            + "<h2>연동 상태</h2>"
            + _table(["항목", "필드", "상태"], rows)
            + f"<p><a href='/settings'>→ 연동 설정 페이지</a></p>"
            + "<h2>설정 내용 (민감정보 마스킹)</h2>"
            + f"<pre>{html.escape(_json.dumps(redacted, indent=2, ensure_ascii=False))}</pre>"
            + """
            <div class="card">
              <h2>메모</h2>
              <ul>
                <li>패스워드/토큰은 앞 4자리만 표시됩니다.</li>
                <li><code>config.json</code>이 없으면 기본값 기반으로 동작합니다.</li>
                <li>서비스 연동은 <a href='/settings'>/settings</a>에서 UI로 설정하거나 <code>config.json</code>을 직접 편집하세요.</li>
              </ul>
            </div>
            """
        )
        return _html_page("Config Summary", body)

    @app.post("/trigger-sync")
    def trigger_sync():
        """동기화 실행 — subprocess로 sync.py 호출 후 결과 표시."""
        import subprocess
        import shlex
        source = request.form.get("source", "all").strip()
        days = request.form.get("days", "7").strip()
        # 입력 검증 (허용값만)
        if source not in ("all", "garmin", "strava", "intervals", "runalyze"):
            source = "all"
        try:
            days_int = max(1, min(int(days), 365))
        except ValueError:
            days_int = 7

        try:
            proc = subprocess.run(
                ["python", "src/sync.py", "--source", source, "--days", str(days_int)],
                capture_output=True, text=True, timeout=300,
                cwd=str(_project_root()),
            )
            stdout = proc.stdout[-4000:] if proc.stdout else "(출력 없음)"
            stderr = proc.stderr[-2000:] if proc.stderr else ""
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            stdout = "(타임아웃 — 300초 초과)"
            stderr = ""
            rc = -1
        except Exception as e:
            stdout = ""
            stderr = str(e)
            rc = -1

        status_label = "✅ 성공" if rc == 0 else f"❌ 오류 (exit {rc})"
        body = f"""
        <div class="card">
          <h2>동기화 결과 — {html.escape(source)} / 최근 {days_int}일</h2>
          <p>{status_label}</p>
          <h3>출력</h3>
          <pre>{html.escape(stdout)}</pre>
          {"<h3>에러</h3><pre style='color:#c0392b;'>" + html.escape(stderr) + "</pre>" if stderr else ""}
          <p><a href="/">&larr; 홈으로</a></p>
        </div>
        """
        return _html_page("동기화 결과", body)

    @app.get("/import")
    @app.get("/import-preview")
    def import_page():
        """GPX/FIT 파일 업로드 + 폴더 미리보기."""
        import tempfile, shutil
        project_root = _project_root()
        garmin_dir = project_root / "data/history/garmin"
        strava_dir = project_root / "data/history/strava"

        garmin_info = _scan_history_dir(garmin_dir)
        strava_info = _scan_history_dir(strava_dir)

        msg = html.escape(request.args.get("msg", ""))
        err = html.escape(request.args.get("error", ""))
        msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""
        err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

        def section(title: str, source: str, info: dict) -> str:
            by_ext_rows = [(ext, count) for ext, count in info["by_ext"]]
            return (
                f"<div class='card'>"
                f"<h2>{html.escape(title)}</h2>"
                f"<p>경로: <code>{html.escape(info['base_dir'])}</code> — "
                f"{'존재' if info['exists'] else '없음'}, 파일 {info['total_files']}개</p>"
                + _table(["확장자", "개수"], by_ext_rows)
                + "</div>"
            )

        upload_form = f"""
        <div class="card">
          <h2>파일 업로드</h2>
          <p>GPX 또는 FIT 파일을 선택하면 <code>data/history/&lt;source&gt;/</code> 폴더에 저장 후 import 합니다.</p>
          <form method="post" action="/import/upload" enctype="multipart/form-data">
            <table style="width:auto; border:none;">
              <tr>
                <td style="border:none; padding:0.3rem 0.5rem;">소스:</td>
                <td style="border:none; padding:0.3rem 0.5rem;">
                  <select name="source" style="padding:0.3rem 0.5rem; border-radius:4px;">
                    <option value="garmin">Garmin</option>
                    <option value="strava">Strava</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td style="border:none; padding:0.3rem 0.5rem;">파일:</td>
                <td style="border:none; padding:0.3rem 0.5rem;">
                  <input type="file" name="files" multiple accept=".gpx,.fit,.GPX,.FIT">
                </td>
              </tr>
            </table>
            <div style="margin-top:0.8rem;">
              <button type="submit" style="padding:0.4rem 1.2rem; background:#2ecc71; color:#fff; border:none; border-radius:4px; cursor:pointer;">
                업로드 및 Import
              </button>
            </div>
          </form>
        </div>
        """

        body = (
            err_html + msg_html
            + upload_form
            + section("Garmin 폴더 현황", "garmin", garmin_info)
            + section("Strava 폴더 현황", "strava", strava_info)
        )
        return _html_page("Import", body)

    @app.post("/import/upload")
    def import_upload():
        """GPX/FIT 파일 수신 → 폴더 저장 → import_history 실행."""
        import subprocess
        from werkzeug.utils import secure_filename

        source = request.form.get("source", "garmin").strip()
        if source not in ("garmin", "strava"):
            source = "garmin"

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return redirect("/import?error=" + "파일을 선택하세요.")

        dest_dir = _project_root() / "data" / "history" / source
        dest_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for f in files:
            if f.filename:
                fname = secure_filename(f.filename)
                ext = Path(fname).suffix.lower()
                if ext not in (".gpx", ".fit"):
                    continue
                save_path = dest_dir / fname
                f.save(str(save_path))
                saved.append(fname)

        if not saved:
            return redirect("/import?error=" + "GPX/FIT 파일만 업로드 가능합니다.")

        try:
            proc = subprocess.run(
                ["python", "src/import_history.py", str(dest_dir), "--source", source, "-r"],
                capture_output=True, text=True, timeout=120,
                cwd=str(_project_root()),
            )
            stdout = proc.stdout[-3000:] if proc.stdout else "(출력 없음)"
            stderr = proc.stderr[-1000:] if proc.stderr else ""
            rc = proc.returncode
        except Exception as e:
            stdout, stderr, rc = "", str(e), -1

        status = "✅ 성공" if rc == 0 else f"❌ 오류 (exit {rc})"
        body = f"""
        <div class="card">
          <h2>Import 결과</h2>
          <p>저장된 파일: {html.escape(', '.join(saved))}</p>
          <p>{status}</p>
          <pre>{html.escape(stdout)}</pre>
          {"<pre style='color:#c0392b;'>" + html.escape(stderr) + "</pre>" if stderr else ""}
          <p><a href="/import">&larr; Import 페이지로</a> &nbsp; <a href="/">홈으로</a></p>
        </div>
        """
        return _html_page("Import 결과", body)

    @app.get("/sync-status")
    def sync_status():
        config = load_config()

        garmin_st = check_garmin_connection(config)
        strava_st = check_strava_connection(config)
        intervals_st = check_intervals_connection(config)
        runalyze_st = check_runalyze_connection(config)

        def _row(service: str, status: dict) -> tuple:
            icon = "✅" if status["ok"] else "❌"
            return (service, f"{icon} {status['status']}", status.get("detail", ""))

        rows = [
            _row("Garmin Connect", garmin_st),
            _row("Strava", strava_st),
            _row("Intervals.icu", intervals_st),
            _row("Runalyze", runalyze_st),
        ]

        body = (
            "<div class='card'>"
            "<h2>서비스 연동 상태</h2>"
            "<p>실제 인증 상태 기반 표시입니다. 연동이 필요하면 <a href='/settings'>설정 페이지</a>로 이동하세요.</p>"
            + _table(["서비스", "상태", "상세"], rows)
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
              <h2>Garmin MFA 안내</h2>
              <p>Garmin 로그인 시 MFA(이중 인증)가 요청되면 Garmin 앱 또는 이메일에서 승인하세요.</p>
              <p>로그인 성공 후 토큰이 저장되면 이후 sync 시 MFA 없이 복구됩니다.</p>
              <p><a href='/connect/garmin'>Garmin 연동 설정 →</a></p>
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

    # ── Blueprint 등록 ─────────────────────────────────────────────────
    app.register_blueprint(wellness_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(settings_bp)  # 서비스 연동 설정

    return app
