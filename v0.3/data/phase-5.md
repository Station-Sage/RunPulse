

# Phase 5 상세 설계 — Consumer 코드 마이그레이션

## 5-0. Phase 5의 목표

Phase 1~4가 완료되면, 데이터가 새로운 구조(activity_summaries 46컬럼 + metric_store EAV + daily_wellness/daily_fitness)에 채워져 있습니다. Phase 5에서는 **이 데이터를 읽는 모든 코드** — UI 뷰, Analysis 모듈, AI Context, Training Planner, Export — 를 새 스키마에 맞게 전환합니다.

핵심 원칙:
- UI는 `activity_summaries`에서 빠른 목록/필터를 하고, `metric_store`에서 상세/카드 데이터를 가져온다
- 모든 메트릭 값 표시에 `metric_registry`의 단위/설명을 사용한다
- 소스별 비교 뷰를 제공하여 "데이터 통합 플랫폼"으로서의 가치를 보여준다
- 기존 Flask 라우트 구조는 유지하되, 쿼리 레이어만 교체한다

---

## 5-1. 현재 Consumer 코드 목록 & 영향 분석

기존 코드에서 DB를 직접 읽는 모든 지점을 식별합니다.

| 모듈 | 현재 쿼리 대상 | 변경 필요 사항 |
|------|---------------|--------------|
| `src/services/unified_activities.py` | activity_summaries + activity_detail_metrics JOIN | → activity_summaries + metric_store JOIN |
| `src/web/views_activities_table.py` | unified_activities 호출 | → 새 서비스 레이어 호출 |
| `src/web/views_activity_deep.py` | activity_detail_metrics, activity_streams | → metric_store category별 조회 |
| `src/web/views_dashboard.py` | activity_summaries, daily_wellness, computed_metrics | → activity_summaries + metric_store + daily_wellness |
| `src/web/views_wellness.py` | daily_wellness, daily_detail_metrics | → daily_wellness + metric_store(scope='daily') |
| `src/web/views_training.py` | planned_workouts, goals, computed_metrics | → planned_workouts + metric_store |
| `src/web/views_report.py` | analysis 모듈 호출 | → 새 analysis 인터페이스 |
| `src/analysis/*.py` | 직접 SQL 쿼리 | → db_helpers 함수 사용 |
| `src/ai/ai_context.py` | 여러 테이블 직접 읽기 | → 표준화된 context builder |
| `src/web/views_settings.py` | config, sync_jobs | → sync_jobs 새 스키마 |
| `src/web/views_sync_ui.py` | sync_jobs 조회 | → 새 sync_jobs 스키마 |
| `src/web/views_export.py` | activity_summaries | → 새 컬럼명 |
| `src/web/views_shoes.py` | gear 테이블 | → 스키마 동일, 미세 조정 |
| `src/web/views_merge_group.py` | matched_group_id 조회 | → 로직 동일, 뷰 참조 변경 |

---

## 5-2. 서비스 레이어 재설계 — `src/services/`

UI 뷰가 직접 SQL을 쓰지 않도록, 중간 서비스 레이어를 통해 데이터를 가져옵니다.

### `activity_service.py` — 활동 목록 & 상세

