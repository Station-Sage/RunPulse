"""내보내기 아카이브 zip 작성 — 그룹별 테이블 CSV/JSON·원본 jsonl·manifest·README (data-export §2.2).

행은 fetchmany 커서로 흘려 쓰고, 테이블 경계마다 디스크 여유를 확인한다. 'enc:' 값이 보이면 즉시 중단한다.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from src.db_setup import SCHEMA_VERSION
from src.services import export_groups as eg

FORMAT_VERSION = 1
EXPORT_MIN_FREE_BYTES = 1024**3
_CHUNK = 2000
_SOURCES = ("garmin", "strava", "intervals", "runalyze")
_TIME_MEANING = {
    "activity_summaries.start_time": "local_wall", "activity_laps.start_time": "local_wall",
    "source_payloads.fetched_at": "utc_naive", "metric_store.computed_at": "utc_naive",
    "context_episodes.created_at": "utc_naive", "chat_messages.created_at": "utc_naive",
}

README = """RunPulse 데이터 내보내기
========================
- manifest.json: 포함 그룹·테이블별 행 수·기간·스키마 버전·시각 열의 의미(local_wall/offset_iso/utc_naive).
- tables/*.csv, json/*.json: 테이블 원본 값(UTF-8, CSV 는 BOM 포함).
- csv/*.csv: 사람이 읽기 쉬운 활동·웰니스·부하 요약.
- raw_payloads/<소스>.jsonl: 연동 서비스 원본 응답.
이 파일에는 건강·위치 정보가 들어 있을 수 있어요. 공유 전에 내용을 확인해 주세요.
{profile_note}연동 계정 토큰·비밀번호는 포함되지 않아요.
"""
PROFILE_NOTE = "프로필 그룹에는 질병 정보 동의 기록이 들어 있어요.\n"


class ExportError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def check_free_space(directory: Path, min_free: int | None = None) -> None:
    free = shutil.disk_usage(directory).free
    if free < (EXPORT_MIN_FREE_BYTES if min_free is None else min_free):
        raise ExportError("EXPORT_DISK_FULL", "디스크 여유 공간이 부족해요")


def _columns(conn, table: str) -> list[str]:
    return eg.safe_columns(conn, table)


def _where(conn, tdef: eg.TableDef, frm, to, include_dismissed: bool) -> tuple[str, list]:
    cond, args = "", []
    if tdef.activity_fk:
        sub = ""
        if frm:
            sub += " AND substr(start_time,1,10) >= ?"
            args.append(frm)
        if to:
            sub += " AND substr(start_time,1,10) <= ?"
            args.append(to)
        if sub:
            cond += f" AND activity_id IN (SELECT id FROM activity_summaries WHERE 1=1{sub})"
    elif tdef.date_col and (frm or to) and tdef.date_col in _columns(conn, tdef.name):
        if frm:
            cond += f" AND substr({tdef.date_col},1,10) >= ?"
            args.append(frm)
        if to:
            cond += f" AND substr({tdef.date_col},1,10) <= ?"
            args.append(to)
    if tdef.name == "context_episodes" and not include_dismissed:
        cond += " AND status != 'dismissed'"
    return cond, args


def _rows(conn, table: str, cols: list[str], cond: str, args: list):
    cur = conn.execute(f"SELECT {','.join(cols)} FROM {table} WHERE 1=1{cond}", args)  # noqa: S608 — 상수/허용목록
    while True:
        chunk = cur.fetchmany(_CHUNK)
        if not chunk:
            return
        for row in chunk:
            if eg.has_secret_value(row):
                raise ExportError("EXPORT_SECRET_DETECTED", f"{table}: 비밀 값이 감지돼 중단했어요")
            yield row


def _write_table(z: zipfile.ZipFile, conn, tdef: eg.TableDef, frm, to, include_dismissed, with_json: bool) -> int:
    cols = _columns(conn, tdef.name)
    cond, args = _where(conn, tdef, frm, to, include_dismissed)
    n = 0
    with z.open(f"tables/{tdef.name}.csv", "w") as raw:  # zip 은 쓰기 핸들 1개만 허용 → CSV, JSON 순차
        raw.write("﻿".encode())
        out = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        w = csv.writer(out, lineterminator="\n")
        w.writerow(cols)
        for row in _rows(conn, tdef.name, cols, cond, args):
            w.writerow(row)
            n += 1
        out.flush()
        out.detach()
    if with_json:
        with z.open(f"json/{tdef.name}.json", "w") as jf:
            jf.write(b"[")
            for i, row in enumerate(_rows(conn, tdef.name, cols, cond, args)):
                jf.write((",\n" if i else "\n").encode() + json.dumps(
                    dict(zip(cols, row)), ensure_ascii=False, default=str).encode())
            jf.write(b"\n]\n")
    return n


def _write_raw(z: zipfile.ZipFile, conn, frm, to) -> int:
    total = 0
    for src in _SOURCES:
        cond, args = "", [src]
        if frm:
            cond += " AND substr(entity_date,1,10) >= ?"
            args.append(frm)
        if to:
            cond += " AND substr(entity_date,1,10) <= ?"
            args.append(to)
        cur = conn.execute("SELECT entity_type, entity_id, entity_date, fetched_at, payload FROM source_payloads "
                           f"WHERE source=?{cond} ORDER BY fetched_at", args)
        f = None
        try:
            while chunk := cur.fetchmany(_CHUNK):
                for r in chunk:
                    if eg.has_secret_value(r):
                        raise ExportError("EXPORT_SECRET_DETECTED", "source_payloads: 비밀 값이 감지돼 중단했어요")
                    if f is None:
                        f = z.open(f"raw_payloads/{src}.jsonl", "w")
                    f.write((json.dumps({"entity_type": r[0], "entity_id": r[1], "entity_date": r[2],
                                         "fetched_at": r[3], "payload": _loads(r[4])}, ensure_ascii=False) + "\n").encode())
                    total += 1
        finally:
            if f:
                f.close()
    return total


def _loads(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def build_archive(conn: sqlite3.Connection, path: Path, groups=eg.LEGACY_GROUPS, frm=None, to=None,
                  include_dismissed: bool = False, min_free: int | None = None, progress=None) -> dict:
    """zip 을 쓰고 manifest 요약을 돌려준다. 실패 시 부분 파일을 지우고 ExportError 를 올린다.

    `progress(done, total)` 는 테이블 하나를 쓸 때마다 불린다(요약 CSV 묶음이 마지막 1단계).
    """
    from src.services import export_service as es

    keys = [k for k in eg.GROUP_KEYS if k in set(groups)]
    manifest_groups, counts = [], {}
    total, done = sum(len(eg.get_group(k).tables) for k in keys) + 1, 0
    step = progress or (lambda _d, _t: None)
    step(0, total)
    try:
        check_free_space(path.parent, min_free)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for key in keys:
                gdef = eg.get_group(key)
                entry = {"key": key, "tables": [], "row_counts": {}, "skipped": {}}
                for tdef in gdef.tables:
                    if not eg.table_exists(conn, tdef.name):
                        if not tdef.optional:
                            raise ExportError("EXPORT_FAILED", f"{tdef.name} 테이블이 없어요")
                        entry["skipped"][tdef.name] = "not_migrated"
                        continue
                    check_free_space(path.parent, min_free)
                    if tdef.name == "source_payloads":
                        n = _write_raw(z, conn, frm, to)
                    else:
                        n = _write_table(z, conn, tdef, frm, to, include_dismissed, key != "streams")
                    entry["tables"].append(tdef.name)
                    entry["row_counts"][tdef.name] = counts[tdef.name] = n
                    done += 1
                    step(done, total)
                manifest_groups.append(entry)
            for kind, fn in es._QUICK.items():
                if (kind == "quick_activities" and "activities" in keys) or (
                        kind != "quick_activities" and "metrics" in keys):
                    z.writestr(f"csv/{es.quick_filename(kind)}", es.csv_text(fn(conn, frm, to)))
            step(total, total)
            manifest = {
                "format_version": FORMAT_VERSION, "schema_version": SCHEMA_VERSION,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "range": {"from": frm, "to": to}, "include_dismissed": include_dismissed,
                "groups": manifest_groups,
                "sensitive_groups": [k for k in keys if k in eg.SENSITIVE_GROUPS],
                "time_columns": _TIME_MEANING,
            }
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            z.writestr("README.txt", README.format(profile_note=PROFILE_NOTE if "profile" in keys else ""))
            files = z.namelist()
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {"files": files, "row_counts": counts, "groups": keys}
