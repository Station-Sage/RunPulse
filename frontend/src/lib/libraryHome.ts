// Library 홈 순수 함수 — 검색/빠른 칩 링크, 히트맵 셀 라벨·이동, 월별 진행중 판정. 테스트: tests/libraryHome.test.mjs

export const QUICK_CHIPS: ReadonlyArray<{ label: string; query: string }> = [
	{ label: '대회', query: 'type=race' },
	{ label: '인터벌', query: 'type=interval' },
	{ label: '템포', query: 'type=tempo' },
	{ label: '롱런', query: 'type=long' },
	{ label: '이번 달', query: 'period=month' }
];

/** 검색어 → 활동 목록 쿼리. 빈 검색어는 null(이동 안 함). */
export function finderQuery(q: string): string | null {
	const t = q.trim();
	return t ? `q=${encodeURIComponent(t)}` : null;
}

const DOW = ['일', '월', '화', '수', '목', '금', '토'];

/** '2026-09-20' → '9/20(일)'. */
export function shortDate(date: string): string {
	const d = new Date(`${date}T00:00:00Z`);
	return `${d.getUTCMonth() + 1}/${d.getUTCDate()}(${DOW[d.getUTCDay()]})`;
}

/** 히트맵 셀 팝오버 문구. */
export function heatCellLabel(date: string, km: number): string {
	return `${shortDate(date)} · ${km > 0 ? `${Math.round(km * 10) / 10}km` : '쉰 날'}`;
}

/** 키 → 격자 이동. 열=주, 행=요일(0~6). 범위 밖이면 제자리. */
export function moveHeatCell(
	cells: { col: number; row: number }[],
	idx: number,
	key: string
): number {
	const cur = cells[idx];
	if (!cur) return idx;
	const d: Record<string, [number, number]> = {
		ArrowLeft: [-1, 0],
		ArrowRight: [1, 0],
		ArrowUp: [0, -1],
		ArrowDown: [0, 1]
	};
	const m = d[key];
	if (!m) return idx;
	const next = cells.findIndex((c) => c.col === cur.col + m[0] && c.row === cur.row + m[1]);
	return next < 0 ? idx : next;
}

/** 월별 막대 중 진행 중(기준일이 속한 달)인지. */
export function isMonthInProgress(month: string, asOf: string): boolean {
	return asOf.slice(0, 7) === month;
}
