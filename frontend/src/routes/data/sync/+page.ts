// Data › 동기화 — 소스별 상태·실행 기록. 상태 자체는 syncStore(폴링)가 갱신한다.
import { getAutoSync, getDataRuns, type AutoSyncSettings, type DataRun } from '$lib/api/data';

export interface DataSyncPageData {
	runs: DataRun[] | null;
	auto: AutoSyncSettings | null;
}

export async function load({ depends }: { depends: (key: string) => void }): Promise<DataSyncPageData> {
	depends('app:data-sync');
	const [runs, auto] = await Promise.allSettled([getDataRuns({ limit: 30 }), getAutoSync()]);
	return {
		runs: runs.status === 'fulfilled' ? runs.value.runs : null,
		auto: auto.status === 'fulfilled' ? auto.value : null
	};
}
