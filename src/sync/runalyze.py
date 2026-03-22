"""Runalyze 데이터 동기화 (API Token)."""

import json
import sqlite3
from datetime import datetime, timedelta

from src.utils import api
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields
from src.utils.raw_payload import store_raw_payload as _store_rp
from src.utils.sync_state import get_retry_after_sec, mark_finished, set_retry_after


def _store_raw_payload(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload: dict,
    activity_id: int | None = None,
) -> None:
    """Runalyze raw payload를 raw_source_payloads에 저장/병합."""
    _store_rp(conn, "runalyze", entity_type, entity_id, payload, activity_id=activity_id)


_BASE_URL = "https://runalyze.com/api/v1"

# race prediction 필드 이름 → 거리 키 매핑 (초 단위)
_RACE_PRED_FIELDS = {
    "race_prediction_5000": "5k",
    "race_5k": "5k",
    "race_prediction_10000": "10k",
    "race_10k": "10k",
    "race_prediction_21097": "half",
    "race_half": "half",
    "race_prediction_42195": "full",
    "race_full": "full",
}


def _headers(config: dict) -> dict[str, str]:
    """Runalyze API 인증 헤더."""
    return {"token": config["runalyze"]["token"]}


def _extract_race_pred(detail: dict) -> dict:
    """상세 응답에서 race prediction 데이터 추출."""
    result = {}
    for field, key in _RACE_PRED_FIELDS.items():
        val = detail.get(field)
        if val is not None and key not in result:
            result[key] = int(val)
    return result


