// 마일스톤 전체 이력 로더 — ?type=종류(선택). 첫 페이지만 불러오고 이후는 화면에서 '더 보기'(커서). 실패는 LoadResult.
import { getMilestoneHistory, type MilestoneHistory } from '$lib/api/milestones';
import { PAGE_SIZE, parseTypeParam } from '$lib/milestoneHistory';
import { toResult, type LoadResult } from '$lib/loadFailure';

export interface MilestonesPageData {
	type: string | null;
	history: LoadResult<MilestoneHistory>;
}

export async function load({ url, depends }: { url: URL; depends: (key: string) => void }): Promise<MilestonesPageData> {
	depends('app:milestones');
	const type = parseTypeParam(url.searchParams.get('type'));
	return { type, history: await toResult(getMilestoneHistory({ type, limit: PAGE_SIZE })) };
}
