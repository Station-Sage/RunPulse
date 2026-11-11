// P-25 — 스트리밍 로더: 플랜만 기다리고 보조 데이터는 약속으로 넘긴다(규칙은 $lib/planDetailLoad).
import { getActivePlan, getTodaysAdjustment, getPlanAdaptation, getReplanLast, getPlanWeeks } from '$lib/api/plan';
import { loadPlanDetail, type PlanDetailPageData } from '$lib/planDetailLoad';

export type { PlanDetailPageData };

export function load({
	params,
	depends
}: {
	params: { id: string };
	depends: (k: string) => void;
}): Promise<PlanDetailPageData> {
	depends('app:plan-active');
	return loadPlanDetail(params.id, { getActivePlan, getTodaysAdjustment, getPlanAdaptation, getReplanLast, getPlanWeeks });
}
