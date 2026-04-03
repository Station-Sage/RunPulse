

# Phase 2 상세 설계 — Extractor 모듈

## 2-0. Phase 2의 목표

Phase 1에서 만든 스키마와 레지스트리 위에, **각 소스의 raw JSON을 Layer 1 + Layer 2 데이터로 변환하는 순수 함수 모듈**을 만듭니다.

핵심 원칙: Extractor는 **DB를 모릅니다**. JSON을 받아서 dict/list를 반환할 뿐입니다. DB 저장은 Phase 3(Sync Orchestrator)의 책임입니다. 이 분리 덕분에 단위 테스트가 fixture JSON 하나로 가능합니다.

---

## 2-1. Extractor 공통 인터페이스

### `src/sync/extractors/base.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class MetricRecord:
    """metric_store에 들어갈 한 행의 데이터"""
    metric_name: str
    category: str
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    json_value: Optional[str] = None       # JSON 문자열
    raw_name: Optional[str] = None         # 소스 원본 필드명
    algorithm_version: str = "1.0"
    confidence: Optional[float] = None
    parent_metric_id: Optional[int] = None
    
    def is_empty(self) -> bool:
        return self.numeric_value is None and self.text_value is None and self.json_value is None


class BaseExtractor(ABC):
    """모든 소스 extractor의 기본 클래스"""
    
    SOURCE: str = ""  # 'garmin', 'strava', 'intervals', 'runalyze'
    
    # ── Activity ──
    
    @abstractmethod
    def extract_activity_core(self, raw: dict) -> dict:
        """
        raw API JSON → activity_summaries INSERT용 dict
        
        반환 dict의 key는 activity_summaries 컬럼명과 정확히 일치해야 함.
        소스에 없는 필드는 key 자체를 포함하지 않음 (→ DB에서 NULL).
        반드시 포함해야 하는 key: source, source_id, activity_type, start_time
        """
        ...
    
    @abstractmethod
    def extract_activity_metrics(self, summary_raw: dict, 
                                  detail_raw: dict = None) -> list[MetricRecord]:
        """
        raw API JSON → metric_store INSERT용 MetricRecord 리스트
        
        activity_summaries에 이미 들어간 값은 여기에 넣지 않음 (이중 저장 금지).
        summary_raw: 활동 목록 API 응답의 한 항목
        detail_raw: 활동 상세 API 응답 (없을 수 있음)
        """
        ...
    
    def extract_activity_laps(self, detail_raw: dict) -> list[dict]:
        """
        → activity_laps INSERT용 dict 리스트
        기본 구현: 빈 리스트 (소스가 lap을 제공하지 않으면)
        """
        return []
    
    def extract_activity_streams(self, streams_raw: dict | list) -> list[dict]:
        """
        → activity_streams INSERT용 dict 리스트
        기본 구현: 빈 리스트
        """
        return []
    
    def extract_best_efforts(self, raw: dict) -> list[dict]:
        """
        → activity_best_efforts INSERT용 dict 리스트
        기본 구현: 빈 리스트
        """
        return []
    
    # ── Wellness (Daily) ──
    
    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """
        → daily_wellness INSERT/MERGE용 dict
        기본 구현: 빈 dict
        """
        return {}
    
    def extract_wellness_metrics(self, date: str, **raw_payloads) -> list[MetricRecord]:
        """
        → metric_store INSERT용 (scope_type='daily') MetricRecord 리스트
        기본 구현: 빈 리스트
        """
        return []
    
    # ── Fitness (Daily) ──
    
    def extract_fitness(self, date: str, raw: dict) -> dict:
        """
        → daily_fitness INSERT용 dict
        기본 구현: 빈 dict
        """
        return {}
    
    # ── Helpers ──
    
    def _metric(self, name: str, value=None, text=None, json_val=None,
                category: str = None, raw_name: str = None,
                version: str = "1.0", confidence: float = None) -> MetricRecord:
        """MetricRecord 생성 헬퍼. value가 모두 None이면 None 반환."""
        if value is None and text is None and json_val is None:
            return None
        
        # category가 명시되지 않으면 registry에서 조회
        if category is None:
            from src.utils.metric_registry import get_category
            category = get_category(name)
        
        json_str = json.dumps(json_val, ensure_ascii=False) if json_val is not None else None
        
        return MetricRecord(
            metric_name=name,
            category=category,
            numeric_value=float(value) if value is not None else None,
            text_value=text,
            json_value=json_str,
            raw_name=raw_name or name,
            algorithm_version=version,
            confidence=confidence,
        )
    
    def _collect(self, *records: Optional[MetricRecord]) -> list[MetricRecord]:
        """None이 아닌 MetricRecord만 모아서 반환"""
        return [r for r in records if r is not None and not r.is_empty()]
```

### 설계 결정 — `_metric()` 헬퍼

모든 extractor에서 반복되는 패턴을 제거합니다. "값이 None이면 저장하지 않는다"는 규칙을 한 곳에서 적용합니다. `_collect()`는 가변 인자로 받은 MetricRecord 중 유효한 것만 필터링합니다. Extractor 코드에서는 이렇게 쓸 수 있습니다:

```python
return self._collect(
    self._metric("trimp", raw.get("trimp"), category="training_load"),
    self._metric("efficiency_factor", raw.get("ef"), category="efficiency"),
    # raw에 trimp이 없으면 → _metric이 None 반환 → _collect이 걸러냄
)
```

### 설계 결정 — `extract_activity_core` 반환값에 `source`와 `source_id` 포함

Extractor가 `source` 필드를 직접 채웁니다. Orchestrator가 나중에 추가할 수도 있지만, Extractor 자체가 "나는 Garmin이다"를 아는 게 자연스럽고, 테스트에서도 반환 dict만으로 완전한 데이터인지 검증할 수 있습니다.

---

## 2-2. `garmin_extractor.py` — Garmin Activity

Garmin이 가장 데이터가 풍부하고 복잡합니다. 두 종류의 raw JSON을 처리합니다:

1. **summary_raw**: `GET /activitylist-service/activities/search/activities` 응답의 한 항목 (목록 API)
2. **detail_raw**: `GET /activity-service/activity/{id}/details` 응답 (상세 API)

### `extract_activity_core` — 46컬럼 중 Garmin이 채울 수 있는 것

```python
# src/sync/extractors/garmin_extractor.py

from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.metric_registry import canonicalize
from src.utils.activity_types import normalize_activity_type
import json


class GarminExtractor(BaseExtractor):
    
    SOURCE = "garmin"
    
    def extract_activity_core(self, raw: dict) -> dict:
        """Garmin activity summary JSON → activity_summaries dict"""
        
        activity_type_raw = raw.get("activityType", {})
        type_key = activity_type_raw.get("typeKey", "unknown")
        
        # 속도 → 페이스 변환
        avg_speed = raw.get("averageSpeed")
        avg_pace = None
        if avg_speed and avg_speed > 0:
            avg_pace = round(1000.0 / avg_speed, 2)  # sec/km
        
        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("activityId", "")),
            "name": raw.get("activityName"),
            "activity_type": normalize_activity_type(type_key, self.SOURCE),
            "start_time": raw.get("startTimeGMT"),
            
            # 거리/시간
            "distance_m": raw.get("distance"),
            "duration_sec": _seconds(raw.get("duration")),
            "moving_time_sec": _seconds(raw.get("movingDuration")),
            "elapsed_time_sec": _seconds(raw.get("elapsedDuration")),
            
            # 속도/페이스
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("maxSpeed"),
            "avg_pace_sec_km": avg_pace,
            
            # 심박
            "avg_hr": _int(raw.get("averageHR")),
            "max_hr": _int(raw.get("maxHR")),
            
            # 케이던스
            "avg_cadence": _int(raw.get("averageRunningCadenceInStepsPerMinute")),
            "max_cadence": _int(raw.get("maxRunningCadenceInStepsPerMinute")),
            
            # 파워
            "avg_power": raw.get("avgPower"),
            "max_power": raw.get("maxPower"),
            "normalized_power": raw.get("normPower"),
            
            # 고도
            "elevation_gain": raw.get("elevationGain"),
            "elevation_loss": raw.get("elevationLoss"),
            
            # 에너지
            "calories": _int(raw.get("calories")),
            
            # 훈련 효과/부하
            "training_effect_aerobic": raw.get("aerobicTrainingEffect"),
            "training_effect_anaerobic": raw.get("anaerobicTrainingEffect"),
            "training_load": raw.get("activityTrainingLoad"),
            
            # 러닝 다이내믹스
            "avg_ground_contact_time_ms": raw.get("avgGroundContactTime"),
            "avg_stride_length_cm": _stride_to_cm(raw.get("avgStrideLength")),
            "avg_vertical_oscillation_cm": raw.get("avgVerticalOscillation"),
            "avg_vertical_ratio_pct": raw.get("avgVerticalRatio"),
            
            # 위치
            "start_lat": raw.get("startLatitude"),
            "start_lon": raw.get("startLongitude"),
            "end_lat": raw.get("endLatitude"),
            "end_lon": raw.get("endLongitude"),
            
            # 환경
            "avg_temperature": _celsius_if_available(raw),
            
            # 메타
            "description": raw.get("description"),
            "event_type": raw.get("eventType", {}).get("typeKey") if isinstance(raw.get("eventType"), dict) else raw.get("eventType"),
            "device_name": _extract_device_name(raw),
            "source_url": f"https://connect.garmin.com/modern/activity/{raw.get('activityId')}",
        }
        
        # None 값인 key 제거 (DB에서 자연스럽게 NULL)
        return {k: v for k, v in core.items() if v is not None}
