# REVIEW-06 반영 유닛 명세 3 (autopilot 전용) — 백엔드 포함 라운드

명세 1·2 이후 남은 항목. **코드·시그니처·문구는 그대로 구현한다. 바꾸고 싶으면 DECISIONS.md에 사유를 적고 중단.** 파일 300줄 이하, 새 함수엔 테스트, 백엔드 유닛은 `tests/`의 임시 DB 픽스처만 사용(실 DB 열기 금지).
프론트 검증: `cd frontend && npm install && npm run test:unit && npm run check && npm run build`. 백엔드 검증: 해당 테스트 + `python3 scripts/check_docs.py` + `python3 scripts/check_data_consistency.py`, 새 `.py`를 만들면 `python3 scripts/gen_files_index.py`.

## 배경 — 실데이터(사용자 실 계정) 확인 결과 (2026-09-25)

- 허브 예측(마라톤 4:30)과 개인 최고기록이 약 1시간 어긋난다. 10K PB 45:34(2026-05-03) → Riegel(지수 1.06) 마라톤 환산 ≈ 3:29:40, 5K PB 21:56 → ≈ 3:31.
- 원인(코드 확인): `src/metrics/darp.py`가 **최근 30일 러닝 전체의 평균 VDOT**를 쓴다. 최근 30일 38건의 VDOT 평균은 33.1(최고 43.2)이고 대부분 이지런이라 낮게 나오며, 12km를 677초/km로 걸은 활동(VDOT 17.7) 같은 이상치도 평균에 섞인다. → **계산 방식 변경은 사용자 결정 대기(DECISIONS 후보)이며 이 라운드에서 하지 않는다.** 대신 UI가 두 값을 나란히 보여 준다(유닛 G).

## 유닛 G1 — P7-IMPL-PREDICTION-REFERENCE-API (백엔드)

파일: `src/services/race_reference_service.py`(신규), `src/services/race_hub_service.py`, `tests/test_race_reference_service.py`(신규), `tests/test_race_hub_service.py`(기존 파일에 1~2케이스 추가).

1. `src/services/race_reference_service.py`:

```python
"""레이스 예측 대조 기준 — 개인 최고기록(PB)을 Riegel 공식으로 목표 거리에 환산한다.

예측 기록(DARP)이 최근 30일 평균 훈련 VDOT 기반이라 PB와 크게 어긋날 수 있어,
허브가 두 값을 나란히 보여 주기 위한 참고값. 계산 방식 자체는 바꾸지 않는다.
"""
from __future__ import annotations

import sqlite3

RIEGEL_EXPONENT = 1.06
# best effort 이름 → 거리(km). 목표 거리 이하 중 가장 긴 것을 기준으로 삼는다.
_EFFORT_KM = {"5K": 5.0, "10K": 10.0, "15K": 15.0}
_LABELS = {"5K": "5K", "10K": "10K", "15K": "15K"}


def riegel(time_sec: float, from_km: float, to_km: float) -> int:
    """Riegel: t2 = t1 * (d2 / d1) ** 1.06."""
    return int(round(time_sec * (to_km / from_km) ** RIEGEL_EXPONENT))


def pb_reference(conn: sqlite3.Connection, goal_distance_km: float) -> dict | None:
    """목표 거리 이하에서 가장 긴 PB(5K/10K/15K)를 목표 거리로 환산.

    반환: {"basis": "pb_riegel", "pb_key", "pb_label", "pb_sec", "pb_date", "projected_sec"} 또는 None(PB 없음).
    """
    conn.row_factory = sqlite3.Row
    for key in sorted(_EFFORT_KM, key=_EFFORT_KM.get, reverse=True):
        if _EFFORT_KM[key] > goal_distance_km:
            continue
        row = conn.execute(
            "SELECT b.elapsed_sec AS sec, substr(a.start_time, 1, 10) AS d"
            " FROM activity_best_efforts b JOIN activity_summaries a ON a.id = b.activity_id"
            " WHERE b.effort_name = ? AND b.elapsed_sec IS NOT NULL AND a.activity_type LIKE '%running%'"
            " ORDER BY b.elapsed_sec ASC LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            return {
                "basis": "pb_riegel",
                "pb_key": key,
                "pb_label": _LABELS[key],
                "pb_sec": int(row["sec"]),
                "pb_date": row["d"],
                "projected_sec": riegel(row["sec"], _EFFORT_KM[key], goal_distance_km),
            }
    return None
```

