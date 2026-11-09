// 셸 주 메뉴 탭 정의와 활성 판정(순수). ShellNav 가 side/bottom 두 번 렌더할 때 공유한다.
export type NavIcon = 'today' | 'library' | 'coach';
export interface NavTab {
	href: string;
	label: string;
	match: string;
	icon: NavIcon;
}

export function navTabs(base: string): NavTab[] {
	return [
		{ href: `${base}/today`, label: 'Today', match: '/today', icon: 'today' },
		{ href: `${base}/library`, label: 'Library', match: '/library', icon: 'library' },
		{ href: `${base}/coach`, label: 'Coach', match: '/coach', icon: 'coach' }
	];
}

export function isTabActive(pathname: string, base: string, match: string): boolean {
	return pathname.startsWith(`${base}${match}`);
}

/** S-06 — 이동 중이면 목적지 기준으로 탭을 활성 표시한다(눌렀다는 피드백). 이동이 없으면 현재 경로. */
export function tabHighlightPath(currentPath: string, pendingPath: string | null | undefined): string {
	return pendingPath ?? currentPath;
}
