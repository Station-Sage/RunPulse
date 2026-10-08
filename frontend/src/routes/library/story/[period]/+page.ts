import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { period } = params;

	const response = await fetch(`/api/v1/library/story/${period}`);
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.error?.message || 'Failed to load story');
	}

	const { data } = await response.json();
	return data;
};
