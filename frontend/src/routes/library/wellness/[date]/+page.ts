import { error, redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { getWellnessDetail, getWellnessTrend } from '$lib/api/wellness';
import { dateError, DATE_ERROR_TEXT } from '$lib/wellnessDay';
import type { WellnessDetailData, WellnessTrendData } from '$lib/types';

export interface WellnessDayPageData {
	date: string;
	detail: WellnessDetailData;
	trend: Promise<WellnessTrendData | null>;
	/** M-23: 미래 날짜를 요청해 오늘로 옮겨 왔을 때 원래 요청한 날짜. */
	movedFrom: string | null;
}

export async function load({ params, url }: { params: { date: string }; url: URL }): Promise<WellnessDayPageData> {
	const bad = dateError(params.date);
	if (bad) error(400, DATE_ERROR_TEXT[bad].title);
	const detail = await getWellnessDetail(params.date);
	// 서버는 미래 날짜를 오늘로 보정한다 — 조용히 바꾸지 않고 요청 날짜를 ?moved= 로 넘겨 안내한다.
	if (detail.date !== params.date) redirect(307, `${base}/library/wellness/${detail.date}?moved=${params.date}`);
	const moved = url.searchParams.get('moved');
	const trend = getWellnessTrend(30, detail.date).catch(() => null);
	return { date: params.date, detail, trend, movedFrom: moved && !dateError(moved) ? moved : null };
}
