from __future__ import annotations

"""Garmin Connect 데이터 동기화."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from garminconnect import Garmin
    # Error 1015 = Too Many Requests (Cloudflare 차단)
    try:
        from garminconnect import GarminConnectTooManyRequestsError
    except ImportError:
        GarminConnectTooManyRequestsError = Exception
except ImportError:  # 선택 의존성 — 테스트/Termux 환경 대응
    Garmin = None
    GarminConnectTooManyRequestsError = Exception

from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields
from src.utils.raw_payload import store_raw_payload as _store_rp
from src.utils.sync_policy import POLICIES
from src.utils.sync_state import mark_finished, set_retry_after


def _tokenstore_path(config: dict) -> Path:
    """garth 토큰 저장소 경로 반환. 기본: ~/.garth"""
    path_str = config.get("garmin", {}).get("tokenstore", "~/.garth")
    return Path(path_str).expanduser()


def _login(config: dict) -> "Garmin":
    """Garmin Connect 인증.

    순서:
    1. garth 토큰 저장소에서 세션 복구 시도
    2. 실패 시 이메일/패스워드 로그인 + 토큰 저장
    """
    if Garmin is None:
        raise ImportError("garminconnect 패키지가 필요합니다: pip install garminconnect")

    garmin_cfg = config.get("garmin", {})
    tokenstore = _tokenstore_path(config)

    # 1단계: 기존 토큰으로 세션 복구 시도
    if tokenstore.exists():
        try:
            client = Garmin()
            client.login(tokenstore=str(tokenstore))
            return client
        except Exception as e:
            print(f"[garmin] 토큰 복구 실패, 이메일/패스워드 로그인 시도: {e}")

    # 2단계: 이메일/패스워드 로그인
    email = garmin_cfg.get("email", "")
    password = garmin_cfg.get("password", "")
    if not email or not password:
        raise ValueError(
            "Garmin 이메일/패스워드 미설정. config.json에 garmin.email/password를 입력하거나 "
            "웹 UI(/settings)에서 연동하세요."
        )

    client = Garmin(email, password)
    client.login()

    # 토큰 저장 (다음 로그인 시 재사용)
    try:
        tokenstore.mkdir(parents=True, exist_ok=True)
        client.garth.dump(str(tokenstore))
        print(f"[garmin] 토큰 저장 완료: {tokenstore}")
    except Exception as e:
        print(f"[garmin] 토큰 저장 실패 (동기화는 계속됨): {e}")

    return client


def check_garmin_connection(config: dict) -> dict:
    """Garmin 연결 상태 확인 — garth 토큰 만료 여부까지 검사.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    tokenstore = _tokenstore_path(config)
    garmin_cfg = config.get("garmin", {})
    has_email = bool(garmin_cfg.get("email"))
    has_password = bool(garmin_cfg.get("password"))

    oauth2_file = tokenstore / "oauth2_token.json"

    if oauth2_file.exists():
        try:
            import garth as _garth
            g = _garth.Client()
            g.load(str(tokenstore))
            token = g.oauth2_token
            if token is None:
                raise ValueError("oauth2_token 없음")
            if token.refresh_expired:
                return {
                    "ok": False,
                    "status": "토큰 만료 (재로그인 필요)",
                    "detail": "refresh_token 만료. /connect/garmin 에서 재로그인하세요.",
                }
            if token.expired:
                return {
                    "ok": True,
                    "status": "토큰 갱신 필요",
                    "detail": "access_token 만료, refresh_token 유효. 다음 sync 시 자동 갱신됩니다.",
                }
            return {
                "ok": True,
                "status": "연결됨",
                "detail": f"토큰 유효. tokenstore: {tokenstore}",
            }
        except Exception as e:
            return {
                "ok": False,
                "status": "토큰 손상",
                "detail": f"토큰 파일 읽기 실패: {e}. 재로그인 필요.",
            }

    if tokenstore.exists() and not oauth2_file.exists():
        return {
            "ok": False,
            "status": "토큰 없음",
            "detail": f"{tokenstore} 디렉터리만 존재. /connect/garmin 에서 로그인하세요.",
        }

    if has_email and has_password:
        return {
            "ok": False,
            "status": "미로그인",
            "detail": "이메일/패스워드 설정됨. /connect/garmin 에서 '저장 + 연결 테스트'로 로그인하세요.",
        }
    return {
        "ok": False,
        "status": "미설정",
        "detail": "이메일/패스워드 미설정 및 토큰 없음. /connect/garmin 에서 연동하세요.",
    }



