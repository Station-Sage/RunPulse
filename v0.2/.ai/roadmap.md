# RunPulse 개발 로드맵

> 상세 작업 체크리스트는 `todo.md` 참조. 이 파일은 버전별 고수준 목표와 의존 관계만 정리.

---

## v0.2 (현재, 대부분 완료)

**목표**: 2차 메트릭 계산 엔진 + 고도화 웹 대시보드

| 영역 | 상태 | 요약 |
|------|------|------|
| 2차 메트릭 엔진 | ✅ 완료 | 13개 메트릭 (UTRS/CIRS/FEARP/DI/DARP/RMR/TIDS/LSI/ACWR/ADTI/RTTI/WLEI/TPDI) |
| 1차 메트릭 자체 계산 | ✅ 완료 | GAP/NGP/TRIMP/Monotony/Decoupling/RelativeEffort/MarathonShape |
| 4소스 API 완성 | ✅ 완료 | Garmin/Strava/Intervals/Runalyze 전체 데이터 수집 |
| 웹 대시보드 | ✅ 완료 | 7개 화면 (대시보드/활동/레포트/레이스/AI코칭/훈련/웰니스) |
| 남은 작업 | ⏳ | UI 보완 (6.4~6.8, S5-C2), Import/Export, 문서 정합성 |

---

## v0.3 (다음)

**목표**: 인프라 고도화 + 신규 메트릭 + UI 전면 재설계

### 인프라
- 인증/로그인 시스템 (bcrypt, 세션)
- PWA (오프라인, service worker)
- REST API (`/api/v1/*`)
- DB 정규화, 멀티유저 강화

### 메트릭
- eFTP, Critical Power / W'
- REC (러닝 효율성), RRI (레이스 준비도)
- SAPI (계절 성과 비교), TEROI (훈련 ROI)

### UI
- 6.4~6.8 UI 보완 + S5-C2 UI 전면 재설계
- Training Plan 풀 구현 (캘린더, 운동 CRUD)
- AI 채팅 (대화형 코칭)

---

## v0.4 (계획)

**목표**: 네이티브 앱 + ML 기반 메트릭

- React Native 모바일 앱
- TQI (훈련 품질 지수) — ML 기반
- PLTD (개인화 역치 자동 탐지) — ML 기반
- Google/Naver Calendar 연동

---

## 메트릭 구현 타임라인

```
v0.2 (완료): LSI, GAP, NGP, FEARP, ADTI, TIDS, RE, MarathonShape
             ACWR, TRIMP, UTRS, CIRS, Decoupling, DI, DARP, RMR
             Monotony, RTTI, WLEI, TPDI
                    ↓
v0.3 (다음): eFTP, Critical Power, REC, RRI, SAPI, TEROI
                    ↓
v0.4 (ML):   TQI, PLTD
```

---

## 의존 관계

```
v0.2 Phase 0~9 + Sprint 1~6 ← ✅ 완료
        ↓
v0.2 잔여 (UI 보완, Import/Export)
        ↓
v0.3 인프라 (인증 → REST API → PWA)
v0.3 메트릭 (eFTP/CP → REC/RRI/SAPI/TEROI)
v0.3 UI (S5-C2 재설계 → Training 풀 구현)
        ↓
v0.4 네이티브 앱 + ML 메트릭
```

---

## 구현 시 주의사항

1. **메트릭 데이터 없을 때**: "수집 중" graceful UI 표시
2. **PDF 계산식 우선**: 문서-구현 차이 시 PDF 기준으로 수정
3. **ECharts CDN**: 오프라인 시 SVG fallback
4. **파일 300줄 제한**: 초과 시 분리
5. **날씨 API**: Open-Meteo (무료, 키 없음)
6. **RMR 5축**: 유산소용량/역치강도/지구력/동작효율성/회복력
7. **DI**: pace/HR 비율법, 최소 90분+ 세션 8주간 3회
8. **CIRS 가중치**: ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1
