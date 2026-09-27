# v2 미구현 영역 — 러닝 데이터(통합·소유권) 리뷰

**리뷰일**: 2026-09-27 · **대상**: v2에서 비어 있거나 반만 있는 영역. ☰ Data(동기화 상태·지금 동기화·소스 연결·아카이브 임포트·재계산·내보내기·설정/프로필·AI 제공자), 계획 비교(`/v2/coach/plan/compare`), Story(주간·월간·블록 이야기), 웰니스 일자별(`/library/wellness/:date`), v2를 기본 진입으로 바꿀 때의 데이터 전제
**관점**: 러닝 데이터 전문가. 미구현이나 결손이 **러너의 결정**(훈련·회복·레이스)과 **데이터 신뢰**에 주는 영향을 본다.
**범위 메모**: v1은 평가하지 않는다. v1 화면과 코드에서는 v2가 계승하거나 참고할 데이터 기능만 뽑는다(§A). 백엔드 API의 재사용 가능 여부는 §B에 정리했다.

요약:
- **"마지막 동기화"의 진실 원천이 세 곳이고 값이 모두 다르다.** `sync_state.json`(Garmin 2026-05-11 09:39), `sync_jobs.updated_at`(2026-09-27 10:46), `source_payloads.fetched_at`(2026-09-27 11:56:47 UTC)이다. 자동 동기화는 `sync_state`를 갱신하지 않는다. v2 Today의 as-of 줄 "오늘 지금까지 반영"은 **날짜만 비교해서** 신선하다고 말한다. v2를 기본 진입으로 삼으려면 동기화 시각 하나를 정의하는 일이 가장 먼저다.
- **소스 실패가 러너에게 보이지 않는다.** Strava 403이 `completed, count=0`으로 몇 주간 기록되었다(BACKLOG SYNC-ERROR-SURFACE). 지금 Strava job은 `stopped / "프로세스 재시작으로 중단됨" / resumable`으로 남아 있는데, 이 소스는 사용자가 끈 상태다. v2에는 오류를 볼 곳이 없고, 빠진 데이터는 "휴식일"처럼 보여 CTL을 과소평가하게 만든다. 전례가 있다: 2026-05~09 CTL이 0으로 수렴했는데 아무도 몰랐다(DATA-FITNESS-GAP).
- **v2는 "동기화를 실행하세요"라고 말하면서 실행할 곳을 주지 않는다.** ☰가 `disabled`이고(`+layout.svelte:29-36`), `healthNotice.ts:14`, `providerHint.ts:9`, Today 빈 상태 문구가 모두 막다른 곳이다.
- **개인 기준값(HRmax·LTHR·역치 페이스)이 세 벌이고, 사용자가 보거나 고를 곳이 v2에 없다.** config `user.max_hr`(v1 존 분석), 자체 추정 HRmax 192·LTHR 177.5(예측), Garmin LTHR 168이다. v1 프로필 저장 키(`threshold_pace`)와 계획 엔진이 읽는 키(`threshold_pace_sec_km`)가 달라서 사용자가 입력한 역치 페이스는 무시된다.
- **계획 비교는 선택지 1개짜리 "비교"이고, 예측 기록이 Today와 15분 다르다.** 템플릿 API는 9주 압축 1건만 준다. 예상 완주 3:25:51이 Today 예측 3:40:23보다 낙관적이고, 위험도 "낮음"과 "훈련 기간이 최적보다 짧습니다"가 한 카드에 같이 적혀 있다.

---

## 영역별 준비도 (0~10, v2 기본 진입 기준)

| 영역 | 준비도 | 백엔드 | v2 프론트 | 한 줄 |
|---|---|---|---|---|
| 동기화 상태·마지막 시각 | **2** | 값 3종이 서로 어긋남 | as-of가 날짜만 봄 | 진실 원천부터 정의해야 함 |
| 지금 동기화(기본·기간) | 3 | `/trigger-sync-bg`, `/bg-sync/status` 있음(비-JSON API, v1 경로) | 없음 | API 이관만 하면 재사용 가능 |
| 소스 연결(4종) | 3 | `/connect/*` HTML 폼 + OAuth, `check_*_connection` | 커버리지 띠에 "데이터 있음"으로만 추정 | 자격증명 상태 API 없음(`data_service.py` 스텁) |
| 소스 오류 표시 | **1** | 403이 completed로 기록됨 | 없음 | 신뢰를 가장 크게 깎는 결손 |
| 아카이브 임포트 | 3 | Strava zip·FIT/GPX·폴더 임포트 있음 | 없음 | 미리보기·중복 보고 설계 필요 |
| 재계산 | 3 | `/metrics/recompute*` 있음(GET이 부작용을 냄, 메모리 상태) | 없음 | 잡(job) 모델로 바꿔야 함 |
| 내보내기 | 2 | 활동 CSV(요약 14열), 계획 ICS | 없음 | 메트릭·웰니스·원본 payload 없음 |
| 설정·프로필(기준값) | 2 | v1 폼, 키 불일치 | 없음 | 기준값 3중 → 러너가 고를 곳 필요 |
| AI 제공자·전송 고지 | 3 | provider 체인 있음 | Coach에 "규칙 기반 답변" 라벨만 있음 | 무엇이 외부로 나가는지 고지 없음(P8) |
| 계획 비교 | 4 | 템플릿 API 동작(7ms) | 화면 있음, 1건·직접 진입 시 400 원문 | 예측 모델 불일치 |
| Story(주간·월간·블록) | 3 | 월간 규칙 내러티브(`?year&month`) | Today 인페이지 펼침만 있음 | 주간·블록·기간 비교 없음 |
| 웰니스 일자별 | **6** | `?date=` 지원(확인) | `getWellnessDetail(date)` 있음, 라우트만 없음 | 가장 싸게 채울 수 있는 영역 |

