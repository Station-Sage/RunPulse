# DESIGN — ◆ 알고리즘 버전 변경 마커 (TrendChart)

> 작성 2026-10-10 · system-architect 초안 · 상태: **승인 대기 (구현 금지)**
> 근거: `BACKLOG.md` P7-UXR-DESIGN-PENDING ③·9단계2. 코드 조사는 2026-10-10 `renew/data-architecture` HEAD(e265a30) 기준.

---

## 0. 요약

- BACKLOG ③의 "◆ 미구현"은 **일부 stale**하다. U17b/c(7c4d057, 2026-10-06)에서 **데이터 파생형 ◆**와 **재계산 캡션**은 이미 구현됐다.
- 남은 문제: 전 기간 재계산(`recompute_all`) 뒤에는 시계열 안에 불연속이 없어서 ◆가 뜨지 않는다. 캡션 소스(`milestones.algo_recompute`)는
  이 경로에서 **기록되지 않고**, 7개 지표만 추적하며, "왜 바뀌었는지"(사유)도 없다.
- 추천안: **코드 안에 선언하는 changelog 레지스트리**(`src/metrics/algo_changelog.py`)를 단일 소스로 둔다. 서비스 레이어가 이 레지스트리를
  `events[]`(kind=`version_change`)로 바꿔 넣고, 과거 이력은 git log로 한 번 백필한다. DB 변경은 없다.

---

## 1. 현황 조사 (grep으로 확인)

### 1-1. 버전 정의
| 위치 | 내용 |
|------|------|
| `src/metrics/base.py:59` | `MetricCalculator.version: str = "1.0"` (클래스 속성 1개, 이력 없음) |
| `src/metrics/*.py` | 37개 Calculator가 `version = ...` 선언. 형식이 섞여 있음: `"2.0"`, `"banister_1991_v2"`, `"minetti_2002_v2"`, `"daniels_2005"`, `"pdf_weights_v1"` |
| `src/sync/extractors/base.py:25` | 소스 메트릭 `algorithm_version: str = "1.0"` (소스는 사실상 고정) |

### 1-2. 저장
- `metric_store.algorithm_version TEXT DEFAULT '1.0'` (`src/db_setup.py:193`). UNIQUE(scope_type, scope_id, metric_name, provider)라서
  **행마다 버전 값 하나**만 있고, 이력은 남지 않는다.
- `engine.py:307`에서 `upsert_metric(..., algorithm_version=calc.version)`을 호출한다.

### 1-3. 재계산 흐름
- `recompute_all(conn, days=None)` (`engine.py:740`): `clear_runpulse_metrics(lo, hi)`로 기간 안 RunPulse 행을 **먼저 삭제**한 뒤 다시 계산한다.
- `upsert_metric` (`db_helpers.py:234-270`): 지표가 `_MILESTONE_TRACKED_METRICS`(ctl, runpulse_vdot, race_pred_×4, rri)에 들어 있고
  **기존 행이 남아 있을 때만** 버전 차이를 감지해 `milestones(type='algo_recompute', date=today)`에 INSERT한다.
  → `recompute_all` 경로에서는 행이 이미 지워져 있으므로 **감지가 일어나지 않는다**. 감지는 `recompute_recent`·`recompute_single_metric`처럼
  덮어쓰는 경로에서만 일어난다.
- 로컬 `data/running.db`·`running.db`에는 `milestones` 테이블 자체가 없다. 운영 DB(OCI 컨테이너)의 실제 기록 여부는 따로 확인해야 한다.

### 1-4. 현재 ◆ 구현 (U17b/c)
- `src/services/metrics_version_events.py`
  - `version_change_events(conn, slug, d0, d1)`: 대표 시계열에서 (provider, algorithm_version)이 바뀐 첫 날을
    `{date, kind:"version_change", from, to, label}`로 돌려준다. 부분 재계산·출처 전환이 있을 때만 결과가 나온다.
  - `recompute_note(...)`: 불연속이 없을 때 `milestones.algo_recompute`의 최신 날짜로 "M/D부터 계산 vX · 과거 값도 모두 다시 계산됐어요" 캡션을 만든다.
