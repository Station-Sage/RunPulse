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
