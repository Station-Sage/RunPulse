# AI Everywhere v2 — 캐시 기반 AI 해석 통합 설계

> 탭별 1회 API 호출 → DB 캐시 → 8시간/동기화 후 갱신
> 검증 + 재시도 + 규칙 기반 fallback

---

## 아키텍처 (v2)

### 호출 흐름

```
페이지 접속
    ↓
ai_cache 테이블에서 해당 탭 캐시 조회
    ↓
캐시 유효? (8시간 이내 AND 동기화 후 생성)
    ├─ YES → 캐시에서 즉시 표시 (API 호출 0)
    └─ NO  → 탭별 통합 프롬프트 1회 호출
              ↓
           포맷 검증 (JSON 파싱, 필수 키)
              ├─ 실패 → 재시도 1회 (엄격 프롬프트)
              └─ 통과 → 내용 검증 (길이, 데이터 정합성)
                          ├─ 실패 → 규칙 기반 fallback
                          └─ 통과 → ai_cache에 저장 → 표시
```

### 갱신 조건

| 조건 | 동작 |
|------|------|
| 동기화 직후 첫 접속 | AI 재생성 (데이터 변경됨) |
| 마지막 생성 후 8시간 경과 | AI 재생성 (하루 3회: 아침/점심/저녁) |
| 수동 "AI 분석 업데이트" | AI 재생성 |
| 캐시 유효 | DB에서 즉시 표시 (0회 호출) |

### 일일 API 호출 예상

```
탭 6개 × 하루 3회 = 18회/일 (최대)
실제: 사용하는 탭만 → 약 10~12회/일
Gemini 무료 1,500 RPD → 충분
```

---

## DB 스키마

### ai_cache 테이블

```sql
CREATE TABLE IF NOT EXISTS ai_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tab TEXT NOT NULL,           -- 'dashboard', 'activity', 'report', ...
    cache_key TEXT NOT NULL,     -- 탭 내 고유 키 (activity_id, period 등)
    content_json TEXT NOT NULL,  -- {"recommendation": "...", "risk": "...", ...}
    generated_at TEXT NOT NULL,  -- 생성 시각
    data_hash TEXT,              -- 입력 데이터 해시 (변경 감지용)
    UNIQUE(tab, cache_key)
);
```

---

## 탭별 통합 프롬프트

### 대시보드 (1회 호출 → 4개 카드)

```json
// 응답 포맷
{
  "recommendation": "오늘은 이지런 6km 권장. BB 61이고 어제 템포런 후 회복 중.",
  "risk": "ACWR 1.2 적정. 지난주 대비 안정적 추세.",
  "rmr": "강점: 유산소용량 82. 약점: 회복력 55 — 수면 개선 필요.",
  "fitness": "VDOT 43.7 유지. eFTP 5:17로 2주 전 대비 3초 개선."
}
```

### 활동 심층분석 (1회 호출 → 종합 + 메트릭별)

```json
{
  "summary": "템포런 8km. EF 1.58로 효율 양호. Dec 3.2%로 유산소 기반 안정.",
  "metrics": {
    "EF": "1.58 — 효율 양호, 이번 달 평균 대비 5% 향상",
    "AerobicDecoupling": "3.2% — 유산소 기반 안정, 5% 이하 유지",
    "TRIMP": "328 — 고부하, 내일 회복일 권장",
    "FEARP": "4:51 — 기온 22°C 반영, 실제보다 3초 빠른 조건"
  }
}
```

### 레포트 (1회 호출)

```json
{
  "insight": "이번 주 42km/목표 40km 달성. UTRS 48→55 회복 추세. ACWR 1.1 안정."
}
```

### 훈련 (1회 호출)

```json
{
  "coaching": "이행률 80%. 내일 인터벌 예정, 컨디션 양호하니 계획대로.",
  "adjustment": "BB 61, 수면 62 → 정상 범위. 조정 불필요."
}
```

### 웰니스 (1회 호출)

```json
{
  "recovery": "BB 49 → 보통. 어제 고강도 후 회복 중. 스트레칭 권장.",
  "pattern": "HRV 3일 연속 하락 → 누적 피로 주의. 수면 시간 일정."
}
```

### 레이스 (1회 호출)

```json
{
  "readiness": "RRI 65. VDOT 43.7 기준 하프 1:43 예상. DI 70 양호.",
  "pacing": "전반 4:55, 후반 4:50 네거티브 스플릿 가능."
}
```

---

## 검증 + 재시도

### 3단계 검증