- `metrics_browser_service.py:258-264`: `events = race(▲) + basis_change(◇) + version_change(◆)`를 날짜순으로 정렬하고, `recompute_note`를 따로 둔다.
- API: `GET /api/v1/library/metrics/<slug>/trend` (`src/api/routes_library.py:144`).
- 프론트: `trendChart.ts` `EVENT_SYMBOL`/`markerEvents`(같은 날 ◆>◇>▲ 하나만 표시), `TrendChart.svelte:142` 선택 날짜 readout에 `{기호} {label}` 표시.

### 1-5. ADR 기록 방식
- `v0.3/data/decisions.md`의 `## ADR-NNN:` / `### ADR-NNN:` 자유 서식 마크다운 (최신 ADR-041).
- 버전 올림과 ADR이 1:1로 대응하지 않는다. 예: GAP v2(8d2b9ad), 68e7635(RE·디커플링 등)는 ADR 없이 커밋 메시지에만 기록돼 있다.

### 1-6. 과거 버전 올림 이력 (`git log -G'^\s+version = ' -- src/metrics/`)
| 커밋 | 날짜 | 변경 |
|------|------|------|
| bec7947 | 2026-09-26 | P7-PRED r4: 약 8개 Calculator 1.0→2.0, darp_r4 4.0 신규 |
| d43dedf | 2026-09-28 | PMC 1.0→2.0(α=1/τ·252일), TRIMP banister_1991→_v2 |
| 68e7635 | 2026-09-28 | relative_effort·decoupling 등 2개 1.0→2.0 |
| 8d2b9ad | 2026-09-28 | GAP minetti_2002→_v2 |
| d726191 | 2026-10-07 | trimp_est_v1 신규 (ADR-024) |

→ 백필 대상은 약 15건으로, 손으로 정리할 수 있는 규모다.

---

## 2. changelog 소스 후보

### A. 코드 선언 레지스트리 (`src/metrics/algo_changelog.py`)
버전 올림 커밋에서 Calculator `version`과 레지스트리 항목을 함께 고친다.
- 장점: 코드와 함께 버전이 관리된다. DB 마이그레이션이 없다. 계약 테스트로 "`calc.version`에 대응하는 항목이 있다"를 강제할 수 있다.
  사유 문구와 ADR 링크를 담을 수 있다. `recompute_all`의 삭제 동작과 무관하다. 데모 스냅샷·새 설치에서도 결과가 같다.
- 단점: 날짜가 **코드 날짜**다. 사용자 DB에서 실제로 재계산한 날과 며칠 어긋날 수 있다. 버전을 올릴 때 개발자가 항목을 써야 하지만, 테스트가 누락을 막는다.

### B. DB 테이블 `algorithm_changes` (엔진이 기록)
`recompute_*` 시작 전에 `metric_store`의 기존 (metric_name, provider, algorithm_version)을 스냅샷해 두고, 계산 후 버전이 달라진 지표를 기록한다.
- 장점: 실제 적용일이 정확하다. 37개 지표 전체를 다룰 수 있다.
- 단점: 스키마 v36 마이그레이션과 백업·승인이 필요하다. 사유 문구는 결국 코드에서 가져와야 하므로 A가 어차피 필요하다.
  과거 이력은 DB에 남아 있지 않아 백필할 수 없다. 데모·테스트 DB마다 결과가 다르다. 재계산 경로가 여러 개라 기록 누락 지점이 생긴다(현재 milestones와 같은 문제).

