// Data › 설정 › 러너 기준값.
import { getProfile, type ProfileRow } from '$lib/api/data';

export interface ProfilePageData {
	rows: ProfileRow[] | null;
}

export async function load(): Promise<ProfilePageData> {
	try {
		return { rows: (await getProfile()).rows };
	} catch {
		return { rows: null };
	}
}
