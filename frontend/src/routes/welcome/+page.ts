import { getPreferences } from '$lib/api/me';

export async function load({ url }: { url: URL }) {
	const prefs = await getPreferences().catch(() => null);
	return { saved: prefs?.onboarding_step ?? 0, query: url.searchParams.get('step') };
}
