import { getActivity } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivityDetail } from '$lib/types';

export interface ActivityPageData {
	activity: ActivityDetail | null;
	errorMessage: string | null;
}

export async function load({ params }: { params: { id: string } }): Promise<ActivityPageData> {
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
