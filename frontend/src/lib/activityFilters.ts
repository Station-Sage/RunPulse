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
/** 종목 칩 키 — 5개 family + 그 밖의 종목 묶음 'other'(서버 SPORT_GROUPS 와 같음, A-14). */
export const SPORT_KEYS = ['running', 'cycling', 'swimming', 'walking', 'strength', 'other'];
/** 유형 칩 키(서버 TYPE_CLASSES 와 같음). */
export const TYPE_KEYS = ['race', 'interval', 'tempo', 'long', 'easy', 'recovery'];

const DAY = 86_400_000;
const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const isDate = (s: string | null): s is string => !!s && /^\d{4}-\d{2}-\d{2}$/.test(s);
const isMonth = (s: string | null): s is string => !!s && /^\d{4}-(0[1-9]|1[0-2])$/.test(s);
const isDist = (s: string | null): s is string => !!s && /^\d+(\.\d+)?$/.test(s) && Number(s) > 0;
const pick = (v: string | null, allowed: string[]) => (v && allowed.includes(v) ? v : '');

/** 칩 줄 키 이름 → 사용자에게 보일 이름. */
const PARAM_LABELS: Record<string, string> = {
	month: '월', period: '기간', from: '시작일', to: '종료일', sport: '종목', type: '유형',
	dist_min: '거리', sort: '정렬', page: '페이지', at: '위치'
};

/**
 * 주소의 필터 값 중 쓸 수 없어 빼고 보여 주는 것(E-27·A-19). 순서는 PARAM_LABELS 순.
 * page 는 목록이 아래로 내리며 더 불러오는 방식이라 값과 무관하게 쓰지 않는다.
 */
export function invalidListParams(params: URLSearchParams): string[] {
	const bad = (k: string, ok: (v: string) => boolean) => params.has(k) && !ok(params.get(k) ?? '');
	const checks: Record<string, (v: string) => boolean> = {
		month: (v) => v === '' || isMonth(v),
		period: (v) => ['', 'all', '30d', 'month', 'year'].includes(v),
		from: (v) => v === '' || isValidDate(v),
		to: (v) => v === '' || isValidDate(v),
		sport: (v) => v === '' || SPORT_KEYS.includes(v),
		type: (v) => v === '' || TYPE_KEYS.includes(v),
		dist_min: (v) => v === '' || isDist(v),
		sort: (v) => v === '' || SORTS.includes(v),
		page: () => false,
		at: (v) => v === '' || isMonth(v)
	};
	return Object.keys(PARAM_LABELS).filter((k) => bad(k, checks[k]));
}

/** 빼고 보여 준 조건 안내 한 줄('' 이면 표시 안 함). 문구는 TXT-1 확정. */
export function invalidParamsNotice(keys: string[]): string {
	if (keys.length === 0) return '';
	return `주소의 ${keys.map((k) => PARAM_LABELS[k] ?? k).join('·')} 값을 쓸 수 없어 빼고 보여 드려요.`;
}

/** 실제 달력에 있는 YYYY-MM-DD 인지(2026-02-30 거부). */
function isValidDate(s: string): boolean {
	if (!isDate(s)) return false;
	const d = new Date(`${s}T00:00:00Z`);
	return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

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
		if (f && isValidDate(f)) from = f;
		if (t && isValidDate(t)) to = t;
		if (!from && !to) preset = 'all';
	}
	return {
		preset,
		month: isMonth(month) ? month : '',
		from,
		to,
		sport: pick(params.get('sport'), SPORT_KEYS),
		type: pick(params.get('type'), TYPE_KEYS),
		sort: pick(params.get('sort'), SORTS),
		distMin: isDist(params.get('dist_min')) ? (params.get('dist_min') as string) : '',
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

/** 접힌 칩 줄(종목·유형·거리) 중 기본값이 아닌 것의 수 — 접힘 버튼에 표시(A-16). */
export function appliedCount(s: Pick<ActivityFilterState, 'sport' | 'type' | 'distMin'>): number {
	return [s.sport, s.type, s.distMin].filter(Boolean).length;
}
