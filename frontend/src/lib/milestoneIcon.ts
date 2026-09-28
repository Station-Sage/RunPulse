// 마일스톤 타입 → §C8 아이콘 이름. 이모지 금지(§C8) — Today/MonthNarrative/MilestonesPanel 공유.
import type { IconName } from '$lib/icon';

const MILESTONE_ICON: Record<string, IconName> = {
	distance_threshold: 'target',
	pb: 'trophy',
	metric_recompute: 'refresh'
};

export function milestoneIconName(type: string): IconName {
	return MILESTONE_ICON[type] ?? 'note';
}
