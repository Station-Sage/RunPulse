// Data › 소스 — 4개 소스 목록.
import { getDataSources, type DataSourceCard } from '$lib/api/data';

export interface DataSourcesPageData {
	sources: DataSourceCard[] | null;
}

export async function load(): Promise<DataSourcesPageData> {
	try {
		return { sources: (await getDataSources()).sources };
	} catch {
		return { sources: null };
	}
}
