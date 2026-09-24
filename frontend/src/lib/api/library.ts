import { apiFetch } from './client';
import type {
	ActivitiesListResponse,
	ActivityDetailResponse
} from '$lib/types';

export interface ActivitiesFilters {
	sport?: string;
	from?: string;
	to?: string;
	search?: string;
	dist_min?: number; // km
	page?: number;
	per_page?: number;
}

export function getActivities(filters: ActivitiesFilters = {}): Promise<ActivitiesListResponse> {
	const params = new URLSearchParams();
	if (filters.sport) params.set('sport', filters.sport);
	if (filters.from) params.set('from', filters.from);
	if (filters.to) params.set('to', filters.to);
	if (filters.search) params.set('search', filters.search);
	if (filters.dist_min != null) params.set('dist_min', String(filters.dist_min));
	if (filters.page != null) params.set('page', String(filters.page));
	if (filters.per_page != null) params.set('per_page', String(filters.per_page));
	const qs = params.toString();
	return apiFetch<ActivitiesListResponse>(`/library/activities${qs ? `?${qs}` : ''}`);
}

export function getActivity(id: number): Promise<ActivityDetailResponse> {
	return apiFetch<ActivityDetailResponse>(`/library/activities/${id}`);
}
