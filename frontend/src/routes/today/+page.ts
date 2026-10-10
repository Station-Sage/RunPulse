import { getToday, getTodayNarrative, getRaceHub } from '$lib/api/today';
import { getActivePlan, getTodaysAdjustment } from '$lib/api/plan';
import { getMetricTrend } from '$lib/api/metrics';
import { ApiError } from '$lib/api/client';
import { invalidate } from '$app/navigation';
import { swrEvict, swrLoad } from '$lib/loadCache';
import type { NarrativeResponse, RaceHubData, TodayResponse, ActivePlan, TodaysAdjustment, MetricTrendData } from '$lib/types';

const KEY = 'app:today';

export type NextSessionData = {
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
};
export type FormChartData = { ctl: MetricTrendData; atl: MetricTrendData; tsb: MetricTrendData };

export interface TodayPageData {
	today: TodayResponse | null;
	errorMessage: string | null;
	/** 'empty' = 소스 미연결/DB 없음(온보딩), 'failed' = 조회 실패(재시도) — 40 design §6.1 두 상태 분리. */
	errorKind: 'empty' | 'failed' | null;
	/** 핵심(today)만 await — 나머지는 스트리밍 Promise로 넘겨 화면이 `{#await}` 블록 스켈레톤으로 먼저 뜬다
	 *  (10-today design §5·§6, 02-performance.md P-3). 실패는 reject → 블록 단위 ErrorState(compact)+재시도. */
	narrative: Promise<NarrativeResponse | null>;
	/** plan 없음(404)은 null로 정상 처리, 그 외 실패만 reject. */
	nextSession: Promise<NextSessionData>;
	formChart: Promise<FormChartData>;
	/** 히어로 CTA·레이스 예측선에 쓰인다. 실패해도 화면은 유지(null). */
	raceHub: Promise<RaceHubData | null>;
}

// 스트리밍 블록이 하나라도 실패하면 캐시를 비운다 — 아니면 SWR이 실패한 Promise를 30초간 재사용해 재시도가 안 먹는다.
// swrLoad가 결과를 캐시에 넣은 "뒤"에 지워야 하므로, today가 끝난 다음에 걸고 매크로태스크로 미룬다.
function evictOnFailure(...blocks: Promise<unknown>[]): void {
	for (const p of blocks) p.catch(() => setTimeout(() => swrEvict(KEY), 0));
}

async function fetchToday(): Promise<TodayPageData> {
	// 스트리밍 Promise는 핵심 today와 동시에 쏘되 await하지 않는다.
	const narrative = getTodayNarrative().catch(() => null);
	const nextSession = Promise.all([getActivePlan().catch(orNull), getTodaysAdjustment().catch(orNull)]).then(([plan, adjustment]) => ({ plan, adjustment }));
	const trend = (slug: string) => getMetricTrend(slug, '3m').catch((e) => emptyTrend(slug, e));
	const formChart = Promise.all([trend('ctl'), trend('atl'), trend('tsb')]).then(([ctl, atl, tsb]) => ({ ctl, atl, tsb }));
	const raceHub = getRaceHub().catch(() => null);
	// today가 실패하면 이 Promise들은 소비되지 않는다 — 미처리 rejection 경고를 막는다(소비자는 {#await}로 그대로 받는다).
	for (const p of [nextSession, formChart]) p.catch(() => {});
	const today = await getToday();
	evictOnFailure(nextSession, formChart);
	return { today, errorMessage: null, errorKind: null, narrative, nextSession, formChart, raceHub };
}

// 플랜/조정 없음(404)은 빈 상태이지 실패가 아니다.
function orNull(e: unknown): null {
	if (e instanceof ApiError && e.status === 404) return null;
	throw e;
}

// 메트릭 데이터 없음(404)은 실패가 아니라 "데이터 수집 중" — 차트 블록은 숨기고 오류 카드를 띄우지 않는다.
function emptyTrend(slug: string, e: unknown): MetricTrendData {
	if (e instanceof ApiError && e.status === 404) return { slug, label: slug, unit: '', current: null, peak: null, change_pct: null, points: [] };
	throw e;
}

function failed(e: unknown): TodayPageData {
	// running.db 없음(NOT_FOUND/503)은 "데이터 없음"(온보딩), 그 외는 "조회 실패"(재시도).
	const empty = e instanceof ApiError && (e.status === 404 || (e.status === 503 && e.code === 'NOT_FOUND'));
	const message = e instanceof Error ? e.message : '오늘 데이터를 불러올 수 없습니다.';
	const none = Promise.resolve(null);
	return {
		today: null, errorMessage: message, errorKind: empty ? 'empty' : 'failed', narrative: none,
		nextSession: Promise.resolve({ plan: null, adjustment: null }),
		formChart: new Promise<FormChartData>(() => {}),
		raceHub: none
	};
}

// 탭 재방문 시 즉시 이전 값을 보여주고 조용히 갱신(02-performance.md P-5) — depends()가 있어야 invalidate가 먹는다.
// 실패는 캐시에 남기지 않는다(fetchToday가 throw → swrLoad 미저장) — 그래야 "다시 시도"가 실제로 재요청한다.
export async function load({ depends }: { depends: (key: string) => void }): Promise<TodayPageData> {
	depends(KEY);
	try {
		return await swrLoad(KEY, fetchToday, invalidate);
	} catch (e) {
		return failed(e);
	}
}
