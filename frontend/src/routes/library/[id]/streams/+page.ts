import { getActivityStreams } from '$lib/api/streams';
import { ApiError } from '$lib/api/client';
import type { ActivityStreamPoint } from '$lib/types';

export interface StreamsPageData {
	activityId: number;
	streams: ActivityStreamPoint[];
	errorMessage: string | null;
}

export async function load({ params }: { params: { id: string } }): Promise<StreamsPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, streams: [], errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const streams = await getActivityStreams(id);
		return { activityId: id, streams, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '스트림 데이터를 불러올 수 없습니다.';
		return { activityId: id, streams: [], errorMessage: message };
	}
}
