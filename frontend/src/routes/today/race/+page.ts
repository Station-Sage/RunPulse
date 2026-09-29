import { getRaceHub } from '$lib/api/today';
import { invalidate } from '$app/navigation';
import { swrLoad } from '$lib/loadCache';
import type { RaceHubData } from '$lib/types';

export interface RaceHubPageData {
	hub: RaceHubData | null;
	/** true = 조회 실패(재시도). 목표 없음은 hub.goal == null 로 구분한다(40 design §6.1). */
	failed: boolean;
}

// 실패는 캐시에 남기지 않는다 — getRaceHub가 throw → swrLoad 미저장.
export async function load({ depends }: { depends: (key: string) => void }): Promise<RaceHubPageData> {
	depends('app:race-hub');
	try {
		return { hub: await swrLoad('app:race-hub', getRaceHub, invalidate), failed: false };
	} catch {
		return { hub: null, failed: true };
	}
}
