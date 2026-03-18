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
            # Strava는 러닝 케이던스를 절반 값으로 보고
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

            # 상세 + 스트림
            try:
                detail = api.get(f"{_BASE_URL}/activities/{source_id}", headers=headers)
                suffer_score = detail.get("suffer_score")
                if suffer_score is not None:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'strava', 'suffer_score', ?)""",
                        (activity_id, float(suffer_score)),
                    )
            except Exception as e:
                print(f"[strava] 상세 조회 실패 {source_id}: {e}")

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