### C. `decisions.md` 파싱
- 장점: 새 저장소가 필요 없다.
- 단점: 서식이 자유라 파싱이 깨지기 쉽다. ADR 없는 버전 올림(1-5)이 빠진다. 런타임에 문서를 읽게 되어 레이어를 위반한다(배포 이미지에 문서가 없을 수도 있다).
  **기각.**

### (참고) D. 기존 `milestones.algo_recompute` 확대
- 1-3의 구조적 누락(전 기간 재계산 시 미기록), 날짜가 실행일이라는 점, 사유 없음 때문에 단독 소스로는 부적합하다. 역할을 줄여 보조 신호로만 남긴다(§3-6).

---

## 3. 추천안 — A. 코드 선언 레지스트리

### 3-1. 레지스트리 정의
```python
# src/metrics/algo_changelog.py
"""Calculator 알고리즘 버전 변경 이력 — ◆ 마커·재계산 캡션의 단일 소스(순수 데이터, SQL 없음)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class AlgoChange:
    calculator: str          # MetricCalculator.name
    version: str             # 이 항목이 도입한 calc.version (문자열 그대로)
    date: str                # YYYY-MM-DD, 코드 반영일(커밋 날짜)
    reason: str              # 사용자용 한 줄 사유(40자 안팎, 수식·영문 약어 최소화)
    prev: str | None = None  # 직전 버전, 신규 Calculator면 None
    adr: str | None = None   # "ADR-024" 등

CHANGELOG: tuple[AlgoChange, ...] = (
    AlgoChange("pmc", "2.0", "2026-09-28", "체력·피로 반영 속도를 표준 식으로 바로잡았어요", "1.0"),
    AlgoChange("trimp", "banister_1991_v2", "2026-09-28", "심박 기반 부하 계수를 교정했어요", "banister_1991"),
    # ... §3-5 백필
)

def changes_for(calculator: str) -> list[AlgoChange]: ...
```
- 신규 Calculator의 최초 버전(`prev=None`)은 **마커를 만들지 않는다**. 값이 새로 생긴 것이지 바뀐 것이 아니므로, 레지스트리에는 기록만 한다.
- `version`은 현재 문자열 형식을 그대로 둔다. 형식 통일은 이 범위 밖이다(§5 D-3).

### 3-2. 지표 → Calculator 해석과 의존 전파
- 서비스 레이어(`metrics_version_events.py`)가 `ALL_CALCULATORS`의 `produces`에서 slug를 만드는 Calculator를 찾는다.
- 직접 변경: 그 Calculator의 changelog 항목.
- 상위 변경 전파: `requires`를 거꾸로 따라가 상위 Calculator의 항목도 포함한다(예: TRIMP v2 → ctl). 사유 앞에 `입력 지표(TRIMP) 변경 · `를 붙인다.
  같은 날짜의 항목은 마커 1개로 합치고 사유는 `;`로 잇는다(d43dedf처럼 PMC와 TRIMP가 같은 날 바뀐 경우).
- 표시 조건: 이벤트 날짜 **이후** 대표 시계열의 provider가 `runpulse%`일 때만 낸다. 대표값이 Garmin 등 소스라면 RunPulse 알고리즘 변경은 차트와 무관하다.

### 3-3. API — `events[]` 확장 스키마
기존 키는 유지하고(하위 호환), 선택 키만 추가한다. `kind`는 `version_change`를 그대로 써서 프론트의 기호·우선순위 로직을 바꾸지 않는다.
```jsonc
{
  "date": "2026-09-28",
  "kind": "version_change",
  "label": "계산 방식 변경: v1.0→v2.0",     // 기존 (readout 한 줄)
  "from": "1.0", "to": "2.0",               // 기존
  "source": "changelog",                    // 신규: "changelog" | "data"(기존 불연속 감지)
  "reason": "체력·피로 반영 속도를 표준 식으로 바로잡았어요",  // 신규, 없으면 생략
  "via": "trimp",                           // 신규: 상위 지표 전파일 때만
  "adr": "ADR-024",                         // 신규, 선택
  "recomputed": true                        // 신규: 과거 값도 새 방식으로 다시 계산됐다는 뜻(전 기간 재계산)
}
```
- **data 이벤트와 병합**: 같은 slug에서 data 이벤트의 `to`가 changelog 항목의 `version`과 같으면 1건으로 합친다.
  날짜는 data 쪽(실제로 선이 끊긴 날)을 쓰고, `reason`·`adr`은 changelog 쪽에서 가져오며, `recomputed=false`로 둔다.
