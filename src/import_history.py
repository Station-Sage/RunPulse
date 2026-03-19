"""GPX/FIT 파일 일괄 파싱 및 DB 삽입."""

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import gpxpy
import fitparse

from src.db_setup import get_db_path, init_db
from src.utils.dedup import assign_group_id


def parse_gpx(file_path: Path) -> dict | None:
    """GPX 파일을 파싱하여 활동 dict 반환.

    Args:
        file_path: GPX 파일 경로.

    Returns:
        활동 데이터 dict 또는 파싱 실패 시 None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    if not gpx.tracks:
        return None

    # 거리 계산
    distance_m = gpx.length_3d() or gpx.length_2d()
    distance_km = distance_m / 1000 if distance_m else 0

    # 시간 계산
    bounds = gpx.get_time_bounds()
    if not bounds.start_time:
        return None

    start_time = bounds.start_time.isoformat()
    duration_sec = 0
    if bounds.end_time and bounds.start_time:
        duration_sec = int((bounds.end_time - bounds.start_time).total_seconds())

    avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

    # HR (확장 데이터에서 추출 시도)
    hr_values: list[int] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                for ext in point.extensions:
                    # Garmin HR 확장
                    hr_elem = ext.find(".//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr")
                    if hr_elem is not None and hr_elem.text:
                        hr_values.append(int(hr_elem.text))

    avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else None
    max_hr = max(hr_values) if hr_values else None

    # 고도
    uphill, _ = gpx.get_uphill_downhill()

    return {
        "start_time": start_time,
        "distance_km": round(distance_km, 2),
        "duration_sec": duration_sec,
        "avg_pace_sec_km": avg_pace,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "elevation_gain": round(uphill, 1) if uphill else None,
        "description": gpx.tracks[0].name or file_path.stem,
    }


def parse_fit(file_path: Path) -> dict | None:
    """FIT 파일을 파싱하여 활동 dict 반환.

    Args:
        file_path: FIT 파일 경로.

    Returns:
        활동 데이터 dict 또는 파싱 실패 시 None.
    """
    fit = fitparse.FitFile(str(file_path))

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


def import_file(
    conn: sqlite3.Connection, file_path: Path, source: str,
) -> bool:
    """단일 파일 파싱 후 DB 삽입.

    Args:
        conn: SQLite 연결.
        file_path: GPX 또는 FIT 파일 경로.
        source: 데이터 소스 ("garmin" 또는 "strava").

    Returns:
        성공 시 True.
    """
    ext = file_path.suffix.lower()
    if ext == ".gpx":
        data = parse_gpx(file_path)
    elif ext == ".fit":
        data = parse_fit(file_path)
    else:
        print(f"지원하지 않는 파일 형식: {file_path}")
        return False

    if not data:
        print(f"파싱 실패: {file_path}")
        return False

    source_id = f"import_{file_path.stem}"

    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO activities
               (source, source_id, activity_type, start_time, distance_km,
                duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                elevation_gain, calories, description)
               VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source, source_id,
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


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="GPX/FIT 파일 일괄 임포트")
    parser.add_argument("path", help="파일 또는 디렉터리 경로")
    parser.add_argument(
        "--source", choices=["garmin", "strava"], default="garmin",
        help="데이터 소스 (기본: garmin)",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true",
        help="하위 디렉터리 재귀 탐색",
    )
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()
    target = Path(args.path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = "**/*" if args.recursive else "*"
        files = [f for f in target.glob(pattern) if f.suffix.lower() in (".gpx", ".fit")]
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
