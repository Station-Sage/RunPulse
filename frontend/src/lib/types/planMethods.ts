import type { ReplanParams } from './index';

export type MethodReplanParams = ReplanParams & { plan_method?: string };

export interface PlanMethodInfo {
	id: string;
	label: string;
	summary: string;
	pros: string[];
	cons: string[];
	target_runners: string;
	sources: string[];
}

export interface PlanMethodsState {
	goal_id: number;
	distance_label: string;
	current: string;
	methods: PlanMethodInfo[];
}

export interface PlanMethodRecommend {
	source: 'ai' | 'rule';
	recommended: string;
	ranking: string[];
	reasons: Record<string, string>;
	warnings: Record<string, string>;
	current: string;
	pending: boolean;
}
