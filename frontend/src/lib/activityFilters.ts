// frontend/src/lib/activityFilters.ts
// 활동 목록 필터 상태 ↔ URL 쿼리 순수 함수. 테스트: frontend/tests/activityFilters.test.mjs

export type PeriodPreset = 'all' | '30d' | 'month' | 'year';

export interface ActivityFilterState {
	preset: PeriodPreset | null; // from/to 직접 지정이면 null
	month: string; // YYYY-MM, 없으면 ''
	from: string | undefined; // YYYY-MM-DD
	to: string | undefined;
	sport: string; // sport_group (running 등)
	type: string; // race|interval|tempo|long|easy|recovery
	sort: string; // date(기본)|distance|pace|load
	distMin: string;
	q: string;
}

export const PRESETS: ReadonlyArray<readonly [PeriodPreset, string]> = [
	['all', '전체'],
	['30d', '최근 30일'],
	['month', '이번 달'],
	['year', '올해']
];

export const SORTS = ['date', 'distance', 'pace', 'load'];

const DAY = 86_400_000;
const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const isDate = (s: string | null): s is string => !!s && /^\d{4}-\d{2}-\d{2}$/.test(s);
const isMonth = (s: string | null): s is string => !!s && /^\d{4}-(0[1-9]|1[0-2])$/.test(s);

export function monthRange(month: string): { from: string; to: string } {
	const [y, m] = month.split('-').map(Number);
	return { from: `${month}-01`, to: iso(Date.UTC(y, m, 1) - DAY) };
}

/** 프리셋 → 기간. `today`는 YYYY-MM-DD(로컬 기준). 'all'은 기간 없음. */
export function presetRange(preset: PeriodPreset, today: string): { from?: string; to?: string } {
	if (preset === 'all') return {};
	if (preset === '30d') return { from: iso(Date.parse(`${today}T00:00:00Z`) - 29 * DAY), to: today };
	if (preset === 'month') return { from: `${today.slice(0, 7)}-01`, to: today };
	return { from: `${today.slice(0, 4)}-01-01`, to: today };
}

/** 최근 n개월(이번 달부터 과거 순) YYYY-MM. */
export function recentMonths(today: string, n: number): string[] {
	let y = Number(today.slice(0, 4));
	let m = Number(today.slice(5, 7));
	const out: string[] = [];
	for (let i = 0; i < n; i++) {
		out.push(`${y}-${String(m).padStart(2, '0')}`);
		if (--m === 0) {
			m = 12;
			y--;
		}
	}
	return out;
}

export function parseFilters(params: URLSearchParams, today: string): ActivityFilterState {
	const month = params.get('month');
	const pr = params.get('period');
	let from: string | undefined;
	let to: string | undefined;
	let preset: PeriodPreset | null = null;
	if (isMonth(month)) {
		({ from, to } = monthRange(month));
	} else if (pr === '30d' || pr === 'month' || pr === 'year') {
		preset = pr;
		({ from, to } = presetRange(pr, today));
	} else {
		const f = params.get('from');
		const t = params.get('to');
		if (isDate(f)) from = f;
		if (isDate(t)) to = t;
		if (!from && !to) preset = 'all';
	}
	return {
		preset,
		month: isMonth(month) ? month : '',
		from,
		to,
		sport: params.get('sport') ?? '',
		type: params.get('type') ?? '',
		sort: SORTS.includes(params.get('sort') ?? '') ? (params.get('sort') as string) : '',
		distMin: params.get('dist_min') ?? '',
		q: params.get('q') ?? ''
	};
}

/** 기본값은 생략한 쿼리 문자열('?a=b' 또는 ''). month/period가 있으면 from/to는 쓰지 않는다. */
export function serializeFilters(s: ActivityFilterState): string {
	const p = new URLSearchParams();
	if (s.month) p.set('month', s.month);
	else if (s.preset && s.preset !== 'all') p.set('period', s.preset);
	else if (s.preset === null) {
		if (s.from) p.set('from', s.from);
		if (s.to) p.set('to', s.to);
	}
	if (s.sport) p.set('sport', s.sport);
	if (s.type) p.set('type', s.type);
	if (s.sort && s.sort !== 'date') p.set('sort', s.sort);
	if (s.distMin) p.set('dist_min', s.distMin);
	if (s.q) p.set('q', s.q);
	const qs = p.toString();
	return qs ? `?${qs}` : '';
}
