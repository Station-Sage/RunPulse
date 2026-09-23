import { getActivePlan, getTodaysAdjustment } from '$lib/api/plan';
import { ApiError } from '$lib/api/client';
import type { ActivePlan, TodaysAdjustment } from '$lib/types';

export interface PlanDetailPageData {
	plan: ActivePlan | null;
	adjustment: TodaysAdjustment | null;
	errorMessage: string | null;
}

export async function load({
	params
}: {
	params: { id: string };
}): Promise<PlanDetailPageData> {
	const goalId = parseInt(params.id, 10);
	if (isNaN(goalId)) {
		return { plan: null, adjustment: null, errorMessage: '잘못된 플랜 ID입니다.' };
	}
	const [plan, adjustment] = await Promise.all([
		getActivePlan(goalId).catch(() => null),
		getTodaysAdjustment().catch(() => null) as Promise<TodaysAdjustment | null>
	]);
	return {
		plan,
		adjustment,
		errorMessage: plan === null ? '플랜을 불러올 수 없습니다.' : null
	};
}
