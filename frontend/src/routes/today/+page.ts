import { getToday } from '$lib/api/today';
import { ApiError } from '$lib/api/client';
import type { TodayResponse } from '$lib/types';

export interface TodayPageData {
	today: TodayResponse | null;
	errorMessage: string | null;
}

export async function load(): Promise<TodayPageData> {
	try {
		const today = await getToday();
		return { today, errorMessage: null };
	} catch (e) {
		// running.db 없음(NOT_FOUND/503) 등 — 1-E "데이터 없음" 상태로 처리(03a-today.md).
		const message = e instanceof ApiError ? e.message : '오늘 데이터를 불러올 수 없습니다.';
		return { today: null, errorMessage: message };
	}
}
