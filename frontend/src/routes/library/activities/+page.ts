import { getActivities } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivitiesListResponse } from '$lib/types';

export interface ActivitiesPageData {
	result: ActivitiesListResponse | null;
	errorMessage: string | null;
	from: string | undefined;
	to: string | undefined;
}

export async function load({ url }: { url: URL }): Promise<ActivitiesPageData> {
	const from = url.searchParams.get('from') ?? undefined;
	const to = url.searchParams.get('to') ?? undefined;
	try {
		const result = await getActivities({ per_page: 20, from, to: to ? `${to} 23:59:59` : undefined });
		return { result, errorMessage: null, from, to };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '활동 목록을 불러올 수 없습니다.';
		return { result: null, errorMessage: message, from, to };
	}
}
