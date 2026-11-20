// 03e-coach.md 5-E — 프로그램 비교: 쿼리 파라미터로 템플릿 재조회.
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { getPlanTemplates } from '$lib/api/plan';
import { parseLongRunWeekday, parseReportedLoad, parseRunWeekdays } from '$lib/planPrefill';
import type { PlanTemplate } from '$lib/types';

export interface ComparePlanData {
	templates: PlanTemplate[];
	distanceKm: number;
	raceDate: string | null;
	targetTimeSec: number | null;
	recentWeeklyKm: number | null;
	recentLongKm: number | null;
	runWeekdays: number[];
	/** P-14: 롱런 요일(null = 자동). */
	longRunWeekday: number | null;
	planMethod: string | null;
}

export async function load({ url }: { url: URL }): Promise<ComparePlanData> {
	const distanceKm = Number(url.searchParams.get('distance_km'));
	if (!Number.isFinite(distanceKm) || distanceKm <= 0) {
		throw redirect(302, `${base}/coach/plan/new`);
	}
	const raceDateParam = url.searchParams.get('race_date');
	const targetTimeParam = url.searchParams.get('target_time_sec');
	const targetTimeSec = targetTimeParam ? Number(targetTimeParam) : null;
	const reported = parseReportedLoad(url.searchParams);
	const runWeekdays = parseRunWeekdays(url.searchParams.get('run_weekdays'));

	const templates = await getPlanTemplates(
		distanceKm,
		targetTimeSec ?? undefined,
		raceDateParam ?? undefined
	);

	return {
		templates,
		distanceKm,
		raceDate: raceDateParam || null,
		targetTimeSec,
		recentWeeklyKm: reported.weeklyKm,
		recentLongKm: reported.longKm,
		runWeekdays,
		longRunWeekday: parseLongRunWeekday(url.searchParams.get('long_run'), runWeekdays),
		planMethod: url.searchParams.get('plan_method')
	};
}
