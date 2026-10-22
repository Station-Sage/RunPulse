import { getThreads, getEngine, getSuggestions } from '$lib/api/coach';
import { getActivePlan } from '$lib/api/plan';
import { getTodayCheckin, getRaceHub, getToday } from '$lib/api/today';
import { toResult, type Failure } from '$lib/loadFailure';
import type { UnlockMap } from '$lib/unlock';
import type { ThreadsListResponse, ActivePlan, CheckinRow, RaceHubGoal, CoachEngine, CoachChip } from '$lib/types';

export interface CoachPageData {
	result: ThreadsListResponse | null;
	activePlan: ActivePlan | null;
	checkin: CheckinRow | null;
	goal: RaceHubGoal | null;
	errorMessage: string | null;
	threadsFailure: Failure | null;
	engine: CoachEngine | null;
	suggestions: CoachChip[];
	unlock: UnlockMap | null;
}

export async function load({ depends }: { depends: (k: string) => void }): Promise<CoachPageData> {
	depends('app:coach-threads');
	const [threadsResult, activePlan, checkin, hub, engine, suggested, today] = await Promise.all([
		toResult(getThreads()),
		getActivePlan().catch(() => null),
		getTodayCheckin().catch(() => null),
		getRaceHub().catch(() => null),
		getEngine().catch(() => null),
		getSuggestions().catch(() => null),
		getToday().catch(() => null)
	]);
	const suggestions = suggested?.suggestions ?? [];
	const unlock = today?.unlock ?? null;

	const base = { activePlan, checkin, goal: hub?.goal ?? null, engine, suggestions, unlock };
	if (!threadsResult.ok) {
		return { ...base, result: null, errorMessage: threadsResult.failure.detail ?? null, threadsFailure: threadsResult.failure };
	}
	return { ...base, result: threadsResult.data, errorMessage: null, threadsFailure: null };
}
