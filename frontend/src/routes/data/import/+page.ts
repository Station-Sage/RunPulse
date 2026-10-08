// Data › 가져오기: 최근 가져오기 이력.
import { getImports, type ImportItem } from '$lib/api/data';

export interface ImportPageData {
	history: ImportItem[] | null;
}

export async function load(): Promise<ImportPageData> {
	try {
		return { history: await getImports() };
	} catch {
		return { history: null };
	}
}
