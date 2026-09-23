// 03e-coach.md 5-F/5-D/5-E — Coach 플랜 조회 + 생성 API.
import { apiFetch } from './client';
import type { ActivePlan, TodaysAdjustment, PlanTemplate, CreatePlanPayload } from '$lib/types';

export function getActivePlan(goalId?: number): Promise<ActivePlan> {
	const path = goalId != null ? `/coach/plan/${goalId}` : '/coach/plan/active';
	return apiFetch<ActivePlan>(path);
}

export function getTodaysAdjustment(): Promise<
	TodaysAdjustment | { adjusted: false; adjustment_reason: null }
> {
	return apiFetch('/coach/plan/adjustment');
}

export function getPlanTemplates(
	distanceKm: number,
	targetTimeSec?: number
): Promise<PlanTemplate[]> {
	const params = new URLSearchParams({ distance_km: String(distanceKm) });
	if (targetTimeSec != null) params.set('target_time_sec', String(targetTimeSec));
	return apiFetch<PlanTemplate[]>(`/coach/plan/templates?${params}`);
}

export function createPlan(payload: CreatePlanPayload): Promise<number> {
	return apiFetch<{ goal_id: number }>('/coach/plan', {
		method: 'POST',
		body: JSON.stringify(payload)
	}).then((r) => r.goal_id);
}
