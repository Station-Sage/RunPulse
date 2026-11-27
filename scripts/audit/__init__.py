"""자동 감사(autopilot audit) 도구 — 화면·API 커버리지 인벤토리, 셀 원장, 기계 감지 스윕.

감사가 "어디를 봤고 어디를 못 봤는지"를 기계적으로 알 수 있게 한다(P1 inventory.py).
sweep.py(+sweep_pw.mjs)는 합성 DB 로 화면×상태×뷰포트를 방문해 결함 후보를 감지하고 원장에 기록한다(P2).
perspectives.py·agents.py 는 이슈 셀을 관점별(ui/ux/data/value/persona) 모델로 트리아지해 real/noise 를 가른다(P3).
cycle.py 는 페이싱 확인→브라우저 스윕(필수, 실패 시 sweep_failed 로 중단)→관점 감사+review.py 독립 검토→텔레그램 요약을 1회 수행하고 cycles.jsonl 에 기록하며, procs.py 는 자식 서버를 등록·회수한다(P4). loop.py 는 감사→설계(triage.py 등급 분류: 위험 가드+작성·교차 검토 통과 시 자체 승인 queued, 아니면 needs_decision+결정 보고서)→개발(verify)→테스트(스윕 없이 done 처리)를 단계 1개씩 상태 파일로 이어 가는 중첩 반복기다(P6). 브라우저 전체 스윕은 단위마다 돌리지 않고 라운드 종료 시 운영 반영 직전 1회만 수행하며 실패하면 수정 단위(SWEEP-*)를 큐에 올려 개발로 되돌아가 고친 뒤 재스윕하고(최대 SWEEP_FIX_LIMIT 회, 초과 시 반영 보류) 통과해야 반영한다.
버전 사이클(S0~S5): release_plan.py(버전→이니셔티브→항목 계획 원본)·docs_ctx.py(비전·버전·설계 문서를 역할별로 에이전트 프롬프트에 주입, 트리 v0.3/data/releases/)·propose.py·wake.py(결정 대기 후 재개)·orchestrator.py(결정적 단계 전이·안정화 게이트)·planner.py(버전 계획 작성, 사용자 승인 대기)·idesign.py(이니셔티브 설계)·versioning.py(버전 승인·종료·다음 버전)·steward.py(비전 개정 제안만, 적용은 사용자 승인)·roles.py(역할별 일시정지·건너뛰기·재실행 플래그, ROLE_PAUSE 로 정지).
"""
