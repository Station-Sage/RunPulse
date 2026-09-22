import { getThreads } from '$lib/api/coach';
import { ApiError } from '$lib/api/client';
import type { ThreadsListResponse } from '$lib/types';

export interface CoachPageData {
	result: ThreadsListResponse | null;
	errorMessage: string | null;
}

export async function load(): Promise<CoachPageData> {
	try {
		const result = await getThreads();
		return { result, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '대화 목록을 불러올 수 없습니다.';
		return { result: null, errorMessage: message };
	}
}
