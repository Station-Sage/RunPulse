// Data 개요 — 요약 타일·소스 카드·최근 기록. 블록별로 실패를 격리한다.
import { getDataSources, getDataSummary, type DataSourceCard, type DataSummary } from '$lib/api/data';
import { invalidate } from '$app/navigation';
import { swrLoad } from '$lib/loadCache';

export interface DataHomeData {
	summary: DataSummary | null;
	sources: DataSourceCard[] | null;
}

export async function load({ depends }: { depends: (key: string) => void }): Promise<DataHomeData> {
	depends('app:data-home');
	const [summary, sources] = await Promise.allSettled([
		swrLoad('app:data-summary', getDataSummary, invalidate),
		swrLoad('app:data-sources', () => getDataSources().then((r) => r.sources), invalidate)
	]);
	return {
		summary: summary.status === 'fulfilled' ? summary.value : null,
		sources: sources.status === 'fulfilled' ? sources.value : null
	};
}
