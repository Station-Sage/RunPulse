---
name: project-pred-r4
description: 예측 리뉴얼 r4(2026-09-26) — r3 기본+r4 섀도 결정, 거리별 전력 판정, 명세 31단계 적용 검증 완료, 명세 생성기 위치
metadata:
  type: project
---
상태(2026-09-26): specs/PRED-* r4 전 유닛 코드 명세 작성·새 사본 적용 검증 통과(31단계, 전체 pytest 실패는 autopilot 워크트리 부재 3건뿐). svelte-check·build는 미실행(사용자가 npm check 실행을 거부함 → 사람 확인).

- 사용자 결정: r3 (c) 기본 표시 유지, r4는 섀도 provider(runpulse:shadow_r4, _asym)로 병행 + prediction_snapshots(PRED-63) 전향 평가 후 전환은 사용자 결정. 85·87~90 승인, 86은 "통합".
- 9/12 Forest run = 최대 이하(paced). 전력 판정은 단일 %HRmax 임계 금지 → effort.py(지속시간별 평균HR/LTHR 기대 + 최대HR 도달, 대회일 HRmax, 사용자 effort 우선, uncertain은 확인 요청). 평균 HR만으로는 9/12와 5/9 PB 구분 불가.
- 분석 반복에 턴을 많이 써서 조정자가 "결론이 바뀔 때만 분석" 지시 — 다음엔 명세·검증 우선.
- 명세 생성기: /home/ubuntu/rp_specwork/specgen (main.py → finalize(ORDER) 지연 Stager, apply_test.py), 샌드박스 sb/, r3 중간본 /tmp/rp_sandbox(휘발 주의).

**Why:** 재개·후속 수정 시 구조를 다시 파악하지 않도록. **How to apply:** 명세 수정은 sb 코드 수정 → specgen main.py → apply_test.py 순. /tmp/rp_sandbox 가 사라졌으면 R3 중간본 diff(11·53·63 두 단계 파일) 재구성 필요.
