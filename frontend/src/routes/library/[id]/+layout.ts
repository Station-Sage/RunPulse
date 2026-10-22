import { getActivity } from '$lib/api/library';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import type { ActivityDetail } from '$lib/types';

export interface ActivityLayoutData {
	activity: ActivityDetail | null;
	errorMessage: string | null;
	failure: Failure | null;
}

/**
 * 활동 상세(상세 응답(series·splits 포함), streams 포함)를 서브탭(요약/랩/메트릭/스트림)당 1회만 가져와 공유한다.
 * 이전엔 각 +page.ts가 개별적으로 getActivity를 호출해 서브탭 전환마다 전량 재요청됐다(02-performance.md P-4).
 */
export async function load({ params, depends }: { params: { id: string }; depends: (k: string) => void }): Promise<ActivityLayoutData> {
	const id = parseInt(params.id, 10);
	depends(`app:activity:${params.id}`);
	if (isNaN(id)) {
		return { activity: null, errorMessage: '잘못된 활동 ID입니다.', failure: { kind: 'not_found', status: 404, code: 'BAD_ID', detail: 'bad id' } };
	}
	try {
		const res = await getActivity(id);
		return { activity: res.activity, errorMessage: null, failure: null };
	} catch (e) {
		const failure = classifyFailure(e);
		return { activity: null, errorMessage: failure.detail, failure };
	}
}
