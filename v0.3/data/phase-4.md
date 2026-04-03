

# Phase 4 상세 설계 — Metrics Engine 재구축

## 4-0. Phase 4의 목표

Phase 3까지 완료되면, `activity_summaries`(Layer 1)와 `metric_store`(Layer 2, 소스 데이터)에 데이터가 채워져 있습니다. Phase 4에서는 **이 데이터를 입력으로 RunPulse 자체 메트릭을 계산하고, 같은 `metric_store`에 `provider=runpulse:*`로 저장**합니다.

핵심 원칙:
- 모든 calculator는 `metric_store`에서 읽고 `metric_store`에 쓴다 (동일 테이블, provider만 다름)
- 의존성 그래프를 자동으로 해소한다 (TRIMP → ATL/CTL → ACWR → CIRS 순서)
- 입력 데이터가 부족하면 `None`을 반환하고, `confidence` 필드로 신뢰도를 표시한다
- 재계산이 쉽다 (`provider LIKE 'runpulse%'`인 행만 삭제 후 재실행)

---

## 4-1. MetricCalculator 기본 클래스

```python
# src/metrics/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import logging

log = logging.getLogger(__name__)


@dataclass
class CalcResult:
    """계산 결과 하나. metric_store에 저장될 데이터."""
    metric_name: str
    scope_type: str                        # 'activity' | 'daily' | 'weekly' | 'athlete'
    scope_id: str
    category: str
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    json_value: Optional[str] = None
    confidence: Optional[float] = None     # 0.0~1.0
    parent_metric_id: Optional[int] = None
    
    def is_empty(self) -> bool:
        return (self.numeric_value is None and 
                self.text_value is None and 
                self.json_value is None)


class MetricCalculator(ABC):
    """모든 RunPulse 메트릭 계산기의 기본 클래스"""
    
    # ── 서브클래스가 반드시 정의해야 하는 속성 ──
    name: str = ""                         # 정규 메트릭 이름 (예: "trimp")
    provider: str = "runpulse:formula_v1"  # metric_store.provider 값
    version: str = "1.0"                   # algorithm_version
    scope_type: str = "activity"           # 이 calculator가 생성하는 scope
    category: str = ""                     # metric_store.category
    
    # 이 calculator가 필요로 하는 입력 메트릭/컬럼 이름 목록
    # engine이 topological sort에 사용
    requires: list[str] = field(default_factory=list)
    
    # 이 calculator가 생성하는 메트릭 이름 목록
    # (대부분 [self.name]이지만, 여러 개를 한 번에 생성하는 경우도 있음)
    produces: list[str] = field(default_factory=list)
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.produces:
            cls.produces = [cls.name] if cls.name else []
    
    @abstractmethod
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        """
        메트릭 계산 실행.
        
        반환: CalcResult 리스트 (보통 1개, 여러 메트릭을 동시에 생성하는 경우 N개)
        입력 데이터가 부족하면 빈 리스트 반환.
        """
        ...
    
    def _result(self, value=None, text=None, json_val=None,
                confidence=None, scope_id=None, metric_name=None) -> CalcResult:
        """CalcResult 생성 헬퍼"""
        import json as json_mod
        return CalcResult(
            metric_name=metric_name or self.name,
            scope_type=self.scope_type,
            scope_id=scope_id or "",  # engine에서 채워줌
            category=self.category,
            numeric_value=float(value) if value is not None else None,
            text_value=text,
            json_value=json_mod.dumps(json_val, ensure_ascii=False) if json_val is not None else None,
            confidence=confidence,
        )


@dataclass  
class CalcContext:
    """
    Calculator에 전달되는 컨텍스트.
    필요한 데이터를 lazy-load로 제공.
    """
    conn: object                           # SQLite connection
    scope_type: str                        # 현재 계산 대상의 scope
    scope_id: str                          # 현재 계산 대상의 ID
    
    _activity_cache: Optional[dict] = field(default=None, repr=False)
    _metrics_cache: Optional[dict] = field(default=None, repr=False)
    
    # ── Activity 데이터 접근 ──
    
    @property
    def activity(self) -> dict:
        """현재 활동의 activity_summaries 행 (scope_type='activity'일 때)"""
        if self._activity_cache is None and self.scope_type == "activity":
            row = self.conn.execute(
                "SELECT * FROM activity_summaries WHERE id = ?",
                [int(self.scope_id)]
            ).fetchone()
            if row:
                cols = [d[0] for d in self.conn.execute(
                    "SELECT * FROM activity_summaries LIMIT 0"
                ).description]
                self._activity_cache = dict(zip(cols, row))
            else:
                self._activity_cache = {}
        return self._activity_cache or {}
    
    # ── Metric 데이터 접근 ──
    
    def get_metric(self, metric_name: str, provider: str = None) -> Optional[float]:
        """
        현재 scope의 메트릭 값 조회.
        provider 미지정 시 is_primary=1인 값 반환.
        """
        if provider:
            row = self.conn.execute("""
                SELECT numeric_value FROM metric_store
                WHERE scope_type=? AND scope_id=? AND metric_name=? AND provider=?
            """, [self.scope_type, self.scope_id, metric_name, provider]).fetchone()
        else:
            row = self.conn.execute("""
                SELECT numeric_value FROM metric_store
                WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1
            """, [self.scope_type, self.scope_id, metric_name]).fetchone()
        return row[0] if row else None
    
    def get_metric_json(self, metric_name: str, provider: str = None) -> Optional[str]:
        """JSON 값 조회"""
        if provider:
            row = self.conn.execute("""
                SELECT json_value FROM metric_store
                WHERE scope_type=? AND scope_id=? AND metric_name=? AND provider=?
            """, [self.scope_type, self.scope_id, metric_name, provider]).fetchone()
        else:
            row = self.conn.execute("""
                SELECT json_value FROM metric_store
                WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1
            """, [self.scope_type, self.scope_id, metric_name]).fetchone()
        return row[0] if row else None
    
    def get_metric_text(self, metric_name: str) -> Optional[str]:
        """텍스트 값 조회"""
        row = self.conn.execute("""
            SELECT text_value FROM metric_store
            WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1
        """, [self.scope_type, self.scope_id, metric_name]).fetchone()
        return row[0] if row else None
    
    # ── 시계열/범위 접근 (daily, weekly scope에서 사용) ──
    
    def get_daily_metric_series(self, metric_name: str, days: int,
                                 provider: str = None) -> list[tuple[str, float]]:
        """
        과거 N일간의 일별 메트릭 시계열.
        Returns: [(date, value), ...]
        """
        from datetime import datetime, timedelta
        
        if self.scope_type == "daily":
            end_date = self.scope_id
        else:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
        
        if provider:
            rows = self.conn.execute("""
                SELECT scope_id, numeric_value FROM metric_store
                WHERE scope_type='daily' AND metric_name=? AND provider=?
                AND scope_id BETWEEN ? AND ?
                ORDER BY scope_id
            """, [metric_name, provider, start_date, end_date]).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT scope_id, numeric_value FROM metric_store
                WHERE scope_type='daily' AND metric_name=? AND is_primary=1
                AND scope_id BETWEEN ? AND ?
                ORDER BY scope_id
            """, [metric_name, start_date, end_date]).fetchall()
        
        return [(r[0], r[1]) for r in rows if r[1] is not None]
    
    def get_activities_in_range(self, days: int, activity_type: str = None) -> list[dict]:
        """
        과거 N일간의 활동 목록 (activity_summaries).
        """
        from datetime import datetime, timedelta
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        
        sql = """
            SELECT * FROM v_canonical_activities 
            WHERE start_time >= ? AND start_time <= ?
        """
        params = [start.isoformat(), end.isoformat()]
        
        if activity_type:
            sql += " AND activity_type = ?"
            params.append(activity_type)
        
        sql += " ORDER BY start_time"
        
        rows = self.conn.execute(sql, params).fetchall()
        if not rows:
            return []
        
        cols = [d[0] for d in self.conn.execute(
            "SELECT * FROM v_canonical_activities LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]
    
    def get_activity_metric(self, activity_id: int, metric_name: str) -> Optional[float]:
        """특정 활동의 메트릭 값"""
        row = self.conn.execute("""
            SELECT numeric_value FROM metric_store
            WHERE scope_type='activity' AND scope_id=? AND metric_name=? AND is_primary=1
        """, [str(activity_id), metric_name]).fetchone()
        return row[0] if row else None
    
    # ── Stream 접근 ──
    
    def get_streams(self, activity_id: int = None) -> list[dict]:
        """활동의 스트림 데이터"""
        aid = activity_id or (int(self.scope_id) if self.scope_type == "activity" else None)
        if aid is None:
            return []
        
        rows = self.conn.execute("""
            SELECT elapsed_sec, distance_m, heart_rate, cadence, power_watts,
                   altitude_m, speed_ms, grade_pct, temperature_c
            FROM activity_streams
            WHERE activity_id = ?
            ORDER BY elapsed_sec
        """, [aid]).fetchall()
        
        cols = ["elapsed_sec", "distance_m", "heart_rate", "cadence", "power_watts",
                "altitude_m", "speed_ms", "grade_pct", "temperature_c"]
        return [dict(zip(cols, row)) for row in rows]
    
    # ── Wellness 접근 ──
    
    def get_wellness(self, date: str = None) -> dict:
        """특정 날짜의 daily_wellness"""
        d = date or self.scope_id
        row = self.conn.execute("SELECT * FROM daily_wellness WHERE date = ?", [d]).fetchone()
        if row:
            cols = [desc[0] for desc in self.conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
            return dict(zip(cols, row))
        return {}
```

---

## 4-2. Activity-Scope 1차 Calculator (소스 데이터 기반)

### TRIMP Calculator

```python
# src/metrics/trimp.py

import math
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class TRIMPCalculator(MetricCalculator):
    """Banister (1991) TRIMPexp 계산"""
    
    name = "trimp"
    provider = "runpulse:formula_v1"
    version = "banister_1991"
    scope_type = "activity"
    category = "rp_load"
    requires = []  # activity_summaries의 컬럼만 사용
    
    # 성별 계수 (config에서 가져올 수 있음)
    MALE_A = 1.92
    MALE_B = 0.64
    FEMALE_A = 1.67
    FEMALE_B = 1.92
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        
        avg_hr = act.get("avg_hr")
        duration_sec = act.get("duration_sec") or act.get("moving_time_sec")
        
        if not avg_hr or not duration_sec:
            return []
        
        # MaxHR & RestHR는 athlete 또는 daily wellness에서 가져옴
        max_hr = self._get_max_hr(ctx)
        rest_hr = self._get_rest_hr(ctx)
        
        if not max_hr or not rest_hr or max_hr <= rest_hr:
            return []
        
        duration_min = duration_sec / 60.0
        hr_reserve_frac = (avg_hr - rest_hr) / (max_hr - rest_hr)
        hr_reserve_frac = max(0.0, min(1.0, hr_reserve_frac))
        
        # 남성 기본 (추후 config에서 성별 구분)
        a, b = self.MALE_A, self.MALE_B
        
        trimp = duration_min * hr_reserve_frac * a * math.exp(b * hr_reserve_frac)
        
        # confidence: MaxHR, RestHR의 출처에 따라
        confidence = 1.0
        if not self._has_measured_max_hr(ctx):
            confidence -= 0.2  # 추정치 사용
        
        return [self._result(
            value=round(trimp, 1),
            confidence=confidence,
        )]
    
    def _get_max_hr(self, ctx: CalcContext) -> int | None:
        """MaxHR 가져오기: metric_store → activity 최대값 → 추정"""
        # 1. metric_store에 저장된 athlete max_hr
        stored = ctx.get_metric("max_hr_measured")
        if stored:
            return int(stored)
        
        # 2. 최근 활동들의 max_hr 중 최대값
        activities = ctx.get_activities_in_range(days=180)
        max_hrs = [a["max_hr"] for a in activities if a.get("max_hr")]
        if max_hrs:
            return max(max_hrs)
        
        # 3. 나이 기반 추정 (220 - age), fallback 190
        return 190
    
    def _get_rest_hr(self, ctx: CalcContext) -> int | None:
        """안정시 심박: daily_wellness → metric_store → fallback"""
        act = ctx.activity
        date = act.get("start_time", "")[:10]
        
        wellness = ctx.get_wellness(date)
        if wellness.get("resting_hr"):
            return wellness["resting_hr"]
        
        # 최근 7일 평균
        recent = ctx.get_daily_metric_series("resting_hr", days=7)
        if recent:
            return int(sum(v for _, v in recent) / len(recent))
        
        return 60  # fallback
    
    def _has_measured_max_hr(self, ctx: CalcContext) -> bool:
        return ctx.get_metric("max_hr_measured") is not None
```

### HRSS Calculator

```python
# src/metrics/hrss.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class HRSSCalculator(MetricCalculator):
    """HR Stress Score = TRIMP normalized to lactate threshold HR"""
    
    name = "hrss"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_load"
    requires = ["trimp"]
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        trimp = ctx.get_metric("trimp", provider="runpulse:formula_v1")
        if trimp is None:
            return []
        
        # LTHR 기반 정규화 (1시간 LTHR 운동 = 100점)
        lthr = ctx.get_metric("lactate_threshold_hr") or self._estimate_lthr(ctx)
        if not lthr:
            return []
        
        rest_hr = self._get_rest_hr(ctx)
        max_hr = self._get_max_hr(ctx)
        
        if not max_hr or max_hr <= rest_hr:
            return []
        
        # 1시간 LTHR의 TRIMP 계산
        import math
        hr_frac = (lthr - rest_hr) / (max_hr - rest_hr)
        trimp_lthr_1h = 60 * hr_frac * 1.92 * math.exp(0.64 * hr_frac)
        
        if trimp_lthr_1h == 0:
            return []
        
        hrss = (trimp / trimp_lthr_1h) * 100
        
        return [self._result(value=round(hrss, 1))]
    
    def _estimate_lthr(self, ctx):
        max_hr = self._get_max_hr(ctx)
        return int(max_hr * 0.85) if max_hr else None
    
    def _get_rest_hr(self, ctx):
        # TRIMP과 같은 로직 재사용
        return TRIMPCalculator()._get_rest_hr(ctx)
    
    def _get_max_hr(self, ctx):
        return TRIMPCalculator()._get_max_hr(ctx)
```

### Aerobic Decoupling Calculator