def _store_raw_payload(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload,
    activity_id: int | None = None,
) -> None:
    """Garmin raw payload를 raw_source_payloads에 저장/병합."""
    _store_rp(conn, "garmin", entity_type, entity_id, payload, activity_id=activity_id)


def _upsert_vo2max(conn: sqlite3.Connection, date_str: str, vo2max: float) -> None:
    """garmin_vo2max를 daily_fitness에 저장/업데이트."""
    try:
        conn.execute("""
            INSERT INTO daily_fitness (date, source, garmin_vo2max)
            VALUES (?, 'garmin', ?)
            ON CONFLICT(date, source) DO UPDATE SET
                garmin_vo2max = excluded.garmin_vo2max,
                updated_at = datetime('now')
        """, (date_str, vo2max))
    except sqlite3.OperationalError:
        pass  # daily_fitness 테이블 미생성 환경 (graceful)


def _upsert_daily_detail_metric(
    conn: sqlite3.Connection,
    date_str: str,
    metric_name: str,
    metric_value=None,
    metric_json=None,
) -> None:
    """Upsert a Garmin daily detail metric."""
    try:
        conn.execute(
            """
            INSERT INTO daily_detail_metrics
                (date, source, metric_name, metric_value, metric_json)
            VALUES
                (?, 'garmin', ?, ?, ?)
            ON CONFLICT(date, source, metric_name) DO UPDATE SET
                metric_value = excluded.metric_value,
                metric_json = excluded.metric_json,
                updated_at = datetime('now')
            """,
            (date_str, metric_name, metric_value, metric_json),
        )
    except sqlite3.OperationalError:
        pass