```python
def validate_ai_response(tab, response_json, actual_data):
    # 1. 포맷 검증
    if not isinstance(response_json, dict):
        return False, "JSON 형식 아님"
    required_keys = TAB_REQUIRED_KEYS[tab]
    for key in required_keys:
        if key not in response_json:
            return False, f"필수 키 누락: {key}"

    # 2. 길이 검증
    for key, text in response_json.items():
        if len(text) < 5:
            return False, f"{key}: 너무 짧음 ({len(text)}자)"
        if len(text) > 500:
            return False, f"{key}: 너무 김 ({len(text)}자)"

    # 3. 데이터 정합성
    return validate_data_consistency(tab, response_json, actual_data)
```

### 데이터 정합성 규칙

```python
CONSISTENCY_RULES = {
    "dashboard": [
        # UTRS 낮은데 고강도 추천 → 모순
        lambda data, ai: not (data["utrs"] < 40 and
            any(w in ai.get("recommendation","") for w in ["고강도","인터벌","레이스페이스"])),
        # CIRS 위험인데 정상 훈련 → 모순
        lambda data, ai: not (data["cirs"] > 75 and
            any(w in ai.get("recommendation","") for w in ["계획대로","정상","가능"])),
    ],
    "wellness": [
        # BB 30 미만인데 양호 → 모순
        lambda data, ai: not (data.get("bb",100) < 30 and
            "양호" in ai.get("recovery","")),
    ],
}
```

### 재시도 전략

```
1차 시도: temperature=0.3, JSON 형식 요청
    ↓ 검증 실패
2차 시도: temperature=0.1, 실패 이유 포함 + "반드시 JSON으로"
    ↓ 검증 실패
규칙 기반 fallback (항상 동작)
```

---

## API 호출 최적화

### temperature 설정

| 용도 | temperature | 이유 |
|------|------------|------|
| 분석/해석 | 0.3 | 일관성 + 약간의 변화 |
| 재시도 | 0.1 | 더 엄격한 일관성 |
| AI 채팅 | 0.7 | 대화적 자연스러움 |

### JSON 강제

```python
# Gemini: response_mime_type
json={"generationConfig": {"responseMimeType": "application/json"}}

# OpenAI/Groq: response_format
json={"response_format": {"type": "json_object"}}
```

### Few-shot 예시 포함

```
프롬프트 끝에:
예시 응답:
{"recommendation": "컨디션 양호. 템포런 8km, Z3-4 유지.", "risk": "ACWR 1.1 적정."}
```

---

## 공통 모듈 구조 (v2)

```
src/ai/
├── ai_message.py        ← get_tab_ai() 탭별 통합 호출 (리팩토링)
├── ai_cache.py          ← DB 캐시 관리 (신규)
├── ai_validator.py      ← 검증 + 재시도 (신규)
├── context_builders.py  ← 탭별 컨텍스트 빌더 (기존)
├── prompt_config.py     ← 프롬프트 템플릿 (리팩토링: 탭별 통합)
├── chat_engine.py       ← AI 채팅 (기존, 변경 없음)
└── genspark_driver.py   ← Genspark DOM (기존)
```

---

## 구현 순서

### Phase A: 캐시 인프라
- [ ] ai_cache 테이블 (db_setup.py)
- [ ] ai_cache.py — get/set/invalidate/is_fresh
- [ ] 동기화 후 캐시 무효화 훅

### Phase B: 탭별 통합 프롬프트
- [ ] 대시보드: 4카드 → 1회 호출
- [ ] 활동: 종합 + 메트릭배치 → 1회 호출
- [ ] 훈련/레포트/웰니스/레이스: 각 1회 호출
- [ ] temperature 0.3 + JSON 강제

### Phase C: 검증 + 재시도
- [ ] ai_validator.py — 포맷/길이/정합성
- [ ] 재시도 로직 (temperature 0.1)
- [ ] 정합성 규칙 탭별 정의

### Phase D: UI
- [ ] "AI 분석 업데이트" 버튼 (각 탭 또는 설정)
- [ ] AI 배지 (생성 시각 표시)
- [ ] 프롬프트 관리 설정 UI (기존)

---

## 주의사항

1. **캐시 키**: 대시보드=날짜, 활동=activity_id, 레포트=기간
2. **동기화 감지**: sync_jobs.updated_at vs ai_cache.generated_at
3. **규칙 기반 항상 유지**: AI 없어도 동작
4. **API 에러 시 무음 실패**: 사용자에게 에러 안 보임, 규칙 기반 표시
5. **캐시 TTL**: 8시간 (하루 3회 갱신)