2. `race_hub_service.get_race_hub`: `prediction` dict를 만드는 곳에 키 `"reference": pb_reference(conn, goal_dict["distance_km"])`를 추가한다(`from src.services.race_reference_service import pb_reference`). 예측이 없으면 기존처럼 `prediction=None`(reference도 없음). 예외가 나면 `reference`는 `None`(try/except로 삼킴 — 허브 응답을 막지 않는다).
3. 테스트: (a) `riegel(2734, 10, 42.195)`가 12,570~12,600 범위(≈ 3:29:40); (b) `pb_reference` — `activity_best_efforts`에 `5K=1316`, `10K=2734`를 넣은 임시 DB에서 goal 42.195 → `pb_key == '10K'`, `pb_sec == 2734`; goal 8km → `pb_key == '5K'`; goal 3km → `None`; PB 없으면 `None`. (c) `get_race_hub`가 목표+예측 시드가 있는 DB에서 `prediction["reference"]`를 포함(기존 `tests/test_race_hub_service.py`의 시드 방식을 그대로 따른다; PB 시드가 없으면 `reference is None`).

## 유닛 G2 — P7-IMPL-PREDICTION-REFERENCE-UI (프론트, G1 이후)

1. `frontend/src/lib/types/index.ts`: `RaceHubPrediction`에 `reference?: RaceHubReference | null;` 추가, 그 위에 `export interface RaceHubReference { basis: string; pb_key: string; pb_label: string; pb_sec: number; pb_date: string; projected_sec: number; }`.
2. 신규 `frontend/src/lib/predictionReference.ts`(순수, 런타임 import 없음):

```ts
export interface RefLite {
	pb_label: string;
	pb_sec: number;
	pb_date: string;
	projected_sec: number;
}

const hms = (s: number) => {
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	const sec = Math.round(s % 60);
	return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
};
const ms = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

// "PB 기준 환산 3:29:40 (10K 45:34 · 2026-05)"
export function referenceLine(ref: RefLite): string {
	const pb = ref.pb_sec >= 3600 ? hms(ref.pb_sec) : ms(ref.pb_sec);
	return `PB 기준 환산 ${hms(ref.projected_sec)} (${ref.pb_label} ${pb} · ${ref.pb_date.slice(0, 7)})`;
}

// 예측이 PB 환산보다 10% 넘게 느리면 두 값이 왜 다른지 알려 준다. 아니면 null.
export function divergenceNote(predSec: number, ref: RefLite): string | null {
	if (predSec <= ref.projected_sec * 1.1) return null;
	return '예측은 최근 30일 러닝 평균(이지런 위주) 기준이라 PB 환산보다 보수적으로 나와요.';
}
```

   `frontend/tests/predictionReference.test.mjs`(신규): `referenceLine({pb_label:'10K',pb_sec:2734,pb_date:'2026-05-03',projected_sec:12580})` === `'PB 기준 환산 3:29:40 (10K 45:34 · 2026-05)'`; `divergenceNote(16226, {..., projected_sec:12580})`는 위 문장; `divergenceNote(13000, 같은 ref)`는 `null`(13000 ≤ 12580×1.1).
3. `frontend/src/lib/components/RaceHub.svelte`: 예측/목표 두 칸 grid와 `{#if verdict}` 문장 사이(또는 verdict 바로 아래)에 `{#if pred?.reference}<div class="flex flex-col gap-0.5"><p class="text-[11px] text-fg-muted">{referenceLine(pred.reference)}</p>{#if divergenceNote(pred.value_sec, pred.reference)}<p class="text-[11px] text-semantic-amber">{divergenceNote(pred.value_sec, pred.reference)}</p>{/if}</div>{/if}` (`import { referenceLine, divergenceNote } from '$lib/predictionReference';`). 그 외 변경 금지.

