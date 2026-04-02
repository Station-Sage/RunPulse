# BACKLOG.md — RunPulse 작업 추적

## 상태
v0.3 | 1139 tests | DB 3.1 | fix/metrics-everythings

## NOW

## NEXT
- INFRA-1: 앱 자체 Google OAuth 로그인
- INFRA-2: REST API /api/v1 (INFRA-3 완료됨, 진행 가능)
- REFAC-4: helpers.py 915줄 분리
- REFAC-5: db_setup.py 968줄 분리
- **AI-TIER**: 무료/유료 API tier별 토큰·컨텍스트·tool 라운드 차등화
- **AI-RULE-SPLIT**: rule based에 km별 스플릿 직접 조회 기능 추가
- **STRAVA-STREAM-TIME**: Strava 스트림 재동기화 시 time 스트림 확인

## BUGS
- BUG-PWA: manifest IP→도메인 변경 → [상세](BUGS_DETAIL.md#bug-pwa)
- BUG-TRAIN-HDR: plan 없을 때 헤더버튼 숨김 → [상세](BUGS_DETAIL.md#bug-train-hdr)
- BUG-TRAIN-MAP: 오늘 러닝 2개 자동매핑 (판단 필요) → [상세](BUGS_DETAIL.md#bug-train-map)
- BUG-TRAIN-IMP: 가져오기 미리보기 필수 (판단 필요) → [상세](BUGS_DETAIL.md#bug-train-imp)
- BUG-TRAIN-DATE: 목표일자→훈련기간 자동셋팅 → [상세](BUGS_DETAIL.md#bug-train-date)
- BUG-TRAIN-GOAL: 목표→wizard 프리필 → [상세](BUGS_DETAIL.md#bug-train-goal)
- BUG-REQ: requirements.txt 컨테이너 대응 → [상세](BUGS_DETAIL.md#bug-req)
- BUG-IMPORT-USER: import_history.py --user 미전달 → default DB 사용 → [상세](BUGS_DETAIL.md#bug-import-user)