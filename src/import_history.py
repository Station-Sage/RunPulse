"""GPX / FIT / TCX 파일 일괄 파싱 및 DB 삽입.

지원 형식:
  .gpx, .fit, .tcx          — 직접 파싱
  .gpx.gz, .fit.gz, .tcx.gz — gzip 압축 해제 후 파싱

Strava archive 모드 (--strava-archive):
  activities.csv + activities/ 폴더를 통합 임포트.
  source_id = CSV의 Activity ID, 파일 파싱 실패 시 CSV-only fallback.
"""
from __future__ import annotations

import argparse
import gzip
import io
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import gpxpy
import fitparse

from src.db_setup import get_db_path, init_db
from src.utils.dedup import assign_group_id

# 지원 확장자 (단일 및 .gz 포함)
_SUPPORTED = {".gpx", ".fit", ".tcx", ".gpx.gz", ".fit.gz", ".tcx.gz"}

_TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
_TCX_SPORT_MAP = {
    "Running": "running",
    "Cycling": "cycling",
    "Biking": "cycling",
    "Swimming": "swimming",
    "Other": "workout",
}


# ── 파서 ──────────────────────────────────────────────────────────────────

def parse_gpx(file_path: Path, *, data: bytes | None = None) -> dict | None:
    """GPX 파일 → activity dict."""
    try:
        if data is not None:
            gpx = gpxpy.parse(io.StringIO(data.decode("utf-8")))
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                gpx = gpxpy.parse(f)
    except Exception:
        return None

    if not gpx.tracks:
        return None

    distance_m = gpx.length_3d() or gpx.length_2d()
    distance_km = distance_m / 1000 if distance_m else 0

    bounds = gpx.get_time_bounds()
    if not bounds.start_time:
        return None

    start_time = bounds.start_time.isoformat()
    duration_sec = 0
    if bounds.end_time:
        duration_sec = int((bounds.end_time - bounds.start_time).total_seconds())

    avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

    hr_values: list[int] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                for ext in point.extensions:
                    hr_elem = ext.find(
                        ".//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr"
                    )
                    if hr_elem is not None and hr_elem.text:
                        hr_values.append(int(hr_elem.text))

    uphill, _ = gpx.get_uphill_downhill()
    return {
        "start_time": start_time,
        "distance_km": round(distance_km, 2),
        "duration_sec": duration_sec,
        "avg_pace_sec_km": avg_pace,
        "avg_hr": round(sum(hr_values) / len(hr_values)) if hr_values else None,
        "max_hr": max(hr_values) if hr_values else None,
        "elevation_gain": round(uphill, 1) if uphill else None,
        "description": gpx.tracks[0].name or file_path.stem,
    }