## 유닛 J — P7-IMPL-TODAY-RECENT-THUMBS (Today 최근 활동에 경로 썸네일)

파일: `src/services/today_service.py`, `tests/test_today_service.py`, `frontend/src/lib/types/index.ts`, `frontend/src/routes/today/+page.svelte`.
1. `today_service.get_recent_activities`: 반환 직전에 `from src.services.activity_service import _route_previews`로 `previews = _route_previews(conn, [a["id"] for a in activities])`를 구해 각 항목에 `a["route"] = previews.get(a["id"])`를 추가. 테스트: 스트림(위도·경도 2점 이상)이 있는 활동은 `route`가 리스트, 없는 활동은 `None`.
2. 프론트: `TodayResponse.recent_activities` 항목 타입(`RecentActivity` 등 기존 이름 유지)에 `route?: [number, number][] | null;` 추가. `today/+page.svelte`의 최근 활동 행 맨 앞(상대 날짜 `span` 앞)에 `<RouteThumb route={act.route} size={32} />`를 추가(`import RouteThumb from '$lib/components/RouteThumb.svelte';`).

## 유닛 L — P7-IMPL-COACH-THREAD-STALE (낡은 스레드에 시점 표기; 프론트)

파일: `frontend/src/lib/threadAge.ts`(신규), `frontend/tests/threadAge.test.mjs`(신규), `frontend/src/routes/coach/+page.svelte`.
1. `threadAge.ts`(순수):

```ts
// 마지막 메시지가 7일 넘게 지난 스레드는 "당시 기준"임을 알린다 — 지금 상태와 다를 수 있다.
export function staleLabel(lastMessageAt: string | null | undefined, nowMs: number): string | null {
	if (!lastMessageAt) return null;
	const t = Date.parse(lastMessageAt.includes('T') ? lastMessageAt : lastMessageAt.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	return days >= 7 ? `${days}일 전 대화 · 당시 기준` : null;
}
```

   테스트: `nowMs = Date.parse('2026-09-25T00:00:00Z')`; `'2026-09-10 10:00:00'` → `'14일 전 대화 · 당시 기준'`; `'2026-09-24 10:00:00'` → `null`; `null` → `null`; 잘못된 문자열 → `null`.
2. `coach/+page.svelte`: 스레드 목록 항목의 `last_message` 미리보기 `<p>` 아래에 `{#if staleLabel(t.last_message_at, Date.now())}<p class="text-[10px] text-semantic-amber">{staleLabel(t.last_message_at, Date.now())}</p>{/if}` 추가(`import { staleLabel } from '$lib/threadAge';`). 그 외 변경 금지.

## 유닛 H1 — P7-IMPL-ACTIVITY-IMPACT-API (백엔드)

파일: `src/services/activity_impact_service.py`(신규), `src/services/activity_service.py`(상세 응답에 키 추가), `tests/test_activity_impact_service.py`(신규).
1. `activity_impact_service.get_activity_impact(conn, activity_id, today=None) -> dict | None`:
   - 대상 활동은 `activity_summaries`에서 `id, activity_type, start_time, distance_m, avg_pace_sec_km, avg_hr`를 읽는다. 러닝 계열(`activity_type LIKE '%running%'`)이 아니거나 거리가 없으면 `None`.
   - `load`: 그 날짜(`substr(start_time,1,10)`)의 metric_store daily `ctl`(is_primary=1)과 전날 값의 차 `ctl_delta`(소수 1자리), 그날 `tsb`. 어느 쪽이든 없으면 해당 키는 `None`.
   - `similar`: 같은 `activity_type`, 거리 ±15%, 이 활동보다 **이전**(start_time <)인 `v_canonical_activities` 최근 10건 중 `avg_pace_sec_km`가 있는 것. 3건 미만이면 `None`. 아니면 `{"n": N, "pace_rank": (이 활동보다 빠른 이전 활동 수 + 1), "avg_pace_sec_km": 평균(소수 1자리), "pace_diff_sec": 이 활동 페이스 − 평균(소수 1자리, 음수면 더 빠름)}`.
   - `race`: `today`(기본 `date.today()`) 기준 가장 가까운 미래 활성 목표(`goals` 테이블, `race_hub_service`의 목표 조회와 같은 조건 — 먼저 읽고 같은 SQL 사용)가 있으면 `{"name", "days_left"}`, 없으면 `None`.
   - 반환: `{"ctl_delta", "tsb", "similar", "race"}`.