```

### Garmin 필드 매핑 근거

여기서 각 매핑의 근거를 명시합니다. 이것은 extractor를 유지보수하는 다음 개발자(또는 AI)가 "왜 이 필드를 이 컬럼에 매핑했는지" 이해할 수 있게 합니다.

```python
# ── 필드 매핑 근거 (주석으로 코드에 포함) ──
#
# raw["distance"]           → distance_m       Garmin API는 미터 단위 반환
# raw["duration"]           → duration_sec     밀리초일 수 있음, _seconds()로 변환
# raw["movingDuration"]     → moving_time_sec  움직인 시간만 (정지 제외)
# raw["elapsedDuration"]    → elapsed_time_sec 전체 경과 시간
# raw["averageSpeed"]       → avg_speed_ms     m/s 단위
# raw["maxSpeed"]           → max_speed_ms     m/s 단위
# raw["averageHR"]          → avg_hr           bpm, 소수점 있을 수 있어 _int()
# raw["maxHR"]              → max_hr           bpm
# raw["averageRunningCadenceInStepsPerMinute"] → avg_cadence  spm (steps/min)
# raw["maxRunningCadenceInStepsPerMinute"]     → max_cadence  spm
# raw["avgPower"]           → avg_power        watts
# raw["maxPower"]           → max_power        watts  
# raw["normPower"]          → normalized_power watts
# raw["elevationGain"]      → elevation_gain   미터
# raw["elevationLoss"]      → elevation_loss   미터
# raw["calories"]           → calories         kcal
# raw["aerobicTrainingEffect"]   → training_effect_aerobic    0.0~5.0
# raw["anaerobicTrainingEffect"] → training_effect_anaerobic  0.0~5.0
# raw["activityTrainingLoad"]    → training_load              Garmin 고유 점수
# raw["avgGroundContactTime"]    → avg_ground_contact_time_ms 밀리초
# raw["avgStrideLength"]         → avg_stride_length_cm       미터→cm 변환 필요
# raw["avgVerticalOscillation"]  → avg_vertical_oscillation_cm cm
# raw["avgVerticalRatio"]        → avg_vertical_ratio_pct     %
```

### 헬퍼 함수들

```python
def _seconds(value) -> int | None:
    """Garmin duration 값을 초 단위로 변환.
    Garmin API는 일부 엔드포인트에서 초, 일부에서 밀리초를 반환.
    """
    if value is None:
        return None
    value = float(value)
    if value > 86400 * 1000:  # 1일 이상의 밀리초 → 확실히 ms 단위
        return int(value / 1000)
    if value > 86400:  # 1일 이상이면 밀리초일 가능성 (24시간 이상 달리지 않음)
        return int(value / 1000)
    return int(value)  # 이미 초 단위


def _int(value) -> int | None:
    """안전한 int 변환"""
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _stride_to_cm(value_m) -> float | None:
    """Garmin stride length는 미터 단위. cm로 변환."""
    if value_m is None:
        return None
    return round(float(value_m) * 100, 1)


def _celsius_if_available(raw: dict) -> float | None:
    """다양한 온도 필드에서 값 추출"""
    for key in ("averageTemperature", "minTemperature", "maxTemperature"):
        val = raw.get(key)
        if val is not None:
            return float(val)
    return None


def _extract_device_name(raw: dict) -> str | None:
    """deviceName 또는 metadataDTO에서 디바이스명 추출"""
    name = raw.get("deviceName")
    if name:
        return name
    meta = raw.get("metadataDTO", {})
    return meta.get("deviceName") or meta.get("productDisplayName")
```

### `extract_activity_metrics` — metric_store로 가는 값들

```python
    def extract_activity_metrics(self, summary_raw: dict,
                                  detail_raw: dict = None) -> list[MetricRecord]:
        """activity_summaries에 없는 모든 Garmin 메트릭 추출"""
        
        raw = summary_raw  # 편의 alias
        
        metrics = self._collect(
            # ── Fitness ──
            self._metric("vo2max_activity",
                         raw.get("vO2MaxValue"),
                         category="fitness",
                         raw_name="vO2MaxValue"),
            
            # ── General ──
            self._metric("steps",
                         raw.get("steps"),
                         category="general",
                         raw_name="steps"),
            self._metric("perceived_exertion",
                         raw.get("averageRPE"),
                         category="general",
                         raw_name="averageRPE"),
            
            # ── Recovery ──
            self._metric("body_battery_diff",
                         raw.get("differenceBodyBattery"),
                         category="recovery",
                         raw_name="differenceBodyBattery"),
            
            # ── Training Load 추가 ──
            self._metric("intensity_mins_moderate",
                         raw.get("moderateIntensityMinutes"),
                         category="training_load",
                         raw_name="moderateIntensityMinutes"),
            self._metric("intensity_mins_vigorous",
                         raw.get("vigorousIntensityMinutes"),
                         category="training_load",
                         raw_name="vigorousIntensityMinutes"),
            self._metric("training_stress_score",
                         raw.get("trainingStressScore"),
                         category="training_load",
                         raw_name="trainingStressScore"),
            self._metric("intensity_factor",
                         raw.get("intensityFactor"),
                         category="training_load",
                         raw_name="intensityFactor"),
            
            # ── Running Dynamics 추가 (core에 없는 것들) ──
            self._metric("ground_contact_balance",
                         raw.get("avgGroundContactBalance"),
                         category="running_dynamics",
                         raw_name="avgGroundContactBalance"),
            
            # ── Efficiency ──
            self._metric("avg_stride",
                         raw.get("avgStrideLength"),
                         category="efficiency",
                         raw_name="avgStrideLength"),
            
            # ── Fitness 추가 ──
            self._metric("lactate_threshold_hr",
                         raw.get("lactateThresholdBpm"),
                         category="fitness",
                         raw_name="lactateThresholdBpm"),
            self._metric("lactate_threshold_speed",
                         raw.get("lactateThresholdSpeed"),
                         category="fitness",
                         raw_name="lactateThresholdSpeed"),
            self._metric("performance_condition",
                         raw.get("performanceCondition"),
                         category="fitness",
                         raw_name="performanceCondition"),
            
            # ── 호흡 ──
            self._metric("avg_respiration_rate",
                         raw.get("averageRespirationRate"),
                         category="general",
                         raw_name="averageRespirationRate"),
            
            # ── SpO2 ──
            self._metric("avg_spo2",
                         raw.get("avgSpo2"),
                         category="fitness",
                         raw_name="avgSpo2"),
            self._metric("min_spo2",
                         raw.get("minSpo2"),
                         category="fitness",
                         raw_name="minSpo2"),
            
            # ── 메타 (metric_store로 가는 것들) ──
            self._metric("timezone_offset",
                         raw.get("timeZoneUnitDTO", {}).get("offset") if isinstance(raw.get("timeZoneUnitDTO"), dict) else None,
                         category="general",
                         raw_name="timeZoneUnitDTO.offset"),
            self._metric("best_pace_sec_km",
                         _best_pace(raw.get("maxSpeed")),
                         category="general",
                         raw_name="maxSpeed→best_pace"),
        )
        
        # ── Detail API에서만 오는 메트릭 ──
        if detail_raw:
            metrics.extend(self._extract_detail_metrics(detail_raw))
        
        return metrics
    
    
    def _extract_detail_metrics(self, detail: dict) -> list[MetricRecord]:
        """활동 상세 API 응답에서 추가 메트릭 추출"""
        
        results = []
        
        # ── HR Zones ──
        hr_zones = detail.get("hrTimeInZone") or detail.get("heartRateZones")
        if hr_zones and isinstance(hr_zones, list):
            for i, zone_data in enumerate(hr_zones[:5]):
                if isinstance(zone_data, dict):
                    secs = zone_data.get("secsInZone")
                elif isinstance(zone_data, (int, float)):
                    # 밀리초인 경우
                    secs = zone_data / 1000 if zone_data > 10000 else zone_data
                else:
                    continue
                
                r = self._metric(
                    f"hr_zone_{i+1}_sec", secs,
                    category="hr_zone",
                    raw_name=f"hrTimeInZone[{i}]"
                )
                if r:
                    results.append(r)
            
            # 전체 JSON도 저장
            r = self._metric(
                "hr_zones_detail", json_val=hr_zones,
                category="hr_zone",
                raw_name="hrTimeInZone"
            )
            if r:
                results.append(r)
        
        # ── Power Zones ──
        pz = detail.get("powerTimeInZone") or detail.get("powerZones")
        if pz and isinstance(pz, list):
            for i, zone_data in enumerate(pz[:7]):
                val = zone_data
                if isinstance(zone_data, dict):
                    val = zone_data.get("secsInZone")
                if val is not None:
                    r = self._metric(
                        f"power_zone_{i+1}_sec", val,
                        category="power_zone",
                        raw_name=f"powerTimeInZone[{i}]"
                    )
                    if r:
                        results.append(r)
            
            r = self._metric(
                "power_zones_detail", json_val=pz,
                category="power_zone",
                raw_name="powerTimeInZone"
            )
            if r:
                results.append(r)
        
        # ── Weather ──
        weather = detail.get("weatherDTO") or detail.get("weather", {})
        if weather and isinstance(weather, dict):
            results.extend(self._collect(
                self._metric("weather_temp_c", weather.get("temp"),
                             category="weather", raw_name="weatherDTO.temp"),
                self._metric("weather_humidity_pct", weather.get("relativeHumidity"),
                             category="weather", raw_name="weatherDTO.relativeHumidity"),
                self._metric("weather_wind_speed_ms", weather.get("windSpeed"),
                             category="weather", raw_name="weatherDTO.windSpeed"),
                self._metric("weather_wind_direction_deg", weather.get("windDirection"),
                             category="weather", raw_name="weatherDTO.windDirection"),
                self._metric("weather_dew_point_c", weather.get("dewPoint"),
                             category="weather", raw_name="weatherDTO.dewPoint"),
            ))
        
        # ── Splits (km별 스플릿) ──
        splits = detail.get("splitSummaries") or detail.get("splits")
        if splits:
            r = self._metric(
                "splits_metric", json_val=splits,
                category="general",
                raw_name="splitSummaries"
            )
            if r:
                results.append(r)
        
        return results
