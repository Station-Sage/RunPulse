import { getActivityStreams } from '$lib/api/streams';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import type { ActivityStreamPoint, StreamTimeBasis } from '$lib/types';
import type { ActivityLayoutData } from '../+layout';

export interface StreamsPageData {
	activityId: number;
	streams: ActivityStreamPoint[];
	/** 활동 총 시간(초). streamSeconds 보정에 사용. null이면 보정 불가. */
	totalSec: number | null;
	/** 서버가 확정한 시간축 출처. unknown이면 화면 휴리스틱으로 보정한다. */
	timeBasis: StreamTimeBasis;
	errorMessage: string | null;
	failure: Failure | null;
}

// duration_sec 하나 때문에 활동 상세(650KB)를 또 fetch하던 걸 없애고 +layout.ts 결과를 재사용한다(P-4).
// 이 탭 고유의 스트림 데이터(630KB)는 별도 엔드포인트라 그대로 유지.
export async function load({
	params,
	parent,
	depends
}: {
	params: { id: string };
	depends: (k: string) => void;
	parent: () => Promise<ActivityLayoutData>;
}): Promise<StreamsPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, streams: [], totalSec: null, timeBasis: 'unknown', errorMessage: '잘못된 활동 ID입니다.', failure: null };
	}
	depends(`app:activity-streams:${params.id}`);
	const parentData = parent();
	try {
		const { streams, time_basis } = await getActivityStreams(id);
		const { activity } = await parentData;
		const totalSec = activity?.core?.duration_sec ?? null;
		return { activityId: id, streams, totalSec, timeBasis: time_basis ?? 'unknown', errorMessage: null, failure: null };
	} catch (e) {
		const failure = classifyFailure(e);
		return { activityId: id, streams: [], totalSec: null, timeBasis: 'unknown', errorMessage: failure.detail, failure };
	}
}