2. `activity_service.get_activity_detail`의 반환 dict에 `"impact": get_activity_impact(conn, activity_id)` 추가(예외 시 `None`, 응답을 막지 않는다).
3. 테스트(임시 DB): 러닝 활동 + 전날/당일 ctl 시드 → `ctl_delta` 값; 유사 활동 4건 시드 → `similar.n == 4`, `pace_rank` 계산; 유사 2건 → `similar is None`; 비러닝 → `None`; 목표 없으면 `race is None`.

## 유닛 H2 — P7-IMPL-ACTIVITY-IMPACT-UI (프론트, H1 이후)

파일: `frontend/src/lib/types/index.ts`, `frontend/src/lib/activityImpact.ts`(신규), `frontend/tests/activityImpact.test.mjs`(신규), `frontend/src/routes/library/[id]/+page.svelte`.
1. 타입: `ActivityDetail`(상세 응답 활동 객체 타입 — 기존 이름 유지)에 `impact?: ActivityImpact | null;`, `export interface ActivityImpact { ctl_delta: number | null; tsb: number | null; similar: { n: number; pace_rank: number; avg_pace_sec_km: number; pace_diff_sec: number } | null; race: { name: string; days_left: number } | null }`.
2. `activityImpact.ts`(순수):

```ts
export interface ImpactLite {
	ctl_delta: number | null;
	tsb: number | null;
	similar: { n: number; pace_rank: number; avg_pace_sec_km: number; pace_diff_sec: number } | null;
	race: { name: string; days_left: number } | null;
}

// 화면에 줄 문장 목록 — 값이 없는 항목은 만들지 않는다(근거 없는 문장 금지).
export function impactLines(i: ImpactLite): string[] {
	const out: string[] = [];
	if (i.ctl_delta != null) out.push(`이 날 체력(CTL) ${i.ctl_delta >= 0 ? '+' : ''}${i.ctl_delta.toFixed(1)}${i.tsb != null ? ` · 폼(TSB) ${i.tsb >= 0 ? '+' : ''}${Math.round(i.tsb)}` : ''}`);
	if (i.similar) {
		const s = i.similar;
		const d = Math.abs(Math.round(s.pace_diff_sec));
		const cmp = s.pace_diff_sec < 0 ? `${d}초/km 빠름` : s.pace_diff_sec > 0 ? `${d}초/km 느림` : '평균과 같음';
		out.push(`비슷한 거리 이전 ${s.n}회 중 ${s.pace_rank}번째로 빠른 페이스 (평균보다 ${cmp})`);
	}
	if (i.race) out.push(`${i.race.name} D-${i.race.days_left}에 쌓은 세션`);
	return out;
}
```

   테스트: 모든 값이 있는 입력 → 3줄(첫 줄 `'이 날 체력(CTL) +2.3 · 폼(TSB) +5'` 형태 — 입력 `ctl_delta:2.3, tsb:5.2`), similar `pace_diff_sec:-12.4` → `'…평균보다 12초/km 빠름)'`; `pace_diff_sec: 0` → `'평균과 같음'`; 전부 null → `[]`.
3. `library/[id]/+page.svelte`: 스토리 카드 아래(핵심 메트릭 그리드 위)에 `{#if impactList.length > 0}<section class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3"><p class="text-xs uppercase tracking-wide text-fg-muted">이 러닝의 의미</p>{#each impactList as line}<p class="text-sm text-fg-primary">{line}</p>{/each}</section>{/if}`, 스크립트에 `const impactList = $derived(data.activity?.impact ? impactLines(data.activity.impact) : []);`(`data.activity`가 core를 담는 기존 구조를 먼저 읽고 `impact`가 상세 응답 어디에 오는지에 맞춰 경로를 조정 — 응답 최상위 `activity.impact`).