```

### `extract_activity_laps` — Garmin 랩 데이터

```python
    def extract_activity_laps(self, detail_raw: dict) -> list[dict]:
        """Garmin 상세 API에서 랩 추출"""
        laps_raw = detail_raw.get("laps") or detail_raw.get("lapDTOs") or []
        laps = []
        
        for i, lap in enumerate(laps_raw):
            lap_dict = {
                "source": self.SOURCE,
                "lap_index": i,
                "start_time": lap.get("startTimeGMT"),
                "duration_sec": _seconds(lap.get("duration")),
                "distance_m": lap.get("distance"),
                "avg_hr": _int(lap.get("averageHR")),
                "max_hr": _int(lap.get("maxHR")),
                "avg_cadence": _int(lap.get("averageRunningCadenceInStepsPerMinute")),
                "avg_power": lap.get("avgPower"),
                "max_power": lap.get("maxPower"),
                "elevation_gain": lap.get("elevationGain"),
                "calories": _int(lap.get("calories")),
                "lap_trigger": lap.get("lapTrigger"),
            }
            
            # avg_pace_sec_km 계산
            avg_speed = lap.get("averageSpeed")
            if avg_speed and avg_speed > 0:
                lap_dict["avg_pace_sec_km"] = round(1000.0 / avg_speed, 2)
            
            # None 제거
            laps.append({k: v for k, v in lap_dict.items() if v is not None})
        
        return laps
```

---

## 2-3. Garmin Wellness Extractor

Garmin wellness는 여러 API 엔드포인트에서 데이터가 옵니다:

- Sleep: `/wellness-service/wellness/dailySleepData/{date}`
- HRV: `/hrv-service/hrv/{date}`
- Body Battery: `/wellness-service/wellness/bodyBattery/date/{date}`
- Stress: `/wellness-service/wellness/dailyStress/{date}`
- User Summary: `/usersummary-service/usersummary/daily/{date}`
- Training Readiness: `/metrics-service/metrics/trainingreadiness/{date}`
- Race Predictions: `/metrics-service/metrics/racepredictions`

각 엔드포인트의 raw JSON이 `source_payloads`에 개별 저장되고, extractor에 `**raw_payloads`로 전달됩니다.

```python
    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """여러 Garmin wellness API → daily_wellness 핵심 필드"""
        
        core = {}
        
        # ── Sleep ──
        sleep = raw_payloads.get("sleep_day", {})
        if sleep:
            core["sleep_score"] = _int(sleep.get("overallScore") or sleep.get("sleepScores", {}).get("overall"))
            core["sleep_duration_sec"] = _seconds(sleep.get("sleepTimeSeconds"))
            core["sleep_start_time"] = sleep.get("sleepStartTimestampGMT") or sleep.get("calendarDate")
        
        # ── HRV ──
        hrv = raw_payloads.get("hrv_day", {})
        if hrv:
            summary = hrv.get("hrvSummary", hrv)
            core["hrv_weekly_avg"] = summary.get("weeklyAvg")
            core["hrv_last_night"] = summary.get("lastNightAvg") or summary.get("lastNight5MinHigh")
            core["resting_hr"] = _int(summary.get("restingHeartRate") or 
                                      raw_payloads.get("user_summary_day", {}).get("restingHeartRate"))
        
        # ── Body Battery ──
        bb = raw_payloads.get("body_battery_day", {})
        if bb:
            # body battery는 리스트 형태일 수 있음
            if isinstance(bb, list) and bb:
                values = [item.get("bodyBatteryLevel", 0) for item in bb if item.get("bodyBatteryLevel") is not None]
                if values:
                    core["body_battery_high"] = max(values)
                    core["body_battery_low"] = min(values)
            elif isinstance(bb, dict):
                core["body_battery_high"] = bb.get("bodyBatteryHigh") or bb.get("highestValue")
                core["body_battery_low"] = bb.get("bodyBatteryLow") or bb.get("lowestValue")
        
        # ── Stress ──
        stress = raw_payloads.get("stress_day", {})
        if stress:
            core["avg_stress"] = _int(stress.get("overallStressLevel") or stress.get("avgStressLevel"))
        
        # ── User Summary ──
        summary = raw_payloads.get("user_summary_day", {})
        if summary:
            core["steps"] = _int(summary.get("totalSteps"))
            core["active_calories"] = _int(summary.get("activeKilocalories"))
            # resting_hr fallback
            if "resting_hr" not in core:
                core["resting_hr"] = _int(summary.get("restingHeartRate"))
        
        return {k: v for k, v in core.items() if v is not None}
    
    
    def extract_wellness_metrics(self, date: str, **raw_payloads) -> list[MetricRecord]:
        """daily_wellness core에 안 들어가는 모든 상세 값 → metric_store"""
        
        metrics = []
        
        # ── Sleep 상세 ──
        sleep = raw_payloads.get("sleep_day", {})
        if sleep:
            metrics.extend(self._collect(
                self._metric("sleep_deep_sec", _seconds(sleep.get("deepSleepSeconds")),
                             category="sleep", raw_name="deepSleepSeconds"),
                self._metric("sleep_light_sec", _seconds(sleep.get("lightSleepSeconds")),
                             category="sleep", raw_name="lightSleepSeconds"),
                self._metric("sleep_rem_sec", _seconds(sleep.get("remSleepSeconds")),
                             category="sleep", raw_name="remSleepSeconds"),
                self._metric("sleep_awake_sec", _seconds(sleep.get("awakeSleepSeconds")),
                             category="sleep", raw_name="awakeSleepSeconds"),
                self._metric("avg_respiration", sleep.get("averageRespiration"),
                             category="sleep", raw_name="averageRespiration"),
                self._metric("avg_spo2_sleep", sleep.get("averageSpO2Value"),
                             category="sleep", raw_name="averageSpO2Value"),
                self._metric("avg_sleep_stress", sleep.get("averageSleepStress"),
                             category="sleep", raw_name="averageSleepStress"),
                
                # 수면 점수 상세
                self._metric("sleep_deep_score",
                             (sleep.get("sleepScores") or {}).get("deep"),
                             category="sleep", raw_name="sleepScores.deep"),
                self._metric("sleep_rem_score",
                             (sleep.get("sleepScores") or {}).get("rem"),
                             category="sleep", raw_name="sleepScores.rem"),
                self._metric("sleep_recovery_score",
                             (sleep.get("sleepScores") or {}).get("recovery"),
                             category="sleep", raw_name="sleepScores.recovery"),
            ))
        
        # ── Stress 상세 ──
        stress = raw_payloads.get("stress_day", {})
        if stress:
            metrics.extend(self._collect(
                self._metric("stress_high_duration", stress.get("highStressDuration"),
                             category="stress", raw_name="highStressDuration"),
                self._metric("stress_medium_duration", stress.get("mediumStressDuration"),
                             category="stress", raw_name="mediumStressDuration"),
                self._metric("stress_low_duration", stress.get("lowStressDuration"),
                             category="stress", raw_name="lowStressDuration"),
                self._metric("rest_stress_duration", stress.get("restStressDuration"),
                             category="stress", raw_name="restStressDuration"),
                self._metric("max_stress", stress.get("maxStressLevel"),
                             category="stress", raw_name="maxStressLevel"),
            ))
        
        # ── Training Readiness ──
        tr = raw_payloads.get("training_readiness", {})
        if tr:
            metrics.extend(self._collect(
                self._metric("training_readiness_score", tr.get("score"),
                             category="readiness", raw_name="score"),
                self._metric("training_readiness_level", text=tr.get("level"),
                             category="readiness", raw_name="level"),
                self._metric("training_readiness_sleep_factor", tr.get("sleepScoreFactorPercent"),
                             category="readiness", raw_name="sleepScoreFactorPercent"),
                self._metric("training_readiness_hrv_factor", tr.get("hrvFactorPercent"),
                             category="readiness", raw_name="hrvFactorPercent"),
                self._metric("training_readiness_acute_load_factor", tr.get("acuteLoadFactorPercent"),
                             category="readiness", raw_name="acuteLoadFactorPercent"),
            ))
        
        # ── Race Predictions ──
        rp = raw_payloads.get("race_predictions", {})
        if rp:
            metrics.extend(self._collect(
                self._metric("race_pred_5k_sec", rp.get("raceTime5K"),
                             category="prediction", raw_name="raceTime5K"),
                self._metric("race_pred_10k_sec", rp.get("raceTime10K"),
                             category="prediction", raw_name="raceTime10K"),
                self._metric("race_pred_half_sec", rp.get("raceTimeHalf"),
                             category="prediction", raw_name="raceTimeHalf"),
                self._metric("race_pred_marathon_sec", rp.get("raceTimeMarathon"),
                             category="prediction", raw_name="raceTimeMarathon"),
            ))
        
        # ── User Summary 추가 ──
        summary = raw_payloads.get("user_summary_day", {})
        if summary:
            metrics.extend(self._collect(
                self._metric("floors_climbed", summary.get("floorsAscended"),
                             category="general", raw_name="floorsAscended"),
                self._metric("intensity_mins_moderate", summary.get("moderateIntensityMinutes"),
                             category="training_load", raw_name="moderateIntensityMinutes"),
                self._metric("intensity_mins_vigorous", summary.get("vigorousIntensityMinutes"),
                             category="training_load", raw_name="vigorousIntensityMinutes"),
                self._metric("avg_spo2", summary.get("averageSpo2"),
                             category="fitness", raw_name="averageSpo2"),
                self._metric("total_calories", summary.get("totalKilocalories"),
                             category="general", raw_name="totalKilocalories"),
            ))
        
        # ── HRV 추가 상세 ──
        hrv = raw_payloads.get("hrv_day", {})
        if hrv:
            summary_hrv = hrv.get("hrvSummary", hrv)
            metrics.extend(self._collect(
                self._metric("hrv_7d_avg", summary_hrv.get("weeklyAvg"),
                             category="hrv", raw_name="weeklyAvg"),
                self._metric("hrv_status",
                             text=summary_hrv.get("status") or summary_hrv.get("hrvStatus"),
                             category="hrv", raw_name="status"),
                self._metric("hrv_baseline_low", summary_hrv.get("baselineLowUpper"),
                             category="hrv", raw_name="baselineLowUpper"),
                self._metric("hrv_baseline_balanced_low", summary_hrv.get("baselineBalancedLow"),
                             category="hrv", raw_name="baselineBalancedLow"),
                self._metric("hrv_baseline_balanced_upper", summary_hrv.get("baselineBalancedUpper"),
                             category="hrv", raw_name="baselineBalancedUpper"),
            ))
        
        return metrics
    
    
    def extract_fitness(self, date: str, raw: dict) -> dict:
        """→ daily_fitness INSERT용 dict. Garmin 자체 PMC가 있으면 추출."""
        # Garmin은 직접적인 CTL/ATL을 API로 제공하지 않음.
        # training_status 엔드포인트에 vo2max 히스토리가 있을 수 있음.
        fitness = {
            "source": self.SOURCE,
            "date": date,
        }
        
        vo2max = raw.get("vo2MaxValue") or raw.get("vo2max")
        if vo2max is not None:
            fitness["vo2max"] = float(vo2max)
        
        return {k: v for k, v in fitness.items() if v is not None}
