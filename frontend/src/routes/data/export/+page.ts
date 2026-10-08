// Data › 내보내기: 아카이브 이력.
import { getExports, type ExportItem } from '$lib/api/data';

export interface ExportPageData {
	history: ExportItem[] | null;
}

export async function load(): Promise<ExportPageData> {
	try {
		return { history: await getExports() };
	} catch {
		return { history: null };
	}
}