## 유닛 I — P7-IMPL-MERGED-SOURCES (통합의 가시화: 병합 소스 수)

파일: `src/services/activity_service.py`, `tests/test_activity_service.py`(기존), `frontend/src/lib/types/index.ts`, `frontend/src/routes/library/activities/+page.svelte`.
1. **먼저 확인**: `v_canonical_activities` 뷰(`src/db_setup.py`)가 `matched_group_id`를 노출하는지, 활동 목록 쿼리가 무엇을 SELECT하는지 읽는다. 뷰가 컬럼을 노출하지 않으면 `activity_summaries` 조인으로 대체. 어느 쪽이든 그룹 개념이 이 설명과 다르면 DECISIONS.md에 사유를 적고 중단.
2. 활동 목록 각 항목에 `source_count: int`를 추가 — 같은 `matched_group_id`(NULL이 아님)를 가진 `activity_summaries` 행 수(서로 다른 `source` 개수, 최소 1). 테스트: 같은 그룹 2소스 → `source_count == 2`, 그룹 없음 → `1`.
3. 프론트: `ActivitySummary` 타입에 `source_count?: number;`. `activities/+page.svelte`의 소스 배지 자리(유닛 D의 `showBadge` 조건 안팎 무관): `{#if (act.source_count ?? 1) > 1}<span class="rounded border border-semantic-teal/50 px-1 py-px text-[9px] text-semantic-teal">{act.source_count}소스 병합</span>{/if}`를 행 메타 줄에 추가.

## 유닛 K — P7-IMPL-DESKTOP-SIDENAV (데스크톱 ≥1024px 좌측 내비; 사용자 승인 2026-09-25)

모바일(<1024px)은 지금 그대로(하단 3탭). 데스크톱에서만 하단 탭바를 좌측 고정 사이드바로 바꾼다. 프론트 전용. 파일: `frontend/src/routes/+layout.svelte`, `frontend/src/routes/coach/[threadId]/+page.svelte`.
1. `+layout.svelte`:
   - 루트 `<div class="flex min-h-screen flex-col bg-surface-1 text-fg-primary">`에 `lg:pl-52`를 추가(사이드바 폭만큼 콘텐츠 밀기).
   - `<main class="mx-auto w-full max-w-3xl lg:max-w-6xl flex-1 pb-20">`의 `pb-20`을 `pb-20 lg:pb-6`으로.
   - `<nav aria-label="주 메뉴" class="fixed inset-x-0 bottom-0 border-t border-border-subtle bg-surface-2">`를 `<nav aria-label="주 메뉴" class="fixed inset-x-0 bottom-0 border-t border-border-subtle bg-surface-2 lg:inset-y-0 lg:right-auto lg:w-52 lg:border-r lg:border-t-0 lg:pt-16">`로.
   - nav 안쪽 `<div class="mx-auto flex w-full max-w-3xl lg:max-w-6xl">`를 `<div class="mx-auto flex w-full max-w-3xl lg:max-w-none lg:flex-col lg:gap-1 lg:px-2">`로.
   - 탭 링크 클래스를 `class="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] lg:flex-none lg:flex-row lg:gap-3 lg:rounded-lg lg:px-3 lg:py-2.5 lg:text-sm {isActive(tab.match) ? 'text-fg-primary lg:bg-surface-3' : 'text-fg-muted lg:hover:bg-surface-3'}"`로(기존 활성/비활성 삼항을 이 문자열로 교체).
2. `coach/[threadId]/+page.svelte`: 입력 바 `sticky bottom-14 z-10 …`에 `lg:bottom-0`을 추가하고, 메시지 목록 컨테이너의 `min-h-[calc(100dvh-15.5rem)]`에 `lg:min-h-[calc(100dvh-11rem)]`를 추가.
3. 검증: `cd frontend && npm install && npm run test:unit && npm run check && npm run build`.