```python
# src/services/activity_service.py

import json
from typing import Optional
from src.utils.db_helpers import get_primary_metrics, get_all_providers_for_metric
from src.utils.metric_registry import METRIC_REGISTRY, get_unit, get_category


def get_activity_list(conn, filters: dict = None, page: int = 1, per_page: int = 20) -> dict:
    """
    활동 목록 조회 (대시보드, 활동 탭).
    activity_summaries만 사용 — JOIN 없이 빠름.
    
    Returns: {
        "activities": [dict, ...],
        "total": int,
        "page": int,
        "pages": int,
    }
    """
    where_clauses = []
    params = []
    
    # 대표 활동만 (dedup 그룹에서 1개)
    base_table = "v_canonical_activities"
    
    if filters:
        if filters.get("activity_type"):
            where_clauses.append("activity_type = ?")
            params.append(filters["activity_type"])
        
        if filters.get("start_date"):
            where_clauses.append("start_time >= ?")
            params.append(filters["start_date"])
        
        if filters.get("end_date"):
            where_clauses.append("start_time <= ?")
            params.append(filters["end_date"])
        
        if filters.get("min_distance_m"):
            where_clauses.append("distance_m >= ?")
            params.append(filters["min_distance_m"])
        
        if filters.get("max_distance_m"):
            where_clauses.append("distance_m <= ?")
            params.append(filters["max_distance_m"])
        
        if filters.get("search"):
            where_clauses.append("(name LIKE ? OR description LIKE ?)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])
        
        if filters.get("min_training_load"):
            where_clauses.append("training_load >= ?")
            params.append(filters["min_training_load"])
        
        if filters.get("gear_id"):
            where_clauses.append("gear_id = ?")
            params.append(filters["gear_id"])
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # 총 개수
    count_row = conn.execute(
        f"SELECT COUNT(*) FROM {base_table} WHERE {where_sql}",
        params
    ).fetchone()
    total = count_row[0]
    
    # 페이지네이션
    offset = (page - 1) * per_page
    
    rows = conn.execute(f"""
        SELECT * FROM {base_table}
        WHERE {where_sql}
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset]).fetchall()
    
    cols = _get_column_names(conn, base_table)
    activities = [dict(zip(cols, row)) for row in rows]
    
    # 각 활동에 RunPulse workout_type 추가 (metric_store에서)
    for act in activities:
        wt = _get_workout_type(conn, act["id"])
        act["workout_type"] = wt
    
    return {
        "activities": activities,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


def get_activity_detail(conn, activity_id: int) -> dict:
    """
    활동 상세 페이지용 전체 데이터.
    activity_summaries + metric_store(category별) + laps + group info
    
    Returns: {
        "summary": dict,              # activity_summaries 행
        "metrics_by_category": dict,   # {category: [metric, ...]}
        "provider_comparison": dict,   # {metric_name: [{provider, value}, ...]}
        "laps": [dict, ...],
        "group": [dict, ...] | None,   # 같은 활동의 다른 소스
        "workout_type": dict | None,
        "has_streams": bool,
    }
    """
    # ── Summary ──
    row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?", [activity_id]
    ).fetchone()
    if not row:
        return None
    
    cols = _get_column_names(conn, "activity_summaries")
    summary = dict(zip(cols, row))
    
    # ── Metrics by Category ──
    metrics_rows = conn.execute("""
        SELECT metric_name, category, provider, numeric_value, text_value, json_value,
               confidence, is_primary, algorithm_version
        FROM metric_store
        WHERE scope_type = 'activity' AND scope_id = ?
        ORDER BY category, is_primary DESC, provider
    """, [str(activity_id)]).fetchall()
    
    metrics_by_category = {}
    provider_comparison = {}
    
    for name, cat, provider, num, text, json_val, conf, is_primary, version in metrics_rows:
        # 카테고리별 그룹핑 (primary만)
        if is_primary:
            if cat not in metrics_by_category:
                metrics_by_category[cat] = []
            
            reg = METRIC_REGISTRY.get(name, None)
            metrics_by_category[cat].append({
                "metric_name": name,
                "display_name": reg.description if reg else name,
                "value": num if num is not None else text,
                "json_value": json.loads(json_val) if json_val else None,
                "unit": reg.unit if reg else None,
                "provider": provider,
                "confidence": conf,
            })
        
        # provider별 비교 데이터
        if name not in provider_comparison:
            provider_comparison[name] = []
        provider_comparison[name].append({
            "provider": provider,
            "numeric_value": num,
            "text_value": text,
            "is_primary": bool(is_primary),
            "algorithm_version": version,
            "confidence": conf,
        })
    
    # ── Laps ──
    laps = conn.execute("""
        SELECT * FROM activity_laps
        WHERE activity_id = ?
        ORDER BY source, lap_index
    """, [activity_id]).fetchall()
    laps_cols = _get_column_names(conn, "activity_laps")
    laps_list = [dict(zip(laps_cols, lap)) for lap in laps]
    
    # ── Group (같은 활동의 다른 소스) ──
    group = None
    if summary.get("matched_group_id"):
        group_rows = conn.execute("""
            SELECT id, source, distance_m, duration_sec, avg_hr, training_load
            FROM activity_summaries
            WHERE matched_group_id = ? AND id != ?
        """, [summary["matched_group_id"], activity_id]).fetchall()
        group = [
            dict(zip(["id", "source", "distance_m", "duration_sec", "avg_hr", "training_load"], r))
            for r in group_rows
        ]
    
    # ── Workout Type ──
    workout_type = _get_workout_type(conn, activity_id)
    
    # ── Streams 존재 여부 ──
    has_streams = conn.execute(
        "SELECT 1 FROM activity_streams WHERE activity_id = ? LIMIT 1",
        [activity_id]
    ).fetchone() is not None
    
    return {
        "summary": summary,
        "metrics_by_category": metrics_by_category,
        "provider_comparison": provider_comparison,
        "laps": laps_list,
        "group": group,
        "workout_type": workout_type,
        "has_streams": has_streams,
    }


def get_activity_streams(conn, activity_id: int) -> dict:
    """
    활동 스트림 데이터 (차트용).
    Returns: {
        "time": [0, 1, 2, ...],
        "heart_rate": [120, 122, ...],
        "speed_ms": [...],
        "altitude_m": [...],
        "cadence": [...],
        "power_watts": [...],
        "grade_pct": [...],
    }
    """
    rows = conn.execute("""
        SELECT elapsed_sec, heart_rate, speed_ms, altitude_m, cadence,
               power_watts, grade_pct, distance_m, latitude, longitude
        FROM activity_streams
        WHERE activity_id = ?
        ORDER BY elapsed_sec
    """, [activity_id]).fetchall()
    
    if not rows:
        return {}
    
    streams = {
        "time": [], "heart_rate": [], "speed_ms": [], "altitude_m": [],
        "cadence": [], "power_watts": [], "grade_pct": [],
        "distance_m": [], "latitude": [], "longitude": [],
    }
    
    for row in rows:
        streams["time"].append(row[0])
        streams["heart_rate"].append(row[1])
        streams["speed_ms"].append(row[2])
        streams["altitude_m"].append(row[3])
        streams["cadence"].append(row[4])
        streams["power_watts"].append(row[5])
        streams["grade_pct"].append(row[6])
        streams["distance_m"].append(row[7])
        streams["latitude"].append(row[8])
        streams["longitude"].append(row[9])
    
    # None만 있는 채널 제거
    return {k: v for k, v in streams.items() if any(x is not None for x in v)}


def get_activity_trend(conn, metric_name: str, days: int = 90,
                       activity_type: str = "running") -> list[dict]:
    """
    활동 메트릭 추세 (차트용).
    activity_summaries 컬럼이면 직접 조회, metric_store면 JOIN.
    
    Returns: [{"date": "2026-03-01", "value": 85.2, "activity_id": 123}, ...]
    """
    # activity_summaries에 있는 컬럼인지 확인
    as_columns = _get_column_names(conn, "activity_summaries")
    
    if metric_name in as_columns:
        rows = conn.execute(f"""
            SELECT substr(start_time, 1, 10) as date, {metric_name}, id
            FROM v_canonical_activities
            WHERE activity_type = ? AND {metric_name} IS NOT NULL
            AND start_time >= datetime('now', ? || ' days')
            ORDER BY start_time
        """, [activity_type, str(-days)]).fetchall()
        
        return [{"date": r[0], "value": r[1], "activity_id": r[2]} for r in rows]
    
    else:
        rows = conn.execute("""
            SELECT substr(a.start_time, 1, 10) as date, m.numeric_value, a.id
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity' AND m.metric_name = ? AND m.is_primary = 1
            AND a.activity_type = ?
            AND a.start_time >= datetime('now', ? || ' days')
            ORDER BY a.start_time
        """, [metric_name, activity_type, str(-days)]).fetchall()
        
        return [{"date": r[0], "value": r[1], "activity_id": r[2]} for r in rows]


# ── 내부 헬퍼 ──

def _get_workout_type(conn, activity_id: int) -> dict | None:
    row = conn.execute("""
        SELECT json_value, text_value, confidence
        FROM metric_store
        WHERE scope_type = 'activity' AND scope_id = ? 
        AND metric_name = 'workout_type' AND is_primary = 1
    """, [str(activity_id)]).fetchone()
    
    if row and row[0]:
        result = json.loads(row[0])
        result["confidence"] = row[2]
        return result
    elif row and row[1]:
        return {"type": row[1], "confidence": row[2]}
    return None


def _get_column_names(conn, table_name: str) -> list[str]:
    """테이블 또는 뷰의 컬럼명 목록"""
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
    return [desc[0] for desc in cursor.description]
```

### `dashboard_service.py` — 대시보드 데이터