```

---

## 2-4. `strava_extractor.py`

Strava API 응답 구조는 Garmin보다 단순합니다. 주요 엔드포인트:

1. **activity list**: `GET /api/v3/athlete/activities` → 배열
2. **activity detail**: `GET /api/v3/activities/{id}` → 단일 객체
3. **streams**: `GET /api/v3/activities/{id}/streams` → 배열

```python
class StravaExtractor(BaseExtractor):
    
    SOURCE = "strava"
    
    def extract_activity_core(self, raw: dict) -> dict:
        """Strava activity JSON → activity_summaries dict"""
        
        avg_speed = raw.get("average_speed")
        avg_pace = round(1000.0 / avg_speed, 2) if avg_speed and avg_speed > 0 else None
        
        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("id", "")),
            "name": raw.get("name"),
            "activity_type": normalize_activity_type(raw.get("type", "unknown"), self.SOURCE),
            "start_time": raw.get("start_date"),         # UTC ISO8601
            
            "distance_m": raw.get("distance"),
            "duration_sec": raw.get("elapsed_time"),      # Strava: elapsed_time은 초 단위
            "moving_time_sec": raw.get("moving_time"),
            "elapsed_time_sec": raw.get("elapsed_time"),
            
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("max_speed"),
            "avg_pace_sec_km": avg_pace,
            
            "avg_hr": _int(raw.get("average_heartrate")),
            "max_hr": _int(raw.get("max_heartrate")),
            
            "avg_cadence": _strava_cadence(raw.get("average_cadence")),
            
            "avg_power": raw.get("average_watts") or raw.get("weighted_average_watts"),
            "max_power": raw.get("max_watts"),
            
            "elevation_gain": raw.get("total_elevation_gain"),
            
            "calories": _int(raw.get("calories")),
            
            "suffer_score": _int(raw.get("suffer_score")),
            
            "start_lat": _latlng_first(raw.get("start_latlng")),
            "start_lon": _latlng_second(raw.get("start_latlng")),
            "end_lat": _latlng_first(raw.get("end_latlng")),
            "end_lon": _latlng_second(raw.get("end_latlng")),
            
            "avg_temperature": raw.get("average_temp"),
            
            "description": raw.get("description"),
            "event_type": raw.get("workout_type"),
            "device_name": raw.get("device_name"),
            "gear_id": raw.get("gear_id"),
            "source_url": f"https://www.strava.com/activities/{raw.get('id')}",
        }
        
        return {k: v for k, v in core.items() if v is not None}
    
    
    def extract_activity_metrics(self, summary_raw: dict,
                                  detail_raw: dict = None) -> list[MetricRecord]:
        """Strava 활동의 metric_store 메트릭"""
        
        raw = detail_raw or summary_raw
        
        metrics = self._collect(
            self._metric("kilojoules", raw.get("kilojoules"),
                         category="general", raw_name="kilojoules"),
            self._metric("perceived_exertion", raw.get("perceived_exertion"),
                         category="general", raw_name="perceived_exertion"),
            self._metric("achievement_count", raw.get("achievement_count"),
                         category="general", raw_name="achievement_count"),
            self._metric("pr_count", raw.get("pr_count"),
                         category="general", raw_name="pr_count"),
            self._metric("normalized_power",
                         raw.get("weighted_average_watts"),
                         category="power_zone", raw_name="weighted_average_watts"),
            self._metric("timezone_offset",
                         text=raw.get("timezone"),
                         category="general", raw_name="timezone"),
        )
        
        # ── Segment Efforts (상세 API에서만) ──
        if raw.get("segment_efforts"):
            metrics.append(self._metric(
                "segment_efforts",
                json_val=_simplify_segments(raw["segment_efforts"]),
                category="general",
                raw_name="segment_efforts"
            ))
        
        # ── Splits ──
        if raw.get("splits_metric"):
            metrics.append(self._metric(
                "splits_metric",
                json_val=raw["splits_metric"],
                category="general",
                raw_name="splits_metric"
            ))
        
        return [m for m in metrics if m is not None]
    
    
    def extract_activity_streams(self, streams_raw: dict | list) -> list[dict]:
        """Strava streams API → activity_streams dict 리스트"""
        
        # Strava streams는 {type: {data: [...], ...}, ...} 또는 [{type, data}, ...] 형태
        if isinstance(streams_raw, list):
            stream_map = {s["type"]: s["data"] for s in streams_raw if "type" in s and "data" in s}
        elif isinstance(streams_raw, dict):
            stream_map = {k: v.get("data", v) if isinstance(v, dict) else v 
                          for k, v in streams_raw.items()}
        else:
            return []
        
        time_data = stream_map.get("time", [])
        if not time_data:
            return []
        
        rows = []
        for i, t in enumerate(time_data):
            row = {
                "source": self.SOURCE,
                "elapsed_sec": t,
                "distance_m": _safe_index(stream_map.get("distance"), i),
                "heart_rate": _safe_index(stream_map.get("heartrate"), i),
                "cadence": _strava_cadence(_safe_index(stream_map.get("cadence"), i)),
                "power_watts": _safe_index(stream_map.get("watts"), i),
                "altitude_m": _safe_index(stream_map.get("altitude"), i),
                "speed_ms": _safe_index(stream_map.get("velocity_smooth"), i),
                "latitude": _safe_index(_latlng_stream(stream_map.get("latlng"), "lat"), i),
                "longitude": _safe_index(_latlng_stream(stream_map.get("latlng"), "lng"), i),
                "grade_pct": _safe_index(stream_map.get("grade_smooth"), i),
                "temperature_c": _safe_index(stream_map.get("temp"), i),
            }
            rows.append({k: v for k, v in row.items() if v is not None})
        
        return rows
    
    
    def extract_best_efforts(self, raw: dict) -> list[dict]:
        """Strava best_efforts → activity_best_efforts"""
        efforts = raw.get("best_efforts", [])
        results = []
        for e in efforts:
            results.append({
                "source": self.SOURCE,
                "effort_name": e.get("name", "unknown"),
                "elapsed_sec": e.get("elapsed_time"),
                "distance_m": e.get("distance"),
                "start_index": e.get("start_index"),
                "end_index": e.get("end_index"),
                "pr_rank": e.get("pr_rank"),
            })
        return results


