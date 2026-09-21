"""AI Function Calling 도구 선언 — Gemini function_declarations 형식.

실행기는 tool_exec_activity / tool_exec_context, 디스패치는 tools.py.
"""
from __future__ import annotations

TOOL_DECLARATIONS = [
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
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_metrics",
        "description": "특정 날짜의 2차 메트릭(UTRS, CIRS, ACWR, DI 등)을 조회한다.",
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
                "metric_name": {"type": "string", "description": "메트릭 이름 (UTRS, CIRS, ACWR 등)"},
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
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
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_fitness",
        "description": "CTL(만성훈련부하), ATL(급성훈련부하), TSB(신선도), VO2Max 추세를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
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
                "period_a_start": {"type": "string", "description": "기간A 시작일"},
                "period_a_end": {"type": "string", "description": "기간A 종료일"},
                "period_b_start": {"type": "string", "description": "기간B 시작일"},
                "period_b_end": {"type": "string", "description": "기간B 종료일"},
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
            "특정 활동의 랩(세트)별 기록을 조회한다. 거리·페이스·심박·케이던스·파워와 "
            "랩 종류(WARMUP/ACTIVE/RECOVERY/COOLDOWN/INTERVAL)를 반환한다. "
            "인터벌·크루즈 세션의 세트별 수행을 볼 때 사용. activity_id는 "
            "get_activity 또는 get_activities_range 결과에 포함된다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "integer", "description": "활동 ID"},
                "lap_type": {
                    "type": "string",
                    "description": (
                        "특정 랩 종류만 필터 (ACTIVE=작업 구간, RECOVERY=회복, "
                        "WARMUP, COOLDOWN, INTERVAL=자동 1km랩). 생략 시 전체."
                    ),
                },
            },
            "required": ["activity_id"]
        }
    },
    {
        "name": "compare_workout_sets",
        "description": (
            "구조화 워크아웃(ACTIVE 랩이 있는 세션)의 작업 구간을 세션 간 비교한다. "
            "세션별 세트 수, 세트 페이스 목록, 평균/최고/최저, 첫→마지막 세트 드리프트를 "
            "반환한다. '지난 크루즈 세션들과 비교' 같은 질문에 사용."
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
        "description": "특정 날짜(또는 기간)의 날씨 데이터를 조회한다. 기온, 체감온도, 습도, 풍속, 강수량, 운량.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "조회 날짜 YYYY-MM-DD"},
                "to_date": {"type": "string", "description": "종료 날짜 YYYY-MM-DD (선택, 기간 조회 시)"}
            },
            "required": ["date"]
        }
    },

]
