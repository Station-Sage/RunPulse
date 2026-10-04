import { error, redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { getWellnessDetail, getWellnessTrend } from '$lib/api/wellness';
import { isValidDate } from '$lib/wellnessDay';
import type { WellnessDetailData, WellnessTrendData } from '$lib/types';

export interface WellnessDayPageData {
	date: string;
	detail: WellnessDetailData;
	trend: Promise<WellnessTrendData | null>;
}

export async function load({ params }: { params: { date: string } }): Promise<WellnessDayPageData> {
	if (!isValidDate(params.date)) error(400, '날짜 형식이 올바르지 않아요');
	const detail = await getWellnessDetail(params.date);
	if (detail.date !== params.date) redirect(307, `${base}/library/wellness/${detail.date}`);
	const trend = getWellnessTrend(30, detail.date).catch(() => null);
	return { date: params.date, detail, trend };
}
