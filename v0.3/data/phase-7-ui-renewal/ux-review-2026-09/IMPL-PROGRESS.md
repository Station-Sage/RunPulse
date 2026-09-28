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
| 1-1 부하 모델 재기준화(PMC α=1/τ, TRIMP 계수, 재계산) | 완료·운영 반영(2026-09-28 12:45, 백업 `running.db.bak-20260928-pre-pmc-v2`) | d43dedf. 남음: Today 1회성 변경 알림(10 S0 명세) — 2-1 공통 규격 때 함께 |
| 1-2 등급 SSOT | 완료·운영 반영(2026-09-28 13:30, bbb66de) | `src/metrics/bands.py`, API status·status_label, 프론트 등급표 4벌 제거, consistency 검사 17. 남음: formChart 레이스 최적 음영 [5,25] 상수(시각 밴드) |
| 1-5 이행 재정의 | 완료·운영 반영 | `src/training/week_compliance.py`(R1 유효 계획·R2 분모·R3 세 수치·R5 라벨, 읽기 시점 계산), API `compliance`·`week.days`, 계획 화면·NextSessionCard. 보류: R4 매칭 게이트(재매칭 = 실 DB 변경), R9 CTL 궤적, R5 강도 판정은 평균 페이스 근사(스트림·HR존 미사용) |
| 1-6 동기화 원장 | 완료·운영 반영 | `sync_state_service`·`GET /api/v1/data/sync-state`, `get_last_sync_at` 원장 파생. 보류: sync_jobs 열 확장(error_code 등)·4경로 오류 기록(Strava 403이 completed로 남는 문제 = SYNC-ERROR-SURFACE), 프론트 표면(4-1) |
| 1-3 활동 파생 수치 | 코드 완료(68e7635)·1-3 단독 사본 검증 완료(17414 RE 302→93, 910 1221→445, TRIMP 불변) → 1-4·1-7과 합쳐 사본 재검증·배포 | RE 선수 최대심박+스트림 존(conf 0.85/폴백 0.6 숨김), Friel 디커플링(백엔드 단일), TE Garmin 구간, 이동시간 스플릿·⏸, 활동 VDOT 대회·템포만 표시, 소스 비교 캐노니컬·comparable·항목별 임계·케이던스 정규화. 보류: 날씨 category 백필·형제 고유 메트릭 병합·PB 공식 기록(S1 나머지), providers `unit` 세부 |
| 1-4 그룹당 1회 계산 | 코드 완료(edd2d52) → 합산 사본 검증·배포 | `src/utils/canonical.py`, CalcContext `get_group_metric`·`get_group_streams`, 엔진 캐노니컬만 계산·`prune_noncanonical_runpulse`, 상세·소스 비교 캐노니컬 RunPulse 값, consistency 18·19. 남음: 재매칭 시 그룹 재계산 트리거(현재는 다음 재계산 창에서 정리), C4 매트릭스 쌍 비교(3-8) |
| 1-7 GAP v2 | 코드 완료(8d2b9ad) → 합산 사본 검증·배포 | 고도 30m 창 경사, 곱셈 보정, 정지 제외, 경사 없으면 미산출. **설계 예시 4:25(5%)는 Minetti가 아니라 경험 모델 값** — Garmin GAP 대비 오차로 모델 판단 필요. 남음: Garmin gap_speed_ms 소스 GAP 저장(④) |