```python
# src/services/dashboard_service.py

from datetime import datetime, timedelta
from src.utils.db_helpers import get_primary_metrics


def get_dashboard_data(conn) -> dict:
    """
    대시보드 첫 화면에 필요한 모든 데이터를 한 번에 로드.
    
    Returns: {
        "today_wellness": dict,
        "today_readiness": dict,         # UTRS, CIRS
        "fitness_summary": dict,         # CTL, ATL, TSB
        "recent_activities": [dict, ...],
        "weekly_summary": dict,          # 이번 주 거리/시간/횟수
        "race_predictions": dict,        # DARP
        "training_status": str,          # "productive" | "maintaining" | "detraining" | ...
    }
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # ── Today Wellness ──
    wellness = conn.execute(
        "SELECT * FROM daily_wellness WHERE date = ?", [today]
    ).fetchone()
    today_wellness = None
    if wellness:
        cols = [d[0] for d in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
        today_wellness = dict(zip(cols, wellness))
    
    # ── Today Readiness (UTRS, CIRS) ──
    readiness_metrics = get_primary_metrics(
        conn, "daily", today, 
        names=["utrs", "cirs", "training_readiness_score"]
    )
    today_readiness = {m["metric_name"]: m for m in readiness_metrics}
    
    # ── Fitness Summary (CTL, ATL, TSB) ──
    fitness_row = conn.execute("""
        SELECT ctl, atl, tsb, ramp_rate FROM daily_fitness
        WHERE date = ? AND source = 'runpulse'
        ORDER BY date DESC LIMIT 1
    """, [today]).fetchone()
    
    if not fitness_row:
        # RunPulse 값 없으면 Intervals fallback
        fitness_row = conn.execute("""
            SELECT ctl, atl, tsb, ramp_rate FROM daily_fitness
            WHERE date <= ? ORDER BY date DESC LIMIT 1
        """, [today]).fetchone()
    
    fitness_summary = None
    if fitness_row:
        fitness_summary = {
            "ctl": fitness_row[0], "atl": fitness_row[1],
            "tsb": fitness_row[2], "ramp_rate": fitness_row[3],
        }
    
    # ── Recent Activities (최근 7개) ──
    acts = conn.execute("""
        SELECT id, name, activity_type, start_time, distance_m, duration_sec,
               avg_pace_sec_km, avg_hr, training_load, suffer_score
        FROM v_canonical_activities
        ORDER BY start_time DESC LIMIT 7
    """).fetchall()
    
    recent_activities = [
        dict(zip(["id", "name", "activity_type", "start_time", "distance_m",
                   "duration_sec", "avg_pace_sec_km", "avg_hr", "training_load",
                   "suffer_score"], a))
        for a in acts
    ]
    
    # 각 활동에 workout_type 추가
    for act in recent_activities:
        from src.services.activity_service import _get_workout_type
        act["workout_type"] = _get_workout_type(conn, act["id"])
    
    # ── Weekly Summary ──
    monday = _this_monday()
    week_stats = conn.execute("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(distance_m), 0) as total_distance,
            COALESCE(SUM(duration_sec), 0) as total_duration,
            COALESCE(AVG(avg_hr), 0) as avg_hr
        FROM v_canonical_activities
        WHERE start_time >= ? AND activity_type IN ('running', 'trail_running', 'treadmill')
    """, [monday]).fetchone()
    
    weekly_summary = {
        "count": week_stats[0],
        "total_distance_m": week_stats[1],
        "total_duration_sec": week_stats[2],
        "avg_hr": int(week_stats[3]) if week_stats[3] else None,
    }
    
    # ── Race Predictions (DARP) ──
    darp_metrics = get_primary_metrics(
        conn, "daily", today,
        names=["darp_5k", "darp_10k", "darp_half", "darp_full"]
    )
    race_predictions = {m["metric_name"]: m["numeric_value"] for m in darp_metrics}
    
    # ── Training Status ──
    training_status = _determine_training_status(fitness_summary)
    
    return {
        "today_wellness": today_wellness,
        "today_readiness": today_readiness,
        "fitness_summary": fitness_summary,
        "recent_activities": recent_activities,
        "weekly_summary": weekly_summary,
        "race_predictions": race_predictions,
        "training_status": training_status,
    }


def get_pmc_chart_data(conn, days: int = 90) -> dict:
    """
    PMC 차트용 시계열 데이터.
    Returns: {"dates": [...], "ctl": [...], "atl": [...], "tsb": [...]}
    """
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    rows = conn.execute("""
        SELECT date, ctl, atl, tsb
        FROM daily_fitness
        WHERE source = 'runpulse' AND date >= ?
        ORDER BY date
    """, [start]).fetchall()
    
    if not rows:
        # RunPulse PMC가 없으면 Intervals fallback
        rows = conn.execute("""
            SELECT date, ctl, atl, tsb
            FROM daily_fitness
            WHERE date >= ?
            ORDER BY date
        """, [start]).fetchall()
    
    return {
        "dates": [r[0] for r in rows],
        "ctl": [r[1] for r in rows],
        "atl": [r[2] for r in rows],
        "tsb": [r[3] for r in rows],
    }


def get_daily_metric_chart(conn, metric_name: str, days: int = 30) -> dict:
    """
    일별 메트릭 차트 (UTRS, CIRS, Sleep Score 등).
    Returns: {"dates": [...], "values": [...], "providers": [...]}
    """
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # daily_wellness 컬럼인지 확인
    wellness_cols = _get_wellness_columns(conn)
    
    if metric_name in wellness_cols:
        rows = conn.execute(f"""
            SELECT date, {metric_name} FROM daily_wellness
            WHERE date >= ? AND {metric_name} IS NOT NULL
            ORDER BY date
        """, [start]).fetchall()
        return {
            "dates": [r[0] for r in rows],
            "values": [r[1] for r in rows],
            "providers": ["source"] * len(rows),
        }
    else:
        rows = conn.execute("""
            SELECT scope_id, numeric_value, provider
            FROM metric_store
            WHERE scope_type = 'daily' AND metric_name = ? AND is_primary = 1
            AND scope_id >= ?
            ORDER BY scope_id
        """, [metric_name, start]).fetchall()
        return {
            "dates": [r[0] for r in rows],
            "values": [r[1] for r in rows],
            "providers": [r[2] for r in rows],
        }


def _this_monday() -> str:
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _determine_training_status(fitness: dict) -> str:
    if not fitness:
        return "unknown"
    
    tsb = fitness.get("tsb")
    ramp = fitness.get("ramp_rate")
    ctl = fitness.get("ctl")
    
    if ctl is None or ctl < 5:
        return "building"
    
    if ramp and ramp > 0.5:
        if tsb and tsb < -15:
            return "overreaching"
        return "productive"
    elif ramp and ramp < -0.3:
        return "detraining"
    else:
        if tsb and tsb > 10:
            return "fresh"
        return "maintaining"


def _get_wellness_columns(conn):
    return [r[1] for r in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
```

### `wellness_service.py` — 웰니스 & 리커버리