```python
# src/metrics/decoupling.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class AerobicDecouplingCalculator(MetricCalculator):
    """
    Aerobic Decoupling = (EF_first_half - EF_second_half) / EF_first_half × 100
    EF = pace / HR (또는 speed / HR)
    < 5% = good aerobic fitness
    """
    
    name = "aerobic_decoupling_rp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_efficiency"
    requires = []
    
    MINIMUM_DURATION_SEC = 1200  # 20분 이상만 계산
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        duration = act.get("moving_time_sec") or act.get("duration_sec")
        
        if not duration or duration < self.MINIMUM_DURATION_SEC:
            return []
        
        streams = ctx.get_streams()
        if not streams or len(streams) < 120:  # 최소 2분 데이터
            # 스트림 없으면 activity 평균으로는 계산 불가
            return []
        
        # 스트림을 전반/후반으로 분할
        mid = len(streams) // 2
        first_half = streams[:mid]
        second_half = streams[mid:]
        
        ef_first = self._calc_ef(first_half)
        ef_second = self._calc_ef(second_half)
        
        if ef_first is None or ef_second is None or ef_first == 0:
            return []
        
        decoupling = (ef_first - ef_second) / ef_first * 100
        
        return [self._result(value=round(decoupling, 2))]
    
    def _calc_ef(self, stream_segment: list[dict]) -> float | None:
        """세그먼트의 Efficiency Factor = avg_speed / avg_hr"""
        speeds = [s["speed_ms"] for s in stream_segment if s.get("speed_ms") and s["speed_ms"] > 0]
        hrs = [s["heart_rate"] for s in stream_segment if s.get("heart_rate") and s["heart_rate"] > 60]
        
        if not speeds or not hrs:
            return None
        
        avg_speed = sum(speeds) / len(speeds)
        avg_hr = sum(hrs) / len(hrs)
        
        if avg_hr == 0:
            return None
        
        return avg_speed / avg_hr
```

### GAP (Grade Adjusted Pace)

```python
# src/metrics/gap.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class GAPCalculator(MetricCalculator):
    """
    Grade Adjusted Pace: 경사를 보정한 페이스.
    Minetti (2002) 에너지 비용 모델 사용.
    """
    
    name = "gap_rp"
    provider = "runpulse:formula_v1"
    version = "minetti_2002"
    scope_type = "activity"
    category = "rp_performance"
    requires = []
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        streams = ctx.get_streams()
        if not streams or len(streams) < 60:
            return []
        
        total_adjusted_distance = 0.0
        total_time = 0.0
        
        for i in range(1, len(streams)):
            prev, curr = streams[i - 1], streams[i]
            
            dt = (curr.get("elapsed_sec") or 0) - (prev.get("elapsed_sec") or 0)
            if dt <= 0:
                continue
            
            speed = curr.get("speed_ms")
            grade = curr.get("grade_pct")
            
            if speed is None or speed <= 0:
                continue
            
            grade_frac = (grade or 0) / 100.0
            effort_factor = self._grade_effort_factor(grade_frac)
            
            distance_in_interval = speed * dt
            adjusted_distance = distance_in_interval / effort_factor
            
            total_adjusted_distance += adjusted_distance
            total_time += dt
        
        if total_time == 0 or total_adjusted_distance == 0:
            return []
        
        gap_speed_ms = total_adjusted_distance / total_time
        gap_pace_sec_km = 1000.0 / gap_speed_ms if gap_speed_ms > 0 else None
        
        if gap_pace_sec_km is None:
            return []
        
        return [self._result(value=round(gap_pace_sec_km, 1))]
    
    @staticmethod
    def _grade_effort_factor(grade: float) -> float:
        """
        Minetti (2002): 경사에 따른 에너지 비용 비율.
        grade: 소수 (0.05 = 5%)
        반환: 평지 대비 노력 비율 (> 1 = 오르막, < 1 = 내리막)
        """
        # 5차 다항식 근사
        cost = (155.4 * grade**5 
                - 30.4 * grade**4 
                - 43.3 * grade**3 
                + 46.3 * grade**2 
                + 19.5 * grade 
                + 3.6)
        flat_cost = 3.6  # 평지 비용
        
        if cost <= 0:
            cost = 0.5  # 안전 하한
        
        return cost / flat_cost
```

### Workout Classifier

```python
# src/metrics/classifier.py

import json
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class WorkoutClassifier(MetricCalculator):
    """
    규칙 기반 운동 유형 분류.
    easy | tempo | threshold | interval | long_run | recovery | race | unknown
    """
    
    name = "workout_type"
    provider = "runpulse:rule_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_classification"
    requires = []
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        
        if act.get("activity_type") not in ("running", "trail_running", "treadmill"):
            return []
        
        distance_m = act.get("distance_m") or 0
        duration_sec = act.get("moving_time_sec") or act.get("duration_sec") or 0
        avg_hr = act.get("avg_hr")
        max_hr_athlete = self._get_max_hr(ctx)
        avg_pace = act.get("avg_pace_sec_km")
        
        # HR zone 비율
        hr_zone_pcts = self._get_hr_zone_pcts(ctx)
        
        classification = self._classify(
            distance_m, duration_sec, avg_hr, max_hr_athlete, 
            avg_pace, hr_zone_pcts, act
        )
        
        return [self._result(
            json_val={
                "type": classification["type"],
                "confidence": classification["confidence"],
                "reasons": classification["reasons"],
            },
            text=classification["type"],
            confidence=classification["confidence"],
        )]
    
    def _classify(self, distance_m, duration_sec, avg_hr, max_hr,
                  avg_pace, hr_zones, act) -> dict:
        
        reasons = []
        scores = {
            "easy": 0, "recovery": 0, "long_run": 0,
            "tempo": 0, "threshold": 0, "interval": 0, "race": 0,
        }
        
        distance_km = distance_m / 1000 if distance_m else 0
        duration_min = duration_sec / 60 if duration_sec else 0
        
        # ── 거리 기반 ──
        if distance_km >= 18:
            scores["long_run"] += 3
            reasons.append(f"distance {distance_km:.1f}km ≥ 18km")
        elif distance_km >= 14:
            scores["long_run"] += 2
        
        if distance_km < 6 and duration_min < 40:
            scores["recovery"] += 2
            scores["easy"] += 1
        
        # ── HR 기반 ──
        if avg_hr and max_hr and max_hr > 0:
            hr_pct = avg_hr / max_hr * 100
            
            if hr_pct < 70:
                scores["easy"] += 2
                scores["recovery"] += 2
                reasons.append(f"avg HR {hr_pct:.0f}% < 70%")
            elif hr_pct < 80:
                scores["easy"] += 1
                scores["tempo"] += 1
            elif hr_pct < 88:
                scores["tempo"] += 2
                scores["threshold"] += 1
                reasons.append(f"avg HR {hr_pct:.0f}% → tempo zone")
            elif hr_pct < 95:
                scores["threshold"] += 2
                scores["interval"] += 1
                reasons.append(f"avg HR {hr_pct:.0f}% → threshold zone")
            else:
                scores["race"] += 2
                scores["interval"] += 1
        
        # ── HR Zone 분포 기반 ──
        if hr_zones:
            z1_z2_pct = (hr_zones.get("z1", 0) + hr_zones.get("z2", 0))
            z4_z5_pct = (hr_zones.get("z4", 0) + hr_zones.get("z5", 0))
            
            if z1_z2_pct > 80:
                scores["easy"] += 2
            if z4_z5_pct > 30:
                scores["interval"] += 2
                reasons.append(f"Z4+Z5 = {z4_z5_pct:.0f}%")
            if z4_z5_pct > 15 and z1_z2_pct > 40:
                scores["interval"] += 1  # 인터벌 패턴 (고/저 반복)
        
        # ── Event type 참조 ──
        if act.get("event_type") in ("race", "race_running"):
            scores["race"] += 5
            reasons.append("event_type=race")
        
        # 최고 점수 선택
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        total = sum(scores.values()) or 1
        confidence = min(best_score / total, 1.0)
        
        if best_score == 0:
            best_type = "unknown"
            confidence = 0.0
        
        return {"type": best_type, "confidence": round(confidence, 2), "reasons": reasons}
    
    def _get_max_hr(self, ctx):
        return TRIMPCalculator()._get_max_hr(ctx)
    
    def _get_hr_zone_pcts(self, ctx) -> dict:
        """HR zone 시간을 비율(%)로 변환"""
        total = 0
        zones = {}
        for i in range(1, 6):
            val = ctx.get_metric(f"hr_zone_{i}_sec")
            val = val or 0
            zones[f"z{i}"] = val
            total += val
        
        if total == 0:
            return {}
        
        return {k: v / total * 100 for k, v in zones.items()}
```

### VDOT Calculator

```python
# src/metrics/vdot.py

import math
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class VDOTCalculator(MetricCalculator):
    """
    Jack Daniels VDOT 계산.
    distance(m)와 time(sec)에서 VO2 추정.
    """
    
    name = "runpulse_vdot"
    provider = "runpulse:formula_v1"
    version = "daniels_2005"
    scope_type = "activity"
    category = "rp_performance"
    requires = []
    
    MINIMUM_DISTANCE_M = 1500
    MINIMUM_DURATION_SEC = 300   # 5분
    MAXIMUM_DURATION_SEC = 14400 # 4시간
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        
        if act.get("activity_type") not in ("running", "trail_running", "treadmill", "race"):
            return []
        
        distance_m = act.get("distance_m") or 0
        duration_sec = act.get("moving_time_sec") or act.get("duration_sec") or 0
        
        if (distance_m < self.MINIMUM_DISTANCE_M or 
            duration_sec < self.MINIMUM_DURATION_SEC or
            duration_sec > self.MAXIMUM_DURATION_SEC):
            return []
        
        velocity = distance_m / duration_sec  # m/s
        time_min = duration_sec / 60.0
        
        # VO2 from velocity (Daniels & Gilbert)
        # VO2 = -4.60 + 0.182258*v + 0.000104*v^2
        # v in m/min
        v_mpm = velocity * 60
        vo2 = -4.60 + 0.182258 * v_mpm + 0.000104 * v_mpm * v_mpm
        
        # % VO2max from time
        pct_max = 0.8 + 0.1894393 * math.exp(-0.012778 * time_min) \
                  + 0.2989558 * math.exp(-0.1932605 * time_min)
        
        if pct_max <= 0:
            return []
        
        vdot = vo2 / pct_max
        
        # confidence: 러닝만, 적절 거리, 적절 시간
        confidence = 0.9
        if act.get("activity_type") == "treadmill":
            confidence -= 0.1  # 트레드밀은 약간 불정확
        if distance_m < 3000:
            confidence -= 0.1  # 짧은 거리는 불정확
        
        return [self._result(
            value=round(vdot, 1),
            confidence=confidence,
        )]
```

### Efficiency Factor

```python
# src/metrics/efficiency.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class EfficiencyFactorCalculator(MetricCalculator):
    """
    Efficiency Factor = Normalized Speed / Avg HR
    높을수록 효율적 (같은 심박에서 더 빠름)
    """
    
    name = "efficiency_factor_rp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_efficiency"
    requires = []
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        
        avg_speed = act.get("avg_speed_ms")
        avg_hr = act.get("avg_hr")
        
        if not avg_speed or not avg_hr or avg_hr == 0:
            return []
        
        ef = avg_speed / avg_hr
        
        # 표준화: m/s per bpm → *1000 for readability
        ef_display = round(ef * 1000, 2)
        
        return [self._result(value=ef_display)]
```

---

## 4-3. Daily-Scope 1차 Calculator

### ATL / CTL / TSB (PMC)

```python
# src/metrics/pmc.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta


class PMCCalculator(MetricCalculator):
    """
    Performance Management Chart:
    ATL (7일 지수이동평균), CTL (42일 지수이동평균), TSB = CTL - ATL
    
    입력: 각 활동의 TRIMP (또는 HRSS)
    이 calculator는 특수: 한 번 호출로 하루치 ATL/CTL/TSB 세 개를 생성.
    """
    
    name = "ctl"  # 대표 이름
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["trimp"]
    produces = ["ctl", "atl", "tsb", "ramp_rate"]
    
    ATL_DAYS = 7
    CTL_DAYS = 42
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id  # YYYY-MM-DD
        
        # 최근 42일간의 일별 TRIMP 합산
        daily_loads = self._get_daily_loads(ctx, days=self.CTL_DAYS + 7)
        
        if not daily_loads:
            return []
        
        # 지수이동평균 계산
        atl_decay = 2.0 / (self.ATL_DAYS + 1)
        ctl_decay = 2.0 / (self.CTL_DAYS + 1)
        
        atl = 0.0
        ctl = 0.0
        prev_ctl = None
        
        # 날짜순으로 누적
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start = target_date - timedelta(days=self.CTL_DAYS + 7)
        
        current = start
        while current <= target_date:
            ds = current.strftime("%Y-%m-%d")
            load = daily_loads.get(ds, 0)
            
            atl = atl * (1 - atl_decay) + load * atl_decay
            prev_ctl = ctl
            ctl = ctl * (1 - ctl_decay) + load * ctl_decay
            
            current += timedelta(days=1)
        
        tsb = ctl - atl
        ramp_rate = ctl - prev_ctl if prev_ctl is not None else 0
        
        results = [
            self._result(value=round(ctl, 1), metric_name="ctl"),
            self._result(value=round(atl, 1), metric_name="atl"),
            self._result(value=round(tsb, 1), metric_name="tsb"),
            self._result(value=round(ramp_rate, 2), metric_name="ramp_rate"),
        ]
        
        return results
    
    def _get_daily_loads(self, ctx: CalcContext, days: int) -> dict:
        """날짜 → TRIMP 합계 dict"""
        target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        start = (target - timedelta(days=days)).strftime("%Y-%m-%d")
        end = ctx.scope_id
        
        # 활동별 TRIMP 조회
        rows = ctx.conn.execute("""
            SELECT substr(a.start_time, 1, 10) as date, m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity' 
            AND m.metric_name = 'trimp'
            AND m.is_primary = 1
            AND substr(a.start_time, 1, 10) BETWEEN ? AND ?
        """, [start, end]).fetchall()
        
        daily = {}
        for date, val in rows:
            daily[date] = daily.get(date, 0) + (val or 0)
        
        return daily
```

### ACWR (Acute:Chronic Workload Ratio)

```python
# src/metrics/acwr.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class ACWRCalculator(MetricCalculator):
    """
    ACWR = ATL / CTL (또는 7일 평균 / 28일 평균)
    최적 범위: 0.8~1.3
    """
    
    name = "acwr"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["ctl", "atl"]
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        
        if atl is None or ctl is None or ctl == 0:
            return []
        
        acwr = atl / ctl
        
        return [self._result(value=round(acwr, 2))]
```

### LSI (Load Spike Index)

