---
name: runpulse-data
description: >
  RunPulse MCP 도구(get_training_summary, get_activity_laps 등)로 러닝 데이터를 조회·분석할 때의
  호출 레시피와 토큰 절약 규칙. "최근 훈련 어땠어", "이번 블록 리뷰", "인터벌 세트 비교",
  "CTL/TSB 추이", "주간 로그 작성용 데이터" 같은 요청에서 도구를 부르기 전에 참조한다.
user-invocable: false
---

# RunPulse 데이터 조회 레시피

목표는 **호출 횟수와 응답 크기를 최소화**하는 것이다. 호출 규칙 요약본은 MCP initialize의
`instructions`(`src/ai/tool_guide.py`)로도 전달되며, 이 문서는 그 상세판이다.

## 질문 → 호출

| 질문 유형 | 호출 | 비고 |
|---|---|---|
| 최근 N주 / 훈련 블록 / 대회 이후 | `get_training_summary(start,end)` **1회** | 주별 볼륨·페이스·심박, 주말 CTL/ATL/TSB, 대회·퀄리티 세션 id |
| 몸 상태(수면·HRV·바디배터리) | `get_wellness(start,end)` | 14일 이내 권장, 더 길면 주 평균 |
| 피트니스 추이 | `get_fitness(days)` | 62일 초과 시 주말 값 |
| 특정 날 러닝 | `get_activity(date)` | 메트릭·분류 포함 |
| 기간 활동 목록 | `get_activities_range(start,end)` | 62일 초과 시 주별 |
| 인터벌·크루즈 세트별 | `get_activity_laps(id)` | id는 요약 `notable` 또는 목록 `id` |
| 세션 간 세트 비교 | `compare_workout_sets(name_contains, limit)` | 세트 페이스·드리프트 |
| km 스플릿 / HR존 | `get_activity_detail(id)` | |
| 대회 이력 | `get_race_history` | |
| 특정 날 메트릭 / 추세 | `get_metrics(date)` / `get_metrics_trend(name,days)` | 62일 초과 시 주 평균 |
| 기간 비교 | `compare_periods` | |
| 계획 · 프로필 · 날씨 | `get_training_plan` / `get_runner_profile` / `get_weather` | |

**전형적 흐름**: `get_training_summary` → 궁금한 세션 id → `get_activity_laps(id)`.
날짜·id를 모른 채 `get_activities_range`를 넓게 훑지 않는다.

## 응답 형식

- 목록은 `{"fields":[...],"rows":[[...]]}` — 행은 `fields` 순서. 전 행이 NULL인 컬럼은 생략된다
  (예: 파워 센서 없는 기간은 `pwr` 컬럼 자체가 없음).
- `granularity`: `day`/`week`. `week`이면 `unit`에 주 시작 요일(기본 일요일 — 마라톤 플랜 주차와 동일)이 있고
  `week` 값은 그 주의 시작일. `week_start: "mon"`으로 월요일 시작 지정 가능.
- `note`가 있으면 요청한 단위가 상한(180일)을 넘어 주별로 바뀐 것.

## 알아둘 점

- 세션 유형(`type`)은 규칙 기반 분류라 크루즈·짧은 인터벌이 `easy`로 잡히기도 한다.
  `notable`의 `sets`(ACTIVE 랩 수)가 있으면 구조화 세션이므로 `type`보다 랩을 우선 신뢰한다.
- `get_training_summary`의 러닝은 `running`만 집계한다 (실내 러닝 `indoor_running`은 제외).
- 주별 페이스는 평균의 평균이 아니라 총시간/총거리, 심박은 시간 가중 평균이다.

## 응답 크기 (실측 2026-09-21, 문자수÷3 근사)

| 호출 | 이전 | 현재 |
|---|---|---|
| 활동 목록 1년 | ≈7,300 tok | ≈780 tok (주별) |
| 웰니스 30일 | ≈1,300 tok | ≈380 tok |
| 피트니스 30일 | ≈830 tok | ≈330 tok |
| 훈련 요약 1개월 | 4~5회 호출 필요 | ≈280 tok (1회) |
| 훈련 요약 1년 | | ≈1,270 tok |
| 랩 / 세트 비교 5건 | | ≈190 / ≈415 tok |
| 도구 선언 (세션당 1회) | ≈1,470 tok | ≈1,580 tok (15개) |

## 연결 (로컬 stdio, 읽기 전용)

프로젝트 `.mcp.json`(gitignore 대상)에 추가:

    "runpulse": {
      "command": "python3", "args": ["-m", "src.mcp_server"],
      "cwd": "/home/ubuntu/projects/RunPulse",
      "env": {"RUNPULSE_USER_ID": "pansongit@gmail.com"}
    }

`RUNPULSE_USER_ID`가 없으면 서버는 시작하지 않는다. 외부(원격) 접속은 미지원 — BACKLOG `MCP-REMOTE`.
