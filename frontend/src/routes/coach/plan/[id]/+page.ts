import { getActivePlan, getTodaysAdjustment, getPlanAdaptation, getReplanLast, getPlanWeeks } from '$lib/api/plan';
import { toResult, type Failure } from '$lib/loadFailure';
import type { ActivePlan, TodaysAdjustment, PlanAdaptation, ReplanEntry, PlanWeeks } from '$lib/types';

export interface PlanDetailPageData {
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | null;
	adaptation: PlanAdaptation | null;
	replanEntry: ReplanEntry | null;
	weeks: PlanWeeks | null;
	errorMessage: string | null;
	planFailure: Failure | null;
	weeksFailure: Failure | null;
	adaptationFailure: Failure | null;
}

export async function load({
	params,
	depends
}: {
	params: { id: string };
	depends: (k: string) => void;
}): Promise<PlanDetailPageData> {
	depends('app:plan-active');
	const goalId = parseInt(params.id, 10);
	if (isNaN(goalId)) {
		return { plan: null, adjustment: null, adaptation: null, replanEntry: null, weeks: null, errorMessage: '잘못된 플랜 ID입니다.', planFailure: null, weeksFailure: null, adaptationFailure: null };
	}
	const [planR, adjustment, adaptationR, last, weeksR] = await Promise.all([
		toResult(getActivePlan(goalId)),
		getTodaysAdjustment().catch(() => null) as Promise<TodaysAdjustment | null>,
		toResult(getPlanAdaptation()),
		getReplanLast().catch(() => null),
		toResult(getPlanWeeks(goalId))
	]);
	const plan = planR.ok ? planR.data : null;
	const adaptation = adaptationR.ok ? adaptationR.data : null;
	const weeks = weeksR.ok ? weeksR.data : null;
	return {
		plan,
		adjustment,
		adaptation,
		replanEntry: last?.entry ?? null,
		weeks,
		errorMessage: plan === null ? '플랜을 불러올 수 없습니다.' : null,
		planFailure: planR.ok ? null : planR.failure,
		weeksFailure: weeksR.ok ? null : weeksR.failure,
		adaptationFailure: adaptationR.ok ? null : adaptationR.failure
	};
}
