# AI Everywhere — 전체 UI AI 해석 통합 설계

> 모든 카드/섹션에서 AI 해석을 제공하되, API 없으면 규칙 기반 fallback.
> provider 체인: 사용자 선택 → Gemini → Groq → 규칙 기반

---

## 아키텍처

### 공통 모듈

```
src/ai/ai_message.py
├── get_ai_message(prompt, rule_fallback, config, cache_key)
├── get_metric_interpretation(metric_name, value, context, config)
├── build_tab_context(conn, tab, **kwargs)  ← 신규
└── PROMPT_TEMPLATES  ← 신규
```

### Provider 체인

```
사용자 선택 provider
  ↓ 실패
gemini (무료, 1500 RPD)
  ↓ 실패
groq (무료, 14400 RPD)
  ↓ 실패
규칙 기반 fallback (항상 동작)
```

### 캐시 전략

- 동일 cache_key는 세션 내 재사용 (메모리 캐시)
- 대시보드: 30초 TTL (기존 페이지 캐시와 연동)
- 레포트: 기간+날짜 조합 키
- 활동 상세: activity_id 키

---

## 탭별 상세 설계

### 1. 대시보드 (4개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 훈련 권장 | UTRS/CIRS/TSB + 오늘 계획 | UTRS 7일 | "오늘 ~하세요" 조언 | 2문장 |
| 리스크 해석 | ACWR/LSI/Mono/Strain/TSB | 7일 추세 | 위험 요약 + 조언 | 1~2문장 |
| RMR 분석 | 5축 점수 + 28일 변화 | 이전 vs 현재 | 강점/약점 분석 | 2문장 |
| 피트니스 평가 | VDOT/Shape/eFTP/REC/RRI | 4주 추세 | 체력 변화 평가 | 2문장 |

**컨텍스트 빌더:**
```python
def _dashboard_context(conn, today):
    return {
        "utrs_7d": load_metric_series("UTRS", -7, today),
        "cirs_7d": load_metric_series("CIRS", -7, today),
        "acwr_7d": load_metric_series("ACWR", -7, today),
        "tsb_7d": load_metric_series("TSB", -7, today),
        "wellness": {bb, sleep, hrv, stress},
        "today_plan": planned_workout,
        "recent_3_activities": [...],
        "weekly_volume": {this_week, last_week, change_pct},
    }
```

### 2. 활동 심층분석 (3개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 활동 종합 | 거리/페이스/HR/존/스플릿/EF/Dec | 최근 10회 유사 | 총평 + 잘한 점/개선점 | 3~4문장 |
| 메트릭 해설 | 각 메트릭 값 | 해당 메트릭 추세 | 메트릭별 1줄 해석 | 1문장/메트릭 |
| 환경 영향 | FEARP 요소 (기온/습도/고도) | 동일 코스 이력 | 환경 보정 설명 | 1~2문장 |

**컨텍스트 빌더:**
```python
def _activity_context(conn, activity_id):
    return {
        "activity": {distance, pace, hr, duration, type, name},
        "zones": [z1%, z2%, z3%, z4%, z5%],
        "splits": [...],
        "metrics": {EF, Dec, FEARP, TRIMP, WLEI, ...},
        "recent_similar": [최근 10회 유사 거리 활동],
        "personal_best": {5k, 10k, half, full},
        "weather": {temp, humidity, wind},
        "workout_classification": {type, effect, confidence},
    }
```

### 3. 레포트 (3개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 기간 종합 인사이트 | **선택 기간** 전체 메트릭 | 기간 내 주별 추세 | 5항목 분석 | 5줄 |
| 활동 효과 | 활동별 분류/RE/Dec | 기간 내 활동 목록 | 활동별 1줄 효과 | 1문장/활동 |
| 진전/퇴보 | 이전 기간 vs 현재 기간 | 양 기간 비교 | 변화 포인트 3개 | 3줄 |

**⚠️ 기간 변경 시 기간에 맞춰 데이터 재조회**

**컨텍스트 빌더:**
```python
def _report_context(conn, start_date, end_date):
    # 이전 동일 기간도 함께 로드
    span = (end - start).days
    prev_start = start - timedelta(days=span)
    prev_end = start - timedelta(days=1)
    return {
        "period": f"{start_date} ~ {end_date}",
        "stats": {count, total_km, total_sec},
        "prev_stats": {count, total_km, total_sec},
        "utrs_series": [...],  # 기간 내 일별
        "cirs_series": [...],
        "acwr_series": [...],
        "weekly_distance": [...],  # 기간 내 주별
        "tids_trend": [...],  # 기간 내 TIDS 변화
        "top_activities": [...],  # 기간 내 상위 5개
        "wellness_avg": {bb, sleep, hrv},
    }
```

### 4. 레이스 예측 (3개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 레이스 준비도 | VDOT/CTL/DI/CIRS/MarathonShape | 12주 추세 | 종합 준비도 + 확률 | 3문장 |
| 훈련 조정 제안 | 목표 갭 + 남은 기간 | D-day 카운트다운 | 핵심 훈련 3가지 | 3줄 |
| 페이스 전략 | DARP 스플릿 + DI | 최근 장거리 이력 | 구간별 조언 | 4줄 |

**컨텍스트 빌더:**
```python
def _race_context(conn, target_distance):
    return {
        "goal": {name, distance, race_date, target_time, d_day},
        "vdot_12w": [...],
        "di_12w": [...],
        "ctl_trend": [...],
        "marathon_shape": value,
        "darp_predictions": {5k, 10k, half, full},
        "long_run_history": [최근 15km+ 활동],
        "cirs_current": value,
    }
```