# ── Strava 헬퍼 ──

def _strava_cadence(value) -> int | None:
    """Strava cadence는 half cycles (spm/2). 원본 저장 후 UI에서 ×2."""
    # 실제로 Strava API가 half-cadence를 반환하는지 확인 필요
    # 확인될 때까지 원본 그대로 저장
    if value is None:
        return None
    return int(round(float(value)))


def _latlng_first(latlng) -> float | None:
    if isinstance(latlng, (list, tuple)) and len(latlng) >= 2:
        return latlng[0]
    return None

def _latlng_second(latlng) -> float | None:
    if isinstance(latlng, (list, tuple)) and len(latlng) >= 2:
        return latlng[1]
    return None

def _latlng_stream(latlng_data, component: str) -> list | None:
    """latlng stream [[lat,lng], ...] → [lat, ...] or [lng, ...]"""
    if not latlng_data:
        return None
    idx = 0 if component == "lat" else 1
    return [point[idx] if isinstance(point, (list, tuple)) and len(point) > idx else None 
            for point in latlng_data]

def _safe_index(lst, i):
    if lst is None:
        return None
    if i < len(lst):
        return lst[i]
    return None

def _simplify_segments(segments: list) -> list:
    """세그먼트 데이터에서 핵심만 추출 (json 크기 줄이기)"""
    return [
        {
            "name": s.get("name"),
            "elapsed_time": s.get("elapsed_time"),
            "distance": s.get("distance"),
            "average_hr": s.get("average_heartrate"),
            "pr_rank": s.get("pr_rank"),
        }
        for s in (segments or [])
    ]
```

---

## 2-5. `intervals_extractor.py`

Intervals.icu API는 분석 메트릭이 풍부합니다. 응답 구조:

1. **activity list**: `GET /api/v1/athlete/{id}/activities` → 배열
2. **activity detail**: `GET /api/v1/activity/{id}` → 단일 객체
3. **streams**: `GET /api/v1/activity/{id}/streams` → 객체
4. **wellness**: `GET /api/v1/athlete/{id}/wellness?oldest=&newest=` → 배열

```python
class IntervalsExtractor(BaseExtractor):
    
    SOURCE = "intervals"
    
    def extract_activity_core(self, raw: dict) -> dict:
        
        avg_speed = raw.get("average_speed") or raw.get("icu_average_speed")
        avg_pace = round(1000.0 / avg_speed, 2) if avg_speed and avg_speed > 0 else None
        
        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("id", "")),
            "name": raw.get("name"),
            "activity_type": normalize_activity_type(
                raw.get("type", "unknown"), self.SOURCE
            ),
            "start_time": raw.get("start_date_local") or raw.get("start_date"),
            
            "distance_m": raw.get("distance"),
            "duration_sec": raw.get("elapsed_time") or raw.get("moving_time"),
            "moving_time_sec": raw.get("moving_time"),
            "elapsed_time_sec": raw.get("elapsed_time"),
            
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("max_speed"),
            "avg_pace_sec_km": avg_pace,
            
            "avg_hr": _int(raw.get("average_heartrate")),
            "max_hr": _int(raw.get("max_heartrate")),
            
            "avg_cadence": _int(raw.get("average_cadence")),
            "max_cadence": _int(raw.get("max_cadence")),
            
            "avg_power": raw.get("icu_average_watts") or raw.get("average_watts"),
            "max_power": raw.get("max_watts"),
            "normalized_power": raw.get("icu_weighted_avg_watts"),
            
            "elevation_gain": raw.get("total_elevation_gain"),
            "elevation_loss": raw.get("total_elevation_loss"),
            
            "calories": _int(raw.get("calories") or raw.get("icu_calories")),
            
            "training_load": raw.get("icu_training_load"),
            
            "avg_stride_length_cm": _stride_to_cm(raw.get("average_stride")),
            
            "description": raw.get("description"),
            "event_type": raw.get("sub_type"),
            "source_url": f"https://intervals.icu/activities/{raw.get('id')}",
        }
        
        return {k: v for k, v in core.items() if v is not None}
    
    
    def extract_activity_metrics(self, summary_raw: dict,
                                  detail_raw: dict = None) -> list[MetricRecord]:
        
        raw = detail_raw or summary_raw
        
        metrics = self._collect(
            # ── Training Load ──
            self._metric("trimp", raw.get("icu_trimp") or raw.get("trimp"),
                         category="training_load", raw_name="icu_trimp"),
            self._metric("hrss", raw.get("icu_hrss"),
                         category="training_load", raw_name="icu_hrss"),
            self._metric("strain_score", raw.get("strain_score"),
                         category="training_load", raw_name="strain_score"),
            self._metric("pace_load", raw.get("pace_load"),
                         category="training_load", raw_name="pace_load"),
            self._metric("hr_load", raw.get("hr_load"),
                         category="training_load", raw_name="hr_load"),
            self._metric("power_load", raw.get("power_load"),
                         category="training_load", raw_name="power_load"),
            
            # ── Efficiency ──
            self._metric("efficiency_factor",
                         raw.get("icu_efficiency_factor") or raw.get("icu_power_hr"),
                         category="efficiency", raw_name="icu_efficiency_factor"),
            self._metric("decoupling", raw.get("icu_decoupling"),
                         category="efficiency", raw_name="icu_decoupling"),
            self._metric("variability_index", raw.get("icu_variability_index"),
                         category="efficiency", raw_name="icu_variability_index"),
            self._metric("gap", raw.get("gap"),
                         category="efficiency", raw_name="gap"),
            self._metric("coasting_time", raw.get("coasting_time"),
                         category="general", raw_name="coasting_time"),
            
            # ── Fitness ──
            self._metric("ftp", raw.get("icu_ftp") or raw.get("icu_pm_ftp"),
                         category="fitness", raw_name="icu_ftp"),
            self._metric("threshold_pace", raw.get("threshold_pace"),
                         category="fitness", raw_name="threshold_pace"),
            
            # ── RPE/Feel ──
            self._metric("perceived_exertion", raw.get("icu_rpe"),
                         category="general", raw_name="icu_rpe"),
            self._metric("icu_feel", raw.get("icu_feel"),
                         category="general", raw_name="icu_feel"),
            
            # ── PMC snapshot ──
            self._metric("ctl_at_activity", raw.get("icu_ctl"),
                         category="fitness", raw_name="icu_ctl"),
            self._metric("atl_at_activity", raw.get("icu_atl"),
                         category="fitness", raw_name="icu_atl"),
        )
        
        # ── HR Zones ──
        hr_zones = raw.get("icu_hr_zone_times")
        if hr_zones and isinstance(hr_zones, list):
            for i, secs in enumerate(hr_zones[:5]):
                if secs is not None:
                    r = self._metric(f"hr_zone_{i+1}_sec", secs,
                                     category="hr_zone", 
                                     raw_name=f"icu_hr_zone_times[{i}]")
                    if r:
                        metrics.append(r)
            metrics.append(self._metric(
                "hr_zones_detail", json_val=hr_zones,
                category="hr_zone", raw_name="icu_hr_zone_times"
            ))
        
        # ── Power Zones ──
        pz = raw.get("icu_zone_times") or raw.get("icu_power_zone_times")
        if pz and isinstance(pz, list):
            for i, secs in enumerate(pz[:7]):
                if secs is not None:
                    r = self._metric(f"power_zone_{i+1}_sec", secs,
                                     category="power_zone",
                                     raw_name=f"icu_zone_times[{i}]")
                    if r:
                        metrics.append(r)
            metrics.append(self._metric(
                "power_zones_detail", json_val=pz,
                category="power_zone", raw_name="icu_zone_times"
            ))
        
        # ── Pace Zones ──
        gap_zones = raw.get("gap_zone_times")
        if gap_zones:
            metrics.append(self._metric(
                "pace_zone_times", json_val=gap_zones,
                category="pace_zone", raw_name="gap_zone_times"
            ))
        
        # ── Interval Summary ──
        intervals = raw.get("icu_intervals")
        if intervals:
            metrics.append(self._metric(
                "interval_summary", json_val=intervals,
                category="general", raw_name="icu_intervals"
            ))
        
        return [m for m in metrics if m is not None]
    
    
    def extract_activity_laps(self, detail_raw: dict) -> list[dict]:
        """Intervals.icu 랩 데이터"""
        laps_raw = detail_raw.get("icu_laps") or detail_raw.get("laps") or []
        laps = []
        for i, lap in enumerate(laps_raw):
            avg_speed = lap.get("average_speed")
            lap_dict = {
                "source": self.SOURCE,
                "lap_index": i,
                "start_time": lap.get("start_date") or lap.get("start_date_local"),
                "duration_sec": lap.get("elapsed_time") or lap.get("moving_time"),
                "distance_m": lap.get("distance"),
                "avg_hr": _int(lap.get("average_heartrate")),
                "max_hr": _int(lap.get("max_heartrate")),
                "avg_pace_sec_km": round(1000.0 / avg_speed, 2) if avg_speed and avg_speed > 0 else None,
                "avg_cadence": _int(lap.get("average_cadence")),
                "avg_power": lap.get("average_watts"),
                "max_power": lap.get("max_watts"),
                "elevation_gain": lap.get("total_elevation_gain"),
            }
            laps.append({k: v for k, v in lap_dict.items() if v is not None})
        return laps
    
    
    def extract_activity_streams(self, streams_raw: dict | list) -> list[dict]:
        """Intervals.icu streams → activity_streams"""
        if isinstance(streams_raw, dict):
            time_data = streams_raw.get("time", {}).get("data", [])
            if not time_data:
                return []
            
            rows = []
            for i, t in enumerate(time_data):
                row = {
                    "source": self.SOURCE,
                    "elapsed_sec": t,
                    "distance_m": _stream_val(streams_raw, "distance", i),
                    "heart_rate": _stream_val(streams_raw, "heartrate", i),
                    "cadence": _stream_val(streams_raw, "cadence", i),
                    "power_watts": _stream_val(streams_raw, "watts", i),
                    "altitude_m": _stream_val(streams_raw, "altitude", i),
                    "speed_ms": _stream_val(streams_raw, "velocity_smooth", i),
                    "latitude": _stream_val(streams_raw, "latlng", i, sub=0),
                    "longitude": _stream_val(streams_raw, "latlng", i, sub=1),
                    "grade_pct": _stream_val(streams_raw, "grade_smooth", i),
                }
                rows.append({k: v for k, v in row.items() if v is not None})
            return rows
        return []
    
    
    # ── Wellness ──
    
    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """Intervals wellness → daily_wellness"""
        w = raw_payloads.get("wellness_day", {})
        if not w:
            return {}
        
        core = {
            "resting_hr": _int(w.get("restingHR")),
            "hrv_last_night": w.get("hrv"),
            "weight_kg": w.get("weight"),
            "sleep_duration_sec": _seconds(w.get("sleepTime")),
            "sleep_score": _int(w.get("sleepQuality")),
        }
        return {k: v for k, v in core.items() if v is not None}
    
    
    def extract_wellness_metrics(self, date: str, **raw_payloads) -> list[MetricRecord]:
        w = raw_payloads.get("wellness_day", {})
        if not w:
            return []
        
        return self._collect(
            self._metric("hrv_sdnn", w.get("hrv"), category="hrv", raw_name="hrv"),
            self._metric("avg_sleeping_hr", w.get("avgSleepingHR"),
                         category="sleep", raw_name="avgSleepingHR"),
            self._metric("fatigue", w.get("fatigue"), category="recovery", raw_name="fatigue"),
            self._metric("mood", w.get("mood"), category="recovery", raw_name="mood"),
            self._metric("motivation", w.get("motivation"),
                         category="recovery", raw_name="motivation"),
            self._metric("readiness", w.get("readiness"),
                         category="readiness", raw_name="readiness"),
            self._metric("icu_rpe", w.get("rpe"), category="general", raw_name="rpe"),
            self._metric("basal_calories", w.get("basalCalories"),
                         category="general", raw_name="basalCalories"),
        )
    
    
    def extract_fitness(self, date: str, raw: dict) -> dict:
        """Intervals wellness에는 CTL/ATL/TSB가 직접 포함됨"""
        fitness = {
            "source": self.SOURCE,
            "date": date,
            "ctl": raw.get("ctl"),
            "atl": raw.get("atl"),
            "ramp_rate": raw.get("rampRate"),
        }
        # TSB = CTL - ATL
        if fitness.get("ctl") is not None and fitness.get("atl") is not None:
            fitness["tsb"] = round(fitness["ctl"] - fitness["atl"], 2)
        
        return {k: v for k, v in fitness.items() if v is not None}


