// 03e-coach.md 5-G — 일일 세션 상세 페이지 로더.
import { getSessionDetail } from '$lib/api/plan';
import type { SessionDetail } from '$lib/types';

export interface SessionDetailPageData {
	session: SessionDetail | null;
	goalId: number;
	date: string;
	errorMessage: string | null;
}

export async function load({
	params
}: {
	params: { id: string; date: string };
}): Promise<SessionDetailPageData> {
	const goalId = parseInt(params.id, 10);
	if (isNaN(goalId)) {
		return { session: null, goalId: 0, date: params.date, errorMessage: '잘못된 플랜 ID입니다.' };
	}
	try {
		const session = await getSessionDetail(goalId, params.date);
		return { session, goalId, date: params.date, errorMessage: null };
	} catch {
		return {
			session: null,
			goalId,
			date: params.date,
			errorMessage: '세션을 찾을 수 없습니다.'
		};
	}
}
