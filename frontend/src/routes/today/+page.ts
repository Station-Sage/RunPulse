import { getToday, getTodayNarrative, getRaceHub } from '$lib/api/today';
import { getActivePlan, getTodaysAdjustment } from '$lib/api/plan';
import { getMetricTrend } from '$lib/api/metrics';
import { ApiError } from '$lib/api/client';
import { invalidate } from '$app/navigation';
import { swrLoad } from '$lib/loadCache';
import type { NarrativeResponse, RaceHubData, TodayResponse, ActivePlan, TodaysAdjustment, MetricTrendData } from '$lib/types';

export interface TodayPageData {
	today: TodayResponse | null;
	errorMessage: string | null;
	/** 캐시 미스 시 LLM 추론 지연(413ms+)이 있어 핵심 데이터를 막지 않도록 await 없이 넘긴다
	 *  (02-performance.md P-3 나머지 절반) — 화면은 `{#await data.narrative}`로 소비. */
	narrative: Promise<NarrativeResponse | null>;
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
	ctlTrend: MetricTrendData | null;
	atlTrend: MetricTrendData | null;
	tsbTrend: MetricTrendData | null;
	raceHub: RaceHubData | null;
}

async function fetchToday(): Promise<TodayPageData> {
	// narrative는 핵심 데이터와 동시에 쏘되 await하지 않는다 — 핵심 Promise.all보다 늦게 시작하면
	// 그만큼 화면에 채워지는 시점도 늦어진다.
	const narrative = getTodayNarrative().catch(() => null);
	try {
		const [today, plan, adjustment, ctlTrend, atlTrend, tsbTrend, raceHub] = await Promise.all([
			getToday(),
			getActivePlan().catch(() => null),
			getTodaysAdjustment().catch(() => null),
			getMetricTrend('ctl', '3m').catch(() => null),
			getMetricTrend('atl', '3m').catch(() => null),
			getMetricTrend('tsb', '3m').catch(() => null),
			getRaceHub().catch(() => null)
		]);
		return { today, errorMessage: null, narrative, plan, adjustment, ctlTrend, atlTrend, tsbTrend, raceHub };
	} catch (e) {
		// running.db 없음(NOT_FOUND/503) 등 — 1-E "데이터 없음" 상태로 처리(03a-today.md).
		const message = e instanceof ApiError ? e.message : '오늘 데이터를 불러올 수 없습니다.';
		return { today: null, errorMessage: message, narrative: Promise.resolve(null), plan: null, adjustment: null, ctlTrend: null, atlTrend: null, tsbTrend: null, raceHub: null };
	}
}

// 탭 재방문 시 즉시 이전 값을 보여주고 조용히 갱신(02-performance.md P-5) — depends()가 있어야 invalidate가 먹는다.
export async function load({ depends }: { depends: (key: string) => void }): Promise<TodayPageData> {
	depends('app:today');
	return swrLoad('app:today', fetchToday, invalidate);
}
