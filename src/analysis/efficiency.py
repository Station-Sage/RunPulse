"""유산소 효율성(EF) 및 심장 디커플링 분석 (Strava stream 기반)."""

import json
import sqlite3
from datetime import date, timedelta


def _get_stream_path(conn: sqlite3.Connection, activity_id: int) -> str | None:
    """activity_id와 같은 그룹의 Strava stream 식별자 반환.

    activity_streams 테이블 또는 activity_detail_metrics.stream_file 탐색.
    반환값은 _load_stream에서 사용 (activity_id 또는 파일 경로).
    """
    row = conn.execute(
        "SELECT matched_group_id, source FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        return None

    group_id, source = row[0], row[1]

    # 같은 그룹의 strava 활동 탐색
    if group_id:
        strava_ids = conn.execute(
            "SELECT id FROM activity_summaries WHERE matched_group_id = ? AND source = 'strava'",
            (group_id,),
        ).fetchall()
    elif source == "strava":
        strava_ids = [(activity_id,)]
    else:
        strava_ids = []

    for (sid,) in strava_ids:
        # 1. activity_streams 테이블에서 확인 (우선)
        stream_check = conn.execute(
            "SELECT COUNT(*) FROM activity_streams WHERE activity_id = ?",
            (sid,),
        ).fetchone()
        if stream_check and stream_check[0] > 0:
            return f"db:{sid}"  # DB 기반 식별자

        # 2. activity_detail_metrics.stream_file fallback (레거시)
        r = conn.execute(
            "SELECT metric_json FROM activity_detail_metrics "
            "WHERE activity_id = ? AND metric_name = 'stream_file'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            return r[0]
    return None


def _load_stream(path: str, conn: sqlite3.Connection | None = None) -> dict | None:
    """Stream 데이터 로드 — DB 또는 파일.

    Args:
        path: "db:{activity_id}" (DB) 또는 파일 경로.
        conn: SQLite 연결 (DB 로드 시 필요).

    Returns:
        {"heartrate": [...], "velocity_smooth": [...], ...} 또는 None.
    """
    # DB 기반 (activity_streams 테이블)
    if path.startswith("db:") and conn is not None:
        try:
            aid = int(path[3:])
            rows = conn.execute(
                "SELECT stream_type, data_json FROM activity_streams WHERE activity_id = ?",
                (aid,),
            ).fetchall()
            if not rows:
                return None
            return {r[0]: json.loads(r[1]) for r in rows if r[1]}
        except Exception:
            return None

    # 파일 기반 (레거시)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {s["type"]: s["data"] for s in data if "type" in s and "data" in s}
        return data
    except Exception:
        return None



def _get_intervals_metrics(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """Intervals source_metrics 기반 효율 지표 fallback."""
    rows = conn.execute(
        "SELECT metric_name, metric_value FROM activity_detail_metrics WHERE activity_id = ? AND source = 'intervals'",
        (activity_id,),
    ).fetchall()
    if not rows:
        return None

    data = {name: value for name, value in rows if value is not None}
    if not data:
        return None

    ef = data.get("icu_efficiency_factor")
    dec = data.get("decoupling")

    if ef is None and dec is None:
        return None

    if dec is None:
        status = "unknown"
    elif dec < 5:
        status = "good"
    elif dec < 10:
        status = "fair"
    else:
        status = "poor"

    return {
        "ef": round(ef, 4) if ef is not None else None,
        "decoupling_pct": round(dec, 2) if dec is not None else None,
        "status": status,
        "data_source": "intervals_metrics",
        "average_stride": data.get("average_stride"),
        "trimp": data.get("trimp"),
    }

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
        return _get_intervals_metrics(conn, activity_id)

    stream = _load_stream(stream_path, conn=conn)
    if stream is None:
        return _get_intervals_metrics(conn, activity_id)

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
            "SELECT id FROM activity_summaries "
            "WHERE start_time >= ? AND start_time < ? AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')",
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
