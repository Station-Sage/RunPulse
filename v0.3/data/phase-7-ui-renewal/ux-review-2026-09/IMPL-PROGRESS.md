# UX 리뷰 로드맵 구현 진행 (체크포인트)

세션 한도·재시작 대비 재개용. 로드맵 원본: `99-summary.md §7`, 결정: `../DECISIONS.md [P7-UX-REVIEW-0928]`.

## 작업 규칙
- 작업 위치: worktree `/home/ubuntu/projects/RunPulse-p0` (브랜치 `claude/project-thread-vgunp6`).
  메인 폴더 `/home/ubuntu/projects/RunPulse`는 운영 컨테이너가 `--reload`로 마운트 → 직접 편집 금지.
- 운영 반영: 메인 폴더 `renew/data-architecture`에 ff 병합 → `frontend`에서 `npm run build` → (Dockerfile 변경 시) `docker compose build && up -d`.
- 테스트: `$V -m pytest tests/`(venv: 스크래치 `venv`, 없으면 `python3 -m venv` + `pip install -r requirements.txt pytest`), `cd frontend && npm run test:unit && npm run check`.
  기존 실패(무시): `test_plan_service` 2건, worktree에서 `test_autopilot_run_unit` 3건.
- 실 DB 변경 전 백업: `data/users/pansongit@gmail.com/running.db` → `running.db.bak-<날짜>-<사유>`.
- 한도(429) 걸리면 해제 시각 직후로 재개.

## 상태
| 단계 | 상태 | 커밋/메모 |
|---|---|---|
| Phase 0 핫픽스 | 완료·운영 반영(2026-09-28 08:40) | d31511b |
| 1-1 부하 모델 재기준화(PMC α=1/τ, TRIMP 계수, 재계산) | 진행 중 | |
| 1-2 등급 SSOT | 대기 | |
| 1-5 이행 재정의 | 대기 | |
| 1-6 동기화 원장 | 대기 | |
| 1-3, 1-4, 1-7 | 대기 | |
