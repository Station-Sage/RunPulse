# V2-REPAIR D — 능동 인사이트 (v3) 설계안

상태: **설계안, 구현 미승인.** 근거: `REVIEW-10`, 분석·코치·플랜 감사(2026-11-17) "능동 인사이트 경로 없음".
구현 착수는 사용자 승인 후에만 한다.

## 1. 문제
지금 앱은 사용자가 화면을 열거나 질문해야만 해석을 보여 준다. 몸 상태·부하가 임계를 넘어도 "알려 주는" 경로가 없다.
- `src/ai/briefing.py` 는 죽은 코드가 아니다: `build_chip_prompt` 가 `chat_engine.py:84` 에서 쓰인다. 죽은 쪽은 `build_briefing_prompt`(복사·붙여넣기용 일일 프롬프트)뿐이며 호출처는 같은 파일 `:101` 의 래퍼 하나다.
- 오늘 브리핑(`today_service.get_today_briefing`)은 규칙 기반 한 줄이며 화면을 열었을 때만 계산된다.
- 조정 신호(`adjustment_signals.collect` + `adjustment_triggers_v3`)는 "오늘 세션을 바꿀지" 판정에만 쓰이고, 사용자에게 알릴 사건으로는 노출되지 않는다.

## 2. 원칙
1. 새 계산을 만들지 않는다. 기존 신호·메트릭의 **상태 변화**를 사건으로 기록한다.
2. LLM 은 문장 다듬기에만 쓰고, 사건 발생 여부는 규칙으로 판정한다(결정성·테스트 가능).
3. 사건은 적게, 의미 있게: 하루 상한·중복 억제·해소 시 자동 닫힘.
4. 질병·통증 등 민감 신호는 기존 `redact_illness_for_ai` 규칙을 그대로 따른다.

## 3. 이벤트 모델
테이블 `insight_events` (마이그레이션 v47 예정(현재 v46), 단일 사용자 DB 기준):

| 컬럼 | 설명 |
|------|------|
| id | PK |
| kind | `load_spike` / `recovery_low` / `pain_flag` / `adherence_drop` / `hrv_trend` / `pb_candidate` / `data_gap` |
| severity | `info` / `watch` / `act` |
| as_of | 판정 기준일(로컬 날짜) |
| dedupe_key | `kind:scope` — 같은 키는 열린 사건 1개만 |
| signals_json | 근거 신호 스냅샷(`adjustment_signals` 항목 형식 재사용: signal/value/as_of/freshness) |
| text | 한 줄 요약(규칙 템플릿, 선택적 LLM 다듬기) |
| action_json | 권장 행동 `{label, route}` (예: 오늘 세션 보기, 체크인 열기) |
| state | `open` / `seen` / `dismissed` / `resolved` |
| created_at, resolved_at | |

### 판정 규칙(기존 신호 재사용)
- `load_spike`: ACWR ≥ 1.5(`acwr` 신호) — 1.8 이상은 `act`.
- `recovery_low`: CRS level ≤ 1 + 체크인 피로 ≥ 7 중 2개 이상(= `adjustment_triggers_v3.triggered` 결과 재사용). 단독 조건(`pain`/`illness`)은 `pain_flag`.
- `adherence_drop`: 플랜 이행(C-2 의 plan adherence) 최근 2주 < 70%.
- `hrv_trend`: HRV 7일 평균이 28일 기준 −1σ 미만이 3일 지속(C-2 HRV 분포).
- `pb_candidate`: 최근 예측이 개인 최고 기록보다 1% 이상 빠름(기존 prediction 서비스).
- `data_gap`: 소스 동기화 3일 이상 끊김(`sync` 상태).
- 해소: 같은 판정을 다시 돌려 조건이 풀리면 `resolved`. 사용자 `dismissed` 는 같은 dedupe_key 로 7일간 재생성 금지.

## 4. 생성 시점
- bg_sync 가 끝난 직후와 체크인 저장 직후에 `insight_service.refresh(conn, day)` 1회 호출. 읽기 전용 신호 수집 후 위 규칙 평가, upsert.
- 화면 조회는 저장된 사건만 읽는다(요청 시 재계산 금지 → Today 성능 영향 없음).

## 5. 노출
1. Today: 상단 한 줄 배너(최대 1개, `act` > `watch` > `info`) + 탭 시 근거 칩(Coach 근거 칩과 같은 컴포넌트) + 액션 버튼.
2. Coach 홈: "최근 알림" 목록 3건.
3. Coach 대화 컨텍스트: 열린 사건을 `chat_context_builders` 에 한 블록으로 추가해 질문 없이도 답변이 사건을 알게 한다.
4. 푸시·이메일은 범위 밖(별도 결정). 우선은 앱 내 노출만.

## 6. `briefing.py` 처리 안
- `build_chip_prompt` 유지.
- `build_briefing_prompt`·`briefing.txt` 는 사건 문장 다듬기 프롬프트로 **교체**(입력: 사건 text+signals, 출력: 1~2문장). 파싱 실패 시 규칙 템플릿 문장 그대로(coding-rules fallback).

## 7. API
- `GET /api/insights?state=open` · `POST /api/insights/{id}/dismiss` · `POST /api/insights/{id}/seen` (쓰기는 Origin 관문 대상).

## 8. 구현 단계(승인 시)
| 단계 | 내용 | 테스트 |
|------|------|--------|
| D1 | v47 마이그레이션 + `insight_service`(규칙 평가·upsert·해소·dismiss 억제) | 규칙별 경계값, 중복 억제, 해소 |
| D2 | API + sync/체크인 훅 | 훅 후 사건 생성, Origin |
| D3 | Today 배너·Coach 목록 UI | 브라우저 스모크 |
| D4 | Coach 컨텍스트 블록 + LLM 문장 다듬기 + fallback | 파싱 실패 fallback |

## 9. 사용자 결정 필요
1. 푸시/이메일 알림 포함 여부(기본안: 제외).
2. 사건 종류 7개 전부 vs `load_spike`·`recovery_low`·`pain_flag`·`data_gap` 4개로 시작(권장: 4개 먼저).
3. Today 배너 위치(상단 고정 vs 브리핑 카드 내부).
4. dismiss 억제 기간 7일 적정성.
