"""Strava 활동 동기화 (Activity List + Detail + Streams)."""

import json
import sqlite3
import time
from datetime import datetime, timedelta

from src.utils import api
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields
from src.utils.raw_payload import store_raw_payload as _store_rp
from src.utils.sync_policy import POLICIES, should_reduce_expensive_calls
from src.utils.sync_state import get_rate_state, mark_finished

from .strava_auth import _BASE_URL, refresh_token

_STREAM_KEYS = "time,distance,heartrate,velocity_smooth,cadence,altitude,watts,temp,latlng,grade_smooth"


def _store_raw(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload: dict,
    activity_id: int | None = None,
) -> None:
    _store_rp(conn, "strava", entity_type, entity_id, payload, activity_id=activity_id)


def _parse_rate_limit(resp_headers: dict) -> dict:
    """Strava 응답 헤더에서 rate limit 상태 추출."""
    state: dict = {}
    try:
        limit_hdr = resp_headers.get("x-ratelimit-limit", "")
        usage_hdr = resp_headers.get("x-ratelimit-usage", "")
        if limit_hdr and usage_hdr:
            limits = [int(x) for x in limit_hdr.split(",")]
            usages = [int(x) for x in usage_hdr.split(",")]
            state["limit"] = limits[0] if limits else 0
            state["usage"] = usages[0] if usages else 0
            state["daily_limit"] = limits[1] if len(limits) > 1 else 0
            state["daily_usage"] = usages[1] if len(usages) > 1 else 0
    except Exception:
        pass
    return state


def _sync_activity_laps(
    conn: sqlite3.Connection, detail: dict, activity_id: int
) -> None:
    """activity detail에서 laps 추출 → activity_laps 저장."""
    for lap in detail.get("laps") or []:
        lap_dist = (lap.get("distance") or 0) / 1000.0
        lap_dur = lap.get("elapsed_time") or lap.get("moving_time")
        lap_pace = round(lap_dur / lap_dist) if lap_dist > 0 and lap_dur else None
        cadence = lap.get("average_cadence")
        if cadence:
            cadence = int(cadence * 2)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_laps
                   (activity_id, source, lap_index, distance_km, duration_sec,
                    avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    elevation_gain, avg_power, avg_speed_ms, max_speed_ms)
                   VALUES (?, 'strava', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    activity_id,
                    lap.get("lap_index") or lap.get("split"),
                    lap_dist, lap_dur, lap_pace,
                    lap.get("average_heartrate"), lap.get("max_heartrate"),
                    cadence,
                    lap.get("total_elevation_gain"),
                    lap.get("average_watts"),
                    lap.get("average_speed"),
                    lap.get("max_speed"),
                ),
            )
        except Exception:
            pass


def _sync_activity_best_efforts(
    conn: sqlite3.Connection, detail: dict, activity_id: int
) -> None:
    """activity detail에서 best_efforts 추출 → activity_best_efforts 저장."""
    for effort in detail.get("best_efforts") or []:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_best_efforts
                   (activity_id, source, name, distance_m, elapsed_sec, moving_sec,
                    start_index, end_index, pr_rank)
                   VALUES (?, 'strava', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    activity_id,
                    effort.get("name"),
                    effort.get("distance"),
                    effort.get("elapsed_time"),
                    effort.get("moving_time"),
                    effort.get("start_index"),
                    effort.get("end_index"),
                    effort.get("pr_rank"),
                ),
            )
        except Exception:
            pass