---

## 발견

### [치명] F-DATA-01 "마지막 동기화" 값이 저장소 3곳에서 서로 다르고, v2는 날짜만 보고 "오늘 지금까지 반영"이라고 말한다
- 현상: 같은 계정의 같은 시점에 값이 셋이다. ① v1 동기화 탭은 "마지막 동기화: 2026-05-11 09:39"(Garmin), Strava·Intervals 2026-05-08 11:09로 표시한다. 출처는 `sync_state.json`이다. ② v1 대시보드는 "마지막 동기화: 2026-09-27T10:46"이고 출처는 `sync_jobs.updated_at`이다. ③ API `/library/providers/status`는 garmin `2026-09-27 11:56:47`, intervals `07:52:26`, strava `2026-06-23 14:13:16`이고 출처는 `MAX(source_payloads.fetched_at)`, UTC이며 타임존 표기가 없다. 컨테이너 로컬 시간은 KST다(`docker exec … date` 확인). ①과 ②는 로컬 시각, ③은 UTC다. v2 Today의 as-of 줄은 `asOf.ts:1-5`에서 `status.date === 오늘`이면 무조건 "오늘 지금까지 반영"이라고 쓴다.
- 근거: `v1-sync-mobile.png`(상단 "마지막 동기화 2026-05-11", 같은 화면의 자동 동기화 "마지막 실행 2026-09-27T12:40:05"), `raw/v1-root.txt`, `helpers.py:891-903`(`sync_state.get_last_sync_at`), `views_dashboard.py:55-64`(`sync_jobs`), `provider_status_service.py:28-31`. 자동 동기화 `auto_sync._trigger`는 `start_basic_sync`→`sync_jobs`만 쓰고 `mark_finished`를 부르지 않는다(`sync_state`에 기록하는 곳은 `app.py:608-655` 수동 경로와 `sync.py:59`뿐).
- 왜 문제인가: P8은 "마지막 동기화 시각 상시 표시"를 요구한다. 그런데 어느 값을 올려도 틀린 경우가 생긴다. ①은 4개월 전 값이라 "앱이 멈췄다"는 오해를 부른다. ③은 **새 payload가 들어온 시각**이어서, 동기화는 성공했지만 새 데이터가 없는 날(휴식일)에는 과거에 멈춰 보인다. 반대로 실패한 시도는 드러나지 않는다. 러너가 아침에 "어젯밤 달리기가 반영된 TSB인가?"를 판단할 근거가 없다. 오늘 권고가 어제 활동 없이 계산되었다면 TSB와 권고가 달라진다(과소 피로).
- 개선안(설계):
  - **동기화 원장(ledger) 한 곳**: 소스별로 `attempted_at`(마지막 시도), `succeeded_at`(마지막 성공), `last_new_data_at`(마지막으로 새 데이터가 들어온 시각), `last_error{code, message, at}`, `trigger`(auto/manual/range)를 둔다. `sync_jobs`를 이 원장으로 승격하고, `sync_state.json`은 원장을 읽는 파생값으로만 남긴다(ADR 필요).
  - 모든 시각은 **오프셋이 붙은 ISO**(`2026-09-27T20:56:47+09:00`)로 내보내고, 표시는 상대 시간 + 툴팁 절대 시각으로 한다.
  - v2 as-of 줄은 `9월 27일 · Garmin 20:56 동기화` 형식으로 바꾸고, 원장의 `succeeded_at`이 6시간 넘게 지났거나 오늘 활동 없이 계산된 경우 `어제 밤 이후 동기화 없음 · 지금 동기화 ›`로 바뀌게 한다. 탭하면 ☰ Data 시트가 열린다.

### [치명] F-DATA-02 소스 실패가 러너에게 보이지 않는다 — 빠진 데이터는 "쉰 날"로 계산된다
- 현상: Strava는 API 구독 전환으로 403(`Application Status: Inactive`)을 받았는데, job은 `completed, count=0`으로 몇 주간 기록되었다(BACKLOG SYNC-ERROR-SURFACE). 지금 `GET /bg-sync/status?source=strava`는 `status: stopped, last_error: "프로세스 재시작으로 중단됨", resumable: true`이다. 사용자가 이 소스를 동기화 대상에서 **껐는데도** 재개 대기로 남아 있다. v1은 같은 Strava를 "토큰 만료 — 다음 sync 시 자동 갱신됩니다"로 표시한다. 실제 원인(403 구독)과 다르다. v2에는 오류를 표시하는 곳이 한 곳도 없다.
- 근거: `bg-sync/status` 응답(확인), `v1-sync-mobile.png`, BACKLOG.md:20-21, `bg_sync.py:460`(끈 소스는 새 잡에서 제외하지만 기존 잡 상태는 정리하지 않음).
- 왜 문제인가: 부하 지표(ATL/CTL/TSB/ACWR)는 **활동이 없으면 0 부하**로 계산한다. 소스가 조용히 실패하면 러너는 실제보다 신선하다는(TSB↑, ACWR↓) 권고를 받아 과부하 쪽으로 오판한다. 이 결손은 2026-05~09 실제로 일어났다(CTL이 0.4로 수렴, BACKLOG DATA-FITNESS-GAP). 비전 1원칙(통합)에서 "통합이 끊겼다"는 사실이 가장 중요한 데이터다.
- 개선안:
  - 원장(F-DATA-01)의 `last_error`를 **분류 코드**로 저장한다: `auth_expired`, `auth_revoked`, `subscription_required`(403), `rate_limited`(retry_after 포함), `upstream_5xx`, `interrupted`. 코드마다 러너용 문장과 행동을 하나씩 짝짓는다(예: `subscription_required` → "Strava가 API 접근을 막았어요. Garmin 데이터로 계속됩니다 · Strava 끄기").
  - **전역 신호**: 연결된 소스 중 하나라도 `succeeded_at`이 24시간 넘게 지났거나 `last_error`가 있으면 ☰ 버튼에 점 배지를 달고, Today as-of 줄을 amber로 바꾼다. 부하 지표 근거 칩에는 "Strava 미수신 3일 — 부하가 낮게 나올 수 있음" 한정 문구를 붙인다(현재 `healthNotice`의 TRIMP 누락 문구를 확장).
  - 소스를 끄면 그 소스의 대기 잡도 `cancelled`로 정리한다.