```python
# src/services/wellness_service.py

from datetime import datetime, timedelta
from src.utils.db_helpers import get_primary_metrics


def get_wellness_detail(conn, date: str) -> dict:
    """
    특정 날짜의 웰니스 상세.
    daily_wellness(core) + metric_store(daily scope, 모든 카테고리).
    
    Returns: {
        "date": "2026-04-01",
        "core": {...},          # daily_wellness 행
        "metrics_by_category": {
            "sleep": [...],
            "stress": [...],
            "hrv": [...],
            "readiness": [...],
            "prediction": [...],
            "rp_readiness": [...],
            "rp_risk": [...],
        },
        "provider_comparison": {...},
    }
    """
    # Core
    row = conn.execute("SELECT * FROM daily_wellness WHERE date = ?", [date]).fetchone()
    core = None
    if row:
        cols = [d[1] for d in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
        core = dict(zip(cols, row))
    
    # All daily metrics
    metrics_rows = conn.execute("""
        SELECT metric_name, category, provider, numeric_value, text_value, json_value,
               confidence, is_primary
        FROM metric_store
        WHERE scope_type = 'daily' AND scope_id = ?
        ORDER BY category, is_primary DESC
    """, [date]).fetchall()
    
    from src.utils.metric_registry import METRIC_REGISTRY
    
    metrics_by_category = {}
    provider_comparison = {}
    
    for name, cat, provider, num, text, json_val, conf, is_primary in metrics_rows:
        # Primary만 카테고리별로
        if is_primary:
            if cat not in metrics_by_category:
                metrics_by_category[cat] = []
            
            import json
            reg = METRIC_REGISTRY.get(name)
            metrics_by_category[cat].append({
                "metric_name": name,
                "display_name": reg.description if reg else name,
                "value": num if num is not None else text,
                "json_value": json.loads(json_val) if json_val else None,
                "unit": reg.unit if reg else None,
                "provider": provider,
                "confidence": conf,
            })
        
        # Provider 비교
        if name not in provider_comparison:
            provider_comparison[name] = []
        provider_comparison[name].append({
            "provider": provider,
            "value": num if num is not None else text,
            "is_primary": bool(is_primary),
        })
    
    return {
        "date": date,
        "core": core,
        "metrics_by_category": metrics_by_category,
        "provider_comparison": provider_comparison,
    }


def get_wellness_trend(conn, days: int = 30) -> dict:
    """
    웰니스 추세 (대시보드 하단 차트).
    Returns: {
        "dates": [...],
        "sleep_score": [...],
        "hrv_last_night": [...],
        "resting_hr": [...],
        "body_battery_high": [...],
        "avg_stress": [...],
        "utrs": [...],
        "cirs": [...],
    }
    """
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Core wellness
    rows = conn.execute("""
        SELECT date, sleep_score, hrv_last_night, resting_hr, 
               body_battery_high, avg_stress
        FROM daily_wellness
        WHERE date >= ?
        ORDER BY date
    """, [start]).fetchall()
    
    dates = [r[0] for r in rows]
    result = {
        "dates": dates,
        "sleep_score": [r[1] for r in rows],
        "hrv_last_night": [r[2] for r in rows],
        "resting_hr": [r[3] for r in rows],
        "body_battery_high": [r[4] for r in rows],
        "avg_stress": [r[5] for r in rows],
    }
    
    # UTRS & CIRS from metric_store
    for metric_name in ("utrs", "cirs"):
        metric_rows = conn.execute("""
            SELECT scope_id, numeric_value
            FROM metric_store
            WHERE scope_type = 'daily' AND metric_name = ? AND is_primary = 1
            AND scope_id >= ?
            ORDER BY scope_id
        """, [metric_name, start]).fetchall()
        
        metric_map = {r[0]: r[1] for r in metric_rows}
        result[metric_name] = [metric_map.get(d) for d in dates]
    
    return result
```

---

## 5-3. AI Context Builder 재설계

AI Coach에 보낼 컨텍스트를 새 스키마에서 구성합니다. 기존 `ai_context.py`는 여러 테이블을 하드코딩된 쿼리로 읽었습니다.

```python
# src/ai/ai_context.py

import json
from datetime import datetime, timedelta
from src.services.dashboard_service import get_dashboard_data
from src.services.activity_service import get_activity_detail, get_activity_trend
from src.utils.metric_registry import METRIC_REGISTRY
from src.utils.metric_groups import SEMANTIC_GROUPS


def build_daily_briefing_context(conn) -> str:
    """
    AI 일일 브리핑용 컨텍스트 생성.
    마크다운 형식으로 반환.
    """
    dashboard = get_dashboard_data(conn)
    
    sections = []
    
    # ── 오늘의 상태 ──
    sections.append("## 오늘의 상태\n")
    
    wellness = dashboard.get("today_wellness") or {}
    readiness = dashboard.get("today_readiness") or {}
    fitness = dashboard.get("fitness_summary") or {}
    
    if wellness:
        sections.append(f"- 수면 점수: {wellness.get('sleep_score', 'N/A')}/100")
        sections.append(f"- 수면 시간: {_format_duration(wellness.get('sleep_duration_sec'))}")
        sections.append(f"- HRV (전날 밤): {wellness.get('hrv_last_night', 'N/A')}ms")
        sections.append(f"- HRV (주간 평균): {wellness.get('hrv_weekly_avg', 'N/A')}ms")
        sections.append(f"- 안정시 심박: {wellness.get('resting_hr', 'N/A')}bpm")
        sections.append(f"- Body Battery: {wellness.get('body_battery_low', '?')}~{wellness.get('body_battery_high', '?')}")
        sections.append(f"- 스트레스: {wellness.get('avg_stress', 'N/A')}/100")
    
    utrs = readiness.get("utrs", {})
    cirs = readiness.get("cirs", {})
    if utrs:
        sections.append(f"- **RunPulse 훈련 준비도 (UTRS)**: {utrs.get('numeric_value', 'N/A')}/100 "
                        f"(신뢰도 {utrs.get('confidence', '?')})")
    if cirs:
        sections.append(f"- **RunPulse 부상 위험 (CIRS)**: {cirs.get('numeric_value', 'N/A')}/100")
    
    if fitness:
        sections.append(f"\n### 체력 모델 (PMC)")
        sections.append(f"- CTL (만성 부하): {fitness.get('ctl', 'N/A'):.1f}")
        sections.append(f"- ATL (급성 부하): {fitness.get('atl', 'N/A'):.1f}")
        sections.append(f"- TSB (피로도): {fitness.get('tsb', 'N/A'):.1f}")
        sections.append(f"- 훈련 상태: {dashboard.get('training_status', 'unknown')}")
    
    # ── 이번 주 요약 ──
    weekly = dashboard.get("weekly_summary", {})
    sections.append(f"\n## 이번 주 요약")
    sections.append(f"- 달리기 횟수: {weekly.get('count', 0)}회")
    sections.append(f"- 총 거리: {(weekly.get('total_distance_m', 0) / 1000):.1f}km")
    sections.append(f"- 총 시간: {_format_duration(weekly.get('total_duration_sec'))}")
    
    # ── 최근 활동 ──
    sections.append(f"\n## 최근 활동")
    for act in dashboard.get("recent_activities", [])[:5]:
        wt = act.get("workout_type", {})
        wt_label = wt.get("type", "?") if isinstance(wt, dict) else "?"
        dist_km = (act.get("distance_m") or 0) / 1000
        pace = _format_pace(act.get("avg_pace_sec_km"))
        sections.append(
            f"- {act.get('start_time', '')[:10]} {act.get('name', '?')}: "
            f"{dist_km:.1f}km, {_format_duration(act.get('duration_sec'))}, "
            f"페이스 {pace}, HR {act.get('avg_hr', '?')}bpm, "
            f"부하 {act.get('training_load', '?')}, 유형 {wt_label}"
        )
    
    # ── 레이스 예측 ──
    predictions = dashboard.get("race_predictions", {})
    if predictions:
        sections.append(f"\n## 레이스 예측 (RunPulse DARP)")
        for key, label in [("darp_5k", "5K"), ("darp_10k", "10K"), 
                            ("darp_half", "하프"), ("darp_full", "풀")]:
            val = predictions.get(key)
            if val:
                sections.append(f"- {label}: {_format_time(val)}")
    
    return "\n".join(sections)


def build_activity_analysis_context(conn, activity_id: int) -> str:
    """
    AI 활동 심층 분석용 컨텍스트.
    """
    detail = get_activity_detail(conn, activity_id)
    if not detail:
        return "활동을 찾을 수 없습니다."
    
    summary = detail["summary"]
    sections = []
    
    sections.append(f"## 활동 분석: {summary.get('name', '무제')}")
    sections.append(f"- 날짜: {summary.get('start_time', '')[:10]}")
    sections.append(f"- 유형: {summary.get('activity_type')}")
    sections.append(f"- 거리: {(summary.get('distance_m', 0) / 1000):.2f}km")
    sections.append(f"- 시간: {_format_duration(summary.get('duration_sec'))}")
    sections.append(f"- 평균 페이스: {_format_pace(summary.get('avg_pace_sec_km'))}")
    sections.append(f"- 평균 심박: {summary.get('avg_hr', 'N/A')}bpm / 최대: {summary.get('max_hr', 'N/A')}bpm")
    sections.append(f"- 평균 케이던스: {summary.get('avg_cadence', 'N/A')}spm")
    
    if summary.get("avg_ground_contact_time_ms"):
        sections.append(f"\n### 러닝 다이내믹스")
        sections.append(f"- GCT: {summary['avg_ground_contact_time_ms']:.0f}ms")
        sections.append(f"- 보폭: {summary.get('avg_stride_length_cm', 'N/A')}cm")
        sections.append(f"- 수직진동: {summary.get('avg_vertical_oscillation_cm', 'N/A')}cm")
        sections.append(f"- 수직비율: {summary.get('avg_vertical_ratio_pct', 'N/A')}%")
    
    # ── 카테고리별 메트릭 ──
    for cat, metrics in detail.get("metrics_by_category", {}).items():
        if cat.startswith("_"):
            continue
        sections.append(f"\n### {_category_display_name(cat)}")
        for m in metrics:
            val_str = _format_metric_value(m)
            provider_note = f" [{m['provider']}]" if not m["provider"].startswith("runpulse") else ""
            sections.append(f"- {m['display_name']}: {val_str}{provider_note}")
    
    # ── Provider 비교 (같은 메트릭, 다른 소스) ──
    comparisons = detail.get("provider_comparison", {})
    multi_provider = {k: v for k, v in comparisons.items() if len(v) > 1}
    if multi_provider:
        sections.append(f"\n### 소스별 비교")
        for metric_name, providers in multi_provider.items():
            reg = METRIC_REGISTRY.get(metric_name)
            display = reg.description if reg else metric_name
            vals = ", ".join(
                f"{p['provider']}={p['numeric_value']}" 
                for p in providers if p.get("numeric_value") is not None
            )
            sections.append(f"- {display}: {vals}")
    
    # ── Workout Type ──
    wt = detail.get("workout_type")
    if wt:
        sections.append(f"\n### 운동 유형 분류")
        sections.append(f"- 분류: {wt.get('type', '?')}")
        sections.append(f"- 신뢰도: {wt.get('confidence', '?')}")
        if wt.get("reasons"):
            sections.append(f"- 근거: {', '.join(wt['reasons'])}")
    
    return "\n".join(sections)


# ── 포맷 헬퍼 ──

def _format_duration(seconds) -> str:
    if not seconds:
        return "N/A"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"

def _format_pace(sec_per_km) -> str:
    if not sec_per_km:
        return "N/A"
    m = int(sec_per_km // 60)
    s = int(sec_per_km % 60)
    return f"{m}:{s:02d}/km"

def _format_time(seconds) -> str:
    if not seconds:
        return "N/A"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def _format_metric_value(metric: dict) -> str:
    val = metric.get("value")
    unit = metric.get("unit") or ""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.1f} {unit}".strip()
    return f"{val} {unit}".strip()

CATEGORY_NAMES = {
    "hr_zone": "심박 존", "power_zone": "파워 존", "pace_zone": "페이스 존",
    "training_load": "훈련 부하", "running_dynamics": "러닝 다이내믹스",
    "efficiency": "효율성", "weather": "날씨", "fitness": "체력",
    "sleep": "수면", "stress": "스트레스", "hrv": "HRV", "recovery": "회복",
    "readiness": "준비도", "prediction": "예측", "general": "일반",
    "rp_load": "RunPulse 부하", "rp_readiness": "RunPulse 준비도",
    "rp_risk": "RunPulse 위험", "rp_efficiency": "RunPulse 효율",
    "rp_performance": "RunPulse 퍼포먼스", "rp_distribution": "RunPulse 강도",
    "rp_maturity": "RunPulse 성숙도", "rp_classification": "RunPulse 분류",
}

def _category_display_name(cat: str) -> str:
    return CATEGORY_NAMES.get(cat, cat)
```

