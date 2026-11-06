// Training Balance Radar 응답 타입 — GET /library/metrics/training-balance (balance-radar 설계 §6).
export type BalanceAxisKey = 'volume' | 'long_run' | 'easy_base' | 'quality' | 'load' | 'recovery';
export type BalanceStatus = 'low' | 'balanced' | 'high';
export type BalanceBasis = 'plan' | 'goal' | 'default_rule' | 'personal_peak' | 'personal_baseline';
export type BalanceState = 'ready' | 'partial' | 'collecting';

export interface BalanceAxis {
	key: BalanceAxisKey;
	label: string;
	unit: string;
	actual: number | null;
	target: number | null;
	basis: BalanceBasis | null;
	score: number | null;
	band: [number, number];
	status: BalanceStatus | null;
	reason: string | null;
	reason_text: string | null;
	source: string[];
	computed_on: string | null;
	stale: boolean;
}

export interface TrainingBalance {
	as_of: string;
	window_weeks: number;
	state: BalanceState;
	axes: BalanceAxis[];
	compare: { as_of: string; axes: { key: BalanceAxisKey; score: number | null }[] } | null;
	aux: {
		tsb: number | null;
		monotony: number | null;
		tanda_required_km: number | null;
		tids_pattern: string | null;
		race_share_of_quality: number | null;
	};
	notes: string[];
	stale_text: string;
}
