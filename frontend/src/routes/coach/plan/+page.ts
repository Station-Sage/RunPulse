// 03e-coach.md 5-C — 플랜 없음 진입점: 활성 플랜 있으면 /coach/plan/{id}로 리다이렉트.
import { redirect } from '@sveltejs/kit';
import { getActivePlan, getRestorablePlans, type RestorablePlan } from '$lib/api/plan';
import { getToday, getRaceHub } from '$lib/api/today';
import type { ActivePlan, RaceHubGoal } from '$lib/types';
import { base } from '$app/paths';
import { classifyFailure, nullOn404, type Failure } from '$lib/loadFailure';

export interface PlanGatewayData {
	ctlCurrent: number | null;
	goal: RaceHubGoal | null;
	restorable: RestorablePlan[];
	activeId: number | null;
	planFailure: Failure | null;
}

export async function load({ url, depends }): Promise<PlanGatewayData> {
	depends('app:plan-active');
	// 404(활성 플랜 없음)만 정상 빈 상태. 네트워크·서버 실패는 구분해 보여준다(ERR-2).
	let plan: ActivePlan | null = null;
	let planFailure: Failure | null = null;
	try {
		plan = await nullOn404(getActivePlan());
	} catch (e) {
		planFailure = classifyFailure(e);
	}
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
		activeId: plan?.goal.id ?? null,
		planFailure
	};
}