### [치명] F-DATA-03 v2는 "동기화를 실행하세요"라고 안내하지만 실행 경로가 없다
- 현상: ☰ 버튼이 `disabled aria-label="메뉴 (준비 중)"`이다. v2에서 동기화를 권하는 문구는 세 곳이다. `healthNotice.ts:14` "동기화를 실행하면 자동으로 보정됩니다", `providerHint.ts:9` "동기화를 실행해 보세요", Today 빈 상태 "Garmin, Strava 등 소스를 연결하면…"(`today/+page.svelte:87-89`). 셋 다 누를 곳이 없다.
- 근거: `+layout.svelte:29-36`, `01-sitemap.md` §0, `v2-root-*.png`.
- 왜 문제인가: v2 단독 사용자는 신규 가입 후 데이터를 넣을 수 없다. 기존 사용자는 데이터가 틀려 보여도 고칠 수 없어 v1으로 돌아가야 한다. P4("관리는 ☰에서") 경로가 끊겨 있고, v2 기본 진입 전환의 **차단 조건**이다.
- 개선안: 7d 전체를 기다리지 말고 **☰ Data 최소 시트(MVP)**를 먼저 연다. ① 소스 4행(상태 점 · 마지막 성공 · 오류 문장 · [지금 동기화]) ② 진행 표시(`bg-sync/status` 폴링, 날짜 창 진행률 `completed_days/total_days`) ③ "자세히 → /v2/data". 안내 문구 3곳은 이 시트를 여는 버튼으로 바꾼다.

### [중요] F-DATA-04 소스 "연결"은 데이터 유무로만 추정되고, 4번째 소스(Runalyze)는 v2에서 존재 자체가 사라진다
- 현상: v2의 유일한 소스 표면은 Library 홈 "소스 커버리지"다. 이 표면은 `has_data`(활동 수 또는 payload 존재)로 연결을 추정한다. 코드 주석도 "연결 여부는 7d Data 화면(data_service)의 몫"이라고 적고 있다. `SourceCoverage.svelte:18`은 `sync_enabled=false && total=0`인 소스를 숨기므로 Runalyze는 v2 어디에도 나타나지 않는다. 정상 경로(coverage 성공)에서는 마지막 동기화 시각도 보이지 않는다. 시각은 coverage가 실패할 때 나오는 대체 목록에만 있다(`library/+page.svelte:135-160`). `data_service.py`는 docstring만 있는 스텁이다.
- 근거: `raw/library.txt:109-120`, API `providers/coverage`(runalyze total 0, sync_enabled false 확인), `src/services/data_service.py`.
- 왜 문제인가: 비전의 "4소스 통합"이 v2에서는 3소스로 보인다. 연결은 되어 있지만 데이터가 오래된 경우와 연결이 끊긴 경우가 구분되지 않는다. P3(출처 투명성)의 기반이 없다.
- 개선안: `GET /api/v1/data/sources`를 신설한다. 기존 `check_{garmin,strava,intervals,runalyze}_connection`과 원장, config `sync_sources`를 합쳐 소스별 `{connection: connected|expired|error|not_connected, sync_enabled, last_success, last_error, counts{activities, wellness_days}, coverage_first/last}`를 반환한다. v2 소스 카드는 연결 상태와 동기화 포함 여부(on/off)를 **별개 축**으로 보여준다(끈 소스 = 회색 "동기화 안 함 · 과거 202건 보존").