```python
# src/metrics/lsi.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta


class LSICalculator(MetricCalculator):
    """
    Load Spike Index = 당일 부하 / 21일 롤링 평균
    > 1.5면 급격한 부하 증가
    """
    
    name = "lsi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["trimp"]
    
    ROLLING_DAYS = 21
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id
        
        # 당일 TRIMP 합계
        today_load = self._get_day_load(ctx, date_str)
        if today_load == 0:
            return []
        
        # 21일 롤링 평균
        target = datetime.strptime(date_str, "%Y-%m-%d")
        daily_loads = []
        for i in range(1, self.ROLLING_DAYS + 1):
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_loads.append(self._get_day_load(ctx, d))
        
        avg_load = sum(daily_loads) / len(daily_loads) if daily_loads else 0
        
        if avg_load == 0:
            return []
        
        lsi = today_load / avg_load
        
        return [self._result(value=round(lsi, 2))]
    
    def _get_day_load(self, ctx, date_str) -> float:
        """특정 날짜의 TRIMP 합계"""
        rows = ctx.conn.execute("""
            SELECT m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity'
            AND m.metric_name = 'trimp' AND m.is_primary = 1
            AND substr(a.start_time, 1, 10) = ?
        """, [date_str]).fetchall()
        return sum(r[0] or 0 for r in rows)
```

### Monotony & Strain

```python
# src/metrics/monotony.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta
import math


class MonotonyStrainCalculator(MetricCalculator):
    """
    Monotony = 7일 TRIMP 평균 / 7일 TRIMP 표준편차
    Strain = 7일 TRIMP 합계 × Monotony
    Monotony > 2.0 → 과훈련 위험
    """
    
    name = "monotony"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["trimp"]
    produces = ["monotony", "training_strain"]
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id
        target = datetime.strptime(date_str, "%Y-%m-%d")
        
        loads = []
        for i in range(7):
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            loads.append(self._get_day_load(ctx, d))
        
        if not loads or all(l == 0 for l in loads):
            return []
        
        mean = sum(loads) / len(loads)
        variance = sum((x - mean) ** 2 for x in loads) / len(loads)
        std = math.sqrt(variance)
        
        if std == 0:
            monotony = float('inf')
        else:
            monotony = mean / std
        
        strain = sum(loads) * monotony
        
        results = [
            self._result(value=round(monotony, 2), metric_name="monotony"),
        ]
        
        if not math.isinf(strain):
            results.append(
                self._result(value=round(strain, 1), metric_name="training_strain")
            )
        
        return results
    
    def _get_day_load(self, ctx, date_str):
        return LSICalculator()._get_day_load(ctx, date_str)
```

---

## 4-4. Daily-Scope 2차 Calculator (RunPulse 고유)

### UTRS (Unified Training Readiness Score)

```python
# src/metrics/utrs.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class UTRSCalculator(MetricCalculator):
    """
    Unified Training Readiness Score (0~100).
    
    PDF 버전 가중치:
    body_battery × 0.30 + TSB × 0.25 + sleep × 0.20 + HRV × 0.15 + stress × 0.10
    """
    
    name = "utrs"
    provider = "runpulse:formula_v1"
    version = "pdf_weights_v1"
    scope_type = "daily"
    category = "rp_readiness"
    requires = ["tsb"]
    
    WEIGHTS = {
        "body_battery": 0.30,
        "tsb": 0.25,
        "sleep": 0.20,
        "hrv": 0.15,
        "stress": 0.10,
    }
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        wellness = ctx.get_wellness()
        
        components = {}
        available_count = 0
        total_weight = 0.0
        
        # ── Body Battery (0~100) ──
        bb_high = wellness.get("body_battery_high")
        if bb_high is not None:
            components["body_battery"] = self._normalize(bb_high, 0, 100)
            available_count += 1
            total_weight += self.WEIGHTS["body_battery"]
        
        # ── TSB (일반적으로 -30 ~ +30) ──
        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        if tsb is None:
            # fallback: 소스 TSB
            tsb = ctx.get_metric("tsb")
        if tsb is not None:
            # TSB를 0~100으로 정규화: -30→0, 0→50, +30→100
            components["tsb"] = self._normalize(tsb + 30, 0, 60)
            available_count += 1
            total_weight += self.WEIGHTS["tsb"]
        
        # ── Sleep Score (0~100) ──
        sleep = wellness.get("sleep_score")
        if sleep is not None:
            components["sleep"] = self._normalize(sleep, 0, 100)
            available_count += 1
            total_weight += self.WEIGHTS["sleep"]
        
        # ── HRV (last_night / weekly_avg 비율) ──
        hrv_last = wellness.get("hrv_last_night")
        hrv_avg = wellness.get("hrv_weekly_avg")
        if hrv_last is not None and hrv_avg is not None and hrv_avg > 0:
            hrv_ratio = hrv_last / hrv_avg
            # 0.7~1.3 → 0~100
            components["hrv"] = self._normalize(hrv_ratio, 0.7, 1.3)
            available_count += 1
            total_weight += self.WEIGHTS["hrv"]
        
        # ── Stress (0~100, 낮을수록 좋음) ──
        stress = wellness.get("avg_stress")
        if stress is not None:
            # 역전: stress 0→100점, stress 100→0점
            components["stress"] = self._normalize(100 - stress, 0, 100)
            available_count += 1
            total_weight += self.WEIGHTS["stress"]
        
        if available_count == 0:
            return []
        
        # 가중 합산 (사용 가능한 가중치로 재정규화)
        utrs = 0.0
        for key, norm_value in components.items():
            weight = self.WEIGHTS[key]
            utrs += norm_value * (weight / total_weight)
        
        utrs_score = round(utrs * 100, 1)
        confidence = available_count / 5.0  # 5개 중 몇 개 있는지
        
        return [self._result(
            value=utrs_score,
            confidence=round(confidence, 2),
            json_val={
                "components": {k: round(v * 100, 1) for k, v in components.items()},
                "available": available_count,
                "total_inputs": 5,
            },
        )]
    
    @staticmethod
    def _normalize(value, min_val, max_val) -> float:
        """값을 0.0~1.0으로 정규화"""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
```

### CIRS (Composite Injury Risk Score)

```python
# src/metrics/cirs.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta


class CIRSCalculator(MetricCalculator):
    """
    Composite Injury Risk Score (0~100).
    
    ACWR × 0.4 + LSI × 0.3 + Consecutive × 0.2 + Fatigue × 0.1
    """
    
    name = "cirs"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_risk"
    requires = ["acwr", "lsi"]
    
    WEIGHTS = {
        "acwr_risk": 0.4,
        "lsi_risk": 0.3,
        "consecutive_risk": 0.2,
        "fatigue_risk": 0.1,
    }
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        components = {}
        available = 0
        total_weight = 0.0
        
        # ── ACWR 위험도 ──
        acwr = ctx.get_metric("acwr", provider="runpulse:formula_v1")
        if acwr is not None:
            if acwr < 0.8:
                acwr_risk = 0.3  # 낮은 ACWR도 위험 (detraining)
            elif acwr <= 1.3:
                acwr_risk = 0.0  # 최적 구간
            elif acwr <= 1.5:
                acwr_risk = (acwr - 1.3) / 0.2  # 1.3→0, 1.5→1
            else:
                acwr_risk = 1.0  # 매우 위험
            
            components["acwr_risk"] = acwr_risk
            available += 1
            total_weight += self.WEIGHTS["acwr_risk"]
        
        # ── LSI 위험도 ──
        lsi = ctx.get_metric("lsi", provider="runpulse:formula_v1")
        if lsi is not None:
            if lsi <= 1.0:
                lsi_risk = 0.0
            elif lsi <= 1.5:
                lsi_risk = (lsi - 1.0) / 0.5
            else:
                lsi_risk = 1.0
            
            components["lsi_risk"] = lsi_risk
            available += 1
            total_weight += self.WEIGHTS["lsi_risk"]
        
        # ── 연속 훈련일 위험도 ──
        consecutive = self._count_consecutive_days(ctx)
        if consecutive is not None:
            if consecutive <= 3:
                consec_risk = 0.0
            elif consecutive <= 5:
                consec_risk = (consecutive - 3) / 2
            else:
                consec_risk = 1.0
            
            components["consecutive_risk"] = consec_risk
            available += 1
            total_weight += self.WEIGHTS["consecutive_risk"]
        
        # ── Fatigue 위험도 (CTL - TSB가 클수록 피로) ──
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        if ctl is not None and tsb is not None:
            fatigue = ctl - tsb
            fatigue_risk = min(fatigue / 100, 1.0)
            fatigue_risk = max(0.0, fatigue_risk)
            
            components["fatigue_risk"] = fatigue_risk
            available += 1
            total_weight += self.WEIGHTS["fatigue_risk"]
        
        if available == 0:
            return []
        
        # 가중 합산
        cirs = 0.0
        for key, risk in components.items():
            weight = self.WEIGHTS[key]
            cirs += risk * (weight / total_weight)
        
        cirs_score = round(cirs * 100, 1)
        confidence = available / 4.0
        
        return [self._result(
            value=cirs_score,
            confidence=round(confidence, 2),
            json_val={
                "components": {k: round(v * 100, 1) for k, v in components.items()},
            },
        )]
    
    def _count_consecutive_days(self, ctx) -> int | None:
        """현재 날짜 기준 연속 훈련일 수"""
        date = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        count = 0
        
        for i in range(14):  # 최대 14일 역추적
            d = (date - timedelta(days=i)).strftime("%Y-%m-%d")
            has_activity = ctx.conn.execute("""
                SELECT 1 FROM v_canonical_activities
                WHERE substr(start_time, 1, 10) = ?
            """, [d]).fetchone()
            
            if has_activity:
                count += 1
            else:
                break
        
        return count
```

### FEARP (Field-Equivalent Adjusted Running Pace)

```python
# src/metrics/fearp.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class FEARPCalculator(MetricCalculator):
    """
    Field-Equivalent Adjusted Running Pace.
    실제 페이스를 온도, 습도, 고도, 경사 보정하여 "표준 환경 페이스"로 변환.
    """
    
    name = "fearp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_performance"
    requires = []
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        
        avg_pace = act.get("avg_pace_sec_km")
        if not avg_pace or avg_pace <= 0:
            return []
        
        # 보정 팩터 수집
        temp_factor = self._temperature_factor(ctx)
        humidity_factor = self._humidity_factor(ctx)
        altitude_factor = self._altitude_factor(ctx)
        grade_factor = self._grade_factor(ctx)
        
        total_factor = temp_factor * humidity_factor * altitude_factor * grade_factor
        
        if total_factor <= 0:
            return []
        
        fearp = avg_pace / total_factor
        
        # confidence: 보정 데이터 가용성
        available_factors = sum(1 for f in [temp_factor, humidity_factor, altitude_factor]
                                if f != 1.0)
        confidence = 0.5 + 0.15 * available_factors  # base 0.5 + 각 팩터당 0.15
        
        return [self._result(
            value=round(fearp, 1),
            confidence=round(min(confidence, 1.0), 2),
            json_val={
                "actual_pace": avg_pace,
                "temp_factor": round(temp_factor, 4),
                "humidity_factor": round(humidity_factor, 4),
                "altitude_factor": round(altitude_factor, 4),
                "grade_factor": round(grade_factor, 4),
                "total_factor": round(total_factor, 4),
            },
        )]
    
    def _temperature_factor(self, ctx) -> float:
        """온도 보정. 15°C = 1.0 (최적). 고온일수록 < 1.0 (더 느려지는 게 정상)."""
        temp = ctx.activity.get("avg_temperature")
        if temp is None:
            # metric_store에서 날씨 데이터 시도
            temp = ctx.get_metric("weather_temp_c")
        if temp is None:
            return 1.0
        
        # Cheuvront (2005) 모델 근사
        if temp <= 10:
            return 1.02
        elif temp <= 15:
            return 1.0
        elif temp <= 20:
            return 0.98
        elif temp <= 25:
            return 0.95
        elif temp <= 30:
            return 0.90
        elif temp <= 35:
            return 0.84
        else:
            return 0.78
    
    def _humidity_factor(self, ctx) -> float:
        humidity = ctx.get_metric("weather_humidity_pct")
        if humidity is None:
            return 1.0
        
        # 고습도에서만 영향 (70% 이상)
        if humidity < 70:
            return 1.0
        return 1.0 - (humidity - 70) * 0.002  # 70%→1.0, 100%→0.94
    
    def _altitude_factor(self, ctx) -> float:
        """고도 보정. 해수면 = 1.0."""
        alt = ctx.activity.get("elevation_gain")  # 대략적 고도
        # 정확한 고도는 스트림의 평균 altitude
        streams = ctx.get_streams()
        if streams:
            alts = [s["altitude_m"] for s in streams if s.get("altitude_m") is not None]
            if alts:
                avg_alt = sum(alts) / len(alts)
                if avg_alt > 1000:
                    return 1.0 - (avg_alt - 1000) * 0.00003
                return 1.0
        return 1.0
    
    def _grade_factor(self, ctx) -> float:
        """경사 보정. GAP이 있으면 GAP/실제페이스 비율 사용."""
        gap = ctx.get_metric("gap_rp", provider="runpulse:formula_v1")
        actual_pace = ctx.activity.get("avg_pace_sec_km")
        
        if gap and actual_pace and actual_pace > 0:
            return actual_pace / gap
        
        return 1.0
```

### DI (Durability Index)

