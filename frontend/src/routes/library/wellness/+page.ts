import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { getWellnessDetail } from '$lib/api/wellness';
import { isValidDate } from '$lib/wellnessDay';

// /library/wellness(?date=) → /library/wellness/:date 로 정규화(서버가 오늘/미래를 오늘로 보정).
export async function load({ url }: { url: URL }) {
	const q = url.searchParams.get('date');
	const target = q && isValidDate(q) ? q : undefined;
	let date: string;
	try {
		date = (await getWellnessDetail(target)).date;
	} catch {
		date = target ?? new Date().toLocaleDateString('sv-SE');
	}
	redirect(307, `${base}/library/wellness/${date}`);
}
