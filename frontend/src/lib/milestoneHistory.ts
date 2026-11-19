// 마일스톤 전체 이력 화면의 순수 로직 — 월별 묶음·필터 칩·날짜 표기 (ADR-057).
import { MILESTONE_LABEL } from './milestoneIcon.ts';

/** 한 번에 불러오는 건수(서버 상한 100). */
export const PAGE_SIZE = 50;

export interface MonthGroup<T> {
	ym: string;
	label: string;
	items: T[];
}

/** 최신순 목록을 'YYYY-MM' 단위로 묶는다(순서 유지). 날짜 = 사건일. */
export function groupByMonth<T extends { date: string }>(items: T[]): MonthGroup<T>[] {
	const out: MonthGroup<T>[] = [];
	for (const m of items) {
		const ym = m.date.slice(0, 7);
		let g = out[out.length - 1];
		if (!g || g.ym !== ym) {
			g = { ym, label: `${Number(ym.slice(0, 4))}년 ${Number(ym.slice(5, 7))}월`, items: [] };
			out.push(g);
		}
		g.items.push(m);
	}
	return out;
}

/** 'YYYY-MM-DD' → '11월 19일'. */
export function dayLabel(date: string): string {
	return `${Number(date.slice(5, 7))}월 ${Number(date.slice(8, 10))}일`;
}

/** 필터 칩 — 기록이 있는 종류만, MILESTONE_LABEL 순서(모르는 종류는 뒤로). */
export function filterChips(counts: { type: string; count: number }[]): { value: string; label: string }[] {
	const order = Object.keys(MILESTONE_LABEL);
	const rank = (t: string) => (order.indexOf(t) < 0 ? order.length : order.indexOf(t));
	return counts
		.filter((c) => c.count > 0)
		.sort((a, b) => rank(a.type) - rank(b.type))
		.map((c) => ({ value: c.type, label: `${(MILESTONE_LABEL as Record<string, string>)[c.type] ?? '기록'} ${c.count}` }));
}

/** ?type= 값 정규화 — 소문자·밑줄만 허용, 그 외는 전체(null). */
export function parseTypeParam(raw: string | null): string | null {
	return raw && /^[a-z_]{1,32}$/.test(raw) ? raw : null;
}
