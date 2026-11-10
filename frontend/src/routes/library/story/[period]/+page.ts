import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client';
import { getStory } from '$lib/api/story';

export async function load({ params }: { params: { period: string } }) {
	try {
		return { story: await getStory(params.period) };
	} catch (e) {
		// M-16: 형식 오류(예: /story/2026)는 볼 수 있는 형식을 알려 준다. 문구 임시(TXT-1).
		if (e instanceof ApiError && e.status === 400) error(404, '월(예: 2026-09)이나 주(예: 2026-W40) 단위만 볼 수 있어요');
		throw e;
	}
}
