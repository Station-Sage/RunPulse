# src/ai/ — AI 코치 엔진 v2

Gemini Function Calling 기반 AI 코치. 의도 감지 + 10개 도구 + AJAX 실시간 채팅.

## 파일 구조

| 파일 | 역할 | 줄수 |
|------|------|------|
| `chat_engine.py` | 채팅 오케스트레이터 — 의도 감지 + 도구 라우팅 + SSE 스트림 | 696 |
| `chat_context.py` | 전체 러너 컨텍스트 조립 (DB → 구조화 dict) | 932 |
| `context_builders.py` | 섹션별 컨텍스트 빌더 (활동/메트릭/목표/웰니스) | 397 |
| `tools.py` | Gemini Function Calling 도구 정의 10개 | 379 |
| `genspark_driver.py` | Genspark AI Chat HTTP 드라이버 (기본 AI 백엔드) | 384 |
| `ai_context.py` | 레거시 컨텍스트 빌더 (v0.1 호환) | 347 |
| `ai_message.py` | AI 메시지 포매터 + 파서 | 311 |
| `ai_parser.py` | AI 응답 파싱 (훈련 계획 추출) | 125 |
| `ai_validator.py` | AI 응답 검증 | 127 |
| `ai_schema.py` | AI 응답 스키마 정의 | — |
| `ai_cache.py` | AI 응답 캐시 (TTL 기반) | 152 |
| `briefing.py` | 일일 브리핑 생성 | — |
| `suggestions.py` | 추천 칩 생성 | 171 |
| `prompt_config.py` | 프롬프트 설정 관리 | 244 |
| `prompt_templates/` | 프롬프트 템플릿 파일들 (`.txt`) | — |

## 아키텍처

```
웹 요청 → chat_engine.py
              ↓ 의도 감지
         [훈련계획 요청]  → context_builders.py → Gemini Function Calling
         [일반 질문]      → chat_context.py → genspark_driver.py
         [브리핑]         → briefing.py
              ↓ 응답
         ai_message.py → SSE 스트림 → 클라이언트
```

## 도구 10개 (tools.py)
1. `get_recent_activities` — 최근 활동 조회
2. `get_fitness_metrics` — PMC/CTL/ATL/TSB
3. `get_training_plan` — 현재 훈련 계획
4. `get_goal_info` — 목표 정보
5. `get_readiness` — 준비도 점수
6. `get_wellness_data` — 웰니스/HRV/수면
7. `generate_training_plan` — 훈련 계획 생성
8. `analyze_race_readiness` — 레이스 준비도 분석
9. `get_weather_forecast` — 날씨 예보
10. `get_injury_risk` — 부상 위험도

## AI 백엔드 교체
`genspark_driver.py` 인터페이스:
```python
def send_message(prompt: str, context: dict) -> str: ...
```
ChatGPT/Claude/DeepSeek로 교체 시 같은 인터페이스로 드라이버 교체

## 컨텍스트 조립 (chat_context.py)
`build_full_context(conn, config)` — 932줄의 메인 함수
- 최근 활동 7일/30일/90일
- PMC 시리즈 (CTL/ATL/TSB)
- 목표 + 훈련 계획
- 웰니스 (수면/HRV/스트레스)
- 메트릭 스냅샷 (UTRS/CIRS/VDOT/DARP)

## 캐시 전략 (ai_cache.py)
- TTL: 기본 300초 (5분)
- 키: `hash(prompt + context_fingerprint)`
- graceful fallback: 캐시 미스 시 그냥 API 호출
