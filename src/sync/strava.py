"""Strava 데이터 동기화 (OAuth2)."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.utils import api
from src.utils.config import update_service_config
from src.utils.dedup import assign_group_id
from src.utils.sync_policy import POLICIES, should_reduce_expensive_calls
from src.utils.sync_state import get_rate_state, mark_finished


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

    # 공유 헬퍼로 config.json 업데이트 (ad hoc 파일 직접 쓰기 제거)
    try:
        update_service_config("strava", {
            "access_token": strava["access_token"],
            "refresh_token": strava["refresh_token"],
            "expires_at": strava["expires_at"],
        })
    except Exception as e:
        print(f"[strava] 토큰 저장 실패 (동기화는 계속됨): {e}")

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


def _parse_rate_limit(resp_headers: dict) -> dict:
    """Strava 응답 헤더에서 rate limit 상태 추출.

    Strava 헤더 형식:
      X-RateLimit-Limit: 200,2000
      X-RateLimit-Usage: 150,1500
    """
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
    token = _refresh_token(config)
    headers = {"Authorization": f"Bearer {token}"}

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
    rate_state = get_rate_state("strava")  # 이전 저장된 rate 상태 로드
    partial = False

    while True:
        try:
            params: dict = {"after": after, "per_page": 30, "page": page}
            if before is not None:
                params["before"] = before
            activity_summaries, resp_headers = api.get_with_headers(
                f"{_BASE_URL}/athlete/activities",
                headers=headers,
                params=params,
            )
            # rate limit 상태 갱신
            new_rate = _parse_rate_limit(resp_headers)
            if new_rate:
                rate_state = new_rate
        except api.ApiError as e:
            if e.status_code == 429:
                print("[strava] ⚠️ Strava 요청 제한(429) 발생. 15분 후 재시도를 권장합니다.")
                from src.utils.sync_state import set_retry_after
                set_retry_after("strava", 900)  # 15분 후 재시도
                partial = True
            raise

        if not activity_summaries:
            break

        # 80% 이상 소진 시 고비용 호출 생략
        skip_expensive = should_reduce_expensive_calls("strava", rate_state)
        if skip_expensive:
            print(
                f"[strava] ⚠️ API 사용량이 한도({rate_state.get('usage')}/{rate_state.get('limit')})에 "
                f"근접했습니다. 상세/스트림 조회를 건너뜁니다."
            )

        for act in activity_summaries:
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
                    """INSERT OR IGNORE INTO activity_summaries
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

            if skip_expensive:
                # 한도 근접 시 상세/스트림 생략 — 다음 동기화로 이월
                partial = True
                assign_group_id(conn, activity_id)
                time.sleep(policy.per_request_sleep_sec)
                continue

            # 상세 조회 (suffer_score + best_efforts)
            try:
                detail = api.get(f"{_BASE_URL}/activities/{source_id}", headers=headers)

                suffer_score = detail.get("suffer_score")
                if suffer_score is not None:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'strava', 'relative_effort', ?)""",
                        (activity_id, float(suffer_score)),
                    )

                best_efforts = _extract_best_efforts(detail.get("best_efforts") or [])
                if best_efforts:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_json)
                           VALUES (?, 'strava', 'best_efforts', ?)""",
                        (activity_id, json.dumps(best_efforts)),
                    )
            except api.ApiError as e:
                if e.status_code == 429:
                    print(f"[strava] ⚠️ rate limit — 상세 조회 중단 (source_id={source_id})")
                    from src.utils.sync_state import set_retry_after
                    set_retry_after("strava", 900)
                    partial = True
                    conn.commit()
                    if not bg_mode:
                        mark_finished("strava", count=count, partial=True,
                                      error="Strava 요청 제한(429). 약 15분 후 재시도하세요.",
                                      rate_state=rate_state)
                    return count
                print(f"[strava] 상세 조회 실패 {source_id}: {e}")
            except Exception as e:
                print(f"[strava] 상세 조회 실패 {source_id}: {e}")

            # 스트림 저장 (한도 재확인)
            if not should_reduce_expensive_calls("strava", rate_state):
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
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_json)
                           VALUES (?, 'strava', 'stream_file', ?)""",
                        (activity_id, str(stream_path)),
                    )
                except Exception as e:
                    print(f"[strava] 스트림 저장 실패 {source_id}: {e}")

            assign_group_id(conn, activity_id)
            time.sleep(policy.per_request_sleep_sec)

        if len(activity_summaries) < 30:
            break
        page += 1

    conn.commit()
    if not bg_mode:
        mark_finished("strava", count=count, partial=partial, rate_state=rate_state)
    if partial:
        print(
            "[strava] ⚠️ 호출 제한에 근접하여 일부 상세 데이터는 다음 동기화로 미뤘습니다."
        )
    return count


def check_strava_connection(config: dict) -> dict:
    """Strava 연결 상태 확인.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    import time as _time
    strava = config.get("strava", {})
    has_client = bool(strava.get("client_id") and strava.get("client_secret"))
    has_refresh = bool(strava.get("refresh_token"))
    access_token = strava.get("access_token")
    expires_at = strava.get("expires_at", 0)

    if not has_client:
        return {
            "ok": False,
            "status": "설정 누락",
            "detail": "client_id / client_secret 미설정. /settings에서 연동하세요.",
        }
    if not has_refresh:
        return {
            "ok": False,
            "status": "재연동 필요",
            "detail": "refresh_token 없음. /connect/strava에서 OAuth 연동을 완료하세요.",
        }
    if not access_token:
        return {
            "ok": True,
            "status": "갱신 필요",
            "detail": "access_token 없음. 다음 sync 시 자동 갱신됩니다.",
        }
    if expires_at and expires_at < _time.time():
        return {
            "ok": True,
            "status": "토큰 만료",
            "detail": "access_token 만료. 다음 sync 시 자동 갱신됩니다.",
        }
    return {
        "ok": True,
        "status": "연결됨",
        "detail": f"토큰 유효. 만료: {expires_at}",
    }
