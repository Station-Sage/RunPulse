// P-25 — 페이지 이동 대기 중(로더가 끝나기 전) 보여 줄 페이지별 스켈레톤 종류. 로더는 바꾸지 않는다.
export type NavSkeletonKind = 'plan-detail';

export interface NavPoint {
	route: { id: string | null };
	params: Record<string, string> | null;
}

const SKELETON_ROUTES: Record<string, NavSkeletonKind> = {
	'/coach/plan/[id]': 'plan-detail'
};

/**
 * from → to 이동에 쓸 스켈레톤. 대상 라우트가 표에 있고, 같은 화면(같은 라우트·같은 id)에 머무는 게 아닐 때만.
 * 같은 화면 안의 쿼리·해시 변경이나 데이터 다시 읽기(invalidate)는 기존 화면을 그대로 둔다.
 */
export function navSkeletonKind(from: NavPoint | null | undefined, to: NavPoint | null | undefined): NavSkeletonKind | null {
	const id = to?.route?.id;
	if (!id) return null;
	const kind = SKELETON_ROUTES[id];
	if (!kind) return null;
	if (from?.route?.id === id && (from.params?.id ?? null) === (to?.params?.id ?? null)) return null;
	return kind;
}
