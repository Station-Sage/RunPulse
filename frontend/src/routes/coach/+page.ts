import { getThreads, getEngine } from '$lib/api/coach';
import { getActivePlan } from '$lib/api/plan';
import { getTodayCheckin, getRaceHub } from '$lib/api/today';
import { ApiError } from '$lib/api/client';
import type { ThreadsListResponse, ActivePlan, CheckinRow, RaceHubGoal, CoachEngine } from '$lib/types';

export interface CoachPageData {
	result: ThreadsListResponse | null;
	activePlan: ActivePlan | null;
	checkin: CheckinRow | null;
	goal: RaceHubGoal | null;
	errorMessage: string | null;
	engine: CoachEngine | null;
}

export async function load(): Promise<CoachPageData> {
	const [threadsResult, activePlan, checkin, hub, engine] = await Promise.all([
		getThreads().catch((e: unknown) => {
			const message = e instanceof ApiError ? e.message : '대화 목록을 불러올 수 없습니다.';
			return { error: message };
		}),
		getActivePlan().catch(() => null),
		getTodayCheckin().catch(() => null),
		getRaceHub().catch(() => null),
		getEngine().catch(() => null)
	]);

	if ('error' in threadsResult) {
		return { result: null, activePlan, checkin, goal: hub?.goal ?? null, errorMessage: threadsResult.error, engine };
	}
	return { result: threadsResult, activePlan, checkin, goal: hub?.goal ?? null, errorMessage: null, engine };
}
