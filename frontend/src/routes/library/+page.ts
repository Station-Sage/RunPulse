import { getActivities } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivitiesListResponse } from '$lib/types';

export interface LibraryPageData {
	result: ActivitiesListResponse | null;
	errorMessage: string | null;
}

export async function load(): Promise<LibraryPageData> {
	try {
		const result = await getActivities({ per_page: 20 });
		return { result, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '활동 목록을 불러올 수 없습니다.';
		return { result: null, errorMessage: message };
	}
}
