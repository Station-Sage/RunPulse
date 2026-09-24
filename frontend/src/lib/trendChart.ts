// frontend/src/lib/trendChart.ts
// 추세 차트 순수 함수 — 공통 y 범위·날짜 x 위치·스크럽 최근접점·변화 라벨. 테스트: frontend/tests/trendChart.test.mjs

export interface TrendPoint {
	date: string;
	value: number;
}

export interface TrendSeries {
	key: string;
	label: string;
	color: string;
	points: TrendPoint[];
}

/** 모든 시리즈를 한 축에 그릴 공통 y 범위(위아래 5% 여백, 데이터가 전부 0 이상이면 아래 여백이 0을 넘지 않음). 값이 하나도 없으면 null. 최댓값=최솟값이면 ±1. */
export function commonRange(series: TrendSeries[]): { min: number; max: number } | null {
	const vals = series.flatMap((s) => s.points.map((p) => p.value));
	if (vals.length === 0) return null;
	let min = Math.min(...vals);
	let max = Math.max(...vals);
	if (min === max) {
		min -= 1;
		max += 1;
	}
	const pad = (max - min) * 0.05;
	const lo = min >= 0 ? Math.max(0, min - pad) : min - pad;
	return { min: lo, max: max + pad };
}

/** 날짜(YYYY-MM-DD)의 [t0, t1] 구간 내 위치 0~1 — 시리즈마다 날짜가 달라도 같은 x축에 놓기 위함. 구간 길이가 0이면 0. */
export function xFraction(date: string, t0: string, t1: string): number {
	const a = Date.parse(t0);
	const b = Date.parse(t1);
	if (!(b > a)) return 0;
	return Math.min(1, Math.max(0, (Date.parse(date) - a) / (b - a)));
}

/** 위치 frac(0~1)에 가장 가까운 날짜의 점. 점이 없으면 null. */
export function nearestPoint(
	points: TrendPoint[],
	frac: number,
	t0: string,
	t1: string
): TrendPoint | null {
	let best: TrendPoint | null = null;
	let bestD = Infinity;
	for (const p of points) {
		const d = Math.abs(xFraction(p.date, t0, t1) - frac);
		if (d < bestD) {
			bestD = d;
			best = p;
		}
	}
	return best;
}

/** "N일 변화" 라벨 — 기준값(N일 전 이하의 마지막 점, 없으면 첫 점)이 작으면(|기준|<10) 퍼센트가 무의미하므로 절대 변화(+33.4)로, 아니면 퍼센트(+13.0%)로. 점이 없으면 '—'. */
export function changeLabel(points: TrendPoint[], days = 30): string {
	if (points.length === 0) return '—';
	const last = points[points.length - 1];
	const cutoff = Date.parse(last.date) - days * 86_400_000;
	let base = points[0];
	for (const p of points) if (Date.parse(p.date) <= cutoff) base = p;
	const delta = last.value - base.value;
	const sign = delta >= 0 ? '+' : '';
	if (Math.abs(base.value) < 10) return `${sign}${delta.toFixed(1)}`;
	return `${sign}${((delta / base.value) * 100).toFixed(1)}%`;
}
