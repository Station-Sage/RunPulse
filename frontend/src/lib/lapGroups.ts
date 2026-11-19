// 랩 표 보조 계산 — 랩 페이스, 인터벌(워크/회복) 분류와 그룹 평균(20 §2-6).
import type { ActivityLap } from '$lib/types';

export function lapPace(l: ActivityLap): number | null {
	if (l.avg_pace_sec_km != null && l.avg_pace_sec_km > 0) return l.avg_pace_sec_km;
	if (l.distance_m && l.duration_sec && l.distance_m > 0) return l.duration_sec / (l.distance_m / 1000);
	return null;
}

export type LapRole = 'work' | 'recovery';

export interface IntervalSummary {
	roles: (LapRole | null)[];
	workAvg: number;
	recoveryAvg: number;
}

const MIN_LAPS = 5;
const MIN_GAP_SEC = 60;
const MIN_TRANSITIONS = 3;

/** 페이스가 빠른/느린 두 무리로 번갈아 나오면 인터벌. 그렇지 않으면 null(일반 랩 표). */
export function classifyIntervals(laps: ActivityLap[]): IntervalSummary | null {
	const paces = laps.map(lapPace);
	const valid = paces.filter((p): p is number => p != null);
	if (laps.length < MIN_LAPS || valid.length < MIN_LAPS) return null;
	const lo = Math.min(...valid);
	const hi = Math.max(...valid);
	if (hi - lo < MIN_GAP_SEC) return null;
	const mid = (lo + hi) / 2;
	const roles = paces.map((p): LapRole | null => (p == null ? null : p < mid ? 'work' : 'recovery'));
	const seq = roles.filter((r): r is LapRole => r != null);
	let transitions = 0;
	for (let i = 1; i < seq.length; i++) if (seq[i] !== seq[i - 1]) transitions++;
	if (transitions < MIN_TRANSITIONS) return null;
	const avg = (r: LapRole) => {
		const xs = paces.filter((_, i) => roles[i] === r) as number[];
		return xs.reduce((a, b) => a + b, 0) / xs.length;
	};
	return { roles, workAvg: avg('work'), recoveryAvg: avg('recovery') };
}

/** 발산 막대: 기준 페이스 대비 ±30초/km를 −1..1로 정규화(빠름=+). */
export function divergence(pace: number | null, base: number | null, range = 30): number {
	if (pace == null || base == null) return 0;
	return Math.max(-1, Math.min(1, (base - pace) / range));
}

/** 마지막 랩이 다른 랩 거리 중앙값의 절반 미만이면 자투리 랩(A-08). */
export function isPartialLastLap(laps: ActivityLap[], i: number): boolean {
	if (i !== laps.length - 1 || laps.length < 3) return false;
	const d = laps[i].distance_m;
	const others = laps.slice(0, -1).map((l) => l.distance_m).filter((x): x is number => x != null && x > 0).sort((a, b) => a - b);
	if (d == null || others.length === 0) return false;
	const median = others[Math.floor(others.length / 2)];
	return d < median * 0.5;
}

/** "가장 빠른 랩" — 자투리 마지막 랩은 제외(A-08). 값이 없으면 null. */
export function fastestLap(laps: ActivityLap[]): { pace: number; index: number } | null {
	let best: { pace: number; index: number } | null = null;
	for (let i = 0; i < laps.length; i++) {
		const p = lapPace(laps[i]);
		if (p == null || isPartialLastLap(laps, i)) continue;
		if (best == null || p < best.pace) best = { pace: p, index: i };
	}
	return best;
}

/** 시간 열(랩 전체 시간)과 페이스 열(소스 페이스, 보통 이동 시간 기준)이 1초 넘게 어긋나는 랩이 있는지(A-09). */
export function lapPaceBasisDiffers(laps: ActivityLap[]): boolean {
	return laps.some((l) => {
		if (l.avg_pace_sec_km == null || !l.distance_m || !l.duration_sec) return false;
		return Math.abs(l.duration_sec / (l.distance_m / 1000) - l.avg_pace_sec_km) >= 1;
	});
}

export interface StepBlock {
	kind: string;
	label: string;
	idx: number[];
	distance: number;
	duration: number;
	pace: number | null;
}

const KIND_LABEL: Record<string, string> = { WARMUP: '워밍업', RECOVERY: '회복', COOLDOWN: '쿨다운', REST: '휴식' };

/** 워치가 기록한 랩 단계(lap_kind)로 연속 구간을 묶고 소계(거리·시간·합산 페이스)를 낸다. 단계가 2종 미만이면 null. */
export function groupByStep(laps: ActivityLap[]): StepBlock[] | null {
	const kinds = new Set(laps.map((l) => l.lap_kind).filter((k): k is string => !!k));
	if (kinds.size < 2 || laps.some((l) => !l.lap_kind)) return null;
	const out: StepBlock[] = [];
	let sets = 0;
	laps.forEach((l, i) => {
		const k = l.lap_kind as string;
		let b = out[out.length - 1];
		if (!b || b.kind !== k) {
			if (k === 'ACTIVE') sets++;
			b = { kind: k, label: k === 'ACTIVE' ? `인터벌 ${sets}` : (KIND_LABEL[k] ?? k), idx: [], distance: 0, duration: 0, pace: null };
			out.push(b);
		}
		b.idx.push(i);
		b.distance += l.distance_m ?? 0;
		b.duration += l.duration_sec ?? 0;
	});
	for (const b of out) b.pace = b.distance > 0 && b.duration > 0 ? b.duration / (b.distance / 1000) : null;
	if (sets === 1) for (const b of out) if (b.kind === 'ACTIVE') b.label = '인터벌';
	return out;
}
