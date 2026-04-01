# BUGS_DETAIL.md — 미해결 버그 상세

읽기 조건: 해당 BUG ID 작업 시에만 참조

---

## BUG-PWA
**manifest IP→도메인 변경**

과거 IP 기반으로 작성된 PWA manifest가 남아있음.
도메인 기반으로 변경하거나, 없다면 신규 작성.

파일: `static/manifest.json` (또는 해당 경로 확인)

---

## BUG-TRAIN-HDR
**plan 없을 때 헤더 버튼 전체 숨김**

훈련 계획이 없는 상태에서 헤더 영역의 액션 버튼들이 전부 숨겨짐.
최소한 "계획 생성" 버튼은 노출되어야 함.

파일: `src/web/views_training.py`, 관련 템플릿

---

## BUG-TRAIN-MAP
**오늘 러닝 2개일 때 자동매핑 규칙 미정 (판단 필요)**

오늘의 훈련 자동 매핑에서 당일 러닝 활동이 2개 이상일 경우 어떤 것을 매핑할지 규칙이 없음.

옵션:
- A: 훈련 계획 타입과 실제 활동 타입 비교 → 가장 유사한 것 매핑
  - 문제: 계획이 이지런인데 사용자가 템포런만 뛰었을 경우 매핑 실패
- B: 사용자에게 알림/모달 띄워서 직접 선택
  - 문제: 매번 선택 강요
- C: 시간순 첫 번째 활동 자동 매핑 + "변경" 버튼 제공
  - 절충안: 기본은 자동, 필요 시 수동 변경

판단 필요: 사용자 확인 요청

---

## BUG-TRAIN-IMP
**기존 훈련 가져오기 — 미리보기 필수 (판단 필요)**

외부 훈련 데이터 가져오기 시 "미리보기" 버튼을 눌러야만 실제 적용됨.
의도된 동작인지 사용자 확인 필요.

가능성:
- 의도된 UX: 미리보기로 확인 후 "적용" → 2단계 확인
- 버그: 가져오기 클릭만으로 적용되어야 하는데 미리보기가 끼어든 것

판단 필요: 사용자 확인 요청

---

## BUG-TRAIN-DATE
**목표 일자 → 훈련기간 자동 셋팅**

훈련 계획 생성 wizard에서 레이스 목표 일자를 선택할 경우:
1. 오늘 ~ 목표일 사이 주수를 자동 계산하여 훈련 기간 프리셋
2. 훈련 캘린더에 해당 일자를 "레이스 데이"로 시각적 표시 (아이콘/배지)

현재: 목표 일자와 훈련 기간이 독립적으로 입력되어 미스매치 발생 가능

파일: wizard UI + `src/training/planner.py` + 캘린더 렌더러

---

## BUG-TRAIN-GOAL
**목표 → wizard 프리필 + 추천 워크플로우**

목표 관리에 레이스 일자/목표 시간(페이스)이 이미 설정되어 있을 경우:

1. 훈련 계획 생성 버튼 클릭 시 → 기존 목표 데이터를 wizard에 프리필
   - 거리, 목표 시간, 레이스 일자, 훈련 기간(자동 계산)
2. 목표 설정 과정의 마지막 단계에서:
   - "훈련 프로그램을 추천받으시겠습니까?" 모달/프롬프트 표시
   - Yes → 훈련 계획 wizard 자동 오픈 + 프리셋 데이터 채움
   - No → 목표만 저장하고 종료

현재: 목표와 훈련 계획이 완전히 분리되어 수동으로 동일 데이터를 재입력해야 함

파일: 목표 UI + wizard UI + `src/training/goals.py`

---

## BUG-REQ
**requirements.txt 컨테이너 환경 대응**

VPS에서 Docker 컨테이너로 실행되는 환경.
현재 requirements.txt가 Termux 환경 기준인지, 범용인지 확인 필요.
컨테이너용 Dockerfile 또는 별도 requirements 필요 여부 검토.

파일: `requirements.txt`, `Dockerfile`(신규 가능)

---

## BUG-IMPORT-USER
**import_history.py user_id 미전달**

`src/web/app.py`의 import 관련 subprocess 호출에서 `--user` 인자를 전달하지 않음.
`src/import_history.py`도 `--user` 인자를 받지 않고, `get_db_path()`를 인자 없이 호출하여 항상 default DB에 접근.

수정 필요:
1. `src/import_history.py`에 `--user` argparse 인자 추가
2. `get_db_path(args.user)` 전달
3. `src/web/app.py` import subprocess 호출에 `--user` 추가

파일: `src/import_history.py`, `src/web/app.py`