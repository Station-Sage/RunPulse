"""AI Function Calling 도구 선언 — Gemini function_declarations 형식.

실행기는 tool_exec_activity / tool_exec_context, 디스패치는 tools.py.
"""
from __future__ import annotations

# 목록형 도구 공통 — 긴 기간은 주별 롤업으로 응답 크기를 제한한다
_GRANULARITY = {
    "type": "string",
    "enum": ["auto", "day", "week"],
    "description": "기본 auto(62일 초과 시 주별). day는 180일까지.",
}

TOOL_DECLARATIONS = [
    {
        "name": "get_training_summary",
        "description": (
            "기간 훈련 요약 1회 반환: 주별 거리·페이스·심박·주말 CTL/ATL/TSB, "
            "대회·퀄리티 세션(id 포함). 훈련 기간 질문의 첫 호출."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                "week_start": {"type": "string", "enum": ["sun", "mon"],
                               "description": "주 시작 요일 (기본 sun)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_activity",
        "description": "특정 날짜의 러닝 활동 상세 데이터를 조회한다. 거리, 페이스, 심박, 메트릭, 운동 분류 포함.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "조회할 날짜 (YYYY-MM-DD)"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_activities_range",
        "description": "기간 내 러닝 활동 목록을 조회한다. 날짜별 거리, 페이스, 심박 요약.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                "granularity": _GRANULARITY
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_metrics",
        "description": "특정 날짜의 2차 메트릭(utrs, cirs, acwr, di 등, 이름은 소문자)을 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "날짜 (YYYY-MM-DD)"},
                "metric_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "조회할 메트릭 이름 목록. 비어있으면 전체 조회.",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_metrics_trend",
        "description": "메트릭의 기간별 추세를 조회한다. 시계열 데이터 반환.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "메트릭 이름 (소문자: utrs, cirs, acwr 등)"},
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
                "granularity": _GRANULARITY
            },
            "required": ["metric_name"],
        },
    },
    {
        "name": "get_wellness",
        "description": "기간 내 웰니스 데이터를 조회한다. 바디배터리, 수면, HRV, 스트레스, 안정심박.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                "granularity": _GRANULARITY
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_fitness",
        "description": "CTL(만성훈련부하), ATL(급성훈련부하), TSB(폼), VO2Max 추세를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
                "granularity": _GRANULARITY
            },
            "required": [],
        },
    },
    {
        "name": "get_race_history",
        "description": "레이스(대회) 활동 이력을 조회한다. 거리, 완주 시간, 페이스 포함.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "최대 결과 수 (기본 10)"},
            },
            "required": [],
        },
    },
    {
        "name": "compare_periods",
        "description": "두 기간의 훈련 데이터를 비교한다. 볼륨, 메트릭, 페이스 등.",
        "parameters": {
            "type": "object",
            "properties": {
                "period_a_start": {"type": "string"},
                "period_a_end": {"type": "string"},
                "period_b_start": {"type": "string"},
                "period_b_end": {"type": "string"},
            },
            "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"],
        },
    },
    {
        "name": "get_training_plan",
        "description": "훈련 계획을 조회한다. 이번 주 또는 특정 주의 계획.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_offset": {"type": "integer", "description": "0=이번주, 1=다음주, -1=지난주"},
            },
            "required": [],
        },
    },
    {
        "name": "get_runner_profile",
        "description": "러너의 전체 프로필 요약. 주간 평균, VO2Max, 목표, 수준.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_activity_detail",
        "description": "특정 활동의 km별 스플릿(페이스·심박·케이던스·파워), 랩 데이터, HR zone 비율을 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "integer", "description": "활동 ID"}
            },
            "required": ["activity_id"]
        }
    },
    {
        "name": "get_activity_laps",
        "description": (
            "활동의 랩(세트)별 거리·페이스·심박·케이던스·파워·랩 종류를 조회한다. "
            "인터벌·크루즈 세트별 수행 확인용. id는 요약/목록 결과에 있다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "integer", "description": "활동 ID"},
                "lap_type": {
                    "type": "string",
                    "description": "랩 종류 필터: ACTIVE(작업)|RECOVERY|WARMUP|COOLDOWN|INTERVAL(자동1km). 생략=전체",
                },
            },
            "required": ["activity_id"]
        }
    },
    {
        "name": "compare_workout_sets",
        "description": (
            "ACTIVE 랩이 있는 구조화 워크아웃의 작업 구간을 세션 간 비교한다. "
            "세트 수·세트 페이스·평균/최고/최저·첫→마지막 드리프트. '지난 크루즈들과 비교'용."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name_contains": {"type": "string", "description": "워크아웃 이름 부분 일치 (예: '크루즈', '템포')"},
                "start_date": {"type": "string", "description": "시작일 YYYY-MM-DD (선택)"},
                "end_date": {"type": "string", "description": "종료일 YYYY-MM-DD (선택)"},
                "limit": {"type": "integer", "description": "최근 N개 세션 (기본 5)"},
            },
            "required": []
        }
    },
    {
        "name": "get_weather",
        "description": "특정 날짜(또는 기간)의 시간별 날씨를 조회한다. 기온, 습도, 풍속, 운량, 날씨 상태.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "조회 날짜 YYYY-MM-DD"},
                "to_date": {"type": "string", "description": "종료 날짜 YYYY-MM-DD (선택, 기간 조회 시)"}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_plan_adherence",
        "description": "주별 훈련 계획 이행(세션 완료/전체, 볼륨 실제/계획, 퀄리티)과 세션별 계획 대비 결과. 최근 N주(기본 4, 최대 8).",
        "parameters": {
            "type": "object",
            "properties": {"weeks": {"type": "integer", "description": "기본 4, 최대 8"}}
        }
    },
    {
        "name": "get_plan_constraints",
        "description": "훈련 계획 초안이 지켜야 할 제약: 운동·휴식·롱런 요일, 차단 날짜, Q일 상한, 세션 최소·주간 증가율·롱런 상한 등 게이트 한계값.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_wellness_series",
        "description": "웰니스 시계열의 일별 요약(평균·최소·최대)과 7/28일 기준선. kind 생략 시 존재하는 kind 목록. 최대 120일.",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string"}, "days": {"type": "integer"},
            "date_from": {"type": "string"}, "date_to": {"type": "string"}}}
    },
    {
        "name": "get_insights",
        "description": "능동 인사이트 사건(부하 급증·회복 저하·통증·데이터 공백). 기본 열린 것 최대 10건.",
        "parameters": {"type": "object", "properties": {
            "state": {"type": "string", "description": "open(기본)/dismissed/resolved"}, "limit": {"type": "integer"}}}
    },
    {
        "name": "get_checkins",
        "description": "체크인(피로·통증·기분)과 활동 피드백(RPE·통증). 최대 28일.",
        "parameters": {"type": "object", "properties": {
            "days": {"type": "integer"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}}}
    },
    {
        "name": "get_predictions",
        "description": "최근 레이스 예측 스냅샷, 거리별 베스트 에포트, 대회 기록.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}}
    },
]