---

## 5-4. Analysis 모듈 마이그레이션

기존 `src/analysis/*.py` 모듈은 직접 SQL을 실행했습니다. 새 구조에서는 서비스 레이어를 통해 데이터를 가져오도록 전환합니다.

```python
# src/analysis/report.py — 재작성 핵심 부분

from src.services.dashboard_service import get_dashboard_data, get_pmc_chart_data
from src.services.activity_service import get_activity_list, get_activity_trend
from src.services.wellness_service import get_wellness_trend


def generate_weekly_report(conn) -> str:
    """주간 보고서 마크다운 생성"""
    
    dashboard = get_dashboard_data(conn)
    wellness_trend = get_wellness_trend(conn, days=7)
    pmc = get_pmc_chart_data(conn, days=14)
    
    activities = get_activity_list(conn, filters={
        "start_date": _this_monday(),
        "activity_type": "running",
    }, per_page=50)
    
    report = []
    report.append(f"# RunPulse 주간 보고서 ({_this_monday()} ~ 오늘)\n")
    
    # 주간 요약
    weekly = dashboard.get("weekly_summary", {})
    report.append(f"## 요약")
    report.append(f"- 달리기: {weekly.get('count', 0)}회")
    report.append(f"- 총 거리: {weekly.get('total_distance_m', 0) / 1000:.1f}km")
    report.append(f"- 총 시간: {_format_duration(weekly.get('total_duration_sec'))}")
    
    # 체력 변화
    fitness = dashboard.get("fitness_summary", {})
    if fitness:
        report.append(f"\n## 체력 모델")
        report.append(f"- CTL: {fitness.get('ctl', 0):.1f}")
        report.append(f"- TSB: {fitness.get('tsb', 0):.1f}")
        report.append(f"- 상태: {dashboard.get('training_status', 'unknown')}")
    
    # 활동별 상세
    report.append(f"\n## 활동 상세")
    for act in activities.get("activities", []):
        dist_km = (act.get("distance_m") or 0) / 1000
        report.append(
            f"- **{act.get('name', '?')}** ({act.get('start_time', '')[:10]}): "
            f"{dist_km:.1f}km, 페이스 {_format_pace(act.get('avg_pace_sec_km'))}, "
            f"HR {act.get('avg_hr', '?')}"
        )
    
    return "\n".join(report)


def _this_monday():
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    return (today - timedelta(days=today.weekday())).isoformat()

def _format_duration(sec):
    if not sec: return "N/A"
    return f"{int(sec//3600)}h {int((sec%3600)//60)}m"

def _format_pace(v):
    if not v: return "N/A"
    return f"{int(v//60)}:{int(v%60):02d}/km"
```

---

## 5-5. Flask View 모듈 마이그레이션 패턴

기존 뷰 모듈들은 직접 SQL을 쓰거나 기존 서비스를 호출합니다. 마이그레이션 패턴을 정합니다.

### 패턴: 뷰는 서비스만 호출, SQL 직접 쓰지 않음

