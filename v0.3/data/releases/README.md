# releases — 비전·버전업·설계 문서 (오토파일럿 에이전트 필독)

오토파일럿 역할 에이전트(비전 관리자·버전 기획자·설계자·개발자·검증자·감사자)가 작업 전 읽는 문서 트리다.
에이전트 프롬프트에는 `scripts/audit/docs_ctx.py` 가 아래 순서로 발췌해 주입한다(역할별 상한 있음).

## 폴더 구조

    v0.3/data/releases/
      README.md                      ← 이 파일: 규약 + 읽는 순서 (모든 역할)
      VISION.md                      ← 제품 본질·원칙·비목표의 단일 원본. 변경은 사용자 승인 후에만
      vision-proposals/
        YYYY-MM-DD-<slug>.md         ← 비전 관리자가 쓰는 변경 제안(diff 형태). 적용은 사용자가 한다
      vN/                            ← 버전 단위 (v1, v2, ...)
        PLAN.md                      ← 버전 기획서: 목표·이니셔티브 목록·범위 밖·안정화 기준
        RETRO.md                     ← 안정화 게이트 통과 시 회고(남은 결함·다음 버전 후보)
        initiatives/
          INI-<slug>/
            DESIGN.md                ← 이니셔티브 설계서: 목표·범위·범위 밖·완료 기준·항목 분해

런타임 상태(문서 아님)는 `.claude/autopilot/release_plan.json` 에 둔다. 문서가 *왜·무엇*, JSON 이 *지금 어디*다.

## 역할별 읽는 순서

| 역할 | 읽을 것 | 쓸 것 |
|------|---------|-------|
| 비전 관리자 | VISION.md, 최근 vN/RETRO.md | vision-proposals/*.md (제안만) |
| 버전 기획자 | VISION.md, 직전 vN/RETRO.md, 기존 PLAN.md | vN/PLAN.md(초안 → 사용자 승인) |
| 설계자 | VISION.md, vN/PLAN.md, 해당 INI 의 DESIGN.md(있으면 이어쓰기) | vN/initiatives/INI-*/DESIGN.md |
| 개발자·검증자 | 해당 항목의 INI DESIGN.md(범위·완료 기준) | 코드·테스트 |
| 감사자 | VISION.md, 현재 PLAN.md 의 범위 밖 목록 | (결함 후보만) |

## 규약

1. VISION.md 는 에이전트가 직접 고치지 않는다. 변경은 vision-proposals 에 제안 → 사용자가 적용.
2. PLAN.md·DESIGN.md 는 상단 front-matter(`status: proposed|approved|active|done|rejected|parked`)를 가진다. status 의 원본은 release_plan.json, 문서는 사람이 읽는 사본.
3. 이니셔티브 ID 는 `INI-<slug>`(소문자·숫자·하이픈), 항목 key 는 이니셔티브 안에서 유일. 큐 항목 ID 는 `AUD-sha(INI-id+key)` 로 재진입에 멱등.
4. 모든 이니셔티브는 원칙 번호(1~8)와 *러너가 지금 앱에서 답을 못 얻는 질문* + 코드 증거(path:line)를 근거로 둔다.
5. DESIGN.md 는 완료 기준을 *실행 가능한 검증 명령*으로 쓴다(LLM 판단 금지). 모든 항목이 done 이고 명령이 통과해야 이니셔티브 done.
6. 문서 한 파일 300줄 이하. 초과 시 INI 를 나눈다.
