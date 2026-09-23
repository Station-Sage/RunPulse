// 03e-coach.md 5-F — Coach 플랜 조회 API.
import { apiFetch } from './client';
import type { ActivePlan, TodaysAdjustment } from '$lib/types';

export function getActivePlan(goalId?: number): Promise<ActivePlan> {
	const path = goalId != null ? `/coach/plan/${goalId}` : '/coach/plan/active';
	return apiFetch<ActivePlan>(path);
}

export function getTodaysAdjustment(): Promise<
	TodaysAdjustment | { adjusted: false; adjustment_reason: null }
> {
	return apiFetch('/coach/plan/adjustment');
}
