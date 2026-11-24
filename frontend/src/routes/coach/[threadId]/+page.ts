import { getThread, getEngine } from '$lib/api/coach';
import { parseThreadId } from '$lib/threadAge';
import { classifyFailure, notFoundFailure, type Failure } from '$lib/loadFailure';
import type { ThreadDetailResponse, CoachEngine } from '$lib/types';

export interface ThreadPageData {
	detail: ThreadDetailResponse | null;
	failure: Failure | null;
	engine: CoachEngine | null;
	threadId: string;
}

export async function load({
	params,
	depends
}: {
	params: { threadId: string };
	depends: (key: string) => void;
}): Promise<ThreadPageData> {
	const threadId = params.threadId;
	depends(`app:coach-thread:${threadId}`);
	// C-09: "12abc" 같은 값은 parseInt 로 12가 되던 것 — 숫자만으로 된 경로만 받는다
	const id = parseThreadId(threadId);
	if (id == null) {
		return { detail: null, failure: notFoundFailure('BAD_ID'), engine: null, threadId };
	}
	try {
		const [detail, engine] = await Promise.all([getThread(id), getEngine().catch(() => null)]);
		return { detail, failure: null, engine, threadId };
	} catch (e) {
		return { detail: null, failure: classifyFailure(e), engine: null, threadId };
	}
}
