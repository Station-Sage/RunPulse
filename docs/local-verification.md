# 로컬 검증 가이드 — Phase 5 웹 UI

## 앱 실행

```bash
# DB 초기화 (최초 1회)
python src/db_setup.py

# Garmin 데이터 동기화 (실제 데이터 확인 시)
python src/sync.py --source garmin --days 14

# 웹 서버 시작
python src/serve.py
```

## 확인할 URL

| URL | 설명 |
|-----|------|
| `http://localhost:8080/` | 홈 대시보드 |
| `http://localhost:8080/activities` | 활동 목록 탭 |
| `http://localhost:8080/wellness` | 회복/웰니스 |
| `http://localhost:8080/activity/deep` | 가장 최근 활동 심층 분석 |
| `http://localhost:8080/activity/deep?id=1` | id=1 활동 심층 분석 |

---

## 샘플 데이터 삽입 (실제 동기화 없이 빠른 확인)

```python
import sqlite3

conn = sqlite3.connect("running.db")

# 활동 3개 (이전/다음 네비 확인용)
for i, (dt, dist) in enumerate([
    ("2026-03-19T07:00:00", 8.0),
    ("2026-03-20T07:00:00", 10.5),
    ("2026-03-21T07:00:00", 21.1),
], start=1):
    conn.execute("""
        INSERT INTO activity_summaries
        (source, source_id, activity_type, start_time,
         distance_km, duration_sec, avg_pace_sec_km, avg_hr)
        VALUES ('garmin', ?, 'running', ?, ?, ?, 343, 148)
    """, (f"test-{i}", dt, dist, int(dist * 360)))

# Garmin 일별 상세 지표 (2026-03-21 기준)
today = "2026-03-21"
for metric, val in [
    ("training_readiness_score", 72),
    ("overnight_hrv_avg", 58.2),
    ("overnight_hrv_sdnn", 12.5),
    ("hrv_baseline_low", 52),
    ("hrv_baseline_high", 65),
    ("sleep_stage_deep_sec", 5400),   # 1h 30m
    ("sleep_stage_rem_sec", 4800),    # 1h 20m
    ("sleep_restless_moments", 8),
    ("body_battery_delta", -20),
    ("stress_high_duration", 1800),   # 30분
    ("respiration_avg", 14.2),
    ("spo2_avg", 97.5),
]:
    conn.execute(
        "INSERT INTO daily_detail_metrics"
        " (date, source, metric_name, metric_value) VALUES (?, 'garmin', ?, ?)",
        (today, metric, val),
    )

# Intervals 걸음수/체중
conn.execute("""
    INSERT INTO daily_wellness (date, source, steps, weight_kg)
    VALUES ('2026-03-21', 'intervals', 8500, 70.2)
""")

conn.commit()
conn.close()
```

---

## 수동 테스트 체크리스트

### 공통
- [ ] 다크 모드(OS 설정) 전환 시 배경/글자 색상 변경됨
- [ ] 브라우저 너비 600px 미만 시 카드가 세로로 쌓임 (flex-direction: column)
- [ ] nav 바에 `홈 / 활동 목록 / 회복/웰니스 / 활동 심층` 링크 표시

### `/activities` — 활동 목록
- [ ] 기본 접속 시 최근 90일 활동 목록 표시
- [ ] 소스 필터(garmin 선택) → garmin 활동만 표시
- [ ] 날짜 범위 입력 후 조회 → 해당 기간 활동만 표시
- [ ] 총 활동 수 / 총 거리 요약 한 줄 표시
- [ ] `심층` 링크 클릭 → `/activity/deep?id=N`으로 이동

### `/wellness` — 회복/웰니스

| 상황 | 기대 화면 |
|------|-----------|
| **Garmin 데이터 있음** | 훈련 준비도 배지 (색상 반영), 회복 점수 카드, 수면(딥/REM/뒤척임), 야간 HRV (avg/SDNN/기준선), SpO2·호흡수·바디배터리·고스트레스 카드 |
| **intervals 체중/걸음수 있음** | 일별 활동 지표 카드에 걸음 수·체중 표시 |
| **Garmin 데이터 없음** | "Garmin 웰니스 데이터가 없습니다" 안내 + 동기화 명령 |
| **공통** | 14일 회복 추세 테이블 항상 표시 (데이터 없으면 "(데이터 없음)") |

### `/activity/deep` — 활동 심층 분석

| 상황 | 기대 화면 |
|------|-----------|
| **Garmin 일별 상세 있음** | 훈련 준비도 배지, 딥/REM 슬립, 야간 HRV, SpO2, 바디배터리 변화, 고스트레스 시간 카드 |
| **Garmin 일별 상세 없음** | "해당 날짜의 Garmin 일별 상세 데이터가 없습니다" 문구 |
| **활동 여러 개** | 네비 바에 `← 이전날짜  목록으로  다음날짜 →` 링크 표시 |
| **가장 오래된 활동** | `← (없음)` + 다음 날짜 링크만 표시 |
| **가장 최신 활동** | 이전 날짜 링크 + `(없음) →` 표시 |