```python
# src/metrics/di.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta


class DurabilityIndexCalculator(MetricCalculator):
    """
    Durability Index: 장시간 세션에서의 페이스 유지 능력.
    DI = 100 - clamp(pace_drop_pct × 5, 0, 100)
    
    최근 8주 내 90분+ 세션 3개 미만이면 None.
    """
    
    name = "di"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"  # 일별 지표 (여러 세션의 종합)
    category = "rp_efficiency"
    requires = []
    
    MIN_SESSION_DURATION_SEC = 5400  # 90분
    MIN_SESSIONS = 3
    LOOKBACK_DAYS = 56  # 8주
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        activities = ctx.get_activities_in_range(
            days=self.LOOKBACK_DAYS, activity_type="running"
        )
        
        long_sessions = [
            a for a in activities
            if (a.get("moving_time_sec") or a.get("duration_sec") or 0) >= self.MIN_SESSION_DURATION_SEC
        ]
        
        if len(long_sessions) < self.MIN_SESSIONS:
            return []
        
        pace_drops = []
        for a in long_sessions:
            drop = self._calc_pace_drop(ctx, a["id"])
            if drop is not None:
                pace_drops.append(drop)
        
        if not pace_drops:
            return []
        
        avg_drop = sum(pace_drops) / len(pace_drops)
        di = 100 - max(0, min(100, avg_drop * 5))
        
        confidence = min(len(pace_drops) / 5, 1.0)  # 5개 이상이면 confidence=1.0
        
        return [self._result(
            value=round(di, 1),
            confidence=round(confidence, 2),
            json_val={
                "sessions_used": len(pace_drops),
                "avg_pace_drop_pct": round(avg_drop, 2),
            },
        )]
    
    def _calc_pace_drop(self, ctx, activity_id: int) -> float | None:
        """전반/후반 페이스 비교로 pace drop % 계산"""
        streams = ctx.get_streams(activity_id)
        if not streams or len(streams) < 120:
            return None
        
        mid = len(streams) // 2
        first_half = streams[:mid]
        second_half = streams[mid:]
        
        avg_pace_first = self._avg_pace(first_half)
        avg_pace_second = self._avg_pace(second_half)
        
        if avg_pace_first is None or avg_pace_second is None or avg_pace_first == 0:
            return None
        
        # pace가 sec/km이면 값이 커질수록 느린 것
        pace_drop_pct = (avg_pace_second - avg_pace_first) / avg_pace_first * 100
        return max(0, pace_drop_pct)  # 음수(후반이 더 빠른 경우)는 0으로
    
    def _avg_pace(self, stream_segment) -> float | None:
        speeds = [s["speed_ms"] for s in stream_segment 
                  if s.get("speed_ms") and s["speed_ms"] > 0.5]
        if not speeds:
            return None
        avg_speed = sum(speeds) / len(speeds)
        return 1000.0 / avg_speed  # sec/km
```

### DARP (Dynamic Adjusted Race Predictor)

```python
# src/metrics/darp.py

import math
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class DARPCalculator(MetricCalculator):
    """
    Dynamic Adjusted Race Predictor.
    Riegel 공식 기반 + VDOT + DI 보정.
    5K, 10K, 하프, 풀 예측.
    """
    
    name = "darp_5k"  # 대표 이름
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["runpulse_vdot", "di"]
    produces = ["darp_5k", "darp_10k", "darp_half", "darp_full"]
    
    DISTANCES = {
        "5k": 5000,
        "10k": 10000,
        "half": 21097.5,
        "full": 42195,
    }
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # 최근 활동에서 가장 높은 VDOT 찾기
        vdot = self._get_best_recent_vdot(ctx)
        if vdot is None:
            return []
        
        di = ctx.get_metric("di", provider="runpulse:formula_v1")
        
        results = []
        for label, dist in self.DISTANCES.items():
            pred_sec = self._predict(vdot, dist, di)
            if pred_sec:
                results.append(self._result(
                    value=round(pred_sec, 0),
                    metric_name=f"darp_{label}",
                ))
        
        return results
    
    def _predict(self, vdot: float, distance_m: float, di: float = None) -> float | None:
        """VDOT에서 목표 거리의 예상 시간 역산"""
        # Daniels: velocity = f(VO2max, %VO2max at distance)
        # 간소화: Riegel T2 = T1 × (D2/D1)^1.06
        
        # VDOT에서 기준 레이스 속도 역산 (10km 기준)
        # VO2 at 10km pace = VDOT × %VO2max_at_10km
        # 대략적 %VO2max for 10km ≈ 93%
        vo2_at_10k = vdot * 0.93
        
        # VO2 → velocity: v(m/min) = (VO2 + 4.60) / (0.182258 + 0.000104*v)
        # 이차방정식 풀기
        v_mpm = self._vo2_to_velocity(vo2_at_10k)
        if v_mpm is None or v_mpm <= 0:
            return None
        
        t_10k = 10000.0 / v_mpm  # 분
        
        # Riegel 공식으로 목표 거리 예측
        t_target = t_10k * (distance_m / 10000.0) ** 1.06
        
        # DI 보정 (하프, 풀에만 적용)
        if di is not None and distance_m >= 21000:
            di_penalty = 1.0 + (100 - di) * 0.002  # DI 80 → +4% 페널티
            t_target *= di_penalty
        
        return t_target * 60  # 초
    
    @staticmethod
    def _vo2_to_velocity(vo2: float) -> float | None:
        """VO2 (ml/kg/min) → velocity (m/min). 이차방정식 풀기."""
        # 0.000104*v^2 + 0.182258*v + (-4.60 - vo2) = 0
        a = 0.000104
        b = 0.182258
        c = -4.60 - vo2
        
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        
        return (-b + math.sqrt(disc)) / (2 * a)
    
    def _get_best_recent_vdot(self, ctx) -> float | None:
        """최근 90일 활동 중 최고 VDOT"""
        rows = ctx.conn.execute("""
            SELECT m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity'
            AND m.metric_name = 'runpulse_vdot'
            AND m.provider = 'runpulse:formula_v1'
            AND a.start_time >= datetime('now', '-90 days')
            ORDER BY m.numeric_value DESC
            LIMIT 1
        """).fetchone()
        
        return rows[0] if rows else None
```

### TIDS (Training Intensity Distribution Score)

```python
# src/metrics/tids.py

import json
from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta


class TIDSCalculator(MetricCalculator):
    """
    Training Intensity Distribution Score.
    최근 4주간 HR zone 분포를 분석하여 80/20, Polarized, Pyramid 모델과 비교.
    """
    
    name = "tids"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "weekly"
    category = "rp_distribution"
    requires = ["hr_zone_1_sec", "hr_zone_2_sec", "hr_zone_3_sec", "hr_zone_4_sec", "hr_zone_5_sec"]
    
    MODELS = {
        "polarized_80_20": {"z1_z2": 80, "z3": 5, "z4_z5": 15},
        "pyramid": {"z1_z2": 75, "z3": 15, "z4_z5": 10},
        "threshold": {"z1_z2": 60, "z3": 25, "z4_z5": 15},
    }
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # scope_id = "2026-W14" 같은 ISO week
        # 해당 주의 모든 활동에서 HR zone 시간 합산
        
        zone_totals = self._aggregate_week_zones(ctx)
        if not zone_totals:
            return []
        
        total = sum(zone_totals.values())
        if total == 0:
            return []
        
        # 비율 계산
        pcts = {k: v / total * 100 for k, v in zone_totals.items()}
        z1_z2 = pcts.get("z1", 0) + pcts.get("z2", 0)
        z3 = pcts.get("z3", 0)
        z4_z5 = pcts.get("z4", 0) + pcts.get("z5", 0)
        
        actual = {"z1_z2": z1_z2, "z3": z3, "z4_z5": z4_z5}
        
        # 각 모델과의 편차
        deviations = {}
        for model_name, targets in self.MODELS.items():
            dev = sum(abs(actual[k] - targets[k]) for k in targets)
            deviations[model_name] = round(dev, 1)
        
        best_model = min(deviations, key=deviations.get)
        
        return [self._result(
            json_val={
                "zone_pcts": {k: round(v, 1) for k, v in pcts.items()},
                "summary": {"z1_z2": round(z1_z2, 1), "z3": round(z3, 1), "z4_z5": round(z4_z5, 1)},
                "deviations": deviations,
                "best_fit_model": best_model,
                "is_80_20": z1_z2 >= 78,
            },
        )]
    
    def _aggregate_week_zones(self, ctx) -> dict:
        """해당 주의 모든 활동에서 HR zone 시간 합산"""
        week_str = ctx.scope_id  # "2026-W14"
        
        # ISO week → 날짜 범위
        year = int(week_str.split("-W")[0])
        week = int(week_str.split("-W")[1])
        
        from datetime import date
        jan4 = date(year, 1, 4)
        start_of_week = jan4 + timedelta(weeks=week - 1, days=-jan4.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # 해당 주의 활동 ID 조회
        rows = ctx.conn.execute("""
            SELECT id FROM v_canonical_activities
            WHERE substr(start_time, 1, 10) BETWEEN ? AND ?
            AND activity_type IN ('running', 'trail_running', 'treadmill')
        """, [start_of_week.isoformat(), end_of_week.isoformat()]).fetchall()
        
        totals = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
        
        for (aid,) in rows:
            for i in range(1, 6):
                val = ctx.get_activity_metric(aid, f"hr_zone_{i}_sec")
                if val:
                    totals[f"z{i}"] += val
        
        return totals if any(v > 0 for v in totals.values()) else {}
```

### RMR (Runner Maturity Radar)

```python
# src/metrics/rmr.py

import json
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class RMRCalculator(MetricCalculator):
    """
    Runner Maturity Radar — 6축 레이더 차트.
    aerobic_capacity, threshold_intensity, endurance, 
    movement_efficiency, recovery, economy
    """
    
    name = "rmr"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_maturity"
    requires = ["runpulse_vdot", "di", "utrs"]
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        axes = {}
        
        # ── Aerobic Capacity: VDOT 기반 ──
        vdot = self._get_best_vdot(ctx)
        if vdot is not None:
            # VDOT 30~70 → 0~100
            axes["aerobic_capacity"] = self._norm(vdot, 30, 70)
        
        # ── Threshold Intensity: 최근 threshold 세션 페이스 / VDOT 예측 페이스 ──
        axes["threshold_intensity"] = self._calc_threshold_axis(ctx)
        
        # ── Endurance: DI ──
        di = ctx.get_metric("di", provider="runpulse:formula_v1")
        if di is not None:
            axes["endurance"] = round(di, 1)
        
        # ── Movement Efficiency: cadence + vertical ratio ──
        axes["movement_efficiency"] = self._calc_movement_axis(ctx)
        
        # ── Recovery: UTRS, body battery, sleep ──
        utrs = ctx.get_metric("utrs", provider="runpulse:formula_v1")
        if utrs is not None:
            axes["recovery"] = round(utrs, 1)
        
        # ── Economy: efficiency factor 추세 ──
        axes["economy"] = self._calc_economy_axis(ctx)
        
        # None 축 제거
        axes = {k: v for k, v in axes.items() if v is not None}
        
        if len(axes) < 3:  # 최소 3축은 있어야 레이더 의미 있음
            return []
        
        return [self._result(
            json_val={
                "axes": axes,
                "axes_count": len(axes),
                "total_possible": 6,
            },
        )]
    
    def _get_best_vdot(self, ctx) -> float | None:
        rows = ctx.conn.execute("""
            SELECT MAX(m.numeric_value)
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.metric_name = 'runpulse_vdot' AND m.provider = 'runpulse:formula_v1'
            AND a.start_time >= datetime('now', '-90 days')
        """).fetchone()
        return rows[0] if rows and rows[0] else None
    
    def _calc_threshold_axis(self, ctx) -> float | None:
        # 간소화: 최근 30일 tempo/threshold 분류 세션의 평균 EF
        return None  # TODO: 구현
    
    def _calc_movement_axis(self, ctx) -> float | None:
        # 최근 30일 활동의 평균 cadence와 vertical ratio
        acts = ctx.get_activities_in_range(30, "running")
        cadences = [a["avg_cadence"] for a in acts if a.get("avg_cadence")]
        vrs = [a["avg_vertical_ratio_pct"] for a in acts if a.get("avg_vertical_ratio_pct")]
        
        if not cadences:
            return None
        
        avg_cadence = sum(cadences) / len(cadences)
        # cadence 160~190 → 0~100
        cadence_score = self._norm(avg_cadence, 160, 190)
        
        if vrs:
            avg_vr = sum(vrs) / len(vrs)
            # VR 낮을수록 좋음: 10%→0, 6%→100
            vr_score = self._norm(10 - avg_vr, 0, 4)
            return round((cadence_score + vr_score) / 2, 1)
        
        return round(cadence_score, 1)
    
    def _calc_economy_axis(self, ctx) -> float | None:
        # 최근 30일 EF 추세
        return None  # TODO: Phase 5에서 구현
    
    @staticmethod
    def _norm(value, min_val, max_val) -> float:
        if max_val == min_val:
            return 50.0
        n = (value - min_val) / (max_val - min_val) * 100
        return round(max(0, min(100, n)), 1)
```

### ADTI (Aerobic Decoupling Trend Index)

```python
# src/metrics/adti.py

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from datetime import datetime, timedelta
import math


class ADTICalculator(MetricCalculator):
    """
    Aerobic Decoupling Trend Index.
    최근 N주간 주별 평균 decoupling의 선형 회귀 기울기.
    음수 = 개선 추세 (좋음), 양수 = 악화 추세
    """
    
    name = "adti"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "weekly"
    category = "rp_efficiency"
    requires = ["aerobic_decoupling_rp"]
    
    LOOKBACK_WEEKS = 8
    MIN_WEEKS_WITH_DATA = 4
    
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # 최근 8주간 주별 평균 decoupling 수집
        weekly_avgs = self._get_weekly_decouplings(ctx)
        
        if len(weekly_avgs) < self.MIN_WEEKS_WITH_DATA:
            return []
        
        # 선형 회귀
        xs = list(range(len(weekly_avgs)))
        ys = [v for _, v in weekly_avgs]
        
        slope = self._linear_regression_slope(xs, ys)
        
        if slope is None:
            return []
        
        return [self._result(
            value=round(slope, 4),
            json_val={
                "weeks": len(weekly_avgs),
                "weekly_values": [{"week": w, "avg_decoupling": round(v, 2)} for w, v in weekly_avgs],
                "interpretation": "improving" if slope < -0.1 else "stable" if abs(slope) <= 0.1 else "declining",
            },
        )]
    
    def _get_weekly_decouplings(self, ctx) -> list[tuple[str, float]]:
        """최근 N주간 주별 평균 decoupling"""
        rows = ctx.conn.execute("""
            SELECT 
                strftime('%Y-W%W', a.start_time) as week,
                AVG(m.numeric_value) as avg_dc
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.metric_name = 'aerobic_decoupling_rp'
            AND m.provider = 'runpulse:formula_v1'
            AND a.start_time >= datetime('now', ? || ' days')
            GROUP BY week
            ORDER BY week
        """, [str(-self.LOOKBACK_WEEKS * 7)]).fetchall()
        
        return [(r[0], r[1]) for r in rows if r[1] is not None]
    
    @staticmethod
    def _linear_regression_slope(xs, ys) -> float | None:
        n = len(xs)
        if n < 2:
            return None
        
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)
        
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return None
        
        return (n * sum_xy - sum_x * sum_y) / denom
```

---

## 4-5. Metrics Engine — Topological Execution

