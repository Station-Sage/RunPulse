// 마일스톤 응답 타입 — /today/milestones·/library/milestones·내러티브 공유(ADR-057).
/** 표시되는 마일스톤 종류(ADR-057). 내부 재계산(metric_recompute·algo_recompute)은 서버가 걸러 보내지 않는다. */
export type MilestoneType =
	| 'distance_threshold'
	| 'pb'
	| 'race_finish'
	| 'goal_set'
	| 'goal_changed'
	| 'plan_replan'
	| 'race_registered'
	| 'illness_start'
	| 'injury_start'
	| 'recovery'
	| 'longest_run'
	| 'streak_weeks';

export interface MilestoneEntry {
	id: number;
	type: MilestoneType;
	date: string;
	title: string;
	detail: string | null;
	activity_id: number | null;
}