### [중요] F-DATA-05 내보내기가 "활동 요약 CSV" 수준이라 데이터 소유권(P8)을 증명하지 못한다
- 현상: 내보내기는 `/activities/export.csv`(14열: 소스·시작·거리·초 단위 시간·초/km 페이스·심박 등)와 계획 ICS 두 가지다. RunPulse 계산 메트릭(`metric_store`, 공식 버전 포함), 웰니스(1,087일), 랩·스트림, 원본 payload, 체크인·코치 대화는 내보낼 수 없다. `GET /api/v1/data/export`는 설계 요건인데 로드맵 어느 단계에도 배정되지 않았다(`phase-7 BACKLOG.md:80`). DB 크기는 788MB다(`raw/v1-settings.txt`).
- 왜 문제인가: "클라우드 잠금 없음"과 "내 아카이브"는 비전 핵심이다. 러너가 RunPulse를 떠나거나 다른 도구(Excel·Intervals 수동 분석)로 검증하려 할 때, 가장 가치 있는 부분(4소스 통합 결과와 계산 메트릭)을 가져갈 수 없다. 계산 공식 버전이 없는 메트릭 export는 재현도 안 된다.
- 개선안: `/v2/data/export`에 세 단계를 둔다. ① **빠른 CSV**: 활동(통합 대표값 + 소스별 원값 열), 일별 웰니스, 일별 부하(CTL/ATL/TSB/ACWR). 사람용 열(`h:mm:ss`, `m:ss/km`)과 기계용 열(초)을 모두 넣는다. ② **전체 아카이브 zip**(비동기 잡): 테이블별 CSV/Parquet + `metric_store`(provider·formula_version·computed_at) + 원본 payload JSON + `manifest.json`(스키마 버전, 생성 시각, 행 수). ③ 기간·종류 필터. 완료되면 ☰ 배지와 다운로드 링크를 주고, 링크는 7일 뒤 만료된다.

### [중요] F-DATA-06 개인 기준값(HRmax·LTHR·역치 페이스)이 세 벌이고, v1 입력값 일부는 저장 키가 달라 무시된다
- 현상: HRmax는 config `user.max_hr`(v1 프로필 기본 190, `zones_analysis.py:35`가 사용), 자체 추정 192(`hrmax_self`, 예측·존), Garmin 참조(null)로 세 벌이다. LTHR은 자체 177.5(대회 2건 기반)와 Garmin 168.0으로 9.5bpm 차이가 난다(`/prediction/profile` 확인). v1 프로필 저장은 `config["user"]["threshold_pace"]`에 쓰는데(`views_settings.py:237`), 계획 엔진의 대체 경로는 `threshold_pace_sec_km`를 읽는다(`planner_rules.py:195`). 그래서 사용자가 입력한 역치 페이스는 VDOT·eFTP가 없을 때도 쓰이지 않는다(기본 300초). 그리고 v1 프로필 저장은 다른 라우트와 달리 `load_config()`를 user_id 없이 호출한다(멀티테넌트에서 저장 대상이 어긋날 가능성, 추정).
- 왜 문제인가: 존 경계가 9.5bpm 움직이면 "쉬운 달리기 Z2" 처방과 이행률 판정(페이스 40%·볼륨 60%)이 바뀐다. 러너는 어느 기준으로 판정되었는지 모르고, 틀려도 교정할 수 없다. U6(원천)과 P3 위반이다.
- 개선안: `/v2/data/settings/profile`을 **기준값 페이지**로 설계한다. 행마다(HRmax, LTHR, 안정심박, 역치 페이스, 주간 목표 거리) `자체 추정 | 기기 | 직접 입력` 3열과 "사용 중" 라디오를 둔다. 자체 추정 값은 근거(대회 2건 링크, 추정 시각, 신뢰도)를 보여준다. 선택을 바꾸면 "존·이행률·예측 재계산 필요 — 최근 90일 재계산(약 N초)"을 제안한다(F-DATA-07). 저장 키는 한 곳(예: `profile.overrides`)으로 모으고, 기존 키 불일치는 이관 시 정리한다.

### [중요] F-DATA-07 재계산은 결과를 설명하지 않는 "버튼"이다 — 무엇이 바뀌었는지 알 수 없다
- 현상: `GET /recompute-metrics?days=`가 **GET인데 재계산을 실행**한다(`views_settings_metrics.py:91-110`). 상태는 프로세스 메모리(`_recompute_state`)에 있어 재시작하면 사라진다. v1에서 "최근 90일 / 전체 기간" 버튼 두 개가 동기화 탭과 설정 탭에 중복으로 있다. v2에는 없다. BACKLOG DATA-CTL-WARMUP(2025-09 이전 CTL 출처 불명, 전체 재계산 필요)처럼 재계산이 필요한 데이터 결함이 실제로 대기 중이다.
- 왜 문제인가: 재계산은 과거 CTL·예측·마일스톤을 바꾼다. 러너 입장에서는 "지난주 예측 3:38이 왜 3:41이 됐지?"가 설명되지 않는 이력 변경이다. 투명한 분석(비전 2원칙)과 충돌한다.
- 개선안: POST 잡으로 바꾸고(`POST /api/v1/data/recompute {scope: 90d|all|from, reason}`) 원장에 기록한다. 완료 보고에는 **변경 요약**을 준다. 대표 지표 5개(CTL, TSB, VDOT, 마라톤 예측, UTRS)의 오늘 값 전후, 바뀐 날짜 수, 공식 버전 변경을 보여준다. 메트릭 상세에는 "2026-09-27 재계산됨(formula_v1→v2)" 이력 표식을 남긴다. 일반 러너에게는 버튼을 숨기고, 기준값 변경·임포트 뒤 제안으로만 노출한다.