def _stream_val(streams: dict, key: str, idx: int, sub: int = None):
    """Intervals stream dict에서 안전하게 값 추출"""
    stream = streams.get(key, {})
    data = stream.get("data", []) if isinstance(stream, dict) else []
    if idx >= len(data):
        return None
    val = data[idx]
    if sub is not None and isinstance(val, (list, tuple)):
        return val[sub] if sub < len(val) else None
    return val
```

---

## 2-6. `runalyze_extractor.py`

Runalyze는 가장 제한적인 API이지만, VO2Max 계산과 레이스 예측에 특화되어 있습니다.

```python
class RunalyzeExtractor(BaseExtractor):
    
    SOURCE = "runalyze"
    
    def extract_activity_core(self, raw: dict) -> dict:
        
        duration = raw.get("duration") or raw.get("s")  # Runalyze는 's' 키 사용 가능
        distance = raw.get("distance") or raw.get("km")
        
        # Runalyze distance가 km 단위일 수 있음
        distance_m = None
        if distance is not None:
            distance_m = float(distance) * 1000 if float(distance) < 1000 else float(distance)
        
        avg_speed = None
        avg_pace = None
        if distance_m and duration and float(duration) > 0:
            avg_speed = distance_m / float(duration)
            avg_pace = round(1000.0 / avg_speed, 2)
        
        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("id", "")),
            "name": raw.get("title") or raw.get("name"),
            "activity_type": normalize_activity_type(
                raw.get("sport", {}).get("name", "unknown") if isinstance(raw.get("sport"), dict)
                else raw.get("type", "unknown"),
                self.SOURCE
            ),
            "start_time": raw.get("datetime") or raw.get("start_time"),
            
            "distance_m": distance_m,
            "duration_sec": _int(duration),
            
            "avg_speed_ms": avg_speed,
            "avg_pace_sec_km": avg_pace,
            
            "avg_hr": _int(raw.get("heartrate") or raw.get("avg_heart_rate") or raw.get("pulse_avg")),
            "max_hr": _int(raw.get("heartrate_max") or raw.get("max_heart_rate") or raw.get("pulse_max")),
            
            "avg_cadence": _int(raw.get("cadence")),
            
            "avg_power": raw.get("power"),
            
            "elevation_gain": raw.get("elevation") or raw.get("total_ascent"),
            
            "calories": _int(raw.get("calories") or raw.get("kcal")),
            
            "avg_temperature": raw.get("temperature"),
            
            "description": raw.get("notes") or raw.get("description"),
        }
        
        return {k: v for k, v in core.items() if v is not None}
    
    
    def extract_activity_metrics(self, summary_raw: dict,
                                  detail_raw: dict = None) -> list[MetricRecord]:
        raw = detail_raw or summary_raw
        
        return self._collect(
            self._metric("effective_vo2max", raw.get("vo2max") or raw.get("effective_vo2max"),
                         category="fitness", raw_name="vo2max"),
            self._metric("trimp", raw.get("trimp"),
                         category="training_load", raw_name="trimp"),
            self._metric("perceived_exertion", raw.get("rpe"),
                         category="general", raw_name="rpe"),
            self._metric("marathon_shape", raw.get("marathonShape"),
                         category="fitness", raw_name="marathonShape"),
            
            # Runalyze 레이스 예측
            self._metric("race_prediction",
                         json_val=raw.get("raceResult") or raw.get("race_predictions"),
                         category="prediction", raw_name="raceResult"),
            
            # GCT balance (Runalyze에서 제공 시)
            self._metric("ground_contact_balance", raw.get("groundcontact_balance"),
                         category="running_dynamics", raw_name="groundcontact_balance"),
        )
```

---

## 2-7. Extractor 팩토리

```python
# src/sync/extractors/__init__.py

from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.strava_extractor import StravaExtractor
from src.sync.extractors.intervals_extractor import IntervalsExtractor
from src.sync.extractors.runalyze_extractor import RunalyzeExtractor
from src.sync.extractors.base import BaseExtractor


_EXTRACTORS = {
    "garmin": GarminExtractor,
    "strava": StravaExtractor,
    "intervals": IntervalsExtractor,
    "runalyze": RunalyzeExtractor,
}

def get_extractor(source: str) -> BaseExtractor:
    """소스명으로 extractor 인스턴스 반환"""
    cls = _EXTRACTORS.get(source)
    if cls is None:
        raise ValueError(f"Unknown source: {source}. Available: {list(_EXTRACTORS.keys())}")
    return cls()

def get_all_extractors() -> dict[str, BaseExtractor]:
    """모든 extractor 인스턴스 반환"""
    return {name: cls() for name, cls in _EXTRACTORS.items()}
```

---

## 2-8. 테스트 전략

### Fixture 수집 방법

실제 API 응답을 익명화하여 fixture로 만듭니다.

```python
# scripts/capture_fixture.py (개발용, 커밋하지 않음)

def capture_garmin_fixture(api, activity_id):
    """실제 Garmin API 호출 → 익명화 → fixture JSON 저장"""
    summary = api.get_activity(activity_id)
    detail = api.get_activity_details(activity_id)
    
    # 익명화
    summary = anonymize(summary)
    detail = anonymize(detail)
    
    with open(f"tests/fixtures/garmin/activity_{activity_id}.json", "w") as f:
        json.dump({"summary": summary, "detail": detail}, f, indent=2)

