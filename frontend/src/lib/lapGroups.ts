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