### [중요] F-DATA-08 아카이브 임포트가 v2에 없어 과거 공백을 메울 방법이 없다
- 현상: 커버리지 띠를 보면 2024-03~05(전 소스 0건), Strava 2024-10~2025-04 공백이 보인다. API 창 밖의 과거는 Strava zip, Garmin bulk, FIT/GPX 업로드로만 채울 수 있는데, 이 기능들은 v1(`/import/strava-archive`, `/import/upload`, `/import-export`)에만 있다. 랩 누락(BACKLOG MARATHON-LOG-LAPS)은 "기간 동기화"로만 보충되는데, 자동 동기화 창이 14일이라 자동으로는 채워지지 않는다.
- 왜 문제인가: "수년치가 내 것으로 보이는 아카이브"(REVIEW-05)와 PB·마일스톤·장기 추세의 정확도가 과거 공백에 좌우된다. 누적 3800km 마일스톤도 공백 기간 활동을 빼고 센 값이다.
- 개선안: `/v2/data/import`는 ① 파일 선택 → ② **미리보기**(인식된 활동 N건, 기간, 기존과 중복 M건[같은 시작 시각 ±60초·거리 ±3%], 신규 K건, 스트림/랩 보강 L건) → ③ 실행(잡) → ④ 결과(신규·보강·건너뜀·오류 행 목록, 재계산 제안) 순서로 간다. 커버리지 띠의 0건 월을 탭하면 "이 기간 가져오기 — 기간 동기화 또는 파일 임포트"로 이어지게 한다.

### [중요] F-DATA-09 계획 비교: 선택지는 1개, 예상 완주는 Today 예측보다 15분 낙관적이고, 위험도와 설명이 서로 모순된다
- 현상: `GET /coach/plan/templates?distance_km=42.195&race_date=2026-11-22&target_time_sec=11940`은 `[{label:"압축 일정", weeks:9, projected_time_end:12351(3:25:51), achievability_pct:70, risk_level:"낮음", status_summary:"…VDOT 3.0 향상이 필요… 훈련 기간이 최적값(18~20주)보다 짧습니다."}]` 1건을 준다. 같은 시점 Today 예측은 3:40:23(80% 범위 3:26~4:03)이다. `/v2/coach/plan/compare`에 직접 들어가면(쿼리 없음) 400 "거리 정보가 없습니다."가 원문 그대로 뜬다(`raw/coach-plan-compare.txt`). 설계는 3~5개 병렬 비교다(`02-IA:66`).
- 근거: API 응답(확인, 7ms), `compare/+page.ts:14-17`, `compare/+page.svelte:74-91`.
- 왜 문제인가: 러너는 이 화면에서 **9주 계획을 확정**한다. 예상 완주가 다른 모델(VDOT 기반)에서 나와 목표 3:19에 근접해 보이고, 위험 "낮음"은 "기간이 짧다"는 경고와 모순된다. 낙관적인 수치로 목표를 유지하게 만들 수 있다. 비교할 대안(목표 완화, 주간 거리 하향)이 없으면 "비교"가 아니다.
- 개선안: ① 레이스일이 고정되면 주수 대신 **목표·강도 축으로 3안**을 만든다(목표 유지 3:19 고강도 / 현실 3:30 / 보수 3:40 완주 안정). 각 안에 주간 최대 거리, 품질 세션 수, ACWR 최대 예상값, 부상 위험 근거를 보여준다. ② 예상 완주는 Today와 **같은 예측 엔진**의 투영을 쓰고, 출처 배지와 80% 범위를 붙인다. ③ 위험도는 규칙 출력(기간 부족, 주간 증가율, 현재 CTL 대비 피크 부하)에서 파생시켜 설명 문장과 모순되지 않게 한다. ④ 쿼리 없이 들어오면 현재 목표로 프리필하거나 `/coach/plan/new`로 리다이렉트한다.

### [중요] F-DATA-10 Story: 월간 규칙 문단만 있고, 러너가 실제로 되돌아보는 단위(주간·블록)가 없다
- 현상: 백엔드 `/today/narrative?year&month`는 과거 달도 준다(2026-08: 183.4km/18회, CTL 53→72, 확인). v2는 이를 Today 인페이지 펼침으로만 쓴다. `/library/story`, `/library/story/:year/:month`, milestones 라우트가 없다. 주간 리뷰와 **훈련 블록(빌드·피크·테이퍼) 리뷰**가 없다. v1 레포트의 "이전 동일 기간 대비"(거리 ↑11%), 강도 분포(TIDS), 위험 지표 기간 평균·최고(ACWR 최고 1.71, LSI 최고 3.35), 효율 추세(ADTI)도 v2에 자리가 없다. `03b-story.md`는 Today로 흡수되었다는 스텁이다.
- 왜 문제인가: 마라톤 D-56 러너의 핵심 질문은 "지난 블록이 효과가 있었나, 다음 블록에서 무엇을 바꿀까"다. 월 경계는 훈련 주기와 맞지 않는다(블록은 계획의 phase 경계). 기간 비교가 없으면 성장(REVIEW-05 "내 아카이브")을 증명하지 못한다.
- 개선안: `/v2/library/story`에 단위 토글 `주 | 블록 | 월`을 둔다. 공통 골격은 ① 한 문단(규칙 기반, AI 가능 시 보강) ② **이전 동일 단위 대비 4지표**(거리·시간·부하 합·품질 세션 수, Δ%) ③ 강도 분포 막대(Z1-2/3/4-5, 목표 80/20 대비) ④ 대표 세션 3개(롱런 최장·품질 최고·레이스, 각 → 활동) ⑤ 위험 최고값과 발생일 ⑥ 예측 변화(시작 → 끝)와 원인 칩이다. 블록 경계는 활성 계획의 phase(`plan_service`의 주기화 결과)에서 가져오고, 계획이 없으면 4주 단위로 한다. 백엔드는 narrative를 `scope=week|block|month&start=&end=`로 일반화한다.

