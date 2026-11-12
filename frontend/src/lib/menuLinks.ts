// MenuDrawer 링크 정의 — 컴포넌트 밖으로 빼서 node 테스트로 경로를 고정한다.
// 링크는 `base` 를 붙여 클라이언트 라우팅으로 이동한다(v1 화면은 S5-4 에서 제거).
// v1 일몰 후 정보 구조(MENUDRAWER-POST-V1, S4-90 — design-2026-11-features/menudrawer-post-v1.md):
// 드로어는 "탭이 없는 영역(데이터)·설정·계정"의 입구이고, 탭(Today/Library/Coach) 루트와 같은 목적지는 두지 않는다.
// 라벨은 TXT-1 잠정.

export interface MenuLink {
	href: string;
	label: string;
	/** 브라우저 스모크·테스트가 찾는 고정 식별자(선택). */
	testid?: string;
}

export interface MenuGroup {
	id: 'data' | 'settings' | 'shortcuts';
	title: string;
	links: readonly MenuLink[];
}

/** V1-11 (b): '데이터 내보내기' 는 v1 `/activities/export.csv` 가 아니라 v2 내보내기(EXP) 화면(CSV·아카이브·캘린더)으로 연결한다. */
export const EXPORT_PATH = '/data/export';
export const EXPORT_LABEL = '데이터 내보내기';

/** 탭 루트 — 드로어에 다시 두지 않는다(하단 탭·좌측 사이드바가 항상 보임). shell/navTabs.ts 의 match 와 같다. */
export const TAB_ROOTS: readonly string[] = ['/today', '/library', '/coach'];

/** 드로어 그룹(순서 = 화면 순서). 경로는 base 미적용(렌더 시 `{base}` 를 붙인다). */
export const MENU_GROUPS: readonly MenuGroup[] = [
	{
		// 데이터 영역은 주 탭이 없다 — 드로어가 주 입구
		id: 'data',
		title: '데이터',
		links: [
			{ href: '/data', label: '데이터 개요' },
			{ href: '/data/sources', label: '소스 연결' },
			{ href: '/data/import', label: '가져오기' },
			{ href: EXPORT_PATH, label: EXPORT_LABEL, testid: 'menu-export-link' }
		]
	},
	{
		id: 'settings',
		title: '설정',
		links: [
			{ href: '/data/settings', label: '데이터 설정' },
			{ href: '/data/settings/profile', label: '러너 기준값' },
			{ href: '/data/settings/ai', label: 'AI 설정' }
		]
	},
	{
		// 탭에서 두 번 이상 눌러야 닿는 자주 쓰는 화면
		id: 'shortcuts',
		title: '바로가기',
		links: [
			{ href: '/library/activities', label: '활동 목록' },
			{ href: '/coach/plan', label: '훈련 계획' },
			{ href: '/today/race', label: '레이스' },
			{ href: '/library/wellness', label: '웰니스' },
			{ href: '/library/shoes', label: '신발' },
			{ href: '/library/metrics', label: '지표 가이드' }
		]
	}
];

/** 모든 드로어 링크(테스트·점검용). */
export function allMenuLinks(groups: readonly MenuGroup[] = MENU_GROUPS): MenuLink[] {
	return groups.flatMap((g) => g.links);
}