def anonymize(data: dict) -> dict:
    """PII 제거: 이름, 이메일, GPS 좌표 오프셋, 디바이스 시리얼 등"""
    data = copy.deepcopy(data)
    # GPS 오프셋 (실제 위치 숨기기)
    if "startLatitude" in data:
        data["startLatitude"] = 37.5665 + random.uniform(-0.01, 0.01)
        data["startLongitude"] = 126.9780 + random.uniform(-0.01, 0.01)
    # 이름 변경
    if "activityName" in data:
        data["activityName"] = "Test Activity"
    # ...
    return data
```

### Fixture 파일 구조

```
tests/
├── fixtures/
│   ├── garmin/
│   │   ├── activity_easy_run.json          # 쉬운 달리기
│   │   ├── activity_interval.json          # 인터벌 훈련
│   │   ├── activity_long_run.json          # 장거리 달리기
│   │   ├── activity_no_hr.json             # HR 없는 활동
│   │   ├── activity_treadmill.json         # 트레드밀 (GPS 없음)
│   │   ├── wellness_sleep.json             # 수면 데이터
│   │   ├── wellness_hrv.json               # HRV 데이터
│   │   ├── wellness_stress.json            # 스트레스 데이터
│   │   ├── wellness_body_battery.json      # Body Battery
│   │   ├── wellness_training_readiness.json # Training Readiness
│   │   └── wellness_user_summary.json      # User Summary
│   ├── strava/
│   │   ├── activity_run.json
│   │   ├── activity_with_segments.json
│   │   ├── streams_full.json               # 모든 스트림 포함
│   │   └── streams_minimal.json            # HR만 있는 스트림
│   ├── intervals/
│   │   ├── activity_with_zones.json
│   │   ├── activity_with_intervals.json
│   │   ├── wellness_day.json
│   │   └── streams.json
│   └── runalyze/
│       ├── activity_basic.json
│       └── activity_with_vo2max.json
```

### 테스트 코드 구조

```python
# tests/test_garmin_extractor.py

import pytest
import json
from src.sync.extractors.garmin_extractor import GarminExtractor

@pytest.fixture
def extractor():
    return GarminExtractor()

@pytest.fixture
def easy_run_raw():
    with open("tests/fixtures/garmin/activity_easy_run.json") as f:
        return json.load(f)


class TestExtractActivityCore:
    
    def test_required_fields_present(self, extractor, easy_run_raw):
        """source, source_id, activity_type, start_time 필수 존재"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        assert core["source"] == "garmin"
        assert "source_id" in core
        assert "activity_type" in core
        assert "start_time" in core
    
    def test_distance_in_meters(self, extractor, easy_run_raw):
        """distance_m가 미터 단위인지 확인 (10km 달리기 → ~10000)"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        assert 5000 < core["distance_m"] < 50000  # 합리적 범위
    
    def test_pace_calculated_from_speed(self, extractor, easy_run_raw):
        """avg_speed_ms가 있으면 avg_pace_sec_km이 계산되어야 함"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        if core.get("avg_speed_ms"):
            assert "avg_pace_sec_km" in core
            expected_pace = 1000.0 / core["avg_speed_ms"]
            assert abs(core["avg_pace_sec_km"] - expected_pace) < 0.1
    
    def test_none_values_excluded(self, extractor, easy_run_raw):
        """None인 값은 dict에 포함되지 않아야 함"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        for v in core.values():
            assert v is not None
    
    def test_training_effect_present_for_garmin(self, extractor, easy_run_raw):
        """Garmin 활동에는 training_effect가 있어야 함 (fixture에 포함된 경우)"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        # fixture에 따라 있을 수도 없을 수도 있으므로, 있다면 범위 검증
        te = core.get("training_effect_aerobic")
        if te is not None:
            assert 0.0 <= te <= 5.0
    
    def test_running_dynamics_in_cm(self, extractor, easy_run_raw):
        """stride_length가 cm 단위로 변환되었는지"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        stride = core.get("avg_stride_length_cm")
        if stride is not None:
            assert 50 < stride < 200  # 합리적 범위: 50~200cm
    
    def test_source_url_format(self, extractor, easy_run_raw):
        """source_url이 올바른 Garmin Connect URL인지"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        assert core.get("source_url", "").startswith("https://connect.garmin.com/modern/activity/")
    
    def test_activity_type_normalized(self, extractor, easy_run_raw):
        """activity_type이 정규화되었는지 (raw 값이 아닌)"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        valid_types = {"running", "trail_running", "treadmill", "cycling", "swimming",
                       "walking", "hiking", "strength", "other"}
        assert core["activity_type"] in valid_types


class TestExtractActivityMetrics:
    
    def test_no_overlap_with_core(self, extractor, easy_run_raw):
        """metric_store에 들어가는 값이 activity_summaries 컬럼과 겹치지 않아야 함"""
        core = extractor.extract_activity_core(easy_run_raw["summary"])
        metrics = extractor.extract_activity_metrics(
            easy_run_raw["summary"],
            easy_run_raw.get("detail")
        )
        
        core_keys = set(core.keys())
        # metric_name이 activity_summaries 컬럼명과 겹치면 안 됨
        ACTIVITY_SUMMARY_COLUMNS = {
            "distance_m", "duration_sec", "avg_hr", "max_hr", "avg_cadence",
            "avg_speed_ms", "max_speed_ms", "avg_pace_sec_km", "calories",
            "elevation_gain", "elevation_loss", "avg_power", "max_power",
            "normalized_power", "training_effect_aerobic", "training_effect_anaerobic",
            "training_load", "suffer_score", "avg_ground_contact_time_ms",
            "avg_stride_length_cm", "avg_vertical_oscillation_cm", "avg_vertical_ratio_pct",
            "avg_temperature", "start_lat", "start_lon", "end_lat", "end_lon",
        }
        
        metric_names = {m.metric_name for m in metrics}
        overlap = metric_names & ACTIVITY_SUMMARY_COLUMNS
        assert overlap == set(), f"Overlap with core columns: {overlap}"
    
    def test_hr_zones_extracted(self, extractor, easy_run_raw):
        """상세 데이터가 있으면 HR zone이 추출되어야 함"""
        if not easy_run_raw.get("detail"):
            pytest.skip("No detail data in fixture")
        
        metrics = extractor.extract_activity_metrics(
            easy_run_raw["summary"], easy_run_raw["detail"]
        )
        zone_metrics = [m for m in metrics if m.category == "hr_zone"]
        assert len(zone_metrics) > 0
    
    def test_metric_category_always_set(self, extractor, easy_run_raw):
        """모든 MetricRecord에 category가 설정되어야 함"""
        metrics = extractor.extract_activity_metrics(
            easy_run_raw["summary"], easy_run_raw.get("detail")
        )
        for m in metrics:
            assert m.category is not None, f"metric {m.metric_name} has no category"
            assert m.category != "", f"metric {m.metric_name} has empty category"
    
    def test_no_empty_metrics(self, extractor, easy_run_raw):
        """빈 MetricRecord가 포함되지 않아야 함"""
        metrics = extractor.extract_activity_metrics(
            easy_run_raw["summary"], easy_run_raw.get("detail")
        )
        for m in metrics:
            assert not m.is_empty(), f"Empty metric: {m.metric_name}"


class TestExtractWellness:
    
    @pytest.fixture
    def wellness_payloads(self):
        payloads = {}
        for name in ("sleep", "hrv", "stress", "body_battery", "user_summary", "training_readiness"):
            path = f"tests/fixtures/garmin/wellness_{name}.json"
            try:
                with open(path) as f:
                    key = f"{name}_day" if name != "training_readiness" else name
                    payloads[key] = json.load(f)
            except FileNotFoundError:
                pass
        return payloads
    
    def test_wellness_core_fields(self, extractor, wellness_payloads):
        """daily_wellness 핵심 필드가 추출되는지"""
        core = extractor.extract_wellness_core("2026-04-01", **wellness_payloads)
        # sleep_score, hrv, body_battery 중 하나 이상은 있어야 함
        assert any(core.get(k) is not None for k in 
                   ("sleep_score", "hrv_last_night", "body_battery_high"))
    
    def test_wellness_metrics_categories(self, extractor, wellness_payloads):
        """wellness metric의 카테고리가 올바른지"""
        metrics = extractor.extract_wellness_metrics("2026-04-01", **wellness_payloads)
        valid_categories = {"sleep", "stress", "hrv", "recovery", "readiness",
                            "prediction", "general", "training_load", "fitness"}
        for m in metrics:
            assert m.category in valid_categories, \
                f"Invalid category '{m.category}' for {m.metric_name}"


# tests/test_strava_extractor.py — 동일 패턴
# tests/test_intervals_extractor.py — 동일 패턴
# tests/test_runalyze_extractor.py — 동일 패턴
```

### Cross-Extractor 통합 테스트

```python
# tests/test_extractors_cross.py

