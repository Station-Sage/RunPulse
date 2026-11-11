// P-25 — 플랜 상세 스트리밍 로더(순수 모듈, API 주입). 머리·이번 주 목록에 필요한 플랜만 기다리고,
// 아래쪽 보조 데이터는 약속으로 넘겨 화면이 자리 표시(스켈레톤) 뒤 채운다.
// SPA(ssr=false)라 SvelteKit 은 반환한 약속을 그대로 page data 로 넘긴다(직렬화 없음).
// 넘기는 약속은 거부되지 않는다(toResult·catch) — 처리 안 된 거부나 +error 전환이 생기지 않는다.
import { toResult, type Failure, type LoadResult } from './loadFailure.ts';
import type { ActivePlan, TodaysAdjustment, PlanAdaptation, ReplanEntry, PlanWeeks } from './types';

export interface PlanDetailPageData {
	plan: ActivePlan | null;
	errorMessage: string | null;
	planFailure: Failure | null;
	/** 보조 데이터(기다리지 않음). 실패 분류가 필요한 둘은 LoadResult, 나머지는 실패 시 null. */
	adjustment: Promise<TodaysAdjustment | null>;
	adaptation: Promise<LoadResult<PlanAdaptation> | null>;
	replanEntry: Promise<ReplanEntry | null>;
	weeks: Promise<LoadResult<PlanWeeks> | null>;
}

export interface PlanDetailApi {
	getActivePlan: (goalId: number) => Promise<ActivePlan>;
	getTodaysAdjustment: () => Promise<unknown>;
	getPlanAdaptation: () => Promise<PlanAdaptation>;
	getReplanLast: () => Promise<{ entry?: ReplanEntry | null } | null>;
	getPlanWeeks: (goalId: number) => Promise<PlanWeeks>;
}

function none<T>(): Promise<T | null> {
	return Promise.resolve(null);
}

function empty(errorMessage: string | null, planFailure: Failure | null): PlanDetailPageData {
	return { plan: null, errorMessage, planFailure, adjustment: none(), adaptation: none(), replanEntry: none(), weeks: none() };
}

export async function loadPlanDetail(rawId: string, api: PlanDetailApi): Promise<PlanDetailPageData> {
	const goalId = parseInt(rawId, 10);
	if (isNaN(goalId)) return empty('잘못된 플랜 ID입니다.', null);
	// 요청은 모두 지금 시작한다(병렬). 기다리는 건 플랜 하나.
	const planP = toResult(api.getActivePlan(goalId));
	const adjustment = (api.getTodaysAdjustment() as Promise<TodaysAdjustment>).catch(() => null);
	const adaptation = toResult(api.getPlanAdaptation());
	const replanEntry = api
		.getReplanLast()
		.then((r) => r?.entry ?? null)
		.catch(() => null);
	const weeks = toResult(api.getPlanWeeks(goalId));
	const planR = await planP;
	if (!planR.ok) return empty('플랜을 불러올 수 없습니다.', planR.failure);
	return { plan: planR.data, errorMessage: null, planFailure: null, adjustment, adaptation, replanEntry, weeks };
}
