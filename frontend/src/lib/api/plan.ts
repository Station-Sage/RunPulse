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
	WorkoutActionResult,
	ReplanParams,
	ReplanPreview,
	ReplanUndoResult
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
	op: 'reduce' | 'easy' | 'rest' | 'skip' | 'move';
	pct?: number;
	reps?: number;
	to_date?: string;
	reason?: string;
	pain_level?: string;
	pain_sites?: string[];
	via: string;
}

export function workoutAction(workoutId: number, body: WorkoutActionBody): Promise<WorkoutActionResult> {
	return apiFetch(`/coach/plan/workouts/${workoutId}/action`, {
		method: 'POST',
		body: JSON.stringify(body)
	});
}

export function previewWorkoutAction(
	workoutId: number,
	q: { op: string; pct?: number; reps?: number; pain_level?: string; pain_sites?: string[] }
): Promise<{ load_delta: import('$lib/rowActionView').LoadDelta | null }> {
	const p = new URLSearchParams({ op: q.op });
	if (q.pct != null) p.set('pct', String(q.pct));
	if (q.reps != null) p.set('reps', String(q.reps));
	if (q.pain_level) { p.set('reason', 'pain'); p.set('pain_level', q.pain_level); p.set('pain_sites', (q.pain_sites ?? []).join(',')); }
	return apiFetch(`/coach/plan/workouts/${workoutId}/action/preview?${p}`);
}

export function getPlanAdvisories(date: string): Promise<{ advisories: import('$lib/replanBanner').PlanAdvisory[] }> {
	return apiFetch(`/coach/plan/advisories?date=${date}`);
}

export function previewReplan(q: string): Promise<ReplanPreview> {
	return apiFetch<ReplanPreview>(`/coach/plan/replan/preview${q ? `?${q}` : ''}`);
}

export function applyReplan(params: ReplanParams, expectAnchor: string): Promise<ReplanPreview> {
	return apiFetch<ReplanPreview>('/coach/plan/replan', {
		method: 'POST',
		body: JSON.stringify({ ...params, expect_anchor: expectAnchor })
	});
}

export function undoReplan(replanId: number): Promise<ReplanUndoResult> {
	return apiFetch<ReplanUndoResult>(`/coach/plan/replan/${replanId}/undo`, { method: 'POST' });
}

export function getReplanLast(): Promise<{ last: import('$lib/types').ReplanLast | null; entry: import('$lib/types').ReplanEntry }> {
	return apiFetch('/coach/plan/replan/last');
}

export interface GarminCleanupResult {
	deleted: number;
	missing: number;
	failed: { date: string; error: string }[];
}

export function cleanupGarmin(replanId: number): Promise<GarminCleanupResult> {
	return apiFetch<GarminCleanupResult>(`/coach/plan/replan/${replanId}/garmin-cleanup`, { method: 'POST' });
}
