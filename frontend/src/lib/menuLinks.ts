// MenuDrawer 링크 정의 — 컴포넌트 밖으로 빼서 node 테스트로 경로를 고정한다.
// v1 링크(`v1`)는 SvelteKit 라우터 밖이라 전체 새로고침(data-sveltekit-reload)이 필요하고,
// v2 링크는 `base` 를 붙여 클라이언트 라우팅으로 이동한다.

export interface MenuLink {
	href: string;
	label: string;
}

/** 기존 화면(v1) 링크 — 경로는 v1 라우트 그대로(base 미적용). */
export const V1_QUICK_LINKS: readonly MenuLink[] = [
	{ href: '/dashboard', label: '대시보드' },
	{ href: '/activities', label: '활동 목록' },
	{ href: '/wellness', label: '웰니스' },
	{ href: '/training', label: '훈련 계획' },
	{ href: '/race', label: '레이스' },
	{ href: '/ai-coach', label: 'AI 코치' },
	{ href: '/shoes', label: '신발' }
];

/** 데이터·설정 중 아직 v1 인 링크. */
export const V1_DATA_LINKS: readonly MenuLink[] = [
	{ href: '/settings', label: '설정' },
	{ href: '/guide', label: '지표 가이드' }
];

/** V1-11 (b): 'CSV 내보내기' 는 v1 `/activities/export.csv` 가 아니라 v2 내보내기(EXP) 화면으로 연결한다. */
export const EXPORT_PATH = '/data/export';
export const EXPORT_LABEL = 'CSV 내보내기';
