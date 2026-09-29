import { getActivity } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivityDetail } from '$lib/types';

export interface ActivityLayoutData {
	activity: ActivityDetail | null;
	errorMessage: string | null;
}

/**
 * 활동 상세(650KB, streams 포함)를 서브탭(요약/랩/메트릭/스트림)당 1회만 가져와 공유한다.
 * 이전엔 각 +page.ts가 개별적으로 getActivity를 호출해 서브탭 전환마다 전량 재요청됐다(02-performance.md P-4).
 */
export async function load({ params }: { params: { id: string } }): Promise<ActivityLayoutData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activity: null, errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const res = await getActivity(id);
		return { activity: res.activity, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '활동 데이터를 불러올 수 없습니다.';
		return { activity: null, errorMessage: message };
	}
}
