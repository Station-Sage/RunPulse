// frontend/src/lib/formChart.ts
// 피트니스·폼 차트 순수 계산 — 두 패널(CTL/ATL · TSB) 공통 x축, y 범위, 좌표 변환, 스크럽 최근접. 테스트: frontend/tests/formChart.test.mjs

export interface Pt {
	date: string;
	value: number;
}
export interface FutureSeries {
	key: string;
	label: string;
	points: Pt[];
}
export interface FormInput {
	ctl: Pt[];
	atl: Pt[];
	tsb: Pt[];
	future: FutureSeries[];
	raceDate: string | null;
}
export interface FormLayout {
	t0: string;
	t1: string;
	today: string;
	top: { min: number; max: number };
	bottom: { min: number; max: number };
}

/** 레이스 최적 TSB 밴드 — race_hub formBand와 같은 기준 */
export const OPTIMAL_BAND = { lo: 5, hi: 25 };

/** 날짜의 [t0,t1] 내 위치 0~1 (구간 길이 0이면 0). */
export function xFrac(date: string, t0: string, t1: string): number {
	const a = Date.parse(t0);
	const b = Date.parse(t1);
	if (!(b > a)) return 0;
	return Math.min(1, Math.max(0, (Date.parse(date) - a) / (b - a)));
}

/** 값의 y 위치(0=위, 1=아래). */
export function yFrac(value: number, r: { min: number; max: number }): number {
	return (r.max - value) / (r.max - r.min);
}

/**
 * 공통 레이아웃. x: 이력 첫 날~(레이스 날짜 | 예측 마지막 | 이력 마지막) 중 가장 늦은 날.
 * 위 패널 y: 0~max(CTL,ATL)×1.08. 아래 패널 y: 최적 밴드가 항상 보이도록 [min(-10, 최솟값), max(30, 최댓값)]에 여백.
 * 이력(tsb)이 비어 있으면 null.
 */
export function buildFormLayout(input: FormInput): FormLayout | null {
	if (input.tsb.length === 0) return null;
	const hist = [...input.ctl, ...input.atl, ...input.tsb].map((p) => p.date).sort();
	const today = input.tsb[input.tsb.length - 1].date;
	const futureDates = input.future.flatMap((f) => f.points.map((p) => p.date));
	const ends = [today, ...futureDates, ...(input.raceDate ? [input.raceDate] : [])].sort();
	const loads = [...input.ctl, ...input.atl].map((p) => p.value);
	const topMax = Math.max(1, ...loads) * 1.08;
	const tsbVals = [...input.tsb, ...input.future.flatMap((f) => f.points)].map((p) => p.value);
	const lo = Math.min(-10, ...tsbVals);
	const hi = Math.max(30, ...tsbVals);
	const pad = (hi - lo) * 0.06;
	return {
		t0: hist[0],
		t1: ends[ends.length - 1],
		today,
		top: { min: 0, max: topMax },
		bottom: { min: lo - pad, max: hi + pad }
	};
}

/** 점들을 SVG 좌표 문자열로. w×h 패널, 위치는 레이아웃 기준. */
export function toPolyline(
	pts: Pt[],
	layout: FormLayout,
	range: { min: number; max: number },
	w: number,
	h: number
): string {
	return pts
		.map((p) => `${(xFrac(p.date, layout.t0, layout.t1) * w).toFixed(1)},${(yFrac(p.value, range) * h).toFixed(1)}`)
		.join(' ');
}

/** frac(0~1)에 가장 가까운 날짜의 점(없으면 null). */
export function nearestByFrac(pts: Pt[], frac: number, layout: FormLayout): Pt | null {
	let best: Pt | null = null;
	let bd = Infinity;
	for (const p of pts) {
		const d = Math.abs(xFrac(p.date, layout.t0, layout.t1) - frac);
		if (d < bd) {
			bd = d;
			best = p;
		}
	}
	return best;
}