def _upsert_daily_fitness(
    conn: sqlite3.Connection,
    date_str: str,
    evo2max: float | None,
    vdot: float | None,
    marathon_shape: float | None,
) -> None:
    """runalyze 피트니스 지표를 daily_fitness에 저장/업데이트."""
    if not any(v is not None for v in [evo2max, vdot, marathon_shape]):
        return
    try:
        conn.execute("""
            INSERT INTO daily_fitness
                (date, source, runalyze_evo2max, runalyze_vdot, runalyze_marathon_shape)
            VALUES (?, 'runalyze', ?, ?, ?)
            ON CONFLICT(date, source) DO UPDATE SET
                runalyze_evo2max = COALESCE(excluded.runalyze_evo2max, runalyze_evo2max),
                runalyze_vdot = COALESCE(excluded.runalyze_vdot, runalyze_vdot),
                runalyze_marathon_shape = COALESCE(
                    excluded.runalyze_marathon_shape, runalyze_marathon_shape
                ),
                updated_at = datetime('now')
        """, (date_str, evo2max, vdot, marathon_shape))
    except sqlite3.OperationalError:
        pass  # daily_fitness 테이블 미생성 환경 (graceful)


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    from_date: str | None = None,
    to_date: str | None = None,
) -> int:
    """Runalyze 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시 사용).
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일 (YYYY-MM-DD). None이면 오늘.

    Returns:
        새로 저장된 활동 수.
    """
    token = config.get("runalyze", {}).get("token", "")
    if not token:
        print("[runalyze] 토큰 없음 — 동기화 건너뜀")
        return 0

    # 이전 403 인증 오류로 인한 대기 중인지 확인
    retry_sec = get_retry_after_sec("runalyze")
    if retry_sec:
        hours = retry_sec // 3600
        print(f"[runalyze] 이전 인증 오류(403)로 인해 동기화 대기 중 (약 {hours}시간 남음). "
              f"토큰 재설정 후 다시 시도하세요.")
        return 0

    headers = _headers(config)
    if from_date:
        cutoff = datetime.fromisoformat(from_date)
        cutoff_end: datetime | None = (
            datetime.fromisoformat(to_date) + timedelta(days=1) if to_date else None
        )
    else:
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_end = None

    # Runalyze API 목록 엔드포인트: /activity (복수형 /activities는 404)
    try:
        activity_summaries = api.get(f"{_BASE_URL}/activity", headers=headers)
    except api.ApiError as e:
        if e.status_code == 403:
            print("[runalyze] 403 Forbidden — 토큰 오류. 24시간 동안 동기화 중단.")
            set_retry_after("runalyze", 86400)
            mark_finished("runalyze", count=0, error="403 Forbidden — 토큰 오류/만료. 토큰을 재발급하세요.")
        else:
            print(f"[runalyze] API 오류 {e.status_code}: {e}")
        return 0
    count = 0

    for act in activity_summaries:
        source_id = str(act.get("id", ""))
        start_time = act.get("datetime", "")

        if not start_time:
            continue

        try:
            act_dt = datetime.fromisoformat(start_time)
            if act_dt < cutoff:
                continue
            if cutoff_end and act_dt >= cutoff_end:
                continue
        except ValueError:
            continue

        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("s") or act.get("duration") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, activity_type, start_time, distance_km,
                    duration_sec, avg_pace_sec_km, avg_hr, max_hr,
                    elevation_gain, calories, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "runalyze", source_id, "running",
                    start_time, distance_km, duration_sec, avg_pace,
                    act.get("heart_rate_avg") or act.get("pulse_avg"),
                    act.get("heart_rate_max") or act.get("pulse_max"),
                    act.get("elevation"), act.get("calories"),
                    act.get("title"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[runalyze] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — 변경/누락 필드 업데이트 + raw payload merge
            existing_id = update_changed_fields(conn, "runalyze", source_id, {
                "avg_hr": act.get("heart_rate_avg") or act.get("pulse_avg"),
                "max_hr": act.get("heart_rate_max") or act.get("pulse_max"),
                "elevation_gain": act.get("elevation"),
                "calories": act.get("calories"),
                "description": act.get("title"),
            })
            if existing_id:
                _store_raw_payload(conn, "activity", source_id, act, activity_id=existing_id)
            continue

        activity_id = cursor.lastrowid
        count += 1
        _store_raw_payload(conn, "activity", source_id, act, activity_id=activity_id)

        # 상세 지표 조회
        try:
            # 올바른 Runalyze 단일 활동 엔드포인트: /activity/{id}
            detail = api.get(f"{_BASE_URL}/activity/{source_id}", headers=headers)
            _store_raw_payload(conn, "activity_detail", source_id, detail, activity_id=activity_id)

            evo2max = detail.get("vo2max")
            vdot = detail.get("vdot")
            trimp = detail.get("trimp")
            marathon_shape = detail.get("marathon_shape") or detail.get("marathonShape")

            # activity_detail_metrics에 저장 (activity 단위)
            metrics = {
                "effective_vo2max": evo2max,
                "vdot": vdot,
                "trimp": trimp,
                "marathon_shape": marathon_shape,
            }
            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'runalyze', ?, ?)""",
                        (activity_id, name, float(value)),
                    )

            # race prediction → activity_detail_metrics (JSON)
            race_pred = _extract_race_pred(detail)
            if race_pred:
                conn.execute(
                    """INSERT INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_json)
                       VALUES (?, 'runalyze', 'race_prediction', ?)""",
                    (activity_id, json.dumps(race_pred)),
                )

            # daily_fitness에도 저장/업데이트
            date_str = start_time[:10]
            _upsert_daily_fitness(
                conn, date_str,
                float(evo2max) if evo2max is not None else None,
                float(vdot) if vdot is not None else None,
                float(marathon_shape) if marathon_shape is not None else None,
            )

        except Exception as e:
            print(f"[runalyze] 상세 조회 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    return count


def check_runalyze_connection(config: dict) -> dict:
    """Runalyze 연결 상태를 실제 API 호출로 확인.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    runalyze_cfg = config.get("runalyze", {})
    token = runalyze_cfg.get("token", "")

    if not token:
        return {
            "ok": False,
            "status": "토큰 없음",
            "detail": "API 토큰 미설정. /settings에서 입력하세요.",
        }

    # 최근 활동 1건 조회로 토큰 유효성 확인 (/activity 단수형이 올바른 경로)
    try:
        result = api.get(
            f"{_BASE_URL}/activity",
            headers={"token": token},
            params={"limit": 1},
            timeout=10,
        )
        return {
            "ok": True,
            "status": "연결됨",
            "detail": "토큰 유효. 활동 데이터 접근 가능.",
        }
    except api.ApiError as e:
        if e.status_code == 401:
            return {
                "ok": False,
                "status": "토큰 오류",
                "detail": "인증 실패 (401). Runalyze 설정 > API 토큰을 확인하세요.",
            }
        if e.status_code == 403:
            return {
                "ok": False,
                "status": "권한 없음",
                "detail": "접근 거부 (403). 토큰이 만료되었거나 Runalyze 프리미엄 플랜이 필요할 수 있습니다.",
            }
        if e.status_code == 404:
            return {
                "ok": False,
                "status": "엔드포인트 불일치",
                "detail": "API 엔드포인트를 찾을 수 없습니다 (404).",
            }
        return {"ok": False, "status": "연결 실패", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "status": "연결 오류", "detail": str(e)}
