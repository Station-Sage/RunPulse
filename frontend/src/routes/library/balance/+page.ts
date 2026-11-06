// Training Balance 상세 로더 — ?date=YYYY-MM-DD(없으면 오늘), 28일 전 비교 포함. 실패는 LoadResult 로 분류.
import { getTrainingBalance } from '$lib/api/balance';
import { parseDateParam } from '$lib/balanceView';
import { toResult, type LoadResult } from '$lib/loadFailure';
import type { TrainingBalance } from '$lib/types/trainingBalance';

export interface BalancePageData {
	balance: LoadResult<TrainingBalance>;
}

export async function load({ url, depends }: { url: URL; depends: (key: string) => void }): Promise<BalancePageData> {
	depends('app:balance');
	return { balance: await toResult(getTrainingBalance(parseDateParam(url.searchParams.get('date')), 28)) };
}