```python
# src/web/views_dashboard.py — 마이그레이션 전

@bp.route("/")
def dashboard():
    conn = get_db()
    # 기존: 직접 SQL 여러 개
    activities = conn.execute("SELECT ... FROM activity_summaries ...").fetchall()
    wellness = conn.execute("SELECT ... FROM daily_wellness ...").fetchall()
    metrics = conn.execute("SELECT ... FROM computed_metrics ...").fetchall()
    return render_template("dashboard.html", ...)


# src/web/views_dashboard.py — 마이그레이션 후

@bp.route("/")
def dashboard():
    conn = get_db()
    data = get_dashboard_data(conn)
    return render_template("dashboard.html", **data)
```

### 마이그레이션 대상 뷰 목록 & 매핑

| 뷰 모듈 | 사용 서비스 | 주요 변경 |
|---------|-----------|----------|
| `views_dashboard.py` | `dashboard_service.get_dashboard_data()` | 직접 SQL → 서비스 호출 |
| `views_activities_table.py` | `activity_service.get_activity_list()` | unified_activities → 새 서비스 |
| `views_activity_deep.py` | `activity_service.get_activity_detail()`, `get_activity_streams()` | detail_metrics → metric_store 카테고리별 |
| `views_wellness.py` | `wellness_service.get_wellness_detail()`, `get_wellness_trend()` | daily_detail_metrics → metric_store |
| `views_report.py` | `analysis/report.py` | 새 report 모듈 호출 |
| `views_training.py` | `dashboard_service`, `activity_service` | computed_metrics → metric_store |
| `views_sync_ui.py` | 직접 `sync_jobs` 조회 (스키마 동일) | 컬럼명 미세 조정 |
| `views_export.py` | `activity_service.get_activity_list()` | distance_km → distance_m 변환 |
| `views_shoes.py` | 직접 `gear` 조회 (스키마 동일) | total_distance_m 단위 확인 |
| `views_merge_group.py` | `activity_service.get_activity_detail()` | group 정보 활용 |
| `views_settings.py` | config + sync_jobs | 변경 최소 |

---

## 5-6. Template 마이그레이션 — 단위 변환 & 포맷팅

### Jinja2 전역 함수 등록

```python
# src/web/template_helpers.py

from src.utils.metric_registry import METRIC_REGISTRY


def register_template_helpers(app):
    """Flask app에 Jinja2 전역 함수 등록"""
    
    @app.template_global()
    def format_distance(meters, unit="km"):
        """거리 포맷. DB는 m 단위, UI는 km."""
        if meters is None:
            return "—"
        km = meters / 1000
        if km >= 100:
            return f"{km:.0f} km"
        elif km >= 10:
            return f"{km:.1f} km"
        else:
            return f"{km:.2f} km"
    
    @app.template_global()
    def format_pace(sec_per_km):
        """페이스 포맷 (sec/km → M:SS/km)"""
        if sec_per_km is None:
            return "—"
        minutes = int(sec_per_km // 60)
        seconds = int(sec_per_km % 60)
        return f"{minutes}:{seconds:02d}"
    
    @app.template_global()
    def format_duration(seconds):
        """시간 포맷"""
        if seconds is None:
            return "—"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    
    @app.template_global()
    def format_time_prediction(seconds):
        """레이스 예측 시간 포맷"""
        if seconds is None:
            return "—"
        return format_duration(seconds)
    
    @app.template_global()
    def format_speed(ms):
        """속도 포맷 (m/s → km/h)"""
        if ms is None:
            return "—"
        kmh = ms * 3.6
        return f"{kmh:.1f}"
    
    @app.template_global()
    def format_metric(value, metric_name):
        """metric_registry에 따른 자동 포맷"""
        if value is None:
            return "—"
        
        reg = METRIC_REGISTRY.get(metric_name)
        if not reg:
            return str(value)
        
        unit = reg.unit or ""
        
        if reg.unit == "sec/km":
            return format_pace(value)
        elif reg.unit == "sec":
            return format_duration(value)
        elif reg.unit == "m":
            return format_distance(value)
        elif isinstance(value, float):
            return f"{value:.1f} {unit}".strip()
        else:
            return f"{value} {unit}".strip()
    
    @app.template_global()
    def metric_display_name(metric_name):
        """메트릭의 한국어 표시명"""
        reg = METRIC_REGISTRY.get(metric_name)
        return reg.description if reg else metric_name
    
    @app.template_global()
    def metric_unit(metric_name):
        """메트릭 단위"""
        reg = METRIC_REGISTRY.get(metric_name)
        return reg.unit if reg else ""
    
    @app.template_global()
    def workout_type_color(wt_type):
        """운동 유형별 색상"""
        colors = {
            "easy": "#4CAF50",
            "recovery": "#8BC34A",
            "long_run": "#2196F3",
            "tempo": "#FF9800",
            "threshold": "#F44336",
            "interval": "#9C27B0",
            "race": "#FFD700",
            "unknown": "#9E9E9E",
        }
        return colors.get(wt_type, "#9E9E9E")
    
    @app.template_global()
    def metric_level_color(metric_name, value):
        """메트릭 값에 따른 색상 (좋음/보통/나쁨)"""
        from src.metrics.engine import ALL_CALCULATORS
        
        for calc in ALL_CALCULATORS:
            if metric_name in calc.produces and calc.ranges:
                for level, (low, high) in calc.ranges.items():
                    if low <= value < high:
                        return _level_color(level, calc.higher_is_better)
        
        return "#FFFFFF"
    
    @app.template_global()
    def confidence_badge(confidence):
        """신뢰도 배지 HTML"""
        if confidence is None:
            return ""
        if confidence >= 0.8:
            return f'<span class="badge badge-confidence high">{confidence:.0%}</span>'
        elif confidence >= 0.5:
            return f'<span class="badge badge-confidence mid">{confidence:.0%}</span>'
        else:
            return f'<span class="badge badge-confidence low">{confidence:.0%}</span>'
    
    @app.template_global()
    def provider_badge(provider):
        """데이터 출처 배지"""
        colors = {
            "garmin": "#007DC1",
            "strava": "#FC4C02",
            "intervals": "#1A73E8",
            "runalyze": "#00A651",
        }
        if provider.startswith("runpulse"):
            return f'<span class="badge badge-provider rp">RP</span>'
        elif provider == "user":
            return f'<span class="badge badge-provider user">사용자</span>'
        else:
            color = colors.get(provider, "#666")
            return f'<span class="badge badge-provider" style="background:{color}">{provider}</span>'


def _level_color(level, higher_is_better):
    positive = {"excellent": "#4CAF50", "good": "#8BC34A", "moderate": "#FFC107"}
    negative = {"poor": "#F44336", "low": "#FF5722", "high": "#F44336"}
    neutral = {"unknown": "#9E9E9E"}
    
    all_colors = {**positive, **negative, **neutral}
    return all_colors.get(level, "#9E9E9E")
```

### Template 사용 예시