def parse_fit(file_path: Path, *, data: bytes | None = None) -> dict | None:
    """FIT 파일 → activity dict."""
    try:
        src = io.BytesIO(data) if data is not None else str(file_path)
        fit = fitparse.FitFile(src)
    except Exception:
        return None

    for record in fit.get_messages("session"):
        fields = {f.name: f.value for f in record.fields}

        start_time = fields.get("start_time") or fields.get("timestamp")
        if isinstance(start_time, datetime):
            start_time = start_time.replace(tzinfo=timezone.utc).isoformat()
        elif not start_time:
            return None

        distance_m = fields.get("total_distance") or 0
        distance_km = distance_m / 1000
        duration_sec = int(fields.get("total_timer_time") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None
        cadence = fields.get("avg_running_cadence") or fields.get("avg_cadence")

        return {
            "start_time": start_time,
            "distance_km": round(distance_km, 2),
            "duration_sec": duration_sec,
            "avg_pace_sec_km": avg_pace,
            "avg_hr": fields.get("avg_heart_rate"),
            "max_hr": fields.get("max_heart_rate"),
            "avg_cadence": int(cadence) if cadence else None,
            "elevation_gain": fields.get("total_ascent"),
            "calories": fields.get("total_calories"),
            "description": file_path.stem,
        }

    return None


def parse_tcx(file_path: Path, *, data: bytes | None = None) -> dict | None:
    """TCX XML (Garmin Training Center / Strava) → activity dict.

    TCX는 여러 Lap을 집계하여 전체 활동 수치를 계산한다.
    네임스페이스 없는 TCX도 폴백으로 처리한다.

    주의: xml.etree.ElementTree Element는 자식 없으면 bool=False이므로
    `el or el2` 패턴 금지. 반드시 `is not None` 체크를 사용한다.
    """
    ns = _TCX_NS
    t = lambda name: f"{{{ns}}}{name}"  # noqa: E731

    def _fe(parent, tag_name: str):
        """네임스페이스 우선 탐색, 없으면 bare tag 폴백. is None 비교 사용."""
        el = parent.find(t(tag_name))
        if el is None:
            el = parent.find(tag_name)
        return el

    def _fep(parent, path_ns: str, path_bare: str):
        """경로 탐색 (중첩 태그용). is None 비교 사용."""
        el = parent.find(path_ns)
        if el is None:
            el = parent.find(path_bare)
        return el

    try:
        root = ET.fromstring(data) if data is not None else ET.parse(str(file_path)).getroot()
    except ET.ParseError:
        return None

    # Activities/Activity — 네임스페이스 있는 버전 우선, 없으면 폴백
    act = root.find(f"{t('Activities')}/{t('Activity')}")
    if act is None:
        act = root.find("Activities/Activity")
    if act is None:
        return None

    sport = act.get("Sport", "Running")

    id_el = _fe(act, "Id")
    start_time = (id_el.text or "").strip() if id_el is not None else None

    tot_dist = tot_time = tot_cal = 0.0
    hr_vals: list[int] = []
    max_hr = 0

    laps = act.findall(t("Lap")) or act.findall("Lap")
    for lap in laps:
        def _v(tag_name: str) -> str | None:  # noqa: E306
            el = _fe(lap, tag_name)
            return el.text if el is not None else None

        if (v := _v("DistanceMeters")):
            tot_dist += float(v)
        if (v := _v("TotalTimeSeconds")):
            tot_time += float(v)
        if (v := _v("Calories")):
            tot_cal += float(v)

        hr_el = _fep(lap,
                     f"{t('AverageHeartRateBpm')}/{t('Value')}",
                     "AverageHeartRateBpm/Value")
        if hr_el is not None and hr_el.text:
            hr_vals.append(int(float(hr_el.text)))

        mhr_el = _fep(lap,
                      f"{t('MaximumHeartRateBpm')}/{t('Value')}",
                      "MaximumHeartRateBpm/Value")
        if mhr_el is not None and mhr_el.text:
            max_hr = max(max_hr, int(float(mhr_el.text)))

    if not start_time or tot_dist <= 0:
        return None

    dist_km = tot_dist / 1000
    dur_sec = int(tot_time)
    return {
        "start_time": start_time,
        "activity_type": _TCX_SPORT_MAP.get(sport, sport.lower()),
        "distance_km": round(dist_km, 2),
        "duration_sec": dur_sec,
        "avg_pace_sec_km": int(dur_sec / dist_km) if dist_km > 0 else None,
        "avg_hr": int(sum(hr_vals) / len(hr_vals)) if hr_vals else None,
        "max_hr": max_hr or None,
        "calories": int(tot_cal) if tot_cal > 0 else None,
        "description": file_path.stem,
    }


def parse_file_data(file_path: Path) -> dict | None:
    """GPX / FIT / TCX (+ .gz 압축) 파일 → activity dict.

    확장자 기반으로 자동 라우팅하며, .gz 파일은 먼저 압축 해제한다.
    파싱 실패 시 None 반환.
    """
    name = file_path.name.lower()
    data: bytes | None = None

    if name.endswith(".gz"):
        try:
            with gzip.open(file_path, "rb") as gz_f:
                data = gz_f.read()
        except Exception:
            return None
        inner = name[:-3]  # e.g. "12345678.fit"
    else:
        inner = name

    if inner.endswith(".gpx"):
        return parse_gpx(file_path, data=data)
    if inner.endswith(".fit"):
        return parse_fit(file_path, data=data)
    if inner.endswith(".tcx"):
        return parse_tcx(file_path, data=data)
    return None


# ── DB 삽입 ───────────────────────────────────────────────────────────────

def import_file(
    conn: sqlite3.Connection, file_path: Path, source: str,
) -> bool:
    """단일 파일 파싱 후 DB 삽입.

    source_id는 파일명 stem 기반 (import_<stem>).
    Strava archive 모드에서는 이 함수 대신 strava_archive.import_strava_archive()를 사용한다.
    """
    data = parse_file_data(file_path)
    if not data:
        print(f"파싱 실패: {file_path}")
        return False

    source_id = f"import_{file_path.stem}"
    activity_type = data.get("activity_type", "running")

    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO activity_summaries
               (source, source_id, activity_type, start_time, distance_km,
                duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                elevation_gain, calories, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source, source_id, activity_type,
                data["start_time"], data["distance_km"], data["duration_sec"],
                data.get("avg_pace_sec_km"), data.get("avg_hr"), data.get("max_hr"),
                data.get("avg_cadence"), data.get("elevation_gain"),
                data.get("calories"), data.get("description"),
            ),
        )
    except sqlite3.Error as e:
        print(f"DB 삽입 실패 {file_path}: {e}")
        return False

    if cursor.rowcount == 0:
        print(f"이미 존재: {file_path.name}")
        return False

    assign_group_id(conn, cursor.lastrowid)
    return True


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="GPX/FIT/TCX (+ .gz) 파일 일괄 임포트"
    )
    parser.add_argument("path", help="파일 또는 디렉터리 경로")
    parser.add_argument(
        "--source", choices=["garmin", "strava"], default="garmin",
        help="데이터 소스 (기본: garmin)",
    )
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="하위 디렉터리 재귀 탐색")
    parser.add_argument(
        "--strava-archive", action="store_true",
        help="Strava archive 모드: activities.csv + activities/ 폴더 통합 임포트",
    )
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()
    target = Path(args.path)

    if args.strava_archive:
        from src.import_export.strava_archive import import_strava_archive
        with sqlite3.connect(db_path) as conn:
            stats = import_strava_archive(conn, target)
        print(
            f"Strava archive 임포트 완료: "
            f"+{stats['inserted']} 신규, {stats['skipped']} 중복, "
            f"{stats['file_linked']} 파일 연결, {stats['csv_only']} CSV-only, "
            f"{stats['gz_ok']} gz 해제, {stats['errors']} 오류"
        )
        return

    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = "**/*" if args.recursive else "*"
        files = [
            f for f in target.glob(pattern)
            if f.is_file() and any(
                "".join(f.suffixes).lower().endswith(ext) for ext in _SUPPORTED
            )
        ]
    else:
        print(f"경로를 찾을 수 없습니다: {target}")
        return

    print(f"발견된 파일: {len(files)}개")
    success = 0
    with sqlite3.connect(db_path) as conn:
        for f in sorted(files):
            if import_file(conn, f, args.source):
                success += 1
                print(f"  임포트: {f.name}")
        conn.commit()

    print(f"\n임포트 완료: {success}/{len(files)}개")


if __name__ == "__main__":
    main()