- 출처 전환 이벤트(`provider` 변경)는 지금 동작을 그대로 둔다(`source:"data"`).
- `recompute_note`: changelog에서 기간 안 최신 항목으로 캡션을 만든다. "9/28부터 계산 v2.0 · 과거 값도 모두 다시 계산됐어요 — {reason}".
  changelog에 항목이 없을 때만 지금처럼 `milestones`를 폴백으로 쓴다.

### 3-4. 프론트 표시·툴팁 (데이터 계약만 다룬다. 시각 표현은 product-architect 검수 대상)
- 기호·색·우선순위는 기존 로직을 그대로 쓴다(`◆`, `text-semantic-amber`, ◆>◇>▲).
- readout 줄(`TrendChart.svelte:142`): `◆ {label}`, 그리고 `reason`이 있으면 다음 줄에 `{reason}`, `recomputed`이면 짧은 꼬리말을 붙인다.
- `types/index.ts`의 이벤트 타입에 선택 필드 `source? reason? via? adr? recomputed?`를 추가한다.
- 문구 규칙은 기존 캡션 톤(해요체, 수식 없이)을 따르고, 사유 초안은 사용자 검수(D-4 A 관례)를 거친 뒤 커밋한다.

### 3-5. 과거 이력 백필
1. `git log --format='%h %ad %s' --date=short -p -G'^\s+version = ' -- src/metrics/`로 (파일, 이전 버전, 새 버전, 날짜) 목록을 뽑는다(§1-6, 약 15건).
2. 사유는 커밋 메시지와 ADR(ADR-024 등), bec7947 PR 본문에서 한 줄로 요약한다. `scripts/`의 1회용 스크립트가 초안 튜플을 출력하고, 사람이 다듬어 커밋한다.
   런타임에는 git에 의존하지 않는다.
3. 날짜는 커밋 날짜를 쓴다. 운영 반영일이 따로 확인되면 손으로 고친다.
4. 2026-04-03~04 포팅 커밋(최초 1.0)은 `prev=None`이므로 마커가 없다. 레지스트리에는 남길지 생략할지 중 **생략을 추천**한다. 테스트는 "1.0이 아닌 버전만 항목 필수"로 둔다.

### 3-6. ADR-009와 레이어 준수
- Calculator 코드는 바뀌지 않는다(버전 상수만). 레지스트리는 SQL이 없는 순수 데이터 모듈이다. Calculator 안에서 import하지 않는다.
- 조회와 조립은 `src/services/metrics_version_events.py`에서만 한다. DB 접근은 기존 `get_metric_history` 헬퍼로만 하고, 새 raw SQL은 0건이다.
- `milestones.algo_recompute` 기록 로직(`db_helpers`)은 그대로 둔다(A/B 기록 용도). 표시 소스 역할은 changelog로 넘긴다.

---

## 4. 구현 슬라이스와 테스트 계획

