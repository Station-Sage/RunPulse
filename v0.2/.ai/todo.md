# v0.2 작업 목록

최종 업데이트: 2026-03-29 (리팩토링 3차 — dashboard_cards 분리)

---

## ▶ 다음 세션 시작 시 여기부터 (2026-03-29 기준)

### 최근 완료 요약 (상세: `changelog_history.md` 참조)
- **리팩토링 1차**: `views_training_crud.py` 896줄 → 3분리, README 3개 신설
- **리팩토링 2차**: `views_settings.py` 1508줄 → 6분리, `views_activities.py` 1096줄 → 4분리, `chat_context.py` 932줄 → 6분리
- **리팩토링 3차**: `views_dashboard_cards.py` 880줄 → 5분리
- **현재 상태: SCHEMA_VERSION=3.1(내부4), 1122 테스트 통과 (2026-03-29)**

### 다음 우선 작업

**리팩토링 계속 (300줄 초과 파일)**
- [ ] `views_report_sections.py` (707줄) 분리
- [ ] `src/training/planner.py` (713줄) 분리
- [ ] `src/ai/chat_engine.py` (696줄) 분리
- [ ] `helpers.py` (915줄) 분리 검토
- [ ] `db_setup.py` (968줄) 분리 검토

**v0.3 인프라**
- [ ] REST API (`/api/v1/*`)
- [ ] 인증/로그인 시스템 (bcrypt, 세션)

---

## 다음 세션 시작 프롬프트

```
v0.2/.ai/todo.md 상단 섹션 확인 후 다음 작업 제안.

최근 완료: 리팩토링 3차 (views_dashboard_cards 880줄 → 5분리, 1122 테스트 통과)

다음: 리팩토링 계속 (views_report_sections 707줄 → 분리) 또는 v0.3 인프라
```

---

## 현재 미완료 작업

### v0.3 예정 (인프라)
- [ ] 인증/로그인 시스템 (bcrypt, 세션)
- [ ] REST API (`/api/v1/*`)
- [ ] DB 정규화, 멀티유저

### 훈련탭 UX 재설계 ✅ Phase A~H 전체 완료