```python
# src/metrics/engine.py

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from src.metrics.base import MetricCalculator, CalcContext, CalcResult
from src.utils.db_helpers import upsert_metric
from src.utils.metric_priority import resolve_primaries_for_scope

log = logging.getLogger(__name__)

# ── Calculator 등록 ──

from src.metrics.trimp import TRIMPCalculator
from src.metrics.hrss import HRSSCalculator
from src.metrics.decoupling import AerobicDecouplingCalculator
from src.metrics.gap import GAPCalculator
from src.metrics.vdot import VDOTCalculator
from src.metrics.classifier import WorkoutClassifier
from src.metrics.efficiency import EfficiencyFactorCalculator
from src.metrics.pmc import PMCCalculator
from src.metrics.acwr import ACWRCalculator
from src.metrics.lsi import LSICalculator
from src.metrics.monotony import MonotonyStrainCalculator
from src.metrics.utrs import UTRSCalculator
from src.metrics.cirs import CIRSCalculator
from src.metrics.fearp import FEARPCalculator
from src.metrics.di import DurabilityIndexCalculator
from src.metrics.darp import DARPCalculator
from src.metrics.tids import TIDSCalculator
from src.metrics.rmr import RMRCalculator
from src.metrics.adti import ADTICalculator

ALL_CALCULATORS = [
    # ── Activity-scope: 1차 (소스 데이터만 필요) ──
    TRIMPCalculator(),
    HRSSCalculator(),
    AerobicDecouplingCalculator(),
    GAPCalculator(),
    VDOTCalculator(),
    WorkoutClassifier(),
    EfficiencyFactorCalculator(),
    FEARPCalculator(),
    
    # ── Daily-scope: 1차 (활동 메트릭 필요) ──
    PMCCalculator(),
    ACWRCalculator(),
    LSICalculator(),
    MonotonyStrainCalculator(),
    
    # ── Daily-scope: 2차 (1차 결과 필요) ──
    UTRSCalculator(),
    CIRSCalculator(),
    DurabilityIndexCalculator(),
    DARPCalculator(),
    RMRCalculator(),
    
    # ── Weekly-scope ──
    TIDSCalculator(),
    ADTICalculator(),
]


def recompute_recent(conn, days: int = 7):
    """최근 N일 데이터에 대해 전체 메트릭 재계산"""
    
    log.info(f"Recomputing metrics for last {days} days...")
    
    # Topological sort
    ordered = _topological_sort(ALL_CALCULATORS)
    
    # Scope별로 분류
    activity_calcs = [c for c in ordered if c.scope_type == "activity"]
    daily_calcs = [c for c in ordered if c.scope_type == "daily"]
    weekly_calcs = [c for c in ordered if c.scope_type == "weekly"]
    
    # ── Activity-scope 계산 ──
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    
    activities = conn.execute("""
        SELECT id FROM v_canonical_activities
        WHERE start_time >= ? AND start_time <= ?
        ORDER BY start_time
    """, [start.isoformat(), end.isoformat()]).fetchall()
    
    log.info(f"Processing {len(activities)} activities...")
    
    for (activity_id,) in activities:
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(activity_id))
        
        for calc in activity_calcs:
            try:
                results = calc.compute(ctx)
                _store_results(conn, calc, results, str(activity_id))
            except Exception as e:
                log.warning(f"Calculator {calc.name} failed for activity {activity_id}: {e}")
        
        resolve_primaries_for_scope(conn, "activity", str(activity_id))
    
    conn.commit()
    
    # ── Daily-scope 계산 ──
    dates = []
    current = start.date()
    while current <= end.date():
        dates.append(current.isoformat())
        current += timedelta(days=1)
    
    log.info(f"Processing {len(dates)} dates...")
    
    for date_str in dates:
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id=date_str)
        
        for calc in daily_calcs:
            try:
                results = calc.compute(ctx)
                _store_results(conn, calc, results, date_str)
            except Exception as e:
                log.warning(f"Calculator {calc.name} failed for {date_str}: {e}")
        
        resolve_primaries_for_scope(conn, "daily", date_str)
    
    conn.commit()
    
    # ── Weekly-scope 계산 ──
    weeks = _get_weeks_in_range(start.date(), end.date())
    
    log.info(f"Processing {len(weeks)} weeks...")
    
    for week_str in weeks:
        ctx = CalcContext(conn=conn, scope_type="weekly", scope_id=week_str)
        
        for calc in weekly_calcs:
            try:
                results = calc.compute(ctx)
                _store_results(conn, calc, results, week_str)
            except Exception as e:
                log.warning(f"Calculator {calc.name} failed for {week_str}: {e}")
        
        resolve_primaries_for_scope(conn, "weekly", week_str)
    
    conn.commit()
    
    log.info("Metric recomputation complete")


def recompute_all(conn):
    """전체 기간 재계산"""
    row = conn.execute("""
        SELECT MIN(substr(start_time, 1, 10)), MAX(substr(start_time, 1, 10))
        FROM activity_summaries
    """).fetchone()
    
    if not row or not row[0]:
        log.warning("No activities found")
        return
    
    start = datetime.strptime(row[0], "%Y-%m-%d")
    end = datetime.strptime(row[1], "%Y-%m-%d")
    days = (end - start).days + 1
    
    recompute_recent(conn, days=days)


def clear_runpulse_metrics(conn):
    """RunPulse가 계산한 모든 메트릭 삭제 (소스 데이터는 유지)"""
    deleted = conn.execute(
        "DELETE FROM metric_store WHERE provider LIKE 'runpulse%'"
    ).rowcount
    conn.commit()
    log.info(f"Cleared {deleted} RunPulse metrics")


def _store_results(conn, calc: MetricCalculator, results: list[CalcResult], scope_id: str):
    """계산 결과를 metric_store에 저장"""
    for r in results:
        if r.is_empty():
            continue
        
        r.scope_id = scope_id
        
        upsert_metric(conn, r.scope_type, r.scope_id, calc.provider, {
            "metric_name": r.metric_name,
            "category": r.category,
            "numeric_value": r.numeric_value,
            "text_value": r.text_value,
            "json_value": r.json_value,
            "algorithm_version": calc.version,
            "confidence": r.confidence,
            "parent_metric_id": r.parent_metric_id,
        })


def _topological_sort(calculators: list[MetricCalculator]) -> list[MetricCalculator]:
    """
    의존성 그래프 기반 정렬.
    requires에 명시된 메트릭을 produces하는 calculator가 먼저 실행되어야 함.
    """
    # produces 역매핑
    producer_map = {}
    for calc in calculators:
        for p in calc.produces:
            producer_map[p] = calc.name
    
    # 인접 리스트 빌드
    graph = defaultdict(set)  # calc.name → set of dependent calc.names
    in_degree = {c.name: 0 for c in calculators}
    name_to_calc = {c.name: c for c in calculators}
    
    for calc in calculators:
        for req in calc.requires:
            producer = producer_map.get(req)
            if producer and producer != calc.name:
                graph[producer].add(calc.name)
                in_degree[calc.name] = in_degree.get(calc.name, 0) + 1
    
    # Kahn's algorithm
    queue = [name for name, deg in in_degree.items() if deg == 0]
    ordered = []
    
    while queue:
        # 안정적 순서를 위해 정렬
        queue.sort()
        node = queue.pop(0)
        ordered.append(name_to_calc[node])
        
        for dependent in graph.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    if len(ordered) != len(calculators):
        # 순환 의존성 감지
        missing = set(c.name for c in calculators) - set(c.name for c in ordered)
        log.error(f"Circular dependency detected among: {missing}")
        # fallback: 원래 순서로
        for calc in calculators:
            if calc not in ordered:
                ordered.append(calc)
    
    return ordered


def _get_weeks_in_range(start_date, end_date) -> list[str]:
    """날짜 범위에 포함되는 ISO week 목록"""
    weeks = set()
    current = start_date
    while current <= end_date:
        iso = current.isocalendar()
        weeks.add(f"{iso[0]}-W{iso[1]:02d}")
        current += timedelta(days=1)
    return sorted(weeks)
```

---

## 4-6. 테스트 계획

```python
# tests/test_trimp.py
def test_trimp_basic_calculation():
    """알려진 입력값으로 TRIMP 계산 정확성 검증"""
    # duration=60min, avg_hr=155, max_hr=190, rest_hr=60
    # 기대 TRIMP ≈ 85~95 범위

def test_trimp_missing_hr():
    """avg_hr 없으면 빈 결과"""

def test_trimp_missing_duration():
    """duration 없으면 빈 결과"""


# tests/test_pmc.py
def test_ctl_increases_with_training():
    """매일 훈련하면 CTL이 증가"""

def test_tsb_negative_after_hard_training():
    """고강도 훈련 후 TSB < 0"""

def test_tsb_positive_after_rest():
    """휴식 후 TSB > 0"""


# tests/test_utrs.py
def test_utrs_full_inputs():
    """5개 입력 모두 있을 때 confidence=1.0"""

def test_utrs_partial_inputs():
    """3개만 있을 때 confidence=0.6, 가중치 재정규화"""

def test_utrs_no_inputs():
    """모든 입력 없으면 빈 결과"""


# tests/test_cirs.py
def test_cirs_high_acwr():
    """ACWR > 1.5 → CIRS 높음"""

def test_cirs_optimal_range():
    """ACWR 0.8~1.3 → CIRS 낮음"""


# tests/test_engine.py
def test_topological_sort():
    """TRIMP → PMC → ACWR → CIRS 순서 보장"""
    ordered = _topological_sort(ALL_CALCULATORS)
    names = [c.name for c in ordered]
    assert names.index("trimp") < names.index("ctl")
    assert names.index("ctl") < names.index("acwr")
    assert names.index("acwr") < names.index("cirs")

def test_circular_dependency_handling():
    """순환 의존성 시 에러 로그 + fallback"""

def test_recompute_recent():
    """전체 파이프라인 실행 후 metric_store에 결과 존재"""

def test_clear_runpulse_metrics():
    """소스 메트릭은 유지, runpulse 메트릭만 삭제"""
```

---

## 4-7. Phase 4 산출물 & 작업 순서

| 순서 | 파일 | 작업 | 예상 시간 |
|------|------|------|----------|
| 1 | `src/metrics/base.py` | MetricCalculator, CalcContext, CalcResult | 2시간 |
| 2 | `src/metrics/trimp.py` | TRIMP + MaxHR/RestHR 조회 로직 | 1.5시간 |
| 3 | `src/metrics/hrss.py` | HRSS | 30분 |
| 4 | `src/metrics/decoupling.py` | Aerobic Decoupling (stream 기반) | 1시간 |
| 5 | `src/metrics/gap.py` | Grade Adjusted Pace (Minetti) | 1시간 |
| 6 | `src/metrics/vdot.py` | VDOT (Daniels) | 1시간 |
| 7 | `src/metrics/classifier.py` | Workout Type Classifier | 1.5시간 |
| 8 | `src/metrics/efficiency.py` | Efficiency Factor | 30분 |
| 9 | `src/metrics/fearp.py` | FEARP (환경 보정) | 1.5시간 |
| 10 | `src/metrics/pmc.py` | ATL/CTL/TSB/Ramp Rate | 2시간 |
| 11 | `src/metrics/acwr.py` | ACWR | 30분 |
| 12 | `src/metrics/lsi.py` | Load Spike Index | 30분 |
| 13 | `src/metrics/monotony.py` | Monotony + Strain | 1시간 |
| 14 | `src/metrics/utrs.py` | UTRS | 1.5시간 |
| 15 | `src/metrics/cirs.py` | CIRS | 1.5시간 |
| 16 | `src/metrics/di.py` | Durability Index | 1시간 |
| 17 | `src/metrics/darp.py` | DARP (레이스 예측) | 1.5시간 |
| 18 | `src/metrics/tids.py` | TIDS (강도 분포) | 1시간 |
| 19 | `src/metrics/rmr.py` | RMR (성숙도 레이더) | 1.5시간 |
| 20 | `src/metrics/adti.py` | ADTI (디커플링 추세) | 1시간 |
| 21 | `src/metrics/engine.py` | Engine + topological sort + recompute | 2시간 |
| 22 | `tests/test_trimp.py` | TRIMP 단위 테스트 | 1시간 |
| 23 | `tests/test_pmc.py` | PMC 단위 테스트 | 1시간 |
| 24 | `tests/test_utrs.py` | UTRS 단위 테스트 | 1시간 |
| 25 | `tests/test_cirs.py` | CIRS 단위 테스트 | 30분 |
| 26 | `tests/test_engine.py` | Engine topological sort + 통합 | 1.5시간 |

**총 예상: ~30시간 (6~7 세션)**

---

## 4-8. Phase 4 완료 기준 (Definition of Done)

1. `ALL_CALCULATORS`에 19개 calculator 등록
2. `_topological_sort()`가 의존성 순서를 올바르게 해소 (TRIMP < PMC < ACWR < CIRS)
3. `recompute_recent(conn, days=7)` 실행 시 에러 없이 완료
4. `metric_store`에 `provider LIKE 'runpulse%'`인 행이 존재
5. 각 activity에 대해 최소 TRIMP, workout_type, efficiency_factor 3개 이상 RunPulse 메트릭 생성
6. 각 date에 대해 최소 CTL, ATL, TSB, UTRS 4개 이상 RunPulse 메트릭 생성
7. `clear_runpulse_metrics()` 후 `recompute_all()` 실행 시 동일 결과 재현
8. 소스 메트릭(`provider NOT LIKE 'runpulse%'`)은 `clear_runpulse_metrics()`에 영향 없음
9. `confidence` 필드가 UTRS, CIRS, FEARP 등 복합 메트릭에 설정됨
10. `json_value`가 TIDS, RMR, workout_type 등 구조화 메트릭에 설정됨
11. `pytest tests/test_trimp.py tests/test_pmc.py tests/test_utrs.py tests/test_cirs.py tests/test_engine.py` 전체 통과

---



좋은 지적입니다. Phase 4를 Phase 1~3과 같은 깊이로 재검토하겠습니다.

---

## Phase 4에서 누락되거나 보강해야 할 항목들

### 1. CalcContext의 성능 문제 — 쿼리 폭발

현재 설계에서 **가장 심각한 구조적 문제**입니다.

활동 500개 × calculator 8개 = 4,000번의 `compute()` 호출. 각 `compute()`에서 `ctx.activity`(SELECT 1회), `ctx.get_metric()`(SELECT N회), `ctx.get_streams()`(SELECT 1회, 수천 행) 등을 호출합니다. PMCCalculator는 `_get_daily_loads()`에서 42일치 JOIN 쿼리를 매일 실행합니다. DARP은 90일치 VDOT를 스캔합니다.

**보강 — Prefetch & Cache 전략**

