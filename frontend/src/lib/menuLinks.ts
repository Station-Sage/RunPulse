// MenuDrawer 링크 정의 — 컴포넌트 밖으로 빼서 node 테스트로 경로를 고정한다.
// 링크는 `base` 를 붙여 클라이언트 라우팅으로 이동한다(v1 화면은 S5-4 에서 제거).

export interface MenuLink {
	href: string;
	label: string;
}

/** v2 바로가기 — 경로는 base 미적용(렌더 시 `{base}` 를 붙인다). */
export const QUICK_LINKS: readonly MenuLink[] = [
	{ href: '/today', label: '오늘' },
	{ href: '/library/activities', label: '활동 목록' },
	{ href: '/library/wellness', label: '웰니스' },
	{ href: '/coach/plan', label: '훈련 계획' },
	{ href: '/today/race', label: '레이스' },
	{ href: '/coach', label: 'AI 코치' }
];

/** 데이터·설정 중 v2 화면 링크. */
export const DATA_LINKS: readonly MenuLink[] = [
	{ href: '/data/settings', label: '설정' },
	{ href: '/library/metrics', label: '지표 가이드' }
];

/** V1-11 (b): 'CSV 내보내기' 는 v1 `/activities/export.csv` 가 아니라 v2 내보내기(EXP) 화면으로 연결한다. */
export const EXPORT_PATH = '/data/export';
export const EXPORT_LABEL = 'CSV 내보내기';
