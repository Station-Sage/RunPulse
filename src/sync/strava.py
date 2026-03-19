"""Strava 데이터 동기화 (OAuth2)."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.utils import api
from src.utils.dedup import assign_group_id


_BASE_URL = "https://www.strava.com/api/v3"
_TOKEN_URL = "https://www.strava.com/oauth/token"
_STREAMS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sources" / "strava"

# best_efforts에서 추출할 이름-거리 매핑 (미터)
_BEST_EFFORT_DISTANCES = {
    "400m": 400, "1/2 mile": 804, "1k": 1000,
    "1 mile": 1609, "2 mile": 3218, "5k": 5000,
    "10k": 10000, "15k": 15000, "10 mile": 16090,
    "20k": 20000, "Half-Marathon": 21097, "Marathon": 42195,
}


def _refresh_token(config: dict) -> str:
    """access_token 만료 시 갱신. config dict 업데이트.

    Args:
        config: 전체 설정 딕셔너리.

    Returns:
        유효한 access_token.
    """
    strava = config["strava"]
    if strava.get("expires_at", 0) > time.time():
        return strava["access_token"]

    result = api.post(
        _TOKEN_URL,
        data={
            "client_id": strava["client_id"],
            "client_secret": strava["client_secret"],
            "refresh_token": strava["refresh_token"],
            "grant_type": "refresh_token",
        },
    )

    strava["access_token"] = result["access_token"]
    strava["refresh_token"] = result["refresh_token"]
    strava["expires_at"] = result["expires_at"]

    # config.json에 업데이트 저장
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            full = json.load(f)
        full["strava"] = strava
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(full, f, indent=2, ensure_ascii=False)

    return strava["access_token"]


def _extract_best_efforts(best_efforts: list) -> dict:
    """Strava best_efforts 배열에서 거리별 최고 기록 추출 (초 단위).

    Args:
        best_efforts: Strava activity detail의 best_efforts 배열.

    Returns:
        {"1k": 245, "5k": 1320, ...} 형태의 딕셔너리.
    """
    result = {}
    if not best_efforts:
        return result

    # 거리→키 역매핑
    dist_to_key = {v: k for k, v in _BEST_EFFORT_DISTANCES.items()}

    for effort in best_efforts:
        dist = effort.get("distance")
        elapsed = effort.get("elapsed_time")
        if dist and elapsed and dist in dist_to_key:
            result[dist_to_key[dist]] = int(elapsed)

    return result


def sync_activities(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Strava 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        새로 저장된 활동 수.
    """
    token = _refresh_token(config)
    headers = {"Authorization": f"Bearer {token}"}
    after = int((datetime.now() - timedelta(days=days)).timestamp())
    count = 0
    page = 1

    while True:
        activities = api.get(
            f"{_BASE_URL}/athlete/activities",
            headers=headers,
            params={"after": after, "per_page": 30, "page": page},
        )
        if not activities:
            break

        for act in activities:
            source_id = str(act.get("id", ""))
            distance_km = (act.get("distance") or 0) / 1000
            duration_sec = int(act.get("moving_time") or 0)
            avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

            # Strava는 stride/min 반환 → steps/min으로 환산 (* 2)
            cadence = act.get("average_cadence")
            if cadence:
                cadence = int(cadence * 2)

            start_time = act.get("start_date_local", "")

            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO activities
                       (source, source_id, activity_type, start_time, distance_km,
                        duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                        elevation_gain, calories, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "strava", source_id,
                        act.get("type", "Run").lower(),
                        start_time, distance_km, duration_sec, avg_pace,
                        act.get("average_heartrate"), act.get("max_heartrate"),
                        cadence, act.get("total_elevation_gain"),
                        act.get("calories"), act.get("name"),
                    ),
                )
            except sqlite3.Error as e:
                print(f"[strava] 활동 삽입 실패 {source_id}: {e}")
                continue

            if cursor.rowcount == 0:
                continue

            activity_id = cursor.lastrowid
            count += 1

            # 상세 조회 (suffer_score + best_efforts)
            try:
                detail = api.get(f"{_BASE_URL}/activities/{source_id}", headers=headers)

                suffer_score = detail.get("suffer_score")
                if suffer_score is not None:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'strava', 'relative_effort', ?)""",
                        (activity_id, float(suffer_score)),
                    )

                # best_efforts 추출 및 저장
                best_efforts = _extract_best_efforts(detail.get("best_efforts") or [])
                if best_efforts:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_json)
                           VALUES (?, 'strava', 'best_efforts', ?)""",
                        (activity_id, json.dumps(best_efforts)),
                    )

            except Exception as e:
                print(f"[strava] 상세 조회 실패 {source_id}: {e}")

            # 스트림 저장
            try:
                streams = api.get(
                    f"{_BASE_URL}/activities/{source_id}/streams",
                    headers=headers,
                    params={"keys": "time,distance,heartrate,velocity_smooth,cadence,altitude"},
                )
                _STREAMS_DIR.mkdir(parents=True, exist_ok=True)
                stream_path = _STREAMS_DIR / f"{source_id}.json"
                with open(stream_path, "w", encoding="utf-8") as f:
                    json.dump(streams, f)
                conn.execute(
                    """INSERT INTO source_metrics
                       (activity_id, source, metric_name, metric_json)
                       VALUES (?, 'strava', 'stream_file', ?)""",
                    (activity_id, str(stream_path)),
                )
            except Exception as e:
                print(f"[strava] 스트림 저장 실패 {source_id}: {e}")

            assign_group_id(conn, activity_id)

        if len(activities) < 30:
            break
        page += 1

    conn.commit()
    return count
