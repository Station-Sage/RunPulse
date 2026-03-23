"""Strava Archive Import 뷰 — Flask Blueprint.

/import/strava-archive        : 아카이브 임포트 폼 + 병합 규칙 설명
/import/strava-archive (POST) : 임포트 실행 → 결과 리포트
/import/strava-archive/backfill (POST) : 기존 DB 행 파일 재연결
"""
from __future__ import annotations

import html as _html
from pathlib import Path

from flask import Blueprint, render_template, request

from .helpers import db_path

import_bp = Blueprint("import_data", __name__)


# ── 결과 리포트 렌더링 ────────────────────────────────────────────────

def _stat_row(label: str, value: str, color: str = "") -> str:
    style = f"color:{color};" if color else ""
    return (
        f"<tr><td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>{label}</td>"
        f"<td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);"
        f"text-align:right;font-weight:600;{style}'>{value}</td></tr>"
    )


def _render_import_result_card(stats: dict) -> str:
    """import_strava_archive() 결과 리포트 카드."""
    csv_total = stats.get("csv_total", 0)
    inserted = stats.get("inserted", 0)
    skipped = stats.get("skipped", 0)
    file_linked = stats.get("file_linked", 0)
    csv_only = stats.get("csv_only", 0)
    gz_ok = stats.get("gz_ok", 0)
    errors = stats.get("errors", 0)

    err_color = "var(--red)" if errors > 0 else "var(--green)"
    ok_color = "var(--green)" if inserted > 0 else "var(--muted)"

    rows = (
        _stat_row("처리된 총 행 수 (CSV)", str(csv_total))
        + _stat_row("신규 activity 생성", str(inserted), ok_color)
        + _stat_row("FIT/GPX 파일 연결 성공", str(file_linked), "var(--cyan)")
        + _stat_row("CSV-only fallback (파일 없음)", str(csv_only))
        + _stat_row("gzip (.gz) 압축 해제", str(gz_ok))
        + _stat_row("중복 건너뜀 (source_id 중복)", str(skipped))
        + _stat_row("처리 오류 (삽입 실패)", str(errors), err_color)
    )

    summary = "완료" if errors == 0 else f"완료 (오류 {errors}건 있음)"
    border = "var(--green)" if errors == 0 else "var(--orange)"

    return f"""
<div class='card' style='border-color:{border};'>
  <h2>임포트 결과 — {summary}</h2>
  <div style='overflow-x:auto;'>
    <table style='width:100%;border-collapse:collapse;'>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <p class='muted' style='font-size:0.8rem;margin-top:0.8rem;'>
    FIT/GPX 파일 연결: {file_linked}개 | CSV-only: {csv_only}개 |
    총 생성: {inserted}개 (건너뜀 {skipped} + 오류 {errors})
  </p>
</div>"""


def _render_backfill_result_card(stats: dict) -> str:
    """backfill_strava_archive() 결과 리포트 카드."""
    rows = (
        _stat_row("처리된 총 행 수 (CSV)", str(stats.get("csv_total", 0)))
        + _stat_row("파일 재연결 성공 (updated)", str(stats.get("updated", 0)), "var(--green)")
        + _stat_row("파일 없음 (건너뜀)", str(stats.get("skipped_no_file", 0)))
        + _stat_row("파일 파싱 실패 (건너뜀)", str(stats.get("skipped_parse_fail", 0)))
        + _stat_row("DB에 없는 source_id (건너뜀)", str(stats.get("skipped_not_in_db", 0)))
        + _stat_row("gzip (.gz) 압축 해제", str(stats.get("gz_ok", 0)))
        + _stat_row("처리 오류", str(stats.get("errors", 0)),
                    "var(--red)" if stats.get("errors", 0) > 0 else "")
    )
    return f"""
<div class='card' style='border-color:var(--cyan);'>
  <h2>파일 재연결 결과</h2>
  <div style='overflow-x:auto;'>
    <table style='width:100%;border-collapse:collapse;'>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def _render_merge_rules_card() -> str:
    """병합 규칙 설명 카드 (Section 7.4)."""
    return """
