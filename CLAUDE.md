# CLAUDE.md - RunPulse

## 필수 읽기 — 3계층 점진적 로딩

### Level 1 (매 세션 항상 읽을 것)
1. **이 파일** (`CLAUDE.md`) — 프로젝트 헌법
2. **`BACKLOG.md`** — NOW/BUGS 섹션만 확인 (현재 작업 + 버그)

### Level 2 (작업 대상 폴더)
| 작업 대상 | 읽을 파일 |
|-----------|----------|
| 폴더별 상세 | 해당 폴더 `__init__.py` docstring |
| 전체 파일 구조 | `v0.3/data/files_index.md` (필요할 때 grep으로 필요한 부분만 읽을 것) |
| 버그 수정 | `BUGS_DETAIL.md` (해당 BUG ID 섹션만) |

### Level 3 (명시적 지시 시만 읽을 것)
| 파일 | 용도 |
|------|------|
| `v0.3/data/architecture.md` | 스키마, 레이어 구조 |
| `v0.3/data/phase_summary.md` | Phase 1-5 구현 요약 |
| `v0.3/data/metric_dictionary.md` | 메트릭 사전 (자동 생성) |
| `v0.3/data/phase-5-impl/` | Phase 5 서비스 레이어 설계서 |
| `v0.2/.ai/metrics.md` | 새 메트릭 구현 시 계산식 원본 (PDF 기준) |
| `v0.2/.ai/metrics_by_claude.md` | 대안 계산식 비교용 |
| `v0.2/.ai/decisions.md` | 설계 판단 필요 시 기존 결정 확인 |

### 읽지 말 것
- `LATER.md` — 장기 아이디어 풀 (사용자가 NEXT로 승격 시에만 참조)
- `v0.2/.ai/archive/*` — 폐기된 문서 (필요 시 사용자가 지시)
- `v0.1/.ai/*` — 완료된 v0.1 히스토리

---

## 브랜치 전략
- `main`: 안정 릴리스 전용, 보호됨
- `dev` : 개발 통합 브랜치
- `renew/data-architecture`: v0.3 개발 브랜치
- `chore/*`, `feat/*`, `fix/*`: 작업별 브랜치 (위 브랜치에서 분기)

---

## 빌드 및 실행 명령어 (파일 내용 읽지 말 것)

    python3 src/sync.py --source all --days 7      # 데이터 동기화
    python3 -m pytest tests/                       # 테스트
    python3 scripts/check_docs.py                  # 문서 정합성 검증 (15개 검사)
    python3 scripts/gen_files_index.py             # 파일 인덱스 재생성
    python3 scripts/gen_metric_dictionary.py       # 메트릭 사전 재생성

---

## 문서 관리 규칙

- 파일/디렉토리 설명의 유일한 소스는 **코드의 docstring**
  - 디렉토리 설명: `__init__.py` docstring
  - 파일 설명: 각 `.py` 모듈 docstring 첫 줄
- 문서 정합성 확인: `/doc-sync` (코딩 중 수시로)
- 커밋 전 전체 검증: `/pre-commit`

---

## 핵심 규칙
→ 코딩/워크플로우/MCP 상세 규칙은 `.claude/rules/` 자동 적용


---

## Who Is Claude Code
시니어 Python 엔지니어로서 깔끔하고 테스트 가능한 코드를 작성한다.
작업 전 반드시 plan을 세우고 승인을 요청한다.
불필요한 칭찬이나 장황한 설명 없이 핵심만 전달한다.
파일 생성과 수정은 확인 없이 진행하되, 설계 변경은 반드시 확인한다.
