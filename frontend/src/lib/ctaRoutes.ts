// 같은 의도의 CTA 는 한 목적지로 — 화면마다 새로 쓰지 말고 여기서 가져온다.
export const SOURCE_CONNECT = '/data/sources';
export const PLAN_HOME = '/coach/plan';
export const PLAN_NEW = '/coach/plan/new';

export function planDetail(goalId: number): string {
	return `/coach/plan/${goalId}`;
}

// 세션 상세. 플랜(goalId)이나 날짜를 모르면 플랜 홈으로.
export function sessionDetail(goalId: number | null | undefined, date: string | null | undefined): string {
	if (goalId == null || !date) return PLAN_HOME;
	return `/coach/plan/${goalId}/session/${date}`;
}
