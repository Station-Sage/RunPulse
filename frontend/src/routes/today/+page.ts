import { getToday, getTodayNarrative } from '$lib/api/today';
import { getActivePlan, getTodaysAdjustment } from '$lib/api/plan';
import { ApiError } from '$lib/api/client';
import type { NarrativeResponse, TodayResponse, ActivePlan, TodaysAdjustment } from '$lib/types';

export interface TodayPageData {
	today: TodayResponse | null;
	errorMessage: string | null;
	narrative: NarrativeResponse | null;
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
}

export async function load(): Promise<TodayPageData> {
	try {
		const [today, narrative, plan, adjustment] = await Promise.all([
			getToday(),
			getTodayNarrative().catch(() => null),
			getActivePlan().catch(() => null),
			getTodaysAdjustment().catch(() => null)
		]);
		return { today, errorMessage: null, narrative, plan, adjustment };
	} catch (e) {
		// running.db 없음(NOT_FOUND/503) 등 — 1-E "데이터 없음" 상태로 처리(03a-today.md).
		const message = e instanceof ApiError ? e.message : '오늘 데이터를 불러올 수 없습니다.';
		return { today: null, errorMessage: message, narrative: null, plan: null, adjustment: null };
	}
}
