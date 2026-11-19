# REVIEW-AI-WORDING — 기존 AI 문구 점검과 공통 계층 (2026-11-19)

목표(사용자 결정): AI 연결이 있으면 규칙 기반 사용자 문구를 AI 가 다듬는다. 이 문서는 1단계 결과 — 이미 있는 AI 문구 4종의
가치 판정, 이번에 고친 것, 공통 계층(`src/services/ai_wording.py`, ADR-059) 사용 규칙이다.

근거: 프롬프트(`src/ai/prompt_templates/*`)·검증 함수·호출 경로 정독. 비운영 DB(`data/synth_20users.db`, 개발용
`data/users/default`)에는 저장된 AI 출력이 0건이라 실제 출력 표본은 못 봤다 — 판정은 입력·지침·검증 기준이다.

## 1. 표면별 판정

| 표면 | AI 가 받는 것 | 규칙 문구 대비 더하는 것 | 판정 |
|---|---|---|---|
| metric_note (지표 행동 힌트) | 정적 힌트 문장뿐(57개, 사용자 데이터 없음) | 어조만. 새 정보·개인화 없음 | **drop 예정** — 2단계 지표 해석(값·추세·개인 기준선을 facts 로)으로 대체. 그전까지 유지(비용 작음) |
| today narrative (월 내러티브·warm) | CTL 월초→현재, 월 누적·횟수, 수면 7일 대비, 주별 요약 | 주별 흐름을 한 줄로 묶는 종합(규칙 문장은 주 정보를 못 씀) | **keep** |
| adherence review (지난주 리뷰) | 주 이행 수치·요일별 결과 | 요점 3개 + 다음 주 집중점(규칙 화면엔 없음) | **keep + 프롬프트 개선(적용)** |
| insight polish (능동 인사이트) | 규칙 문장 1개뿐 | 사실상 바꿔 말하기(4종 문장이 이미 해요체 1~2문장) | **improve** — 근거 신호(비건강)를 facts 로 함께 주면 "어떤 회복 신호가 낮은지"를 말할 수 있다. 2단계에서 공통 계층으로 옮기며 `polished` 를 프런트에 연결 |

비용: metric_note 사용자 DB 당 haiku 2회(힌트 문구가 바뀔 때만), insight polish 동기화당 최대 1회(새·바뀐 사건 있을 때),
narrative 하루 1회(상한 3), adherence 주 1회(sonnet, 입력 해시 같으면 재호출 없음). 전부 백그라운드라 화면 지연 0.
판정상 비용 대비 가치가 낮은 건 metric_note 뿐이고, 그마저 절대 비용이 작아 즉시 끌 이유는 없다.

## 2. 발견한 문제와 조치

적용(저위험, 검증·프롬프트만):
1. **metric_note 숫자 전면 금지 → 3건 상시 거부.** 원문에 수치가 있는 힌트(`acwr:layoff` 60~70%, 수면 6시간·7시간)는
   AI 가 숫자를 빼면 뜻이 바뀌고, 남기면 `\d` 검사로 거부됐다. 금지 검사를 없애고 "원문 수치 유지, 새 수치 금지"로 바꿈.
2. **반올림 거부.** 모든 검증이 문자열 완전 일치라 CTL 35.2 → "35", 12.35km → "12.4km" 를 환각으로 거부했다.
   `ai_wording.numbers_ok` 로 통일(근거 수치 또는 그 반올림 0·1자리만 허용) — insight polish·metric_note·narrative·adherence.
3. **adherence evidence_key 를 모델이 추측.** 프롬프트가 "입력의 evidence 키"라고만 하고 허용 키(`sessions`, `day:YYYY-MM-DD` …)를
   주지 않아 하나라도 틀리면 리뷰 전체가 버려졌다. 프롬프트에 허용 키 목록(`{{KEYS}}`)을 넣음.
4. **narrative 키 기반 provider 출력 미검증.** 큐 경로만 `validate_narrative` 를 거쳤고 Gemini/Groq 출력은 그대로 캐시됐다.
   같은 검증을 적용(실패 → 다음 provider → 규칙 문장).

미적용(사용자 결정 필요, §4):
- A. `GET /today/narrative`(요청 스레드)가 키가 설정돼 있으면 **동의 확인 없이** Gemini/Groq 를 동기 호출한다
  (`today_narrative` → `_build_chat_provider_chain`). 캐시만 읽는 원칙과 동의 원칙(ADR-055) 둘 다 어긋난다.
- B. insight polish·adherence 의 백그라운드 생성은 coach 동의를 보지 않는다(narrative warm 은 본다). 둘 다 사용자 수치를 보낸다.
- C. insight polish 의 큐 불가 시 경로(`polish_text`)도 동의 없이 키 기반 체인을 부른다.

## 3. 공통 계층 사용 규칙 (ADR-059)

```python
from src.services import ai_wording as aw
REASON = aw.register(aw.Surface(name="today_reason", guide="- 오늘 훈련을 왜 바꿨는지 한 문장으로.", max_chars=100))
# 요청 스레드 — 캐시만
view = aw.present(conn, REASON, scope_key=day, rule_text=rule, facts={"acwr": 1.52, "planned": "tempo"})
# → {"text": ..., "source": "ai"|"rule"}
# 동기화 뒤 백그라운드
aw.warm_in_background(db_path, config, REASON, collect=lambda c: [aw.Item(day, rule, facts)])
```

