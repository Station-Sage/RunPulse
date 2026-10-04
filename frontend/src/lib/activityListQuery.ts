// frontend/src/lib/activityListQuery.ts
// 활동 목록 질의·스크럽 순수 함수. 테스트: frontend/tests/activityListQuery.test.mjs
import type { ActivityFilterState } from './activityFilters';
import type { ActivitiesFilters } from './api/library';
import type { ActivityWeekSummary } from './types';

export const PER_PAGE = 40;

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