### [중요] F-DATA-11 웰니스 일자별: API는 이미 날짜를 받지만 라우트가 없고, 하루 중 값이 바뀌는데 측정 시각을 보여주지 않는다
- 현상: `GET /library/wellness?date=2026-09-20`은 core(수면 90·HRV 97·RHR 41)와 카테고리별 메트릭 34개를 준다(확인). 프런트 `getWellnessDetail(date?)`도 이미 date 인자를 받는다. `/library/wellness/:date` 라우트와 30일 추세 차트의 날짜 클릭만 없다. 오늘 값은 스크린샷 시점 걸음 12,743·스트레스 16에서 현재 22,971·29로 바뀌었다(`updated_at 2026-09-27 11:56:49` UTC). 화면에는 날짜만 있고 "몇 시 기준"인지가 없다. 수면 4h14m·점수 52가 부분 동기화인지 실제 짧은 수면인지 구분할 단서도 없다.
- 왜 문제인가: "어제 왜 HRV가 떨어졌나"를 보려면 그날의 수면·스트레스·전날 훈련·체크인을 한 화면에서 봐야 한다. 이것이 회복 결정의 핵심 드릴다운(P2 D3)이다. 누적형 값(걸음·스트레스·BB)을 시각 없이 보여주면 하루 중간 값을 최종값으로 오독하게 된다.
- 개선안: `/v2/library/wellness/:date` 구성은 ① 헤더 `9월 20일(일) · Garmin 04:53 갱신 · 최종`(당일이면 "진행 중") ② 핵심 6개 값과 **개인 기준선 대비**(HRV 97 vs 기준 75~111 → "균형 범위", Garmin 기준선 필드가 이미 있음) ③ 수면 단계 막대와 취침 시각 ④ 전날·당일 활동(→ 활동 상세)과 당일 계획·체크인 ⑤ ← 이전날 / 다음날 → 이다. 추세 차트 포인트, Today 수면 칩, 메트릭 상세 포인트에서 이 화면으로 온다.

### [개선] F-DATA-12 AI 제공자와 외부 전송 범위를 v2에서 알 수도 바꿀 수도 없다
- 현상: v2 Coach 답변 아래에 "규칙 기반 답변" 라벨이 보인다(`raw/coach-thread.txt`). 이것이 키 미설정 때문인지, 제공자 장애 때문인지, 의도한 설정인지 알 수 없다. provider 체인은 "선택 → gemini → groq → rule"이다(`coach_service.py:8`). v1 설정에는 Gemini·Groq 키가 있지만 시스템 정보에는 "AI 모델 genspark (기본)"(수동 복사형)으로 적혀 있다. 무엇이 외부 LLM으로 전송되는지(활동·웰니스·메모 범위)는 v2 어디에도 고지되지 않는다.
- 왜 문제인가: P8(외부 LLM 전송 범위 고지) 위반이다. 규칙 기반과 LLM 답변은 신뢰 수준이 다른데 러너는 전환 조건을 모른다.
- 개선안: `/v2/data/settings/ai`에 제공자 선택, 키 상태(마스킹, 연결 테스트), **전송 범위 체크리스트**(최근 N일 활동 요약 / 웰니스 / 체크인 메모 / 원본 GPS 제외 기본값), 최근 7일 사용량을 둔다. Coach 답변 라벨은 `Gemini · 폴백 없음` 또는 `규칙 기반 · Gemini 오류로 대체`처럼 사유까지 적는다.

### [개선] F-DATA-13 동기화 범위·주기와 "기간 동기화"가 v2에서 보이지 않는다
- 현상: 자동 동기화는 1시간 주기, 14일 창이다(`v1-sync-mobile.png`). 과거 랩·스트림 보충은 기간 동기화로만 된다(BACKLOG DATA-LAPS-EMPTY "남은 작업"). Garmin 잡은 15일 창을 16요청으로 끝내고 `synced_count: 0`을 보고한다. 이미 있는 활동은 0으로 세는 것으로 보이고(추정), 웰니스 갱신은 카운트에 없다.
- 왜 문제인가: "동기화했는데 0건"은 성공인지 실패인지 러너가 판단할 수 없다. 레이트리밋(Garmin 15분 50·일 500)도 기간 동기화 비용을 예측하는 데 필요하다.
- 개선안: 동기화 결과를 `활동 신규 0 · 갱신 2 · 웰니스 15일 갱신 · 랩 보강 1`처럼 **종류별 카운트**로 기록한다(원장 필드). 기간 동기화 폼에는 예상 요청 수와 레이트리밋 잔량을 보여준다.

---

## §A. v1에서 v2가 계승·참고할 데이터 기능

