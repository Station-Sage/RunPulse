// 신규 계정(소스 0·활동 0·온보딩 pending)을 /welcome으로 보낸다 — Today 빈 분기와 빈 DB(200) 양쪽에서 공용.
import { goto } from '$app/navigation';
import { base } from '$app/paths';
import { getSyncState } from './api/data';
import { getPreferences } from './api/me';
import { shouldRedirect } from './onboarding.ts';

export async function redirectToWelcomeIfNew(): Promise<void> {
	try {
		const [s, prefs] = await Promise.all([getSyncState(), getPreferences()]);
		if (shouldRedirect(s, prefs.onboarding)) await goto(`${base}/welcome`, { replaceState: true });
	} catch {
		/* 조회 실패는 리다이렉트하지 않는다 */
	}
}
