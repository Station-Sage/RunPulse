// 활동 행 링크 — 상세에서 "돌아가기" 목적지를 결정하는 ?from= 쿼리를 붙인다.
export type ActivityOrigin = 'home' | 'list' | 'today';

export function activityDetailHref(base: string, id: number, from: ActivityOrigin): string {
	return `${base}/library/${id}?from=${from}`;
}
