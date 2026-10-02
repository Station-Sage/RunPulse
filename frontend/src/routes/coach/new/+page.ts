// 활동 컨텍스트 새 대화 — `?activity={id}`의 근거 카드·추천 질문과 엔진 상태를 로드한다.
import { getActivityContext, getEngine } from '$lib/api/coach';
import type { CoachActivityContext, CoachEngine } from '$lib/types';

export interface CoachNewPageData {
	activityId: number | null;
	activity: CoachActivityContext | null;
	engine: CoachEngine | null;
}

export async function load({ url }: { url: URL }): Promise<CoachNewPageData> {
	const raw = url.searchParams.get('activity');
	const activityId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
	const [activity, engine] = await Promise.all([
		activityId != null ? getActivityContext(activityId).catch(() => null) : Promise.resolve(null),
		getEngine().catch(() => null)
	]);
	return { activityId, activity, engine };
}
