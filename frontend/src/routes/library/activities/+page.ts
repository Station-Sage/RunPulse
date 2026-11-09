import { getActivities, getActivityFacets, getActivitySummary } from '$lib/api/library';
import { getSyncState } from '$lib/api/data';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import { invalidListParams, parseFilters, type ActivityFilterState } from '$lib/activityFilters';
import { toApiFilters, PER_PAGE } from '$lib/activityListQuery';
import type { ActivitiesListResponse, ActivityFacets, ActivityListSummary } from '$lib/types';

export interface ActivitiesPageData {
	result: ActivitiesListResponse | null;
	facets: ActivityFacets | null;
	summary: ActivityListSummary | null;
	errorMessage: string | null;
	failure: Failure | null;
	filters: ActivityFilterState;
	today: string;
	firstSyncRunning: boolean;
	/** 주소에서 쓸 수 없어 뺀 조건 키(E-27·A-19) */
	invalidParams: string[];
}

const localToday = () => {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export async function load({ url }: { url: URL }): Promise<ActivitiesPageData> {
	const today = localToday();
	const filters = parseFilters(url.searchParams, today);
	const api = toApiFilters(filters);
	const invalidParams = invalidListParams(url.searchParams);
	const soft = <T>(p: Promise<T>) => p.catch(() => null);
	const syncing = getSyncState().then((s) => s.first_sync_running).catch(() => false);
	try {
		const [result, facets, summary] = await Promise.all([
			getActivities({ ...api, page: 1, per_page: PER_PAGE }),
			soft(getActivityFacets(api)),
			soft(getActivitySummary(api))
		]);
		return { result, facets, summary, errorMessage: null, failure: null, filters, today, firstSyncRunning: await syncing, invalidParams };
	} catch (e) {
		const failure = classifyFailure(e);
		return { result: null, facets: null, summary: null, errorMessage: failure.detail, failure, filters, today, firstSyncRunning: await syncing, invalidParams };
	}
}