### 5. 웰니스 (3개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 회복 분석 | BB/수면/HRV/스트레스 | 14일 추세 | 회복 상태 + 원인 | 2~3문장 |
| 수면 분석 | 수면 점수/시간/패턴 | 14일 + 주중/주말 | 수면 질 평가 + 팁 | 2문장 |
| 생활 패턴 | 전체 웰니스 패턴 | 14일 상관분석 | 훈련↔회복 상관 | 2~3문장 |

**컨텍스트 빌더:**
```python
def _wellness_context(conn, today):
    return {
        "today": {bb, sleep_score, hrv, stress, resting_hr},
        "bb_14d": [...],
        "sleep_14d": [...],
        "hrv_14d": [...],
        "stress_14d": [...],
        "sleep_times": [{bed, wake}, ...],  # 취침/기상 패턴
        "training_load_7d": [...],  # 훈련 부하 → 회복 상관
        "outliers": [...],  # 이상치 날짜
    }
```

### 6. 훈련 계획 (4개 카드)

| 카드 | 프롬프트 인풋 | 시계열 | AI 출력 | 길이 제약 |
|------|-------------|--------|---------|----------|
| 종합 코칭 | 이행률 + 지표 + 오늘 결과 | 4주 볼륨 | 종합 조언 | 3~4문장 |
| 컨디션 조정 | fatigue + 웰니스 + CIRS | 웰니스 7일 | 오늘 조정 사항 | 2문장 |
| 주간 피드백 | 주간 완료율 + 볼륨 | 이번 주 일별 | 남은 일 권장 | 2문장 |
| 다음 주 미리보기 | 훈련 단계 + 목표 | 다음 주 계획 | 볼륨/강도 예고 | 2문장 |

**컨텍스트 빌더:**
```python
def _training_context(conn, week_offset=0):
    return {
        "goal": {name, distance, race_date, d_day},
        "phase": "build",  # base/build/peak/taper
        "this_week": {workouts: [...], completion_pct, total_km, total_time},
        "last_4_weeks": [{week, km, count}, ...],
        "today_activity": {있으면 오늘 활동 데이터},
        "today_plan": {workout_type, distance, pace},
        "remaining_workouts": [이번 주 남은 워크아웃],
        "next_week_plan": [...],
        "utrs": value, "cirs": value,
        "wellness": {bb, sleep, hrv},
        "volume_change_pct": 지난주 대비 변화율,
    }
```

### 7. AI 코치 (브리핑 + 채팅)

| 카드 | 프롬프트 인풋 | AI 출력 | 길이 제약 |
|------|-------------|---------|----------|
| 브리핑 | 위 모든 컨텍스트 통합 | 5항목 구조화 브리핑 | 10~15줄 |
| 채팅 | 위 + 대화 히스토리 | 자연어 대화 | 자유 |

---

## 프롬프트 템플릿 관리

### 기본 구조

```python
PROMPT_TEMPLATES = {
    "dashboard_recommendation": {
        "system": "당신은 경험 많은 러닝 코치입니다.",
        "template": "아래 데이터로 오늘 훈련 조언을 한국어 2문장으로.\n\n{context}",
        "max_length": "50자",
        "editable": True,
    },
    "report_insight": {
        "system": "당신은 러닝 데이터 분석가입니다.",
        "template": "{period} 기간 분석을 5항목으로.\n\n{context}",
        "max_length": "각 항목 1줄",
        "editable": True,
    },
    # ...
}
```

### 설정 UI에서 관리

- 설정 → "AI 프롬프트 관리" 섹션
- 각 프롬프트 미리보기 (읽기 전용 또는 수정 가능)
- "기본값 복원" 버튼
- config.json의 `ai.custom_prompts`에 사용자 수정본 저장

---

## 구현 순서

### Phase 1: 기반 (이번 PR)
- [ ] `ai_message.py` 확장 — `build_tab_context()` + `PROMPT_TEMPLATES`
- [ ] 프롬프트 템플릿 14종 정의
- [ ] 컨텍스트 빌더 7개 (탭별)

### Phase 2: 핵심 탭 적용 (이번 PR)
- [ ] 훈련탭 4개 카드
- [ ] 대시보드 4개 카드
- [ ] AI 코치 브리핑

### Phase 3: 전체 확장 (다음 PR)
- [ ] 레포트 3개 카드 (기간 변동 지원)
- [ ] 레이스 3개 카드
- [ ] 웰니스 3개 카드
- [ ] 활동 심층분석 3개 카드

### Phase 4: 설정 + 품질 (다음 PR)
- [ ] 설정 UI 프롬프트 관리
- [ ] 프롬프트 튜닝 + 테스트
- [ ] 응답 품질 모니터링 (too long / off-topic 감지)

---

## 주의사항

1. **API 호출 비용**: 페이지 로딩마다 호출하면 RPD 소진. 캐시 필수
2. **응답 시간**: AI 호출은 1~5초. 페이지 렌더링 지연 방지 (비동기 or 캐시)
3. **길이 제약**: 카드마다 다름. 프롬프트에 명시적 길이 지정
4. **기간 변경**: 레포트 기간 바꾸면 AI 인사이트도 재생성 필요
5. **규칙 기반은 항상 유지**: AI 실패 시 즉시 fallback. 빈 카드 없어야 함
6. **시계열 데이터 크기**: 90일 일별 데이터 = ~90 토큰. 적절히 다운샘플링
