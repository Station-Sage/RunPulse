// 03e-coach.md 5-G — 일일 세션 상세 페이지 로더.
import { getSessionDetail, getTodaysAdjustment } from '$lib/api/plan';
import type { SessionDetail, TodaysAdjustment } from '$lib/types';

export interface SessionDetailPageData {
	session: SessionDetail | null;
	/** 오늘 세션일 때만 — 수락·되돌리기 대상(ADR-035). */
	todaysAdj: TodaysAdjustment | null;
	goalId: number;
	date: string;
	errorMessage: string | null;
}

function localToday(): string {
	const d = new Date();
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export async function load({
	params
}: {
	params: { id: string; date: string };
}): Promise<SessionDetailPageData> {
	const goalId = parseInt(params.id, 10);
	if (isNaN(goalId)) {
		return { session: null, todaysAdj: null, goalId: 0, date: params.date, errorMessage: '잘못된 플랜 ID입니다.' };
	}
	try {
		const isToday = params.date === localToday();
		const [session, todaysAdj] = await Promise.all([
			getSessionDetail(goalId, params.date),
			isToday ? (getTodaysAdjustment() as Promise<TodaysAdjustment>).catch(() => null) : Promise.resolve(null)
		]);
		return { session, todaysAdj, goalId, date: params.date, errorMessage: null };
	} catch {
		return {
			session: null,
			todaysAdj: null,
			goalId,
			date: params.date,
			errorMessage: '세션을 찾을 수 없습니다.'
		};
	}
}
