// 03e-coach.md 5-C — 플랜 없음 진입점: 활성 플랜 있으면 /coach/plan/{id}로 리다이렉트.
import { redirect } from '@sveltejs/kit';
import { getActivePlan, } from '$lib/api/plan';
import { getToday, getRaceHub } from '$lib/api/today';
import type { ActivePlan, RaceHubGoal } from '$lib/types';
import { base } from '$app/paths';

export interface PlanGatewayData {
	ctlCurrent: number | null;
	goal: RaceHubGoal | null;
}

export async function load(): Promise<PlanGatewayData> {
	const plan: ActivePlan | null = await getActivePlan().catch(() => null);
	if (plan != null) {
		throw redirect(302, `${base}/coach/plan/${plan.goal.id}`);
	}
	const [today, hub] = await Promise.all([
		getToday().catch(() => null),
		getRaceHub().catch(() => null)
	]);
	return { ctlCurrent: today?.status.training_status.ctl ?? null, goal: hub?.goal ?? null };
}