<div class='card'>
  <h2>병합 규칙 안내</h2>
  <p class='muted' style='font-size:0.85rem;margin-bottom:0.6rem;'>
    Strava 아카이브 임포트 시 다음 우선순위 규칙이 적용됩니다.
  </p>
  <table style='width:100%;border-collapse:collapse;font-size:0.85rem;'>
    <thead>
      <tr>
        <th style='text-align:left;padding:0.3rem 0.6rem;'>항목</th>
        <th style='text-align:left;padding:0.3rem 0.6rem;'>우선 소스</th>
        <th style='text-align:left;padding:0.3rem 0.6rem;'>설명</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>source_id 중복</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>기존 유지</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>동일 strava_id가 이미 DB에 있으면 건너뜀</td>
      </tr>
      <tr>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>GPS 데이터</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>FIT &gt; GPX &gt; CSV</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>FIT 우선, 없으면 GPX, 둘 다 없으면 CSV 수치만 사용</td>
      </tr>
      <tr>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>canonical 병합</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>Garmin &gt; Strava</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>동일 시간대 Garmin 활동이 있으면 Garmin이 canonical</td>
      </tr>
      <tr>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>timestamp 매칭</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>±5분 AND</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>시작 시각 ±5분 + 거리 ±3% 동시 만족 시 동일 활동</td>
      </tr>
      <tr>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>gzip 처리</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>자동 해제</td>
        <td style='padding:0.3rem 0.6rem;border-color:rgba(255,255,255,0.08);'>.fit.gz / .gpx.gz → 메모리 내 자동 압축 해제</td>
      </tr>
    </tbody>
  </table>
  <p class='muted' style='font-size:0.8rem;margin-top:0.6rem;'>
    파일 재연결(Backfill): 이미 DB에 있는 Strava 활동에 FIT/GPX 파일이 있으면 GPS 데이터를 추가로 저장합니다.
  </p>
</div>"""


# ── 임포트 폼 ─────────────────────────────────────────────────────────

def _render_import_form(result_html: str = "", backfill_html: str = "") -> str:
    return f"""
{result_html}
{backfill_html}
<div class='card'>
  <h2>Strava 아카이브 임포트</h2>
  <p class='muted' style='font-size:0.85rem;'>
    Strava에서 내보낸 zip 파일 경로를 입력하세요.<br>
    zip 파일 내의 <code>activities.csv</code>와 <code>activities/</code> 폴더가 처리됩니다.
  </p>
  <form method='post' action='/import/strava-archive'>
    <table style='width:auto;border:none;'>
      <tr>
        <td style='border:none;padding:0.3rem 0.5rem;'><label>아카이브 경로:</label></td>
        <td style='border:none;padding:0.3rem 0.5rem;'>
          <input type='text' name='archive_path' required style='width:340px;'
                 placeholder='/path/to/export.zip'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit'
              style='padding:0.4rem 1.2rem;background:var(--cyan);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
        임포트 시작
      </button>
    </div>
  </form>
</div>
<div class='card'>
  <h2>파일 재연결 (Backfill)</h2>
  <p class='muted' style='font-size:0.85rem;'>
    이미 DB에 있는 Strava 활동에 FIT/GPX 파일 GPS 데이터를 추가 저장합니다.<br>
    아카이브 zip 경로를 입력하면 기존 행을 재처리합니다.
  </p>
  <form method='post' action='/import/strava-archive/backfill'>
    <table style='width:auto;border:none;'>
      <tr>
        <td style='border:none;padding:0.3rem 0.5rem;'><label>아카이브 경로:</label></td>
        <td style='border:none;padding:0.3rem 0.5rem;'>
          <input type='text' name='archive_path' required style='width:340px;'
                 placeholder='/path/to/export.zip'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit'
              style='padding:0.4rem 1.2rem;background:var(--orange);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
        재연결 시작
      </button>
    </div>
  </form>
