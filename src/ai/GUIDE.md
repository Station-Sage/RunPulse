# src/ai/ GUIDE — AI 코치 엔진 v2

## 구조
```
웹 요청 → chat_engine.py (의도 감지 + 도구 라우팅)
              ↓
         [훈련 요청]  → context_builders.py → Gemini Function Calling
         [일반 질문]  → chat_context*.py → genspark_driver.py
         [브리핑]     → briefing.py
              ↓
         ai_message.py → SSE 스트림 → 클라이언트
```

## 파일 맵

### 채팅 엔진 (핵심)
| 파일 | 역할 |
|------|------|
| `chat_engine.py` | 오케스트레이터 — 코어 chat 함수 + 시스템 프롬프트 + provider chain |
| `chat_engine_providers.py` | 외부 API 호출 (Claude/OpenAI/Gemini/Groq/Genspark) |
| `chat_engine_rules.py` | 규칙 기반 fallback 응답 (키워드 매칭) |
| `chat_context.py` | 전체 러너 컨텍스트 조립 메인 |
| `chat_context_builders.py` | 섹션별 컨텍스트 빌더 |
| `chat_context_format.py` | 컨텍스트 포매터 |
| `chat_context_intent.py` | 의도 감지 로직 |
| `chat_context_rich.py` | 리치 컨텍스트 빌더 |
| `chat_context_utils.py` | 컨텍스트 유틸 |
| `context_builders.py` | 훈련/메트릭/목표/웰니스 빌더 |
| `tools.py` | Gemini Function Calling 도구 정의 10개 |

### AI 백엔드
| 파일 | 역할 |
|------|------|
| `genspark_driver.py` | Genspark AI Chat HTTP 드라이버 (기본 백엔드) |
| `ai_cache.py` | AI 응답 캐시 (TTL 300초) |
| `prompt_config.py` | 프롬프트 설정 관리 |
| `prompt_templates/` | 10종 프롬프트 템플릿 (`.txt`) |

### 메시지/파싱
| 파일 | 역할 |
|------|------|
| `ai_message.py` | 메시지 포매터 + 파서 |
| `ai_parser.py` | 훈련 계획 응답 파싱 |
| `ai_validator.py` | 응답 검증 |
| `ai_schema.py` | 응답 JSON 스키마 |

### 레거시/기타
| 파일 | 역할 |
|------|------|
| `ai_context.py` | 레거시 컨텍스트 빌더 (v0.1 호환) |
| `briefing.py` | 일일 브리핑 생성 |
| `suggestions.py` | 추천 칩 생성 |

## Function Calling 도구 10개
`get_recent_activities`, `get_fitness_metrics`, `get_training_plan`, `get_goal_info`, `get_readiness`, `get_wellness_data`, `generate_training_plan`, `analyze_race_readiness`, `get_weather_forecast`, `get_injury_risk`

## 규칙
1. AI 응답 파싱 실패 시 항상 graceful fallback (규칙 기반)
2. 프롬프트 템플릿은 `src/ai/prompt_templates/*.txt`에 분리 관리 (코드 내 하드코딩 금지)
3. 백엔드 교체: `genspark_driver.py`와 같은 인터페이스 (`send_message(prompt, context) -> str`)
4. 캐시: TTL 300초, 키는 `hash(prompt + context_fingerprint)`
5. 숫자 계산은 Python에서 수행. AI는 해석/서술/계획 생성에만 활용

## 주의사항 — 300줄 초과
없음 (REFAC-3 완료: chat_engine.py 207줄 + chat_engine_providers.py 248줄 + chat_engine_rules.py 259줄)

## 의존성
- `src/web/views_ai_coach.py` — 웹 라우트에서 호출
- `src/training/` — 훈련 계획 생성 시 참조
- `src/metrics/store.py` — 메트릭 데이터 조회
- `src/weather/provider.py` — 날씨 예보 도구
