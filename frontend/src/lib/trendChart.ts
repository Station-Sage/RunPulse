// frontend/src/lib/trendChart.ts
// 추세 차트 순수 함수 — 공통 y 범위·변화 라벨 계산. 테스트: frontend/tests/trendChart.test.mjs

export interface ChartSeries {
	values: (number | null)[];
	color: string;
	label?: string;
}

/**
 * 여러 계열의 공통 y 범위를 계산한다.
 * null은 무시, 전부 null이면 { min: 0, max: 1 } 반환.
 * min === max 이면 ±1 패딩을 추가한다.
 */
export function sharedYRange(series: ChartSeries[]): { min: number; max: number } {
	const nums: number[] = [];
	for (const s of series) {
		for (const v of s.values) {
			if (v != null) nums.push(v);
		}
	}
	if (nums.length === 0) return { min: 0, max: 1 };
	const min = Math.min(...nums);
	const max = Math.max(...nums);
	if (min === max) return { min: min - 1, max: max + 1 };
	return { min, max };
}

/**
 * "N일 변화" 라벨을 반환한다.
 * 기준값(prev)의 절댓값이 10 미만이면 절대 변화(±X.X), 그 이상이면 퍼센트(±X.X%).
 * prev 또는 current가 null이면 '—'.
 * prev === 0 인 경우 절대 변화로 표기한다 (0으로 나누기 방지).
 */
export function changeLabel(current: number | null, prev: number | null): string {
	if (current == null || prev == null) return '—';
	const delta = current - prev;
	const sign = delta >= 0 ? '+' : '';
	if (prev === 0 || Math.abs(prev) < 10) {
		return `${sign}${delta.toFixed(1)}`;
	}
	const pct = (delta / Math.abs(prev)) * 100;
	return `${sign}${pct.toFixed(1)}%`;
}