```html
<!-- templates/activity_card.html -->
<div class="activity-card">
    <h3>{{ activity.name or "무제" }}</h3>
    <span class="workout-badge" style="background: {{ workout_type_color(activity.workout_type.type) }}">
        {{ activity.workout_type.type }}
    </span>
    
    <div class="stats-grid">
        <div class="stat">
            <label>거리</label>
            <value>{{ format_distance(activity.distance_m) }}</value>
        </div>
        <div class="stat">
            <label>시간</label>
            <value>{{ format_duration(activity.duration_sec) }}</value>
        </div>
        <div class="stat">
            <label>페이스</label>
            <value>{{ format_pace(activity.avg_pace_sec_km) }}/km</value>
        </div>
        <div class="stat">
            <label>심박</label>
            <value>{{ activity.avg_hr or '—' }} bpm</value>
        </div>
    </div>
</div>

<!-- templates/metric_card.html (재사용 매크로) -->
{% macro render_metric(metric) %}
<div class="metric-item">
    <span class="metric-name">{{ metric.display_name }}</span>
    <span class="metric-value">{{ format_metric(metric.value, metric.metric_name) }}</span>
    {% if metric.confidence %}
        {{ confidence_badge(metric.confidence) }}
    {% endif %}
    {{ provider_badge(metric.provider) }}
</div>
{% endmacro %}

<!-- templates/activity_detail.html — 카테고리별 메트릭 카드 -->
{% for category, metrics in metrics_by_category.items() %}
    {% if not category.startswith('_') %}
    <div class="metric-category-card">
        <h4>{{ category_display_name(category) }}</h4>
        {% for m in metrics %}
            {{ render_metric(m) }}
        {% endfor %}
    </div>
    {% endif %}
{% endfor %}

<!-- provider 비교 뷰 -->
{% if provider_comparison %}
<div class="provider-comparison">
    <h4>소스별 비교</h4>
    {% for metric_name, providers in provider_comparison.items() %}
        {% if providers|length > 1 %}
        <div class="comparison-row">
            <span class="metric-name">{{ metric_display_name(metric_name) }}</span>
            {% for p in providers %}
                <span class="provider-value {% if p.is_primary %}primary{% endif %}">
                    {{ provider_badge(p.provider) }}
                    {{ format_metric(p.numeric_value or p.text_value, metric_name) }}
                </span>
            {% endfor %}
        </div>
        {% endif %}
    {% endfor %}
</div>
{% endif %}
```

---

## 5-7. 기존 `unified_activities.py` 제거 & 마이그레이션

기존 `unified_activities.py`는 `activity_summaries`와 `activity_detail_metrics`를 JOIN해서 통합 뷰를 만들었습니다. v0.3에서는 이 역할이 `activity_service.py`로 대체됩니다.

```python
# src/services/unified_activities.py — 호환성 래퍼 (점진적 마이그레이션용)

import warnings
from src.services.activity_service import get_activity_list, get_activity_detail


def fetch_unified_activities(conn, **kwargs):
    """
    기존 코드 호환용. 새 코드에서는 activity_service를 직접 사용하세요.
    """
    warnings.warn(
        "fetch_unified_activities is deprecated. Use activity_service.get_activity_list()",
        DeprecationWarning,
        stacklevel=2,
    )
    result = get_activity_list(conn, filters=kwargs)
    return result["activities"]
```

기존 코드에서 `unified_activities`를 import하는 모든 곳을 찾아서 `activity_service`로 교체합니다. 즉시 교체가 어려운 곳은 이 래퍼를 통해 동작하게 두고, DeprecationWarning으로 추후 정리합니다.

---

## 5-8. Export 마이그레이션

기존 export는 `activity_summaries`의 `distance_km` 등을 직접 썼습니다. 단위가 변경되었으므로 변환이 필요합니다.

```python
# src/web/views_export.py — 변경 필요 부분

def export_csv(conn, filters=None):
    """활동 데이터 CSV 내보내기"""
    from src.services.activity_service import get_activity_list
    
    data = get_activity_list(conn, filters=filters, per_page=10000)
    
    rows = []
    for act in data["activities"]:
        rows.append({
            "날짜": act.get("start_time", "")[:10],
            "이름": act.get("name", ""),
            "유형": act.get("activity_type", ""),
            "거리(km)": round((act.get("distance_m") or 0) / 1000, 2),
            "시간(분)": round((act.get("duration_sec") or 0) / 60, 1),
            "페이스(min/km)": _pace_str(act.get("avg_pace_sec_km")),
            "평균심박": act.get("avg_hr", ""),
            "최대심박": act.get("max_hr", ""),
            "케이던스": act.get("avg_cadence", ""),
            "고도상승(m)": act.get("elevation_gain", ""),
            "칼로리": act.get("calories", ""),
            "훈련부하": act.get("training_load", ""),
            "소스": act.get("source", ""),
        })
    
    # CSV 생성 ...
```

---

## 5-9. Background Sync UI 마이그레이션

```python
# src/web/views_sync_ui.py — 변경 부분

def get_sync_status(conn) -> list[dict]:
    """최근 sync 작업 상태"""
    rows = conn.execute("""
        SELECT id, source, job_type, status, completed_items, error_count,
               last_error, created_at, updated_at
        FROM sync_jobs
        ORDER BY created_at DESC
        LIMIT 20
    """).fetchall()
    
    return [
        {
            "id": r[0],
            "source": r[1],
            "job_type": r[2],         # 새 필드
            "status": r[3],
            "completed": r[4],        # total_days → completed_items
            "errors": r[5],           # 새 필드
            "last_error": r[6],
            "created_at": r[7],
            "updated_at": r[8],
        }
        for r in rows
    ]
```

---

## 5-10. 마이그레이션 호환성 검증 — 스모크 테스트