def _sync_activity_streams(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    headers: dict,
    force: bool = False,
) -> int:
    """Strava 활동 스트림 → activity_streams 저장.

    force=True면 기존 데이터 삭제 후 재수집.
    """
    if not force:
        existing = conn.execute(
            "SELECT COUNT(*) FROM activity_streams WHERE activity_id = ? AND source = 'strava'",
            (activity_id,),
        ).fetchone()[0]
        if existing > 0:
            return 0

    if force:
        conn.execute(
            "DELETE FROM activity_streams WHERE activity_id = ? AND source = 'strava'",
            (activity_id,),
        )

    try:
        streams = api.get(
            f"{_BASE_URL}/activities/{source_id}/streams",
            headers=headers,
            params={"keys": _STREAM_KEYS, "key_by_type": "true"},
        )
    except api.ApiError as e:
        if e.status_code != 404:
            print(f"[strava] 스트림 조회 실패 {source_id}: {e}")
        return 0
    except Exception as e:
        print(f"[strava] 스트림 조회 실패 {source_id}: {e}")
        return 0

    if not streams:
        return 0

    # key_by_type=true → dict, 아니면 list
    if isinstance(streams, list):
        stream_dict = {s["type"]: s for s in streams if isinstance(s, dict) and "type" in s}
    else:
        stream_dict = streams

    rows = []
    for stream_type, stream_obj in stream_dict.items():
        data = stream_obj.get("data") if isinstance(stream_obj, dict) else stream_obj
        if data:
            rows.append((
                activity_id, "strava", stream_type,
                json.dumps(data),
                len(data),
            ))

    if rows:
        conn.executemany(
            """INSERT OR IGNORE INTO activity_streams
               (activity_id, source, stream_type, data_json, original_size)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )

    return len(rows)


def _sync_activity_zones(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    headers: dict,
) -> None:
    """Strava 활동 구간 분포 → activity_detail_metrics 저장."""
    try:
        zones = api.get(
            f"{_BASE_URL}/activities/{source_id}/zones",
            headers=headers,
        )
    except api.ApiError as e:
        if e.status_code not in (402, 404):
            print(f"[strava] zones 조회 실패 {source_id}: {e}")
        return
    except Exception as e:
        print(f"[strava] zones 조회 실패 {source_id}: {e}")
        return

    if not zones:
        return

    for zone_block in zones if isinstance(zones, list) else [zones]:
        zone_type = zone_block.get("type")  # "heartrate" or "power"
        distribution = zone_block.get("distribution_buckets") or []
        score = zone_block.get("score")

        if score is not None:
            metric_name = f"{zone_type}_zone_score" if zone_type else "zone_score"
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_value)
                       VALUES (?, 'strava', ?, ?)""",
                    (activity_id, metric_name, float(score)),
                )
            except (sqlite3.Error, TypeError, ValueError):
                pass

        for i, bucket in enumerate(distribution):
            sec = bucket.get("time") or bucket.get("seconds")
            prefix = zone_type or "zone"
            if sec is not None:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'strava', ?, ?)""",
                        (activity_id, f"{prefix}_zone_{i + 1}_sec", float(sec)),
                    )
                except (sqlite3.Error, TypeError, ValueError):
                    pass

        if distribution:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_json)
                       VALUES (?, 'strava', ?, ?)""",
                    (activity_id, f"{zone_type or 'zones'}_distribution",
                     json.dumps(distribution)),
                )
            except sqlite3.Error:
                pass


