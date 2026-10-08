// 03e-coach.md 5-F/5-D/5-E/5-G — Coach 플랜 조회 + 생성 + 세션 상세 API.
import { apiFetch } from './client';
import type {
	ActivePlan,
	TodaysAdjustment,
	PlanTemplate,
	CreatePlanPayload,
	CreatePlanResult,
	SessionDetail,
	PlanAdaptation,
	AdjustmentDecisionResult,
	PlanAdjustment,
	WorkoutActionResult
} from '$lib/types';

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
	targetTimeSec?: number,
	raceDate?: string
): Promise<PlanTemplate[]> {
	const params = new URLSearchParams({ distance_km: String(distanceKm) });
	if (targetTimeSec != null) params.set('target_time_sec', String(targetTimeSec));
	if (raceDate) params.set('race_date', raceDate);
	return apiFetch<PlanTemplate[]>(`/coach/plan/templates?${params}`);
}

export function createPlan(payload: CreatePlanPayload): Promise<CreatePlanResult> {
	return apiFetch<CreatePlanResult>('/coach/plan', {
		method: 'POST',
		body: JSON.stringify(payload)
	}).then((r) => ({ ...r, warnings: r.warnings ?? [] }));
}

export function getSessionDetail(goalId: number, date: string): Promise<SessionDetail> {
	return apiFetch<SessionDetail>(`/coach/plan/${goalId}/session/${date}`);
}

export function saveSessionNote(date: string, note: string): Promise<void> {
	return apiFetch<{ note: string }>(`/coach/plan/session/${date}/note`, {
		method: 'POST',
		body: JSON.stringify({ note })
	}).then(() => undefined);
}

export function getPlanAdaptation(): Promise<PlanAdaptation> {
	return apiFetch<{ adaptation: PlanAdaptation }>('/coach/plan/adaptation').then((r) => r.adaptation);
}

export function acceptAdjustment(
	id: number,
	rev: number,
	via: string
): Promise<AdjustmentDecisionResult> {
	return apiFetch(`/coach/plan/adjustments/${id}/accept`, {
		method: 'POST',
		body: JSON.stringify({ rev, via })
	});
}

export function revertAdjustment(id: number, via: string): Promise<AdjustmentDecisionResult> {
	return apiFetch(`/coach/plan/adjustments/${id}/revert`, {
		method: 'POST',
		body: JSON.stringify({ via })
	});
}

export function listAdjustments(goalId: number, from: string, to: string): Promise<{ adjustments: PlanAdjustment[] }> {
	return apiFetch(`/coach/plan/${goalId}/adjustments?from=${from}&to=${to}`);
}

export interface WorkoutActionBody {
	op: 'reduce' | 'rest' | 'skip';
	pct?: number;
	reason?: string;
	via: string;
}

export function workoutAction(workoutId: number, body: WorkoutActionBody): Promise<WorkoutActionResult> {
	return apiFetch(`/coach/plan/workouts/${workoutId}/action`, {
		method: 'POST',
		body: JSON.stringify(body)
	});
}