```python
# tests/test_consumer_migration.py

import pytest
from src.services.activity_service import get_activity_list, get_activity_detail, get_activity_trend
from src.services.dashboard_service import get_dashboard_data, get_pmc_chart_data
from src.services.wellness_service import get_wellness_detail, get_wellness_trend
from src.ai.ai_context import build_daily_briefing_context, build_activity_analysis_context


@pytest.fixture
def populated_db(test_db):
    """Phase 1~4 통과 후 데이터가 채워진 테스트 DB"""
    # fixture로 최소한의 데이터 삽입
    _insert_sample_data(test_db)
    return test_db


class TestActivityService:
    
    def test_activity_list_returns_structure(self, populated_db):
        result = get_activity_list(populated_db)
        assert "activities" in result
        assert "total" in result
        assert "page" in result
        assert "pages" in result
    
    def test_activity_list_filtering(self, populated_db):
        result = get_activity_list(populated_db, filters={"activity_type": "running"})
        for act in result["activities"]:
            assert act["activity_type"] == "running"
    
    def test_activity_list_search(self, populated_db):
        result = get_activity_list(populated_db, filters={"search": "오후"})
        # 검색이 name과 description에서 작동
        assert isinstance(result["activities"], list)
    
    def test_activity_list_distance_in_meters(self, populated_db):
        result = get_activity_list(populated_db)
        for act in result["activities"]:
            if act.get("distance_m"):
                assert act["distance_m"] > 100  # m 단위
    
    def test_activity_detail_has_categories(self, populated_db):
        activities = get_activity_list(populated_db)
        if activities["activities"]:
            aid = activities["activities"][0]["id"]
            detail = get_activity_detail(populated_db, aid)
            assert detail is not None
            assert "summary" in detail
            assert "metrics_by_category" in detail
            assert "provider_comparison" in detail
            assert "laps" in detail
    
    def test_activity_detail_no_overlap(self, populated_db):
        """metric_store의 메트릭이 activity_summaries 컬럼과 겹치지 않는지"""
        activities = get_activity_list(populated_db)
        if activities["activities"]:
            aid = activities["activities"][0]["id"]
            detail = get_activity_detail(populated_db, aid)
            
            summary_keys = set(detail["summary"].keys())
            for cat, metrics in detail["metrics_by_category"].items():
                for m in metrics:
                    assert m["metric_name"] not in summary_keys, \
                        f"Metric {m['metric_name']} overlaps with summary column"
    
    def test_activity_trend(self, populated_db):
        trend = get_activity_trend(populated_db, "avg_pace_sec_km", days=30)
        assert isinstance(trend, list)
        for point in trend:
            assert "date" in point
            assert "value" in point


class TestDashboardService:
    
    def test_dashboard_data_structure(self, populated_db):
        data = get_dashboard_data(populated_db)
        assert "today_wellness" in data
        assert "today_readiness" in data
        assert "fitness_summary" in data
        assert "recent_activities" in data
        assert "weekly_summary" in data
        assert "race_predictions" in data
        assert "training_status" in data
    
    def test_pmc_chart_data(self, populated_db):
        data = get_pmc_chart_data(populated_db, days=30)
        assert "dates" in data
        assert "ctl" in data
        assert "atl" in data
        assert "tsb" in data
        assert len(data["dates"]) == len(data["ctl"])


class TestWellnessService:
    
    def test_wellness_trend_structure(self, populated_db):
        data = get_wellness_trend(populated_db, days=7)
        assert "dates" in data
        assert "sleep_score" in data
        assert "utrs" in data
        assert "cirs" in data


class TestAIContext:
    
    def test_daily_briefing_not_empty(self, populated_db):
        ctx = build_daily_briefing_context(populated_db)
        assert isinstance(ctx, str)
        assert len(ctx) > 100  # 최소한의 내용
    
    def test_daily_briefing_contains_sections(self, populated_db):
        ctx = build_daily_briefing_context(populated_db)
        assert "상태" in ctx or "요약" in ctx
    
    def test_activity_analysis_context(self, populated_db):
        activities = get_activity_list(populated_db)
        if activities["activities"]:
            aid = activities["activities"][0]["id"]
            ctx = build_activity_analysis_context(populated_db, aid)
            assert isinstance(ctx, str)
            assert "분석" in ctx


class TestTemplateHelpers:
    
    def test_format_distance(self):
        from src.web.template_helpers import register_template_helpers
        # 직접 함수 테스트
        assert "10.00 km" in _call_format_distance(10000)
        assert "0.50 km" in _call_format_distance(500)
    
    def test_format_pace(self):
        assert _call_format_pace(300) == "5:00"
        assert _call_format_pace(330) == "5:30"
        assert _call_format_pace(None) == "—"
    
    def test_format_metric_pace_type(self):
        # fearp는 unit="sec/km" → 페이스 형식
        assert ":" in _call_format_metric(320, "fearp")
```

---

## 5-11. Phase 5 산출물 & 작업 순서

| 순서 | 파일 | 작업 | 예상 시간 |
|------|------|------|----------|
| 1 | `src/services/activity_service.py` | 활동 목록/상세/추세/스트림 서비스 | 3시간 |
| 2 | `src/services/dashboard_service.py` | 대시보드/PMC/일별 차트 서비스 | 2시간 |
| 3 | `src/services/wellness_service.py` | 웰니스 상세/추세 서비스 | 1.5시간 |
| 4 | `src/ai/ai_context.py` | AI 컨텍스트 빌더 재작성 | 2시간 |
| 5 | `src/analysis/report.py` | 주간 보고서 재작성 | 1.5시간 |
| 6 | `src/web/template_helpers.py` | Jinja2 전역 함수 등록 | 1.5시간 |
| 7 | `src/web/views_dashboard.py` | 서비스 호출로 전환 | 1시간 |
| 8 | `src/web/views_activities_table.py` | 서비스 호출로 전환 | 1시간 |
| 9 | `src/web/views_activity_deep.py` | 카테고리별 메트릭 표시 | 2시간 |
| 10 | `src/web/views_wellness.py` | metric_store 기반 전환 | 1시간 |
| 11 | `src/web/views_training.py` | metric_store 기반 전환 | 1시간 |
| 12 | `src/web/views_report.py` | 새 report 모듈 연결 | 30분 |
| 13 | `src/web/views_export.py` | 단위 변환 (m → km) | 30분 |
| 14 | `src/web/views_sync_ui.py` | sync_jobs 스키마 적응 | 30분 |
| 15 | `src/services/unified_activities.py` | 호환성 래퍼 (deprecated) | 30분 |
| 16 | `src/utils/metric_groups.py` | 의미적 그룹핑 정의 | 1시간 |
| 17 | Template 수정 | activity_card, detail, wellness 등 | 3시간 |
| 18 | `tests/test_activity_service.py` | 서비스 레이어 테스트 | 1.5시간 |
| 19 | `tests/test_dashboard_service.py` | 대시보드 서비스 테스트 | 1시간 |
| 20 | `tests/test_wellness_service.py` | 웰니스 서비스 테스트 | 30분 |
| 21 | `tests/test_ai_context.py` | AI 컨텍스트 테스트 | 1시간 |
| 22 | `tests/test_template_helpers.py` | 포맷 함수 단위 테스트 | 30분 |
| 23 | `tests/test_consumer_migration.py` | 스모크 테스트 | 1.5시간 |
| 24 | Flask 라우트 스모크 테스트 | 전체 라우트 200 응답 확인 | 1시간 |

**총 예상: ~30시간 (6~7 세션)**

---

## 5-12. Phase 5 완료 기준 (Definition of Done)

1. **모든 뷰 모듈**에서 `activity_detail_metrics`, `daily_detail_metrics`, `computed_metrics` 테이블 직접 참조 제거
2. **모든 뷰 모듈**이 `src/services/` 레이어를 통해 데이터 조회
3. `distance_km` 참조 없음 → 모든 곳에서 `distance_m` 사용, UI에서 km 변환
4. `get_activity_detail()`이 `metrics_by_category`를 올바르게 반환 (카테고리 그룹핑)
5. `get_activity_detail()`의 `provider_comparison`에 멀티 소스 비교 데이터 포함
6. `build_daily_briefing_context()`가 UTRS, CIRS, PMC, DARP 정보 포함
7. Template 헬퍼 (`format_distance`, `format_pace`, `format_metric` 등) 정상 동작
8. `confidence_badge`, `provider_badge` 렌더링 정상
9. Export CSV에서 거리가 km 단위로 변환되어 출력
10. DeprecationWarning 없이 모든 주요 뷰 동작 (unified_activities 래퍼 미사용)
11. `pytest tests/test_*_service.py tests/test_ai_context.py tests/test_template_helpers.py tests/test_consumer_migration.py` 전체 통과
12. Flask 전체 라우트 스모크 테스트 (HTTP 200) 통과

---
