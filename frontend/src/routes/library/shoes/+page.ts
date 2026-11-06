// V2-SHOES 신발 목록 로더 — LoadResult 로 실패를 분류하고 'app:shoes' 키로 재로드한다.
import { getShoes, type ShoeList } from '$lib/api/shoes';
import { toResult, type LoadResult } from '$lib/loadFailure';

export interface ShoesPageData {
	list: LoadResult<ShoeList>;
}

export async function load({ depends }: { depends: (key: string) => void }): Promise<ShoesPageData> {
	depends('app:shoes');
	return { list: await toResult(getShoes(true)) };
}
