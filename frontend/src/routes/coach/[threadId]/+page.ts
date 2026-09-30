import { getThread, getEngine } from '$lib/api/coach';
import { ApiError } from '$lib/api/client';
import type { ThreadDetailResponse, CoachEngine } from '$lib/types';

export interface ThreadPageData {
	detail: ThreadDetailResponse | null;
	errorMessage: string | null;
	engine: CoachEngine | null;
}

export async function load({
	params
}: {
	params: { threadId: string };
}): Promise<ThreadPageData> {
	const id = parseInt(params.threadId, 10);
	if (isNaN(id)) {
		return { detail: null, errorMessage: '잘못된 스레드 ID입니다.', engine: null };
	}
	try {
		const [detail, engine] = await Promise.all([getThread(id), getEngine().catch(() => null)]);
		return { detail, errorMessage: null, engine };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '대화를 불러올 수 없습니다.';
		return { detail: null, errorMessage: message, engine: null };
	}
}
