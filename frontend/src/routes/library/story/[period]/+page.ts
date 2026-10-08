import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client';
import { getStory } from '$lib/api/story';

export async function load({ params }: { params: { period: string } }) {
	try {
		return { story: await getStory(params.period) };
	} catch (e) {
		if (e instanceof ApiError && e.status === 400) error(404, e.message);
		throw e;
	}
}
