"""유산소 효율성(EF) 및 심장 디커플링 분석 (Strava stream 기반)."""

import json
import sqlite3
from datetime import date, timedelta


def _get_stream_path(conn: sqlite3.Connection, activity_id: int) -> str | None:
    """activity_id와 같은 그룹의 Strava stream 파일 경로 반환.

    Args:
        conn: SQLite 연결.
        activity_id: activities 테이블 id.

    Returns:
        stream 파일 경로, 없으면 None.
    """
    row = conn.execute(
        "SELECT matched_group_id, source FROM activities WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        return None

    group_id, source = row[0], row[1]

    # 같은 그룹의 strava 활동 탐색
    if group_id:
        strava_ids = conn.execute(
            "SELECT id FROM activities WHERE matched_group_id = ? AND source = 'strava'",
            (group_id,),
        ).fetchall()
    elif source == "strava":
        strava_ids = [(activity_id,)]
    else:
        strava_ids = []

    for (sid,) in strava_ids:
        r = conn.execute(
            "SELECT metric_json FROM source_metrics "
            "WHERE activity_id = ? AND metric_name = 'stream_file'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            return r[0]
    return None


def _load_stream(path: str) -> dict | None:
    """Stream JSON 파일 로드. Strava API 리스트 형식도 dict로 변환.

    Args:
        path: stream JSON 파일 경로.

    Returns:
        {"heartrate": [...], "velocity_smooth": [...], ...} 또는 None.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Strava API는 리스트 형식: [{type, data}, ...]
        if isinstance(data, list):
            return {s["type"]: s["data"] for s in data if "type" in s and "data" in s}
        return data
    except Exception:
        return None


def calculate_efficiency(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """Strava stream 기반 EF(효율성 지수) 및 심장 디커플링 계산.

    전반/후반 EF를 비교해 심장이 얼마나 표류하는지 측정한다.

    Args:
        conn: SQLite 연결.
        activity_id: activities 테이블 id.

    Returns:
        EF/디커플링 결과 dict, 데이터 부족 또는 stream 없으면 None.
    """
    stream_path = _get_stream_path(conn, activity_id)
    if not stream_path:
        return None

    stream = _load_stream(stream_path)
    if stream is None:
        return None

    hr = stream.get("heartrate")
    vel = stream.get("velocity_smooth")
    if not hr or not vel:
        return None

    n = min(len(hr), len(vel))
    if n < 60:
        return None

    mid = n // 2
    hr1, hr2 = hr[:mid], hr[mid:n]
    v1, v2 = vel[:mid], vel[mid:n]

    avg_hr1 = sum(hr1) / len(hr1)
    avg_hr2 = sum(hr2) / len(hr2)
    avg_v1 = sum(v1) / len(v1)
    avg_v2 = sum(v2) / len(v2)

    if avg_hr1 <= 0 or avg_hr2 <= 0:
        return None

    ef1 = avg_v1 / avg_hr1
    ef2 = avg_v2 / avg_hr2
    decoupling = (ef1 - ef2) / ef1 * 100 if ef1 > 0 else 0.0
    # 반올림 후 비교 — 부동소수점 경계 오차 방지
    dec_r = round(decoupling, 2)

    if dec_r < 5.0:
        status = "good"
    elif dec_r < 10.0:
        status = "fair"
    else:
        status = "poor"

    return {
        "ef_first_half": round(ef1, 4),
        "ef_second_half": round(ef2, 4),
        "decoupling_pct": round(decoupling, 2),
        "avg_hr_first": round(avg_hr1, 1),
        "avg_hr_second": round(avg_hr2, 1),
        "avg_speed_first": round(avg_v1, 3),
        "avg_speed_second": round(avg_v2, 3),
        "status": status,
        "data_points": n,
    }


def efficiency_trend(conn: sqlite3.Connection, weeks: int = 8) -> list[dict]:
    """최근 N주간 주별 평균 EF 및 디커플링 추세.

    stream이 없는 활동은 건너뛴다.

    Args:
        conn: SQLite 연결.
        weeks: 조회할 주 수.

    Returns:
        데이터가 있는 주만 포함한 주별 집계 리스트.
    """
    today = date.today()
    # 이번 주 월요일에서 weeks-1주 전 월요일부터 시작
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)

    results = []
    for w in range(weeks):
        ws = week_start + timedelta(weeks=w)
        we = ws + timedelta(weeks=1)

        rows = conn.execute(
            "SELECT id FROM activities "
            "WHERE start_time >= ? AND start_time < ? AND activity_type = 'running'",
            (ws.isoformat(), we.isoformat()),
        ).fetchall()

        ef_list = []
        dec_list = []
        for (act_id,) in rows:
            result = calculate_efficiency(conn, act_id)
            if result is None:
                continue
            ef_list.append((result["ef_first_half"] + result["ef_second_half"]) / 2)
            dec_list.append(result["decoupling_pct"])

        if not ef_list:
            continue

        avg_ef = round(sum(ef_list) / len(ef_list), 4)
        avg_dec = round(sum(dec_list) / len(dec_list), 2)

        if avg_dec < 5.0:
            status = "good"
        elif avg_dec < 10.0:
            status = "fair"
        else:
            status = "poor"

        results.append({
            "week_start": ws.isoformat(),
            "avg_ef": avg_ef,
            "avg_decoupling": avg_dec,
            "activity_count": len(ef_list),
            "status": status,
        })

    return results