| 슬라이스 | 내용 | 변경 파일 | 테스트 |
|---------|------|----------|--------|
| V1 | 레지스트리 모듈과 백필 데이터, 계약 테스트 | `src/metrics/algo_changelog.py`(신규), `scripts/gen_algo_changelog_draft.py`(1회용, 선택) | `tests/test_algo_changelog.py` 약 5건: ① 모든 `ALL_CALCULATORS`에서 version≠"1.0"이면 (name, version) 항목 존재 ② calculator 이름이 실제로 존재 ③ 날짜 형식·오름차순 ④ prev 연쇄 일관성(같은 calc 안에서 prev = 직전 version) ⑤ reason 비어 있지 않음·80자 이하 |
| V2 | 서비스: changelog→events 변환, 의존 전파, data 이벤트 병합, provider 조건 | `src/services/metrics_version_events.py`(300줄 이내 유지, 넘으면 `metrics_changelog_events.py`로 분리), `metrics_browser_service.py` | `tests/test_metrics_version_events.py`에 약 7건 추가: 기간 밖 제외 / 신규 calc 무마커 / 대표가 소스 provider이면 제외 / TRIMP→ctl 전파·`via` / 같은 날 병합 / data 이벤트와 병합(날짜=data, reason=changelog) / 레지스트리 비었을 때 기존 동작 회귀 |
| V3 | `recompute_note` 소스 전환(changelog 우선, milestones 폴백) | 같음 | 2건: changelog 캡션에 reason 포함 / 항목 없으면 milestones 폴백 |
| V4 | 프론트 타입과 readout 사유 줄 | `types/index.ts`, `TrendChart.svelte`, 데모 `snapshot.json` | `frontend/tests/trendChart.test.mjs` 1~2건(선택 필드가 있어도 `markerEvents` 결과 불변). 실 DB 사본으로 `/library/metrics/ctl` 1y에서 9/28 ◆와 사유 readout을 브라우저 스모크(성능·표시 검증 규율) |
| V5 | 문서 | `decisions.md` ADR-042(changelog 단일 소스), `files_index.md` 재생성, `.claude/rules/coding-rules.md` 메트릭 항목에 "version 올리면 algo_changelog 항목 추가" 1줄, BACKLOG ③ 정정(U17b/c 반영) | `check_docs.py` 통과. 검사 추가는 V1 계약 테스트로 대체하므로 불필요 |

예상 신규 테스트: 백엔드 약 14건, 프론트 1~2건. 스키마 변경 없음(SCHEMA_VERSION 35 유지).

### 검증 항목
1. `pytest tests/` 전체 통과. 특히 V1 계약 테스트가 현재 37개 Calculator 버전과 맞는지.
2. ctl 1y 응답의 `events[]`에 `2026-09-28` `source:"changelog"` 항목이 1건만 있는지(PMC와 TRIMP 병합).
3. 대표 provider가 소스인 지표(예: Garmin VO2max 계열)에는 RunPulse changelog ◆가 나오지 않는지.
4. `race`·`basis_change` 이벤트와 기존 data ◆에 회귀가 없는지(기존 테스트 유지).
5. `recompute_all` 실행 후에도 ◆와 캡션이 유지되는지. 이것이 milestones 방식과 비교해 핵심 개선점이다.

---

## 5. 열린 결정 (추천안 포함)

| ID | 질문 | 추천 | 이유 |
|----|------|------|------|
| D-1 | ◆ 날짜를 코드 반영일(커밋)로 할지, 사용자 DB 재계산일로 할지 | **커밋 날짜**(운영 반영일을 알면 손으로 정정) | 결정적이고 재현 가능하며 백필할 수 있다. 재계산일 기록은 B안 스키마가 필요해 비용 대비 이득이 작다(단일 사용자) |
| D-2 | 상위 지표 변경을 하위 지표 차트에도 ◆로 전파할지 | **전파**(같은 날 병합, `via`·"입력 지표 변경" 접두) | 사용자 입장에서는 값이 바뀐 원인이 무엇이든 같은 사건이다. 전파하지 않으면 ctl 차트에서 TRIMP 교정 사실이 사라진다 |

판단이 필요 없는 항목(추천대로 진행): 신규 Calculator 최초 버전은 마커 없음 / `kind` 재사용 / milestones는 폴백으로 유지 / version 문자열 형식 통일은 범위 밖(D-3, 필요하면 별도 BACKLOG).
