// 03e-coach.md 5-C — 플랜 없음 진입점: 활성 플랜 있으면 /coach/plan/{id}로 리다이렉트.
import { redirect } from '@sveltejs/kit';
import { getActivePlan, getRestorablePlans, type RestorablePlan } from '$lib/api/plan';
import { getToday, getRaceHub } from '$lib/api/today';
import type { ActivePlan, RaceHubGoal } from '$lib/types';
import { base } from '$app/paths';

export interface PlanGatewayData {
	ctlCurrent: number | null;
	goal: RaceHubGoal | null;
	restorable: RestorablePlan[];
	activeId: number | null;
}

export async function load({ url }): Promise<PlanGatewayData> {
	const plan: ActivePlan | null = await getActivePlan().catch(() => null);
	const past = url.searchParams.has('past');
	if (plan != null && !past) {
		throw redirect(302, `${base}/coach/plan/${plan.goal.id}`);
	}
	const [today, hub, rest] = await Promise.all([
		getToday().catch(() => null),
		getRaceHub().catch(() => null),
		getRestorablePlans().catch(() => ({ plans: [] as RestorablePlan[] }))
	]);
	return {
		ctlCurrent: today?.status.training_status.ctl ?? null,
		goal: hub?.goal ?? null,
		restorable: rest.plans,
		activeId: plan?.goal.id ?? null
	};
}
