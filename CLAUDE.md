# CLAUDE.md - RunPulse

## 필수 읽기 — 3계층 점진적 로딩

### Level 1 (매 세션 항상 읽을 것) — ~10KB
1. **이 파일** (`CLAUDE.md`) — 프로젝트 헌법
2. **`BACKLOG.md`** — NOW/BUGS 섹션만 확인 (현재 작업 + 버그)

### Level 2 (작업 대상 폴더만 읽을 것) — 각 1~2KB
| 작업 대상 | 읽을 파일 |
|-----------|----------|
| 웹 UI | `src/web/GUIDE.md` |
| 메트릭 | `src/metrics/GUIDE.md` |
| 동기화 | `src/sync/GUIDE.md` |
| AI 코치 | `src/ai/GUIDE.md` |
| 훈련 엔진 | `src/training/GUIDE.md` |

### Level 3 (명시적 지시 시만 읽을 것)
| 파일 | 용도 |
|------|------|
| `v0.2/.ai/metrics.md` | 새 메트릭 구현 시 계산식 원본 (PDF 기준) |
| `v0.2/.ai/metrics_by_claude.md` | 대안 계산식 비교용 |
| `v0.2/.ai/decisions.md` | 설계 판단 필요 시 기존 결정 확인 |

### 읽지 말 것
- `v0.2/.ai/archive/*` — 폐기된 문서 (필요 시 사용자가 지시)
- `v0.1/.ai/*` — 완료된 v0.1 히스토리

---

## 프로젝트 개요
- 이름: RunPulse — 개인 러닝 코치 에이전트
- 목적: Garmin, Strava, Intervals.icu, Runalyze 4개 소스의 러닝/건강 데이터를 통합 분석하고, AI 코치가 훈련 계획을 추천하며, 가민 워치에 자동 등록
- 저장소: https://github.com/Station-Sage/RunPulse
- 실행 환경: Android Termux, Python 3.11+, SQLite3, 파일 기반 저장
- 버전/테스트/브랜치 현황: **`BACKLOG.md` 상단** 참조

---

## 기술 스택
- Python 3.11+, SQLite3 (running.db)
- garminconnect[workout] (비공식, Typed Workout 모델 포함)
- httpx (Strava/Intervals/Runalyze API)
- gpxpy, fitparse (GPX/FIT 파싱)
- Flask 3.x (웹 대시보드)
- ECharts (CDN, 차트), SVG (게이지/레이더)
- Leaflet + OSM (지도, 오픈소스)
- Open-Meteo API (날씨, 무료, 키 없음)

---

## 브랜치 전략
- `main`: 안정 릴리스 전용, 보호됨
- `fix/metrics-everythings`: v0.2 개발 브랜치
- `chore/*`, `feat/*`, `fix/*`: 작업별 브랜치 (위 브랜치에서 분기)

---

## 빌드 및 실행 명령어

    python src/db_setup.py                         # DB 초기화/마이그레이션
    python src/sync.py --source all --days 7       # 데이터 동기화
    python src/analyze.py today                    # 오늘 리포트
    python src/serve.py                            # 웹 대시보드 localhost:18080
    python -m pytest tests/                        # 테스트 (1122개 기준)
    python scripts/check_docs.py                   # 문서 정합성 검증

---

## 핵심 규칙

### 코드 규칙
1. 파일 300줄 이하 유지. 초과 시 모듈 분리
2. 모든 외부 API 호출은 `src/utils/api.py`의 래퍼 함수 사용
3. 비밀 정보(토큰, 비밀번호)는 `config.json`에 저장. 절대 커밋 금지
4. 숫자 계산은 Python에서 수행. LLM은 해석/서술/계획 생성에만 활용
5. 4개 소스의 중복 활동은 timestamp ±5분 AND distance ±3%로 매칭
6. CLI 출력은 마크다운 형식. `--clipboard` 옵션으로 termux-clipboard-set 연동
7. 커밋 메시지: conventional commits (`feat:` `fix:` `docs:` `refactor:` `test:`)
8. 한국어 주석 허용, 코드와 변수명은 영어
9. 프롬프트 템플릿은 `src/ai/prompt_templates/*.txt`에 분리 관리
10. AI 응답 파싱 실패 시 항상 graceful fallback (규칙 기반 등)
11. 메트릭 데이터 없을 때 에러 대신 "데이터 수집 중" graceful UI
12. 하단 네비게이션 7+1탭: 홈 | 활동 | 레포트 | 훈련 | AI코치 | 동기화 | 설정 (+개발자)

### 작업 규칙
13. **BACKLOG.md에 없는 작업은 임의 진행 금지** — 사용자가 구두로 지시한 경우 먼저 BACKLOG.md BUGS에 기록 후 진행
14. 작업 시작 전 반드시 plan을 세우고 승인 요청
15. 설계 변경은 반드시 사용자 확인 후 진행

### 완료 규칙 (작업 완료 시 반드시 확인)
16. BACKLOG.md 해당 항목의 `done` 조건 모두 충족 확인
17. 수정한 파일이 속한 폴더의 GUIDE.md 파일맵이 여전히 정확한지 확인
18. `python -m pytest tests/` 전체 통과
19. 300줄 초과 파일이 새로 생기면 즉시 분리 계획 제시
20. BACKLOG.md 해당 항목 `[x]` 체크 및 DONE으로 이동
21. `python scripts/check_docs.py` 실행 및 불일치 수정

---

## 폴더 구조
```
CLAUDE.md             — 프로젝트 헌법 (이 파일)
BACKLOG.md            — 유일한 작업 추적 (NOW/NEXT/BUGS/DONE)
AGENTS.md             — Codex 등 다른 에이전트용 요약
.claude/rules/        — Claude 자동 적용 규칙
src/web/GUIDE.md      — 웹 폴더 가이드
src/metrics/GUIDE.md  — 메트릭 폴더 가이드
src/sync/GUIDE.md     — 동기화 폴더 가이드
src/ai/GUIDE.md       — AI 폴더 가이드
src/training/GUIDE.md — 훈련 엔진 폴더 가이드
v0.2/.ai/             — 유지: metrics.md, decisions.md (Level 3 참조)
v0.2/.ai/archive/     — 폐기된 문서 보관
v0.3/workflow.md      — v0.3 개선 계획서
scripts/              — 자동화 스크립트
```

---

## Who Is Claude Code
시니어 Python 엔지니어로서 깔끔하고 테스트 가능한 코드를 작성한다.
작업 전 반드시 plan을 세우고 승인을 요청한다.
불필요한 칭찬이나 장황한 설명 없이 핵심만 전달한다.
파일 생성과 수정은 확인 없이 진행하되, 설계 변경은 반드시 확인한다.
