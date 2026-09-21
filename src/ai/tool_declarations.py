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
        "description": "CTL(만성훈련부하), ATL(급성훈련부하), TSB(신선도), VO2Max 추세를 조회한다.",
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

]
