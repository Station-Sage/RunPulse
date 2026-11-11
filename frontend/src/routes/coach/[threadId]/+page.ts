import { getThread, getEngine } from '$lib/api/coach';
import { parseThreadId } from '$lib/threadAge';
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
	// C-09: "12abc" 같은 값은 parseInt 로 12가 되던 것 — 숫자만으로 된 경로만 받는다
	const id = parseThreadId(params.threadId);
	if (id == null) {
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
