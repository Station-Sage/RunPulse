"""가져오기 업로드 판별 — CSV 머리글·ZIP 경로·소스 일치 검사 (V2-AUDIT D-11~D-14).

판별은 파일을 실제로 읽어 본다: CSV 는 전체 행을 훑어 깨진 필드(128KB 초과 등)를 400 으로 걸러내고,
ZIP 은 압축을 풀기 전에 경로 이탈(`../`, 절대 경로) 항목을 거부한다. 소스(garmin/strava)를 주면
파일 종류와 맞는지도 본다(Strava 파일을 Garmin 으로 올리는 실수 방지).
"""
from __future__ import annotations

import csv
import zipfile
from pathlib import Path, PurePosixPath

FILE_EXTS = (".fit", ".gpx", ".tcx")
_GARMIN_TYPE_COLS = ("활동 종류", "활동 유형")
_KIND_SOURCE = {"strava_archive": "strava", "strava_csv": "strava", "garmin_csv": "garmin"}
_NAME = {"garmin": "Garmin", "strava": "Strava"}


def is_media(name: str) -> bool:
    n = name.lower().removesuffix(".gz")
    return n.endswith(FILE_EXTS)


def unsafe_member(name: str) -> bool:
    """압축 항목 이름이 풀 위치 밖을 가리키면 True(`../x`, `/etc/x`, `C:\\x`)."""
    p = PurePosixPath(name.replace("\\", "/"))
    return p.is_absolute() or ".." in p.parts or (len(name) > 1 and name[1] == ":")


def _zip_kind(path: Path) -> tuple[str | None, str | None]:
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except (zipfile.BadZipFile, OSError):
        return None, "유효한 ZIP 파일이 아니에요"
    if any(unsafe_member(n) for n in names):
        return None, "ZIP 안에 허용되지 않는 경로(../ 등)가 있어 열지 않았어요"
    if any(n.endswith("activities.csv") for n in names):
        return "strava_archive", None
    return None, "activities.csv가 없어요. Strava 아카이브 ZIP이 맞는지 확인해 주세요"


def _csv_kind(path: Path) -> tuple[str | None, str | None]:
    try:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.reader(f)
            head = [h.strip() for h in next(reader, [])]
            for _ in reader:  # 전체를 훑어 깨진 행을 미리 찾는다(임포터에서 500 이 나지 않게)
                pass
    except csv.Error:
        return None, "CSV를 읽지 못했어요. 너무 긴 칸이 있거나 형식이 깨졌어요"
    if "Activity Date" in head:
        return "strava_csv", None
    if "날짜" in head and any(c in head for c in _GARMIN_TYPE_COLS):
        return "garmin_csv", None
    return None, ("알 수 없는 CSV 형식이에요. Garmin Connect 활동 내보내기(한국어)나 "
                  "Strava activities.csv를 올려 주세요")


def extension_hint(source: str | None) -> str:
    """D-14: 고른 소스에 맞는 허용 파일 안내."""
    if source == "garmin":
        return "Garmin 활동 CSV 한 개, 또는 FIT/GPX/TCX(.gz) 파일만 올릴 수 있어요"
    if source == "strava":
        return "Strava ZIP·CSV 한 개, 또는 FIT/GPX/TCX(.gz) 파일만 올릴 수 있어요"
    return "Strava ZIP, Garmin·Strava CSV 한 개, 또는 FIT/GPX/TCX(.gz) 파일만 올릴 수 있어요"


def detect_kind(paths: list[Path], source: str | None = None) -> tuple[str | None, str | None]:
    """업로드 파일들 → (kind, 오류). kind: strava_archive | strava_csv | garmin_csv | files."""
    if not paths:
        return None, "파일을 선택해 주세요"
    kind, err = None, None
    if len(paths) == 1 and paths[0].suffix.lower() == ".zip":
        kind, err = _zip_kind(paths[0])
    elif len(paths) == 1 and paths[0].suffix.lower() == ".csv":
        kind, err = _csv_kind(paths[0])
    elif all(is_media(p.name) for p in paths):
        kind = "files"
    else:
        err = extension_hint(source)
    if err:
        return None, err
    want = _KIND_SOURCE.get(kind)
    if source and want and want != source:
        return None, f"{_NAME[want]} 파일로 보여요. 가져올 소스를 {_NAME[want]}(으)로 바꿔 주세요"
    return kind, None