</div>
{_render_merge_rules_card()}"""


# ── 라우트 ────────────────────────────────────────────────────────────

@import_bp.get("/import/strava-archive")
def strava_archive_view():
    """Strava 아카이브 임포트 폼 페이지."""
    body = _render_import_form()
    return render_template(
        "generic_page.html",
        title="Strava 아카이브 임포트",
        body=body,
        active_tab="settings",
    )


def _resolve_archive_folder(archive_path_str: str) -> tuple[Path, object]:
    """zip이면 tempfile에 추출, 폴더면 그대로 반환. (folder, tmpdir_or_None)"""
    import tempfile, zipfile
    p = Path(archive_path_str)
    if not p.exists():
        raise FileNotFoundError(f"경로를 찾을 수 없음: {archive_path_str}")
    if p.suffix.lower() == ".zip":
        tmpdir = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(p) as zf:
            zf.extractall(tmpdir.name)
        extracted = Path(tmpdir.name)
        # 단일 하위 폴더만 있으면 그것을 루트로
        children = [c for c in extracted.iterdir() if c.is_dir()]
        if len(children) == 1 and not (extracted / "activities.csv").exists():
            extracted = children[0]
        return extracted, tmpdir
    elif p.is_dir():
        return p, None
    else:
        raise ValueError(f"zip 파일 또는 폴더 경로를 입력하세요: {archive_path_str}")


@import_bp.post("/import/strava-archive")
def strava_archive_post():
    """Strava 아카이브 임포트 실행 → 결과 리포트."""
    import sqlite3 as _sqlite3
    from src.import_export.strava_archive import import_strava_archive

    archive_path = request.form.get("archive_path", "").strip()
    if not archive_path:
        result_html = "<div class='card' style='border-color:var(--red);'><p>아카이브 경로를 입력하세요.</p></div>"
        return render_template(
            "generic_page.html", title="Strava 아카이브 임포트",
            body=_render_import_form(result_html), active_tab="settings",
        )

    dpath = db_path()
    if not dpath.exists():
        result_html = "<div class='card' style='border-color:var(--red);'><p>running.db가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return render_template(
            "generic_page.html", title="Strava 아카이브 임포트",
            body=_render_import_form(result_html), active_tab="settings",
        )

    tmpdir = None
    try:
        folder, tmpdir = _resolve_archive_folder(archive_path)
        with _sqlite3.connect(str(dpath)) as conn:
            stats = import_strava_archive(conn, folder)
        result_html = _render_import_result_card(stats)
    except (FileNotFoundError, ValueError) as exc:
        result_html = f"<div class='card' style='border-color:var(--red);'><p>{_html.escape(str(exc))}</p></div>"
    except Exception as exc:
        result_html = f"<div class='card' style='border-color:var(--red);'><p>임포트 오류: {_html.escape(str(exc)[:300])}</p></div>"
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()

    return render_template(
        "generic_page.html", title="Strava 아카이브 임포트",
        body=_render_import_form(result_html), active_tab="settings",
    )


@import_bp.post("/import/strava-archive/backfill")
def strava_archive_backfill():
    """기존 Strava 활동에 FIT/GPX 파일 재연결."""
    import sqlite3 as _sqlite3
    from src.import_export.strava_archive import backfill_strava_archive

    archive_path = request.form.get("archive_path", "").strip()
    if not archive_path:
        backfill_html = "<div class='card' style='border-color:var(--red);'><p>아카이브 경로를 입력하세요.</p></div>"
        return render_template(
            "generic_page.html", title="Strava 아카이브 임포트",
            body=_render_import_form(backfill_html=backfill_html), active_tab="settings",
        )

    dpath = db_path()
    tmpdir = None
    try:
        folder, tmpdir = _resolve_archive_folder(archive_path)
        with _sqlite3.connect(str(dpath)) as conn:
            stats = backfill_strava_archive(conn, folder)
        backfill_html = _render_backfill_result_card(stats)
    except (FileNotFoundError, ValueError) as exc:
        backfill_html = f"<div class='card' style='border-color:var(--red);'><p>{_html.escape(str(exc))}</p></div>"
    except Exception as exc:
        backfill_html = f"<div class='card' style='border-color:var(--red);'><p>재연결 오류: {_html.escape(str(exc)[:300])}</p></div>"
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()

    return render_template(
        "generic_page.html", title="Strava 아카이브 임포트",
        body=_render_import_form(backfill_html=backfill_html), active_tab="settings",
    )
