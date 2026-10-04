import { getActivities } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import { parseFilters, type ActivityFilterState } from '$lib/activityFilters';
import type { ActivitiesListResponse } from '$lib/types';

export interface ActivitiesPageData {
	result: ActivitiesListResponse | null;
	errorMessage: string | null;
	filters: ActivityFilterState;
	today: string;
}

const localToday = () => {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export async function load({ url }: { url: URL }): Promise<ActivitiesPageData> {
	const today = localToday();
	const filters = parseFilters(url.searchParams, today);
	try {
		const result = await getActivities({
			per_page: 20,
			sport: filters.sport || undefined,
			search: filters.q || undefined,
			dist_min: filters.distMin ? Number(filters.distMin) : undefined,
			from: filters.from,
			to: filters.to ? `${filters.to} 23:59:59` : undefined
		});
		return { result, errorMessage: null, filters, today };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '활동 목록을 불러올 수 없습니다.';
		return { result: null, errorMessage: message, filters, today };
	}
}
