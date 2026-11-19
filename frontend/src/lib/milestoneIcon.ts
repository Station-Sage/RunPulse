// 마일스톤 타입 → §C8 아이콘 이름·한국어 라벨. 이모지 금지(§C8) — Today/월간 라우트/MilestonesPanel/전체 이력 공유.
import type { IconName } from '$lib/icon';
import type { MilestoneType } from '$lib/types';

const MILESTONE_ICON: Record<MilestoneType, IconName> = {
	distance_threshold: 'target',
	pb: 'trophy',
	race_finish: 'medal',
	goal_set: 'flag',
	goal_changed: 'note',
	plan_replan: 'refresh',
	race_registered: 'calendar',
	illness_start: 'warning',
	injury_start: 'warning',
	recovery: 'heart',
	longest_run: 'activity',
	streak_weeks: 'flame'
};

/** 필터 칩 순서 = 이 객체의 키 순서(기록 → 대회 → 계획 → 몸 상태). */
export const MILESTONE_LABEL: Record<MilestoneType, string> = {
	distance_threshold: '누적 거리',
	pb: '개인 최고',
	longest_run: '최장거리',
	streak_weeks: '연속 훈련',
	race_finish: '대회 완주',
	race_registered: '대회 등록',
	goal_set: '목표 설정',
	goal_changed: '목표 수정',
	plan_replan: '계획 재조정',
	illness_start: '질병',
	injury_start: '부상',
	recovery: '회복'
};

export function milestoneIconName(type: string): IconName {
	return MILESTONE_ICON[type as MilestoneType] ?? 'note';
}

export function milestoneLabel(type: string): string {
	return MILESTONE_LABEL[type as MilestoneType] ?? '기록';
}