# 로컬 stdio(MCP)·워커 전용 — 챗 LLM 고정 비용(예산)과 원격 노출에서 제외.
LOCAL_TOOL_DECLARATIONS = [
    {
        "name": "get_activity_stream",
        "description": "활동 스트림 채널(heart_rate/cadence/power_watts/altitude_m/speed_ms/grade_pct)을 30초로 리샘플한 최대 300점과 통계. from_sec/to_sec 로 구간 지정.",
        "parameters": {"type": "object", "properties": {
            "activity_id": {"type": "integer"}, "channel": {"type": "string"},
            "from_sec": {"type": "integer"}, "to_sec": {"type": "integer"}, "resample_sec": {"type": "integer"}},
            "required": ["activity_id"]}
    },
    {
        "name": "list_raw_payloads",
        "description": "수집된 외부 API 원본(JSON) 목록. source·entity_type·entity_id·activity_id·기간으로 좁힌다. 본문은 get_raw_payload.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "garmin / strava / intervals / runalyze 등"},
                "entity_type": {"type": "string", "description": "activity_detail / wellness_day 등"},
                "entity_id": {"type": "string"},
                "activity_id": {"type": "integer", "description": "activity_summaries.id"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                "limit": {"type": "integer", "description": "기본 20, 최대 50"}
            }
        }
    },
    {
        "name": "get_raw_payload",
        "description": "원본 payload 한 건. 길면 잘리므로 path(점 구분, 예: summaryDTO.hrTimeInZones.0)로 하위만 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "list_raw_payloads 의 id"},
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "description": "기본 6000, 최대 20000"}
            },
            "required": ["id"]
        }
    },
]
