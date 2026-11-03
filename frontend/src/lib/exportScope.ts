// 내보내기 범위 선택 — 그룹 메타·기본 선택·확인 필요 여부·요청 본문.
export interface ExportGroup {
	key: string;
	label: string;
	default: boolean;
	sensitive: boolean;
}

export const GROUP_HINTS: Record<string, string> = {
	activities: '활동·랩·스트림 요약',
	streams: '초 단위 스트림(용량이 커요)',
	metrics: '일별 지표·피트니스 추이',
	plans: '훈련 계획',
	checkins: '컨디션 체크인',
	episodes: '아프거나 쉬었던 기록',
	races: '대회 기록과 예정',
	coach: 'AI 코치 대화',
	profile: '러너 프로필',
	raw: '소스별 원본 데이터'
};

export function defaultSelection(groups: ExportGroup[]): string[] {
	return groups.filter((g) => g.default).map((g) => g.key);
}

/** 건강 정보(아픈 기간)가 담기는 그룹을 고르면 받기 전에 한 번 더 확인한다. */
export function needsConfirm(selected: string[]): boolean {
	return selected.includes('episodes');
}

export function toggleKey(selected: string[], key: string): string[] {
	return selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key];
}

export function archiveBody(
	selected: string[],
	includeDismissed: boolean,
	range: { from?: string; to?: string }
) {
	return {
		groups: selected,
		include_dismissed: selected.includes('episodes') && includeDismissed,
		...range
	};
}