```python
# CalcContext에 추가

@dataclass
class CalcContext:
    conn: object
    scope_type: str
    scope_id: str
    
    # ── Prefetched data (engine이 미리 채워줌) ──
    _prefetched_activities: dict = field(default=None, repr=False)
    _prefetched_metrics: dict = field(default=None, repr=False)
    _prefetched_wellness: dict = field(default=None, repr=False)
    
    # ── Per-scope cache ──
    _activity_cache: dict = field(default=None, repr=False)
    _metric_cache: dict = field(default=None, repr=False)
    _stream_cache: list = field(default=None, repr=False)
```

Engine이 scope별 계산을 시작하기 전에 **해당 scope에 필요한 데이터를 한 번에 로드**합니다:

```python
# engine.py에서

def _compute_activity_scope(conn, activity_id, calculators):
    """한 활동에 대해 모든 calculator 실행 (prefetch 포함)"""
    
    # 1. activity_summaries 한 번 로드
    activity_row = _load_activity(conn, activity_id)
    
    # 2. 이 활동의 모든 metric_store 행을 한 번에 로드
    metrics_map = _load_all_metrics_for_scope(conn, "activity", str(activity_id))
    
    # 3. streams는 필요한 calculator가 있을 때만 lazy-load (but 캐시)
    
    ctx = CalcContext(
        conn=conn,
        scope_type="activity",
        scope_id=str(activity_id),
        _activity_cache=activity_row,
        _metric_cache=metrics_map,
    )
    
    for calc in calculators:
        results = calc.compute(ctx)
        # 결과를 metric_cache에도 즉시 반영 (후속 calculator가 참조 가능)
        for r in results:
            if r.numeric_value is not None:
                ctx._metric_cache[(r.metric_name, calc.provider)] = r.numeric_value
        _store_results(conn, calc, results, str(activity_id))


def _load_all_metrics_for_scope(conn, scope_type, scope_id) -> dict:
    """한 scope의 모든 메트릭을 dict로 로드.
    key: (metric_name, provider) → numeric_value
    is_primary인 것은 (metric_name, None) → numeric_value로도 매핑
    """
    rows = conn.execute("""
        SELECT metric_name, provider, numeric_value, text_value, json_value, is_primary
        FROM metric_store
        WHERE scope_type = ? AND scope_id = ?
    """, [scope_type, scope_id]).fetchall()
    
    cache = {}
    for name, provider, num, text, json_val, is_primary in rows:
        cache[(name, provider)] = {"numeric": num, "text": text, "json": json_val}
        if is_primary:
            cache[(name, None)] = {"numeric": num, "text": text, "json": json_val}
    
    return cache
```

그러면 `ctx.get_metric()`이 DB 쿼리 대신 **dict 조회 O(1)**이 됩니다:

```python
def get_metric(self, metric_name: str, provider: str = None) -> Optional[float]:
    if self._metric_cache is not None:
        entry = self._metric_cache.get((metric_name, provider))
        if entry:
            return entry["numeric"]
        return None
    
    # fallback: DB 쿼리 (prefetch 안 된 경우)
    ...
```

Daily scope에서 PMCCalculator의 `_get_daily_loads()`처럼 **다른 scope의 데이터가 필요한 경우**는 여전히 DB 쿼리가 필요합니다. 하지만 이것은 **engine 레벨에서 daily 범위 전체를 한 번 prefetch**하여 해결합니다:

```python
def _compute_daily_scope(conn, dates, calculators):
    """모든 날짜에 대해 daily calculator 실행"""
    
    # 전체 기간의 daily TRIMP 합산을 한 번에 로드
    daily_loads = _prefetch_daily_loads(conn, dates[0], dates[-1])
    
    # 전체 기간의 wellness를 한 번에 로드
    wellness_map = _prefetch_wellness(conn, dates[0], dates[-1])
    
    for date_str in dates:
        ctx = CalcContext(
            conn=conn,
            scope_type="daily",
            scope_id=date_str,
            _prefetched_activities=daily_loads,
            _prefetched_wellness=wellness_map.get(date_str, {}),
        )
        
        for calc in calculators:
            results = calc.compute(ctx)
            _store_results(conn, calc, results, date_str)
```

이렇게 하면 **activity scope: scope당 SELECT 2회 (activity + metrics)**, **daily scope: 전체 기간에 대해 SELECT 3~5회 (loads, wellness, fitness)**로 줄어듭니다.

---

### 2. Stream 데이터 접근 최적화

Aerobic Decoupling, GAP, FEARP는 stream 데이터가 필요합니다. 한 활동의 stream이 ~3,000행이므로, 500개 활동 × 3,000행 = 150만 행을 읽는 것은 비효율적입니다.

**보강 — Stream 필요 여부 사전 판별**

```python
class MetricCalculator(ABC):
    # 기존 속성에 추가
    needs_streams: bool = False  # True이면 stream prefetch 대상
```

Engine이 `needs_streams=True`인 calculator가 있을 때만 stream을 로드합니다:

```python
def _compute_activity_scope(conn, activity_id, calculators):
    needs_streams = any(c.needs_streams for c in calculators)
    
    stream_cache = None
    if needs_streams:
        stream_cache = _load_streams(conn, activity_id)
    
    ctx = CalcContext(
        conn=conn,
        scope_type="activity",
        scope_id=str(activity_id),
        _activity_cache=activity_row,
        _metric_cache=metrics_map,
        _stream_cache=stream_cache,
    )
```

Calculator에서:

```python
class AerobicDecouplingCalculator(MetricCalculator):
    needs_streams = True

class GAPCalculator(MetricCalculator):
    needs_streams = True

class TRIMPCalculator(MetricCalculator):
    needs_streams = False  # activity summary만 사용
```

---

### 3. 에러 격리 & 부분 실패 처리

Phase 3에서는 sync 실패 시 `SyncResult`로 보고하는 체계가 있었습니다. Phase 4에도 동등한 체계가 필요합니다.

**보강 — `ComputeResult`**

```python
# src/metrics/engine.py

@dataclass
class ComputeResult:
    """메트릭 계산 전체 결과"""
    total_calculators: int = 0
    total_scopes: int = 0
    computed_count: int = 0        # 값을 생성한 (calculator, scope) 쌍
    skipped_count: int = 0         # 입력 부족으로 스킵
    error_count: int = 0
    errors: list = field(default_factory=list)  # [(calc_name, scope_id, error_msg)]
    
    elapsed_seconds: float = 0.0
    
    def summary(self) -> str:
        return (f"Computed: {self.computed_count}, Skipped: {self.skipped_count}, "
                f"Errors: {self.error_count}, Time: {self.elapsed_seconds:.1f}s")
```

Engine의 `recompute_recent()`가 이것을 반환합니다. 개별 calculator의 `compute()`가 예외를 던져도 다른 calculator에 영향을 주지 않습니다. 이것은 현재 설계에서 `try/except`로 되어 있지만, **어떤 에러가 얼마나 발생했는지 추적**하는 구조가 없었습니다.

```python
def recompute_recent(conn, days: int = 7) -> ComputeResult:
    result = ComputeResult()
    import time
    start_time = time.time()
    
    # ... 기존 로직 ...
    
    for calc in activity_calcs:
        result.total_calculators += 1
        try:
            outcomes = calc.compute(ctx)
            if outcomes:
                result.computed_count += 1
                _store_results(conn, calc, outcomes, str(activity_id))
                # 후속 calculator용 캐시 업데이트
                for r in outcomes:
                    if r.numeric_value is not None:
                        ctx._metric_cache[(r.metric_name, calc.provider)] = {
                            "numeric": r.numeric_value, "text": r.text_value, "json": r.json_value
                        }
            else:
                result.skipped_count += 1
        except Exception as e:
            result.error_count += 1
            result.errors.append((calc.name, str(activity_id), str(e)))
            log.warning(f"Calculator {calc.name} failed for activity {activity_id}: {e}")
    
    result.elapsed_seconds = time.time() - start_time
    return result
```

---

### 4. Calculator 선택적 실행 — Dirty Tracking

전체 재계산은 느립니다. "Garmin에서 새 활동 3개가 sync됐으면, 그 3개에 대해서만 activity-scope를 실행하고, 해당 날짜의 daily-scope만 실행"하는 것이 효율적입니다.

**보강 — `compute_for_activities()`와 `compute_for_dates()`**

```python
# src/metrics/engine.py

def compute_for_activities(conn, activity_ids: list[int]) -> ComputeResult:
    """특정 활동들에 대해서만 activity-scope calculator 실행"""
    result = ComputeResult()
    ordered = _topological_sort(ALL_CALCULATORS)
    activity_calcs = [c for c in ordered if c.scope_type == "activity"]
    
    for activity_id in activity_ids:
        ctx = _build_activity_context(conn, activity_id, activity_calcs)
        for calc in activity_calcs:
            _run_single(calc, ctx, result, str(activity_id))
        resolve_primaries_for_scope(conn, "activity", str(activity_id))
    
    conn.commit()
    return result


def compute_for_dates(conn, dates: list[str]) -> ComputeResult:
    """특정 날짜들에 대해서만 daily-scope calculator 실행"""
    result = ComputeResult()
    ordered = _topological_sort(ALL_CALCULATORS)
    daily_calcs = [c for c in ordered if c.scope_type == "daily"]
    
    for date_str in dates:
        ctx = _build_daily_context(conn, date_str, daily_calcs)
        for calc in daily_calcs:
            _run_single(calc, ctx, result, date_str)
        resolve_primaries_for_scope(conn, "daily", date_str)
    
    conn.commit()
    return result
```

Phase 3의 Orchestrator에서 sync 후 이 함수를 호출합니다:

```python
# garmin_activity_sync.py의 sync() 마지막 부분

# sync 완료 후 해당 활동들만 메트릭 계산
if synced_activity_ids:
    from src.metrics.engine import compute_for_activities, compute_for_dates
    compute_for_activities(conn, synced_activity_ids)
    
    affected_dates = set(...)  # sync된 활동들의 날짜
    compute_for_dates(conn, sorted(affected_dates))
```

---

### 5. Calculator 단위 테스트 패턴 — Mock CalcContext

Phase 2에서 extractor를 fixture JSON으로 테스트하듯, calculator도 **실제 DB 없이 테스트할 수 있어야** 합니다.

**보강 — `MockCalcContext`**

```python
# tests/helpers/mock_context.py

from src.metrics.base import CalcContext
from dataclasses import dataclass, field
from typing import Optional


class MockCalcContext(CalcContext):
    """DB 없이 calculator를 테스트하기 위한 mock context"""
    
    def __init__(self, scope_type="activity", scope_id="1",
                 activity_data=None, metrics=None, wellness_data=None,
                 streams=None):
        # conn은 None — DB 접근 시 에러 발생하므로 실수 방지
        super().__init__(conn=None, scope_type=scope_type, scope_id=scope_id)
        self._activity_cache = activity_data or {}
        self._metric_cache = self._build_metric_cache(metrics or {})
        self._wellness_cache = wellness_data or {}
        self._stream_cache = streams
    
    def _build_metric_cache(self, metrics: dict) -> dict:
        """{'trimp': 85.0, 'hr_zone_1_sec': 600} → cache format"""
        cache = {}
        for name, value in metrics.items():
            if isinstance(value, dict):
                cache[(name, None)] = value
            else:
                cache[(name, None)] = {"numeric": value, "text": None, "json": None}
        return cache
    
    @property
    def activity(self) -> dict:
        return self._activity_cache
    
    def get_metric(self, metric_name: str, provider: str = None) -> Optional[float]:
        key = (metric_name, provider) if provider else (metric_name, None)
        entry = self._metric_cache.get(key)
        if entry:
            return entry.get("numeric") if isinstance(entry, dict) else entry
        return None
    
    def get_wellness(self, date: str = None) -> dict:
        return self._wellness_cache
    
    def get_streams(self, activity_id: int = None) -> list[dict]:
        return self._stream_cache or []
    
    def get_activities_in_range(self, days: int, activity_type: str = None) -> list[dict]:
        # 테스트에서 필요 시 직접 설정
        return getattr(self, '_mock_activities_range', [])
    
    def get_daily_metric_series(self, metric_name, days, provider=None):
        return getattr(self, '_mock_daily_series', {}).get(metric_name, [])
    
    def get_activity_metric(self, activity_id, metric_name):
        return getattr(self, '_mock_activity_metrics', {}).get((activity_id, metric_name))
```

이것으로 테스트가 이렇게 깔끔해집니다:

```python
# tests/test_trimp.py

from tests.helpers.mock_context import MockCalcContext
from src.metrics.trimp import TRIMPCalculator

def test_trimp_basic():
    ctx = MockCalcContext(
        activity_data={
            "avg_hr": 155,
            "duration_sec": 3600,
            "moving_time_sec": 3600,
            "activity_type": "running",
        },
        wellness_data={"resting_hr": 55},
    )
    ctx._mock_activities_range = [
        {"max_hr": 190},  # 최근 활동 max_hr
    ]
    
    calc = TRIMPCalculator()
    results = calc.compute(ctx)
    
    assert len(results) == 1
    assert 80 < results[0].numeric_value < 120  # 합리적 범위
    assert results[0].confidence is not None


def test_trimp_no_hr_returns_empty():
    ctx = MockCalcContext(
        activity_data={"duration_sec": 3600},  # avg_hr 없음
    )
    
    calc = TRIMPCalculator()
    results = calc.compute(ctx)
    assert results == []


def test_trimp_short_duration():
    ctx = MockCalcContext(
        activity_data={"avg_hr": 155, "duration_sec": 60},  # 1분
        wellness_data={"resting_hr": 55},
    )
    ctx._mock_activities_range = [{"max_hr": 190}]
    
    calc = TRIMPCalculator()
    results = calc.compute(ctx)
    # 1분이라도 계산 가능 — 하지만 매우 낮은 값
    assert len(results) == 1
    assert results[0].numeric_value < 10
```

---

### 6. Confidence 계산 표준화

현재 각 calculator가 자체적으로 confidence를 설정합니다. 기준이 제각각입니다. **표준화된 confidence 계산 프레임워크**가 필요합니다.

**보강 — `ConfidenceBuilder`**

