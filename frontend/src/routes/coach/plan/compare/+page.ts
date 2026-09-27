// 03e-coach.md 5-E — 프로그램 비교: 쿼리 파라미터로 템플릿 재조회.
import { error } from '@sveltejs/kit';
import { getPlanTemplates } from '$lib/api/plan';
import type { PlanTemplate } from '$lib/types';

export interface ComparePlanData {
	templates: PlanTemplate[];
	distanceKm: number;
	raceDate: string | null;
	targetTimeSec: number | null;
}

export async function load({ url }: { url: URL }): Promise<ComparePlanData> {
	const distanceKm = Number(url.searchParams.get('distance_km'));
	if (!distanceKm) {
		throw error(400, '거리 정보가 없습니다.');
	}
	const raceDateParam = url.searchParams.get('race_date');
	const targetTimeParam = url.searchParams.get('target_time_sec');
	const targetTimeSec = targetTimeParam ? Number(targetTimeParam) : null;

	const templates = await getPlanTemplates(
		distanceKm,
		targetTimeSec ?? undefined,
		raceDateParam ?? undefined
	);

	return {
		templates,
		distanceKm,
		raceDate: raceDateParam || null,
		targetTimeSec
	};
}
