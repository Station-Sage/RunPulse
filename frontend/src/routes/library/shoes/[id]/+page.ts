// V2-SHOES 신발 상세 로더 — 상세·배정 활동 첫 페이지를 각각 LoadResult 로(활동 목록 실패가 상세를 막지 않음).
import { getShoe, getShoeActivities, getShoes, type ShoeActivityPage, type ShoeDetail, type Shoe } from '$lib/api/shoes';
import { toResult, type LoadResult } from '$lib/loadFailure';

export interface ShoeDetailPageData {
	id: number;
	shoe: LoadResult<ShoeDetail>;
	activities: LoadResult<ShoeActivityPage>;
	others: Shoe[];
}

export async function load({
	params,
	depends
}: {
	params: { id: string };
	depends: (key: string) => void;
}): Promise<ShoeDetailPageData> {
	depends('app:shoes');
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) {
		const failure = { kind: 'not_found' as const, status: 404, code: 'NOT_FOUND', detail: '404 NOT_FOUND' };
		return { id, shoe: { ok: false, failure }, activities: { ok: false, failure }, others: [] };
	}
	const [shoe, activities, list] = await Promise.all([
		toResult(getShoe(id)),
		toResult(getShoeActivities(id)),
		getShoes(false).catch(() => null)
	]);
	return { id, shoe, activities, others: (list?.shoes ?? []).filter((s) => s.id !== id) };
}