def sync_activity_detail(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    headers: dict,
) -> None:
    """Strava 활동 상세 조회 및 저장 (laps, best_efforts, extra metrics).

    신규 활동 + 기존 활동 중 detail 누락 시 모두 호출.
    """
    try:
        detail = api.get(f"{_BASE_URL}/activities/{source_id}", headers=headers)
        _store_raw(conn, "activity_detail", source_id, detail, activity_id=activity_id)
    except api.ApiError as e:
        if e.status_code == 429:
            print(f"[strava] ⚠️ rate limit — 상세 조회 중단 (source_id={source_id})")
            from src.utils.sync_state import set_retry_after
            set_retry_after("strava", 900)
        else:
            print(f"[strava] 상세 조회 실패 {source_id}: {e}")
        return
    except Exception as e:
        print(f"[strava] 상세 조회 실패 {source_id}: {e}")
        return

    # activity_summaries 추가 필드 업데이트 (detail에서만 얻을 수 있는 것)
    update_changed_fields(conn, "strava", source_id, {
        "suffer_score": detail.get("suffer_score"),
        "description": detail.get("description"),
        "max_elevation": detail.get("elev_high"),
        "min_elevation": detail.get("elev_low"),
        "steps": detail.get("total_steps"),
        "normalized_power": detail.get("weighted_average_watts"),
    })

    # laps → activity_laps
    _sync_activity_laps(conn, detail, activity_id)

    # best_efforts → activity_best_efforts
    _sync_activity_best_efforts(conn, detail, activity_id)

    # zones → activity_detail_metrics
    _sync_activity_zones(conn, source_id, activity_id, headers)

    # splits_metric → detail_metrics JSON
    splits_metric = detail.get("splits_metric")
    if splits_metric:
        conn.execute(
            """INSERT OR IGNORE INTO activity_detail_metrics
               (activity_id, source, metric_name, metric_json)
               VALUES (?, 'strava', 'splits_metric', ?)""",
            (activity_id, json.dumps(splits_metric)),
        )

    # 추가 수치 지표
    for mname, mval in {
        "suffer_score": detail.get("suffer_score"),
        "avg_grade_pct": detail.get("average_grade"),
        "max_grade_pct": detail.get("max_grade"),
        "kilojoules": detail.get("kilojoules"),
        "normalized_power_w": detail.get("weighted_average_watts"),
        "max_watts": detail.get("max_watts"),
    }.items():
        if mval is not None:
            conn.execute(
                """INSERT OR IGNORE INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_value)
                   VALUES (?, 'strava', ?, ?)""",
                (activity_id, mname, float(mval)),
            )


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    from_date: str | None = None,
    to_date: str | None = None,
    bg_mode: bool = False,
) -> int:
    """Strava 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시 사용).
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일 (YYYY-MM-DD). None이면 오늘.
        bg_mode: True이면 mark_finished 호출 생략.

    Returns:
        새로 저장된 활동 수.
    """
    policy = POLICIES["strava"]
    token = refresh_token(config)
    headers = {"Authorization": f"Bearer {token}"}
    force_streams = bool(from_date)

    if from_date:
        after = int(datetime.fromisoformat(from_date).timestamp())
        before = int(
            (datetime.fromisoformat(to_date) + timedelta(days=1)).timestamp()
        ) if to_date else None
    else:
        after = int((datetime.now() - timedelta(days=days)).timestamp())
        before = None

    count = 0
    page = 1
    rate_state = get_rate_state("strava")
    partial = False

    while True:
        try:
            params: dict = {"after": after, "per_page": 30, "page": page}
            if before is not None:
                params["before"] = before
            activity_list, resp_headers = api.get_with_headers(
                f"{_BASE_URL}/athlete/activities",
                headers=headers,
                params=params,
            )
            new_rate = _parse_rate_limit(resp_headers)
            if new_rate:
                rate_state = new_rate
        except api.ApiError as e:
            if e.status_code == 429:
                print("[strava] ⚠️ Strava 요청 제한(429) 발생. 15분 후 재시도를 권장합니다.")
                from src.utils.sync_state import set_retry_after
                set_retry_after("strava", 900)
                partial = True
            raise

        if not activity_list:
            break

        skip_expensive = should_reduce_expensive_calls("strava", rate_state)
        if skip_expensive:
            print(
                f"[strava] ⚠️ API 사용량이 한도({rate_state.get('usage')}/{rate_state.get('limit')})에 "
                f"근접했습니다. 상세/스트림 조회를 건너뜁니다."
            )

        for act in activity_list:
            source_id = str(act.get("id", ""))
            distance_km = (act.get("distance") or 0) / 1000
            duration_sec = int(act.get("moving_time") or 0)
            avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None
            cadence = act.get("average_cadence")
            if cadence:
                cadence = int(cadence * 2)
            start_time = act.get("start_date_local", "").rstrip("Z")
            start_latlng = act.get("start_latlng") or [None, None]
            end_latlng = act.get("end_latlng") or [None, None]

            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO activity_summaries
                       (source, source_id, name, activity_type, sport_type, start_time,
                        distance_km, duration_sec, moving_time_sec, elapsed_time_sec,
                        avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                        avg_speed_ms, max_speed_ms, elevation_gain, calories,
                        start_lat, start_lon, end_lat, end_lon,
                        kudos_count, achievement_count, pr_count,
                        suffer_score, strava_gear_id, avg_power, normalized_power,
                        workout_type, trainer, commute)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "strava", source_id,
                        act.get("name"),
                        act.get("type", "Run").lower(),
                        act.get("sport_type"),
                        start_time,
                        distance_km, duration_sec,
                        act.get("moving_time"),
                        act.get("elapsed_time"),
                        avg_pace,
                        act.get("average_heartrate"), act.get("max_heartrate"),
                        cadence,
                        act.get("average_speed"), act.get("max_speed"),
                        act.get("total_elevation_gain"),
                        act.get("calories"),
                        start_latlng[0], start_latlng[1],
                        end_latlng[0], end_latlng[1],
                        act.get("kudos_count"),
                        act.get("achievement_count"),
                        act.get("pr_count"),
                        act.get("suffer_score"),
                        act.get("gear_id"),
                        act.get("average_watts"),
                        act.get("weighted_average_watts"),
                        act.get("workout_type"),
                        1 if act.get("trainer") else None,
                        1 if act.get("commute") else None,
                    ),
                )
            except sqlite3.Error as e:
                print(f"[strava] 활동 삽입 실패 {source_id}: {e}")
                continue

            if cursor.rowcount == 0:
                existing_id = update_changed_fields(conn, "strava", source_id, {
                    "name": act.get("name"),
                    "avg_hr": act.get("average_heartrate"),
                    "max_hr": act.get("max_heartrate"),
                    "avg_cadence": cadence,
                    "avg_speed_ms": act.get("average_speed"),
                    "max_speed_ms": act.get("max_speed"),
                    "elevation_gain": act.get("total_elevation_gain"),
                    "calories": act.get("calories"),
                    "kudos_count": act.get("kudos_count"),
                    "achievement_count": act.get("achievement_count"),
                    "pr_count": act.get("pr_count"),
                    "suffer_score": act.get("suffer_score"),
                    "strava_gear_id": act.get("gear_id"),
                    "avg_power": act.get("average_watts"),
                    "workout_type": act.get("workout_type"),
                    "trainer": 1 if act.get("trainer") else None,
                    "commute": 1 if act.get("commute") else None,
                })
                if existing_id:
                    _store_raw(conn, "activity_summary", source_id, act, activity_id=existing_id)
                    if not skip_expensive:
                        has_detail = conn.execute(
                            "SELECT 1 FROM activity_detail_metrics "
                            "WHERE activity_id = ? AND source = 'strava' LIMIT 1",
                            (existing_id,),
                        ).fetchone()
                        if not has_detail:
                            sync_activity_detail(conn, source_id, existing_id, headers)
                            _sync_activity_streams(conn, source_id, existing_id, headers, force=force_streams)
                continue

            activity_id = cursor.lastrowid
            count += 1
            _store_raw(conn, "activity_summary", source_id, act, activity_id=activity_id)

            if skip_expensive:
                partial = True
                assign_group_id(conn, activity_id)
                time.sleep(policy.per_request_sleep_sec)
                continue

            sync_activity_detail(conn, source_id, activity_id, headers)
            _sync_activity_streams(conn, source_id, activity_id, headers, force=force_streams)

            assign_group_id(conn, activity_id)
            time.sleep(policy.per_request_sleep_sec)

        if len(activity_list) < 30:
            break
        page += 1

    conn.commit()
    if not bg_mode:
        mark_finished("strava", count=count, partial=partial, rate_state=rate_state)
    if partial:
        print("[strava] ⚠️ 호출 제한에 근접하여 일부 상세 데이터는 다음 동기화로 미뤘습니다.")
    return count
