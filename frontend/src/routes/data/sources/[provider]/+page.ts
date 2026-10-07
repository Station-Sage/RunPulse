// Data › 소스 상세 — 연결 상태·보유 수·12개월 커버리지·최근 기록.
import { getDataSource, type DataSourceDetail } from '$lib/api/data';
import { ApiError } from '$lib/api/client';

export interface DataSourcePageData {
	provider: string;
	detail: DataSourceDetail | null;
	notFound: boolean;
}

export async function load({ params }: { params: { provider: string } }): Promise<DataSourcePageData> {
	try {
		return { provider: params.provider, detail: await getDataSource(params.provider), notFound: false };
	} catch (e) {
		return { provider: params.provider, detail: null, notFound: e instanceof ApiError && e.status === 404 };
	}
}
