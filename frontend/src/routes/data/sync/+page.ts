// Data › 동기화 — 소스별 상태·실행 기록. 상태 자체는 syncStore(폴링)가 갱신한다.
import { getDataRuns, type DataRun } from '$lib/api/data';

export interface DataSyncPageData {
	runs: DataRun[] | null;
}

export async function load({ depends }: { depends: (key: string) => void }): Promise<DataSyncPageData> {
	depends('app:data-sync');
	try {
		return { runs: (await getDataRuns({ limit: 30 })).runs };
	} catch {
		return { runs: null };
	}
}
