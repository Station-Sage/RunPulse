import { getActivityStreams } from '$lib/api/streams';
import { getActivity } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivityStreamPoint } from '$lib/types';

export interface StreamsPageData {
	activityId: number;
	streams: ActivityStreamPoint[];
	/** 활동 총 시간(초). streamSeconds 보정에 사용. null이면 보정 불가. */
	totalSec: number | null;
	errorMessage: string | null;
}

export async function load({ params }: { params: { id: string } }): Promise<StreamsPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, streams: [], totalSec: null, errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const [streams, actDetail] = await Promise.all([
			getActivityStreams(id),
			getActivity(id).catch(() => null)
		]);
		const totalSec = actDetail?.activity?.core?.duration_sec ?? null;
		return { activityId: id, streams, totalSec, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '스트림 데이터를 불러올 수 없습니다.';
		return { activityId: id, streams: [], totalSec: null, errorMessage: message };
	}
}
