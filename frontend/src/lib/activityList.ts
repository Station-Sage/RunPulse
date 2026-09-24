// frontend/src/lib/activityList.ts
// 활동 목록 순수 함수 — 월요일 시작 주 그룹·주간 합계·날짜 라벨. 테스트: frontend/tests/activityList.test.mjs

export interface ListItem {
	start_time: string;
	distance_m: number | null;
	duration_sec: number | null;
	activity_type?: string;
}

export interface WeekGroup<T> {
	key: string; // 그 주 월요일 YYYY-MM-DD
	year: number;
	label: string; // '9/14 – 9/20'
	items: T[];
	km: number; // 러닝 활동만 합산
	seconds: number;
	runs: number;
}

const DAY = 86_400_000;
const utc = (d: string) => Date.parse(`${d.slice(0, 10)}T00:00:00Z`);
const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const weekday = (ms: number) => (new Date(ms).getUTCDay() + 6) % 7; // 월=0
const isRun = (a: ListItem) => (a.activity_type ?? 'running').includes('running');

export function mondayOf(date: string): string {
	const ms = utc(date);
	return iso(ms - weekday(ms) * DAY);
}

/** '9/14 – 9/20' — 월요일 날짜 문자열을 받아 그 주의 월~일 범위 라벨. */
export function weekLabel(monday: string): string {
	const a = new Date(utc(monday));
	const b = new Date(utc(monday) + 6 * DAY);
	return `${a.getUTCMonth() + 1}/${a.getUTCDate()} – ${b.getUTCMonth() + 1}/${b.getUTCDate()}`;
}

const KO_DAYS = ['일', '월', '화', '수', '목', '금', '토'];
/** '9/20 (일)' */
export function dayLabel(date: string): string {
	const d = new Date(utc(date));
	return `${d.getUTCMonth() + 1}/${d.getUTCDate()} (${KO_DAYS[d.getUTCDay()]})`;
}

/** 입력 순서를 유지하며 같은 주가 연속된 항목을 그룹으로 묶는다. 주간 km·시간·횟수는 러닝 활동만 합산. */
export function weekGroups<T extends ListItem>(items: T[]): WeekGroup<T>[] {
	const groups: WeekGroup<T>[] = [];
	for (const it of items) {
		const key = mondayOf(it.start_time);
		let g = groups[groups.length - 1];
		if (!g || g.key !== key) {
			g = { key, year: Number(key.slice(0, 4)), label: weekLabel(key), items: [], km: 0, seconds: 0, runs: 0 };
			groups.push(g);
		}
		g.items.push(it);
		if (isRun(it)) {
			g.km += (it.distance_m ?? 0) / 1000;
			g.seconds += it.duration_sec ?? 0;
			g.runs += 1;
		}
	}
	return groups;
}
