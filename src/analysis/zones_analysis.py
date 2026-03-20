"""HR Zone 분포 분석 및 80/20 훈련 강도 검증."""

import json
import sqlite3
from datetime import date, timedelta

from src.utils.zones import hr_zones


_ZONE_LABELS = ["회복", "유산소", "템포", "역치", "VO2Max"]


def _get_zone_uppers(config: dict | None) -> list[int]:
    """config에서 HR zone 상한값 리스트 반환.

    우선순위: config hr_zones > config max_hr > zones.py 기본값.

    Args:
        config: 설정 딕셔너리 또는 None.

    Returns:
        [z1_max, z2_max, z3_max, z4_max] 4개 값 (z5는 이 이상 전부).
    """
    if config:
        user = config.get("user", {})
        hz = user.get("hr_zones", {})
        if hz and hz.get("zone1_max"):
            return [
                hz["zone1_max"],
                hz.get("zone2_max", hz["zone1_max"] + 20),
                hz.get("zone3_max", hz["zone1_max"] + 35),
                hz.get("zone4_max", hz["zone1_max"] + 50),
            ]
        max_hr = user.get("max_hr")
        if max_hr:
            zones = hr_zones(int(max_hr))
            return [z[1] for z in zones[:4]]

    # 기본값: max_hr=190 기준 zones.py 계산
    zones = hr_zones(190)
    return [z[1] for z in zones[:4]]


def _classify_hr(hr: int, zone_uppers: list[int]) -> int:
    """HR 값을 존 번호(1-5)로 분류.

    Args:
        hr: 심박수.
        zone_uppers: [z1_max, z2_max, z3_max, z4_max].

    Returns:
        1~5 존 번호.
    """
    for i, upper in enumerate(zone_uppers):
        if hr <= upper:
            return i + 1
    return 5


