"""자동 감사(autopilot audit) 도구 — 화면·API 커버리지 인벤토리, 셀 원장, 기계 감지 스윕.

감사가 "어디를 봤고 어디를 못 봤는지"를 기계적으로 알 수 있게 한다(P1 inventory.py).
sweep.py(+sweep_pw.mjs)는 합성 DB 로 화면×상태×뷰포트를 방문해 결함 후보를 감지하고 원장에 기록한다(P2).
perspectives.py·agents.py 는 이슈 셀을 관점별(ui/ux/data/value/persona) 모델로 트리아지해 real/noise 를 가른다(P3).
"""