def _store_daily_detail_metrics(
    conn: sqlite3.Connection,
    date_str: str,
    numeric_metrics: dict[str, float | int | None],
    json_metrics: dict[str, object] | None = None,
) -> None:
    """Store multiple Garmin daily detail metrics."""
    for metric_name, metric_value in numeric_metrics.items():
        if metric_value is not None:
            _upsert_daily_detail_metric(conn, date_str, metric_name, metric_value=metric_value)

    if json_metrics:
        for metric_name, payload in json_metrics.items():
            if payload is not None:
                _upsert_daily_detail_metric(
                    conn,
                    date_str,
                    metric_name,
                    metric_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                )


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: Garmin | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    bg_mode: bool = False,
) -> int:
    """Garmin 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시 사용).
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일 (YYYY-MM-DD). None이면 오늘.
        bg_mode: True이면 mark_running/mark_finished 호출 생략 (bg_sync 관리).

    Returns:
        새로 저장된 활동 수.
    """
    if client is None:
        client = _login(config)

    # 날짜 범위 계산
    if from_date:
        cutoff = datetime.fromisoformat(from_date)
        cutoff_end: datetime | None = (
            datetime.fromisoformat(to_date) + timedelta(days=1)
            if to_date else None
        )
        fetch_days = (datetime.now() - cutoff).days + 2
    else:
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_end = None
        fetch_days = days

    activity_summaries = client.get_activities(0, fetch_days * 3)
    count = 0

    for act in activity_summaries:
        start_time = act.get("startTimeLocal", "")
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

        source_id = str(act.get("activityId", ""))
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("duration") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, activity_type, start_time, distance_km,
                    duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    elevation_gain, calories, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "garmin", source_id,
                    act.get("activityType", {}).get("typeKey", "running"),
                    start_time, distance_km, duration_sec, avg_pace,
                    act.get("averageHR"), act.get("maxHR"),
                    act.get("averageRunningCadenceInStepsPerMinute"),
                    act.get("elevationGain"), act.get("calories"),
                    act.get("activityName"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[garmin] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — 변경/누락 필드 업데이트 + raw payload merge
            existing_id = update_changed_fields(conn, "garmin", source_id, {
                "avg_hr": act.get("averageHR"),
                "max_hr": act.get("maxHR"),
                "avg_cadence": act.get("averageRunningCadenceInStepsPerMinute"),
                "elevation_gain": act.get("elevationGain"),
                "calories": act.get("calories"),
                "description": act.get("activityName"),
            })
            if existing_id:
                _store_raw_payload(conn, "activity_summary", source_id, act, activity_id=existing_id)
            continue

        activity_id = cursor.lastrowid
        count += 1

        _store_raw_payload(
            conn,
            entity_type="activity_summary",
            entity_id=source_id,
            payload=act,
            activity_id=activity_id,
        )

        # 상세 지표 조회
        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            detail = client.get_activity(int(source_id))
            _store_raw_payload(
                conn,
                entity_type="activity_detail",
                entity_id=source_id,
                payload=detail,
                activity_id=activity_id,
            )
            summary = detail.get("summaryDTO", {})
            aerobic_te = detail.get("aerobicTrainingEffect", summary.get("aerobicTrainingEffect"))
            anaerobic_te = detail.get("anaerobicTrainingEffect", summary.get("anaerobicTrainingEffect"))
            training_load = detail.get("activityTrainingLoad", summary.get("activityTrainingLoad"))
            vo2max = detail.get("vO2MaxValue", summary.get("vO2MaxValue"))

            # 운동효과 레이블 (trainingEffectLabel) → workout_label 저장
            te_label = summary.get("trainingEffectLabel") or detail.get("trainingEffectLabel")
            if te_label:
                conn.execute(
                    "UPDATE activity_summaries SET workout_label = ? WHERE id = ?",
                    (te_label, activity_id),
                )

            # aerobic/anaerobic TE 분리 저장 + 하위호환 alias
            avg_power = detail.get("averagePower", summary.get("averagePower"))
            normalized_power = (
                detail.get("normalizedPower")
                or detail.get("normPower")
                or summary.get("normalizedPower")
                or summary.get("normPower")
            )
            steps = (
                detail.get("steps")
                or summary.get("steps")
                or act.get("steps")
            )

            avg_speed = (
                detail.get("averageSpeed")
                or summary.get("averageSpeed")
                or act.get("averageSpeed")
            )
            max_speed = (
                detail.get("maxSpeed")
                or summary.get("maxSpeed")
                or act.get("maxSpeed")
            )
            avg_run_cadence = (
                detail.get("averageRunCadence")
                or summary.get("averageRunCadence")
                or act.get("averageRunningCadenceInStepsPerMinute")
            )
            max_run_cadence = (
                detail.get("maxRunCadence")
                or summary.get("maxRunCadence")
                or act.get("maxRunningCadenceInStepsPerMinute")
            )
            avg_stride_length = (
                detail.get("averageStrideLength")
                or summary.get("averageStrideLength")
            )
            avg_vertical_ratio = (
                detail.get("avgVerticalRatio")
                or summary.get("avgVerticalRatio")
            )
            avg_ground_contact_time = (
                detail.get("avgGroundContactTime")
                or summary.get("avgGroundContactTime")
            )

            hr_zone_times = summary.get("hrTimeInZone", []) or detail.get("hrTimeInZone", [])
            power_zone_times = summary.get("powerTimeInZone", []) or detail.get("powerTimeInZone", [])

            metrics = {
                "training_effect_aerobic": aerobic_te,
                "training_effect_anaerobic": anaerobic_te,
                "training_effect": aerobic_te,  # 하위호환
                "training_load": training_load,
                "vo2max": vo2max,
                "avg_power": avg_power,
                "normalized_power": normalized_power,
                "steps": steps,
                "avg_speed": avg_speed,
                "max_speed": max_speed,
                "avg_run_cadence": avg_run_cadence,
                "max_run_cadence": max_run_cadence,
                "avg_stride_length": avg_stride_length,
                "avg_vertical_ratio": avg_vertical_ratio,
                "avg_ground_contact_time": avg_ground_contact_time,
            }
            for idx, value in enumerate(hr_zone_times[:5], start=1):
                if value is not None:
                    metrics[f"hr_zone_time_{idx}"] = value

            for idx, value in enumerate(power_zone_times[:5], start=1):
                if value is not None:
                    metrics[f"power_zone_time_{idx}"] = value

            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'garmin', ?, ?)""",
                        (activity_id, name, float(value)),
                    )

            # vo2max를 daily_fitness에도 저장
            if vo2max is not None:
                date_str = start_time[:10]  # YYYY-MM-DD
                _upsert_vo2max(conn, date_str, float(vo2max))

        except GarminConnectTooManyRequestsError:
            _handle_rate_limit("garmin", source_id)
            conn.commit()
            if not bg_mode:
                mark_finished("garmin", count=count, partial=True,
                              error="Garmin 요청 제한 발생. 잠시 후 다시 시도하세요.")
            return count
        except Exception as e:
            msg = str(e)
            if "1015" in msg or "Too Many Requests" in msg or "429" in msg:
                _handle_rate_limit("garmin", source_id)
                conn.commit()
                if not bg_mode:
                    mark_finished("garmin", count=count, partial=True,
                                  error="Garmin 요청 제한(Error 1015). 약 15분 후 재시도하세요.")
                return count
            print(f"[garmin] 상세 조회 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    if not bg_mode:
        mark_finished("garmin", count=count)
    return count


def _handle_rate_limit(service: str, source_id: str = "") -> None:
    """rate limit 발생 시 공통 처리 — 메시지 출력 + 재시도 시각 설정."""
    msg = (
        f"[{service}] ⚠️ Garmin 로그인/조회 요청이 짧은 시간에 너무 많이 발생하여 "
        f"일시적으로 제한되었습니다 (Error 1015 / Too Many Requests). "
        f"약 15분 후 다시 시도하세요."
    )
    if source_id:
        msg += f" (마지막 처리 활동: {source_id})"
    print(msg)
    set_retry_after(service, 900)  # 15분


def sync_wellness(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: Garmin | None = None,
) -> int:
    """Garmin 웰니스 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.

    Returns:
        저장된 레코드 수.
    """
    if client is None:
        client = _login(config)

    count = 0
    today = datetime.now().date()

    for i in range(days):
        day = today - timedelta(days=i)
        date_str = day.isoformat()
        sleep_score = sleep_hours = hrv_value = hrv_sdnn = body_battery = stress_avg = resting_hr = None
        avg_sleeping_hr = readiness_score = weight_kg = steps = None
        detail_metrics: dict[str, float | int | None] = {}
        detail_json_metrics: dict[str, object] = {}

        try:
            sleep = client.get_sleep_data(date_str)
            _store_raw_payload(conn, "sleep_day", date_str, sleep)
            if sleep:
                daily_sleep = sleep.get("dailySleepDTO", {})
                sleep_score = (daily_sleep.get("sleepScores", {})
                               .get("overall", {}).get("value"))
                sleep_secs = daily_sleep.get("sleepTimeSeconds")
                if sleep_secs:
                    sleep_hours = round(sleep_secs / 3600, 1)

                avg_sleeping_hr = (
                    daily_sleep.get("averageHeartRate")
                    or sleep.get("averageHeartRate")
                )

                readiness_score = (
                    sleep.get("readinessScore")
                    or daily_sleep.get("readinessScore")
                    or sleep.get("readiness")
                    or daily_sleep.get("readiness")
                )

                weight_kg = (
                    sleep.get("weight")
                    or sleep.get("weightKg")
                    or daily_sleep.get("weight")
                    or daily_sleep.get("weightKg")
                    or daily_sleep.get("bodyWeight")
                )

                steps = (
                    sleep.get("steps")
                    or daily_sleep.get("steps")
                    or sleep.get("totalSteps")
                    or daily_sleep.get("totalSteps")
                    or steps
                )

                resting_hr = (
                    daily_sleep.get("restingHeartRate")
                    or sleep.get("restingHeartRate")
                    or resting_hr
                )

                detail_metrics.update({
                    "sleep_stage_awake_sec": (
                        daily_sleep.get("awakeSleepSeconds")
                        or daily_sleep.get("awakeSeconds")
                    ),
                    "sleep_stage_light_sec": (
                        daily_sleep.get("lightSleepSeconds")
                        or daily_sleep.get("lightSeconds")
                    ),
                    "sleep_stage_deep_sec": (
                        daily_sleep.get("deepSleepSeconds")
                        or daily_sleep.get("deepSeconds")
                    ),
                    "sleep_stage_rem_sec": (
                        daily_sleep.get("remSleepSeconds")
                        or daily_sleep.get("remSeconds")
                    ),
                    "sleep_total_sec": (
                        daily_sleep.get("sleepTimeSeconds")
                        or daily_sleep.get("totalSleepSeconds")
                    ),
                    "sleep_restless_moments": (
                        daily_sleep.get("restlessMomentsCount")
                        or daily_sleep.get("restlessMoments")
                    ),
                    "sleep_avg_respiration": (
                        daily_sleep.get("averageRespiration")
                        or daily_sleep.get("avgRespiration")
                    ),
                    "sleep_avg_spo2": (
                        daily_sleep.get("averageSpO2")
                        or daily_sleep.get("avgSpO2")
                    ),
                })

                sleep_start = (
                    daily_sleep.get("sleepStartTimestampLocal")
                    or daily_sleep.get("sleepStartTimestampGMT")
                    or daily_sleep.get("sleepStartTimestamp")
                )
                sleep_end = (
                    daily_sleep.get("sleepEndTimestampLocal")
                    or daily_sleep.get("sleepEndTimestampGMT")
                    or daily_sleep.get("sleepEndTimestamp")
                )
                if sleep_start is not None:
                    detail_json_metrics["sleep_start_timestamp"] = {"value": sleep_start}
                if sleep_end is not None:
                    detail_json_metrics["sleep_end_timestamp"] = {"value": sleep_end}

                detail_json_metrics["sleep_summary_json"] = {
                    "dailySleepDTO": daily_sleep,
                    "top_level": {
                        k: v
                        for k, v in sleep.items()
                        if k != "dailySleepDTO"
                    },
                }
        except Exception as e:
            print(f"[garmin] 수면 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            hrv = client.get_hrv_data(date_str)
            _store_raw_payload(conn, "hrv_day", date_str, hrv)
            if hrv:
                hrv_summary = hrv.get("hrvSummary", {})
                hrv_value = (
                    hrv_summary.get("lastNightAvg")
                    or hrv.get("lastNightAvg")
                )
                hrv_sdnn = (
                    hrv_summary.get("sdnn")
                    or hrv_summary.get("lastNightSDNN")
                    or hrv.get("sdnn")
                    or hrv.get("lastNightSDNN")
                )

                detail_metrics.update({
                    "overnight_hrv_avg": hrv_value,
                    "overnight_hrv_sdnn": hrv_sdnn,
                    "hrv_weekly_avg": (
                        hrv_summary.get("weeklyAvg")
                        or hrv.get("weeklyAvg")
                    ),
                    "hrv_baseline_low": (
                        hrv_summary.get("baselineLow")
                        or hrv.get("baselineLow")
                    ),
                    "hrv_baseline_high": (
                        hrv_summary.get("baselineHigh")
                        or hrv.get("baselineHigh")
                    ),
                })

                hrv_status = (
                    hrv_summary.get("status")
                    or hrv.get("status")
                )
                if hrv_status is not None:
                    detail_json_metrics["hrv_status"] = {"value": hrv_status}

                detail_json_metrics["hrv_summary_json"] = {
                    "hrvSummary": hrv_summary,
                    "top_level": {
                        k: v
                        for k, v in hrv.items()
                        if k != "hrvSummary"
                    },
                }
        except Exception as e:
            print(f"[garmin] HRV 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            bb = client.get_body_battery(date_str)
            _store_raw_payload(conn, "body_battery_day", date_str, bb)
            if bb and isinstance(bb, list) and bb:
                item = bb[0]
                bb_vals_array = item.get("bodyBatteryValuesArray") or []
                # 각 원소: [timestamp_ms, level]
                vals = [pair[1] for pair in bb_vals_array
                        if len(pair) > 1 and pair[1] is not None]
                charged = item.get("charged")
                drained = item.get("drained")
                body_battery = max(vals) if vals else None

                if vals:
                    detail_metrics.update({
                        "body_battery_start": vals[0],
                        "body_battery_end": vals[-1],
                        "body_battery_min": min(vals),
                        "body_battery_max": max(vals),
                        "body_battery_samples": len(vals),
                        "body_battery_delta": vals[-1] - vals[0],
                    })
                if charged is not None:
                    detail_metrics["body_battery_charged"] = charged
                if drained is not None:
                    detail_metrics["body_battery_drained"] = drained
                detail_json_metrics["body_battery_timeline"] = bb_vals_array
                detail_json_metrics["body_battery_summary_json"] = {
                    "sample_count": len(vals),
                    "min": min(vals) if vals else None,
                    "max": max(vals) if vals else None,
                    "start": vals[0] if vals else None,
                    "end": vals[-1] if vals else None,
                    "charged": charged,
                    "drained": drained,
                }
        except Exception as e:
            print(f"[garmin] Body Battery 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            stress = client.get_stress_data(date_str)
            _store_raw_payload(conn, "stress_day", date_str, stress)
            if stress:
                stress_avg = stress.get("averageStressLevel")
                if stress_avg is None:
                    stress_avg = stress.get("avgStressLevel")

                stress_values = stress.get("stressValuesArray") or stress.get("stressTimeline")

                # API가 직접 제공하지 않을 경우 stressValuesArray에서 계산
                # 각 샘플: [timestamp_ms, stress_level], 간격 약 3분 (180초)
                # stress level: -1=unknown, 0-25=rest, 26-50=low, 51-75=medium, 76-100=high
                def _compute_stress_durations(vals: list) -> dict:
                    if not vals or len(vals) < 2:
                        return {}
                    interval_sec = (vals[1][0] - vals[0][0]) / 1000
                    rest = low = medium = high = 0
                    for _, lvl in vals:
                        if lvl is None or lvl < 0:
                            continue
                        if lvl <= 25:
                            rest += interval_sec
                        elif lvl <= 50:
                            low += interval_sec
                        elif lvl <= 75:
                            medium += interval_sec
                        else:
                            high += interval_sec
                    return {
                        "stress_rest_duration": int(rest) if rest else None,
                        "stress_low_duration": int(low) if low else None,
                        "stress_medium_duration": int(medium) if medium else None,
                        "stress_high_duration": int(high) if high else None,
                    }

                # API 직접 제공값 우선, 없으면 계산값
                computed = _compute_stress_durations(stress_values or [])
                detail_metrics.update({
                    "stress_avg": stress_avg,
                    "stress_max": (
                        stress.get("maxStressLevel")
                        or stress.get("dailyStressMax")
                    ),
                    "stress_rest_duration": (
                        stress.get("restStressDuration")
                        or stress.get("restDuration")
                        or computed.get("stress_rest_duration")
                    ),
                    "stress_low_duration": (
                        stress.get("lowStressDuration")
                        or stress.get("lowDuration")
                        or computed.get("stress_low_duration")
                    ),
                    "stress_medium_duration": (
                        stress.get("mediumStressDuration")
                        or stress.get("mediumDuration")
                        or computed.get("stress_medium_duration")
                    ),
                    "stress_high_duration": (
                        stress.get("highStressDuration")
                        or stress.get("highDuration")
                        or computed.get("stress_high_duration")
                    ),
                })

                if stress_values is not None:
                    detail_json_metrics["stress_timeline"] = stress_values

                detail_json_metrics["stress_summary_json"] = {
                    "summary": {
                        k: v for k, v in stress.items()
                        if k not in {"stressValuesArray", "stressTimeline"}
                    }
                }
        except Exception as e:
            print(f"[garmin] 스트레스 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            respiration = client.get_respiration_data(date_str)
            _store_raw_payload(conn, "respiration_day", date_str, respiration)
            if respiration:
                detail_metrics.update({
                    "respiration_avg": (
                        respiration.get("averageRespiration")
                        or respiration.get("avgRespiration")
                        or respiration.get("avgBreathsPerMinute")
                    ),
                    "respiration_min": (
                        respiration.get("minRespiration")
                        or respiration.get("minimumRespiration")
                        or respiration.get("minBreathsPerMinute")
                    ),
                    "respiration_max": (
                        respiration.get("maxRespiration")
                        or respiration.get("maximumRespiration")
                        or respiration.get("maxBreathsPerMinute")
                    ),
                })
                detail_json_metrics["respiration_summary_json"] = respiration
        except Exception:
            pass

        try:
            time.sleep(2)
            spo2 = client.get_spo2_data(date_str)
            _store_raw_payload(conn, "spo2_day", date_str, spo2)
            if spo2:
                detail_metrics.update({
                    "spo2_avg": (
                        spo2.get("averageSpO2")
                        or spo2.get("avgSpO2")
                        or spo2.get("averageValue")
                    ),
                    "spo2_min": (
                        spo2.get("minSpO2")
                        or spo2.get("minimumSpO2")
                        or spo2.get("minValue")
                    ),
                    "spo2_max": (
                        spo2.get("maxSpO2")
                        or spo2.get("maximumSpO2")
                        or spo2.get("maxValue")
                    ),
                })
                detail_json_metrics["spo2_summary_json"] = spo2
        except Exception:
            pass

        try:
            time.sleep(2)
            readiness = client.get_training_readiness(date_str)
            _store_raw_payload(conn, "training_readiness_day", date_str, readiness)
            if readiness:
                detail_metrics.update({
                    "training_readiness_score": (
                        readiness.get("score")
                        or readiness.get("readinessScore")
                        or readiness.get("trainingReadinessScore")
                    ),
                    "training_readiness_sleep_score": (
                        readiness.get("sleepScore")
                        or readiness.get("sleepContribution")
                    ),
                    "training_readiness_recovery_score": (
                        readiness.get("recoveryScore")
                        or readiness.get("recoveryContribution")
                    ),
                    "training_readiness_hrv_score": (
                        readiness.get("hrvScore")
                        or readiness.get("hrvContribution")
                    ),
                })
                detail_json_metrics["training_readiness_summary_json"] = readiness
        except Exception:
            try:
                time.sleep(2)
                readiness = client.get_morning_training_readiness(date_str)
                _store_raw_payload(conn, "morning_training_readiness_day", date_str, readiness)
                if readiness:
                    detail_metrics.update({
                        "training_readiness_score": (
                            readiness.get("score")
                            or readiness.get("readinessScore")
                            or readiness.get("trainingReadinessScore")
                        ),
                        "training_readiness_sleep_score": (
                            readiness.get("sleepScore")
                            or readiness.get("sleepContribution")
                        ),
                        "training_readiness_recovery_score": (
                            readiness.get("recoveryScore")
                            or readiness.get("recoveryContribution")
                        ),
                        "training_readiness_hrv_score": (
                            readiness.get("hrvScore")
                            or readiness.get("hrvContribution")
                        ),
                    })
                    detail_json_metrics["training_readiness_summary_json"] = readiness
            except Exception:
                pass

        try:
            time.sleep(2)
            body_comp = client.get_body_composition(date_str)
            _store_raw_payload(conn, "body_composition_day", date_str, body_comp)
            if body_comp:
                detail_metrics.update({
                    "body_weight_kg": (
                        body_comp.get("weight")
                        or body_comp.get("weightKg")
                    ),
                    "body_fat_pct": (
                        body_comp.get("bodyFat")
                        or body_comp.get("bodyFatPercentage")
                    ),
                    "body_water_pct": (
                        body_comp.get("bodyWater")
                        or body_comp.get("bodyWaterPercentage")
                    ),
                    "skeletal_muscle_mass_kg": (
                        body_comp.get("skeletalMuscleMass")
                        or body_comp.get("muscleMass")
                    ),
                    "bone_mass_kg": (
                        body_comp.get("boneMass")
                    ),
                    "bmi": (
                        body_comp.get("bmi")
                    ),
                })
                detail_json_metrics["body_composition_summary_json"] = body_comp
        except Exception:
            pass

        try:
            rhr_data = client.get_rhr_day(date_str)
            _store_raw_payload(conn, "rhr_day", date_str, rhr_data)
            if rhr_data and resting_hr is None:
                resting_hr = rhr_data.get("restingHeartRate")
        except Exception:
            pass

        has_data = any(v is not None for v in
                       [sleep_score, sleep_hours, hrv_value, body_battery, stress_avg])
        if not has_data:
            continue

        try:
            conn.execute(
                """INSERT OR REPLACE INTO daily_wellness
                   (date, source, sleep_score, sleep_hours, hrv_value, hrv_sdnn,
                    resting_hr, avg_sleeping_hr, body_battery, stress_avg,
                    readiness_score, steps, weight_kg)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (date_str, sleep_score, sleep_hours, hrv_value, hrv_sdnn,
                 resting_hr, avg_sleeping_hr, body_battery, stress_avg,
                 readiness_score, steps, weight_kg),
            )
            _store_daily_detail_metrics(conn, date_str, detail_metrics, detail_json_metrics)
            count += 1
        except sqlite3.Error as e:
            print(f"[garmin] 웰니스 삽입 실패 {date_str}: {e}")

    conn.commit()
    return count


def sync_garmin(config: dict, conn: sqlite3.Connection, days: int) -> dict:
    """Garmin 전체 동기화 (활동 + 웰니스). 클라이언트를 한 번만 로그인.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        {"activity_summaries": 저장 수, "wellness": 저장 수}
    """
    client = _login(config)
    act_count = sync_activities(config, conn, days, client=client)
    well_count = sync_wellness(config, conn, days, client=client)
    return {"activity_summaries": act_count, "wellness": well_count}
