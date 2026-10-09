// 플랜 행 액션(직접 조정)의 순수 표시 로직 — 백엔드 규칙(plan_adjustment_service)과 일치해야 한다.
import type { PlannedWorkout, WorkoutActionResult } from '$lib/types';

export type RowOp = 'reduce' | 'easy' | 'rest' | 'skip' | 'move';
export type RowActionMode = 'hidden' | 'locked' | 'active';

export const MAX_REDUCE_PCT = 50;
export const MIN_REDUCED_KM = 3;
const WORK_FLOOR_KM: Record<string, number> = { tempo: 2, threshold: 2, marathon: 5, long_mp: 5 };
const WORK_PCTS = [20, 30];
const LONG_PCTS = [15, 30];
const EASY_FROM = ['interval', 'long', ...Object.keys(WORK_FLOOR_KM)];

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
	easy: { ok: boolean; hint: string | null };
	rest: { ok: boolean };
	skip: { ok: boolean };
	move: { ok: boolean; hint: string | null };
}

const DAY_KO = ['일', '월', '화', '수', '목', '금', '토'];

// 오늘 세션을 옮길 수 있는 후보 날짜 — 내일부터 3일 이내, 같은 주(월~일). 세부 규칙은 서버가 판정한다.
export function moveCandidates(today: string): { date: string; label: string }[] {
	const t = new Date(today + 'T00:00:00Z');
	const wk = (d: Date) => Math.floor((d.getTime() / 86400000 + 3) / 7);
	const out: { date: string; label: string }[] = [];
	for (let i = 1; i <= 3; i++) {
		const d = new Date(t.getTime() + i * 86400000);
		if (wk(d) !== wk(t)) break;
		out.push({ date: d.toISOString().slice(0, 10), label: `${DAY_KO[d.getUTCDay()]} ${d.getUTCMonth() + 1}/${d.getUTCDate()}` });
	}
	return out;
}

export function reducedKm(km: number, pct: number): number {
	return Math.round(km * (1 - pct / 100) * 10) / 10;
}

export function intervalSets(w: Pick<PlannedWorkout, 'interval_prescription'>): number | null {
	try {
		const n = Number(JSON.parse(w.interval_prescription ?? 'null')?.sets);
		return Number.isFinite(n) && n > 0 ? n : null;
	} catch {
		return null;
	}
}

// reduce 의 입력 방식 — 인터벌은 반복 횟수, 강도·롱런은 정해진 비율, 쉬운 러닝은 자유 비율.
export type ReduceInput = { kind: 'reps' | 'pct'; options: number[]; free: boolean };

export function reduceInput(w: PlannedWorkout): ReduceInput {
	const t = w.workout_type;
	if (t === 'interval') {
		const sets = intervalSets(w) ?? 0;
		return { kind: 'reps', options: [1, 2].filter((r) => sets - r >= 2 && (sets - r) * 2 >= sets), free: false };
	}
	if (t in WORK_FLOOR_KM) return { kind: 'pct', options: WORK_PCTS.filter((p) => reducedKm(w.distance_km ?? 0, p) >= WORK_FLOOR_KM[t]), free: false };
	if (t === 'long') return { kind: 'pct', options: LONG_PCTS, free: false };
	return { kind: 'pct', options: [20, 40], free: true };
}

export function opAvailability(w: PlannedWorkout): OpAvailability {
	const km = w.distance_km ?? 0;
	const inp = reduceInput(w);
	let hint: string | null = null;
	if (w.workout_type === 'race') hint = '레이스는 줄일 수 없어요';
	else if (w.workout_type === 'interval' && !inp.options.length) hint = '반복을 줄이면 구성이 무너져요 · 쉬운 러닝으로 바꾸거나 쉬세요';
	else if (km <= 0) hint = '거리가 없는 세션이에요';
	else if (!inp.options.length) hint = '더 줄이면 너무 짧아져요 · 쉬는 편이 나아요';
	else if (inp.free && reducedKm(km, 20) < MIN_REDUCED_KM) hint = `줄이면 ${MIN_REDUCED_KM}km 미만이 돼요 · 쉬는 편이 나아요`;
	const moveHint = w.workout_type === 'race' ? '레이스는 옮길 수 없어요' : null;
	const easyOk = EASY_FROM.includes(w.workout_type);
	return {
		reduce: { ok: hint === null, hint }, easy: { ok: easyOk, hint: easyOk ? null : '이미 쉬운 세션이에요' },
		rest: { ok: true }, skip: { ok: true }, move: { ok: moveHint === null, hint: moveHint }
	};
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
	if (op === 'easy') return `오늘은 쉬운 러닝으로 바꿨어요${tail}`;
	if (op === 'rest') return `오늘은 쉬어요${tail}`;
	if (op === 'move') return `${res.adjustment.after.date?.slice(5).replace('-', '/')}로 옮겼어요`;
	return `오늘 세션을 건너뛰었어요${tail}`;
}

const MOVE_ERRORS: Record<string, string> = {
	RACE_FIXED: '레이스는 옮길 수 없어요',
	PAIN_NO_MOVE: '통증이 있으면 옮기지 말고 쉬어 주세요',
	ALREADY_MOVED: '이미 옮긴 세션이에요 · 되돌린 뒤 다시 옮겨 주세요',
	OUT_OF_RANGE: '내일부터 3일 이내로만 옮길 수 있어요',
	CROSS_WEEK: '같은 주 안에서만 옮길 수 있어요',
	TAPER_LOCK: '대회 직전 테이퍼 기간에는 옮길 수 없어요',
	TARGET_DONE: '이미 수행한 날이에요',
	TARGET_HARD: '그날도 강한 훈련이 있어요 · 다른 날을 골라 주세요',
	HARD_SPACING: '강한 훈련이 연속돼요 · 다른 날을 골라 주세요',
	NOT_TODAY: '오늘 세션만 옮길 수 있어요'
};

export function actionErrorText(e: unknown): string {
	const err = e as { status?: number; details?: unknown; message?: string } | null;
	if (err && typeof err.status === 'number') {
		const e2 = err as { status: number; details?: unknown; message?: string };
		const reason = (e2.details as { reason?: string } | undefined)?.reason;
		if (e2.status === 409 && reason === 'LOCKED') return '오늘 세션만 바꿀 수 있어요';
		if (e2.status === 409 && reason && MOVE_ERRORS[reason]) return MOVE_ERRORS[reason];
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

export interface LoadDelta {
	week_pct: number;
	acwr_before: number | null;
	acwr_after: number | null;
	week_load_before: number;
	week_load_after: number;
}

const acwrZone = (v: number) => (v < 0.8 ? 'low' : v > 1.3 ? 'high' : 'ok');

/** 시트의 부하 미리보기 한 줄. 색은 ACWR 이 0.8/1.3 경계를 넘나들 때만(tone='warn'). */
export function loadDeltaView(d: LoadDelta | null | undefined): { text: string; tone: 'warn' | 'none' } | null {
	if (!d || Math.abs(d.week_pct) < 0.5) return null;
	const pct = Math.round(d.week_pct);
	let text = `이번 주 부하 ${pct > 0 ? '+' : '−'}${Math.abs(pct)}%`;
	let tone: 'warn' | 'none' = 'none';
	if (d.acwr_before != null && d.acwr_after != null) {
		text += ` · ACWR ${d.acwr_before.toFixed(2)} → ${d.acwr_after.toFixed(2)}`;
		if (acwrZone(d.acwr_before) !== acwrZone(d.acwr_after)) tone = 'warn';
	}
	return { text, tone };
}
