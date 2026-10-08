// 플랜 행 액션(직접 조정)의 순수 표시 로직 — 백엔드 규칙(plan_adjustment_service)과 일치해야 한다.
import type { PlannedWorkout, WorkoutActionResult } from '$lib/types';

export type RowOp = 'reduce' | 'rest' | 'skip';
export type RowActionMode = 'hidden' | 'locked' | 'active';

export const MAX_REDUCE_PCT = 50;
export const MIN_REDUCED_KM = 3;
const PCT_BLOCKED = ['interval', 'tempo', 'threshold', 'marathon', 'race'];

export const REASONS: { key: string; label: string }[] = [
	{ key: 'fatigue', label: '피로' },
	{ key: 'injury', label: '통증' },
	{ key: 'schedule', label: '일정' }
];

export function reasonLabel(key: string | null | undefined): string {
	return REASONS.find((r) => r.key === key)?.label ?? '';
}

export function rowActionMode(w: PlannedWorkout, today: string): RowActionMode {
	if (w.completed || w.superseded || w.date < today) return 'hidden';
	if (w.workout_type === 'rest' && !w.adjusted) return 'hidden';
	return w.date > today ? 'locked' : 'active';
}

export interface OpAvailability {
	reduce: { ok: boolean; hint: string | null };
	rest: { ok: boolean };
	skip: { ok: boolean };
}

export function reducedKm(km: number, pct: number): number {
	return Math.round(km * (1 - pct / 100) * 10) / 10;
}

export function opAvailability(w: PlannedWorkout): OpAvailability {
	const km = w.distance_km ?? 0;
	let hint: string | null = null;
	if (PCT_BLOCKED.includes(w.workout_type)) hint = '강도 세션은 비율로 줄일 수 없어요 · 쉬기나 건너뛰기를 선택해 주세요';
	else if (km <= 0) hint = '거리가 없는 세션이에요';
	else if (reducedKm(km, 20) < MIN_REDUCED_KM) hint = `줄이면 ${MIN_REDUCED_KM}km 미만이 돼요 · 쉬는 편이 나아요`;
	return { reduce: { ok: hint === null, hint }, rest: { ok: true }, skip: { ok: true } };
}

export function reducePreview(km: number, pct: number): { km: number; valid: boolean; hint: string | null } {
	const out = reducedKm(km, pct);
	if (pct < 1 || pct > MAX_REDUCE_PCT) return { km: out, valid: false, hint: `${MAX_REDUCE_PCT}%까지 줄일 수 있어요` };
	if (out < MIN_REDUCED_KM) return { km: out, valid: false, hint: `${MIN_REDUCED_KM}km 미만은 쉬는 편이 나아요` };
	return { km: out, valid: true, hint: null };
}

export function weekPreview(weekKm: number, cutKm: number): { before: number; after: number } {
	const r = (v: number) => Math.round(v * 10) / 10;
	return { before: r(weekKm), after: r(Math.max(0, weekKm - cutKm)) };
}

function fmt(v: number | null | undefined): string {
	return v == null ? '' : ` · 이번 주 ${v}km`;
}

export function toastText(op: RowOp, res: WorkoutActionResult): string {
	const wk = res.week_planned_km;
	const tail = wk.before != null && wk.after != null ? ` · 이번 주 ${wk.before}→${wk.after}km` : fmt(wk.after);
	if (op === 'reduce') return `오늘 ${res.adjustment.after.distance_km}km로 줄였어요${tail}`;
	if (op === 'rest') return `오늘은 쉬어요${tail}`;
	return `오늘 세션을 건너뛰었어요${tail}`;
}

export function actionErrorText(e: unknown): string {
	const err = e as { status?: number; details?: unknown; message?: string } | null;
	if (err && typeof err.status === 'number') {
		const e2 = err as { status: number; details?: unknown; message?: string };
		const reason = (e2.details as { reason?: string } | undefined)?.reason;
		if (e2.status === 409 && reason === 'LOCKED') return '오늘 세션만 바꿀 수 있어요';
		if (e2.status === 409 && reason === 'UNSUPPORTED') return '아직 지원하지 않는 조정이에요';
		if (e2.status === 409) return '다른 곳에서 계획이 바뀌었어요 · 새로고침 후 다시 시도해 주세요';
		if (e2.status === 404) return '세션을 찾을 수 없어요 · 새로고침해 주세요';
		if (e2.status === 400) return e2.message || '이 조정은 적용할 수 없어요';
	}
	return '처리하지 못했어요 · 잠시 후 다시 시도해 주세요';
}

export function userAdjustmentSummary(w: PlannedWorkout, label: (t: string) => string): { badge: string; original: string } | null {
	if (!w.adjusted || !w.adjustment || !w.original || w.adjustment.source === 'crs') return null;
	const o = w.original;
	const km = o.distance_km != null ? ` ${o.distance_km}km` : '';
	return { badge: w.adjustment.source === 'coach' ? '코치 조정' : '직접 조정', original: `원래 ${label(o.workout_type)}${km}` };
}