```python
# src/metrics/base.py에 추가

class ConfidenceBuilder:
    """
    메트릭 confidence를 체계적으로 계산하는 헬퍼.
    
    사용법:
        cb = ConfidenceBuilder()
        cb.add_input("avg_hr", is_available=True, weight=0.3)
        cb.add_input("max_hr", is_available=True, weight=0.2, is_estimated=True)
        cb.add_input("streams", is_available=False, weight=0.5)
        confidence = cb.compute()  # → 0.4 (available 50% × estimated penalty)
    """
    
    def __init__(self):
        self._inputs = []
    
    def add_input(self, name: str, is_available: bool, weight: float = 1.0,
                  is_estimated: bool = False):
        """
        is_estimated: 실측값이 아닌 추정값을 사용했을 때 (MaxHR 추정 등)
        """
        self._inputs.append({
            "name": name,
            "available": is_available,
            "weight": weight,
            "estimated": is_estimated,
        })
        return self
    
    def compute(self) -> float:
        if not self._inputs:
            return 0.0
        
        total_weight = sum(i["weight"] for i in self._inputs)
        if total_weight == 0:
            return 0.0
        
        score = 0.0
        for inp in self._inputs:
            if inp["available"]:
                contribution = inp["weight"] / total_weight
                if inp["estimated"]:
                    contribution *= 0.7  # 추정값은 30% 페널티
                score += contribution
        
        return round(min(score, 1.0), 2)
```

Calculator에서 사용:

```python
class TRIMPCalculator(MetricCalculator):
    def compute(self, ctx):
        # ... 계산 로직 ...
        
        cb = ConfidenceBuilder()
        cb.add_input("avg_hr", is_available=avg_hr is not None, weight=0.4)
        cb.add_input("duration", is_available=duration_sec is not None, weight=0.3)
        cb.add_input("max_hr", is_available=True, weight=0.2, 
                     is_estimated=not self._has_measured_max_hr(ctx))
        cb.add_input("rest_hr", is_available=True, weight=0.1,
                     is_estimated=(rest_hr == 60))  # fallback 사용 여부
        
        return [self._result(
            value=round(trimp, 1),
            confidence=cb.compute(),
        )]
```

---

### 7. Calculator 메타데이터 — 설명 & UI 힌트

Phase 5(UI 마이그레이션)에서 각 메트릭을 "어떻게 보여줄지"가 중요합니다. Calculator가 자신의 결과에 대한 UI 힌트를 제공해야 합니다.

**보강 — Calculator 메타데이터**

```python
class MetricCalculator(ABC):
    # 기존 속성에 추가
    display_name: str = ""        # "TRIMP (Banister)"
    description: str = ""         # "심박 기반 훈련 부하 점수"
    unit: str = ""                # "AU" (arbitrary units)
    
    # 값 해석 가이드
    ranges: dict = None           # {"low": [0, 50], "moderate": [50, 100], "high": [100, 999]}
    higher_is_better: bool = True # True면 높을수록 좋음, False면 낮을수록 좋음
    
    # UI 표시 형식
    format_type: str = "number"   # "number" | "time" | "pace" | "percentage" | "radar"
    decimal_places: int = 1
```

```python
class TRIMPCalculator(MetricCalculator):
    name = "trimp"
    display_name = "TRIMP (Banister)"
    description = "심박 기반 훈련 부하 점수. 운동 시간과 심박 강도를 종합한 부하 지표."
    unit = "AU"
    higher_is_better = None  # 높다고 좋은 게 아니고, 적절한 범위가 중요
    ranges = {
        "recovery": [0, 50],
        "easy": [50, 100],
        "moderate": [100, 200],
        "hard": [200, 350],
        "very_hard": [350, 999],
    }
    format_type = "number"
    decimal_places = 0

class UTRSCalculator(MetricCalculator):
    display_name = "훈련 준비도 (UTRS)"
    description = "수면, HRV, 체력 상태, 스트레스를 종합한 훈련 준비도."
    unit = "점"
    higher_is_better = True
    ranges = {
        "poor": [0, 30],
        "low": [30, 50],
        "moderate": [50, 70],
        "good": [70, 85],
        "excellent": [85, 100],
    }
    format_type = "number"
    decimal_places = 0

class DARPCalculator(MetricCalculator):
    display_name = "레이스 예측 (DARP)"
    description = "VDOT과 내구성 지수를 기반으로 한 레이스 시간 예측."
    unit = "sec"
    format_type = "time"  # UI에서 HH:MM:SS로 표시
```

UI에서 메트릭 카드를 렌더링할 때:

```python
def render_metric_card(calc_class, value, confidence):
    meta = calc_class  # 클래스 속성 직접 참조
    
    # 범위에 따른 색상 결정
    level = "unknown"
    if meta.ranges:
        for label, (low, high) in meta.ranges.items():
            if low <= value < high:
                level = label
                break
    
    return {
        "name": meta.display_name,
        "value": format_value(value, meta.format_type, meta.decimal_places),
        "unit": meta.unit,
        "description": meta.description,
        "level": level,
        "confidence": confidence,
    }
```

---

### 8. 소스 메트릭 vs RunPulse 메트릭 충돌 방지

Intervals가 제공하는 `decoupling`과 RunPulse가 계산하는 `aerobic_decoupling_rp`는 **같은 개념이지만 다른 이름**으로 metric_store에 들어갑니다. 이것은 의도적입니다. 하지만 UI에서 "이 활동의 디커플링"을 보여줄 때 어떤 값을 보여줄지 결정하는 로직이 필요합니다.

**보강 — 의미적 그룹핑(Semantic Grouping)**

```python
# src/utils/metric_groups.py

SEMANTIC_GROUPS = {
    "decoupling": {
        "display_name": "유산소 분리",
        "members": [
            ("aerobic_decoupling_rp", "runpulse:formula_v1"),  # RunPulse 자체 계산
            ("decoupling", "intervals"),                         # Intervals 제공
        ],
        "primary_strategy": "prefer_runpulse",  # RunPulse 값 우선
    },
    "trimp": {
        "display_name": "TRIMP",
        "members": [
            ("trimp", "runpulse:formula_v1"),
            ("trimp", "intervals"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
    "training_load": {
        "display_name": "훈련 부하",
        "members": [
            ("training_load_score", "intervals"),  # icu_training_load
            ("training_load", "garmin"),            # activityTrainingLoad (in activity_summaries)
            ("suffer_score", "strava"),             # Relative Effort (in activity_summaries)
            ("hrss", "runpulse:formula_v1"),        # HRSS
        ],
        "primary_strategy": "show_all",  # 전부 보여줌 (비교)
    },
    "vo2max": {
        "display_name": "VO2Max",
        "members": [
            ("runpulse_vdot", "runpulse:formula_v1"),
            ("vo2max_activity", "garmin"),
            ("effective_vo2max", "runalyze"),
        ],
        "primary_strategy": "show_all",
    },
    "race_prediction": {
        "display_name": "레이스 예측",
        "members": [
            ("darp_5k", "runpulse:formula_v1"),
            ("darp_10k", "runpulse:formula_v1"),
            ("darp_half", "runpulse:formula_v1"),
            ("darp_full", "runpulse:formula_v1"),
            ("race_pred_5k_sec", "garmin"),
            ("race_pred_10k_sec", "garmin"),
            ("race_pred_half_sec", "garmin"),
            ("race_pred_marathon_sec", "garmin"),
        ],
        "primary_strategy": "show_all",  # Garmin vs RunPulse 비교
    },
}
```

UI에서 "Training Load" 카드를 렌더링할 때, 이 그룹의 모든 멤버 값을 가져와서 **나란히 표시**합니다. 사용자는 "Garmin이 52, Intervals가 85, RunPulse가 91로 계산했구나"를 한눈에 볼 수 있습니다.

---

### 9. 메트릭 이름 충돌 방지 규칙

소스 extractor가 저장하는 `metric_name`과 calculator가 생성하는 `metric_name`이 겹치면 안 됩니다. 현재 설계에서 소스의 `decoupling`과 RunPulse의 `aerobic_decoupling_rp`는 다른 이름이지만, `trimp`은 **소스(Intervals)와 RunPulse가 같은 이름**을 씁니다.

이것은 의도적입니다. UNIQUE 제약이 `(scope_type, scope_id, metric_name, provider)`이므로, 같은 `metric_name`이라도 `provider`가 다르면 공존합니다. `is_primary`로 대표값을 결정합니다.

**보강 — 명시적 규칙 문서화 & 검증 테스트**

```python
# tests/test_metric_naming.py

def test_no_calculator_uses_activity_summary_column_name():
    """calculator가 activity_summaries 컬럼명과 같은 metric_name을 사용하면 안 됨.
    이유: activity_summaries에 있는 값과 metric_store에 있는 값이 이중 저장되는 것 방지.
    
    예외: 소스 extractor가 같은 이름으로 metric_store에 저장하는 것은 허용
    (소스가 activity_summaries에 없는 추가 값을 제공하는 경우).
    """
    from src.metrics.engine import ALL_CALCULATORS
    
    ACTIVITY_SUMMARY_COLUMNS = {
        "distance_m", "duration_sec", "avg_hr", "max_hr", "avg_cadence",
        "avg_speed_ms", "max_speed_ms", "avg_pace_sec_km", "calories",
        "elevation_gain", "elevation_loss", "avg_power", "max_power",
        "normalized_power", "training_effect_aerobic", "training_effect_anaerobic",
        "training_load", "suffer_score", "avg_ground_contact_time_ms",
        "avg_stride_length_cm", "avg_vertical_oscillation_cm", "avg_vertical_ratio_pct",
        "avg_temperature",
    }
    
    for calc in ALL_CALCULATORS:
        for produced_name in calc.produces:
            assert produced_name not in ACTIVITY_SUMMARY_COLUMNS, \
                f"Calculator {calc.name} produces '{produced_name}' which is an activity_summaries column"


def test_calculator_produces_match_registry():
    """모든 calculator의 produces가 metric_registry에 등록되어 있는지"""
    from src.metrics.engine import ALL_CALCULATORS
    from src.utils.metric_registry import METRIC_REGISTRY
    
    for calc in ALL_CALCULATORS:
        for produced_name in calc.produces:
            assert produced_name in METRIC_REGISTRY, \
                f"Calculator {calc.name} produces '{produced_name}' which is not in METRIC_REGISTRY"
```

---

### 10. 재계산 전략 세분화

현재 `recompute_recent(days=7)`과 `recompute_all()`만 있습니다. 실제 운영에서 필요한 시나리오가 더 있습니다.

**보강 — 재계산 CLI 인터페이스**

```python
# src/metrics/engine.py에 추가

def recompute_single_metric(conn, metric_name: str, days: int = None):
    """특정 메트릭만 재계산. 알고리즘 수정 후 검증에 유용."""
    calc = _find_calculator(metric_name)
    if not calc:
        raise ValueError(f"No calculator found for '{metric_name}'")
    
    # 이 calculator의 produces에 해당하는 기존 값 삭제
    for name in calc.produces:
        conn.execute(
            "DELETE FROM metric_store WHERE metric_name = ? AND provider = ?",
            [name, calc.provider]
        )
    conn.commit()
    
    # 재계산
    if calc.scope_type == "activity":
        activities = _get_target_activities(conn, days)
        for (aid,) in activities:
            ctx = _build_activity_context(conn, aid, [calc])
            results = calc.compute(ctx)
            _store_results(conn, calc, results, str(aid))
    
    elif calc.scope_type == "daily":
        dates = _get_target_dates(conn, days)
        for date_str in dates:
            ctx = _build_daily_context(conn, date_str, [calc])
            results = calc.compute(ctx)
            _store_results(conn, calc, results, date_str)
    
    conn.commit()


def _find_calculator(metric_name: str) -> MetricCalculator | None:
    for calc in ALL_CALCULATORS:
        if metric_name in calc.produces:
            return calc
    return None
```

CLI:

```python
# src/sync.py에 추가

# 메트릭 재계산
metric_parser = sub.add_parser("metrics", help="Manage RunPulse metrics")
metric_sub = metric_parser.add_subparsers(dest="metric_command")

metric_sub.add_parser("recompute", help="Recompute all metrics").add_argument("--days", type=int, default=7)
metric_sub.add_parser("recompute-all", help="Recompute all metrics for all time")
metric_sub.add_parser("clear", help="Clear all RunPulse metrics")

single_parser = metric_sub.add_parser("recompute-single", help="Recompute specific metric")
single_parser.add_argument("name", help="Metric name (e.g., utrs, trimp)")
single_parser.add_argument("--days", type=int, default=30)

metric_sub.add_parser("status", help="Show metric computation status")
```

Status 명령은 "어떤 메트릭이 몇 개나 계산되었는지" 요약을 보여줍니다:

```python
def show_metric_status(conn):
    """메트릭 상태 요약"""
    rows = conn.execute("""
        SELECT metric_name, provider, COUNT(*), 
               COUNT(CASE WHEN is_primary=1 THEN 1 END) as primary_count,
               AVG(confidence) as avg_confidence
        FROM metric_store
        WHERE provider LIKE 'runpulse%'
        GROUP BY metric_name, provider
        ORDER BY metric_name
    """).fetchall()
    
    print(f"\n{'Metric':<30} {'Provider':<25} {'Count':>6} {'Primary':>8} {'Avg Conf':>9}")
    print("-" * 80)
    for name, provider, count, primary, conf in rows:
        conf_str = f"{conf:.2f}" if conf else "N/A"
        print(f"{name:<30} {provider:<25} {count:>6} {primary:>8} {conf_str:>9}")
```

---

### 11. Daily Scope에서 공유 데이터 로드 최적화 — Prefetch 상세 설계

PMCCalculator의 `_get_daily_loads()`는 매일 42일치 JOIN 쿼리를 실행합니다. 7일 계산하면 7 × 42일 = 294회의 날짜를 스캔합니다. 이것을 한 번의 SELECT로 해결합니다.

```python
# src/metrics/engine.py

def _prefetch_daily_trimp_sums(conn, start_date: str, end_date: str) -> dict:
    """
    전체 기간의 날짜별 TRIMP 합산을 한 번에 로드.
    Returns: {date_str: trimp_sum}
    """
    rows = conn.execute("""
        SELECT substr(a.start_time, 1, 10) as date, 
               SUM(m.numeric_value) as total_trimp
        FROM metric_store m
        JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
        WHERE m.scope_type = 'activity'
        AND m.metric_name = 'trimp'
        AND m.is_primary = 1
        AND substr(a.start_time, 1, 10) BETWEEN ? AND ?
        GROUP BY date
    """, [start_date, end_date]).fetchall()
    
    return {r[0]: r[1] for r in rows}


def _prefetch_all_wellness(conn, start_date: str, end_date: str) -> dict:
    """
    전체 기간의 daily_wellness를 한 번에 로드.
    Returns: {date_str: {col: value}}
    """
    rows = conn.execute(
        "SELECT * FROM daily_wellness WHERE date BETWEEN ? AND ?",
        [start_date, end_date]
    ).fetchall()
    
    cols = [d[0] for d in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
    result = {}
    for row in rows:
        d = dict(zip(cols, row))
        result[d["date"]] = d
    return result


def _prefetch_daily_metrics(conn, start_date: str, end_date: str) -> dict:
    """
    전체 기간의 daily scope metric_store를 한 번에 로드.
    Returns: {date_str: {(metric_name, provider): {numeric, text, json}}}
    """
    rows = conn.execute("""
        SELECT scope_id, metric_name, provider, numeric_value, text_value, json_value, is_primary
        FROM metric_store
        WHERE scope_type = 'daily' AND scope_id BETWEEN ? AND ?
    """, [start_date, end_date]).fetchall()
    
    result = {}
    for scope_id, name, provider, num, text, json_val, is_primary in rows:
        if scope_id not in result:
            result[scope_id] = {}
        entry = {"numeric": num, "text": text, "json": json_val}
        result[scope_id][(name, provider)] = entry
        if is_primary:
            result[scope_id][(name, None)] = entry
    
    return result
```

