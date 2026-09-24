// frontend/src/lib/archive.ts
// 러닝 아카이브 순수 함수 — 히트맵 격자 배치·거리 단계·월별 막대 정규화. 테스트: frontend/tests/archive.test.mjs

export interface HeatCell {
	date: string;
	km: number;
	level: 0 | 1 | 2 | 3 | 4;
	col: number;
	row: number;
}

/** 하루 러닝 거리(km) → 색 단계. 0=없음, ≤5, ≤10, ≤18, 그 위. */
export function heatLevel(km: number): 0 | 1 | 2 | 3 | 4 {
	if (km <= 0) return 0;
	if (km <= 5) return 1;
	if (km <= 10) return 2;
	if (km <= 18) return 3;
	return 4;
}

const DAY = 86_400_000;
const utc = (d: string) => Date.parse(`${d}T00:00:00Z`);
// 월요일=0 … 일요일=6
const weekday = (ms: number) => (new Date(ms).getUTCDay() + 6) % 7;

/**
 * endDate가 마지막 열에 오는 weeks주 히트맵 격자. 열=주(월요일 시작), 행=요일(월=0).
 * 시작 주 월요일부터 endDate까지 모든 날짜 셀을 만들고(미래 날짜 없음), 없는 날은 km 0.
 * months: 주의 월요일이 속한 달이 바뀌는 열에 '9월' 형태 라벨.
 */
export function buildHeatmap(
	data: { date: string; km: number }[],
	endDate: string,
	weeks = 53
): { cells: HeatCell[]; months: { col: number; label: string }[]; columns: number } {
	const end = utc(endDate);
	const endMonday = end - weekday(end) * DAY;
	const start = endMonday - (weeks - 1) * 7 * DAY;
	const byDate = new Map(data.map((d) => [d.date, d.km]));
	const cells: HeatCell[] = [];
	for (let t = start; t <= end; t += DAY) {
		const date = new Date(t).toISOString().slice(0, 10);
		const km = byDate.get(date) ?? 0;
		cells.push({ date, km, level: heatLevel(km), col: Math.floor((t - start) / (7 * DAY)), row: weekday(t) });
	}
	const months: { col: number; label: string }[] = [];
	let prev = -1;
	for (let c = 0; c < weeks; c++) {
		const m = new Date(start + c * 7 * DAY).getUTCMonth();
		if (m !== prev) {
			months.push({ col: c, label: `${m + 1}월` });
			prev = m;
		}
	}
	return { cells, months, columns: weeks };
}

/** 월별 km를 0~1 높이 비율로(최댓값=1). 전부 0이면 전부 0. */
export function monthHeights(monthly: { km: number }[]): number[] {
	const max = Math.max(0, ...monthly.map((m) => m.km));
	return monthly.map((m) => (max > 0 ? m.km / max : 0));
}
