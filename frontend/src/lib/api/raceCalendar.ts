// 대회 캘린더 API (RC-c) — /api/v1/race-calendar*. 쓰기는 서버가 commit 하고 오류는 ApiError(code, details)로 온다.
import { apiFetch } from './client';

export type RacePriority = 'A' | 'B' | 'C';
export type RaceStatus = 'planned' | 'done' | 'cancelled';
export type AdaptChoice = 'unasked' | 'later' | 'adapt' | 'no_adapt';
export type PlanState = 'none' | 'applied' | 'stale';
export type RaceGoalType = 'finish' | 'time' | 'pb';

export interface RaceRow {
	id: number;
	name: string;
	race_date: string;
	distance_km: number;
	priority: RacePriority;
	goal_type: RaceGoalType | null;
	goal_value: number | null;
	adapt_choice: AdaptChoice;
	plan_state: PlanState;
	taper_days: number | null;
	recovery_days: number | null;
	status: RaceStatus;
	race_result_id: number | null;
	note: string | null;
}

export interface RaceView extends RaceRow {
	needs_review: boolean;
	goal_linked: boolean;
}

export interface RaceZones {
	needs_review: RaceRow[];
	upcoming: RaceRow[];
	past: RaceRow[];
	cancelled: RaceRow[];
	today: string;
	basis?: string;
	goal_race_id: number | null;
}

export interface RaceDraft {
	name: string;
	race_date: string;
	distance_km: number;
	priority: RacePriority;
	goal_type?: RaceGoalType;
	goal_value?: number;
	taper_days?: number;
	recovery_days?: number;
	note?: string;
}

export interface PlanRowLite {
	date: string;
	workout_type: string;
	distance_km: number | null;
}
export interface ImpactChange {
	before: PlanRowLite;
	after: PlanRowLite;
}
export interface RaceImpact {
	race_id: number;
	n: number;
	changes: ImpactChange[];
}

export interface ExistingA {
	id: number;
	name: string;
	race_date: string;
	distance_km: number;
	status: RaceStatus;
	active_goal_id: number | null;
}

const BASE = '/race-calendar';
const post = (path: string, body: unknown = {}) =>
	apiFetch<RaceView>(`${BASE}${path}`, { method: 'POST', body: JSON.stringify(body) });

export const getRaceZones = () => apiFetch<RaceZones>(BASE);
export const createRace = (d: RaceDraft) => apiFetch<RaceView>(BASE, { method: 'POST', body: JSON.stringify(d) });
export const updateRace = (id: number, d: Partial<RaceDraft>) =>
	apiFetch<RaceView>(`${BASE}/${id}`, { method: 'PATCH', body: JSON.stringify(d) });
export const cancelRace = (id: number, cancelGoal = false) =>
	apiFetch<RaceView & { goal_cancelled: boolean }>(`${BASE}/${id}`, {
		method: 'DELETE',
		body: JSON.stringify({ cancel_goal: cancelGoal })
	});
export const getRaceImpact = (id: number) => apiFetch<RaceImpact>(`${BASE}/${id}/impact`);
export const setRacePlan = (id: number, action: 'adapt' | 'later' | 'no_adapt' | 'undo') =>
	post(`/${id}/plan`, { action });
export const restoreRace = (
	id: number,
	opts: { confirm_past?: boolean; demote_existing_a?: boolean; goal_link?: { race_id: number } } = {}
) => post(`/${id}/restore`, opts) as Promise<RaceView & { restore: { replan_applied: boolean | null; reason: string | null } }>;
export const reopenRace = (id: number, opts: { demote_existing_a?: boolean; goal_link?: { race_id: number } } = {}) =>
	post(`/${id}/reopen`, opts);