class TestCrossExtractorConsistency:
    """모든 extractor가 동일한 규약을 따르는지 검증"""
    
    @pytest.fixture(params=["garmin", "strava", "intervals", "runalyze"])
    def extractor_and_fixture(self, request):
        from src.sync.extractors import get_extractor
        ext = get_extractor(request.param)
        # 각 소스의 기본 fixture 로드
        fixture_path = f"tests/fixtures/{request.param}/activity_easy_run.json"
        try:
            with open(fixture_path) as f:
                raw = json.load(f)
        except FileNotFoundError:
            pytest.skip(f"No fixture for {request.param}")
        return ext, raw
    
    def test_core_always_has_required_fields(self, extractor_and_fixture):
        ext, raw = extractor_and_fixture
        summary = raw.get("summary", raw)
        core = ext.extract_activity_core(summary)
        assert "source" in core
        assert "source_id" in core
        assert "activity_type" in core
        assert "start_time" in core
    
    def test_distance_always_in_meters(self, extractor_and_fixture):
        ext, raw = extractor_and_fixture
        core = ext.extract_activity_core(raw.get("summary", raw))
        d = core.get("distance_m")
        if d is not None:
            assert d > 100, "distance_m seems too small — might be in km?"
            assert d < 500000, "distance_m seems too large"
    
    def test_metrics_have_no_none_values(self, extractor_and_fixture):
        ext, raw = extractor_and_fixture
        metrics = ext.extract_activity_metrics(raw.get("summary", raw), raw.get("detail"))
        for m in metrics:
            assert not m.is_empty()
    
    def test_source_field_matches_extractor(self, extractor_and_fixture):
        ext, raw = extractor_and_fixture
        core = ext.extract_activity_core(raw.get("summary", raw))
        assert core["source"] == ext.SOURCE
```

---

## 2-9. 미등록 필드 자동 수집 — `_extract_unmapped`

향후 Garmin API가 새 필드를 추가했을 때 놓치지 않기 위한 안전망입니다.

```python
# base.py에 추가

    def extract_unmapped_fields(self, raw: dict, known_keys: set) -> list[MetricRecord]:
        """raw JSON에서 이미 처리한 key를 제외한 나머지를 _unmapped로 저장
        
        이 함수는 선택적으로 호출합니다.
        개발 초기에 "어떤 필드를 놓치고 있는지" 발견하는 데 유용합니다.
        프로덕션에서는 비활성화할 수 있습니다.
        """
        unmapped = []
        for key, value in raw.items():
            if key in known_keys:
                continue
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                # 복합 타입은 JSON으로 저장
                r = self._metric(
                    f"{self.SOURCE}__{key}",
                    json_val=value,
                    category="_unmapped",
                    raw_name=key,
                )
            elif isinstance(value, (int, float)):
                r = self._metric(
                    f"{self.SOURCE}__{key}",
                    value=value,
                    category="_unmapped",
                    raw_name=key,
                )
            elif isinstance(value, str):
                r = self._metric(
                    f"{self.SOURCE}__{key}",
                    text=value,
                    category="_unmapped",
                    raw_name=key,
                )
            else:
                continue
            if r:
                unmapped.append(r)
        
        return unmapped
```

이것은 **개발 모드**에서만 활성화합니다. `config.json`에 `"capture_unmapped": true`를 두고, Orchestrator에서 이 플래그를 확인하여 호출 여부를 결정합니다.

---

## 2-10. Phase 2 산출물 & 작업 순서

| 순서 | 파일 | 작업 | 예상 시간 |
|------|------|------|----------|
| 1 | `src/sync/extractors/__init__.py` | 팩토리 함수, 패키지 설정 | 15분 |
| 2 | `src/sync/extractors/base.py` | BaseExtractor, MetricRecord, 헬퍼 | 1시간 |
| 3 | `src/sync/extractors/garmin_extractor.py` | Activity core/metrics, Wellness core/metrics, Laps | 3시간 |
| 4 | `src/sync/extractors/strava_extractor.py` | Activity core/metrics, Streams, Best efforts | 2시간 |
| 5 | `src/sync/extractors/intervals_extractor.py` | Activity core/metrics, Wellness, Fitness, Laps, Streams | 2시간 |
| 6 | `src/sync/extractors/runalyze_extractor.py` | Activity core/metrics | 1시간 |
| 7 | Fixture 수집 & 익명화 | 각 소스별 2~3개 fixture JSON 생성 | 2시간 |
| 8 | `tests/test_garmin_extractor.py` | Core/Metrics/Wellness 테스트 | 1.5시간 |
| 9 | `tests/test_strava_extractor.py` | Core/Metrics/Streams 테스트 | 1시간 |
| 10 | `tests/test_intervals_extractor.py` | Core/Metrics/Wellness/Streams 테스트 | 1시간 |
| 11 | `tests/test_runalyze_extractor.py` | Core/Metrics 테스트 | 30분 |
| 12 | `tests/test_extractors_cross.py` | Cross-extractor 일관성 테스트 | 1시간 |

**총 예상: ~16시간 (3~4 세션)**

---

## 2-11. Phase 2 완료 기준 (Definition of Done)

1. 4개 extractor 모듈이 모두 `BaseExtractor`를 상속
2. `get_extractor("garmin")` 등 팩토리 함수 정상 동작
3. 각 extractor의 `extract_activity_core()`가 `source`, `source_id`, `activity_type`, `start_time` 필수 반환
4. `extract_activity_core()` 반환 dict의 key가 모두 `activity_summaries` 컬럼명과 일치
5. `extract_activity_metrics()` 반환 MetricRecord의 `metric_name`이 `activity_summaries` 컬럼명과 겹치지 않음
6. 모든 MetricRecord에 `category`가 설정됨
7. `distance_m`가 미터 단위로 통일
8. `_seconds()` 헬퍼가 밀리초/초 자동 판별
9. fixture 기반 단위 테스트 전체 통과
10. Cross-extractor 일관성 테스트 통과
11. `pytest tests/test_*_extractor.py tests/test_extractors_cross.py` 전체 통과

---

## 2-12. 구현 결과 & 설계 대비 변경 로그 (2026-04-03)

### 변경 1: Strava `normalized_power` 매핑 위치 변경

**설계**: `extract_activity_metrics`에서 `weighted_average_watts` → `normalized_power` MetricRecord로 생성.

**문제**: `normalized_power`는 `activity_summaries` 컬럼에 이미 존재. 이중 저장 금지 원칙(`activity_summaries`에 있는 필드는 `metric_store`에 넣지 않음) 위배.

**구현**: `extract_activity_core`에서 `"normalized_power": raw.get("weighted_average_watts")`로 매핑. `extract_activity_metrics`에서는 해당 항목 제거.

**근거**: architecture.md Part 3 — "activity_summaries에 이미 저장된 값은 metric_store에 중복 저장하지 않는다."

### 변경 2: `get_extractor()` 팩토리 함수 추가

**설계**: `EXTRACTORS = {"garmin": GarminExtractor, ...}` dict만 정의.

**구현**: `__init__.py`에 `get_extractor(source: str) → BaseExtractor` 함수 추가. case-insensitive 처리, 미지원 소스 시 `KeyError` 발생. `__all__`에 export.

**근거**: DoD 조건 2 — `get_extractor("garmin")` 팩토리 함수 정상 동작 요구.

### 변경 3: `test_extractors_cross.py` 신규 파일 추가

**설계**: Phase 2 산출물 목록에 cross-extractor 테스트 파일 없음.

**구현**: `tests/test_extractors_cross.py` 작성 — 7개 테스트 클래스, 약 20+ 테스트 케이스.

**근거**: DoD 조건 10, 11 — cross-extractor 일관성 테스트 통과 요구.

### 변경 4: `src/utils/activity_types.py` 추가

**설계**: 설계서에서 `normalize_activity_type(type_key, source)`를 사용하나, 별도 모듈로 분리하는 것은 명시하지 않음.

**구현**: `src/utils/activity_types.py`에 5개 운동 유형(running, cycling, swimming, walking, strength), 소스별 매핑(_STRAVA_MAP, _INTERVALS_MAP), `normalize_activity_type()` 함수 구현.

**근거**: 4개 extractor 모두에서 공통 사용하므로 모듈 분리가 적절.

### 최종 파일 구조

    src/sync/extractors/
    ├── __init__.py              # EXTRACTORS dict + get_extractor()
    ├── base.py                  # MetricRecord + BaseExtractor
    ├── garmin_extractor.py      # GarminExtractor (activity + wellness + fitness)
    ├── strava_extractor.py      # StravaExtractor (activity + streams + best_efforts)
    ├── intervals_extractor.py   # IntervalsExtractor (activity + wellness + fitness)
    └── runalyze_extractor.py    # RunalyzeExtractor (activity + fitness)

    src/utils/
    ├── activity_types.py        # normalize_activity_type()
    ├── metric_registry.py       # Phase 1
    ├── metric_priority.py       # Phase 1
    └── db_helpers.py            # Phase 1

    tests/
    ├── test_extractor_base.py
    ├── test_garmin_extractor.py
    ├── test_strava_extractor.py
    ├── test_intervals_extractor.py
    ├── test_runalyze_extractor.py
    ├── test_activity_types.py
    ├── test_extractors_cross.py
    └── fixtures/api/
        ├── garmin/   (3 files)
        ├── strava/   (1 file)
        ├── intervals/ (2 files)
        └── runalyze/  (1 file)