| v1 기능(위치) | 무엇을 | 왜(러너 결정·신뢰) | v2 어디에 | 비고 |
|---|---|---|---|---|
| 상단 "마지막 동기화 + 🔄 동기화" (`/dashboard`) | 첫 화면에서 신선도 확인과 1탭 동기화 | 오늘 권고가 최신 데이터 기반인지 판단 | Today as-of 줄 + ☰ 배지 | 값은 원장 기준으로 교체(F-DATA-01) |
| 소스별 연결/재연동/해제 (`/sync`) | Garmin 토큰·MFA·업로드, Strava OAuth, Intervals/Runalyze 키 | 4소스 통합의 입구 | `/v2/data/sources` | `/connect/*` 로직 재사용, 응답만 JSON화 |
| 동기화 대상 체크박스 (`/sync`, 커밋 29f82ef) | 소스별 포함/제외, 과거 데이터 보존 | 깨진 소스(Strava 403)가 부하를 왜곡하지 않게 격리 | 소스 카드 토글 | config `sync_sources` 그대로 사용 |
| 기본/기간 동기화 + 진행률 | 증분·기간 지정, 재개/중지 | 과거 랩·공백 보충 | ☰ 시트 [지금 동기화], `/v2/data/sync` 기간 폼 | `bg_sync` 잡·레이트리밋 재사용 |
| 자동 동기화 주기·범위 | 1~24h, N일 창 | 아침 데이터 신선도 보장 | `/v2/data/sync` 설정 | 원장에 trigger=auto 기록 |
| Strava 아카이브·FIT/GPX 임포트 | zip·파일 업로드, 기존 활동 재연결 | 과거 공백 메우기 | `/v2/data/import` | 미리보기·중복 보고 추가(F-DATA-08) |
| 메트릭 재계산 90일/전체 | 2차 메트릭 재생성 | 기준값·공식 변경 후 일관성 | 설정 변경 뒤 제안형 | GET→POST 잡, 변경 요약(F-DATA-07) |
| 활동 CSV, 계획 ICS | 내보내기 | 소유권·외부 캘린더 | `/v2/data/export` | 메트릭·웰니스·원본 추가(F-DATA-05) |
| 계획 → Garmin 푸시, CalDAV | 계획을 시계·캘린더로 보냄 | 실행 도구와 연결(Runna 수준) | Coach 계획 상세 "내보내기" | `/training/push-garmin`, `/training/push-caldav` |
| 프로필(최대심박·주간목표·역치 페이스) | 개인 기준값 입력 | 존·처방·판정의 기준 | `/v2/data/settings/profile` | 3열 기준값 페이지, 키 통일(F-DATA-06) |
| AI 제공자·키·프롬프트 관리 | LLM 선택, 무료 제공자 안내 | 코칭 품질·비용 | `/v2/data/settings/ai` | 전송 범위 고지 추가 |
| 외부 AI 연동(프롬프트 복사, MCP) | 내 데이터를 다른 AI로 가져감 | 소유권, 도구 선택권 | `/v2/data/settings/ai` 하단 | MCP 도구 14종이 이미 있음 |
| 활동 "동일 활동 묶기", 필드별 소스 배지(G/i) (`/activities`) | 중복 병합과 값 출처 | 4소스 통합의 증거 | 활동 상세 "소스 비교" + 수동 병합/분리 | `/activities/merge`·`ungroup` 로직 재사용 |
| 레포트 기간 선택 + "이전 동일 기간 대비" | 기간 합계와 Δ% | 성장·과부하 판단 | Story 주/블록/월 비교(F-DATA-10) | |
| 레포트 TIDS 강도 분포, 위험 지표 기간 평균/최고 | 80/20·ACWR·LSI 요약 | 블록 회고의 핵심 | Story 블록 ③⑤ | 0.0%로 표시되는 결함은 계승 금지(`raw/v1-report.txt` Zone 전부 0.0%) |
| 레포트 "요약 복사" | 기간 요약 텍스트 | 코치·로그에 붙여넣기 | Story 우상단 "텍스트로 복사" | |
| 훈련 "어제 훈련 확인(완료/건너뜀)" | 계획 이행 수동 확정 | 자동 매칭 실패 보정 | Today done 상태 · 세션 상세 | 자동 매칭 결과를 먼저 보여주고 교정만 받음 |
| 시스템 정보(DB 경로·크기·공식 버전) | 데이터 규모·버전 | 소유권·재현성 | `/v2/data` "내 데이터 요약" | 경로는 숨기고 크기·행 수·공식 버전만 |

**계승하지 않을 것**: 토큰 파일 경로 노출(`/app/data/users/…/.garminconnect`), "/settings에서 입력하세요"처럼 다른 화면으로 떠넘기는 막다른 안내(v1 설정에는 Runalyze 키 입력란이 없다), 같은 재계산 버튼의 중복 배치, 원인과 다른 상태 문구("토큰 만료 — 자동 갱신").

## §B. 백엔드 API 재사용 판단

