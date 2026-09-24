import { getThreads } from '$lib/api/coach';
import { getActivePlan } from '$lib/api/plan';
import { getTodayCheckin } from '$lib/api/today';
import { ApiError } from '$lib/api/client';
import type { ThreadsListResponse, ActivePlan, CheckinRow } from '$lib/types';

export interface CoachPageData {
	result: ThreadsListResponse | null;
	activePlan: ActivePlan | null;
	checkin: CheckinRow | null;
	errorMessage: string | null;
}

export async function load(): Promise<CoachPageData> {
	const [threadsResult, activePlan, checkin] = await Promise.all([
		getThreads().catch((e: unknown) => {
			const message = e instanceof ApiError ? e.message : '대화 목록을 불러올 수 없습니다.';
			return { error: message };
		}),
		getActivePlan().catch(() => null),
		getTodayCheckin().catch(() => null)
	]);

	if ('error' in threadsResult) {
		return { result: null, activePlan, checkin, errorMessage: threadsResult.error };
	}
	return { result: threadsResult, activePlan, checkin, errorMessage: null };
}
