// Data › 설정 › AI: 현재 설정과 사용량.
import { getAiSettings, type AiSettings } from '$lib/api/data';

export interface AiPageData {
	settings: AiSettings | null;
}

export async function load(): Promise<AiPageData> {
	try {
		return { settings: await getAiSettings() };
	} catch {
		return { settings: null };
	}
}