| 기능 | 현재 엔드포인트 | 형식 | v2 재사용 | 조치 |
|---|---|---|---|---|
| 소스 데이터 현황 | `GET /api/v1/library/providers/status` | JSON, 184ms | 부분 | `last_synced_at` 의미를 "마지막 새 데이터"로 개명하고 원장 필드 추가 |
| 커버리지·동기화 on/off | `GET /api/v1/library/providers/coverage` | JSON, 7ms | 그대로 | 공백 월 → 임포트 딥링크에 사용 |
| 동기화 실행 | `POST /trigger-sync-bg` | form→HTML/JSON 혼재 | 로직 재사용 | `POST /api/v1/data/sync {sources, from?, to?}`로 래핑 |
| 동기화 진행 | `GET /bg-sync/status?source=` | JSON(api 밖) | 그대로 가능 | `/api/v1/data/sync/status`로 이관, 끈 소스의 잡 정리 |
| 동기화 대상 토글 | `POST /sync/sources` | form→redirect | 로직 재사용 | `PATCH /api/v1/data/sources/:src {sync_enabled}` |
| 자동 동기화 설정 | `POST /sync/auto-sync-settings` | form→redirect | 로직 재사용 | JSON PATCH + 스레드 재시작 유지 |
| 연결 상태 | `check_*_connection()`(`/sync-status` HTML) | 함수 | 재사용 | `GET /api/v1/data/sources`로 노출(`data_service.py` 구현) |
| 연결·OAuth | `/connect/{garmin,strava,intervals,runalyze}*` | HTML 폼, OAuth 콜백 | 콜백 재사용 | v2 카드에서 시작, 콜백 뒤 `/v2/data/sources`로 복귀 |
| 재계산 | `GET /recompute-metrics`, `/metrics/recompute-status`, `-stream`(SSE) | GET 부작용, 메모리 상태 | 로직만 | POST 잡 + 원장 + 변경 요약 |
| 임포트 | `/import/strava-archive`, `/import/upload`, `/import-export` | HTML·SSE | 로직 재사용 | 미리보기 API 신설 |
| 내보내기 | `/activities/export.csv`, `/training/export.ics` | 파일 | 그대로 링크 가능 | 전체 아카이브 잡 신설 |
| 웰니스 일자 | `GET /api/v1/library/wellness?date=` | JSON | **그대로** | `updated_at`·기준선 판정만 추가 |
| 월간 이야기 | `GET /api/v1/today/narrative?year&month` | JSON, 520ms | 부분 | `scope=week|block|month` 일반화, 이전 기간 Δ 추가 |
| 계획 템플릿 | `GET /api/v1/coach/plan/templates` | JSON, 7ms | 부분 | 목표 축 3안, 예측 엔진 통일 |
| 프로필 | `POST /settings/profile` | form | 사용 불가(키 불일치) | `GET/PATCH /api/v1/data/profile` + `/prediction/profile` 병합 |

---

## 잘된 점 (유지)
- 동기화 대상 토글(커밋 29f82ef)이 "끈 소스는 과거 데이터 보존 + 끊김 경고 없음"을 백엔드(`sync_sources`)와 v2 커버리지 띠(`동기화 안 함`) 양쪽에 일관되게 반영했다. 소스 격리 원칙이 올바르다.
- `providerHint`가 7일·30일 기준으로 "최근 활동이 빠져 있을 수 있어요"라는 **결과 중심 경고**를 이미 갖고 있고, UTC 문자열에 `Z`를 붙여 정확히 해석한다. 원장 도입 후 그대로 확장할 수 있다.
- `healthNotice`(TRIMP 누락 20% 이상이면 부하 과소 경고)는 "데이터 결손이 지표를 왜곡한다"를 러너에게 알리는 드문 설계다. 소스 실패에도 같은 패턴을 쓰면 된다.
- 웰니스 API가 날짜 인자·카테고리별 메트릭·provider·단위를 이미 반환한다. 일자 화면은 대부분 프런트 작업이다.
- 템플릿 API의 `status_summary`가 "VDOT 3.0 향상 필요"처럼 목표 격차를 수치로 말한다. 모순만 정리하면 좋은 근거 문장이 된다.

## 채점 (0~10)
- **비전 부합 3**: 통합·소유권 원칙(P8)의 화면 표면이 v2에 없다. ☰가 비활성이고 export·출처 원장이 없다.
- **정보 정확성 3**: 마지막 동기화 값이 3종으로 어긋나고, 소스 실패가 성공으로 기록되며, 기준값이 3중이고 입력 키가 불일치한다. 계획 비교 예측은 Today와 15분 다르다.
- **시각 품질 —(해당 없음, 4)**: 구현된 커버리지 띠·비교 카드는 정돈되어 있지만 대부분 화면이 없다.
- **상호작용 반응성 3**: 재사용할 API는 빠르다(7~184ms). 그러나 v2에서 동기화·재계산·임포트의 진행 피드백 경로가 0이다.
- **흐름 2**: 안내 문구 3곳이 막다른 곳이고, 계획 비교 직접 진입은 400 원문, 웰니스·Story는 드릴 목적지가 없다.
- **혁신성 4**: 소스 격리 토글, 결손 경고, 3경로 예측은 경쟁 앱에 드문 투명성 요소다. 이를 묶는 "데이터 신뢰 원장" 화면이 있으면 signature moment가 된다(Garmin·Strava에는 소스별 실패 원인 표면이 없다).

## 최우선 개선 3개
1. **동기화 원장 + 신선도 표면(F-DATA-01·02·13)**: 소스별 `attempted/succeeded/last_new_data/last_error(분류 코드)/종류별 카운트`를 한 테이블에 두고 오프셋 ISO로 내보낸다. Today as-of 줄, ☰ 배지, 부하 근거 칩 한정 문구가 이 원장만 읽게 한다. v2 기본 진입의 첫 차단 조건이다.
2. **☰ Data MVP 시트(F-DATA-03·04)**: 소스 4행(연결 상태 × 동기화 포함 여부 × 마지막 성공 × 오류 문장) + [지금 동기화] + 진행률을 기존 `bg_sync`·`sync_sources`·`check_*_connection`을 JSON API로 감싸서 만든다. v2의 "동기화를 실행하세요" 문구 3곳을 이 시트로 연결한다.
3. **기준값 페이지와 재계산 잡(F-DATA-06·07)**: HRmax·LTHR·역치 페이스를 `자체 추정 | 기기 | 직접 입력` 중 선택하게 하고, 저장 키를 통일한다(`threshold_pace` 불일치 해소). 변경 시 POST 재계산 잡을 실행하고 대표 지표 전후 비교를 보고한다. 이후 순서는 웰니스 일자 라우트(가장 저비용) → 내보내기 아카이브 → Story 주/블록 → 계획 비교 3안이다.
