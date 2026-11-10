// S6 소스 비교 매트릭스 로더.
import { getProviderMatrix } from '$lib/api/providers';
import { ApiError } from '$lib/api/client';
import { daysInvalid, parseDays } from '$lib/providerMatrix';
import type { ProviderMatrixData } from '$lib/types';

export interface ProvidersMatrixPageData {
	matrix: ProviderMatrixData | null;
	days: number;
	/** M-20: ?days= 가 쓸 수 없는 값이었음(4주로 보고 안내). */
	daysDropped: boolean;
	errorMessage: string | null;
}

export async function load({ url }: { url: URL }): Promise<ProvidersMatrixPageData> {
	const days = parseDays(url.searchParams.get('days'));
	const daysDropped = daysInvalid(url.searchParams.get('days'));
	try {
		return { matrix: await getProviderMatrix(days), days, daysDropped, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '소스 비교를 불러올 수 없습니다.';
		return { matrix: null, days, daysDropped, errorMessage: message };
	}
}
