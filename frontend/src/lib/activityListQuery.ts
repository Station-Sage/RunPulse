// frontend/src/lib/activityListQuery.ts
// 활동 목록 질의·스크럽 순수 함수. 테스트: frontend/tests/activityListQuery.test.mjs
import type { ActivityFilterState } from './activityFilters';
import type { ActivitiesFilters } from './api/library';
import type { ActivityWeekSummary } from './types';

export const PER_PAGE = 40;
/** 서버 per_page 상한(routes_library.MAX_PER_PAGE, A-17). */
export const MAX_PER_PAGE = 200;

/**
 * 처음부터 need 건을 받기 위한 요청 목록. need 가 상한 이하면 한 번, 넘으면 상한 크기로 나눠 받는다.
 * 상한(200)이 PER_PAGE(40)의 배수라 이어서 '더 불러오기'의 page 계산이 어긋나지 않는다.
 */
export function pagePlan(need: number, max = MAX_PER_PAGE): { page: number; per_page: number }[] {
	if (need <= 0) return [];
	if (need <= max) return [{ page: 1, per_page: need }];
	return Array.from({ length: Math.ceil(need / max) }, (_, i) => ({ page: i + 1, per_page: max }));
}

/** 필터 상태 → API 파라미터. 월 모드는 month 로, 아니면 from/to 로 보낸다(to 는 하루 끝까지). */
export function toApiFilters(s: ActivityFilterState, extra: Partial<ActivitiesFilters> = {}): ActivitiesFilters {
	return {
		sport_group: s.sport || undefined,
		type: s.type || undefined,
		sort: s.sort && s.sort !== 'date' ? s.sort : undefined,
		q: s.q || undefined,
		dist_min: s.distMin ? Number(s.distMin) : undefined,
		month: s.month || undefined,
		from: s.month ? undefined : s.from,
		to: s.month || !s.to ? undefined : `${s.to} 23:59:59`,
		...extra
	};
}

/** 대상 월(YYYY-MM)까지 보이게 하려면 처음부터 몇 건을 불러와야 하는지(per 단위 올림). months 는 최신순 건수. */
export function jumpLoadCount(months: { month: string; n: number }[], target: string, per = PER_PAGE): number {
	let before = 0;
	let hit = false;
	for (const m of months) {
		if (m.month <= target) {
			hit = true;
			if (m.month === target) {
				before += m.n;
				break;
			}
			break;
		}
		before += m.n;
	}
	if (!hit) return 0;
	return Math.max(per, Math.ceil(before / per) * per);
}

/** 대상 월 이하의 첫 월(정확히 없으면 그 이전 달 중 가장 가까운 것). */
export function nearestMonth(months: { month: string }[], target: string): string | null {
	return months.find((m) => m.month <= target)?.month ?? null;
}

export interface WeekHeader {
	key: string;
	n: number;
	km: number;
	sec: number;
	inRangeOnly: boolean;
}

/** summary.weeks → key(월요일) 조회 맵. */
export function weekMap(weeks: ActivityWeekSummary[] | undefined): Map<string, WeekHeader> {
	return new Map((weeks ?? []).map((w) => [w.start, { key: w.start, n: w.n, km: w.km, sec: w.sec, inRangeOnly: w.in_range_only }]));
}

/** 월 이동: 'YYYY-MM' ± delta. */
export function shiftMonth(month: string, delta: number): string {
	const t = Number(month.slice(0, 4)) * 12 + (Number(month.slice(5)) - 1) + delta;
	return `${Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, '0')}`;
}

/** pagePlan 대로 차례로 받아 합친다. 중간에 has_more=false 면 멈춘다. fetchPage 는 getActivities 와 같은 모양. */
export async function fetchFirst<T extends { activities: unknown[]; total: number; has_more: boolean }>(
	need: number,
	fetchPage: (p: { page: number; per_page: number }) => Promise<T>
): Promise<T> {
	const plan = pagePlan(Math.max(1, need));
	let last: T | null = null;
	const all: unknown[] = [];
	for (const p of plan) {
		last = await fetchPage(p);
		all.push(...last.activities);
		if (!last.has_more) break;
	}
	return { ...(last as T), activities: all };
}
