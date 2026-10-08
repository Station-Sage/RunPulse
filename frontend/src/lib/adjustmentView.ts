// 계획 조정 카드의 순수 표시 로직 (ADR-035).
import type { AdjustmentState, PlanAdjustment } from '$lib/types';

export type AdjustmentActions = 'decide' | 'undo' | 'none';

const STATE_TEXT: Partial<Record<AdjustmentState, string>> = {
	declined: '조정을 거절했어요 · 원래 계획대로 진행해요',
	undone: '조정을 되돌렸어요 · 원래 계획대로 진행해요',
	expired: '제안 기간이 지났어요',
	stale: '계획이 바뀌어 이 조정은 더 이상 적용되지 않아요'
};

export function adjustmentActions(state: AdjustmentState | undefined): AdjustmentActions {
	if (state === 'proposed') return 'decide';
	if (state === 'accepted') return 'undo';
	return 'none';
}

export function adjustmentStateText(state: AdjustmentState | undefined): string | null {
	return (state && STATE_TEXT[state]) || null;
}

export function adjustmentHeadline(state: AdjustmentState | undefined): string | null {
	if (state === 'proposed') return '오늘 훈련 조정 제안';
	if (state === 'accepted') return '조정 적용됨';
	return null;
}

export function adjustmentDelta(adj: PlanAdjustment, label: (t: string) => string): string {
	const b = adj.before.workout_type ?? '';
	const a = adj.after.workout_type ?? '';
	const km = (v: number | null) => (v == null ? '-' : `${v}km`);
	const type = b === a ? label(a) : `${label(b)} → ${label(a)}`;
	return adj.before.distance_km === adj.after.distance_km
		? type
		: `${type} (${km(adj.before.distance_km)} → ${km(adj.after.distance_km)})`;
}
