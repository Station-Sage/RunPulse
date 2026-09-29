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
	narrative: NarrativeResponse | null;
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
	ctlTrend: MetricTrendData | null;
	atlTrend: MetricTrendData | null;
	tsbTrend: MetricTrendData | null;
	raceHub: RaceHubData | null;
}

async function fetchToday(): Promise<TodayPageData> {
	try {
		const [today, narrative, plan, adjustment, ctlTrend, atlTrend, tsbTrend, raceHub] = await Promise.all([
			getToday(),
			getTodayNarrative().catch(() => null),
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
		return { today: null, errorMessage: message, narrative: null, plan: null, adjustment: null, ctlTrend: null, atlTrend: null, tsbTrend: null, raceHub: null };
	}
}

// 탭 재방문 시 즉시 이전 값을 보여주고 조용히 갱신(02-performance.md P-5) — depends()가 있어야 invalidate가 먹는다.
export async function load({ depends }: { depends: (key: string) => void }): Promise<TodayPageData> {
	depends('app:today');
	return swrLoad('app:today', fetchToday, invalidate);
}
