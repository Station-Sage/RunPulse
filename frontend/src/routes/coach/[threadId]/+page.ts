import { getThread } from '$lib/api/coach';
import { ApiError } from '$lib/api/client';
import type { ThreadDetailResponse } from '$lib/types';

export interface ThreadPageData {
	detail: ThreadDetailResponse | null;
	errorMessage: string | null;
}

export async function load({
	params
}: {
	params: { threadId: string };
}): Promise<ThreadPageData> {
	const id = parseInt(params.threadId, 10);
	if (isNaN(id)) {
		return { detail: null, errorMessage: '잘못된 스레드 ID입니다.' };
	}
	try {
		const detail = await getThread(id);
		return { detail, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '대화를 불러올 수 없습니다.';
		return { detail: null, errorMessage: message };
	}
}
