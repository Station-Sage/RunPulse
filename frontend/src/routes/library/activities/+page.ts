import { getActivities, getActivityFacets, getActivitySummary } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import { parseFilters, type ActivityFilterState } from '$lib/activityFilters';
import { toApiFilters, PER_PAGE } from '$lib/activityListQuery';
import type { ActivitiesListResponse, ActivityFacets, ActivityListSummary } from '$lib/types';

export interface ActivitiesPageData {
	result: ActivitiesListResponse | null;
	facets: ActivityFacets | null;
	summary: ActivityListSummary | null;
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
	const api = toApiFilters(filters);
	const soft = <T>(p: Promise<T>) => p.catch(() => null);
	try {
		const [result, facets, summary] = await Promise.all([
			getActivities({ ...api, page: 1, per_page: PER_PAGE }),
			soft(getActivityFacets(api)),
			soft(getActivitySummary(api))
		]);
		return { result, facets, summary, errorMessage: null, filters, today };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '활동 목록을 불러올 수 없습니다.';
		return { result: null, facets: null, summary: null, errorMessage: message, filters, today };
	}
}
