// S6 소스 비교 상세(쌍 목록) 로더 — pairs API만 사용.
import { getProviderPairs } from '$lib/api/providers';
import { ApiError } from '$lib/api/client';
import { parseDays } from '$lib/providerMatrix';
import type { ProviderPairsData } from '$lib/types';

export interface ProviderGroupPageData {
	group: string;
	days: number;
	pairs: ProviderPairsData | null;
	errorMessage: string | null;
}

export async function load({ params, url }: { params: { group: string }; url: URL }): Promise<ProviderGroupPageData> {
	const days = parseDays(url.searchParams.get('days'));
	try {
		return { group: params.group, days, pairs: await getProviderPairs(params.group, days), errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '소스 비교 상세를 불러올 수 없습니다.';
		return { group: params.group, days, pairs: null, errorMessage: message };
	}
}
