// frontend/src/lib/chartScale.ts
// 차트 이상치 클램프 유틸. 순수 함수만 포함 — 테스트: frontend/tests/chartScale.test.mjs

/**
 * 숫자 배열에서 p번째 백분위수를 반환한다 (p: 0~100).
 * 선형 보간 없이 가장 가까운 실제 값을 반환한다(nearest-rank).
 */
export function percentile(values: number[], p: number): number {
	if (values.length === 0) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const idx = Math.min(Math.floor((p / 100) * sorted.length), sorted.length - 1);
	return sorted[idx];
}

/**
 * null을 제외한 값을 lo~hi 백분위 범위로 클램프한다.
 * 반환값:
 *   values — 클램프된 배열(null은 그대로)
 *   clamped — true이면 최소 1개 값이 범위 밖이어서 실제로 클램프됐음
 */
export function clampToPercentile(
	values: (number | null)[],
	lo: number,
	hi: number
): { values: (number | null)[]; clamped: boolean } {
	const nums = values.filter((v): v is number => v != null);
	if (nums.length === 0) return { values, clamped: false };
	const lower = percentile(nums, lo);
	const upper = percentile(nums, hi);
	let clamped = false;
	const result = values.map((v) => {
		if (v == null) return null;
		if (v < lower) {
			clamped = true;
			return lower;
		}
		if (v > upper) {
			clamped = true;
			return upper;
		}
		return v;
	});
	return { values: result, clamped };
}

/**
 * 상·하위 2% 백분위로 이상치를 클램프한다.
 * GPS 스파이크 등 단발성 이상값이 차트 범위를 잡아먹는 것을 막는다.
 */
export function clampOutliers(values: (number | null)[]): { values: (number | null)[]; clamped: boolean } {
	return clampToPercentile(values, 2, 98);
}