CalcContext에서 prefetch 데이터를 참조하도록 수정:

```python
@dataclass
class CalcContext:
    # ... 기존 필드 ...
    
    # Prefetched shared data (engine이 설정)
    _prefetched_daily_loads: dict = field(default=None, repr=False)   # {date: trimp_sum}
    _prefetched_wellness_map: dict = field(default=None, repr=False)  # {date: {col: val}}
    _prefetched_daily_metrics: dict = field(default=None, repr=False) # {date: {(name,prov): val}}
    
    def get_daily_load(self, date_str: str) -> float:
        """prefetch된 daily TRIMP 합산. PMC, LSI 등에서 사용."""
        if self._prefetched_daily_loads is not None:
            return self._prefetched_daily_loads.get(date_str, 0)
        # fallback: direct query
        return self._query_daily_load(date_str)
    
    def get_wellness(self, date: str = None) -> dict:
        d = date or self.scope_id
        if self._prefetched_wellness_map is not None:
            return self._prefetched_wellness_map.get(d, {})
        # fallback: direct query
        return self._query_wellness(d)
```

그러면 PMCCalculator는 이렇게 단순해집니다:

```python
class PMCCalculator(MetricCalculator):
    def _get_daily_loads(self, ctx, days):
        # 더 이상 복잡한 JOIN 쿼리 필요 없음
        target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        loads = {}
        for i in range(days):
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            loads[d] = ctx.get_daily_load(d)
        return loads
```

---

### 12. Phase 3 → Phase 4 통합 지점

Phase 3의 Sync Orchestrator가 Phase 4의 Metrics Engine을 언제, 어떻게 호출하는지 명확히 해야 합니다.

**보강 — 통합 흐름**

```python
# src/sync/orchestrator.py의 full_sync() 마지막 부분

def full_sync(conn, sources, days, include_streams, garmin_api):
    # ... Phase 3 sync 로직 ...
    
    # ── Phase 4: Metrics Engine ──
    from src.metrics.engine import recompute_recent, ComputeResult
    
    log.info("Computing RunPulse metrics...")
    metric_result = recompute_recent(conn, days=days)
    log.info(f"Metrics: {metric_result.summary()}")
    
    return all_results, metric_result
```

Background Sync (Web UI)에서도:

```python
# src/web/bg_sync.py

def background_sync_task(conn, sources, days):
    # sync
    results = full_sync(conn, sources, days, ...)
    
    # metrics는 sync 완료 후 자동 실행됨 (full_sync 내부)
    
    # cache 무효화
    invalidate_dashboard_cache()
```

---

### 보강 완료 — 추가 항목 요약

| # | 항목 | 유형 | 영향도 |
|---|------|------|--------|
| 1 | CalcContext Prefetch & Cache | 성능 | 쿼리 수 100배 감소 |
| 2 | Stream needs_streams 플래그 | 성능 | 불필요한 stream 로드 방지 |
| 3 | ComputeResult 에러 추적 | 운영 | 실패 원인 파악 |
| 4 | Dirty Tracking (선택적 실행) | 성능 | 증분 계산 |
| 5 | MockCalcContext | 테스트 | DB 없이 단위 테스트 |
| 6 | ConfidenceBuilder | 품질 | 일관된 신뢰도 계산 |
| 7 | Calculator 메타데이터 | UI 연동 | Phase 5 준비 |
| 8 | Semantic Grouping | UI 연동 | 소스 비교 뷰 |
| 9 | 메트릭 이름 충돌 검증 | 안정성 | 이중 저장 방지 |
| 10 | 재계산 CLI 세분화 | 운영 | 메트릭별 재계산 |
| 11 | Daily Prefetch 상세 | 성능 | PMC 등 O(N²) → O(N) |
| 12 | Phase 3↔4 통합 지점 | 아키텍처 | 호출 시점 명확화 |

이 12개 항목을 Phase 4 설계에 반영하면, Phase 1~3과 동등한 깊이와 완성도가 됩니다. 나머지 Phase 5, 6도 이어서 설계할까요?

---

## Phase 4 구현 완료 기록 — 2026-04-03

### 구현 이력

| 순서 | 커밋 | 내용 |
|------|------|------|
| 1 | Phase 4: Metrics Engine 전체 구현 완료 | 19 calculators + engine + 4 test files |
| 2 | Phase 4 설계서-구현 검증 수정 | 1차 중요 5건 + 경미 5건 반영 |
| 3 | fix: engine에 실패 calculator 목록 반환 | _failed 키 추가 |
| 4 | Phase 4 DoD 완료 | test_phase4_dod.py (15 tests), fearp confidence |
| 5 | 보강 라운드1+2 | Prefetch/Cache, ComputeResult, Dirty Tracking, Integration |
| 6 | 보강 라운드3 | MockCalcContext, ConfidenceBuilder, metric naming |
| 7 | 보강 라운드4 | Calculator metadata, Semantic Grouping, CLI |
| 8 | engine.py 중복 코드 제거 | 713행→612행 축소 |
| 9 | Phase 4-6 테스트 계획 완전 구현 | test_phase4_spec.py (9 tests) |

### DoD 충족 현황

| # | 조건 | 상태 |
|---|------|------|
| 1 | ALL_CALCULATORS에 19개 calculator 등록 | ✅ |
| 2 | _topological_sort()가 의존성 순서 해소 (TRIMP < PMC < ACWR < CIRS) | ✅ |
| 3 | recompute_recent(conn, days=7) 에러 없이 완료 | ✅ |
| 4 | metric_store에 provider LIKE 'runpulse%' 행 존재 | ✅ |
| 5 | 각 activity에 TRIMP, workout_type, efficiency_factor 3개+ 생성 | ✅ |
| 6 | 각 date에 CTL, ATL, TSB, UTRS 4개+ 생성 | ✅ |
| 7 | clear_runpulse_metrics() → recompute_all() 동일 결과 재현 | ✅ |
| 8 | 소스 메트릭은 clear_runpulse_metrics()에 영향 없음 | ✅ |
| 9 | confidence 필드: UTRS, CIRS, FEARP에 설정됨 | ✅ |
| 10 | json_value: TIDS, RMR, workout_type에 설정됨 | ✅ |
| 11 | 전체 pytest 통과 | ✅ 108 tests passed |

### 보강 항목 충족 현황

| # | 항목 | 구현 위치 | 상태 |
|---|------|----------|------|
| 1 | CalcContext Prefetch & Cache | base.py (_metric_cache, _prefetched_*) | ✅ |
| 2 | Stream needs_streams 플래그 | base.py, decoupling.py, gap.py | ✅ |
| 3 | ComputeResult 에러 추적 | engine.py (ComputeResult dataclass) | ✅ |
| 4 | Dirty Tracking | engine.py (compute_for_activities/dates) | ✅ |
| 5 | MockCalcContext | tests/helpers/mock_context.py | ✅ |
| 6 | ConfidenceBuilder | base.py (ConfidenceBuilder class) | ✅ |
| 7 | Calculator 메타데이터 | 19 calculator files (display_name, unit, ranges) | ✅ |
| 8 | Semantic Grouping | src/utils/metric_groups.py (7 groups) | ✅ |
| 9 | 메트릭 이름 충돌 검증 | tests/test_metric_naming.py (4 tests) | ✅ |
| 10 | 재계산 CLI 세분화 | src/metrics/cli.py + engine.py | ✅ |
| 11 | Daily Prefetch 상세 | engine.py (_prefetch_daily_*) | ✅ |
| 12 | Phase 3↔4 통합 지점 | src/sync/integration.py | ✅ |

### 테스트 현황

| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| test_trimp_calc.py | 7 | TRIMP/HRSS 단위 |
| test_activity_calcs.py | 12 | Decoupling/GAP/Classifier/VDOT/EF |
| test_daily_calcs.py | 8 | PMC/ACWR/LSI/Monotony |
| test_daily2_calcs.py | 10 | UTRS/CIRS/FEARP/RMR/ADTI |
| test_engine.py | 12 | Engine topological sort + 통합 |
| test_phase4_dod.py | 15 | DoD 11항목 검증 |
| test_round2.py | 9 | ComputeResult/dirty tracking |
| test_mock_calcs.py | 10 | MockCalcContext 기반 |
| test_metric_naming.py | 4 | 이름 충돌 방지 |
| test_round4.py | 11 | 메타데이터/grouping/CLI |
| test_phase4_spec.py | 9 | 설계서 4-6 누락 케이스 |
| **합계** | **108** | **0.94s** |

### 최종 파일 구조

    src/metrics/
    ├── __init__.py
    ├── base.py          # MetricCalculator, CalcResult, CalcContext, ConfidenceBuilder
    ├── engine.py        # Topological engine, ComputeResult, prefetch, dirty tracking
    ├── reprocess.py     # Layer 0→1/2 재구축
    ├── cli.py           # CLI (status, recompute, clear)
    ├── trimp.py         # TRIMP (Banister)
    ├── hrss.py          # HRSS
    ├── decoupling.py    # Aerobic Decoupling
    ├── gap.py           # GAP (Minetti)
    ├── classifier.py    # Workout Classifier
    ├── vdot.py          # VDOT (Daniels)
    ├── efficiency.py    # Efficiency Factor
    ├── fearp.py         # FEARP (환경 보정)
    ├── pmc.py           # ATL/CTL/TSB/Ramp Rate
    ├── acwr.py          # ACWR
    ├── lsi.py           # Load Spike Index
    ├── monotony.py      # Monotony & Strain
    ├── utrs.py          # UTRS
    ├── cirs.py          # CIRS
    ├── di.py            # Durability Index
    ├── darp.py          # DARP
    ├── tids.py          # TIDS
    ├── rmr.py           # RMR
    └── adti.py          # ADTI

    src/utils/
    ├── metric_groups.py # 7 semantic groups

    src/sync/
    ├── integration.py   # Phase 3→4 통합

    tests/helpers/
    ├── mock_context.py  # MockCalcContext


## v0.2→v0.3 메트릭 포팅 기록 — 2026-04-03

### 포팅 대상 (v0.2에만 있던 14개)

| 배치 | 파일 | scope | 설명 |
|------|------|-------|------|
| 1 | daniels_table | utility | VDOT 룩업 (페이스/레이스/볼륨) |
| 1 | relative_effort | activity | 심박존 노력도 (Strava 방식) |
| 1 | wlei | activity | 날씨 가중 노력 지수 |
| 2 | teroi | daily | 훈련 효과 ROI |
| 2 | tpdi | daily | 실내/실외 FEARP 격차 |
| 2 | rec | daily | 통합 러닝 효율성 |
| 2 | rtti | daily | 달리기 내성 지수 |
| 2 | critical_power | daily | CP/W' 임계 파워 |
| 3 | sapi | daily | 계절 성과 비교 |
| 3 | rri | daily | 레이스 준비도 |
| 4 | eftp | daily | 역치 페이스 (daniels_table 의존) |
| 4 | vdot_adj | daily | VDOT 보정 (daniels_table 의존) |
| 4 | marathon_shape | daily | 마라톤 완성도 (daniels_table 의존) |
| 5 | crs | daily | 복합 준비도 게이트 시스템 |

### 최종 ALL_CALCULATORS (32개)

    Activity-scope (10): trimp, hrss, aerobic_decoupling_rp, gap_rp,
        workout_type, runpulse_vdot, efficiency_factor_rp, fearp,
        relative_effort, wlei

    Daily-scope (22): ctl, acwr, lsi, monotony, utrs, cirs, di, darp,
        tids, rmr, adti, teroi, tpdi, rec, rtti, critical_power,
        sapi, rri, eftp, vdot_adj, marathon_shape, crs

### 테스트: 755 passed, 0 failed


### 포팅 메트릭 테스트 (2026-04-03 추가)

| 파일 | 테스트 수 | 대상 |
|------|-----------|------|
| test_daniels_table.py | 12 | 훈련 페이스, 레이스 예측, 볼륨, T-pace |
| test_porting_activity.py | 10 | RelativeEffort, WLEI |
| test_porting_daily.py | 25 | TEROI, REC, RTTI, CP, RRI, EFTP, VDOTAdj, MarathonShape, CRS, TPDI, SAPI |
| **합계** | **47** | |

전체 테스트: **755 passed**, 0 failed (28.50s)


### 설계 원칙 준수 정비 (2026-04-03)

Phase 1-2-3-4 설계 원칙 대비 전수 점검 후 수정 완료:

| 항목 | 내용 | 조치 |
|------|------|------|
| metric_registry | 17개 메트릭 미등록 | 등록 완료 (기존 4 + 포팅 13) |
| CATEGORY_LABELS | 7개 카테고리 누락 | 추가 (rp_efficiency, rp_trend 등) |
| category 불일치 | cirs=rp_injury, tids=rp_training | registry 기준 통일 (rp_risk, rp_distribution) |
| metric_groups | 중복 그룹 존재 | 재정비 11개 (중복 제거 + 병합) |
| engine.py json_value | 이중 직렬화로 NULL 저장 | json.loads() 역직렬화 추가 |
| engine.py resolve | Phase 3 sync와 불일치 | resolve_for_scope 명시 호출 추가 |
| critical_power requires | 의존성 미선언 | requires=["power_curve"] 명시 |
| confidence | 신규 9개 미설정 | 전부 confidence 추가 |
| ranges 형식 | 단일 숫자 vs [low,high] 혼재 | [low,high] 리스트 통일 (설계서 기준) |
| test_round4.py | 단일 숫자 허용 | [low,high]만 허용 + low≤high 검증 |
| GUIDE.md | v0.2 기준 (store.py, computed_metrics) | v0.3 기준 전면 재작성 |
| architecture.md | computed_metrics 잔존 | metric_store로 수정 |
