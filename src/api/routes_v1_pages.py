"""v1 HTML 페이지 라우트 — `/import`·`/import-preview`·`/import/upload*`·`/sync-status` (V1S-12 b안).

`app.py` 의 `create_app` 안에 있던 직접 라우트를 **URL·동작 불변**으로 옮겼다(S3 6단계). 삭제하지 않는다 —
삭제 여부는 v1 일몰 단계에서 별도 결정한다. v1 UI 의 HTML 헬퍼(`src.web.helpers.html_page`·
`src.web.views_dev._table`)를 쓰므로 `src/api` → `src/web` 의존이 생긴다 — 일몰 때 이 파일도 함께 사라질 대상이다.
"""
from __future__ import annotations

import html
import logging
import sqlite3
import sys
from pathlib import Path

from flask import Blueprint, redirect, request

from src.sync.garmin import check_garmin_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.sync.strava import check_strava_connection
from src.utils.config import load_config
from src.utils.user_context import db_path, project_root
from src.web.helpers import html_page
from src.web.views_dev import _scan_history_dir, _table

log = logging.getLogger(__name__)
v1_pages_bp = Blueprint("v1_pages", __name__)
bp = v1_pages_bp


@bp.get("/import")
@bp.get("/import-preview")
def import_page():
    """GPX/FIT 파일 업로드 + 폴더 미리보기."""
    import tempfile, shutil
    project_root = project_root()
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
      <h2>파일 업로드 (단일/다수)</h2>
      <p>GPX · FIT · TCX (+ .gz) 파일을 선택하면 <code>data/history/&lt;source&gt;/</code> 폴더에 저장 후 import 합니다.</p>
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
              <input type="file" name="files" multiple
                accept=".gpx,.fit,.tcx,.gpx.gz,.fit.gz,.tcx.gz,.GPX,.FIT,.TCX">
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
    <div class="card">
      <h2>Strava archive ZIP 업로드</h2>
      <p>Strava &gt; 내 계정 &gt; 데이터 내보내기에서 받은 <strong>.zip</strong> 파일을 업로드합니다.<br>
         <code>activities.csv</code> + <code>activities/</code> 폴더를 자동으로 인식합니다.</p>
      <form method="post" action="/import/upload-archive" enctype="multipart/form-data">
        <table style="width:auto; border:none;">
          <tr>
            <td style="border:none; padding:0.3rem 0.5rem;">ZIP 파일:</td>
            <td style="border:none; padding:0.3rem 0.5rem;">
              <input type="file" name="archive" accept=".zip,.ZIP">
            </td>
          </tr>
        </table>
        <div style="margin-top:0.8rem;">
          <button type="submit" style="padding:0.4rem 1.2rem; background:#3498db; color:#fff; border:none; border-radius:4px; cursor:pointer;">
            Archive 임포트
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
    return html_page("Import", body)


@bp.post("/import/upload")
def import_upload():
    """GPX/FIT/TCX (+ .gz) 파일 수신 → 폴더 저장 → import_history 실행."""
    import subprocess
    from werkzeug.utils import secure_filename

    _ALLOWED = {".gpx", ".fit", ".tcx", ".gz"}

    source = request.form.get("source", "garmin").strip()
    if source not in ("garmin", "strava"):
        source = "garmin"

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return redirect("/import?error=파일을 선택하세요.")

    dest_dir = project_root() / "data" / "history" / source
    dest_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for f in files:
        if f.filename:
            fname = secure_filename(f.filename)
            ext = Path(fname).suffix.lower()
            if ext not in _ALLOWED:
                continue
            save_path = dest_dir / fname
            f.save(str(save_path))
            saved.append(fname)

    if not saved:
        return redirect("/import?error=GPX/FIT/TCX (.gz 포함) 파일만 업로드 가능합니다.")

    try:
        proc = subprocess.run(
            [sys.executable, "src/import_history.py", str(dest_dir),
             "--source", source, "-r"],
            capture_output=True, text=True, timeout=120,
            cwd=str(project_root()),
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
    return html_page("Import 결과", body)


@bp.post("/import/upload-archive")
def import_upload_archive():
    """Strava archive ZIP 업로드 → 임시 디렉터리 압축 해제 → import_strava_archive 실행."""
    import shutil
    import tempfile
    import zipfile
    from werkzeug.utils import secure_filename
    from src.import_export.strava_archive import import_strava_archive

    f = request.files.get("archive")
    if not f or f.filename == "":
        return redirect("/import?error=ZIP 파일을 선택하세요.")

    fname = secure_filename(f.filename)
    if not fname.lower().endswith(".zip"):
        return redirect("/import?error=ZIP 파일만 업로드 가능합니다.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="runpulse_archive_"))
    try:
        zip_path = tmp_dir / fname
        f.save(str(zip_path))

        # ZIP 압축 해제
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)
        except zipfile.BadZipFile:
            return redirect("/import?error=유효한 ZIP 파일이 아닙니다.")

        # activities.csv 위치 탐색 (루트 또는 1단계 하위)
        archive_root: Path | None = None
        if (tmp_dir / "activities.csv").exists():
            archive_root = tmp_dir
        else:
            for sub in sorted(tmp_dir.iterdir()):
                if sub.is_dir() and (sub / "activities.csv").exists():
                    archive_root = sub
                    break

        if archive_root is None:
            return redirect("/import?error=activities.csv를 찾을 수 없습니다. Strava archive ZIP이 맞는지 확인하세요.")

        db_path = db_path()
        if not db_path.exists():
            return redirect("/import?error=DB가 초기화되지 않았습니다. python src/db_setup.py를 먼저 실행하세요.")

        with sqlite3.connect(str(db_path)) as conn:
            stats = import_strava_archive(conn, archive_root)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    rows = [
        ("CSV 전체 행", stats["csv_total"]),
        ("신규 삽입", stats["inserted"]),
        ("중복 건너뜀", stats["skipped"]),
        ("파일 연결 성공", stats["file_linked"]),
        ("CSV-only fallback", stats["csv_only"]),
        ("gz 압축 해제 성공", stats["gz_ok"]),
        ("오류", stats["errors"]),
    ]
    table_html = _table(["항목", "수"], rows)
    body = f"""
    <div class="card">
      <h2>Strava Archive Import 결과</h2>
      {table_html}
      <p><a href="/import">&larr; Import 페이지로</a> &nbsp; <a href="/activities">활동 목록</a></p>
    </div>
    """
    return html_page("Archive Import 결과", body)


@bp.get("/sync-status")
def sync_status():
    from src.utils.user_context import get_current_user_id
    config = load_config(user_id=get_current_user_id())
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
    return html_page("Sync Status", body)
