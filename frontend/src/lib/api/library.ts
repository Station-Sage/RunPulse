import { apiFetch } from './client';
import type {
	ArchiveData,
	ActivitiesListResponse,
	ActivityFacets,
	ActivityListSummary,
	ActivityDetailResponse
} from '$lib/types';

export interface ActivitiesFilters {
	sport?: string;
	from?: string;
	to?: string;
	search?: string;
	dist_min?: number; // km
	sport_group?: string;
	type?: string;
	month?: string; // YYYY-MM
	sort?: string; // date|distance|pace|load
	q?: string;
	page?: number;
	per_page?: number;
}

function listParams(filters: ActivitiesFilters): URLSearchParams {
	const params = new URLSearchParams();
	const set = (k: string, v: string | number | undefined | null) => {
		if (v != null && v !== '') params.set(k, String(v));
	};
	set('sport', filters.sport);
	set('sport_group', filters.sport_group);
	set('type', filters.type);
	set('month', filters.month);
	set('sort', filters.sort);
	set('q', filters.q);
	set('from', filters.from);
	set('to', filters.to);
	set('search', filters.search);
	set('dist_min', filters.dist_min);
	set('page', filters.page);
	set('per_page', filters.per_page);
	return params;
}

const withQs = (path: string, params: URLSearchParams) => {
	const qs = params.toString();
	return `${path}${qs ? `?${qs}` : ''}`;
};

export function getActivities(filters: ActivitiesFilters = {}): Promise<ActivitiesListResponse> {
	return apiFetch<ActivitiesListResponse>(withQs('/library/activities', listParams(filters)));
}

/** 칩 건수(종목·유형·월). 페이지네이션 파라미터는 무시된다. */
export function getActivityFacets(filters: ActivitiesFilters = {}): Promise<ActivityFacets> {
	return apiFetch<ActivityFacets>(withQs('/library/activities/facets', listParams({ ...filters, page: undefined, per_page: undefined })));
}

export function getActivitySummary(filters: ActivitiesFilters = {}): Promise<ActivityListSummary> {
	return apiFetch<ActivityListSummary>(withQs('/library/activities/summary', listParams({ ...filters, page: undefined, per_page: undefined })));
}

export function getActivity(id: number): Promise<ActivityDetailResponse> {
	return apiFetch<ActivityDetailResponse>(`/library/activities/${id}`);
}

export function getArchive(): Promise<ArchiveData> {
	return apiFetch<ArchiveData>('/library/archive');
}
