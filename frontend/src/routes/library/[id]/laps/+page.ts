import { getActivity } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivityLap } from '$lib/types';

export interface LapsPageData {
	activityId: number;
	laps: ActivityLap[];
	errorMessage: string | null;
}

export async function load({ params }: { params: { id: string } }): Promise<LapsPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, laps: [], errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const res = await getActivity(id);
		return { activityId: id, laps: res.activity.laps ?? [], errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '랩 데이터를 불러올 수 없습니다.';
		return { activityId: id, laps: [], errorMessage: message };
	}
}