- 저장: `ai_outputs(kind='w:<name>', scope_key, src_hash)`. src_hash = (version, guide, max_chars, 원문, facts) — 하나라도 바뀌면 규칙 문구로.
- 생성 관문(`gate`): claude_queue 동의(`coach_consent.provider='claude_queue'`, 정적 문구 표면은 `needs_consent=False`) →
  전역 사용량 `warm_stop_ratio` 미만 → 큐 가용. 표면·DB 별 비차단 락. job kind 는 기존 haiku `insight_polish` 재사용(스키마 변경 없음).
- 검증: 숫자 ⊆ 근거(text+facts, id 제외, 반올림 허용), 길이, 마크다운, 표면별 금지어, 건강 용어 금지.
- 건강 익명화: 원문·facts 문자열의 건강 용어(질병·통증·부상·부위·진단) 문장은 AI 로 보내기 전 "몸 상태 이상 신호가 있어요." 로 바꾼다.
  facts 에 메모·자유 입력은 넣지 않는다(호출자 책임, coach 동의의 exclude_notes 기본값과 같은 취지).
- AI 가 원문과 같은 문장을 돌려주면 `{"text": null, "unchanged": true}` 로 저장 — 재요청하지 않고 화면은 규칙 문구(표시 없음).
- 프런트: `$lib/aiWording.isAiWorded` + `AiMark.svelte` — `source==='ai'` 일 때만 'AI 해설'. '규칙 기반 요약' 라벨은 폐지
  (Today 내러티브·월 화면 두 곳 교체 완료). 이후 표면은 응답에 `source` 를 실어 같은 컴포넌트를 쓴다.

## 4. 좋은 출력의 기준 (표면별 프롬프트 작성 기준)

- 규칙 판정의 방향·강도 유지("줄이세요" → "줄여 보면 좋아요" 는 OK, "괜찮아요" 는 X).
- facts 를 엮어 이유를 한 단계 더 설명: 규칙 "회복 신호가 여러 개 낮아요" → 좋은 출력 "수면 점수와 HRV 가 함께 낮아요. 오늘은 쉬어 가요."
- 새 수치·원인·예측 금지, 반올림만. 1~2문장, 해요체.
- 바꿔 말하기만 될 거면 원문 유지(지침에 명시) — 표시만 'AI' 로 바뀌는 무의미한 다듬기를 막는다.

## 5. 2·3단계 적용 순서(제안)

1단계 표면: Today 조정 사유·hold_reason, '이 러닝의 의미'(현재 `frontend/src/lib/activityImpact.ts` 클라이언트 조립 → 서버로 옮겨야
캐시·검증 가능), Story 월·주 문단(`story_service`). 2단계: 지표 해석 전반(`metrics_explain_*`, metric_note 대체) + insight `polished`
프런트 연결. 3단계: 예측 설명·마일스톤 문구·플랜 조정/weekly_adapt·더위 예보. 각 표면은 Surface 선언 + collect 함수 + 응답 `source` 만 추가한다.

## 6. 사용자 확인 필요

1. §2 A~C: 요청 스레드 동기 LLM 호출 제거(캐시 전용화)와 insight polish·adherence 에 동의 관문 추가 — 동의 없는 사용자는 AI 문구가 사라진다.
2. 공통 계층 동의 기준을 "claude_queue 동의"로 엄격히 둘지(현재 구현), narrative warm 처럼 "아무 동의"로 둘지.
3. metric_note 를 2단계 지표 해석이 나오면 끄는 것(drop) 승인.

## 7. 2단계 결과 (2026-11-19, ADR-059 D10~D14)

- metric_note: **drop 완료** — `metric_notes.py`·`metric_note.txt` 삭제, `action_hint` 는 규칙 문구만. 대체는 아래 지표 해석.
- 지표 해석(`metric_interpretation`, w:metric_interp): 분해 v2 일별 10종. 규칙 so_what 이 기본값이고, AI 는 본인 7·90일 평균·28일 전 값,
  같은 날 다른 계산 지표(ctl·atl·tsb·acwr·utrs·cirs), 다가오는 대회 거리·D-day, 오늘 계획을 facts 로 받아 원문에 없는 연결을 하나 이상 더한다.
  웰니스 원값·체크인·메모·대회 이름은 보내지 않는다. 동기화 뒤 `wording_warm_hooks.after_sync` 로 생성, 화면은 캐시만.
- insight polish: **improve 완료** — 동의(claude_queue) 사용자에게만 비건강 근거(acwr·CRS 게이트·피로 체크인·sync 지연 + 같은 날 tsb/utrs 등)를
  facts 로 보내고, 공통 템플릿·검증(건강 용어 거부)을 쓴다. 프런트 InsightBanner 가 `source==='ai'` 일 때 AiMark 를 붙인다.
- 사용자 결정(2026-11-19): insight polish·adherence 에 동의 관문 추가(적용 — 동의 없으면 규칙 문장만), metric_note drop 승인(적용),
  `/today/narrative` 키 기반 호출 현행 유지, 동의 기준을 '아무 AI 동의'로 확대(미적용 — 병합 시 `_consent_ok` 에서).
- 남은 사용자 확인: 웰니스 지표(수면·스트레스 등) 해석을 AI 대상에서 계속 뺄지.
