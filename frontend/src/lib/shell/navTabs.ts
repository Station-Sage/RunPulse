// 셸 주 메뉴 탭 정의와 활성 판정(순수). ShellNav 가 side/bottom 두 번 렌더할 때 공유한다.
export type NavIcon = 'today' | 'library' | 'coach';
export interface NavTab {
	href: string;
	label: string;
	/** E-12: 영어 탭 이름은 브랜드 표기로 유지하고 한글 뜻을 툴팁·접근성 이름에 덧붙인다(TXT-1 잠정). */
	ko: string;
	match: string;
	icon: NavIcon;
}

export function navTabs(base: string): NavTab[] {
	return [
		{ href: `${base}/today`, label: 'Today', ko: '오늘', match: '/today', icon: 'today' },
		{ href: `${base}/library`, label: 'Library', ko: '기록', match: '/library', icon: 'library' },
		{ href: `${base}/coach`, label: 'Coach', ko: '코치', match: '/coach', icon: 'coach' }
	];
}

/** E-12: 접근성 이름 — 보이는 영어 라벨을 앞에 두어(WCAG 2.5.3 Label in Name) 음성 명령과 맞춘다. */
export function tabAriaLabel(tab: Pick<NavTab, 'label' | 'ko'>): string {
	return `${tab.label} (${tab.ko})`;
}

export function isTabActive(pathname: string, base: string, match: string): boolean {
	return pathname.startsWith(`${base}${match}`);
}

/** S-06 — 이동 중이면 목적지 기준으로 탭을 활성 표시한다(눌렀다는 피드백). 이동이 없으면 현재 경로. */
export function tabHighlightPath(currentPath: string, pendingPath: string | null | undefined): string {
	return pendingPath ?? currentPath;
}