def _find_stream_path(conn: sqlite3.Connection, rep_id: int) -> str | None:
    """rep_id로부터 같은 그룹의 Strava stream 파일 경로 탐색."""
    row = conn.execute(
        "SELECT matched_group_id, source FROM activities WHERE id = ?",
        (rep_id,),
    ).fetchone()
    if not row:
        return None

    group_id, source = row[0], row[1]

    if group_id:
        acts = conn.execute(
            "SELECT id FROM activities WHERE matched_group_id = ? AND source = 'strava'",
            (group_id,),
        ).fetchall()
    elif source == "strava":
        acts = [(rep_id,)]
    else:
        acts = []

    for (sid,) in acts:
        r = conn.execute(
            "SELECT metric_json FROM source_metrics "
            "WHERE activity_id = ? AND metric_name = 'stream_file'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            return r[0]
    return None


def _load_stream(path: str) -> dict | None:
    """Stream JSON 파일 로드. Strava API 리스트 형식도 dict로 변환."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {s["type"]: s["data"] for s in data if "type" in s and "data" in s}
        return data
    except Exception:
        return None


def _get_intervals_zones(conn: sqlite3.Connection, rep_id: int) -> dict | None:
    """Intervals.icu zone time 데이터 조회 (source_metrics JSON).

    우선순위:
    1) icu_hr_zone_times: [z1, z2, ...] 리스트
    2) hr_zone_distribution: {1: secs, ...} 형태의 구버전 JSON

    Returns:
        {1: 초, 2: 초, ...} 또는 None.
    """
    row = conn.execute(
        "SELECT matched_group_id FROM activities WHERE id = ?", (rep_id,)
    ).fetchone()
    if not row:
        return None

    group_id = row[0]
    if group_id:
        acts = conn.execute(
            "SELECT id FROM activities WHERE matched_group_id = ? AND source = 'intervals'",
            (group_id,),
        ).fetchall()
    else:
        src_row = conn.execute(
            "SELECT source FROM activities WHERE id = ?", (rep_id,)
        ).fetchone()
        acts = [(rep_id,)] if src_row and src_row[0] == "intervals" else []

    for (sid,) in acts:
        # 1) 신규 저장 포맷: icu_hr_zone_times = [z1, z2, z3, ...]
        r = conn.execute(
            "SELECT metric_json FROM source_metrics "
            "WHERE activity_id = ? AND metric_name = 'icu_hr_zone_times'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            try:
                data = json.loads(r[0])
                if isinstance(data, list):
                    return {idx + 1: int(v or 0) for idx, v in enumerate(data[:5])}
            except Exception:
                pass

        # 2) 구 포맷: hr_zone_distribution = {1: secs, ...}
        r = conn.execute(
            "SELECT metric_json FROM source_metrics "
            "WHERE activity_id = ? AND metric_name = 'hr_zone_distribution'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            try:
                data = json.loads(r[0])
                return {int(k): v for k, v in data.items()}
            except Exception:
                pass
    return None


def _empty_zones_result() -> dict:
    """활동 없을 때 기본 반환 구조."""
    return {
        "zone_distribution": {
            f"z{i+1}": {"pct": 0.0, "seconds": 0, "label": label}
            for i, label in enumerate(_ZONE_LABELS)
        },
        "easy_pct": 0.0,
        "hard_pct": 0.0,
        "moderate_pct": 0.0,
        "polarization_status": "unknown",
        "data_source": "none",
        "activity_count": 0,
        "total_time_seconds": 0,
    }


def analyze_zones(
    conn: sqlite3.Connection,
    period_start: str,
    period_end: str,
    config: dict | None = None,
) -> dict:
    """기간 내 HR Zone 분포 분석 및 80/20 법칙 준수 여부 판정.

    Args:
        conn: SQLite 연결.
        period_start: 시작 날짜 (포함, ISO 형식).
        period_end: 종료 날짜 (미포함, ISO 형식).
        config: 설정 딕셔너리 (HR zone 경계값 포함).

    Returns:
        zone 분포, 강도 비율, polarization 상태를 담은 dict.
    """
    groups = conn.execute("""
        SELECT COALESCE(matched_group_id, CAST(id AS TEXT)) AS gk,
               MIN(id) AS rep_id,
               SUM(duration_sec) AS total_dur,
               AVG(avg_hr) AS avg_hr_val
        FROM activities
        WHERE start_time >= ? AND start_time < ?
          AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
        GROUP BY gk
    """, (period_start, period_end)).fetchall()

    if not groups:
        return _empty_zones_result()

    zone_uppers = _get_zone_uppers(config)
    zone_secs = [0.0] * 5
    sources_used: list[str] = []

    for _gk, rep_id, total_dur, avg_hr_val in groups:
        # 우선순위 1: Strava stream
        stream_path = _find_stream_path(conn, rep_id)
        if stream_path:
            stream = _load_stream(stream_path)
            if stream and stream.get("heartrate"):
                for hr_val in stream["heartrate"]:
                    z = _classify_hr(int(hr_val), zone_uppers)
                    zone_secs[z - 1] += 1
                sources_used.append("strava_stream")
                continue

        # 우선순위 2: Intervals hr_zone_distribution
        intervals_zones = _get_intervals_zones(conn, rep_id)
        if intervals_zones:
            for z_num, secs in intervals_zones.items():
                if 1 <= z_num <= 5:
                    zone_secs[z_num - 1] += secs
            sources_used.append("intervals_zones")
            continue

        # 우선순위 3: avg_hr 근사 (정확도 낮음)
        if avg_hr_val and total_dur:
            z = _classify_hr(int(avg_hr_val), zone_uppers)
            zone_secs[z - 1] += float(total_dur or 0)
            sources_used.append("avg_hr_estimate")

    total = sum(zone_secs)
    if total == 0:
        return _empty_zones_result()

    zone_distribution = {
        f"z{i+1}": {
            "pct": round(zone_secs[i] / total * 100, 1),
            "seconds": int(zone_secs[i]),
            "label": _ZONE_LABELS[i],
        }
        for i in range(5)
    }

    easy_pct = round((zone_secs[0] + zone_secs[1]) / total * 100, 1)
    moderate_pct = round(zone_secs[2] / total * 100, 1)
    hard_pct = round((zone_secs[3] + zone_secs[4]) / total * 100, 1)

    # polarization_status: threshold_heavy가 optimal보다 우선
    if moderate_pct > 25:
        pol_status = "threshold_heavy"
    elif 75 <= easy_pct <= 85:
        pol_status = "optimal"
    elif easy_pct < 75:
        pol_status = "too_hard"
    else:
        pol_status = "too_easy"

    # 사용된 데이터 소스 중 최우선 소스 보고
    if "strava_stream" in sources_used:
        data_source = "strava_stream"
    elif "intervals_zones" in sources_used:
        data_source = "intervals_zones"
    else:
        data_source = "avg_hr_estimate"

    return {
        "zone_distribution": zone_distribution,
        "easy_pct": easy_pct,
        "hard_pct": hard_pct,
        "moderate_pct": moderate_pct,
        "polarization_status": pol_status,
        "data_source": data_source,
        "activity_count": len(groups),
        "total_time_seconds": int(total),
    }


def weekly_zone_trend(
    conn: sqlite3.Connection,
    weeks: int = 4,
    config: dict | None = None,
) -> list[dict]:
    """최근 N주간 주별 HR zone 분포 추세.

    Args:
        conn: SQLite 연결.
        weeks: 조회할 주 수.
        config: HR zone 설정.

    Returns:
        주별 강도 분포 및 polarization 상태 리스트 (N개).
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)

    results = []
    for w in range(weeks):
        ws = week_start + timedelta(weeks=w)
        we = ws + timedelta(weeks=1)

        zones = analyze_zones(conn, ws.isoformat(), we.isoformat(), config)
        results.append({
            "week_start": ws.isoformat(),
            "easy_pct": zones["easy_pct"],
            "hard_pct": zones["hard_pct"],
            "moderate_pct": zones["moderate_pct"],
            "status": zones["polarization_status"],
            "runs": zones["activity_count"],
        })

    return results
