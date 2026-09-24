import { getActivity } from '$lib/api/library';
import { ApiError } from '$lib/api/client';
import type { ActivityMetric } from '$lib/types';
export interface MetricsTabPageData {
	activityId: number;
	metricsByCategory: Record<string, ActivityMetric[]>;
	errorMessage: string | null;
}
export async function load({ params }: { params: { id: string } }): Promise<MetricsTabPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, metricsByCategory: {}, errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const res = await getActivity(id);
		return { activityId: id, metricsByCategory: res.activity.metrics_by_category ?? {}, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '메트릭 데이터를 불러올 수 없습니다.';
		return { activityId: id, metricsByCategory: {}, errorMessage: message };
	}
}
